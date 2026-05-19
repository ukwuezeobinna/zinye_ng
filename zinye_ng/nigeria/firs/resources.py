"""
FIRS e-Invoice reference data sync.

Large reference tables from the FIRS resources API are fetched once
and cached in Redis for 24 hours. Small static tables live in constants/.

Resources handled here (Tier 2 — Redis cached):
  - countries         (GET /api/v1/invoice/resources/countries)
  - currencies        (GET /api/v1/invoice/resources/currencies)
  - LGAs              (GET /api/v1/invoice/resources/lgas)
  - quantity codes    (GET /api/v1/invoice/resources/invoice-quantity-codes)

Resources handled in constants/ (Tier 1 — Python dicts, no network):
  - invoice types, payment means, tax categories, states

Resources handled in DocTypes (Tier 3 — DB, user-browsable):
  - HS codes          → Nigeria FIRS HS Code DocType
  - service codes     → Nigeria FIRS Service Code DocType
"""
from __future__ import annotations

import frappe
import requests

from zinye_ng.nigeria.firs.einvoice import _base_url, _headers, _get_settings  # noqa: E402

_CACHE_TTL = 86400  # 24 hours

_RESOURCE_PATHS: dict[str, str] = {
    "countries": "/api/v1/invoice/resources/countries",
    "currencies": "/api/v1/invoice/resources/currencies",
    "lgas": "/api/v1/invoice/resources/lgas",
    "quantity_codes": "/api/v1/invoice/resources/invoice-quantity-codes",
}


@frappe.whitelist()
def sync_firs_resources(force: bool = False):
    """
    Fetch all Tier-2 reference resources from FIRS and cache in Redis.
    Called by daily scheduler. Pass force=True to bypass TTL check.
    """
    settings = _get_settings()
    if not settings.einvoice_enabled:
        return

    for key, path in _RESOURCE_PATHS.items():
        cache_key = f"zinye_ng:firs_resource:{key}"
        if not force and frappe.cache.get_value(cache_key):
            continue

        try:
            resp = requests.get(
                f"{_base_url(settings)}{path}",
                headers=_headers(settings),
                timeout=30,
            )
            if resp.ok:
                frappe.cache.set_value(cache_key, resp.json(), expires_in_sec=_CACHE_TTL)
            else:
                frappe.log_error(
                    f"FIRS resource sync failed for {key}: [{resp.status_code}] {resp.text}",
                    "FIRS Resource Sync",
                )
        except Exception as e:
            frappe.log_error(str(e), f"FIRS Resource Sync ({key})")


def get_countries() -> list[dict]:
    cached = frappe.cache.get_value("zinye_ng:firs_resource:countries")
    return cached or []


def get_currencies() -> list[dict]:
    cached = frappe.cache.get_value("zinye_ng:firs_resource:currencies")
    return cached or []


def get_lgas(state_code: str | None = None) -> list[dict]:
    """Return LGAs, optionally filtered by FIRS state code (e.g. 'NG-LA')."""
    cached = frappe.cache.get_value("zinye_ng:firs_resource:lgas") or []
    if state_code:
        return [lga for lga in cached if lga.get("stateCode") == state_code]
    return cached


def get_quantity_codes() -> list[dict]:
    cached = frappe.cache.get_value("zinye_ng:firs_resource:quantity_codes")
    return cached or []


def get_country_code(alpha_2: str) -> dict | None:
    """Look up a country by ISO alpha-2 code (e.g. 'NG')."""
    for c in get_countries():
        if c.get("alpha_2") == alpha_2:
            return c
    return None


def get_currency(code: str) -> dict | None:
    """Look up a currency by code (e.g. 'NGN')."""
    for c in get_currencies():
        if c.get("code") == code:
            return c
    return None


