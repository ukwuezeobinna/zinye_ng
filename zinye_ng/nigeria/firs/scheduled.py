"""
Scheduled background jobs for FIRS integrations.
Registered under scheduler_events in hooks.py.

Retry architecture (3 layers, mirrors india_compliance):
  Layer 1 - on_submit: validation error → "Failed" (no retry)
  Layer 2 - on_submit: server/network error → "Auto-Retry" + set is_retry_einvoice_pending=1
  Layer 3 - cron */5 min: check flag, find all "Auto-Retry", re-submit
"""
from __future__ import annotations

import frappe
from frappe.utils import add_days, now_datetime


def retry_pending_einvoices():
    """
    Every 5 minutes: re-submit all Auto-Retry e-invoices.
    The is_retry_einvoice_pending flag prevents unnecessary DB queries on quiet intervals.
    """
    try:
        settings = frappe.get_cached_doc("Nigeria Compliance Settings")
    except Exception:
        return

    if not settings.einvoice_enabled:
        return

    if not settings.is_retry_einvoice_pending:
        return

    # Clear the flag first so failed retries don't endlessly accumulate
    settings.db_set("is_retry_einvoice_pending", 0, update_modified=False)

    pending = frappe.get_all(
        "Nigeria E-Invoice",
        filters={
            "status": "Auto-Retry",
            "creation": [">=", add_days(now_datetime(), -3)],
        },
        fields=["name", "sales_invoice", "retry_count", "max_retries"],
    )

    from zinye_ng.nigeria.firs.einvoice import submit_invoice

    for record in pending:
        max_r = record.max_retries or 3
        if (record.retry_count or 0) >= max_r:
            # Hit max retries — move to Failed permanently
            frappe.db.set_value("Nigeria E-Invoice", record.name, "status", "Failed")
            frappe.db.set_value(
                "Sales Invoice", record.sales_invoice, "ng_firs_status", "Failed"
            )
            frappe.db.commit()
            continue

        try:
            submit_invoice(record.sales_invoice)
        except Exception as e:
            frappe.log_error(
                f"e-Invoice retry failed for {record.sales_invoice}: {e}",
                "FIRSMBS Retry",
            )
        finally:
            frappe.db.commit()


def poll_pending_einvoices():
    """
    Hourly: poll FIRSMBS for final IRN status on Submitted e-invoices.
    FIRS has up to 2 hours to validate and issue final clearance.
    """
    try:
        settings = frappe.get_cached_doc("Nigeria Compliance Settings")
    except Exception:
        return

    if not settings.einvoice_enabled:
        return

    pending = frappe.get_all(
        "Nigeria E-Invoice",
        filters={"status": "Submitted"},
        fields=["name", "irn", "sales_invoice"],
    )

    from zinye_ng.nigeria.firs.einvoice import check_irn_status

    for record in pending:
        if not record.irn:
            continue
        try:
            result = check_irn_status(record.irn)
            status = (result.get("status") or result.get("Status") or "").lower()
            if status in ("cleared", "valid", "approved"):
                frappe.db.set_value("Nigeria E-Invoice", record.name, {
                    "status": "Cleared",
                    "cleared_at": now_datetime(),
                })
                frappe.db.set_value(
                    "Sales Invoice", record.sales_invoice, "ng_firs_status", "Cleared"
                )
        except Exception as e:
            frappe.log_error(
                f"IRN poll failed for {record.irn}: {e}",
                "FIRSMBS IRN Poll",
            )

    if pending:
        frappe.db.commit()


def retry_failed_atrs():
    """
    Daily: retry Failed ATRS submissions from the last 24 hours.
    """
    try:
        settings = frappe.get_cached_doc("Nigeria Compliance Settings")
    except Exception:
        return

    if not settings.atrs_enabled:
        return

    yesterday = add_days(now_datetime(), -1)
    failed = frappe.get_all(
        "Nigeria ATRS Log",
        filters={"status": "Failed", "creation": [">=", yesterday]},
        fields=["name", "document_name"],
    )

    from zinye_ng.nigeria.firs.atrs import submit_pos_invoice_to_atrs

    for log in failed:
        try:
            submit_pos_invoice_to_atrs(log.document_name)
        except Exception as e:
            frappe.log_error(
                f"ATRS retry failed for {log.document_name}: {e}",
                "FIRS ATRS Retry",
            )
        finally:
            frappe.db.commit()
