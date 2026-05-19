"""
FIRS e-Invoice invoice type codes (UBL UN/ECE 1001 standard).
Source: https://einvoice.firs.gov.ng/docs/resources/get-invoice-type?version=1.1
Endpoint: GET /api/v1/invoice/resources/invoice-types
"""
from __future__ import annotations

# Full code → label map (from FIRS API)
INVOICE_TYPE_CODES: dict[str, str] = {
    "380": "Credit Note",
    "381": "Commercial Invoice",
    "384": "Debit Note",
    "385": "Self Billed Invoice",
    "386": "Factored Invoice",
    "388": "Statement of Account",
    "389": "Purchase Order",
    "390": "Proforma Invoice",
    "392": "Consignment Invoice",
    "393": "Self-billed Credit Note",
    "394": "Self-billed Invoice",
    "395": "Credit Note Request",
    "396": "Invoice Request",
    "397": "Final Settlement",
    "399": "Bill of Lading",
    "400": "Waybill",
    "402": "Shipping Instructions",
    "404": "Certificate of Origin",
    "406": "Customs Declaration",
    "408": "Packing List",
}

# ERPNext doctype + is_return context → FIRS invoice type code
# Sales Invoice (normal)   → 381 Commercial Invoice
# Sales Invoice (return)   → 380 Credit Note
# Sales Invoice (debit)    → 384 Debit Note
# POS Invoice              → 381 Commercial Invoice
_ERPNEXT_TO_FIRS: dict[tuple[str, bool, bool], str] = {
    ("Sales Invoice", False, False): "381",  # normal sale
    ("Sales Invoice", True,  False): "380",  # is_return=1 → credit note
    ("Sales Invoice", False, True):  "384",  # is_debit_note=1 → debit note
    ("POS Invoice",   False, False): "381",
    ("POS Invoice",   True,  False): "380",
}


def get_invoice_type_code(doctype: str, is_return: bool = False, is_debit_note: bool = False) -> str:
    """
    Return the FIRS UBL invoice type code for an ERPNext document.
    Defaults to 381 (Commercial Invoice) for unmapped types.
    """
    return _ERPNEXT_TO_FIRS.get((doctype, is_return, is_debit_note), "381")


def get_invoice_type_label(code: str) -> str:
    return INVOICE_TYPE_CODES.get(code, "Commercial Invoice")
