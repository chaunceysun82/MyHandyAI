from typing import Annotated

from fastapi import Depends
from pymongo.database import Database

from information_gathering_agent.agent.information_gathering_agent import InformationGatheringAgent
from information_gathering_agent.database.mongodb import mongodb
from information_gathering_agent.services.information_gathering_agent_service import InformationGatheringAgentService


# =============================================================================
# DATABASE DEPENDENCIES
# =============================================================================

def get_database() -> Database:
    return mongodb.get_database()


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
        database: Annotated[Database, Depends(get_database)]) -> InformationGatheringAgentService:
    """Provide a configured OrchestratorService instance."""
    return InformationGatheringAgentService(information_gathering_agent, database)


# =============================================================================
# TYPE ALIASES FOR DEPENDENCY INJECTION
# =============================================================================

InformationGatheringAgentServiceDependency = Annotated[
    InformationGatheringAgentService, Depends(get_information_gathering_agent_service)]

# Agent Dependencies    
InformationGatheringAgentDependency = Annotated[InformationGatheringAgent, Depends(get_information_gathering_agent)]
