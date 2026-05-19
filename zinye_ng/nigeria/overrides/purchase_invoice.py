"""
Mixin added to Purchase Invoice via extend_doctype_class (Frappe v16).

Adds Nigeria WHT methods callable from the form:
  - apply_wht: manually calculate and apply WHT to this invoice
"""
from __future__ import annotations

import frappe
from frappe import _


class NigeriaPurchaseInvoiceMixin:
    @frappe.whitelist()
    def apply_wht(self) -> dict:
        """
        Calculate and apply Withholding Tax to this Purchase Invoice.
        Called from the Nigeria menu button on the Purchase Invoice form.
        """
        from zinye_ng.nigeria.tax.wht import calculate_wht, apply_wht_to_invoice

        if self.docstatus != 0:
            frappe.throw(_("WHT can only be applied to draft invoices."))

        wht_data = calculate_wht(self)
        if not wht_data:
            frappe.msgprint(_("No WHT applicable for this supplier/invoice."))
            return {}

        apply_wht_to_invoice(self, wht_data)
        return wht_data

    @frappe.whitelist()
    def get_wht_rate(self) -> dict:
        """Return the WHT rate for this supplier based on their WHT category."""
        from zinye_ng.nigeria.tax.wht import get_supplier_wht_rate

        rate = get_supplier_wht_rate(self.supplier)
        return {"rate": rate}
