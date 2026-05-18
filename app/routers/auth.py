# -----------------------------------------------------------
# app/routers/auth.py
# -----------------------------------------------------------
# med-challenge application authentication
# Login, Callback, and Logout Routes
# -----------------------------------------------------------

from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from app.config import settings

router = APIRouter()

oauth = OAuth()

oauth.register(
    name="keycloak",
    server_metadata_url=(
        f"{settings.keycloak_url}/realms/{settings.keycloak_realm}"
        "/.well-known/openid-configuration"
    ),
    client_id=settings.keycloak_client_id,
    client_secret=settings.keycloak_client_secret,
    client_kwargs={
        "scope": "openid profile email fhirUser patient/*.read",
        "code_challenge_method": "S256",
    },
)


@router.get("/login")
async def login(request: Request):
    """
    Initiate the OAuth2 Authorization Code + PKCE flow.
    Redirects the browser to the keycloak login page.
    """
    redirect_uri = request.url_for("auth_callback")
    return await oauth.keycloak.authorize_redirect(request, redirect_uri)


@router.get("/auth/callback", name="auth_callback")
async def auth_callback(request: Request):
    """
    Handle the redirect from Keycloak after the user authenticates.
    Exchanges the authorization code for tokens, stores user in session.
    """
    token = await oauth.keycloak.authorize_access_token(request)
    user_info = token.get("userinfo")

    if not user_info:
        # Fallback: fetch userinfo manually if not in token response
        user_info = await oauth.keycloak.userinfo(token=token)

    # Store essential user identity in the session
    request.session["user"] = {
        "sub": user_info.get("sub"),
        "name": user_info.get("name", "Unknown User"),
        "email": user_info.get("email", ""),
        "preferred_username": user_info.get("preferred_username", ""),
        "fhirUser": user_info.get("fhirUser"),   # FHIR Practitioner reference (Phase 8)
    }
    request.session["access_token"] = token.get("access_token")  # for FHIR API calls

    return RedirectResponse(url="/")


@router.get("/logout")
async def logout(request: Request):
    """
    Clear the local session.
    Optionally redirect to Keycloak for single sign-out.
    """
    request.session.clear()
    keycloak_logout_url = (
        f"{settings.keycloak_url}/realms/{settings.keycloak_realm}"
        f"/protocol/openid-connect/logout"
        f"?post_logout_redirect_uri={settings.app_base_url}/login"
        f"&client_id={settings.keycloak_client_id}"
    )
    return RedirectResponse(url=keycloak_logout_url)