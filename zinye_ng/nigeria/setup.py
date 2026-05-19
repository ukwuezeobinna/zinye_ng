"""
zinye_ng installation setup.

Adds Nigeria-specific custom fields to standard ERPNext/HRMS doctypes.
Modelled on hrms/regional/india/setup.py — includes install, migrate, and uninstall hooks.

Run automatically on:  bench migrate (after_migrate hook)
Run manually:          bench execute zinye_ng.nigeria.setup.after_install
"""
from __future__ import annotations

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


_NIGERIA_REPORTS = [
    "Nigeria PAYE Schedule",
    "Nigeria Pension Schedule",
    "Nigeria VAT Return",
    "Nigeria WHT Schedule",
]


def after_install():
    create_nigeria_custom_fields()
    create_default_nigeria_payroll_settings()
    create_default_compliance_settings()
    add_custom_roles_for_reports()
    frappe.db.commit()


def after_migrate():
    create_nigeria_custom_fields()
    create_default_compliance_settings()
    _link_payroll_components()
    _create_ng_salary_structures()
    frappe.db.commit()


def before_uninstall():
    """Remove all custom fields added by this app."""
    custom_fields = _get_custom_fields()
    all_fieldnames = []
    for doctype, fields in custom_fields.items():
        for f in fields:
            all_fieldnames.append(f["fieldname"])
        frappe.db.delete(
            "Custom Field",
            {"dt": doctype, "fieldname": ["in", [f["fieldname"] for f in fields]]},
        )
    frappe.db.commit()


def add_custom_roles_for_reports():
    """Register Nigeria reports to be visible to HR Manager and Accounts Manager roles."""
    for report_name in _NIGERIA_REPORTS:
        if not frappe.db.get_value("Custom Role", {"report": report_name}):
            doc = frappe.new_doc("Custom Role")
            doc.update({
                "report": report_name,
                "roles": [
                    {"role": "HR Manager"},
                    {"role": "Accounts Manager"},
                    {"role": "System Manager"},
                ],
            })
            doc.insert(ignore_permissions=True)


def create_nigeria_custom_fields():
    custom_fields = _get_custom_fields()
    create_custom_fields(custom_fields, ignore_validate=True)


