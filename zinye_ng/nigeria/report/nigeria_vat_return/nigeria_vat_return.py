"""
Nigeria VAT Return Report.

Produces a monthly VAT Return summary matching the FIRS VAT Form 002.

Sections:
  A. Output VAT — VAT collected on Sales Invoices (taxable supplies)
  B. Input VAT  — VAT paid on Purchase Invoices (claimable if registered)
  C. VAT Payable — Output VAT minus Input VAT (remit by 21st of following month)

Section 147 Nigeria Tax Act 2025: rate is 7.5%.
Section 148-149: VAT-exempt supplies (food, educational materials, medical supplies,
books, baby products, exported services). Exempt lines are listed separately.
"""
from __future__ import annotations

import frappe
from frappe import _


_VAT_RATE = 7.5


def execute(filters=None):
    filters = frappe._dict(filters or {})
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {"label": _("Type"), "fieldname": "type", "fieldtype": "Data", "width": 120},
        {"label": _("Document"), "fieldname": "document", "fieldtype": "Dynamic Link", "options": "doctype", "width": 160},
        {"label": _("Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 100},
        {"label": _("Party"), "fieldname": "party", "fieldtype": "Data", "width": 180},
        {"label": _("TIN"), "fieldname": "tin", "fieldtype": "Data", "width": 130},
        {"label": _("Net Amount"), "fieldname": "net_amount", "fieldtype": "Currency", "width": 130},
        {"label": _("VAT Amount"), "fieldname": "vat_amount", "fieldtype": "Currency", "width": 120},
        {"label": _("Grand Total"), "fieldname": "grand_total", "fieldtype": "Currency", "width": 130},
        {"label": _("Doctype"), "fieldname": "doctype", "fieldtype": "Data", "hidden": 1},
    ]


def get_data(filters):
    data = []

    # Output VAT (Sales Invoices)
    output_rows = _get_output_vat(filters)
    data.extend(output_rows)

    # Summary row for output VAT
    output_total = sum(r["vat_amount"] for r in output_rows)
    data.append({
        "type": _("Output VAT Total"),
        "vat_amount": output_total,
        "net_amount": sum(r["net_amount"] for r in output_rows),
        "grand_total": sum(r["grand_total"] for r in output_rows),
        "bold": 1,
    })

    # Input VAT (Purchase Invoices)
    if filters.get("include_purchase_vat"):
        input_rows = _get_input_vat(filters)
        data.extend(input_rows)

        input_total = sum(r["vat_amount"] for r in input_rows)
        data.append({
            "type": _("Input VAT Total"),
            "vat_amount": input_total,
            "net_amount": sum(r["net_amount"] for r in input_rows),
            "grand_total": sum(r["grand_total"] for r in input_rows),
            "bold": 1,
        })

        # VAT Payable
        data.append({
            "type": _("VAT Payable"),
            "vat_amount": output_total - input_total,
            "bold": 1,
        })

    return data


def _get_output_vat(filters) -> list[dict]:
    SalesInvoice = frappe.qb.DocType("Sales Invoice")
    SalesTax = frappe.qb.DocType("Sales Taxes and Charges")

    query = (
        frappe.qb.from_(SalesInvoice)
        .inner_join(SalesTax).on(SalesInvoice.name == SalesTax.parent)
        .select(
            SalesInvoice.name,
            SalesInvoice.posting_date,
            SalesInvoice.customer_name,
            SalesInvoice.net_total,
            SalesInvoice.grand_total,
            SalesTax.tax_amount,
            SalesTax.rate,
        )
        .where(
            (SalesInvoice.docstatus == 1)
            & (SalesTax.parenttype == "Sales Invoice")
            & (SalesTax.description.like("%VAT%"))
        )
    )

    query = _apply_date_filters(query, SalesInvoice, filters)

    rows = query.run(as_dict=True)
    return [
        {
            "type": _("Output"),
            "doctype": "Sales Invoice",
            "document": r.name,
            "posting_date": r.posting_date,
            "party": r.customer_name,
            "tin": frappe.db.get_value("Sales Invoice", r.name, "customer") and
                   frappe.db.get_value("Customer", frappe.db.get_value("Sales Invoice", r.name, "customer"), "custom_ng_tin") or "",
            "net_amount": r.net_total,
            "vat_amount": r.tax_amount,
            "grand_total": r.grand_total,
        }
        for r in rows
    ]


def _get_input_vat(filters) -> list[dict]:
    PurchaseInvoice = frappe.qb.DocType("Purchase Invoice")
    PurchaseTax = frappe.qb.DocType("Purchase Taxes and Charges")

    query = (
        frappe.qb.from_(PurchaseInvoice)
        .inner_join(PurchaseTax).on(PurchaseInvoice.name == PurchaseTax.parent)
        .select(
            PurchaseInvoice.name,
            PurchaseInvoice.posting_date,
            PurchaseInvoice.supplier_name,
            PurchaseInvoice.net_total,
            PurchaseInvoice.grand_total,
            PurchaseTax.tax_amount,
        )
        .where(
            (PurchaseInvoice.docstatus == 1)
            & (PurchaseTax.parenttype == "Purchase Invoice")
            & (PurchaseTax.description.like("%VAT%"))
        )
    )

    query = _apply_date_filters(query, PurchaseInvoice, filters)

    rows = query.run(as_dict=True)
    return [
        {
            "type": _("Input"),
            "doctype": "Purchase Invoice",
            "document": r.name,
            "posting_date": r.posting_date,
            "party": r.supplier_name,
            "tin": "",
            "net_amount": r.net_total,
            "vat_amount": r.tax_amount,
            "grand_total": r.grand_total,
        }
        for r in rows
    ]


def _apply_date_filters(query, doctype, filters):
    if filters.company:
        query = query.where(doctype.company == filters.company)
    if filters.from_date:
        query = query.where(doctype.posting_date >= filters.from_date)
    if filters.to_date:
        query = query.where(doctype.posting_date <= filters.to_date)
    return query
