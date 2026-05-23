# -----------------------------------------------------------------
# app/services/capability_service.py
# -----------------------------------------------------------------

import requests
from app.config import settings


def get_capability():
    base_url = settings.fhir_base_url

    headers = {
        "Accept": "application/fhir+json"
    }

    if settings.fhir_external_api_token:
        headers["Authorization"] = f"Bearer {settings.fhir_external_api_token}"

    output = requests.get(f"{base_url}/metadata", headers=headers, timeout=10)
    output.raise_for_status()

    return output.json()
