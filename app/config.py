# -----------------------------------------------------------------
# app/config.py
# -----------------------------------------------------------------
# FastAPI application configuration using Pydantic
# -----------------------------------------------------------------

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings (BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",  # load from this file + actual env vars
        extra="ignore"    # silently ignore env vars that don't match a field
    )

    # Application
    app_name: str = "FHIR Demo"
    app_version: str = "0.0.0.0"
    app_env: str = "development"
    app_debug: bool = False

    # Logging
    log_level: str = "INFO"

    # FHIR server endpoints
    fhir_base_url: str
    fhir_local_url: str
    fhir_external_url: str
    fhir_external_api_token: str = ""

    # PostgreSQL app database
    # TBD

    # Keycloak / SMART auth
    keycloak_url: str = "http://localhost:8180"
    keycloak_realm: str = "med-challenge"
    keycloak_client_id: str = "womens-health-portal"
    keycloak_client_secret: str
    session_secret_key: str

# Module-level singleton - instantiated once when module is first imported
settings = Settings()