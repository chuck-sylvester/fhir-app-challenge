# -----------------------------------------------------------
# app/routers/patient.py
# -----------------------------------------------------------

from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from datetime import date
from app.services import patient_service

router = APIRouter()

templates = Jinja2Templates(directory="app/templates")


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


def _patient_to_context(patient: dict) -> dict:
    """Extract display and form fields from a FHIR Patient resource dict."""
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
    if patient.get("telecom"):
        for t in patient["telecom"]:
            if t.get("system") == "phone":
                phone = t.get("value", "")
                break

    marital_status = ""
    marital_display = ""
    if patient.get("maritalStatus") and patient["maritalStatus"].get("coding"):
        marital_status = patient["maritalStatus"]["coding"][0].get("code", "")
        marital_display = patient["maritalStatus"].get("text", marital_status)

    last_updated = ""
    if patient.get("meta") and patient["meta"].get("lastUpdated"):
        last_updated = patient["meta"]["lastUpdated"][:10]

    return {
        "first_name": first_name,
        "last_name": last_name,
        "gender": gender,
        "birth_date": birth_date,
        "age": age,
        "phone": phone,
        "marital_status": marital_status,
        "marital_display": marital_display,
        "last_updated": last_updated,
    }


# --- List / table routes ---

@router.get("/Patient", response_class=HTMLResponse)
async def get_patient_json(request: Request):
    data = patient_service.get_patient()
    return templates.TemplateResponse(
        request,
        "partials/get_patient_json.html",
        {"results": data}
    )


@router.get("/Patient/table", response_class=HTMLResponse)
async def get_patient_table(request: Request):
    data = patient_service.get_patient("table")
    return templates.TemplateResponse(
        request,
        "partials/get_patient_table.html",
        {"results": data}
    )


# --- Create ---

@router.get("/Patient/new", response_class=HTMLResponse)
async def get_patient_new(request: Request):
    return templates.TemplateResponse(
        request,
        "partials/create_patient_modal.html",
        {}
    )


@router.post("/Patient", response_class=HTMLResponse)
async def post_patient(
    request: Request,
    first_name:     str = Form(...),
    last_name:      str = Form(...),
    gender:         str = Form(...),
    birth_date:     str = Form(...),
    marital_status: str = Form(""),
    phone:          str = Form(""),
):
    try:
        patient_service.create_patient(
            first_name, last_name, gender, birth_date, marital_status, phone
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

@router.get("/Patient/{ptid}/view", response_class=HTMLResponse)
async def get_patient_view(request: Request, ptid: str):
    patient = patient_service.get_patient(ptid)
    context = _patient_to_context(patient)
    context["ptid"] = ptid
    return templates.TemplateResponse(request, "partials/view_patient_modal.html", context)


@router.get("/Patient/{ptid}/edit", response_class=HTMLResponse)
async def get_patient_edit(request: Request, ptid: str):
    patient = patient_service.get_patient(ptid)
    context = _patient_to_context(patient)
    context["ptid"] = ptid
    return templates.TemplateResponse(request, "partials/edit_patient_modal.html", context)


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

@router.get("/Patient/{ptid}", response_class=HTMLResponse)
async def get_patient_by_id(request: Request, ptid: str):
    data = patient_service.get_patient(ptid)
    return templates.TemplateResponse(
        request,
        "partials/get_patient_json.html",
        {"results": data}
    )


# --- Update ---

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
):
    try:
        patient_service.update_patient(
            ptid, first_name, last_name, gender, birth_date, marital_status, phone
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

@router.delete("/Patient/{ptid}", response_class=HTMLResponse)
async def delete_patient(request: Request, ptid: str):
    patient_service.delete_patient(ptid)
    response = HTMLResponse(content="", status_code=200)
    response.headers["HX-Trigger"] = "patient-deleted"
    return response
