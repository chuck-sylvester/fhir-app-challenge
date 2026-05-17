# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A browser-based patient management tool for clinicians, built as a Medblocks LLC FHIR App Challenge 2026 project. The app connects to a FHIR R4 server to manage clinical data and uses SMART App Launch for authentication.

## Development Commands

**Start infrastructure (Docker services first):**
```bash
docker compose up -d
```

**Run the FastAPI dev server:**
```bash
uvicorn app.main:app --reload --port 8000
```

**Install Python dependencies:**
```bash
pip install -r requirements.txt
```

**Check running services:**
```bash
docker compose ps
```

**Generate a session secret key:**
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

## Architecture

```
Browser (HTMX + Jinja2 + Tailwind CSS)
         │ HTTP
FastAPI App (Python 3.11)
    ├── app/config.py          — Pydantic Settings singleton
    ├── app/routers/           — FastAPI route handlers
    ├── app/services/          — Business logic / FHIR HTTP calls
    └── app/templates/         — Jinja2 HTML (base.html, partials/)
         │ HTTP (requests lib)
HAPI FHIR Server v7.0.0 (port 8080) ← FHIR R4 clinical data
PostgreSQL 16 + pgvector (port 5432) ← app storage (2 databases)
Keycloak 26.0 (port 8180)           ← OAuth2 / SMART on FHIR
```

**Frontend**: HTMX handles dynamic updates without page reloads. Jinja2 renders server-side HTML. Tailwind CSS (CDN) for styling. FontAwesome kit `124182fb50` for icons.

**Backend pattern**: Routers handle HTTP routing; services contain business logic and make outbound FHIR calls using the synchronous `requests` library. Auth routes use `authlib` with `httpx` (async) for the OAuth2/OIDC flow.

**FHIR server selection**: Controlled by `FHIR_BASE_URL` in `.env` — point it at `FHIR_LOCAL_URL` (Docker on port 8080) or `FHIR_EXTERNAL_URL` (Medblocks-hosted) without code changes.

## Environment Setup

Copy `.env.example` to `.env` and set:

| Variable | Notes |
|---|---|
| `POSTGRES_APP_PASSWORD` | App database password |
| `POSTGRES_HAPI_PASSWORD` | HAPI FHIR database password |
| `KEYCLOAK_ADMIN_PASSWORD` | Keycloak admin console password |
| `KEYCLOAK_CLIENT_SECRET` | Create in Keycloak after realm setup |
| `SESSION_SECRET_KEY` | Generate with `secrets.token_hex(32)` |

The `scripts/init-db.sh` script runs automatically in the postgres container and creates both databases (`fachallenge` for the app, `hapifhir` for HAPI).

HAPI FHIR server configuration lives in `hapi.application.yaml` (Spring Boot config, mounted into the container).

## Infrastructure Services

| Service | URL | Purpose |
|---|---|---|
| FastAPI app | http://localhost:8000 | Main application |
| HAPI FHIR | http://localhost:8080 | FHIR R4 server |
| PostgreSQL | localhost:5432 | Database |
| Keycloak | http://localhost:8180 | Auth server |

**Mock Keycloak users** (password: `fhir#2026!`):
- `clinician.alpha` — Dr. Alice Anderson, MD
- `clinician.bravo` — Dr. Bob Brown, DO
- `clinician.charlie` — Nurse Carol Chen, RN
- `clinician.delta` — Pharmacist David Davis, PharmD

## Current State

**Authentication** — Fully implemented. SMART App Launch with PKCE via Keycloak. Login, callback, and logout routes are live. Session-based `AuthMiddleware` in `main.py` protects all routes except `/login`, `/auth/callback`, `/logout`, and `/health`. Logged-in user's name and a logout button are displayed at the bottom of the left nav in `base.html`, reading from `request.session["user"]`.

**Keycloak setup** — Realm `fachallenge`, client `fhir-demo` (confidential, standard flow). Two custom client scopes configured: `fhirUser` (Default, with User Attribute mapper) and `patient/*.read` (Optional). See `docs/keycloak-auth-setup.md` for full setup instructions.

**Patient CRUD** — Service layer (`patient_service.py`) and routes (`patient.py`) are scaffolded:
- `GET /Patient` — fetches patient list (JSON view, first 5 results)
- `GET /Patient/table` — fetches patient list rendered as an HTML table with colored avatar initials and a placeholder action ellipsis column
- `GET /Patient/{ptid}` — fetches a single patient by ID
- `POST /Patient` — creates a hardcoded test patient (Claire Hartwell); not yet form-driven
- `DELETE /Patient/{ptid}` — deletes a patient by ID

**Not yet implemented** — Patient profile detail view, create/edit/delete UI forms, action menu on the ellipsis column, age calculation (hardcoded to 42), PostgreSQL queries, FHIR Practitioner reference (`fhirUser` — planned for a later phase).
