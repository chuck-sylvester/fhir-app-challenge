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


_MARITAL_DISPLAY = {
    "M": "Married",
    "D": "Divorced",
    "L": "Legally Separated",
    "W": "Widowed",
    "U": "Unmarried",
}


def create_patient(first_name: str, last_name: str, gender: str,
                   birth_date: str, marital_status: str, phone: str = ""):
    new_patient = {
        "resourceType": "Patient",
        "active": True,
        "name": [{"use": "official", "family": last_name, "given": [first_name]}],
        "gender": gender,
        "birthDate": birth_date,
    }
    if phone:
        new_patient["telecom"] = [{"system": "phone", "value": phone, "use": "home"}]
    if marital_status:
        display = _MARITAL_DISPLAY.get(marital_status, marital_status)
        new_patient["maritalStatus"] = {
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/v3-MaritalStatus",
                "code": marital_status,
                "display": display,
            }],
            "text": display,
        }

    headers = {"Content-Type": "application/fhir+json", "Accept": "application/fhir+json"}
    if settings.fhir_external_api_token:
        headers["Authorization"] = f"Bearer {settings.fhir_external_api_token}"

    output = requests.post(f"{settings.fhir_base_url}/Patient", json=new_patient, headers=headers)
    output.raise_for_status()
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