def get_quantity_code(uom_name: str) -> str:
    """
    Map an ERPNext Unit of Measure name to a FIRS quantity code.
    Falls back to 'EA' (each) if no match found.
    """
    # Common UOM → UBL code mappings
    _UOM_MAP: dict[str, str] = {
        "Nos": "EA",
        "Unit": "EA",
        "Each": "EA",
        "Kg": "KGM",
        "Gram": "GRM",
        "Litre": "LTR",
        "Meter": "MTR",
        "Box": "BX",
        "Dozen": "DZN",
        "Hour": "HUR",
        "Day": "DAY",
        "Month": "MON",
        "Year": "ANN",
        "Tonne": "TNE",
        "Piece": "PCE",
        "Set": "SET",
        "Pair": "PR",
        "Pack": "PK",
        "Roll": "RO",
        "Sheet": "ST",
        "Bag": "BG",
    }
    return _UOM_MAP.get(uom_name, "EA")


# ── Tier 3: HS Code + Service Code DocType sync ───────────────────────────────

@frappe.whitelist()
def sync_hs_codes():
    """
    Sync HS product codes from FIRS into the Nigeria FIRS HS Code DocType.
    Called manually from Nigeria Compliance Settings → Actions, or by weekly scheduler.
    Creates/updates records in bulk.
    """
    settings = _get_settings()
    if not settings.einvoice_enabled:
        frappe.msgprint("e-Invoice is not enabled.", indicator="orange", alert=True)
        return {"synced": 0}

    resp = requests.get(
        f"{_base_url(settings)}/api/v1/invoice/resources/hs-codes",
        headers=_headers(settings),
        timeout=60,
    )
    if not resp.ok:
        frappe.throw(f"FIRS HS Code sync failed [{resp.status_code}]: {resp.text}")

    data = resp.json()
    if isinstance(data, dict):
        items = data.get("data") or data.get("result") or list(data.values())
    else:
        items = data

    count = 0
    for item in items:
        code = str(item.get("code") or item.get("Code") or "").strip()
        description = str(item.get("description") or item.get("Description") or "").strip()
        if not code:
            continue

        if frappe.db.exists("Nigeria FIRS HS Code", code):
            frappe.db.set_value("Nigeria FIRS HS Code", code, "description", description)
        else:
            frappe.get_doc({
                "doctype": "Nigeria FIRS HS Code",
                "name": code,
                "hs_code": code,
                "description": description,
            }).insert(ignore_permissions=True)
        count += 1

    frappe.db.commit()
    frappe.msgprint(f"Synced {count} HS codes from FIRS.", indicator="green", alert=True)
    return {"synced": count}


@frappe.whitelist()
def sync_service_codes():
    """
    Sync service codes from FIRS into the Nigeria FIRS Service Code DocType.
    """
    settings = _get_settings()
    if not settings.einvoice_enabled:
        frappe.msgprint("e-Invoice is not enabled.", indicator="orange", alert=True)
        return {"synced": 0}

    resp = requests.get(
        f"{_base_url(settings)}/api/v1/invoice/resources/services-codes",
        headers=_headers(settings),
        timeout=60,
    )
    if not resp.ok:
        frappe.throw(f"FIRS Service Code sync failed [{resp.status_code}]: {resp.text}")

    data = resp.json()
    if isinstance(data, dict):
        items = data.get("data") or data.get("result") or list(data.values())
    else:
        items = data

    count = 0
    for item in items:
        code = str(item.get("code") or item.get("Code") or "").strip()
        description = str(item.get("description") or item.get("Description") or "").strip()
        if not code:
            continue

        if frappe.db.exists("Nigeria FIRS Service Code", code):
            frappe.db.set_value("Nigeria FIRS Service Code", code, "description", description)
        else:
            frappe.get_doc({
                "doctype": "Nigeria FIRS Service Code",
                "name": code,
                "service_code": code,
                "description": description,
            }).insert(ignore_permissions=True)
        count += 1

    frappe.db.commit()
    frappe.msgprint(f"Synced {count} service codes from FIRS.", indicator="green", alert=True)
    return {"synced": count}
