"""
NRS FIRSMBS (Merchant Buyer Solution) e-invoicing client.

Pre-clearance model: submit → FIRS validates (≤2h) → IRN + CSID issued.

Portal:   https://einvoice.firs.gov.ng  (register as System Integrator)
Auth:     OAuth 2.0 client_credentials → Bearer token
Format:   JSON over UBL BIS Billing 3.0 (55 mandatory fields, 8 categories)
Security: TLS 1.3, AES-256, ECDSA digital signature (XAdES)

All settings are read from Nigeria Compliance Settings (single DocType).
"""
from __future__ import annotations

import json
from typing import Any

import frappe
import requests
from frappe import _
from frappe.utils import now_datetime, add_to_date

_SETTINGS_DOCTYPE = "Nigeria Compliance Settings"
_TOKEN_CACHE_KEY = "zinye_ng:firsmbs_token"
_MAX_RETRIES = 3


class EInvoiceError(Exception):
    pass


class EInvoiceNotConfigured(EInvoiceError):
    pass


# ── Settings helpers ──────────────────────────────────────────────────────────

def _get_settings():
    return frappe.get_cached_doc(_SETTINGS_DOCTYPE)


def _base_url(settings) -> str:
    if settings.einvoice_environment == "Production":
        return (settings.einvoice_production_url or "https://api.einvoice.firs.gov.ng").rstrip("/")
    return (settings.einvoice_sandbox_url or "https://api-sandbox.einvoice.firs.gov.ng").rstrip("/")


def _get_token(settings) -> str:
    cached = frappe.cache.get_value(_TOKEN_CACHE_KEY)
    if cached:
        return cached

    resp = requests.post(
        f"{_base_url(settings)}/oauth/token",
        json={
            "client_id": settings.einvoice_client_id,
            "client_secret": settings.get_password("einvoice_client_secret"),
            "grant_type": "client_credentials",
        },
        timeout=30,
    )
    if not resp.ok:
        raise EInvoiceError(f"FIRSMBS auth failed [{resp.status_code}]: {resp.text}")

    data = resp.json()
    token = data["access_token"]
    expires_in = int(data.get("expires_in", 3600))
    frappe.cache.set_value(_TOKEN_CACHE_KEY, token, expires_in_sec=expires_in - 60)

    # Record token expiry on the settings doc for visibility
    frappe.db.set_value(
        _SETTINGS_DOCTYPE,
        _SETTINGS_DOCTYPE,
        "einvoice_token_expiry",
        add_to_date(now_datetime(), seconds=expires_in),
    )
    return token


def _headers(settings) -> dict:
    return {
        "Authorization": f"Bearer {_get_token(settings)}",
        "Content-Type": "application/json",
        "X-API-Key": settings.get_password("einvoice_api_key"),
    }


# ── Payload builder ──────────────────────────────────────────────────────────