def _get_custom_fields():
    return {
        # ── Company ──────────────────────────────────────────────────────────
        "Company": [
            {
                "fieldname": "ng_compliance_section",
                "label": "Nigeria Compliance",
                "fieldtype": "Section Break",
                "insert_after": "country",
                "collapsible": 1,
            },
            {
                "fieldname": "ng_tin",
                "label": "TIN (Tax Identification Number)",
                "fieldtype": "Data",
                "insert_after": "ng_compliance_section",
                "description": "12-digit NRS Tax Identification Number",
            },
            {
                "fieldname": "ng_rc_number",
                "label": "RC Number (CAC)",
                "fieldtype": "Data",
                "insert_after": "ng_tin",
                "description": "Corporate Affairs Commission registration number",
            },
            {
                "fieldname": "ng_vat_number",
                "label": "VAT Registration Number",
                "fieldtype": "Data",
                "insert_after": "ng_rc_number",
            },
            {
                "fieldname": "ng_col_break_1",
                "fieldtype": "Column Break",
                "insert_after": "ng_vat_number",
            },
            {
                "fieldname": "ng_registered_state",
                "label": "Registered State",
                "fieldtype": "Select",
                "insert_after": "ng_col_break_1",
                "options": _NIGERIA_STATES,
                "description": "State where PAYE is remitted",
            },
            {
                "fieldname": "ng_sirs_code",
                "label": "State IRS Code",
                "fieldtype": "Data",
                "insert_after": "ng_registered_state",
                "description": "State Inland Revenue Service employer code",
            },
            {
                "fieldname": "ng_itf_liable",
                "label": "ITF Liable",
                "fieldtype": "Check",
                "insert_after": "ng_sirs_code",
                "description": "Tick if company has 5+ employees OR ₦50M+ annual payroll",
                "default": "1",
            },
        ],

        # ── Employee ──────────────────────────────────────────────────────────
        "Employee": [
            {
                "fieldname": "ng_compliance_section",
                "label": "Nigeria Compliance",
                "fieldtype": "Section Break",
                "insert_after": "bank_name",
                "collapsible": 1,
            },
            {
                "fieldname": "ng_tin",
                "label": "Employee TIN",
                "fieldtype": "Data",
                "insert_after": "ng_compliance_section",
                "description": "Employee Tax Identification Number (FIRS)",
            },
            {
                "fieldname": "ng_nhf_number",
                "label": "NHF Number",
                "fieldtype": "Data",
                "insert_after": "ng_tin",
                "description": "National Housing Fund registration number (FMBN)",
            },
            {
                "fieldname": "ng_col_break_1",
                "fieldtype": "Column Break",
                "insert_after": "ng_nhf_number",
            },
            {
                "fieldname": "ng_pfa_name",
                "label": "Pension Fund Administrator (PFA)",
                "fieldtype": "Data",
                "insert_after": "ng_col_break_1",
                "description": "Employee's chosen PFA for pension remittance",
            },
            {
                "fieldname": "ng_rsa_pin",
                "label": "RSA PIN",
                "fieldtype": "Data",
                "insert_after": "ng_pfa_name",
                "description": "Retirement Savings Account PIN (PenCom)",
            },
            {
                "fieldname": "ng_exempted_from_nhf",
                "label": "Exempted from NHF",
                "fieldtype": "Check",
                "insert_after": "ng_rsa_pin",
                "description": "Tick for employees earning less than ₦3,000/month",
            },
        ],

        # ── Customer ─────────────────────────────────────────────────────────
        "Customer": [
            {
                "fieldname": "ng_tin",
                "label": "TIN",
                "fieldtype": "Data",
                "insert_after": "tax_id",
                "description": "Required for B2B NRS e-invoicing",
            },
            {
                "fieldname": "ng_rc_number",
                "label": "RC Number",
                "fieldtype": "Data",
                "insert_after": "ng_tin",
            },
        ],

        # ── Supplier ─────────────────────────────────────────────────────────
        "Supplier": [
            {
                "fieldname": "ng_tin",
                "label": "TIN",
                "fieldtype": "Data",
                "insert_after": "tax_id",
                "description": "Required for WHT schedule reporting",
            },
            {
                "fieldname": "ng_rc_number",
                "label": "RC Number",
                "fieldtype": "Data",
                "insert_after": "ng_tin",
            },
            {
                "fieldname": "ng_wht_category",
                "label": "WHT Category",
                "fieldtype": "Select",
                "insert_after": "ng_rc_number",
                "options": _WHT_CATEGORIES,
                "description": "Determines withholding tax rate applied on payments",
            },
        ],

        # ── Sales Invoice ─────────────────────────────────────────────────────
        "Sales Invoice": [
            {
                "fieldname": "ng_firs_section",
                "label": "NRS e-Invoice",
                "fieldtype": "Section Break",
                "insert_after": "against_income_account",
                "collapsible": 1,
            },
            {
                "fieldname": "ng_firs_irn",
                "label": "IRN",
                "fieldtype": "Data",
                "insert_after": "ng_firs_section",
                "read_only": 1,
                "description": "Invoice Reference Number from NRS FIRSMBS",
            },
            {
                "fieldname": "ng_firs_csid",
                "label": "CSID",
                "fieldtype": "Data",
                "insert_after": "ng_firs_irn",
                "read_only": 1,
                "description": "Cryptographic Stamp Identifier from NRS",
            },
            {
                "fieldname": "ng_firs_status",
                "label": "NRS Status",
                "fieldtype": "Select",
                "insert_after": "ng_firs_csid",
                "options": "Not Required\nPending\nSubmitted\nCleared\nFailed",
                "default": "Not Required",
                "read_only": 1,
            },
        ],

        # ── Salary Component ──────────────────────────────────────────────────
        "Salary Component": [
            {
                "fieldname": "ng_component_type",
                "label": "Nigeria Component Type",
                "fieldtype": "Select",
                "insert_after": "statistical_component",
                "options": "\nPAYE\nPension (Employee)\nPension (Employer)\nNHF\nNHIS\nNSITF\nITF",
                "description": "Used for Nigeria statutory compliance reporting",
            },
        ],

        # ── Purchase Invoice ──────────────────────────────────────────────────
        "Purchase Invoice": [
            {
                "fieldname": "ng_wht_section",
                "label": "Withholding Tax",
                "fieldtype": "Section Break",
                "insert_after": "additional_discount_percentage",
                "collapsible": 1,
            },
            {
                "fieldname": "ng_wht_applicable",
                "label": "WHT Applicable",
                "fieldtype": "Check",
                "insert_after": "ng_wht_section",
            },
            {
                "fieldname": "ng_wht_rate",
                "label": "WHT Rate (%)",
                "fieldtype": "Percent",
                "insert_after": "ng_wht_applicable",
                "depends_on": "eval:doc.ng_wht_applicable",
            },
            {
                "fieldname": "ng_wht_amount",
                "label": "WHT Amount",
                "fieldtype": "Currency",
                "insert_after": "ng_wht_rate",
                "read_only": 1,
                "depends_on": "eval:doc.ng_wht_applicable",
            },
            {
                "fieldname": "ng_wht_account",
                "label": "WHT Payable Account",
                "fieldtype": "Link",
                "options": "Account",
                "insert_after": "ng_wht_amount",
                "depends_on": "eval:doc.ng_wht_applicable",
            },
        ],
    }


