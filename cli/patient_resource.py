# -----------------------------------------------------------------
# cli/patient_resource.py
# -----------------------------------------------------------------
# Standalone script to interface with a HAPI FHIR server to
# retrieve and display data from the Patient resource.
# -----------------------------------------------------------------

# Standard library imports
import os
import json
from typing import Any, Final

# Third-party imports
import requests
from dotenv import load_dotenv

load_dotenv()

FHIR_LOCAL_URL: Final = "http://localhost:8080/fhir"
FHIR_EXTERNAL_URL: Final = "https://fhir.medblocks.com/fhir/zWoWdhFBpJ7bL3jVa8VnccPvW39RkU9A"
ENVIRONMENT = "external"

FHIR_EXTERNAL_API_TOKEN = os.getenv('FHIR_EXTERNAL_API_TOKEN')

if ENVIRONMENT == "local":
    FHIR_BASE_URL = FHIR_LOCAL_URL
    headers = {"Accept": "application/fhir+json"}
else:
    FHIR_BASE_URL = FHIR_EXTERNAL_URL
    headers = {
        "Accept": "application/fhir+json",
        "Authorization": f"Bearer {FHIR_EXTERNAL_API_TOKEN}"
    }


def fetch_patient_resource() -> dict[str, Any] | None:
    # Get Patient resource in JSON format and return as Python object
    try:
        response = requests.get(f"{FHIR_BASE_URL}/Patient", headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        print(f"Could not connect to FHIR server at {FHIR_BASE_URL}.")
        print(f"Is the HAPI FHIR server running?")
        return None
    except requests.exceptions.Timeout:
        print(f"Timed out connecting to FHIR server at {FHIR_BASE_URL}.")
        return None
    except requests.exceptions.HTTPError as error:
        print(f"FHIR server returned an HTTP error: {error}")
        return None


def print_patient_resource_summary(patient_resource: dict[str, Any]) -> None:
    # Pull a few top-level fields out of the Patient resource for eaiser reading.
    resource_type = patient_resource.get("resourceType", "Unknown")
    resource_id = patient_resource.get("id", "Unknown")
    resource_total = patient_resource.get("total", "Unknown")
    links = patient_resource.get("link", [])
    link_url = links[0].get("url", "Unknown") if links else "Unknown"

    print("-" * 60)
    print("Patient Resource Summary")
    print("-" * 60)
    print(f" Resource Type: {resource_type}")
    print(f"   Resource ID: {resource_id}")
    print(f"Resource Total: {resource_total}")
    print(f"      Link URL: {link_url}")
    print()


def get_patient_list(patient_resource: dict[str, Any]) -> list[str]:
    patient_list: list[str] = []

    # Patient Bundle.entry is a list; each entry advertises a patient
    for bundle_entry in patient_resource["entry"]:
        patient_list.append(bundle_entry)

    return patient_list


def print_patient_list(patient_list: list[str]) -> None:
    for patient in patient_list:
        print("| ", end='')
        print(patient["resource"]["resourceType"], end=' | ')
        print(f"{patient['resource']['id']:<36}", end=' | ')
        print(f"{patient['resource']['gender']:<6}", end=' | ')
        print(patient["resource"]["name"][0]["given"][0], end=' ')
        print(patient["resource"]["name"][0]["family"])
    print()


def main():
    # Fetch data, stop on failure, display results.
    patient_resource = fetch_patient_resource()

    if patient_resource:
        print("Patient Resource value returned.")
    else:
        return
    
    print(json.dumps(patient_resource, indent=2), "\n")
    print_patient_resource_summary(patient_resource)

    patient_list = get_patient_list(patient_resource)
    print_patient_list(patient_list)

if __name__ == "__main__":
    main()