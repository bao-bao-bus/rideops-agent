from rideops.agents.customer_service import CustomerServiceSupervisor
from rideops.domain.models import CustomerServiceQueryRequest, CustomerServiceResponse
from rideops.rag import RAGService
from rideops.services.business_tools import BusinessTools
from rideops.services.long_rental import LongRentalService
from rideops.skills import SkillRouter


class CustomerService:
    """Compatibility facade for the deterministic multi-agent customer-service supervisor."""

    def __init__(self, router: SkillRouter, rag_service: RAGService, business_tools: BusinessTools, long_rental_service: LongRentalService) -> None:
        self.supervisor = CustomerServiceSupervisor(router, rag_service, business_tools, long_rental_service)

    def query(self, request: CustomerServiceQueryRequest) -> CustomerServiceResponse:
        return self.supervisor.query(request)
