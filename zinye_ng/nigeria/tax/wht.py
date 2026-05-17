"""
Withholding Tax (WHT) on Purchase Invoice.

Section 51, Nigeria Tax Act 2025: WHT rates are prescribed in regulations
(not fixed in the statute). Rates are therefore stored in a WHT Rate table
linked to the supplier's WHT category.

On Purchase Invoice submission:
  1. Check if custom_ng_wht_applicable is ticked
  2. Look up WHT rate from supplier's WHT category (fallback: invoice rate field)
  3. Compute WHT amount = taxable amount × rate
  4. Create a Journal Entry: Dr Payable / Cr WHT Payable
  5. Link the JE to the Purchase Invoice for reconciliation

The JE is the mechanism — the invoice itself is not modified after submission.
"""
from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import flt, nowdate


# Default WHT rates while awaiting updated regulations (old FIRS schedule)
DEFAULT_WHT_RATES: dict[str, float] = {
    "Professional / Consultancy Fees": 10.0,
    "Management / Technical Fees": 10.0,
    "Construction / Building": 5.0,
    "Rent / Lease": 10.0,
    "Royalties": 10.0,
    "Dividends": 10.0,
    "Interest (Financial Institution)": 10.0,
    "Commission / Agency Fees": 10.0,
    "Contracts (Supply of Goods)": 5.0,
    "Directors Fees": 10.0,
}

# Non-resident services to startups: 5% final withholding (s.51(8) Nigeria Tax Act 2025)
NON_RESIDENT_STARTUP_RATE = 5.0


def on_purchase_invoice_submit(doc, method=None):
    """
    Create WHT Journal Entry when Purchase Invoice is submitted.

    Checks the custom_ng_wht_applicable flag set by the user on the invoice.
    If applicable, computes WHT and creates a JE against the payable account.
    """
    if not doc.get("custom_ng_wht_applicable"):
        return

    wht_rate = _get_wht_rate(doc)
    if not wht_rate:
        frappe.log_error(
            f"WHT rate not found for Purchase Invoice {doc.name} (supplier: {doc.supplier})",
            "Nigeria WHT",
        )
        return

    taxable_amount = flt(doc.net_total)
    wht_amount = round(taxable_amount * (wht_rate / 100), 2)

    if wht_amount <= 0:
        return

    _update_invoice_wht_fields(doc, wht_rate, wht_amount)
    _create_wht_journal_entry(doc, wht_amount)


def _get_wht_rate(doc) -> float:
    """
    Resolve WHT rate: invoice field → supplier category → default schedule.
    Returns 0.0 if no rate can be determined.
    """
    # If the user explicitly set the rate on the invoice, use it
    invoice_rate = flt(doc.get("custom_ng_wht_rate"))
    if invoice_rate > 0:
        return invoice_rate

    # Look up supplier's WHT category
    wht_category = frappe.db.get_value("Supplier", doc.supplier, "custom_ng_wht_category")
    if wht_category and wht_category in DEFAULT_WHT_RATES:
        return DEFAULT_WHT_RATES[wht_category]

    return 0.0


def _update_invoice_wht_fields(doc, rate: float, amount: float):
    """Write WHT rate and amount back to the invoice record (read-only display fields)."""
    frappe.db.set_value(
        "Purchase Invoice",
        doc.name,
        {
            "custom_ng_wht_rate": rate,
            "custom_ng_wht_amount": amount,
        },
    )


def _create_wht_journal_entry(doc, wht_amount: float):
    """
    Create Journal Entry:
      Dr  Accounts Payable (supplier)    wht_amount
      Cr  WHT Payable (liability)        wht_amount

    This reduces the net disbursement to the supplier by the WHT amount.
    """
    wht_account = doc.get("custom_ng_wht_account")
    if not wht_account:
        # Try to find WHT payable account from company's chart of accounts
        wht_account = frappe.db.get_value(
            "Account",
            {"account_name": ["like", "%WHT Payable%"], "company": doc.company},
            "name",
        )

    if not wht_account:
        frappe.log_error(
            f"WHT Payable account not configured for company {doc.company}. "
            f"Create an account named 'WHT Payable' or set it on Purchase Invoice {doc.name}.",
            "Nigeria WHT",
        )
        return

    payable_account = _get_payable_account(doc)

    je = frappe.new_doc("Journal Entry")
    je.voucher_type = "Journal Entry"
    je.posting_date = doc.posting_date or nowdate()
    je.company = doc.company
    je.user_remark = f"WHT on Purchase Invoice {doc.name} — {doc.supplier}"
    je.reference_doctype = "Purchase Invoice"
    je.reference_docname = doc.name

    je.append("accounts", {
        "account": payable_account,
        "party_type": "Supplier",
        "party": doc.supplier,
        "debit_in_account_currency": wht_amount,
        "credit_in_account_currency": 0,
        "reference_type": "Purchase Invoice",
        "reference_name": doc.name,
    })
    je.append("accounts", {
        "account": wht_account,
        "credit_in_account_currency": wht_amount,
        "debit_in_account_currency": 0,
    })

    je.flags.ignore_permissions = True
    je.insert()
    je.submit()

    frappe.msgprint(
        _("WHT Journal Entry {0} created for ₦{1:,.2f}").format(je.name, wht_amount),
        indicator="green",
        alert=True,
    )


def _get_payable_account(doc) -> str:
    """Find the payable account for the supplier from the Purchase Invoice."""
    # ERPNext stores the payable account on the invoice
    if doc.credit_to:
        return doc.credit_to

    # Fallback: look up default payable from company
    return frappe.get_cached_value("Company", doc.company, "default_payable_account")
