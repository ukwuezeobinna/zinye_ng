"""
Nigeria Pension Schedule (PenCom Remittance Schedule).

Produces the monthly pension remittance file for submission to the
Pension Fund Administrators (PFAs) via PenCom. Required fields are
employee name, RSA PIN, PFA name, employee contribution, and employer
contribution.

PRA 2014 s.4: employer must remit within 7 working days of salary payment.
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
        {"label": _("RSA PIN"), "fieldname": "ng_rsa_pin", "fieldtype": "Data", "width": 140},
        {"label": _("PFA"), "fieldname": "ng_pfa_name", "fieldtype": "Data", "width": 160},
        {"label": _("Department"), "fieldname": "department", "fieldtype": "Link", "options": "Department", "width": 140},
        {"label": _("Gross Pay"), "fieldname": "gross_pay", "fieldtype": "Currency", "width": 130},
        {"label": _("Employee Contribution (8%)"), "fieldname": "employee_pension", "fieldtype": "Currency", "width": 160},
        {"label": _("Employer Contribution (10%)"), "fieldname": "employer_pension", "fieldtype": "Currency", "width": 160},
        {"label": _("Total Contribution"), "fieldname": "total_pension", "fieldtype": "Currency", "width": 140},
    ]


def get_data(filters):
    SalarySlip = frappe.qb.DocType("Salary Slip")
    SalaryDetail = frappe.qb.DocType("Salary Detail")
    Employee = frappe.qb.DocType("Employee")

    base_query = (
        frappe.qb.from_(SalarySlip)
        .inner_join(Employee).on(SalarySlip.employee == Employee.name)
        .select(
            SalarySlip.employee,
            SalarySlip.employee_name,
            SalarySlip.department,
            SalarySlip.gross_pay,
            Employee.custom_ng_rsa_pin.as_("ng_rsa_pin"),
            Employee.custom_ng_pfa_name.as_("ng_pfa_name"),
        )
        .where(SalarySlip.docstatus == 1)
    )

    if filters.company:
        base_query = base_query.where(SalarySlip.company == filters.company)
    if filters.month:
        base_query = base_query.where(Extract("month", SalarySlip.start_date) == filters.month)
    if filters.year:
        base_query = base_query.where(Extract("year", SalarySlip.start_date) == filters.year)

    slips = base_query.run(as_dict=True)
    if not slips:
        return []

    ded_query = (
        frappe.qb.from_(SalarySlip)
        .inner_join(SalaryDetail).on(SalarySlip.name == SalaryDetail.parent)
        .select(SalarySlip.employee, SalaryDetail.salary_component, SalaryDetail.amount)
        .where(
            (SalarySlip.docstatus == 1)
            & (SalaryDetail.salary_component.isin(["NG - Pension Employee", "NG - Pension Employer"]))
        )
    )

    if filters.company:
        ded_query = ded_query.where(SalarySlip.company == filters.company)
    if filters.month:
        ded_query = ded_query.where(Extract("month", SalarySlip.start_date) == filters.month)
    if filters.year:
        ded_query = ded_query.where(Extract("year", SalarySlip.start_date) == filters.year)

    pension_rows = ded_query.run(as_dict=True)
    pension_map: dict[str, dict] = {}
    for row in pension_rows:
        if row.employee not in pension_map:
            pension_map[row.employee] = {"employee_pension": 0, "employer_pension": 0}
        if row.salary_component == "NG - Pension Employee":
            pension_map[row.employee]["employee_pension"] += row.amount
        elif row.salary_component == "NG - Pension Employer":
            pension_map[row.employee]["employer_pension"] += row.amount

    data = []
    for slip in slips:
        p = pension_map.get(slip.employee, {})
        emp_contrib = p.get("employee_pension", 0)
        er_contrib = p.get("employer_pension", 0)
        data.append({
            "employee": slip.employee,
            "employee_name": slip.employee_name,
            "ng_rsa_pin": slip.ng_rsa_pin,
            "ng_pfa_name": slip.ng_pfa_name,
            "department": slip.department,
            "gross_pay": slip.gross_pay,
            "employee_pension": emp_contrib,
            "employer_pension": er_contrib,
            "total_pension": emp_contrib + er_contrib,
        })

    return sorted(data, key=lambda x: x["employee_name"])
