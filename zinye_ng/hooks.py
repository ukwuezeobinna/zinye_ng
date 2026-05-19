app_name = "zinye_ng"
app_title = "Zinye Nigeria"
app_publisher = "Zinye"
app_description = "Nigeria compliance: PAYE, Pension, NHF, NHIS, NSITF, ITF, VAT, WHT, NRS ATRS, FIRSMBS e-invoicing, NDPR"
app_email = "dev@zinye.com"
app_license = "MIT"
app_version = "0.2.0"

required_apps = ["frappe", "erpnext", "hrms", "zinye_core"]

# ---------------------------------------------------------------------------
# Installation hooks
# ---------------------------------------------------------------------------
after_install = "zinye_ng.nigeria.setup.after_install"
after_migrate = "zinye_ng.nigeria.setup.after_migrate"
before_uninstall = "zinye_ng.nigeria.setup.before_uninstall"

# ---------------------------------------------------------------------------
# Fixtures — reference data only (NOT custom fields — those are programmatic)
# See: zinye_ng.nigeria.setup.create_nigeria_custom_fields()
# ---------------------------------------------------------------------------
fixtures = [
    # Payroll bands (NTA 2025, effective 1 Jan 2026)
    {"dt": "Income Tax Slab", "filters": [["name", "in", ["Nigeria PAYE 2026"]]]},
    # Statutory salary components
    {
        "dt": "Salary Component",
        "filters": [["name", "in", [
            "NG - Basic Salary", "NG - Housing Allowance", "NG - Transport Allowance",
            "NG - Pensionable Base", "NG - Pension Employee", "NG - Pension Employer",
            "NG - NHF", "NG - NHIS", "NG - NSITF", "NG - ITF", "NG - PAYE Tax",
        ]]],
    },
    # Nigeria workspace (home screen tile)
    {"doctype": "Workspace", "filters": [["name", "=", "Nigeria"]]},
]

# ---------------------------------------------------------------------------
# Extend doctype classes (v16 mixin pattern) — adds form button methods only.
# Lifecycle logic stays in doc_events below.
# ---------------------------------------------------------------------------
extend_doctype_class = {
    "Sales Invoice": "zinye_ng.nigeria.overrides.sales_invoice.NigeriaSalesInvoiceMixin",
    "Purchase Invoice": "zinye_ng.nigeria.overrides.purchase_invoice.NigeriaPurchaseInvoiceMixin",
}

# ---------------------------------------------------------------------------
# Client-side scripts
# ---------------------------------------------------------------------------
doctype_js = {
    "Sales Invoice": "public/js/sales_invoice.js",
    "Purchase Invoice": "public/js/purchase_invoice.js",
    "Nigeria Compliance Settings": "public/js/nigeria_compliance_settings.js",
}

# ---------------------------------------------------------------------------
# Doc events — all business logic here, not in extend_doctype_class
# ---------------------------------------------------------------------------
doc_events = {
    "Sales Invoice": {
        "validate":      "zinye_ng.nigeria.overrides.transaction.validate_ng_fields",
        "before_submit": "zinye_ng.nigeria.overrides.transaction.before_submit_ng",
        "on_submit":     "zinye_ng.nigeria.firs.hooks.on_sales_invoice_submit",
        "before_cancel": "zinye_ng.nigeria.firs.hooks.before_sales_invoice_cancel",
        "on_cancel":     "zinye_ng.nigeria.firs.hooks.on_sales_invoice_cancel",
    },
    "POS Invoice": {
        "on_submit": "zinye_ng.nigeria.firs.hooks.on_pos_invoice_submit",
    },
    "Purchase Invoice": {
        "validate":  "zinye_ng.nigeria.tax.wht.validate_wht",
        "on_submit": "zinye_ng.nigeria.tax.wht.on_purchase_invoice_submit",
    },
    "Salary Slip": {
        "validate": "zinye_ng.nigeria.payroll.salary_slip.on_validate",
    },
    "Nigeria Data Subject Request": {
        "after_insert": "zinye_ng.nigeria.ndpr.on_data_subject_request_insert",
    },
}

# ---------------------------------------------------------------------------
# Scheduled jobs
# ---------------------------------------------------------------------------
scheduler_events = {
    "cron": {
        # Every 5 min: retry Auto-Retry e-invoices (mirrors india_compliance pattern)
        "*/5 * * * *": [
            "zinye_ng.nigeria.firs.scheduled.retry_pending_einvoices",
        ],
    },
    "hourly": [
        "zinye_ng.nigeria.firs.scheduled.poll_pending_einvoices",
    ],
    "daily": [
        "zinye_ng.nigeria.firs.scheduled.retry_failed_atrs",
        "zinye_ng.nigeria.firs.scheduled.sync_firs_resources",
        "zinye_ng.nigeria.ndpr.send_sla_warnings",
    ],
}

# ---------------------------------------------------------------------------
# Jinja helpers for print formats
# ---------------------------------------------------------------------------
jinja = {
    "methods": [
        "zinye_ng.nigeria.utils.format_tin",
        "zinye_ng.nigeria.utils.format_naira",
        "zinye_ng.nigeria.utils.is_einvoice_enabled",
    ]
}
