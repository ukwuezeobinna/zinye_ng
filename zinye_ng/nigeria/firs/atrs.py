"""
FIRS ATRS background jobs.

retry_failed_submissions: daily scheduled job — retries ATRS log entries
that have status=Failed from the past 24 hours.
"""
from __future__ import annotations

import frappe
from frappe.utils import add_days, now_datetime

from zinye_ng.nigeria.atrs import submit_pos_invoice_to_atrs, ATRSError


def retry_failed_submissions():
    """
    Retry all failed ATRS submissions from the last 24 hours.
    Called from: scheduler_events.daily in hooks.py.
    """
    yesterday = add_days(now_datetime(), -1)
    failed_logs = frappe.get_all(
        "NRS ATRS Log",
        filters={
            "status": "Failed",
            "document_type": "POS Invoice",
            "creation": [">=", yesterday],
        },
        fields=["name", "document_name"],
    )

    for log in failed_logs:
        try:
            result = submit_pos_invoice_to_atrs(log.document_name)
            if result.get("payment_code"):
                frappe.db.set_value(
                    "NRS ATRS Log",
                    log.name,
                    {"status": "Submitted", "submitted_at": now_datetime()},
                )
        except ATRSError as e:
            frappe.log_error(
                f"ATRS retry failed for POS Invoice {log.document_name}: {e}",
                "FIRS ATRS Retry",
            )

    if failed_logs:
        frappe.db.commit()
