"""
Unit tests for Nigeria PAYE computation engine.

All expected values are derived from first-principles band arithmetic against
the Nigeria Tax Act 2025 bands (s.58 / Fourth Schedule). No DB required.
"""
from frappe.tests import UnitTestCase

from zinye_ng.nigeria.paye import (
    MINIMUM_WAGE_ANNUAL,
    RENT_RELIEF_CAP,
    RENT_RELIEF_RATE,
    compute_annual_paye,
    compute_monthly_paye,
    itf_annual,
    nhf,
    nsitf,
    pension_employee,
    pension_employer,
)


class TestMinimumWageExemption(UnitTestCase):
    def test_exactly_at_minimum_wage_is_exempt(self):
        result = compute_annual_paye(annual_gross=MINIMUM_WAGE_ANNUAL)
        self.assertTrue(result.minimum_wage_exempt)
        self.assertEqual(result.annual_paye, 0.0)
        self.assertEqual(result.monthly_paye, 0.0)

    def test_below_minimum_wage_is_exempt(self):
        result = compute_annual_paye(annual_gross=500_000)
        self.assertTrue(result.minimum_wage_exempt)
        self.assertEqual(result.annual_paye, 0.0)

    def test_above_minimum_wage_is_not_exempt(self):
        result = compute_annual_paye(annual_gross=MINIMUM_WAGE_ANNUAL + 1)
        self.assertFalse(result.minimum_wage_exempt)


class TestPayeBands(UnitTestCase):
    """Verify band arithmetic with no s.30 deductions."""

    def test_income_in_first_zero_rate_band(self):
        # ₦800k falls entirely in the 0% band
        result = compute_annual_paye(annual_gross=800_000)
        self.assertEqual(result.annual_paye, 0.0)

    def test_income_spanning_first_two_bands(self):
        # Annual gross ₦1,200,000:
        #   ₦800k @ 0%   = ₦0
        #   ₦400k @ 15%  = ₦60,000
        result = compute_annual_paye(annual_gross=1_200_000)
        self.assertAlmostEqual(result.annual_paye, 60_000.0, places=2)
        self.assertAlmostEqual(result.monthly_paye, 5_000.0, places=2)

    def test_income_spanning_three_bands(self):
        # Annual gross ₦4,000,000:
        #   ₦800k    @ 0%  =        0
        #   ₦2,200k  @ 15% =  330,000
        #   ₦1,000k  @ 18% =  180,000
        #   Total           =  510,000
        result = compute_annual_paye(annual_gross=4_000_000)
        self.assertAlmostEqual(result.annual_paye, 510_000.0, places=2)

    def test_income_at_full_second_band_boundary(self):
        # Annual gross exactly ₦3,000,000 (800k + 2,200k):
        #   ₦800k   @ 0%  = 0
        #   ₦2,200k @ 15% = 330,000
        result = compute_annual_paye(annual_gross=3_000_000)
        self.assertAlmostEqual(result.annual_paye, 330_000.0, places=2)

    def test_monthly_wrapper_annualises_correctly(self):
        # ₦100,000/month = ₦1,200,000/year → ₦5,000/month PAYE
        result = compute_monthly_paye(monthly_gross=100_000)
        self.assertAlmostEqual(result.monthly_paye, 5_000.0, places=2)


