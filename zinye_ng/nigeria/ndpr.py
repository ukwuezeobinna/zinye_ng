"""
NDPR (Nigeria Data Protection Regulation) Data Subject Request handling.

The NDPR (2019, revised 2023) requires controllers to respond to data subject
requests within 30 days. This module:
  1. Sets the 30-day deadline on insert (also handled by the DocType controller)
  2. Sends daily SLA warnings for requests approaching or past the 30-day limit

Notification recipients: HR Manager + System Manager roles.
"""
from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import add_days, date_diff, getdate, today


_WARN_DAYS_BEFORE = 5  # warn when ≤5 days remain


def on_data_subject_request_insert(doc, method=None):
    """Ensure 30-day deadline is set and send acknowledgement email."""
    if not doc.deadline:
        frappe.db.set_value(
            "Nigeria Data Subject Request",
            doc.name,
            "deadline",
            add_days(doc.received_on, 30),
        )

    _send_acknowledgement(doc)


def send_sla_warnings():
    """
    Daily job: warn on open requests where deadline is within _WARN_DAYS_BEFORE days
    or already breached.

    Called from: scheduler_events.daily in hooks.py
    """
    today_date = getdate(today())
    open_requests = frappe.get_all(
        "Nigeria Data Subject Request",
        filters={"status": ["in", ["Open", "In Progress"]]},
        fields=["name", "subject_name", "subject_email", "deadline", "received_on"],
    )

    for req in open_requests:
        if not req.deadline:
            continue
        days_remaining = date_diff(req.deadline, today_date)
        if days_remaining <= _WARN_DAYS_BEFORE:
            _send_sla_warning(req, days_remaining)


def _send_sla_warning(req, days_remaining: int):
    """Send SLA warning to HR Manager users."""
    if days_remaining < 0:
        subject = f"[NDPR BREACH] Data Subject Request {req.name} — {abs(days_remaining)} days overdue"
        indicator = "🔴"
    else:
        subject = f"[NDPR] Data Subject Request {req.name} — {days_remaining} days remaining"
        indicator = "🟡"

    recipients = _get_hr_manager_emails()
    if not recipients:
        return

    message = frappe.render_template(
        """
        <p>{{ indicator }} NDPR SLA Alert</p>
        <p><strong>Request:</strong> {{ req.name }}<br>
           <strong>Subject:</strong> {{ req.subject_name }} ({{ req.subject_email }})<br>
           <strong>Received:</strong> {{ req.received_on }}<br>
           <strong>Deadline:</strong> {{ req.deadline }}<br>
           <strong>Status:</strong>
           {% if days_remaining < 0 %}
             BREACHED — {{ days_remaining | abs }} days overdue
           {% else %}
             {{ days_remaining }} days remaining
           {% endif %}
        </p>
        <p>
          <a href="{{ frappe.utils.get_url_to_form('Nigeria Data Subject Request', req.name) }}">
            Open Request in ERPNext
          </a>
        </p>
        """,
        {"req": req, "days_remaining": days_remaining, "indicator": indicator},
    )

    frappe.sendmail(
        recipients=recipients,
        subject=subject,
        message=message,
        now=True,
    )


def _send_acknowledgement(doc):
    """Send acknowledgement email to the data subject."""
    if not doc.subject_email:
        return

    frappe.sendmail(
        recipients=[doc.subject_email],
        subject=f"Your data request has been received — Ref: {doc.name}",
        message=frappe.render_template(
            """
            <p>Dear {{ doc.subject_name }},</p>
            <p>We have received your <strong>{{ doc.request_type }}</strong> request
               (Reference: <strong>{{ doc.name }}</strong>) on {{ doc.received_on }}.</p>
            <p>Under the Nigeria Data Protection Regulation (NDPR), we are required to
               respond within <strong>30 days</strong>. Your response deadline is
               <strong>{{ doc.deadline }}</strong>.</p>
            <p>If you have any questions, please reply to this email.</p>
            """,
            {"doc": doc},
        ),
        now=True,
    )


def _get_hr_manager_emails() -> list[str]:
    return frappe.get_all(
        "Has Role",
        filters={"role": "HR Manager", "parenttype": "User"},
        fields=["parent"],
        pluck="parent",
    )
