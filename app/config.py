# -----------------------------------------------------------------
# app/config.py
# -----------------------------------------------------------------
# FastAPI application configuration using Pydantic
# -----------------------------------------------------------------

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings (BaseSettings):
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

    # PostgreSQL app database
    # TBD


    model_config = SettingsConfigDict(
        env_file=".env",  # load from this file + actual env vars
        extra="ignore"    # silently ignore env vars that don't match a field
    )

# Module-level singleton - instantiated once when module is first imported
settings = Settings()