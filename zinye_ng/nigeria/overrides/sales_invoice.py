"""
Mixin added to Sales Invoice via extend_doctype_class (Frappe v16).

Adds Nigeria-specific methods callable from the form:
  - generate_einvoice: manually trigger FIRSMBS submission
  - cancel_einvoice: cancel at FIRS

Lifecycle hooks (on_submit, on_cancel) remain in doc_events in hooks.py.
"""
from __future__ import annotations

import frappe
from frappe import _


class NigeriaSalesInvoiceMixin:
    @frappe.whitelist()
    def generate_einvoice(self) -> dict:
        """
        Manually submit this Sales Invoice to FIRSMBS for pre-clearance.
        Called from the Nigeria menu button on the Sales Invoice form.
        """
        from zinye_ng.nigeria.firs.einvoice import submit_invoice_enqueued

        if self.docstatus != 1:
            frappe.throw(_("Only submitted Sales Invoices can be sent to FIRSMBS."))

        existing = frappe.db.get_value(
            "Nigeria E-Invoice", {"sales_invoice": self.name}, ["name", "status"], as_dict=True
        )
        if existing and existing.status in ("Submitted", "Cleared"):
            frappe.throw(
                _("This invoice already has an e-Invoice with status: {0}").format(existing.status)
            )

        return submit_invoice_enqueued(self.name)

    @frappe.whitelist()
    def cancel_einvoice(self) -> dict:
        """Cancel the e-Invoice at FIRS (called on Sales Invoice cancellation)."""
        from zinye_ng.nigeria.firs.einvoice import cancel_invoice

        return cancel_invoice(self.name)

    @frappe.whitelist()
    def get_einvoice_status(self) -> dict:
        """Return the current Nigeria E-Invoice status for this Sales Invoice."""
        record = frappe.db.get_value(
            "Nigeria E-Invoice",
            {"sales_invoice": self.name},
            ["name", "status", "irn", "csid", "submitted_at", "cleared_at"],
            as_dict=True,
        )
        return record or {}
