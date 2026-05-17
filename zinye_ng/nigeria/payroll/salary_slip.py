"""
Salary Slip validate hook.

Reads the statutory deduction components already computed by ERPNext's payroll
engine and passes them to the PAYE engine to recompute the PAYE Tax row.

Flow:
  1. ERPNext computes all deductions via formula (Pension, NHF, NHIS, etc.)
  2. This hook reads those computed amounts from the slip's deductions table
  3. Passes them to compute_monthly_paye() as s.30 deductions
  4. Overwrites the NG - PAYE Tax row amount with the correct value
  5. If the employee is minimum-wage exempt, the row is zeroed out
"""
from __future__ import annotations

import frappe
from frappe import _

from zinye_ng.nigeria.paye import compute_monthly_paye


_PAYE_COMPONENT = "NG - PAYE Tax"

# Map from salary component name → PayeResult field name for s.30 deductions
_DEDUCTION_MAP = {
    "NG - Pension Employee": "monthly_pension_employee",
    "NG - NHF": "monthly_nhf",
    "NG - NHIS": "monthly_nhis",
}


def on_validate(doc, method=None):
    """Recompute PAYE Tax row using Nigeria Tax Act 2025 bands and s.30 deductions."""
    paye_row = _find_paye_row(doc)
    if not paye_row:
        return

    deductions = _collect_deductions(doc)
    result = compute_monthly_paye(
        monthly_gross=float(doc.gross_pay or 0),
        **deductions,
    )

    paye_row.amount = result.monthly_paye
    paye_row.default_amount = result.monthly_paye

    if result.minimum_wage_exempt:
        frappe.msgprint(
            _("Employee {0} earns ≤ national minimum wage — PAYE set to zero (s.162(1)(t) Nigeria Tax Act 2025).").format(
                doc.employee_name
            ),
            indicator="blue",
            alert=True,
        )


def _find_paye_row(doc):
    for row in doc.get("deductions") or []:
        if row.salary_component == _PAYE_COMPONENT:
            return row
    return None


def _collect_deductions(doc) -> dict:
    """
    Read computed deduction amounts from the slip for use as s.30 inputs.
    Returns keyword arguments for compute_monthly_paye().
    """
    amounts: dict[str, float] = {v: 0.0 for v in _DEDUCTION_MAP.values()}
    for row in doc.get("deductions") or []:
        if row.salary_component in _DEDUCTION_MAP:
            key = _DEDUCTION_MAP[row.salary_component]
            amounts[key] = float(row.amount or 0)
    return amounts
