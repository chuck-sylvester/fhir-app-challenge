# -----------------------------------------------------------------
# app/routers/capability.py
# -----------------------------------------------------------------

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.services import capability_service

router = APIRouter()

templates = Jinja2Templates(directory="app/templates")


@router.get("/metadata", response_class=HTMLResponse)
async def get_capability(request: Request):
    data = capability_service.get_capability()
    return templates.TemplateResponse(
        request,
        "partials/get_capability_result.html",
        {"results": data}
    )