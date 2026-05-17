"""
FIRSMBS e-invoicing background job.

poll_pending_einvoices: hourly — checks IRN status for Submitted e-invoices
and updates them to Cleared when FIRS validates them.
"""
from __future__ import annotations

import frappe
from frappe.utils import now_datetime

from zinye_ng.nigeria.einvoice import check_irn_status, EInvoiceError


def poll_pending_einvoices():
    """
    Poll FIRSMBS for the validation status of Submitted e-invoices.
    Called from: scheduler_events.hourly in hooks.py.

    The FIRSMBS pre-clearance model gives FIRS up to 2 hours to validate and
    issue a final IRN status. This job runs every hour to check and update.
    """
    pending = frappe.get_all(
        "Nigeria E-Invoice",
        filters={"status": "Submitted"},
        fields=["name", "irn", "sales_invoice"],
    )

    for record in pending:
        if not record.irn:
            continue
        try:
            result = check_irn_status(record.irn)
            status = result.get("status") or result.get("Status")
            if status and status.lower() in ("cleared", "valid", "approved"):
                frappe.db.set_value("Nigeria E-Invoice", record.name, "status", "Cleared")
                frappe.db.set_value("Sales Invoice", record.sales_invoice, "ng_firs_status", "Cleared")
        except EInvoiceError as e:
            frappe.log_error(
                f"IRN poll failed for {record.irn} (Sales Invoice {record.sales_invoice}): {e}",
                "FIRSMBS IRN Poll",
            )

    if pending:
        frappe.db.commit()