def create_default_compliance_settings():
    if frappe.db.exists("Nigeria Compliance Settings", "Nigeria Compliance Settings"):
        return
    doc = frappe.new_doc("Nigeria Compliance Settings")
    doc.einvoice_environment = "Sandbox"
    doc.einvoice_sandbox_url = "https://api-sandbox.einvoice.firs.gov.ng"
    doc.einvoice_production_url = "https://api.einvoice.firs.gov.ng"
    doc.einvoice_default_vat_rate = 7.5
    doc.einvoice_b2b_only = 1
    doc.einvoice_auto_submit = 1
    doc.atrs_environment = "Development"
    doc.atrs_auto_submit = 1
    doc.insert(ignore_permissions=True)


def _link_payroll_components():
    """Set component links on Nigeria Payroll Settings if the fixtures exist."""
    component_map = {
        "pension_employee_component": "NG - Pension Employee",
        "pension_employer_component": "NG - Pension Employer",
        "nhf_component": "NG - NHF",
        "nhis_component": "NG - NHIS",
        "nsitf_component": "NG - NSITF",
        "itf_component": "NG - ITF",
    }
    settings = frappe.get_single("Nigeria Payroll Settings")
    changed = False
    for field, component in component_map.items():
        if not settings.get(field) and frappe.db.exists("Salary Component", component):
            settings.set(field, component)
            changed = True
    if changed:
        settings.save(ignore_permissions=True)


_NG_STRUCTURE_NAME = "NG Employee Standard"

# Components required before the salary structure can be created.
# Ordered so that each row's formula variables are already in the structure
# by the time ERPNext evaluates them (earnings first, in dependency order).
_NG_EARNINGS = [
    "NG - Basic Salary",
    "NG - Housing Allowance",
    "NG - Transport Allowance",
    "NG - Pensionable Base",        # formula: basic_salary + housing_allowance + transport_allowance
    "NG - Pension Employer",        # formula: pension_employee_base * 0.10 — statistical
    "NG - NSITF",                   # formula: gross_pay * 0.01 — statistical
]

_NG_DEDUCTIONS = [
    "NG - Pension Employee",        # formula: pension_employee_base * 0.08
    "NG - NHF",                     # formula: basic_salary * 0.025
    "NG - NHIS",                    # formula: gross_pay * 0.05
    "NG - PAYE Tax",                # computed by salary_slip hook — variable_based_on_taxable_salary
]


