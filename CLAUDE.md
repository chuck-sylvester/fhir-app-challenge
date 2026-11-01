# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FHIR App Challenge — a browser-based patient management tool for clinicians, built as a Medblocks LLC FHIR App Challenge submission. It is a FastAPI + HTMX + Jinja2 server-rendered app that proxies to a HAPI FHIR (R4) server for all clinical data (Patient, Observation, Condition, MedicationRequest, AllergyIntolerance) and uses Keycloak for SMART-on-FHIR OAuth2/OIDC login. There is no client-side JS framework and no client-side data store — the server renders HTML fragments and HTMX swaps them into the page.

## Commands

**Setup**
```bash
cp .env.example .env        # then fill in required secrets (see Config section below)
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

**Run infrastructure (HAPI FHIR, Postgres, Keycloak)**
```bash
docker compose up -d
docker compose ps
```
`scripts/init-db.sh` must be `chmod +x` before first run or Docker silently skips it.

**Run the app**
```bash
uvicorn app.main:app --reload --port 8000
```
Must be run from the project root (templates/static paths in the routers are relative to cwd, e.g. `Jinja2Templates(directory="app/templates")`).

**CLI scripts** (standalone, bypass the FastAPI app entirely — useful for quickly inspecting the FHIR server)
```bash
python3 cli/patient_resource.py        # dump/print Patient bundle
python3 cli/capability_statement.py    # dump/print CapabilityStatement
```

There is no test suite, linter, or type-checker configured in this repo currently.

## Configuration

Settings are loaded via `app/config.py` (`pydantic-settings`, `Settings` class) from `.env` + real env vars. Several fields are **required with no default** (`fhir_base_url`, `fhir_local_url`, `fhir_base_url_external_1/2/3`, `keycloak_client_secret`, `session_secret_key`) — the app will fail to start if any are missing. Note `.env.example` currently only documents a single `FHIR_EXTERNAL_URL`, not the `fhir_base_url_external_1/2/3` fields config.py now expects — check `app/config.py` directly for the authoritative list of required env vars rather than trusting `.env.example`.

`FHIR_BASE_URL` selects the active FHIR backend (local HAPI vs. one of the external Medblocks servers); switch it in `.env` without touching code.

## Architecture

**Router → Service → FHIR server.** Each FHIR resource area has a thin FastAPI router (`app/routers/`) and a matching service module (`app/services/`) that does the actual `requests` calls to `settings.fhir_base_url`. Routers own HTTP/template concerns (Jinja2 context building, HX-Trigger headers, error partials); services own FHIR wire format (building resource JSON, auth headers, `raise_for_status()`). Routers never call `requests` directly; services never touch `Request`/templates.

**Everything is server-rendered HTML fragments swapped by HTMX**, not a JSON API consumed by JS. Full-page routes (`/`, `patient.html`) render the app shell once; nearly every other route returns a Jinja2 *partial* (`app/templates/partials/*.html`) that HTMX swaps into either `#result` (main content area) or `#modal-root` (`app/templates/base.html`). Mutations (`POST`/`PUT`/`DELETE`) return an empty 200 body with an `HX-Trigger` header (`patient-created`/`patient-updated`/`patient-deleted`); the patient table wrapper listens for those events via `hx-trigger="... from:body"` and re-fetches `/Patient/table`. See `docs/spec/modal-form-guide.md` and `docs/spec/patient-actions-guide.md` for the full rationale and step-by-step pattern this was built from — read these before adding a new modal/action.

**Route ordering matters.** In `app/routers/patient.py`, literal-segment routes (`/Patient/table`, `/Patient/new`, `/Patient/{ptid}/activity`, `/Patient/{ptid}/view`, `/Patient/{ptid}/edit`, `/Patient/{ptid}/delete-confirm`) must be registered *before* the bare `/Patient/{ptid}` wildcard route, or FastAPI matches the wildcard first and the literal routes become unreachable.

**Auth.** `AuthMiddleware` (custom ASGI middleware in `app/main.py`, not `BaseHTTPMiddleware`) reads `scope["session"]["user"]` directly and redirects to `/login` for any non-public path. `SessionMiddleware` must be added *after* `AuthMiddleware` in `add_middleware()` calls, because Starlette makes the last-added middleware outermost/first-to-run — it has to populate the session before `AuthMiddleware` reads it. `PUBLIC_PATHS` plus `/static` and `/cds-services` prefixes bypass auth. Login/callback/logout live in `app/routers/auth.py` using `authlib`'s `OAuth` client against Keycloak's SMART App Launch (PKCE) flow; the FHIR access token is stashed in the session for future FHIR calls, and `fhirUser` is captured for a not-yet-wired Practitioner-linking phase.

**FHIR patient JSON → template context.** `_patient_to_context()` in `app/routers/patient.py` is the single place raw FHIR `Patient` dicts get flattened into template-friendly fields (name, age computed from `birthDate`, phone/email pulled out of `telecom`, marital status display text, address). It's shared by the view/edit/activity routes — extend it there rather than duplicating extraction logic in a route.

**Activity modal** (`/Patient/{ptid}/activity`) fans out to four independent service calls (`get_vitals`, `get_conditions`, `get_medications`, `get_allergies`), each wrapped in its own try/except so one failing FHIR query doesn't block the others — the template checks per-category `_error` flags to render fallback messaging.

**External FHIR auth.** When `settings.fhir_external_api_token` is set, service functions attach `Authorization: Bearer <token>`; requests to the local Dockerized HAPI server generally don't need it. Every service function repeats this same header-building pattern — follow it when adding new resource-type service functions.

**Docker services** (`docker-compose.yaml`): `postgres` (pgvector/pgvector, hosts both the app DB and a separate HAPI DB via `scripts/init-db.sh`), `hapi-fhir` (HAPI v7.0.0, configured via `hapi.application.yaml`), `keycloak` (dev mode, realm `fachallenge`, client `fhir-demo`). Full setup/mock-user details are in `README.md` and `docs/spec/keycloak-auth-setup.md`.

## Other docs worth knowing about

`docs/spec/` contains detailed guides written while building specific features — treat them as design references/rationale, not just history, since they explain *why* patterns (modal HTMX flow, action-menu JS, activity page) were built the way they were:
- `modal-form-guide.md` — HTMX modal pattern used by every create/edit/delete modal
- `patient-actions-guide.md` — row action-menu (View/Edit/Delete) implementation
- `patient-activity-page-guide.md` — the activity modal (vitals/conditions/medications/allergies)
- `keycloak-auth-setup.md` — Keycloak realm/client setup for local + OCI
- `oci-deployment-guide.md` — Oracle Cloud deployment notes
