# -----------------------------------------------------------------
# cli/capability_statement.py
# -----------------------------------------------------------------
# Standalone script to interface with a HAPI FHIR server and inspect
# the server's CapabilityStatement.
# -----------------------------------------------------------------

# Standard Library Imports
import json
from typing import Any, Final

# Third-party Imports
import requests

FHIR_LOCAL_URL: Final = "http://localhost:8080/fhir"
FHIR_EXTERNAL_URL: Final = "https://fhir.medblocks.com/fhir/zWoWdhFBpJ7bL3jVa8VnccPvW39RkU9A"
FHIR_BASE_URL = FHIR_LOCAL_URL


def fetch_capability_statement() -> dict[str, Any] | None:
    # Ask the FHIR server for its CapabilityStatement in JSON format.
    headers = {"Accept": "application/fhir+json"}

    try:
        response = requests.get(f"{FHIR_BASE_URL}/metadata", headers=headers, timeout=10)

        # Convert non-success HTTP status codes, such as 404 or 500, into exceptions
        response.raise_for_status()

        # Convert JSON response body into Python dictionaries/lists
        return response.json()
    except requests.exceptions.ConnectionError:
        print(f"Could not connect to FHIR server at {FHIR_BASE_URL}.")
        print("Is the HAPI FHIR server running?")
        return None
    except requests.exceptions.Timeout:
        print(f"Timed out connecting to FHIR server at {FHIR_BASE_URL}.")
        return None
    except requests.exceptions.HTTPError as error:
        print(f"FHIR server returned an HTTP error: {error}")
        return None
    except requests.exceptions.JSONDecodeError:
        print("FHIR server response was not valid JSON.")
        return None


def print_capability_summary(capability_statement: dict[str, Any]) -> None:
    # Pull a few top-level fields out of the CapabilityStatement for easier reading.
    resource_type = capability_statement.get("resourceType", "Unknown")
    capability_id = capability_statement.get("id", "Unknown")
    fhir_version = capability_statement.get("fhirVersion", "Unknown")

    # The implementation field is itself a nested dictionary, so read it separately first.
    implementation = capability_statement.get("implementation", {})
    implementation_description = implementation.get("description", "Unknown")
    implementation_url = implementation.get("url", "Unknown")

    print("-" * 60)
    print("CapabilityStatement Summary")
    print("-" * 60)
    print(f"             Resource Type: {resource_type}")
    print(f"                        ID: {capability_id}")
    print(f"Implementation Description: {implementation_description}")
    print(f"        Implementation URL: {implementation_url}")
    print(f"              FHIR Version: {fhir_version}")
    print()


def get_resource_list(capability_statement: dict[str, Any]) -> list[str]:
    resource_list: list[str] = []

    # CapabilityStatement.rest is a list; each rest entry can advertise many resources
    for rest_entry in capability_statement.get("rest", []):
        for resource in rest_entry.get("resource", []):
            resource_type = resource.get("type")
            if resource_type:
                resource_list.append(resource_type)

    return resource_list


def print_resource_list(resource_list: list[str]) -> None:
    print("-" * 60)
    print("Supported FHIR Resources")
    print("-" * 60)
    print(f"Resource Count: {len(resource_list)}")
    print()

    print_newline = 1

    for resource in resource_list:
        if print_newline % 3 == 0:
            print(f"{resource}")
        else:
            print(f"{resource:<35}", end='')
        print_newline += 1

    print("\n")


def main():
    # Coordinate the script: fetch data, stop on failure, then display results.
    capability_statement = fetch_capability_statement()

    if capability_statement is None:
        return

    print(json.dumps(capability_statement, indent=2), "\n")
    print_capability_summary(capability_statement)

    resource_list = get_resource_list(capability_statement)
    print_resource_list(resource_list)

if __name__ == "__main__":
    main()
