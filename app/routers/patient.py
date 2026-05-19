# -----------------------------------------------------------
# app/routers/patient.py
# -----------------------------------------------------------

from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.services import patient_service

router = APIRouter()

templates = Jinja2Templates(directory="app/templates")


@router.get("/Patient", response_class=HTMLResponse)
async def get_patient(request: Request):
    data = patient_service.get_patient()
    return templates.TemplateResponse(
        request,
        "partials/get_patient_json.html",
        {"results": data}
    )


@router.get("/Patient/table", response_class=HTMLResponse)
async def get_patient(request: Request):
    data = patient_service.get_patient("table")
    return templates.TemplateResponse(
        request,
        "partials/get_patient_table.html",
        {"results": data}
    )


@router.get("/Patient/new", response_class=HTMLResponse)
async def get_patient_new(request: Request):
    return templates.TemplateResponse(
        request,
        "partials/create_patient_modal.html",
        {}
    )


@router.get("/Patient/{ptid}", response_class=HTMLResponse)
async def get_patient(request: Request, ptid: str):
    data = patient_service.get_patient(ptid)
    return templates.TemplateResponse(
        request,
        "partials/get_patient_json.html",
        {"results": data}
    )

# This route will get its data from the create patient modal form
@router.post("/Patient", response_class=HTMLResponse)
async def post_patient(
    request: Request,
    first_name: str = Form(...),
    last_name: str = Form(...),
    gender: str = Form(...),
    birth_date: str = Form(...),
    marital_status: str = Form(""),
    phone: str = Form(""),
    ):
    try:
        patient_service.create_patient(first_name, last_name, gender, birth_date, marital_status, phone)
    except Exception:
        return templates.TemplateResponse(
            request,
            "partials/create_patient_modal.html",
            {"error": "Failed to create patient. Please try again."},
        )
    # Close the modal and refresh the patient table in #result
    return HTMLResponse(
        '<div hx-get="/Patient/table" hx-target="#result" hx-swap="innerHTML" hx-trigger="load"></div>'
    )


@router.delete("/Patient/{ptid}", response_class=HTMLResponse)
async def delete_patient(request: Request, ptid: str):
    data = patient_service.delete_patient(ptid)
    return templates.TemplateResponse(
        request,
        "partials/delete_patient_result.html",
        {"results": data, "ptid": ptid}
    )