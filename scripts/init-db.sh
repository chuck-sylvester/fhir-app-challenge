#!/bin/bash

# exit immediately if any command returns a non-zero exit code (fails)
set -e

# Postgres HAPI FHIR user and database
psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d postgres -c "CREATE USER $POSTGRES_HAPI_USER WITH PASSWORD '$POSTGRES_HAPI_PASSWORD';"
psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d postgres -c "CREATE DATABASE $POSTGRES_HAPI_DB OWNER $POSTGRES_HAPI_USER;"

# Postgres user and database already created via POSTGRES_USER and POSTGRES_DB docker-compose variables