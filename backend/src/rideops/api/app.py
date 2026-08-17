from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from rideops.agents import IncidentWorkflow
from rideops.agents.model_provider import build_agent_model_provider
from rideops.api.runs import create_runs_router
from rideops.api.pretrip import create_pretrip_router
from rideops.api.long_rental import create_long_rental_router
from rideops.config import settings
from rideops.domain.models import CustomerServiceQueryRequest, CustomerServiceResponse, CustomerSessionCreateRequest, CustomerSessionDetailResponse, CustomerSessionResponse
from rideops.integrations import MapProvider, build_map_provider
from rideops.rag import RAGQuery, RAGResponse, build_default_service
from rideops.rag.embeddings import build_embedding_provider
from rideops.repositories import BusinessToolError, SQLiteBusinessRepository
from rideops.services import BusinessTools, CustomerService, LongRentalService
from rideops.skills import SkillRegistry, SkillRouter
from rideops.skills.router import SkillRouteRequest, SkillRouteResult

registry = SkillRegistry(settings.skills_dir)
router = SkillRouter(registry)
rag_service = build_default_service(settings.policies_dir, settings.rag_index_path, build_embedding_provider(settings))


def create_app(database_path=None, map_provider: MapProvider | None = None) -> FastAPI:
    business_data = SQLiteBusinessRepository(database_path or settings.database_path)
    selected_map_provider = map_provider or build_map_provider(settings.map_provider, settings.amap_api_key)
    business_tools = BusinessTools(business_data, map_provider=selected_map_provider)
    long_rental_service = LongRentalService(business_data)
    customer_service = CustomerService(router, rag_service, business_tools, long_rental_service, business_data)
    incident_workflow = IncidentWorkflow(rag_service, business_data, router, business_tools, event_sink=business_data.append_event)
    agent_model_provider = build_agent_model_provider(settings)
    application = FastAPI(title=settings.app_name, version="0.2.0")
    application.state.agent_model_provider = agent_model_provider
    application.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"], allow_methods=["*"], allow_headers=["*"])
    application.include_router(create_runs_router(incident_workflow, business_data))
    application.include_router(create_pretrip_router(business_tools))
    application.include_router(create_long_rental_router(long_rental_service))

    @application.post("/api/customer-service/query", response_model=CustomerServiceResponse)
    def customer_service_query(request: CustomerServiceQueryRequest):
        try:
            return customer_service.query(request)
        except BusinessToolError as exc:
            status_code = 404 if exc.code == "NOT_FOUND" else 403 if exc.code == "FORBIDDEN" else 422
            raise HTTPException(status_code=status_code, detail={"code": exc.code, "message": exc.message}) from exc

    @application.post("/api/customer-service/sessions", response_model=CustomerSessionResponse)
    def create_customer_service_session(request: CustomerSessionCreateRequest):
        return customer_service.create_session(request.user_id)

    @application.get("/api/customer-service/sessions/{session_id}", response_model=CustomerSessionDetailResponse)
    def get_customer_service_session(session_id: str, user_id: str = "usr_demo_001"):
        try:
            return customer_service.get_session(session_id, user_id)
        except BusinessToolError as exc:
            status_code = 404 if exc.code == "NOT_FOUND" else 403
            raise HTTPException(status_code=status_code, detail={"code": exc.code, "message": exc.message}) from exc

    @application.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "environment": settings.environment}

    @application.get("/api/agent-model/status")
    def agent_model_status() -> dict:
        return application.state.agent_model_provider.status().__dict__

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
