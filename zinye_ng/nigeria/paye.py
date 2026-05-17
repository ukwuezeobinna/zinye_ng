"""
Nigeria PAYE computation engine.

Nigeria Tax Act 2025 (Act No. 7, gazetted 26 June 2025, effective 1 Jan 2026).
Replaces PITA 2011 and all Finance Act amendments.

Tax bands — Section 58 / Fourth Schedule (annual):
  First  ₦800,000       →  0%
  Next   ₦2,200,000     → 15%
  Next   ₦9,000,000     → 18%
  Next  ₦13,000,000     → 21%
  Next  ₦25,000,000     → 23%
  Above ₦50,000,000     → 25%

Section 30 deductions (replace old CRA):
  - NHF contributions (FMBN)
  - NHIS contributions (NEW vs old PITA)
  - Pension contributions (PRA 2014)
  - Home loan interest (residential mortgage only)
  - Life assurance / annuity premiums
  - Rent relief: 20% of annual rent paid, capped at ₦500,000 (NEW vs old PITA)

Section 162(1)(t): Employees earning ≤ national minimum wage are fully exempt.

Monthly PAYE = annual PAYE / 12
"""
from __future__ import annotations

from dataclasses import dataclass, field

# Annual tax bands: (band_size, rate)
# Cumulative thresholds: 800k, 3M, 12M, 25M, 50M, ∞
_BANDS = [
    (800_000, 0.00),       # First ₦800k — 0% (s.58 Fourth Schedule)
    (2_200_000, 0.15),     # Next ₦2.2M  — 15%
    (9_000_000, 0.18),     # Next ₦9M    — 18%
    (13_000_000, 0.21),    # Next ₦13M   — 21%
    (25_000_000, 0.23),    # Next ₦25M   — 23%
    (float("inf"), 0.25),  # Above ₦50M  — 25%
]

# s.162(1)(t): minimum wage earners are fully exempt (₦70,000/month as of 2024 proclamation)
MINIMUM_WAGE_MONTHLY = 70_000.0
MINIMUM_WAGE_ANNUAL = MINIMUM_WAGE_MONTHLY * 12

# s.30 rent relief cap
RENT_RELIEF_RATE = 0.20
RENT_RELIEF_CAP = 500_000.0


@dataclass
class PayeResult:
    annual_gross: float
    # Section 30 deductions
    nhf: float
    nhis: float
    pension_employee: float
    home_loan_interest: float
    life_assurance: float
    rent_relief: float
    total_deductions: float
    taxable_income: float
    annual_paye: float
    monthly_paye: float
    effective_rate: float  # annual_paye / annual_gross
    minimum_wage_exempt: bool


def compute_annual_paye(
    annual_gross: float,
    nhf: float = 0.0,
    nhis: float = 0.0,
    pension_employee: float = 0.0,
    home_loan_interest: float = 0.0,
    life_assurance: float = 0.0,
    annual_rent: float = 0.0,
) -> PayeResult:
    """
    Compute annual PAYE under the Nigeria Tax Act 2025.

    All amounts in Naira. Deductions that are monthly should be multiplied × 12
    by the caller before passing in. annual_rent is the actual annual rent paid;
    the 20% relief and ₦500k cap are applied here.
    """
    annual_gross = float(annual_gross)

    # s.162(1)(t): minimum wage exemption — full exemption, zero PAYE
    if annual_gross <= MINIMUM_WAGE_ANNUAL:
        return PayeResult(
            annual_gross=annual_gross,
            nhf=nhf,
            nhis=nhis,
            pension_employee=pension_employee,
            home_loan_interest=home_loan_interest,
            life_assurance=life_assurance,
            rent_relief=0.0,
            total_deductions=0.0,
            taxable_income=0.0,
            annual_paye=0.0,
            monthly_paye=0.0,
            effective_rate=0.0,
            minimum_wage_exempt=True,
        )

    # s.30 rent relief: 20% of annual rent paid, capped at ₦500,000
    rent_relief = min(annual_rent * RENT_RELIEF_RATE, RENT_RELIEF_CAP)

    total_deductions = nhf + nhis + pension_employee + home_loan_interest + life_assurance + rent_relief

    # Taxable income cannot go below zero
    taxable = max(0.0, annual_gross - total_deductions)

    annual_paye = _apply_bands(taxable)
    monthly_paye = annual_paye / 12
    effective_rate = (annual_paye / annual_gross) if annual_gross else 0.0

    return PayeResult(
        annual_gross=annual_gross,
        nhf=nhf,
        nhis=nhis,
        pension_employee=pension_employee,
        home_loan_interest=home_loan_interest,
        life_assurance=life_assurance,
        rent_relief=rent_relief,
        total_deductions=total_deductions,
        taxable_income=taxable,
        annual_paye=annual_paye,
        monthly_paye=monthly_paye,
        effective_rate=effective_rate,
        minimum_wage_exempt=False,
    )


def compute_monthly_paye(
    monthly_gross: float,
    monthly_nhf: float = 0.0,
    monthly_nhis: float = 0.0,
    monthly_pension_employee: float = 0.0,
    monthly_home_loan_interest: float = 0.0,
    monthly_life_assurance: float = 0.0,
    annual_rent: float = 0.0,
) -> PayeResult:
    """Convenience wrapper: annualise monthly figures, compute, return monthly PAYE."""
    return compute_annual_paye(
        annual_gross=monthly_gross * 12,
        nhf=monthly_nhf * 12,
        nhis=monthly_nhis * 12,
        pension_employee=monthly_pension_employee * 12,
        home_loan_interest=monthly_home_loan_interest * 12,
        life_assurance=monthly_life_assurance * 12,
        annual_rent=annual_rent,
    )


def _apply_bands(taxable: float) -> float:
    tax = 0.0
    remaining = taxable
    for band_size, rate in _BANDS:
        if remaining <= 0:
            break
        in_band = min(remaining, band_size)
        tax += in_band * rate
        remaining -= in_band
    return tax


# ---------------------------------------------------------------------------
# Statutory deduction helpers (rates as per current regulations)
# ---------------------------------------------------------------------------

def pension_employee(emolument: float) -> float:
    """Employee pension: 8% of (Basic + Housing + Transport). PRA 2014 s.4(1)."""
    return emolument * 0.08


def pension_employer(emolument: float) -> float:
    """Employer pension: 10% of (Basic + Housing + Transport). PRA 2014 s.4(1)."""
    return emolument * 0.10


def nhf(basic_salary: float) -> float:
    """NHF: 2.5% of basic salary. Exempt if earning < ₦3,000/month (FMBN Act)."""
    return basic_salary * 0.025 if basic_salary >= 3_000 else 0.0


def nsitf(total_monthly_emolument: float) -> float:
    """NSITF: 1% of total monthly emolument. Employer contribution only."""
    return total_monthly_emolument * 0.01


def itf_annual(annual_payroll: float, employee_count: int) -> float:
    """
    ITF: 1% of annual payroll.
    Applies to companies with 5+ employees OR annual payroll ≥ ₦50,000,000.
    """
    if employee_count < 5 and annual_payroll < 50_000_000:
        return 0.0
    return annual_payroll * 0.01
