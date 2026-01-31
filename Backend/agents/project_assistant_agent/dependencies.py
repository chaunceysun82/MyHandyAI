from typing import Annotated

from fastapi import Depends

from agents.project_assistant_agent.agent.project_assistant_agent import ProjectAssistantAgent
from agents.project_assistant_agent.services.project_assistant_agent_service import \
    ProjectAssistantAgentService
from database.mongodb import mongodb, MongoDB


# =============================================================================
# DATABASE DEPENDENCIES
# =============================================================================

def get_mongodb() -> MongoDB:
    return mongodb


# =============================================================================
# AGENT DEPENDENCIES
# =============================================================================
def get_project_assistant_agent() -> ProjectAssistantAgent:
    """Provide a configured ProjectAssistantAgent instance."""
    return ProjectAssistantAgent()


# =============================================================================
# SERVICE DEPENDENCIES
# =============================================================================

def get_project_assistant_agent_service(
        project_assistant_agent: Annotated[
            ProjectAssistantAgent, Depends(get_project_assistant_agent)],
        mongodb_instance: Annotated[MongoDB, Depends(get_mongodb)]) -> ProjectAssistantAgentService:
    """Provide a configured ProjectAssistantAgentService instance."""
    return ProjectAssistantAgentService(project_assistant_agent, mongodb_instance)


# =============================================================================
# TYPE ALIASES FOR DEPENDENCY INJECTION
# =============================================================================

ProjectAssistantAgentServiceDependency = Annotated[
    ProjectAssistantAgentService, Depends(get_project_assistant_agent_service)]

# Agent Dependencies    
ProjectAssistantAgentDependency = Annotated[ProjectAssistantAgent, Depends(get_project_assistant_agent)]
