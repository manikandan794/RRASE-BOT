from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    app_name: str
    app_env: str
    database: bool
    # AI provider health is added in Phase 5 once providers exist.