def build_invoice_payload(sales_invoice: str) -> dict[str, Any]:
    """
    Build UBL BIS Billing 3.0 JSON payload for a Sales Invoice.

    55 mandatory fields across 8 categories:
      1. Business identifiers (seller/buyer TIN, RC number)
      2. Invoice details (number, date, type, currency)
      3. Seller details (name, address, state)
      4. Buyer details (name, address, TIN)
      5. Line items (code, qty, price, tax)
      6. Tax breakdown (VAT rate/amount)
      7. Financial totals (net, VAT, grand total)
      8. Validation identifiers (IRN, CSID — populated by FIRS in response)
    """
    doc = frappe.get_doc("Sales Invoice", sales_invoice)
    company = frappe.get_doc("Company", doc.company)
    settings = _get_settings()

    from zinye_ng.nigeria.constants.invoice_types import get_invoice_type_code, get_invoice_type_label
    from zinye_ng.nigeria.constants.payment_means import get_payment_means_code
    from zinye_ng.nigeria.constants.tax_categories import get_tax_category_code
    from zinye_ng.nigeria.constants.states import get_state_code
    from zinye_ng.nigeria.firs.resources import get_quantity_code

    seller_tin = (
        frappe.db.get_value("Company", doc.company, "ng_tin")
        or settings.tin
        or ""
    )
    buyer_tin = frappe.db.get_value("Customer", doc.customer, "ng_tin") or ""
    is_return = bool(doc.get("is_return"))
    is_debit_note = bool(doc.get("is_debit_note"))
    invoice_type_code = get_invoice_type_code("Sales Invoice", is_return, is_debit_note)
    invoice_type_label = get_invoice_type_label(invoice_type_code)
    # B2B/B2C is a separate buyer classification, distinct from the UBL invoice type code
    buyer_type = "B2B" if buyer_tin else "B2C"

    seller_state_name = (
        frappe.db.get_value("Company", doc.company, "ng_registered_state")
        or settings.registered_state
        or ""
    )
    seller_state_code = get_state_code(seller_state_name)

    # Payment means: read from Sales Invoice custom field, fallback to mode of payment
    payment_mode = doc.get("ng_payment_means") or doc.get("mode_of_payment") or ""
    payment_means_code = get_payment_means_code(payment_mode)

    vat_rate = settings.einvoice_default_vat_rate or 7.5
    tax_category_code = get_tax_category_code(vat_rate)

    items = []
    total_vat = 0.0

    for row in doc.items:
        line_vat = round(float(row.net_amount) * (vat_rate / 100), 2)
        total_vat += line_vat
        # HS code / service code from item custom fields (populated via sync_hs_codes)
        hs_code = frappe.db.get_value("Item", row.item_code, "ng_hs_code") or ""
        service_code = frappe.db.get_value("Item", row.item_code, "ng_service_code") or ""
        items.append({
            "lineId": str(row.idx),
            "productCode": hs_code or row.item_code,
            "serviceCode": service_code,
            "description": row.item_name or row.description or "",
            "quantity": float(row.qty),
            "quantityCode": get_quantity_code(row.uom or ""),
            "unitPrice": float(row.rate),
            "netAmount": float(row.net_amount),
            "taxCategoryCode": tax_category_code,
            "vatRate": vat_rate,
            "vatAmount": line_vat,
            "lineTotal": float(row.amount),
        })

    return {
        # Category 1: Business identifiers
        "sellerTIN": seller_tin,
        "sellerRCNumber": frappe.db.get_value("Company", doc.company, "ng_rc_number") or settings.rc_number or "",
        "buyerTIN": buyer_tin,
        "buyerRCNumber": frappe.db.get_value("Customer", doc.customer, "ng_rc_number") or "",

        # Category 2: Invoice details
        "invoiceNumber": doc.name,
        "invoiceDate": str(doc.posting_date),
        "invoiceTime": now_datetime().strftime("%H:%M:%S"),
        "invoiceTypeCode": invoice_type_code,       # UBL UN/ECE 1001 (e.g. "381")
        "invoiceTypeDescription": invoice_type_label,  # e.g. "Commercial Invoice"
        "buyerType": buyer_type,                    # "B2B" or "B2C" — separate from UBL type
        "currency": doc.currency or "NGN",
        "paymentMeansCode": payment_means_code,     # UBL UN/ECE 4461

        # Category 3: Seller details
        "sellerName": doc.company,
        "sellerAddress": company.company_description or "",
        "sellerState": seller_state_name,
        "sellerStateCode": seller_state_code,       # ISO 3166-2 (e.g. "NG-LA")
        "sellerVATNumber": settings.vat_registration_number or "",

        # Category 4: Buyer details
        "buyerName": doc.customer_name,
        "buyerAddress": doc.customer_address or "",

        # Category 5: Line items (with HS/service codes, UOM codes, tax category)
        "lineItems": items,

        # Category 6: Tax breakdown
        "totalVAT": round(total_vat, 2),
        "vatRate": vat_rate,
        "taxCategoryCode": tax_category_code,

        # Category 7: Financial totals
        "netTotal": float(doc.net_total),
        "grandTotal": float(doc.grand_total),
        "paymentTerms": doc.payment_terms_template or "",

        # Category 8: Populated by FIRS on response
        "IRN": None,
        "CSID": None,
        "QRCode": None,
    }


