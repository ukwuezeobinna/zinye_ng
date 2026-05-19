"""
Nigerian states with FIRS/ISO 3166-2 codes.
Source: GET base_url/api/v1/invoice/resources/states
"""
from __future__ import annotations

# name → ISO 3166-2 code (NG-XX)
STATES: dict[str, str] = {
    "Abia": "NG-AB",
    "Adamawa": "NG-AD",
    "Akwa Ibom": "NG-AK",
    "Anambra": "NG-AN",
    "Bauchi": "NG-BA",
    "Bayelsa": "NG-BY",
    "Benue": "NG-BE",
    "Borno": "NG-BO",
    "Cross River": "NG-CR",
    "Delta": "NG-DE",
    "Ebonyi": "NG-EB",
    "Edo": "NG-ED",
    "Ekiti": "NG-EK",
    "Enugu": "NG-EN",
    "FCT": "NG-FC",
    "Gombe": "NG-GO",
    "Imo": "NG-IM",
    "Jigawa": "NG-JI",
    "Kaduna": "NG-KD",
    "Kano": "NG-KN",
    "Katsina": "NG-KT",
    "Kebbi": "NG-KE",
    "Kogi": "NG-KO",
    "Kwara": "NG-KW",
    "Lagos": "NG-LA",
    "Nasarawa": "NG-NA",
    "Niger": "NG-NI",
    "Ogun": "NG-OG",
    "Ondo": "NG-ON",
    "Osun": "NG-OS",
    "Oyo": "NG-OY",
    "Plateau": "NG-PL",
    "Rivers": "NG-RI",
    "Sokoto": "NG-SO",
    "Taraba": "NG-TA",
    "Yobe": "NG-YO",
    "Zamfara": "NG-ZA",
}

# Reverse map: code → name
_CODE_TO_NAME: dict[str, str] = {v: k for k, v in STATES.items()}


def get_state_code(state_name: str | None) -> str:
    """Return FIRS state code for a state name. Returns empty string if not found."""
    if not state_name:
        return ""
    return STATES.get(state_name, "")


def get_state_name(code: str | None) -> str:
    """Return state name for a FIRS state code."""
    if not code:
        return ""
    return _CODE_TO_NAME.get(code, code)
