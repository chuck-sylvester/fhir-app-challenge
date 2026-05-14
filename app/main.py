# -----------------------------------------------------------------
# app/main.py
# -----------------------------------------------------------------
# Starting point for fhir-app-challenge application
#
# Run from project root:
#   uvicorn app.main:app --reload --port 8000
# Access via:
#   localhost:8000
# Stop server:
#   CTRL + C
# -----------------------------------------------------------------

# Main imports
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import logging
import os

# Routes
from app.routers import capability

# Import settings object from app-level config file
from app.config import settings

# Configure Python logging
# Set root logger to use level specified in settings object
logging.basicConfig(
    level=settings.log_level.upper(),
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

print("-" * 60)
print("       APP_NAME:", settings.app_name)
print("    APP_VERSION:", settings.app_version)
print("        APP_ENV:", settings.app_env)
print("  FHIR_BASE_URL:", settings.fhir_base_url)
print("-" * 60)

# Initialize FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="Medblocks 15-day FHIR App Challenge",
    version="1.0.0",
    debug=settings.app_debug
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Mount static files directory
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

# Set up Jinja2 Templates directory with auto-reload for development
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
templates.env.auto_reload = True

# Register all routers
app.include_router(capability.router, tags="metadata")


# Create temporary root route handler
@app.get("/", name="root", include_in_schema=False)
async def home(request: Request):
    """Redirect to home page."""
    return templates.TemplateResponse(
        request,
        "index.html",
        {"title": app.title}
    )