# ── Submission ────────────────────────────────────────────────────────────────

def submit_invoice_enqueued(sales_invoice: str) -> dict:
    """
    Enqueue FIRSMBS submission as a background job.
    Use this from on_submit hooks and manual form buttons.
    """
    settings = _get_settings()
    if not settings.einvoice_enabled:
        return {}

    frappe.enqueue(
        "zinye_ng.nigeria.firs.einvoice.submit_invoice",
        queue="default",
        timeout=120,
        enqueue_after_commit=True,
        sales_invoice=sales_invoice,
    )
    return {"queued": True}


def submit_invoice(sales_invoice: str) -> dict[str, Any]:
    """
    Submit a Sales Invoice to FIRSMBS (runs in background queue).
    Creates or updates a Nigeria E-Invoice record with the result.
    """
    settings = _get_settings()
    if not settings.einvoice_enabled:
        return {}

    einvoice_doc = _get_or_create_einvoice(sales_invoice)
    if einvoice_doc.status in ("Cleared",):
        return {}  # already finalized

    if einvoice_doc.retry_count >= (einvoice_doc.max_retries or _MAX_RETRIES):
        frappe.log_error(
            f"Max retries reached for Sales Invoice {sales_invoice}",
            "FIRSMBS e-Invoice",
        )
        return {}

    # Respect B2B-only setting
    buyer_tin = frappe.db.get_value("Sales Invoice", sales_invoice, "ng_firs_irn")
    actual_buyer_tin = frappe.db.get_value(
        "Customer",
        frappe.db.get_value("Sales Invoice", sales_invoice, "customer"),
        "ng_tin",
    ) or ""
    if settings.einvoice_b2b_only and not actual_buyer_tin:
        return {}

    try:
        payload = build_invoice_payload(sales_invoice)
        resp = requests.post(
            f"{_base_url(settings)}/api/v1/invoice",
            json=payload,
            headers=_headers(settings),
            timeout=60,
        )

        if resp.status_code in (400, 422):
            # Validation error — no point retrying, mark as Failed permanently
            _update_einvoice(einvoice_doc, payload, {}, "Failed", resp.text)
            raise EInvoiceError(f"FIRSMBS validation error [{resp.status_code}]: {resp.text}")

        if not resp.ok:
            # Server/network error — schedule retry
            _update_einvoice(einvoice_doc, payload, {}, "Auto-Retry", resp.text)
            frappe.db.set_value(
                "Nigeria Compliance Settings",
                "Nigeria Compliance Settings",
                "is_retry_einvoice_pending",
                1,
            )
            frappe.db.commit()
            return {}

        result = resp.json()
        irn = result.get("IRN") or result.get("irn") or ""
        csid = result.get("CSID") or result.get("csid") or ""
        qr_data = result.get("QRCode") or result.get("qrCode") or ""

        _update_einvoice(einvoice_doc, payload, result, "Submitted", "", irn, csid, qr_data)

        frappe.db.set_value("Sales Invoice", sales_invoice, {
            "ng_firs_irn": irn,
            "ng_firs_csid": csid,
            "ng_firs_status": "Submitted",
        })
        return result

    except EInvoiceError:
        raise
    except Exception as e:
        _update_einvoice(einvoice_doc, {}, {}, "Auto-Retry", str(e))
        frappe.db.set_value(
            "Nigeria Compliance Settings",
            "Nigeria Compliance Settings",
            "is_retry_einvoice_pending",
            1,
        )
        frappe.log_error(frappe.get_traceback(), "FIRSMBS e-Invoice Submission")
        return {}


