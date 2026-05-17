import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, today


class NigeriaDataSubjectRequest(Document):
    def before_insert(self):
        # NDPR requires response within 30 days
        if not self.deadline:
            self.deadline = add_days(self.received_on or today(), 30)

    def on_update(self):
        if self.status in ("Completed", "Rejected") and not self.closed_on:
            self.db_set("closed_on", today())
        if self.status in ("Completed", "Rejected") and not self.responded_by:
            self.db_set("responded_by", frappe.session.user)
