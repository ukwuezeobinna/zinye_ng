"""
Doc event handlers wired up in hooks.py for FIRS integrations.

Sales Invoice on_submit  → FIRSMBS pre-clearance (B2B) or ATRS flag (B2C)
Sales Invoice on_cancel  → update Nigeria E-Invoice record status
POS Invoice on_submit    → FIRS ATRS real-time receipt (B2C)

All heavy work is enqueued — the event handler returns immediately so the
user is not blocked by a slow FIRS API call.
"""
from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import now_datetime


def on_sales_invoice_submit(doc, method=None):
    """Submit B2B invoice to FIRSMBS; flag B2C invoices for ATRS."""
    buyer_tin = frappe.db.get_value("Customer", doc.customer, "custom_ng_tin") or ""
    if buyer_tin:
        # B2B — must go through FIRSMBS pre-clearance
        frappe.enqueue(
            "zinye_ng.nigeria.einvoice.submit_invoice",
            queue="long",
            enqueue_after_commit=True,
            sales_invoice=doc.name,
        )
    # B2C receipts are handled via POS Invoice, not Sales Invoice


def on_sales_invoice_cancel(doc, method=None):
    """Mark any linked Nigeria E-Invoice as cancelled."""
    if frappe.db.exists("Nigeria E-Invoice", {"sales_invoice": doc.name}):
        frappe.db.set_value(
            "Nigeria E-Invoice",
            {"sales_invoice": doc.name},
            "status",
            "Cancelled",
        )
        frappe.db.commit()


def on_pos_invoice_submit(doc, method=None):
    """Submit B2C POS receipt to FIRS ATRS in background."""
    settings = frappe.get_single("FIRS ATRS Settings")
    if not settings.enabled:
        return

    frappe.enqueue(
        "zinye_ng.nigeria.atrs.submit_pos_invoice_to_atrs",
        queue="short",
        enqueue_after_commit=True,
        pos_invoice=doc.name,
    )
