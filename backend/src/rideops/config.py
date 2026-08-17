import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field


PROJECT_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(PROJECT_ROOT / "backend" / ".env")
load_dotenv(PROJECT_ROOT / ".env")


class Settings(BaseModel):
    app_name: str = "RideOps Agent API"
    environment: str = "mock"
    skills_dir: Path = Field(default_factory=lambda: Path(__file__).resolve().parents[3] / "skills")
    policies_dir: Path = Field(default_factory=lambda: Path(__file__).resolve().parents[3] / "docs" / "policies")
    database_path: Path = Field(default_factory=lambda: Path(os.getenv("RIDEOPS_DATABASE_PATH", str(Path(__file__).resolve().parents[3] / "data" / "rideops.db"))))
    rag_index_path: Path = Field(default_factory=lambda: Path(os.getenv("RIDEOPS_RAG_INDEX_PATH", str(Path(__file__).resolve().parents[3] / "data" / "rag-index.db"))))
    embedding_provider: str = Field(default_factory=lambda: os.getenv("RIDEOPS_EMBEDDING_PROVIDER", "mock"))
    embedding_base_url: str = Field(default_factory=lambda: os.getenv("EMBEDDING_BASE_URL", ""))
    embedding_api_key: str = Field(default_factory=lambda: os.getenv("EMBEDDING_API_KEY", ""))
    embedding_model: str = Field(default_factory=lambda: os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"))
    map_provider: str = Field(default_factory=lambda: os.getenv("RIDEOPS_MAP_PROVIDER", "mock"))
    amap_api_key: str = Field(default_factory=lambda: os.getenv("AMAP_API_KEY", ""))


settings = Settings()
