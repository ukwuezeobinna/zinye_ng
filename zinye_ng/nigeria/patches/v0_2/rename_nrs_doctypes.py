"""
v0.2: Rename NRS ATRS Log → Nigeria ATRS Log.
Migrate NRS ATRS Settings + NRS E-Invoice Settings data into Nigeria Compliance Settings.
"""
from __future__ import annotations

import frappe


def execute():
    _rename_atrs_log()
    _migrate_atrs_settings()
    _migrate_einvoice_settings()
    frappe.db.commit()


def _rename_atrs_log():
    if not frappe.db.exists("DocType", "NRS ATRS Log"):
        return
    if frappe.db.exists("DocType", "Nigeria ATRS Log"):
        return  # already renamed

    frappe.rename_doc("DocType", "NRS ATRS Log", "Nigeria ATRS Log", force=True)
    frappe.clear_cache()


def _migrate_atrs_settings():
    if not frappe.db.exists("DocType", "NRS ATRS Settings"):
        return

    atrs = frappe.get_single("NRS ATRS Settings")
    settings = frappe.get_single("Nigeria Compliance Settings")

    settings.atrs_enabled = atrs.get("enabled") or 0
    settings.atrs_environment = atrs.get("environment") or "Development"
    settings.atrs_vat_number = atrs.get("vat_number") or ""
    settings.atrs_business_place = atrs.get("business_place") or ""
    settings.atrs_business_device = atrs.get("business_device") or ""
    settings.atrs_client_id = atrs.get("client_id") or ""
    settings.atrs_username = atrs.get("username") or ""

    # Copy passwords via raw SQL (Password fields encrypted, can't copy via .get_password cross-doc)
    for old_field, new_field in [
        ("client_secret", "atrs_client_secret"),
        ("atrs_password", "atrs_password"),
    ]:
        raw = frappe.db.get_value("NRS ATRS Settings", "NRS ATRS Settings", old_field)
        if raw:
            frappe.db.set_value("Nigeria Compliance Settings", "Nigeria Compliance Settings", new_field, raw)

    settings.save(ignore_permissions=True)


def _migrate_einvoice_settings():
    if not frappe.db.exists("DocType", "NRS E-Invoice Settings"):
        return

    einv = frappe.get_single("NRS E-Invoice Settings")
    settings = frappe.get_single("Nigeria Compliance Settings")

    settings.einvoice_enabled = einv.get("enabled") or 0
    settings.einvoice_environment = einv.get("environment") or "Sandbox"
    settings.einvoice_sandbox_url = einv.get("sandbox_url") or ""
    settings.einvoice_production_url = einv.get("production_url") or ""
    settings.einvoice_client_id = einv.get("client_id") or ""

    for old_field, new_field in [
        ("client_secret", "einvoice_client_secret"),
        ("api_key", "einvoice_api_key"),
    ]:
        raw = frappe.db.get_value("NRS E-Invoice Settings", "NRS E-Invoice Settings", old_field)
        if raw:
            frappe.db.set_value("Nigeria Compliance Settings", "Nigeria Compliance Settings", new_field, raw)

    settings.save(ignore_permissions=True)
