"""
Thin public API for FIRSMBS e-invoicing. Import from here, not from firs/.
"""
from zinye_ng.nigeria.firs.einvoice import (  # noqa: F401
    submit_invoice,
    submit_invoice_enqueued,
    cancel_invoice,
    check_irn_status,
    build_invoice_payload,
    EInvoiceError,
    EInvoiceNotConfigured,
)
