from typing import Annotated

from fastapi import Depends

from business.agents.information_gathering_agent.information_gathering_agent import InformationGatheringAgent


# =============================================================================
# AGENT DEPENDENCIES
# =============================================================================
def get_information_gathering_agent() -> InformationGatheringAgent:
    """Provide a configured InformationGatheringAgent instance."""
    return InformationGatheringAgent()


# =============================================================================
# TYPE ALIASES FOR DEPENDENCY INJECTION
# =============================================================================

# Agent Dependencies    
InformationGatheringAgentDependency = Annotated[InformationGatheringAgent, Depends(get_information_gathering_agent)]