def _create_ng_salary_structures():
    """
    Create 'NG Employee Standard' salary structure for each Nigeria company.

    Idempotent — skips companies that already have the structure. Requires all
    NG salary component fixtures to be loaded (runs in after_migrate, after import).
    """
    all_components = _NG_EARNINGS + _NG_DEDUCTIONS
    missing = [c for c in all_components if not frappe.db.exists("Salary Component", c)]
    if missing:
        return

    companies = frappe.get_all("Company", filters={"country": "Nigeria"}, pluck="name")
    for company in companies:
        _ensure_ng_structure(company)


def _ensure_ng_structure(company):
    if frappe.db.exists("Salary Structure", _NG_STRUCTURE_NAME):
        return

    currency = frappe.db.get_value("Company", company, "default_currency") or "NGN"

    struct = frappe.new_doc("Salary Structure")
    struct.name = _NG_STRUCTURE_NAME
    struct.company = company
    struct.is_active = "Yes"
    struct.payroll_frequency = "Monthly"
    struct.currency = currency

    for component_name in _NG_EARNINGS:
        _append_component_row(struct, "earnings", component_name)

    for component_name in _NG_DEDUCTIONS:
        _append_component_row(struct, "deductions", component_name)

    struct.insert(ignore_permissions=True)


def _append_component_row(struct, table, component_name):
    """Append a Salary Detail row, populating fetch_from fields from the component."""
    comp = frappe.db.get_value(
        "Salary Component",
        component_name,
        [
            "salary_component_abbr",
            "statistical_component",
            "depends_on_payment_days",
            "exempted_from_income_tax",
            "variable_based_on_taxable_salary",
            "do_not_include_in_total",
            "amount_based_on_formula",
            "formula",
            "condition",
        ],
        as_dict=True,
    )
    if not comp:
        return

    struct.append(table, {
        "salary_component": component_name,
        "abbr": comp.salary_component_abbr,
        "statistical_component": comp.statistical_component,
        "depends_on_payment_days": comp.depends_on_payment_days,
        "exempted_from_income_tax": comp.exempted_from_income_tax,
        "variable_based_on_taxable_salary": comp.variable_based_on_taxable_salary,
        "do_not_include_in_total": comp.do_not_include_in_total,
        "amount_based_on_formula": comp.amount_based_on_formula,
        "formula": comp.formula or "",
        "condition": comp.condition or "",
    })


def create_default_nigeria_payroll_settings():
    if frappe.db.exists("Nigeria Payroll Settings", "Nigeria Payroll Settings"):
        return
    doc = frappe.new_doc("Nigeria Payroll Settings")
    doc.pension_employee_rate = 8.0
    doc.pension_employer_rate = 10.0
    doc.nhf_rate = 2.5
    doc.nsitf_rate = 1.0
    doc.itf_rate = 1.0
    doc.itf_min_employees = 5
    doc.itf_min_annual_payroll = 50_000_000
    doc.insert(ignore_permissions=True)


# ── Reference data ─────────────────────────────────────────────────────────

_NIGERIA_STATES = (
    "\nAbia\nAdamawa\nAkwa Ibom\nAnambra\nBauchi\nBayelsa\nBenue\nBorno"
    "\nCross River\nDelta\nEbonyi\nEdo\nEkiti\nEnugu\nFCT\nGombe\nImo"
    "\nJigawa\nKaduna\nKano\nKatsina\nKebbi\nKogi\nKwara\nLagos\nNasarawa"
    "\nNiger\nOgun\nOndo\nOsun\nOyo\nPlateau\nRivers\nSokoto\nTaraba"
    "\nYobe\nZamfara"
)

_WHT_CATEGORIES = (
    "\nProfessional / Consultancy Fees"
    "\nManagement / Technical Fees"
    "\nConstruction / Building"
    "\nRent / Lease"
    "\nRoyalties"
    "\nDividends"
    "\nInterest (Financial Institution)"
    "\nCommission / Agency Fees"
    "\nContracts (Supply of Goods)"
    "\nDirectors Fees"
)
