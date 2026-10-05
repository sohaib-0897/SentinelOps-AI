from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: Literal["local", "test", "production"] = "local"
    demo_mode: bool = True
    database_url: str = "sqlite+aiosqlite:///./sentinelops.db"
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    operator_token: str = Field(default="", repr=False)
    incident_provider: Literal["local"] = "local"
    log_provider: Literal["local", "gcp"] = "local"
    metrics_provider: Literal["synthetic", "gcp"] = "synthetic"
    deployment_provider: Literal["local", "gcp"] = "local"
    vector_provider: Literal["local", "bigquery"] = "local"
    llm_provider: Literal["deterministic", "vertex", "adk"] = "deterministic"
    remediation_provider: Literal["local", "gcp"] = "local"
    event_provider: Literal["local", "pubsub"] = "local"
    gcp_project_id: str = ""
    gcp_region: str = "us-central1"
    vertex_location: str = "us-central1"
    gemini_model: str = "gemini-2.5-flash"
    bigquery_dataset: str = "sentinelops"
    pubsub_topic: str = "sentinelops-events"
    pubsub_subscription: str = "sentinelops-analytics"
    demo_service_url: str = "http://127.0.0.1:8001"
    connect_demo_service: bool = False
    event_buffer_size: int = Field(default=256, ge=16, le=4096)
    cloud_sql_instance: str = ""
    cloud_sql_user: str = ""
    cloud_sql_database: str = "sentinelops"

    @model_validator(mode="after")
    def production_requires_security(self) -> "Settings":
        if self.app_env == "production" and (len(self.operator_token) < 32 or self.demo_mode):
            raise ValueError("Production requires DEMO_MODE=false and an OPERATOR_TOKEN of at least 32 characters")
        if self.app_env == "production" and not self.cloud_sql_instance and self.database_url.startswith("sqlite"):
            raise ValueError("Production requires persistent PostgreSQL or a CLOUD_SQL_INSTANCE; SQLite is local-only")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
