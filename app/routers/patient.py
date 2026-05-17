# -----------------------------------------------------------
# app/routers/patient.py
# -----------------------------------------------------------

from fastapi import APIRouter, Request
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
        "partials/get_patient_result.html",
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


@router.get("/Patient/{ptid}", response_class=HTMLResponse)
async def get_patient(request: Request, ptid: str):
    data = patient_service.get_patient(ptid)
    return templates.TemplateResponse(
        request,
        "partials/get_patient_result.html",
        {"results": data}
    )


@router.post("/Patient", response_class=HTMLResponse)
async def post_patient(request: Request):
    data = patient_service.create_patient()
    return templates.TemplateResponse(
        request,
        "partials/post_patient_result.html",
        {"results": data}
    )


@router.delete("/Patient/{ptid}", response_class=HTMLResponse)
async def delete_patient(request: Request, ptid: str):
    data = patient_service.delete_patient(ptid)
    return templates.TemplateResponse(
        request,
        "partials/delete_patient_result.html",
        {"results": data, "ptid": ptid}
    )