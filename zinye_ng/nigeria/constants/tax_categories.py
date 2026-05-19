"""
FIRS e-Invoice Tax Category codes.
Source: GET base_url/api/v1/invoice/resources/tax-categories
"""
from __future__ import annotations

TAX_CATEGORIES: dict[str, str] = {
    "STANDARD_GST": "Standard Goods and Services Tax",
    "REDUCED_GST": "Reduced Goods and Services Tax",
    "ZERO_GST": "Zero Goods and Services Tax",
    "STANDARD_VAT": "Standard Value-Added Tax",
    "REDUCED_VAT": "Reduced Value-Added Tax",
    "ZERO_VAT": "Zero Value-Added Tax",
    "STATE_SALES_TAX": "State Sales Tax",
    "LOCAL_SALES_TAX": "Local Sales Tax",
    "ALCOHOL_EXCISE_TAX": "Alcohol Excise Tax",
    "TOBACCO_EXCISE_TAX": "Tobacco Excise Tax",
    "FUEL_EXCISE_TAX": "Fuel Excise Tax",
    "SOCIAL_SECURITY_TAX": "Social Security Tax",
    "MEDICARE_TAX": "Medicare Tax",
    "REAL_ESTATE_TAX": "Real Estate Tax",
    "PERSONAL_PROPERTY_TAX": "Personal Property Tax",
    "CARBON_TAX": "Carbon Tax",
    "PLASTIC_TAX": "Plastic Tax",
    "IMPORT_DUTY": "Import Duty",
    "EXPORT_DUTY": "Export Duty",
    "LUXURY_TAX": "Luxury Tax",
    "SERVICE_TAX": "Service Tax",
    "TOURISM_TAX": "Tourism Tax",
    "WITHHOLDING_TAX": "Withholding Tax",
    "STAMP_DUTY": "Stamp Duty",
    "EXEMPTED": "Tax Exemption",
}

# Nigeria-specific: standard VAT rate (7.5%) maps to STANDARD_VAT
# Zero-rated supplies (exports, basic foodstuffs) use ZERO_VAT
# Exempt supplies use EXEMPTED
DEFAULT_TAX_CATEGORY = "STANDARD_VAT"


def get_tax_category_code(vat_rate: float) -> str:
    """
    Derive FIRS tax category code from VAT rate.
    Nigeria has three bands: standard (7.5%), zero (0%), exempt (None/0 by policy).
    """
    if vat_rate > 0:
        return "STANDARD_VAT"
    return "ZERO_VAT"


def get_tax_category_label(code: str) -> str:
    return TAX_CATEGORIES.get(code, "Standard Value-Added Tax")
