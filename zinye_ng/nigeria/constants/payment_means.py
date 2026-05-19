"""
FIRS e-Invoice Payment Means codes (UBL UN/ECE 4461 standard).
Source: GET base_url/api/v1/invoice/resources/payment_means
"""
from __future__ import annotations

PAYMENT_MEANS: dict[str, str] = {
    "10": "Cash",
    "20": "Cheque",
    "30": "Credit Transfer",
    "31": "Debit Transfer",
    "42": "ACH Credit",
    "43": "ACH Debit",
    "48": "Bank Card",
    "49": "Direct Debit",
    "50": "Credit Card",
    "58": "Banker's Draft",
    "97": "Other",
    "ZZZ": "Mutually Defined",
}

# ERPNext payment mode → FIRS payment means code
_ERPNEXT_TO_FIRS: dict[str, str] = {
    "Cash": "10",
    "Cheque": "20",
    "Bank Transfer": "30",
    "NEFT": "30",
    "RTGS": "30",
    "Direct Debit": "49",
    "Credit Card": "50",
    "Debit Card": "48",
}

# Default for unknown payment modes
DEFAULT_CODE = "97"


def get_payment_means_code(erpnext_mode: str | None) -> str:
    """Return FIRS payment means code for an ERPNext payment mode."""
    if not erpnext_mode:
        return DEFAULT_CODE
    return _ERPNEXT_TO_FIRS.get(erpnext_mode, DEFAULT_CODE)


def get_payment_means_label(code: str) -> str:
    return PAYMENT_MEANS.get(str(code), "Other")
