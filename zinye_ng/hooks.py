app_name = "zinye_ng"
app_title = "Zinye Nigeria"
app_publisher = "Zinye"
app_description = "Nigeria compliance: PAYE, Pension, NHF, NHIS, NSITF, ITF, VAT, WHT, NRS ATRS, NRS MBS e-invoicing, NDPR"
app_email = "dev@zinye.com"
app_license = "MIT"
app_version = "0.1.0"

required_apps = ["frappe", "erpnext", "hrms", "zinye_core"]

# ---------------------------------------------------------------------------
# App setup — adds Nigeria-specific custom fields on install
# ---------------------------------------------------------------------------
after_install = "zinye_ng.nigeria.setup.after_install"
after_migrate = "zinye_ng.nigeria.setup.after_migrate"
before_uninstall = "zinye_ng.nigeria.setup.before_uninstall"

# ---------------------------------------------------------------------------
# Fixtures — loaded via `bench migrate` / `bench import-fixtures`
# ---------------------------------------------------------------------------
fixtures = [
    # Nigeria Income Tax Slab (PAYE bands — Nigeria Tax Act 2025, effective 1 Jan 2026)
    {"dt": "Income Tax Slab", "filters": [["name", "in", ["Nigeria PAYE 2026"]]]},
    # Salary Components: Pension, NHF, NHIS, NSITF, ITF, PAYE
    {
        "dt": "Salary Component",
        "filters": [["name", "in", [
            "NG - Pension Employee",
            "NG - Pension Employer",
            "NG - NHF",
            "NG - NHIS",
            "NG - NSITF",
            "NG - ITF",
            "NG - PAYE Tax",
        ]]],
    },
    # Nigeria VAT 7.5% tax template
    {
        "dt": "Account",
        "filters": [["account_name", "in", ["VAT 7.5% (Nigeria)"]]],
    },
]

# ---------------------------------------------------------------------------
# Doc events
# ---------------------------------------------------------------------------
doc_events = {
    "Salary Slip": {
        "validate": "zinye_ng.nigeria.payroll.salary_slip.on_validate",
    },
    "Sales Invoice": {
        "on_submit": "zinye_ng.nigeria.firs.hooks.on_sales_invoice_submit",
        "on_cancel": "zinye_ng.nigeria.firs.hooks.on_sales_invoice_cancel",
    },
    "POS Invoice": {
        "on_submit": "zinye_ng.nigeria.firs.hooks.on_pos_invoice_submit",
    },
    "Purchase Invoice": {
        "on_submit": "zinye_ng.nigeria.tax.wht.on_purchase_invoice_submit",
    },
    "Nigeria Data Subject Request": {
        "after_insert": "zinye_ng.nigeria.ndpr.on_data_subject_request_insert",
    },
}

# ---------------------------------------------------------------------------
# Scheduled jobs
# ---------------------------------------------------------------------------
scheduler_events = {
    "hourly": [
        "zinye_ng.nigeria.firs.einvoice.poll_pending_einvoices",
    ],
    "daily": [
        "zinye_ng.nigeria.firs.atrs.retry_failed_submissions",
        "zinye_ng.nigeria.ndpr.send_sla_warnings",
    ],
}

# ---------------------------------------------------------------------------
# Jinja environment — expose helpers to print formats
# ---------------------------------------------------------------------------
jinja = {
    "methods": [
        "zinye_ng.nigeria.utils.format_tin",
        "zinye_ng.nigeria.utils.format_naira",
    ]
}
