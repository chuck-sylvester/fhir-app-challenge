# fhir-app-challenge
FHIR App Challenge 2026 - Medblocks

## Overview

**FHIR App Challenge** is a browser-based patient management tool for clinicians at a healthcare clinic or hospital. Patient records are stored in a local HAPI FHIR server (R4) or an external HAPI FHIR server (R4) provided by Medblocks. A PostgreSQL database -- configured to support vector data storage -- is available for any local storage needed by the application, and an instance of Keycloak is also running as a service to demonstrate OAuth2 single sign-on.

This application was developed as part of the [Medblocks LLC](https://medblocks.com) FHIR App Challenge.

## Tech Stack

This application primarily leverages a Python-based technology stack, along with a few supporting tools, as listed below.

| Layer          | Technology |
|----------------|------------|
| Backend        | Python 3.11 + FastAPI |
| Frontend       | HTMX + Jinja2 Templates + Tailwind CSS |
| Clinical Data  | HAPI FHIR Server v7.0.0 (R4) |
| App Database   | PostgreSQL 16 (pgvector/pgvector:pg16) |
| Auth Server    | Keycloak 26.0 (Docker-hosted, SMART on FHIR) |
| Infrastructure | Docker + Docker Compose |
| HTTP Client    | requests (synchronous); httpx (async, in use for auth) |
| FHIR models    | fhir.resources (TBD: may be used in prior auth module) |
| Configuration  | pydantic-settings + python-dotenv |
| Cloud Host     | Oracle Cloud Infrastructure (OCI)

## Authentication

This app demonstrates SMART on FHIR (OAuth2 + OIDC) authentication. Keycloak runs as a Docker container and serves as the authentication server. The implementation uses the SMART App Launch (standalone) flow with PKCE for provider portal login.

**Keycloak configuration (local)**  

- Realm: `fhir-app-challenge`
- Client: `patient-portal`
- Admin console: `http://localhost:8110`

**Mock Users**

| Username           | Display Name                   | Role     |
|--------------------|--------------------------------|----------|
| clinician.alpha    | Dr. Alice Anderson, MD         | TBD      |
| clinician.bravo    | Dr. Bob Brown, DO              | TBD      |
| clinician.charlie  | Nurse Carol Chen, RN           | TBD      |
| clinician.delta    | Pharmacist David Davis, PharmD | TBD      |

**Password (all users):** `fhir#challenge#2026`

## Quick Start

### 1. Configure Environment

```bash
cp .env.example .env

# Edit .env values for:  
# POSTGRESS_APP_PASSWORD, POSTGRES_HAPI_PASSWORD, KEYCLOAK_ADMIN_PASSWORD, SESSION_SECRET_KEY
```

### 2. Create Docker Infrastructure

A complete Docker infrastructure is created via the project folder files:  

- `./docker-compose.yaml`
- `./hapi.application.yaml`
- `./scripts/init-db.sh`

Note that `init-db.sh` must be updated to be executable, or Docker will silently ignore it.

**Start Services**
```bash
docker compose up -d
docker compose ps
```

Verify all three services are ready:

```bash
# FHIR server — should return a CapabilityStatement JSON object
curl http://localhost:8080/fhir/metadata | python3 -m json.tool | head -20

# PostgreSQL — list databases (should show both medchallenge and hapifhir)
# Note: you will be prompted for the facuser password
psql -h localhost -p 5432 -U facuser -d fachallenge -c "\l"

# Keycloak — should return realm metadata JSON
curl -s http://localhost:8180/realms/master | python3 -m json.tool | head -10
```

### 3. Set up Python environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 4. Run the application

From the project root folder, run:
```bash
uvicorn app.main:app --reload --port 8000
```

To run application and supporting services:

| Component | URL |
|-----------|-----|
| FHIR App Challenge     | `http://localhost:8000`      |
| HAPI FHIR server       | `http://localhost:8080/fhir` |
| Keycloak admin console | `http://localhost:8180`      |

# FHIR Server

The application supports switching between a local and an external HAPI FHIR server via `.env`:

```env
FHIR_BASE_URL=${FHIR_LOCAL_URL}    # local Docker instance (http://localhost:8080/fhir)
FHIR_BASE_URL=${FHIR_EXTERNAL_URL} # external server (https://fhir-bootcamp.medblocks.com/fhir)
```

## Authentication

SMART on FHIR (OAuth2 + OIDC) authentication is in progress. Keycloak runs as a Docker container and serves as the authorization server. The implementation uses the SMART App Launch (Standalone) flow with PKCE for provider portal login.

**Keycloak configuration (local):**
- Realm: `med-challenge`
- Client: `womens-health-portal`
- Admin console: `http://localhost:8180`
---

This is a publicly available repository that was created as a learning and demonstration project. It is not suited for production, so any use of this code should take that into account. Copyright (c) 2026 Chuck Sylvester. All rights reserved.