def cancel_invoice(sales_invoice: str) -> dict[str, Any]:
    """Cancel an e-Invoice at FIRS (called on Sales Invoice cancellation)."""
    einvoice_doc = frappe.db.get_value(
        "Nigeria E-Invoice", {"sales_invoice": sales_invoice}, "name"
    )
    if not einvoice_doc:
        return {}

    doc = frappe.get_doc("Nigeria E-Invoice", einvoice_doc)
    if not doc.irn:
        frappe.db.set_value("Nigeria E-Invoice", doc.name, "status", "Cancelled")
        return {}

    settings = _get_settings()
    try:
        resp = requests.post(
            f"{_base_url(settings)}/api/v1/invoice/cancel",
            json={"IRN": doc.irn},
            headers=_headers(settings),
            timeout=30,
        )
        if resp.ok:
            frappe.db.set_value("Nigeria E-Invoice", doc.name, "status", "Cancelled")
            frappe.db.set_value("Sales Invoice", sales_invoice, "ng_firs_status", "Cancelled")
        return resp.json() if resp.ok else {}
    except Exception as e:
        frappe.log_error(str(e), "FIRSMBS e-Invoice Cancel")
        return {}


def check_irn_status(irn: str) -> dict[str, Any]:
    """Poll FIRSMBS for the current validation status of an IRN."""
    settings = _get_settings()
    resp = requests.get(
        f"{_base_url(settings)}/api/v1/invoice/{irn}",
        headers=_headers(settings),
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


# ── Internal helpers ──────────────────────────────────────────────────────────

def _get_or_create_einvoice(sales_invoice: str):
    name = frappe.db.get_value("Nigeria E-Invoice", {"sales_invoice": sales_invoice}, "name")
    if name:
        return frappe.get_doc("Nigeria E-Invoice", name)

    from zinye_ng.nigeria.constants.invoice_types import get_invoice_type_code

    inv = frappe.get_doc("Sales Invoice", sales_invoice)
    buyer_tin = frappe.db.get_value("Customer", inv.customer, "ng_tin") or ""
    type_code = get_invoice_type_code(
        "Sales Invoice",
        bool(inv.get("is_return")),
        bool(inv.get("is_debit_note")),
    )
    doc = frappe.new_doc("Nigeria E-Invoice")
    doc.sales_invoice = sales_invoice
    doc.status = "Pending"
    doc.invoice_type = type_code  # UBL code e.g. "381"
    doc.invoice_number = sales_invoice
    doc.invoice_date = inv.posting_date
    doc.seller_tin = frappe.db.get_value("Company", inv.company, "ng_tin") or ""
    doc.buyer_tin = buyer_tin
    doc.total_excluding_vat = inv.net_total
    doc.grand_total = inv.grand_total
    doc.max_retries = _MAX_RETRIES
    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    return doc


def _update_einvoice(doc, payload: dict, response: dict, status: str, error: str,
                     irn: str = "", csid: str = "", qr_data: str = ""):
    doc.status = status
    doc.irn = irn
    doc.csid = csid
    doc.payload = json.dumps(payload, indent=2, default=str)
    doc.response = json.dumps(response, indent=2, default=str)
    doc.error_message = error
    doc.retry_count = (doc.retry_count or 0) + (1 if status == "Failed" else 0)
    doc.last_retry_at = now_datetime() if status == "Failed" else doc.last_retry_at

    if status == "Submitted":
        doc.submitted_at = now_datetime()
        doc.vat_amount = response.get("totalVAT") or response.get("total_vat") or 0
    if status == "Cleared":
        doc.cleared_at = now_datetime()

    if qr_data:
        _attach_qr_code(doc, qr_data)

    doc.save(ignore_permissions=True)
    frappe.db.commit()


def _attach_qr_code(einvoice_doc, qr_data: str):
    """Generate a QR code PNG from qr_data and attach it to the Nigeria E-Invoice."""
    try:
        import qrcode
        import io
        import base64

        img = qrcode.make(qr_data)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)

        file_doc = frappe.get_doc({
            "doctype": "File",
            "file_name": f"qr_{einvoice_doc.name}.png",
            "content": base64.b64encode(buf.read()).decode(),
            "is_private": 0,
            "attached_to_doctype": "Nigeria E-Invoice",
            "attached_to_name": einvoice_doc.name,
            "attached_to_field": "qr_code",
        })
        file_doc.insert(ignore_permissions=True)
        einvoice_doc.qr_code = file_doc.file_url
    except ImportError:
        # qrcode package not installed — store raw data instead
        einvoice_doc.qr_code = qr_data
    except Exception as e:
        frappe.log_error(str(e), "FIRSMBS QR Code Generation")
