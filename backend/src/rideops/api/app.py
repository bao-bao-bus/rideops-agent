from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from rideops.agents import IncidentWorkflow
from rideops.api.runs import create_runs_router
from rideops.config import settings
from rideops.rag import RAGQuery, RAGResponse, build_default_service
from rideops.rag.embeddings import build_embedding_provider
from rideops.repositories import SQLiteBusinessRepository
from rideops.services import BusinessTools
from rideops.skills import SkillRegistry, SkillRouter
from rideops.skills.router import SkillRouteRequest, SkillRouteResult

registry = SkillRegistry(settings.skills_dir)
router = SkillRouter(registry)
rag_service = build_default_service(settings.policies_dir, settings.rag_index_path, build_embedding_provider(settings))


def create_app(database_path=None) -> FastAPI:
    business_data = SQLiteBusinessRepository(database_path or settings.database_path)
    incident_workflow = IncidentWorkflow(rag_service, business_data, router, BusinessTools(business_data))
    application = FastAPI(title=settings.app_name, version="0.2.0")
    application.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"], allow_methods=["*"], allow_headers=["*"])
    application.include_router(create_runs_router(incident_workflow, business_data))

    @application.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "environment": settings.environment}

    @application.get("/api/skills")
    def list_skills():
        return {"skills": registry.list()}

    @application.post("/api/skills/route", response_model=SkillRouteResult)
    def route_skill(request: SkillRouteRequest):
        return router.route(request.message)

    @application.get("/api/skills/{skill_name}")
    def load_skill(skill_name: str):
        try:
            return registry.load(skill_name)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Skill not found") from exc

    @application.get("/api/demo-data")
    def demo_data():
        return business_data.snapshot()

    @application.post("/api/rag/search", response_model=RAGResponse)
    def rag_search(request: RAGQuery):
        return rag_service.query(request.query, request.top_k, request.min_score)

    return application


app = create_app()
