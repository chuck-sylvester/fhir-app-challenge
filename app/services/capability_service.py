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

    output = requests.get(f"{base_url}/metadata", headers=headers)

    return output.json()