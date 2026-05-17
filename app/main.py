# -----------------------------------------------------------------
# app/main.py
# -----------------------------------------------------------------
# Run from project root directory:
#       Command:  uvicorn app.main:app --reload --port 8000
#    Access via:  localhost:8000
#   Stop server:  CTRL + C
# -----------------------------------------------------------------

"""Starting point for FHIR App Challenge Uvicorn Application."""

# Main imports
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send
import logging
import os

# Router imports
from app.routers import capability, patient, auth

# Settings object import from app-level config file
from app.config import settings

# Configure Python logging
# Set root logger to use log_level specified in settings object
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

# Paths exempt from authentication
PUBLIC_PATHS = {
    "/login",
    "/auth/callback",
    "/logout",
    "/health"
}


class AuthMiddleware:
    """
    ASGI middleware for session-based route protection. Reads scope["session"] directly to
    avoid BaseHTTPMiddleware/SessionMiddleware incompatibility in newer Starlette versions.
    """
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            path = scope["path"]
            is_public = (
                path in PUBLIC_PATHS
                or path.startswith("/static")
                or path.startswith("/cds-services")
            )
            if not is_public and not scope.get("session", {}).get("user"):
                response = RedirectResponse(url="/login")
                await response(scope, receive, send)
                return
        await self.app(scope, receive, send)


# Middleware registration order: Starlette makes the LAST add_middleware call the outermost wrapper to run first
# on every request. SessionMiddleware must be outermost to populates scope["session"] before AuthMiddleware reads it.
app.add_middleware(AuthMiddleware)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret_key,
    https_only=False,   # set to True in production (requires HTTPS)
    same_site="lax"     # allows OAuth2 redirect callbacks (cross-origin top-level nav)
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Mount static files directory
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

# Set up Jinja2 Templates directory with auto-reload for development
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
templates.env.auto_reload = True

# Register all routers
app.include_router(capability.router, tags="metadata")
app.include_router(patient.router, tags="patient")
app.include_router(auth.router, tags="authentication")


# Create temporary root route handler (later adjust for login flow)
@app.get("/", name="root", include_in_schema=False)
async def home(request: Request):
    """Redirect to home page."""
    return templates.TemplateResponse(
        request,
        "patient.html",
        {"title": app.title}
    )


# Create health check route
@app.get("/health", tags=["System"])
async def health_check():
    """Standard health check endpoint."""
    return {
        "application": settings.app_name,
        "status": "healthy",
        "version": settings.app_version,
        "environment": settings.app_env,
        "message": [
            {
                "chant": "Go Green!",
                "response": "Go White!"
            },
            {   "chant": "MSU...",
                "response": "Spartan!"
            }
        ]
    }