class TestSection30Deductions(UnitTestCase):
    """s.30 deductions reduce taxable income before band application."""

    def test_pension_reduces_taxable_income(self):
        # Annual gross ₦1,200,000, pension ₦96,000 (8% × ₦1,200,000)
        # Taxable = 1,200,000 - 96,000 = 1,104,000
        #   800k @ 0% = 0
        #   304k @ 15% = 45,600
        result = compute_annual_paye(annual_gross=1_200_000, pension_employee=96_000)
        self.assertAlmostEqual(result.taxable_income, 1_104_000.0, places=2)
        self.assertAlmostEqual(result.annual_paye, 45_600.0, places=2)

    def test_multiple_deductions_aggregate(self):
        # Annual gross ₦6,000,000
        # pension = ₦576,000 (8% × ₦7,200,000 pensionable base × 8% ← simplified)
        # NHF = ₦30,000 (2.5% × ₦1,200,000 annual basic)
        # Taxable = 6,000,000 - 576,000 - 30,000 = 5,394,000
        #   800k   @ 0%  =         0
        #   2,200k @ 15% =   330,000
        #   2,394k @ 18% =   430,920
        #   Total         =   760,920
        result = compute_annual_paye(
            annual_gross=6_000_000,
            pension_employee=576_000,
            nhf=30_000,
        )
        self.assertAlmostEqual(result.taxable_income, 5_394_000.0, places=2)
        self.assertAlmostEqual(result.annual_paye, 760_920.0, places=2)

    def test_deductions_cannot_make_taxable_below_zero(self):
        # Deductions exceeding gross income → taxable clamped to 0
        result = compute_annual_paye(annual_gross=2_000_000, pension_employee=3_000_000)
        self.assertEqual(result.taxable_income, 0.0)
        self.assertEqual(result.annual_paye, 0.0)


class TestRentRelief(UnitTestCase):
    """s.30 rent relief: 20% of annual rent, capped at ₦500,000."""

    def test_relief_below_cap(self):
        # Annual rent ₦1,500,000 → relief = 20% × 1,500,000 = ₦300,000 (below cap)
        result = compute_annual_paye(annual_gross=5_000_000, annual_rent=1_500_000)
        self.assertAlmostEqual(result.rent_relief, 300_000.0, places=2)

    def test_relief_capped_at_500k(self):
        # Annual rent ₦3,000,000 → 20% = ₦600,000 → capped at ₦500,000
        result = compute_annual_paye(annual_gross=5_000_000, annual_rent=3_000_000)
        self.assertAlmostEqual(result.rent_relief, RENT_RELIEF_CAP, places=2)

    def test_no_rent_no_relief(self):
        result = compute_annual_paye(annual_gross=5_000_000, annual_rent=0)
        self.assertEqual(result.rent_relief, 0.0)


class TestEffectiveRate(UnitTestCase):
    def test_effective_rate_is_paye_over_gross(self):
        result = compute_annual_paye(annual_gross=1_200_000)
        expected = 60_000 / 1_200_000
        self.assertAlmostEqual(result.effective_rate, expected, places=6)

    def test_zero_gross_does_not_raise(self):
        result = compute_annual_paye(annual_gross=0)
        self.assertEqual(result.effective_rate, 0.0)


class TestStatutoryHelpers(UnitTestCase):
    def test_pension_employee_rate(self):
        self.assertAlmostEqual(pension_employee(100_000), 8_000.0, places=2)

    def test_pension_employer_rate(self):
        self.assertAlmostEqual(pension_employer(100_000), 10_000.0, places=2)

    def test_nhf_rate(self):
        self.assertAlmostEqual(nhf(100_000), 2_500.0, places=2)

    def test_nhf_exempt_below_3000(self):
        self.assertEqual(nhf(2_999), 0.0)

    def test_nsitf_rate(self):
        self.assertAlmostEqual(nsitf(100_000), 1_000.0, places=2)

    def test_itf_large_employer(self):
        # 100 employees, ₦100M payroll → ITF = ₦1,000,000
        self.assertAlmostEqual(itf_annual(100_000_000, 100), 1_000_000.0, places=2)

    def test_itf_exempt_small_employer(self):
        # 3 employees, ₦10M payroll → exempt (below both thresholds)
        self.assertEqual(itf_annual(10_000_000, 3), 0.0)

    def test_itf_by_employee_count_alone(self):
        # 5+ employees, even with low payroll → 1%
        self.assertAlmostEqual(itf_annual(1_000_000, 5), 10_000.0, places=2)
