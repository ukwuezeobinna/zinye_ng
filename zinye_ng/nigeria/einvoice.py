"""
NRS FIRSMBS (Merchant Buyer Solution) e-invoicing client.

Used for B2B pre-clearance e-invoicing. Every Sales Invoice to a VAT-registered
buyer must be submitted to FIRS, which validates and returns an IRN + CSID before
the invoice is legally valid.

Portal:     https://einvoice.firs.gov.ng  (register as System Integrator)
Auth:       API Key + Secret Key
Format:     JSON (UBL BIS Billing 3.0 schema, 55 mandatory fields, 8 categories)
Model:      Pre-clearance — submit → validate (≤2h) → IRN + CSID issued
Security:   OAuth 2.0, TLS 1.3, AES-256, ECDSA digital signature (XAdES)

TODO: Replace _PLACEHOLDER_* constants with real values after registering at
      https://einvoice.firs.gov.ng and obtaining API credentials + full schema.
      Contact: community.nrsmbs.com for developer community access.
      Reference implementation: Zhift Platforms (cs@zhiftplatforms.com).
"""
from __future__ import annotations

from typing import Any

import frappe
import requests
from frappe import _
from frappe.utils import now_datetime

# ── Mandatory once you have credentials ──────────────────────────────────────
_SANDBOX_BASE = "https://api-sandbox.einvoice.firs.gov.ng"  # unconfirmed — update after registration
_PROD_BASE = "https://api.einvoice.firs.gov.ng"             # unconfirmed — update after registration
# ─────────────────────────────────────────────────────────────────────────────

_EINVOICE_SETTINGS_DOCTYPE = "NRS E-Invoice Settings"


class EInvoiceError(Exception):
    pass


class EInvoiceNotConfigured(EInvoiceError):
    pass


def _get_settings():
    # TODO: create NRS E-Invoice Settings single doctype after schema confirmation
    return frappe.get_single(_EINVOICE_SETTINGS_DOCTYPE)


def _get_token(settings) -> str:
    # TODO: replace with actual OAuth token endpoint from FIRSMBS docs
    cached = frappe.cache.get_value("zinye_ng:firsmbs_token")
    if cached:
        return cached

    resp = requests.post(
        f"{_base_url(settings)}/oauth/token",
        json={
            "client_id": settings.client_id,
            "client_secret": settings.get_password("client_secret"),
            "grant_type": "client_credentials",
        },
        timeout=30,
    )
    resp.raise_for_status()
    token = resp.json()["access_token"]
    frappe.cache.set_value("zinye_ng:firsmbs_token", token, expires_in_sec=3600)
    return token


def _base_url(settings) -> str:
    return _PROD_BASE if settings.environment == "Production" else _SANDBOX_BASE


