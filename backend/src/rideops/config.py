from pathlib import Path

from pydantic import BaseModel, Field


class Settings(BaseModel):
    app_name: str = "RideOps Agent API"
    environment: str = "mock"
    skills_dir: Path = Field(default_factory=lambda: Path(__file__).resolve().parents[3] / "skills")
    policies_dir: Path = Field(default_factory=lambda: Path(__file__).resolve().parents[3] / "docs" / "policies")


settings = Settings()
