"""
Nigeria WHT Schedule Report.

Lists all Purchase Invoices where WHT was deducted, grouped by supplier.
Used for the FIRS monthly WHT remittance schedule (due by 21st of following month).

Section 51, Nigeria Tax Act 2025: rates are in regulations.
WHT credit certificates must be issued to suppliers within 30 days of remittance.
"""
from __future__ import annotations

import frappe
from frappe import _


def execute(filters=None):
    filters = frappe._dict(filters or {})
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {"label": _("Supplier"), "fieldname": "supplier", "fieldtype": "Link", "options": "Supplier", "width": 160},
        {"label": _("Supplier Name"), "fieldname": "supplier_name", "fieldtype": "Data", "width": 180},
        {"label": _("Supplier TIN"), "fieldname": "supplier_tin", "fieldtype": "Data", "width": 130},
        {"label": _("RC Number"), "fieldname": "supplier_rc", "fieldtype": "Data", "width": 120},
        {"label": _("WHT Category"), "fieldname": "wht_category", "fieldtype": "Data", "width": 200},
        {"label": _("Invoice"), "fieldname": "invoice", "fieldtype": "Link", "options": "Purchase Invoice", "width": 140},
        {"label": _("Invoice Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 100},
        {"label": _("Invoice Amount"), "fieldname": "net_total", "fieldtype": "Currency", "width": 130},
        {"label": _("WHT Rate (%)"), "fieldname": "wht_rate", "fieldtype": "Percent", "width": 110},
        {"label": _("WHT Amount"), "fieldname": "wht_amount", "fieldtype": "Currency", "width": 120},
        {"label": _("WHT Journal Entry"), "fieldname": "wht_je", "fieldtype": "Link", "options": "Journal Entry", "width": 160},
    ]


def get_data(filters):
    PurchaseInvoice = frappe.qb.DocType("Purchase Invoice")
    Supplier = frappe.qb.DocType("Supplier")

    query = (
        frappe.qb.from_(PurchaseInvoice)
        .inner_join(Supplier).on(PurchaseInvoice.supplier == Supplier.name)
        .select(
            PurchaseInvoice.name.as_("invoice"),
            PurchaseInvoice.posting_date,
            PurchaseInvoice.supplier,
            PurchaseInvoice.supplier_name,
            PurchaseInvoice.net_total,
            PurchaseInvoice.ng_wht_rate.as_("wht_rate"),
            PurchaseInvoice.ng_wht_amount.as_("wht_amount"),
            Supplier.ng_tin.as_("supplier_tin"),
            Supplier.ng_rc_number.as_("supplier_rc"),
            Supplier.ng_wht_category.as_("wht_category"),
        )
        .where(
            (PurchaseInvoice.docstatus == 1)
            & (PurchaseInvoice.ng_wht_applicable == 1)
            & (PurchaseInvoice.ng_wht_amount > 0)
        )
    )

    if filters.company:
        query = query.where(PurchaseInvoice.company == filters.company)
    if filters.from_date:
        query = query.where(PurchaseInvoice.posting_date >= filters.from_date)
    if filters.to_date:
        query = query.where(PurchaseInvoice.posting_date <= filters.to_date)
    if filters.wht_category:
        query = query.where(Supplier.ng_wht_category == filters.wht_category)

    rows = query.run(as_dict=True)
    if not rows:
        return []

    # Find linked Journal Entry for each invoice
    invoice_names = [r.invoice for r in rows]
    je_map = {}
    if invoice_names:
        je_refs = frappe.db.get_all(
            "Journal Entry",
            filters={
                "reference_doctype": "Purchase Invoice",
                "reference_docname": ["in", invoice_names],
                "docstatus": 1,
            },
            fields=["name", "reference_docname"],
        )
        je_map = {j.reference_docname: j.name for j in je_refs}

    data = []
    for row in rows:
        data.append({
            "invoice": row.invoice,
            "posting_date": row.posting_date,
            "supplier": row.supplier,
            "supplier_name": row.supplier_name,
            "supplier_tin": row.supplier_tin,
            "supplier_rc": row.supplier_rc,
            "wht_category": row.wht_category,
            "net_total": row.net_total,
            "wht_rate": row.wht_rate,
            "wht_amount": row.wht_amount,
            "wht_je": je_map.get(row.invoice, ""),
        })

    return sorted(data, key=lambda x: (x["supplier_name"], x["posting_date"]))
