"""
FIRS ATRS (Automated Tax Remittance System) client.

B2C real-time POS receipt fiscalization.
Auth: OAuth 2.0 password grant → Bearer token (24h TTL).
Security: MD5(secret + vat_number + business_place + device + bill_number + datetime + total)

Dev:  https://api-dev.i-fis.com
Prod: https://atrs-api.firs.gov.ng

All settings are read from Nigeria Compliance Settings (single DocType).
"""
from __future__ import annotations

import hashlib
from typing import Any

import frappe
import requests
from frappe import _
from frappe.utils import now_datetime

_SETTINGS_DOCTYPE = "Nigeria Compliance Settings"
_TOKEN_CACHE_KEY = "zinye_ng:atrs_token"
_TOKEN_TTL = 82_800  # 23h — refresh before 24h expiry


class ATRSError(Exception):
    pass


def _get_settings():
    return frappe.get_cached_doc(_SETTINGS_DOCTYPE)


def _base_url(settings) -> str:
    return (
        "https://atrs-api.firs.gov.ng"
        if settings.atrs_environment == "Production"
        else "https://api-dev.i-fis.com"
    )


def _get_token(settings) -> str:
    cached = frappe.cache.get_value(_TOKEN_CACHE_KEY)
    if cached:
        return cached

    resp = requests.post(
        f"{_base_url(settings)}/oauth2/token",
        json={
            "grant_type": "password",
            "client_id": settings.atrs_client_id,
            "client_secret": settings.get_password("atrs_client_secret"),
            "username": settings.atrs_username,
            "password": settings.get_password("atrs_password"),
        },
        timeout=30,
    )
    if not resp.ok:
        raise ATRSError(f"ATRS auth failed [{resp.status_code}]: {resp.text}")

    token = resp.json()["access_token"]
    frappe.cache.set_value(_TOKEN_CACHE_KEY, token, expires_in_sec=_TOKEN_TTL)
    return token


def _security_code(settings, bill_number: int, bill_datetime: str, total_value: float) -> str:
    secret = settings.get_password("atrs_client_secret")
    raw = (
        secret
        + settings.atrs_vat_number
        + settings.atrs_business_place
        + settings.atrs_business_device
        + str(bill_number)
        + bill_datetime
        + str(total_value)
    )
    return hashlib.md5(raw.encode()).hexdigest()  # noqa: S324 — FIRS mandates MD5


def submit_receipt(
    bill_number: int,
    total_value: float,
    payment_type: str,
    *,
    tax_free: float = 0.0,
    client_vat_number: str = "",
    vat_rate: float = 7.5,
    bill_datetime: str | None = None,
    currency_code: str = "NGN",
) -> dict[str, Any]:
    """
    Submit a B2C receipt to FIRS ATRS.
    payment_type: C=cash, T=transfer, K=credit card, D=debit card, P=post, O=other
    Returns the ATRS response dict (includes payment_code on success).
    """
    settings = _get_settings()
    if not settings.atrs_enabled:
        return {}

    if bill_datetime is None:
        # WAT = UTC+1
        bill_datetime = now_datetime().strftime("%Y-%d-%mT%H:%M:%S")

    vat_amount = round((total_value - tax_free) * (vat_rate / (100 + vat_rate)), 2)
    base_value = round(total_value - tax_free - vat_amount, 2)

    payload = {
        "vat_number": settings.atrs_vat_number,
        "business_place": settings.atrs_business_place,
        "business_device": settings.atrs_business_device,
        "bill_number": bill_number,
        "bill_datetime": bill_datetime,
        "total_value": total_value,
        "tax_free": tax_free,
        "payment_type": payment_type,
        "currency_code": currency_code,
        "security_code": _security_code(settings, bill_number, bill_datetime, total_value),
        "bill_taxes": {
            "rate": vat_rate,
            "base_value": base_value,
            "value": vat_amount,
        },
    }
    if client_vat_number:
        payload["client_vat_number"] = client_vat_number

    token = _get_token(settings)
    resp = requests.post(
        f"{_base_url(settings)}/v1/bills/report",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )

    if not resp.ok:
        raise ATRSError(f"ATRS submission failed [{resp.status_code}]: {resp.text}")

    return resp.json()


@frappe.whitelist()
def submit_pos_invoice_to_atrs(pos_invoice: str) -> dict:
    """Whitelist handler: submit a submitted POS Invoice to FIRS ATRS."""
    doc = frappe.get_doc("POS Invoice", pos_invoice)
    if doc.docstatus != 1:
        frappe.throw(_("Only submitted POS Invoices can be sent to FIRS ATRS."))

    payment_map = {"Cash": "C", "Bank Transfer": "T", "Credit Card": "K", "Debit Card": "D"}
    payment_type = payment_map.get(doc.mode_of_payment, "O")

    result = submit_receipt(
        bill_number=int("".join(filter(str.isdigit, doc.name)) or "0"),
        total_value=float(doc.grand_total),
        payment_type=payment_type,
        client_vat_number=frappe.db.get_value("Customer", doc.customer, "ng_tin") or "",
        currency_code=doc.currency or "NGN",
    )

    _log_atrs(doc, result, payment_type)
    return result


def _log_atrs(doc, result: dict, payment_type: str):
    log = frappe.new_doc("Nigeria ATRS Log")
    log.document_type = doc.doctype
    log.document_name = doc.name
    log.bill_number = doc.name
    log.total_value = doc.grand_total
    log.payment_type = payment_type
    log.currency_code = doc.currency or "NGN"
    log.status = "Submitted" if result.get("payment_code") else "Failed"
    log.payment_code = result.get("payment_code", "")
    log.error_message = result.get("message", "") if not result.get("payment_code") else ""
    if log.status == "Submitted":
        log.submitted_at = now_datetime()
    log.insert(ignore_permissions=True)
    frappe.db.commit()
