# ---------------------------------------------------------------------
# app/routers/patient.py
# ---------------------------------------------------------------------
# Handles all /Patient routes. Registered in app/main.py via:
#   app.include_router(patient.router, tags="patient")
#
# Route overview:
#   GET  /Patient/table            → HTML table partial (HTMX)
#   GET  /Patient                  → JSON view partial
#   GET  /Patient/xml              → XML view partial
#   GET  /Patient/new              → create modal partial
#   POST /Patient                  → create patient, fires HX-Trigger
#   GET  /Patient/{ptid}/activity  → activity modal partial
#   GET  /Patient/{ptid}/view      → view modal partial (feeds view_patient_modal.html)
#   GET  /Patient/{ptid}/edit      → edit modal partial
#   GET  /Patient/{ptid}/delete-confirm  → delete confirmation partial
#   GET  /Patient/{ptid}           → single patient JSON partial
#   PUT  /Patient/{ptid}           → update patient, fires HX-Trigger
#   DELETE /Patient/{ptid}         → delete patient, fires HX-Trigger
#
# IMPORTANT: The /{ptid}/activity, /{ptid}/view, /{ptid}/edit, and
# /{ptid}/delete-confirm routes MUST be registered before the bare
# /{ptid} wildcard route (line 230) or FastAPI will match "activity",
# "view", etc. as ptid values instead of routing to the right handler.
# --------------------------------------------------------------------

from fastapi import APIRouter, Request, Form, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from datetime import date
from app.services import patient_service

router = APIRouter()

# Jinja2 template directory — resolves relative to the project root
# (not this file's directory). Partials live in app/templates/partials/.
templates = Jinja2Templates(directory="app/templates")


# ---------------------------------------------------------------------------
# Jinja2 filter: age
# Registered below as templates.env.filters["age"] so it can be called in
# templates as: {{ birth_date | age }}. Note: _patient_to_context() also
# computes age as a Python int for direct use in view/edit modals ({{ age }}).
# The filter is used in table/list views where only the raw birth_date string
# is passed and Python-side age calculation is not done.
# ---------------------------------------------------------------------------
def _age_filter(birth_date_str: str) -> str:
    """Jinja2 filter: convert a FHIR birthDate string to a display age."""
    if not birth_date_str:
        return "—"
    try:
        birth = date.fromisoformat(birth_date_str)
        today = date.today()
        age = today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))
        return str(age)
    except (ValueError, TypeError):
        return "—"


templates.env.filters["age"] = _age_filter


# ---------------------------------------------------------------------------
# _patient_to_context(patient: dict) -> dict
#
# Helper to map raw FHIR Patient JSON dict (from patient_service.get_patient(ptid))
# to a flat context dict ready for Jinja2 templates.
#
# Called by: get_patient_view, get_patient_edit, get_patient_activity,
# put_patient (on error)
# ---------------------------------------------------------------------------
def _patient_to_context(patient: dict) -> dict:
    """Extract display and form fields from a complex FHIR Patient resource flat dict."""
    first_name = ""
    last_name = ""
    if patient.get("name"):
        n = patient["name"][0]
        if n.get("given"):
            first_name = n["given"][0]
        last_name = n.get("family", "")

    gender = patient.get("gender", "")
    birth_date = patient.get("birthDate", "")

    age = None
    if birth_date:
        try:
            birth = date.fromisoformat(birth_date)
            today = date.today()
            age = today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))
        except ValueError:
            pass

    phone = ""
    email = ""
    if patient.get("telecom"):
        for t in patient["telecom"]:
            if t.get("system") == "phone" and not phone:
                phone = t.get("value", "")
            elif t.get("system") == "email" and not email:
                email = t.get("value", "")
                break

    marital_status = ""
    marital_display = ""
    if patient.get("maritalStatus") and patient["maritalStatus"].get("coding"):
        marital_status = patient["maritalStatus"]["coding"][0].get("code", "")
        marital_display = patient["maritalStatus"].get("text", marital_status)

    last_updated = ""
    if patient.get("meta") and patient["meta"].get("lastUpdated"):
        last_updated = patient["meta"]["lastUpdated"][:10]

    patient_count = 12

    addr_line1 = addr_line2 = ""
    addr_city = addr_state = addr_postal = ""
    addr_country = ""

    if patient.get("address"):
        a = patient["address"][0]
        line = a.get("line", [])
        addr_line1 = line[0] if len(line) > 0 else ""
        addr_line2 = line[1] if len(line) > 1 else ""
        addr_city = a.get("city", "")
        addr_state= a.get("state", "")
        addr_postal = a.get("postalCode", "")
        addr_country = a.get("country", "")

    return {
        "first_name": first_name,
        "last_name": last_name,
        "gender": gender,
        "birth_date": birth_date,
        "age": age,
        "phone": phone,
        "email": email,
        "marital_status": marital_status,
        "marital_display": marital_display,
        "last_updated": last_updated,
        "patient_count": patient_count,
        "addr_line1": addr_line1,
        "addr_line1": addr_line2,
        "addr_city": addr_city,
        "addr_state": addr_state,
        "addr_postal": addr_postal,
        "addr_country": addr_country,
    }


