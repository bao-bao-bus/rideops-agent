from pydantic import BaseModel, ConfigDict, Field


class RAGQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(min_length=1)
    top_k: int = Field(default=3, ge=1, le=10)
    min_score: float = Field(default=0.18, ge=0, le=1)


class Evidence(BaseModel):
    model_config = ConfigDict(extra="forbid")
    document_id: str
    title: str
    section: str
    content: str
    score: float = Field(ge=0, le=1)
    source: str


class RAGResponse(BaseModel):
    query: str
    answerable: bool
    evidence: list[Evidence]
    refusal_reason: str | None = None
