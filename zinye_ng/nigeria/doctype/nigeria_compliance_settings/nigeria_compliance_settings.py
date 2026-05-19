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
        # Flush ATRS token cache when ATRS credentials change
        if self.has_value_changed("atrs_client_secret") or self.has_value_changed("atrs_password"):
            frappe.cache.delete_value("zinye_ng:atrs_token")
        # No token cache for FIRS e-Invoice — auth is x-api-key/x-api-secret headers, always fresh

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
            frappe.throw(_("VAT Registration Number is required when FIRS e-Invoicing is enabled."))
        if self.atrs_enabled and not self.atrs_vat_number:
            frappe.throw(_("ATRS VAT Number is required when FIRS ATRS is enabled."))

    @frappe.whitelist()
    def test_einvoice_connection(self) -> dict:
        """
        Test FIRS e-Invoice API connectivity.
        Auth is x-api-key + x-api-secret — we verify by calling GET /api/v1/invoice/resources/countries.
        """
        import requests
        from zinye_ng.nigeria.firs.einvoice import _base_url, _headers

        if not self.get_password("einvoice_api_key"):
            frappe.throw(_("API Key is required to test the FIRS connection."))

        try:
            resp = requests.get(
                f"{_base_url(self)}/api/v1/invoice/resources/countries",
                headers=_headers(self),
                timeout=15,
            )
            if resp.ok:
                return {"status": "success", "message": _("FIRS e-Invoice connection successful.")}
            frappe.throw(_("FIRS returned [{0}]: {1}").format(resp.status_code, resp.text[:200]))
        except Exception as e:
            frappe.throw(_("FIRS e-Invoice connection failed: {0}").format(str(e)))

    @frappe.whitelist()
    def test_atrs_connection(self) -> dict:
        """Validate ATRS credentials. Called from form button."""
        from zinye_ng.nigeria.firs.atrs import _get_token

        if not self.atrs_client_id:
            frappe.throw(_("Client ID is required to test the ATRS connection."))

        try:
            frappe.cache.delete_value("zinye_ng:atrs_token")
            token = _get_token(self)
            if token:
                return {"status": "success", "message": _("ATRS connection successful.")}
        except Exception as e:
            frappe.throw(_("ATRS connection failed: {0}").format(str(e)))
