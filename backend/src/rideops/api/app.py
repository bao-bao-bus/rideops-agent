from fastapi import FastAPI, HTTPException

from rideops.config import settings
from rideops.repositories import MockBusinessRepository
from rideops.rag import RAGQuery, RAGResponse, build_default_service
from rideops.skills import SkillRegistry, SkillRouter
from rideops.skills.router import SkillRouteRequest, SkillRouteResult

registry = SkillRegistry(settings.skills_dir)
router = SkillRouter(registry)
business_data = MockBusinessRepository()
rag_service = build_default_service(settings.policies_dir)

app = FastAPI(title=settings.app_name, version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "environment": settings.environment}


@app.get("/api/skills")
def list_skills():
    return {"skills": registry.list()}


@app.post("/api/skills/route", response_model=SkillRouteResult)
def route_skill(request: SkillRouteRequest):
    return router.route(request.message)


@app.get("/api/skills/{skill_name}")
def load_skill(skill_name: str):
    try:
        return registry.load(skill_name)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Skill not found") from exc


@app.get("/api/demo-data")
def demo_data():
    return business_data.snapshot()


@app.post("/api/rag/search", response_model=RAGResponse)
def rag_search(request: RAGQuery):
    return rag_service.query(request.query, request.top_k, request.min_score)
