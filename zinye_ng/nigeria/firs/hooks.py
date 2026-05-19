"""
Doc event handlers for FIRS integrations.
These are the entry points registered in hooks.py doc_events.
"""
from __future__ import annotations

import frappe
from frappe import _


def on_sales_invoice_submit(doc, method=None):
    """Enqueue FIRSMBS submission when a Sales Invoice is submitted."""
    settings = _settings()
    if not settings or not settings.einvoice_enabled or not settings.einvoice_auto_submit:
        return

    from zinye_ng.nigeria.firs.einvoice import submit_invoice_enqueued
    submit_invoice_enqueued(doc.name)


def before_sales_invoice_cancel(doc, method=None):
    """
    Prevent cancellation if the invoice has been submitted to (or cleared by) FIRS.
    Mirrors india_compliance's before_cancel pattern.
    """
    settings = _settings()
    if not settings or not settings.einvoice_enabled:
        return

    einvoice = frappe.db.get_value(
        "Nigeria E-Invoice",
        {"sales_invoice": doc.name},
        ["status", "irn"],
        as_dict=True,
    )
    if not einvoice:
        return

    if einvoice.status == "Cleared":
        frappe.throw(
            _(
                "Sales Invoice {0} has been cleared by FIRS (IRN: {1}). "
                "Cancel the e-Invoice at FIRS before cancelling this invoice."
            ).format(doc.name, einvoice.irn)
        )

    if einvoice.status == "Submitted" and einvoice.irn:
        frappe.throw(
            _(
                "Sales Invoice {0} has been submitted to FIRS (IRN: {1}). "
                "Cancel the e-Invoice at FIRS before cancelling this invoice, "
                "or use the Nigeria → Cancel e-Invoice action."
            ).format(doc.name, einvoice.irn)
        )


def on_sales_invoice_cancel(doc, method=None):
    """Cancel e-Invoice at FIRS when Sales Invoice is cancelled."""
    settings = _settings()
    if not settings or not settings.einvoice_enabled:
        return

    from zinye_ng.nigeria.firs.einvoice import cancel_invoice
    try:
        cancel_invoice(doc.name)
    except Exception as e:
        frappe.log_error(str(e), "FIRSMBS e-Invoice Cancel")


def on_pos_invoice_submit(doc, method=None):
    """Enqueue ATRS submission when a POS Invoice is submitted."""
    settings = _settings()
    if not settings or not settings.atrs_enabled or not settings.atrs_auto_submit:
        return

    frappe.enqueue(
        "zinye_ng.nigeria.firs.atrs.submit_pos_invoice_to_atrs",
        queue="default",
        timeout=60,
        enqueue_after_commit=True,
        pos_invoice=doc.name,
    )


def _settings():
    try:
        return frappe.get_cached_doc("Nigeria Compliance Settings")
    except Exception:
        return None