# --- List / table routes ---

# Returns the patient table partial. The optional `name` query param
# filters results by patient name (passed through to the FHIR search).
# HTMX swaps this into the table container on the main page.
@router.get("/Patient/table", response_class=HTMLResponse)
async def get_patient_table(request: Request, name: str | None = Query(None)):
    """Get patients for display in HTML Table format"""
    data = patient_service.get_patient("table", name=name)
    return templates.TemplateResponse(
        request,
        "partials/get_patient_table.html",
        {
            "results": data,
            "name": name or "",
        },
    )


# Returns the patient JSON view partial (uses default 5-result FHIR query).
@router.get("/Patient", response_class=HTMLResponse)
async def get_patient_json(request: Request):
    """Get patients for display in JSON format"""
    data = patient_service.get_patient()
    return templates.TemplateResponse(
        request,
        "partials/get_patient_json.html",
        {"results": data}
    )


# Returns the patient XML view partial (uses default 5-result FHIR query).
@router.get("/Patient/xml", response_class=HTMLResponse)
async def get_patient_xml(request: Request):
    """Get patients for display in XML format"""
    data = patient_service.get_patient("xml")
    return templates.TemplateResponse(
        request,
        "partials/get_patient_xml.html",
        {"results": data}
    )


# --- Create ---

# Returns the empty create-patient modal partial (no context needed).
@router.get("/Patient/new", response_class=HTMLResponse)
async def get_patient_new(request: Request):
    return templates.TemplateResponse(
        request,
        "partials/create_patient_modal.html",
        {}
    )


# Handles the create-patient form submission.
# On success: returns an empty 200 response with HX-Trigger: patient-created,
#   which HTMX picks up on the main page to refresh the patient table.
# On failure: re-renders the create modal with an error message.
# Note: address is not currently a field in the create form or service call.
@router.post("/Patient", response_class=HTMLResponse)
async def post_patient(
    request: Request,
    first_name:     str = Form(...),
    last_name:      str = Form(...),
    gender:         str = Form(...),
    birth_date:     str = Form(...),
    marital_status: str = Form(""),
    phone:          str = Form(""),
    email:          str = Form(""),
):
    try:
        patient_service.create_patient(
            first_name, last_name, gender, birth_date, marital_status, phone, email
        )
    except Exception:
        return templates.TemplateResponse(
            request,
            "partials/create_patient_modal.html",
            {"error": "Failed to create patient. Please try again."},
        )
    response = HTMLResponse(content="", status_code=200)
    response.headers["HX-Trigger"] = "patient-created"
    return response


# --- Action-menu modal routes (must be registered before /{ptid} wildcard) ---

# Returns the patient activity modal. Fetches vitals, conditions,
# medications, and allergies in separate service calls. Each is wrapped
# in its own try/except so a failure in one category does not block the
# others — the template checks for _error keys to show fallback messaging.
@router.get("/Patient/{ptid}/activity", response_class=HTMLResponse)
async def get_patient_activity(request: Request, ptid: str):
    patient = patient_service.get_patient(ptid)
    context = _patient_to_context(patient)
    context["ptid"] = ptid

    try:
        context["vitals"] = patient_service.get_vitals(ptid)
    except Exception:
        context["vitals"] = {"entry": [], "_error": True}

    try:
        context["conditions"] = patient_service.get_conditions(ptid)
    except Exception:
        context["conditions"] = {"entry": [], "_error": True}

    try:
        context["medications"] = patient_service.get_medications(ptid)
    except Exception:
        context["medications"] = {"entry": [], "_error": True}

    try:
        context["allergies"] = patient_service.get_allergies(ptid)
    except Exception:
        context["allergies"] = {"entry": [], "_error": True}

    return templates.TemplateResponse(request, "partials/view_patient_activity.html", context)


