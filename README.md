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
| HTTP Client    | requests (synchronous); httox (async, in use for auth) |
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
| clinician-alpha    | Dr. Alice Anderson, MD         | TBD      |
| clinician-bravo    | Dr. Bob Brown, DO              | TBD      |
| clinician-charlie  | Nurse Carol Chen, RN           | TBD      |
| clinician-delta    | Pharmacist David Davis, PharmD | TBD      |

**Password (all users):** `fhir#challenge#2026`

---

This is a publicly available repository that was created as a learning and demonstration project. It is not suited for production, so any use of this code should take that into account. Copyright (c) 2026 Chuck Sylvester. All rights reserved.


