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


def create_patient():
    base_url = settings.fhir_base_url

    headers = {
        "Content-Type": "application/fhir+json",
        "Accept": "application/fhir+json"
    }
    if settings.fhir_external_api_token:
      headers["Authorization"] = f"Bearer {settings.fhir_external_api_token}" 

    new_patient = {
        "resourceType": "Patient",
        "active": True,
        "name": [
            {
                "use": "official",
                "family": "Hartwell",
                "given": ["Claire", "Anne"]
            }
        ],
        "gender": "female",
        "birthDate": "1991-07-22",
        "telecom": [
            {"system": "phone", "value": "555-294-1837", "use": "home"},
            {"system": "email", "value": "claire.hartwell@example.com", "use": "home"}
        ],
        "address": [
            {
                "use": "home",
                "line": ["418 Birchwood Lane"],
                "city": "Madison",
                "state": "WI",
                "postalCode": "53703",
                "country": "US"
            }
        ],
        "maritalStatus": {
            "coding": [
                {
                    "system": "http://terminology.hl7.org/CodeSystem/v3-MaritalStatus",
                    "code": "S",
                    "display": "Never Married"
                }
            ]
        },
        "communication": [
            {
                "language": {
                    "coding": [
                        {
                            "system": "urn:ietf:bcp:47",
                            "code": "en",
                            "display": "English"
                        }
                    ]
                },
                "preferred": True
            }
        ],
        "identifier": [
            {
                "use": "usual",
                "system": "http://example-clinic.org/mrn",
                "value": "MRN-20260001"
            }
        ]
    }

    output = requests.post(f"{base_url}/Patient", json=new_patient, headers=headers)
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