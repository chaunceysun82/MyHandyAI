from typing import Annotated

from fastapi import Depends

from business.dependencies import InformationGatheringAgentDependency
from business.services.information_gathering_agent_service import InformationGatheringAgentService


# =============================================================================
# SERVICE DEPENDENCIES
# =============================================================================

def get_information_gathering_agent_service(
        information_gathering_agent: InformationGatheringAgentDependency) -> InformationGatheringAgentService:
    """Provide a configured OrchestratorService instance."""
    return InformationGatheringAgentService(information_gathering_agent)


# =============================================================================
# TYPE ALIASES FOR DEPENDENCY INJECTION
# =============================================================================

InformationGatheringAgentServiceDependency = Annotated[
    InformationGatheringAgentService, Depends(get_information_gathering_agent_service)]
