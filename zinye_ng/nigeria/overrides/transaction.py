"""
Shared doc event handlers for transactional documents.
Applied to Sales Invoice via doc_events in hooks.py.
"""
from __future__ import annotations

import frappe
from frappe import _


def validate_ng_fields(doc, method=None):
    """
    Ensure Nigeria compliance fields are consistent before saving.
    Sets ng_firs_status to 'Not Required' for new invoices that don't need FIRSMBS.
    """
    if doc.get("ng_firs_status"):
        return  # already set — don't override user/API values

    buyer_tin = frappe.db.get_value("Customer", doc.customer, "ng_tin") or ""
    settings = _get_settings_if_enabled()
    if not settings:
        doc.ng_firs_status = "Not Required"
        return

    if settings.einvoice_b2b_only and not buyer_tin:
        doc.ng_firs_status = "Not Required"
    else:
        doc.ng_firs_status = "Pending"


def before_submit_ng(doc, method=None):
    """
    Validate Nigeria-required fields before Sales Invoice submission.
    Hard-blocks submission if e-Invoice is enabled but company TIN is missing.
    """
    settings = _get_settings_if_enabled()
    if not settings or not settings.einvoice_enabled:
        return

    company_tin = frappe.db.get_value("Company", doc.company, "ng_tin") or settings.tin
    if not company_tin:
        frappe.throw(
            _(
                "Company TIN is required for FIRSMBS e-invoicing. "
                "Set it on the Company record (Nigeria Compliance section) or in "
                "<a href='/app/nigeria-compliance-settings'>Nigeria Compliance Settings</a>."
            )
        )


def _get_settings_if_enabled():
    try:
        settings = frappe.get_cached_doc("Nigeria Compliance Settings")
        return settings if settings.einvoice_enabled else None
    except Exception:
        return None
