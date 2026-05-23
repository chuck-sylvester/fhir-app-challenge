# -----------------------------------------------------------------
# app/routers/capability.py
# -----------------------------------------------------------------

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import requests
from app.services import capability_service
from app.config import settings

router = APIRouter()

templates = Jinja2Templates(directory="app/templates")


def _first_rest_server(capability: dict) -> dict:
    """Return the server REST section from a FHIR CapabilityStatement."""
    for rest in capability.get("rest", []):
        if rest.get("mode") == "server":
            return rest

    rest_sections = capability.get("rest", [])
    return rest_sections[0] if rest_sections else {}


def _capability_resources(rest: dict) -> list[dict]:
    """Extract resource support details from the REST section."""
    resources = []

    for resource in rest.get("resource", []):
        interactions = [
            interaction.get("code", "")
            for interaction in resource.get("interaction", [])
            if interaction.get("code")
        ]
        search_params = [
            param.get("name", "")
            for param in resource.get("searchParam", [])
            if param.get("name")
        ]

        resources.append({
            "type": resource.get("type", ""),
            "profile": resource.get("profile", ""),
            "interactions": interactions,
            "search_params": search_params,
            "interaction_count": len(interactions),
            "search_param_count": len(search_params),
        })

    return sorted(resources, key=lambda item: item["type"])


def _capability_operations(rest: dict) -> list[dict]:
    """Extract supported FHIR operations from the REST section."""
    operations = []

    for operation in rest.get("operation", []):
        operations.append({
            "name": operation.get("name", ""),
            "definition": operation.get("definition", ""),
        })

    return operations


def _capability_to_context(capability: dict) -> dict:
    """Extract display fields from a FHIR CapabilityStatement."""
    software = capability.get("software") or {}
    implementation = capability.get("implementation") or {}
    rest = _first_rest_server(capability)
    security = rest.get("security") or {}
    resources = _capability_resources(rest)
    operations = _capability_operations(rest)

    return {
        "server": {
            "resource_type": capability.get("resourceType", ""),
            "id": capability.get("id", ""),
            "name": capability.get("name", ""),
            "title": capability.get("title", ""),
            "status": capability.get("status", ""),
            "date": capability.get("date", ""),
            "publisher": capability.get("publisher", ""),
            "kind": capability.get("kind", ""),
            "fhir_version": capability.get("fhirVersion", ""),
            "base_url": settings.fhir_base_url,
        },
        "software": {
            "name": software.get("name", ""),
            "version": software.get("version", ""),
            "release_date": software.get("releaseDate", ""),
        },
        "implementation": {
            "description": implementation.get("description", ""),
            "url": implementation.get("url", ""),
        },
        "rest": {
            "mode": rest.get("mode", ""),
            "resource_count": len(resources),
            "operation_count": len(operations),
        },
        "formats": capability.get("format", []),
        "security": {
            "cors": security.get("cors"),
            "services": [
                service.get("text", "")
                for service in security.get("service", [])
                if service.get("text")
            ],
        },
        "resources": resources,
        "operations": operations,
        "error": "",
    }


@router.get("/metadata", response_class=HTMLResponse)
async def get_capability(request: Request):
    try:
        data = capability_service.get_capability()
        context = _capability_to_context(data)
    except requests.RequestException as exc:
        context = {
            "server": {"base_url": settings.fhir_base_url},
            "software": {},
            "implementation": {},
            "rest": {},
            "formats": [],
            "security": {},
            "resources": [],
            "operations": [],
            "error": f"Unable to retrieve CapabilityStatement: {exc}",
        }

    return templates.TemplateResponse(
        request,
        "partials/get_capability_modal.html",
        context
    )
