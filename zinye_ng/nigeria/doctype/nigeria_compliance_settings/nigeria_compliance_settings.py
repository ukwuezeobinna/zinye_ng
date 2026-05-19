from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document


class NigeriaComplianceSettings(Document):
    def validate(self):
        self._sync_tin_from_company()
        self._validate_tin()
        self._validate_vat_number()

    def on_update(self):
        # Clear cached tokens when credentials change — force re-auth on next API call.
        if self.has_value_changed("einvoice_client_secret") or self.has_value_changed("einvoice_api_key"):
            frappe.cache.delete_value("zinye_ng:firsmbs_token")
        if self.has_value_changed("atrs_client_secret") or self.has_value_changed("atrs_password"):
            frappe.cache.delete_value("zinye_ng:atrs_token")

    def _sync_tin_from_company(self):
        if self.company and not self.tin:
            company_tin = frappe.db.get_value("Company", self.company, "ng_tin")
            if company_tin:
                self.tin = company_tin

        if self.company and not self.vat_registration_number:
            vat = frappe.db.get_value("Company", self.company, "ng_vat_number")
            if vat:
                self.vat_registration_number = vat

        if self.company and not self.rc_number:
            rc = frappe.db.get_value("Company", self.company, "ng_rc_number")
            if rc:
                self.rc_number = rc

    def _validate_tin(self):
        if self.tin and not self.tin.replace("-", "").isdigit():
            frappe.throw(_("TIN must be numeric (12 digits). Got: {0}").format(self.tin))

    def _validate_vat_number(self):
        if self.einvoice_enabled and not self.vat_registration_number:
            frappe.throw(_("VAT Registration Number is required when FIRSMBS e-Invoicing is enabled."))
        if self.atrs_enabled and not self.atrs_vat_number:
            frappe.throw(_("ATRS VAT Number is required when FIRS ATRS is enabled."))

    @frappe.whitelist()
    def test_einvoice_connection(self) -> dict:
        """Validate FIRSMBS credentials by fetching an auth token. Called from form button."""
        from zinye_ng.nigeria.firs.einvoice import _get_token, _base_url

        if not self.einvoice_client_id:
            frappe.throw(_("Client ID is required to test the FIRSMBS connection."))

        try:
            frappe.cache.delete_value("zinye_ng:firsmbs_token")
            token = _get_token(self)
            if token:
                return {"status": "success", "message": _("FIRSMBS connection successful.")}
        except Exception as e:
            frappe.throw(_("FIRSMBS connection failed: {0}").format(str(e)))

    @frappe.whitelist()
    def test_atrs_connection(self) -> dict:
        """Validate ATRS credentials by fetching an auth token. Called from form button."""
        from zinye_ng.nigeria.atrs import _get_token

        if not self.atrs_client_id:
            frappe.throw(_("Client ID is required to test the ATRS connection."))

        try:
            frappe.cache.delete_value("zinye_ng:atrs_token")
            token = _get_token(self)
            if token:
                return {"status": "success", "message": _("ATRS connection successful.")}
        except Exception as e:
            frappe.throw(_("ATRS connection failed: {0}").format(str(e)))
