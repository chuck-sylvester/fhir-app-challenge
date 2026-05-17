# -----------------------------------------------------------
# app/services/patient_service.py
# -----------------------------------------------------------

import requests
from app.config import settings


def get_patient(ptid: str = None):
    base_url = settings.fhir_base_url

    headers = {
        "Accept": "application/fhir+json"
    }
    if settings.fhir_external_api_token:
      headers["Authorization"] = f"Bearer {settings.fhir_external_api_token}" 

    if ptid == None:
        output = requests.get(f"{base_url}/Patient", headers=headers, params={"_count": 5})
    elif ptid == "table":
        output = requests.get(f"{base_url}/Patient", headers=headers)
    else:
        output = requests.get(f"{base_url}/Patient/{ptid}", headers=headers)

    return output.json()


def create_patient(first_name: str, last_name: str, gender: str,
                   birth_date: str, phone: str = ""):
    new_patient = {
        "resourceType": "Patient",
        "active": True,
        "name": [{"use": "official", "family": last_name, "given": [first_name]}],
        "gender": gender,
        "birthDate": birth_date,
    }
    if phone:
        new_patient["telecom"] = [{"system": "phone", "value": phone, "use": "home"}]

    headers = {"Content-Type": "application/fhir+json", "Accept": "application/fhir+json"}
    if settings.fhir_external_api_token:
        headers["Authorization"] = f"Bearer {settings.fhir_external_api_token}"

    output = requests.post(f"{settings.fhir_base_url}/Patient", json=new_patient, headers=headers)
    return output.json()


def delete_patient(ptid: str):
    base_url = settings.fhir_base_url

    headers = {
        "Accept": "application/fhir+json"
    }
    if settings.fhir_external_api_token:
      headers["Authorization"] = f"Bearer {settings.fhir_external_api_token}" 

    output = requests.delete(f"{base_url}/Patient/{ptid}", headers=headers)
    return output.json()