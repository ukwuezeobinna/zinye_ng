"""
Thin public API for FIRS ATRS. Import from here, not from firs/.
"""
from zinye_ng.nigeria.firs.atrs import (  # noqa: F401
    submit_receipt,
    submit_pos_invoice_to_atrs,
    ATRSError,
    _get_token,
)