def build_invoice_payload(sales_invoice: str) -> dict[str, Any]:
    """
    Build the UBL BIS Billing 3.0 JSON payload for a Sales Invoice.

    The 55 mandatory fields span 8 categories:
      1. Business identifiers (seller/buyer TIN, RC number)
      2. Invoice details (number, date, type B2B/B2C, currency)
      3. Seller details (name, address, state, LGA, TIN)
      4. Buyer details (name, address, TIN — required for B2B)
      5. Line items (description, qty, unit price, product code)
      6. Tax breakdown (VAT rate/amount, WHT details, tax codes)
      7. Financial totals (subtotal, total VAT, grand total, payment terms)
      8. Validation identifiers (populated by FIRS: IRN, CSID, QR code)

    TODO: Map each ERPNext field to the exact FIRSMBS field name once the
          schema is confirmed from the developer portal. Current mapping is
          based on publicly available UBL BIS Billing 3.0 standard.
    """
    doc = frappe.get_doc("Sales Invoice", sales_invoice)
    company = frappe.get_doc("Company", doc.company)
    customer = frappe.get_doc("Customer", doc.customer)

    seller_tin = frappe.db.get_value("Company", doc.company, "tax_id") or ""
    buyer_tin = frappe.db.get_value("Customer", doc.customer, "tax_id") or ""

    items = []
    total_vat = 0.0
    for row in doc.items:
        vat_amount = 0.0
        for tax in doc.taxes:
            if tax.charge_type == "On Net Total" and "VAT" in (tax.description or ""):
                vat_amount = round(row.net_amount * (tax.rate / 100), 2)
                total_vat += vat_amount

        items.append({
            "lineId": str(row.idx),
            "productCode": row.item_code,
            "description": row.item_name or row.description,
            "quantity": float(row.qty),
            "unitPrice": float(row.rate),
            "netAmount": float(row.net_amount),
            "vatRate": 7.5,
            "vatAmount": vat_amount,
            "lineTotal": float(row.amount),
        })

    payload = {
        # Category 1: Business identifiers
        "sellerTIN": seller_tin,
        "sellerRCNumber": getattr(company, "custom_rc_number", ""),
        "buyerTIN": buyer_tin,
        "buyerRCNumber": frappe.db.get_value("Customer", doc.customer, "custom_rc_number") or "",

        # Category 2: Invoice details
        "invoiceNumber": doc.name,
        "invoiceDate": str(doc.posting_date),
        "invoiceTime": now_datetime().strftime("%H:%M:%S"),
        "invoiceType": "B2B" if buyer_tin else "B2C",
        "currency": doc.currency or "NGN",

        # Category 3: Seller details
        "sellerName": doc.company,
        "sellerAddress": company.company_description or "",
        "sellerState": getattr(company, "custom_state", ""),
        "sellerLGA": getattr(company, "custom_lga", ""),

        # Category 4: Buyer details
        "buyerName": doc.customer_name,
        "buyerAddress": doc.customer_address or "",

        # Category 5: Line items
        "lineItems": items,

        # Category 6: Tax breakdown
        "totalVAT": total_vat,
        "vatRate": 7.5,

        # Category 7: Financial totals
        "netTotal": float(doc.net_total),
        "grandTotal": float(doc.grand_total),
        "paymentTerms": doc.payment_terms_template or "",

        # Category 8: Validation identifiers (FIRS populates these on response)
        "IRN": None,
        "CSID": None,
        "QRCode": None,
    }
    return payload


def submit_invoice(sales_invoice: str) -> dict[str, Any]:
    """
    Submit a Sales Invoice to FIRSMBS for pre-clearance.

    On success, FIRS returns IRN + CSID. We store these on a Nigeria E-Invoice
    record linked to the Sales Invoice.

    TODO: Update the endpoint URL once confirmed from FIRSMBS developer portal.
    """
    settings = _get_settings()
    if not getattr(settings, "enabled", False):
        return {}

    payload = build_invoice_payload(sales_invoice)
    token = _get_token(settings)

    resp = requests.post(
        f"{_base_url(settings)}/api/v1/invoice",  # TODO: confirm endpoint
        json=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-API-Key": settings.api_key,
        },
        timeout=60,
    )

    if not resp.ok:
        _save_einvoice_record(sales_invoice, payload, {}, "Failed", resp.text)
        raise EInvoiceError(f"FIRSMBS submission failed [{resp.status_code}]: {resp.text}")

    result = resp.json()
    irn = result.get("IRN") or result.get("irn")
    csid = result.get("CSID") or result.get("csid")

    _save_einvoice_record(sales_invoice, payload, result, "Submitted", "")

    if irn:
        frappe.db.set_value("Sales Invoice", sales_invoice, {
            "custom_firs_irn": irn,
            "custom_firs_csid": csid,
            "custom_firs_status": "Submitted",
        })

    return result


def check_irn_status(irn: str) -> dict[str, Any]:
    """Poll FIRSMBS for the validation status of an IRN."""
    settings = _get_settings()
    token = _get_token(settings)

    resp = requests.get(
        f"{_base_url(settings)}/api/v1/invoice/{irn}",  # TODO: confirm endpoint
        headers={"Authorization": f"Bearer {token}", "X-API-Key": settings.api_key},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def _save_einvoice_record(
    sales_invoice: str,
    payload: dict,
    response: dict,
    status: str,
    error_message: str,
):
    import json

    if frappe.db.exists("Nigeria E-Invoice", {"sales_invoice": sales_invoice}):
        doc = frappe.get_doc("Nigeria E-Invoice", {"sales_invoice": sales_invoice})
    else:
        doc = frappe.new_doc("Nigeria E-Invoice")
        doc.sales_invoice = sales_invoice

    doc.status = status
    doc.irn = response.get("IRN") or response.get("irn") or ""
    doc.csid = response.get("CSID") or response.get("csid") or ""
    doc.payload = json.dumps(payload, indent=2)
    doc.response = json.dumps(response, indent=2)
    doc.error_message = error_message
    if status == "Submitted":
        doc.submitted_at = now_datetime()

    doc.save(ignore_permissions=True)
    frappe.db.commit()