# Returns the view-patient modal partial.
# Calls _patient_to_context() to build the template context, then adds ptid.
# This is the route that feeds view_patient_modal.html.
# Once address extraction is added to _patient_to_context(), no changes
# are needed here — the new variables will automatically be in context.
@router.get("/Patient/{ptid}/view", response_class=HTMLResponse)
async def get_patient_view(request: Request, ptid: str):
    patient = patient_service.get_patient(ptid)
    context = _patient_to_context(patient)
    context["ptid"] = ptid
    return templates.TemplateResponse(request, "partials/view_patient_modal.html", context)


# Returns the edit-patient modal partial.
# Uses the same _patient_to_context() as the view route, so address
# variables added there will also be available here if an edit form
# for address is added later.
@router.get("/Patient/{ptid}/edit", response_class=HTMLResponse)
async def get_patient_edit(request: Request, ptid: str):
    patient = patient_service.get_patient(ptid)
    context = _patient_to_context(patient)
    context["ptid"] = ptid
    return templates.TemplateResponse(request, "partials/edit_patient_modal.html", context)


# Returns the delete-confirmation modal. Only needs patient name — does
# not use _patient_to_context() since no other fields are displayed.
@router.get("/Patient/{ptid}/delete-confirm", response_class=HTMLResponse)
async def get_patient_delete_confirm(request: Request, ptid: str):
    patient = patient_service.get_patient(ptid)
    name = "this patient"
    if patient.get("name") and patient["name"][0].get("given"):
        given  = patient["name"][0]["given"][0]
        family = patient["name"][0].get("family", "")
        name   = f"{given} {family}".strip()
    return templates.TemplateResponse(
        request,
        "partials/delete_confirm_modal.html",
        {"ptid": ptid, "patient_name": name}
    )


# --- Single-resource read ---

# Returns a single patient resource rendered as JSON.
# Uses the JSON partial (same template as the list view).
@router.get("/Patient/{ptid}", response_class=HTMLResponse)
async def get_patient_by_id(request: Request, ptid: str):
    data = patient_service.get_patient(ptid)
    return templates.TemplateResponse(
        request,
        "partials/get_patient_json.html",
        {"results": data}
    )


# --- Update ---

# Handles the edit-patient form submission (HTTP PUT via HTMX).
# On success: returns empty 200 with HX-Trigger: patient-updated
#   to refresh the patient table on the main page.
# On failure: re-renders the edit modal with context + error message.
# Note: address is not currently a field in the update form or service call.
# When address editing is added, new Form() parameters will be needed here
# and passed through to patient_service.update_patient().
@router.put("/Patient/{ptid}", response_class=HTMLResponse)
async def put_patient(
    request: Request,
    ptid:           str,
    first_name:     str = Form(...),
    last_name:      str = Form(...),
    gender:         str = Form(...),
    birth_date:     str = Form(...),
    marital_status: str = Form(""),
    phone:          str = Form(""),
    email:          str = Form(""),
):
    try:
        patient_service.update_patient(
            ptid, first_name, last_name, gender, birth_date, marital_status, phone, email
        )
    except Exception:
        patient = patient_service.get_patient(ptid)
        context = _patient_to_context(patient)
        context["ptid"] = ptid
        context["error"] = "Failed to update patient. Please try again."
        return templates.TemplateResponse(request, "partials/edit_patient_modal.html", context)
    response = HTMLResponse(content="", status_code=200)
    response.headers["HX-Trigger"] = "patient-updated"
    return response


# --- Delete ---

# Handles patient deletion. Returns empty 200 with HX-Trigger: patient-deleted
# to refresh the patient table. The service returns an empty dict if the
# FHIR server returns no body (some servers return 204 No Content on DELETE).
@router.delete("/Patient/{ptid}", response_class=HTMLResponse)
async def delete_patient(request: Request, ptid: str):
    patient_service.delete_patient(ptid)
    response = HTMLResponse(content="", status_code=200)
    response.headers["HX-Trigger"] = "patient-deleted"
    return response
