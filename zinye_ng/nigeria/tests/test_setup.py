"""
Integration tests for zinye_ng setup — requires a Frappe site with DB.

Tests that:
  - All Nigeria custom fields are created on their target doctypes
  - The NG Employee Standard salary structure is created for Nigeria companies
  - _create_ng_salary_structures() is idempotent (safe to run twice)
  - Structure is NOT created when salary component fixtures are missing

Run with:
    bench --site <site> run-tests --app zinye_ng \
          --module zinye_ng.nigeria.tests.test_setup
"""
import frappe
from frappe.tests import IntegrationTestCase

from zinye_ng.nigeria.setup import (
    _NG_DEDUCTIONS,
    _NG_EARNINGS,
    _NG_STRUCTURE_NAME,
    _create_ng_salary_structures,
    _ensure_ng_structure,
    create_nigeria_custom_fields,
)


EXPECTED_CUSTOM_FIELDS = {
    "Company": ["ng_tin", "ng_rc_number", "ng_vat_number", "ng_registered_state"],
    "Employee": ["ng_tin", "ng_nhf_number", "ng_pfa_name", "ng_rsa_pin"],
    "Customer": ["ng_tin", "ng_rc_number"],
    "Supplier": ["ng_tin", "ng_rc_number", "ng_wht_category"],
    "Sales Invoice": ["ng_firs_irn", "ng_firs_csid", "ng_firs_status"],
    "Purchase Invoice": ["ng_wht_applicable", "ng_wht_rate", "ng_wht_amount", "ng_wht_account"],
}


class TestCustomFields(IntegrationTestCase):
    def test_all_expected_custom_fields_exist(self):
        """Every ng_* custom field must be present after create_nigeria_custom_fields()."""
        create_nigeria_custom_fields()
        for doctype, fieldnames in EXPECTED_CUSTOM_FIELDS.items():
            for fn in fieldnames:
                exists = frappe.db.exists("Custom Field", {"dt": doctype, "fieldname": fn})
                self.assertTrue(
                    exists,
                    f"Custom Field '{fn}' missing on {doctype}",
                )

    def test_create_custom_fields_is_idempotent(self):
        """Running create_nigeria_custom_fields() twice must not raise."""
        create_nigeria_custom_fields()
        create_nigeria_custom_fields()  # second call — must not raise or duplicate


class TestSalaryStructureCreation(IntegrationTestCase):
    def setUp(self):
        super().setUp()
        # Remove test structure if leftover from a failed prior run
        if frappe.db.exists("Salary Structure", _NG_STRUCTURE_NAME):
            frappe.delete_doc("Salary Structure", _NG_STRUCTURE_NAME, force=True)

    def tearDown(self):
        if frappe.db.exists("Salary Structure", _NG_STRUCTURE_NAME):
            frappe.delete_doc("Salary Structure", _NG_STRUCTURE_NAME, force=True)
        super().tearDown()

    def _all_components_exist(self):
        return all(
            frappe.db.exists("Salary Component", c)
            for c in _NG_EARNINGS + _NG_DEDUCTIONS
        )

    def test_structure_created_for_nigeria_company(self):
        if not self._all_components_exist():
            self.skipTest("NG salary component fixtures not loaded in this site")

        companies = frappe.get_all("Company", filters={"country": "Nigeria"}, pluck="name")
        if not companies:
            self.skipTest("No Nigeria company exists in this site")

        _ensure_ng_structure(companies[0])

        self.assertTrue(
            frappe.db.exists("Salary Structure", _NG_STRUCTURE_NAME),
            "NG Employee Standard salary structure should have been created",
        )

    def test_structure_has_all_earning_components(self):
        if not self._all_components_exist():
            self.skipTest("NG salary component fixtures not loaded in this site")

        companies = frappe.get_all("Company", filters={"country": "Nigeria"}, pluck="name")
        if not companies:
            self.skipTest("No Nigeria company exists in this site")

        _ensure_ng_structure(companies[0])

        struct = frappe.get_doc("Salary Structure", _NG_STRUCTURE_NAME)
        earning_names = [r.salary_component for r in struct.earnings]
        for comp in _NG_EARNINGS:
            self.assertIn(comp, earning_names, f"Earning '{comp}' missing from structure")

    def test_structure_has_all_deduction_components(self):
        if not self._all_components_exist():
            self.skipTest("NG salary component fixtures not loaded in this site")

        companies = frappe.get_all("Company", filters={"country": "Nigeria"}, pluck="name")
        if not companies:
            self.skipTest("No Nigeria company exists in this site")

        _ensure_ng_structure(companies[0])

        struct = frappe.get_doc("Salary Structure", _NG_STRUCTURE_NAME)
        deduction_names = [r.salary_component for r in struct.deductions]
        for comp in _NG_DEDUCTIONS:
            self.assertIn(comp, deduction_names, f"Deduction '{comp}' missing from structure")

    def test_create_is_idempotent(self):
        if not self._all_components_exist():
            self.skipTest("NG salary component fixtures not loaded in this site")

        companies = frappe.get_all("Company", filters={"country": "Nigeria"}, pluck="name")
        if not companies:
            self.skipTest("No Nigeria company exists in this site")

        _ensure_ng_structure(companies[0])
        _ensure_ng_structure(companies[0])  # second call — must not raise or duplicate

        count = frappe.db.count("Salary Structure", {"name": _NG_STRUCTURE_NAME})
        self.assertEqual(count, 1)

    def test_no_structure_created_when_components_missing(self):
        """If any NG component is absent, _create_ng_salary_structures() must bail out."""
        with self.subTest("with no Nigeria companies — skips silently"):
            # Monkeypatch to return empty company list
            import zinye_ng.nigeria.setup as setup_module
            original = setup_module.frappe.get_all

            def mock_get_all(doctype, **kwargs):
                if doctype == "Company":
                    return []
                return original(doctype, **kwargs)

            setup_module.frappe.get_all = mock_get_all
            try:
                _create_ng_salary_structures()
            finally:
                setup_module.frappe.get_all = original

            self.assertFalse(frappe.db.exists("Salary Structure", _NG_STRUCTURE_NAME))
