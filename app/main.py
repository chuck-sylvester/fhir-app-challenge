# -----------------------------------------------------------------
# app/main.py
# -----------------------------------------------------------------
# Starting point for the fhir-app-challenge application
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

# Routes
# from app.routers import aaa, bbb, ccc

# Import settings object from app-level config file
from app.config import settings

# Configure Python logging
# Set root logger to use level specified in settings object
logging.basicConfig(
    level=settings.log_level.upper(),
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

print()
print("-" * 60)
print("     APP_NAME:", settings.app_name)
print("      APP_ENV:", settings.app_env)
print("-" * 60)

# Initialize FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="Medblocks 15-day FHIR App Challenge",
    version="1.0.0",
    debug=settings.app_debug
)

# Create temporary root route handler
@app.get("/", name="root", include_in_schema=False)
async def home(request: Request):
    """Simple message now; redirect to home page later."""
    return {
        "message1": "Hello",
        "message2": "World!",
        "message3": "May great things happen today..."
    }