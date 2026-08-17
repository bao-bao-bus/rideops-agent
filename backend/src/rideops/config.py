import os
from pathlib import Path

from pydantic import BaseModel, Field


class Settings(BaseModel):
    app_name: str = "RideOps Agent API"
    environment: str = "mock"
    skills_dir: Path = Field(default_factory=lambda: Path(__file__).resolve().parents[3] / "skills")
    policies_dir: Path = Field(default_factory=lambda: Path(__file__).resolve().parents[3] / "docs" / "policies")
    database_path: Path = Field(default_factory=lambda: Path(os.getenv("RIDEOPS_DATABASE_PATH", str(Path(__file__).resolve().parents[3] / "data" / "rideops.db"))))


settings = Settings()
