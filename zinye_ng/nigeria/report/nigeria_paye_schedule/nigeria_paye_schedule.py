"""
Nigeria PAYE Schedule Report.

Produces the monthly PAYE remittance schedule for submission to the
State Inland Revenue Service (SIRS) or FIRS. Lists every employee,
their gross pay, taxable income, monthly PAYE deducted, and TIN.

Employers must remit PAYE to the relevant SIRS by the 10th of the
following month (Finance Act 2020 amendment to PITA, now consolidated
under Nigeria Tax Act 2025 s.64).
"""
from __future__ import annotations

import frappe
from frappe import _
from frappe.query_builder.functions import Extract


def execute(filters=None):
    filters = frappe._dict(filters or {})
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {"label": _("Employee"), "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 140},
        {"label": _("Employee Name"), "fieldname": "employee_name", "fieldtype": "Data", "width": 180},
        {"label": _("Employee TIN"), "fieldname": "ng_tin", "fieldtype": "Data", "width": 140},
        {"label": _("RSA PIN"), "fieldname": "ng_rsa_pin", "fieldtype": "Data", "width": 120},
        {"label": _("Department"), "fieldname": "department", "fieldtype": "Link", "options": "Department", "width": 140},
        {"label": _("Gross Pay"), "fieldname": "gross_pay", "fieldtype": "Currency", "width": 140},
        {"label": _("Pension (Employee)"), "fieldname": "pension_employee", "fieldtype": "Currency", "width": 140},
        {"label": _("NHF"), "fieldname": "nhf", "fieldtype": "Currency", "width": 100},
        {"label": _("NHIS"), "fieldname": "nhis", "fieldtype": "Currency", "width": 100},
        {"label": _("Taxable Income"), "fieldname": "taxable_income", "fieldtype": "Currency", "width": 140},
        {"label": _("PAYE Tax"), "fieldname": "paye_tax", "fieldtype": "Currency", "width": 120},
        {"label": _("Net Pay"), "fieldname": "net_pay", "fieldtype": "Currency", "width": 120},
    ]


def get_data(filters):
    SalarySlip = frappe.qb.DocType("Salary Slip")
    SalaryDetail = frappe.qb.DocType("Salary Detail")
    Employee = frappe.qb.DocType("Employee")

    # Get all submitted salary slips for the period
    query = (
        frappe.qb.from_(SalarySlip)
        .inner_join(Employee).on(SalarySlip.employee == Employee.name)
        .select(
            SalarySlip.employee,
            SalarySlip.employee_name,
            SalarySlip.department,
            SalarySlip.gross_pay,
            SalarySlip.net_pay,
            Employee.custom_ng_tin.as_("ng_tin"),
            Employee.custom_ng_rsa_pin.as_("ng_rsa_pin"),
        )
        .where(SalarySlip.docstatus == 1)
    )

    if filters.company:
        query = query.where(SalarySlip.company == filters.company)
    if filters.month:
        query = query.where(Extract("month", SalarySlip.start_date) == filters.month)
    if filters.year:
        query = query.where(Extract("year", SalarySlip.start_date) == filters.year)
    if filters.department:
        query = query.where(SalarySlip.department == filters.department)

    slips = query.run(as_dict=True)
    if not slips:
        return []

    slip_names = [s.employee for s in slips]
    slip_map = {s.employee: s for s in slips}

    # Get deduction amounts per employee in a single query
    deductions_query = (
        frappe.qb.from_(SalarySlip)
        .inner_join(SalaryDetail).on(SalarySlip.name == SalaryDetail.parent)
        .select(
            SalarySlip.employee,
            SalaryDetail.salary_component,
            SalaryDetail.amount,
        )
        .where(
            (SalarySlip.docstatus == 1)
            & (SalaryDetail.parentfield == "deductions")
            & (SalaryDetail.salary_component.isin(["NG - PAYE Tax", "NG - Pension Employee", "NG - NHF", "NG - NHIS"]))
        )
    )

    if filters.company:
        deductions_query = deductions_query.where(SalarySlip.company == filters.company)
    if filters.month:
        deductions_query = deductions_query.where(Extract("month", SalarySlip.start_date) == filters.month)
    if filters.year:
        deductions_query = deductions_query.where(Extract("year", SalarySlip.start_date) == filters.year)

    deduction_rows = deductions_query.run(as_dict=True)

    # Pivot deductions per employee
    ded_map: dict[str, dict] = {}
    for row in deduction_rows:
        if row.employee not in ded_map:
            ded_map[row.employee] = {"pension_employee": 0, "nhf": 0, "nhis": 0, "paye_tax": 0}
        if row.salary_component == "NG - Pension Employee":
            ded_map[row.employee]["pension_employee"] += row.amount
        elif row.salary_component == "NG - NHF":
            ded_map[row.employee]["nhf"] += row.amount
        elif row.salary_component == "NG - NHIS":
            ded_map[row.employee]["nhis"] += row.amount
        elif row.salary_component == "NG - PAYE Tax":
            ded_map[row.employee]["paye_tax"] += row.amount

    data = []
    for slip in slips:
        emp = slip.employee
        d = ded_map.get(emp, {})
        deductions_total = d.get("pension_employee", 0) + d.get("nhf", 0) + d.get("nhis", 0)
        data.append({
            "employee": emp,
            "employee_name": slip.employee_name,
            "ng_tin": slip.ng_tin,
            "ng_rsa_pin": slip.ng_rsa_pin,
            "department": slip.department,
            "gross_pay": slip.gross_pay,
            "pension_employee": d.get("pension_employee", 0),
            "nhf": d.get("nhf", 0),
            "nhis": d.get("nhis", 0),
            "taxable_income": max(0, float(slip.gross_pay or 0) - deductions_total),
            "paye_tax": d.get("paye_tax", 0),
            "net_pay": slip.net_pay,
        })

    return sorted(data, key=lambda x: x["employee_name"])


@frappe.whitelist()
def get_years() -> str:
    year_list = frappe.db.sql_list(
        "select distinct YEAR(start_date) from `tabSalary Slip` where docstatus=1 ORDER BY YEAR(start_date) DESC"
    )
    if not year_list:
        from frappe.utils import getdate
        year_list = [getdate().year]
    return "\n".join(str(y) for y in year_list)
