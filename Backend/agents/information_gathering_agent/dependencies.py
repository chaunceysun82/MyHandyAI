from typing import Annotated

from fastapi import Depends

from agents.information_gathering_agent.agent.information_gathering_agent import InformationGatheringAgent
from agents.information_gathering_agent.services.information_gathering_agent_service import \
    InformationGatheringAgentService
from database.mongodb import mongodb, MongoDB


# =============================================================================
# DATABASE DEPENDENCIES
# =============================================================================

def get_mongodb() -> MongoDB:
    return mongodb


# =============================================================================
# AGENT DEPENDENCIES
# =============================================================================
def get_information_gathering_agent() -> InformationGatheringAgent:
    """Provide a configured InformationGatheringAgent instance."""
    return InformationGatheringAgent()


# =============================================================================
# SERVICE DEPENDENCIES
# =============================================================================

def get_information_gathering_agent_service(
        information_gathering_agent: Annotated[
            InformationGatheringAgent, Depends(get_information_gathering_agent)],
        mongodb_instance: Annotated[MongoDB, Depends(get_mongodb)]) -> InformationGatheringAgentService:
    """Provide a configured OrchestratorService instance."""
    return InformationGatheringAgentService(information_gathering_agent, mongodb_instance)


# =============================================================================
# TYPE ALIASES FOR DEPENDENCY INJECTION
# =============================================================================

InformationGatheringAgentServiceDependency = Annotated[
    InformationGatheringAgentService, Depends(get_information_gathering_agent_service)]

# Agent Dependencies    
InformationGatheringAgentDependency = Annotated[InformationGatheringAgent, Depends(get_information_gathering_agent)]
