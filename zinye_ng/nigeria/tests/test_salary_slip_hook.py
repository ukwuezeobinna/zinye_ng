"""
Unit tests for the Salary Slip validate hook.

Mocks the Frappe document to avoid a DB connection. Verifies that:
  - The NG - PAYE Tax deduction row is overwritten with the correct amount
  - Minimum-wage employees get PAYE = 0
  - Missing PAYE row is a no-op (doesn't crash)
  - s.30 deduction amounts are correctly collected from the slip
"""
from unittest.mock import MagicMock, patch

from frappe.tests import UnitTestCase

from zinye_ng.nigeria.payroll.salary_slip import on_validate, _collect_deductions, _find_paye_row


def _make_row(salary_component, amount=0.0):
    row = MagicMock()
    row.salary_component = salary_component
    row.amount = amount
    row.default_amount = amount
    return row


def _make_slip(gross_pay, deduction_rows):
    doc = MagicMock()
    doc.gross_pay = gross_pay
    doc.employee_name = "Test Employee"
    doc.get.side_effect = lambda key, default=None: (
        deduction_rows if key == "deductions" else default
    )
    return doc


class TestFindPayeRow(UnitTestCase):
    def test_finds_paye_row(self):
        paye = _make_row("NG - PAYE Tax", 0.0)
        pension = _make_row("NG - Pension Employee", 8_000.0)
        doc = _make_slip(100_000, [pension, paye])
        self.assertIs(_find_paye_row(doc), paye)

    def test_returns_none_when_no_paye_row(self):
        doc = _make_slip(100_000, [_make_row("NG - Pension Employee", 8_000.0)])
        self.assertIsNone(_find_paye_row(doc))

    def test_returns_none_on_empty_deductions(self):
        doc = _make_slip(100_000, [])
        self.assertIsNone(_find_paye_row(doc))


class TestCollectDeductions(UnitTestCase):
    def test_collects_pension_nhf_nhis(self):
        rows = [
            _make_row("NG - Pension Employee", 8_000.0),
            _make_row("NG - NHF", 2_500.0),
            _make_row("NG - NHIS", 5_000.0),
            _make_row("NG - PAYE Tax", 0.0),        # not a s.30 input
            _make_row("NG - Basic Salary", 100_000.0),  # earning, ignored
        ]
        doc = _make_slip(115_500, rows)
        result = _collect_deductions(doc)
        self.assertAlmostEqual(result["monthly_pension_employee"], 8_000.0)
        self.assertAlmostEqual(result["monthly_nhf"], 2_500.0)
        self.assertAlmostEqual(result["monthly_nhis"], 5_000.0)

    def test_missing_deductions_default_to_zero(self):
        doc = _make_slip(100_000, [])
        result = _collect_deductions(doc)
        self.assertEqual(result["monthly_pension_employee"], 0.0)
        self.assertEqual(result["monthly_nhf"], 0.0)
        self.assertEqual(result["monthly_nhis"], 0.0)


class TestOnValidatePAYEOverwrite(UnitTestCase):
    def test_paye_row_updated_to_computed_amount(self):
        # ₦100,000/month gross, no deductions
        # Annual = ₦1,200,000 → band calc: 400k @ 15% = ₦60,000 → monthly ₦5,000
        paye_row = _make_row("NG - PAYE Tax", 0.0)
        doc = _make_slip(100_000, [paye_row])

        with patch("zinye_ng.nigeria.payroll.salary_slip.frappe"):
            on_validate(doc)

        self.assertAlmostEqual(paye_row.amount, 5_000.0, places=2)
        self.assertAlmostEqual(paye_row.default_amount, 5_000.0, places=2)

    def test_paye_zero_for_minimum_wage_employee(self):
        # ₦70,000/month = ₦840,000/year = minimum wage → exempt
        paye_row = _make_row("NG - PAYE Tax", 9_999.0)
        doc = _make_slip(70_000, [paye_row])
        doc.employee_name = "Ade Musa"

        with patch("zinye_ng.nigeria.payroll.salary_slip.frappe") as mock_frappe:
            on_validate(doc)

        self.assertEqual(paye_row.amount, 0.0)
        self.assertEqual(paye_row.default_amount, 0.0)
        mock_frappe.msgprint.assert_called_once()

    def test_no_paye_row_is_safe_noop(self):
        # Salary slip without NG - PAYE Tax deduction → on_validate returns silently
        doc = _make_slip(100_000, [_make_row("NG - Pension Employee", 8_000.0)])
        # Should not raise
        with patch("zinye_ng.nigeria.payroll.salary_slip.frappe"):
            on_validate(doc)

    def test_deductions_reduce_paye(self):
        # ₦100,000/month gross, ₦8,000 pension, ₦2,500 NHF
        # Annual gross = ₦1,200,000
        # Annual deductions = (8,000 + 2,500) × 12 = ₦126,000
        # Taxable = 1,200,000 - 126,000 = 1,074,000
        #   800k @ 0%  = 0
        #   274k @ 15% = 41,100
        # Monthly PAYE = 41,100 / 12 = 3,425
        pension_row = _make_row("NG - Pension Employee", 8_000.0)
        nhf_row = _make_row("NG - NHF", 2_500.0)
        paye_row = _make_row("NG - PAYE Tax", 0.0)
        doc = _make_slip(100_000, [pension_row, nhf_row, paye_row])

        with patch("zinye_ng.nigeria.payroll.salary_slip.frappe"):
            on_validate(doc)

        self.assertAlmostEqual(paye_row.amount, 3_425.0, places=2)
