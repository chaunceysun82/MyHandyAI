from langchain.tools import tool
from loguru import logger
from pydantic import BaseModel, Field


class HomeIssueInput(BaseModel):
    """Input schema for storing home issue information."""
    category: str = Field(
        description="The category from the Home Issue Knowledge Base. Must be one of: Plumbing, Electrical, HVAC (Heating/Cooling), Roofing & Gutters, Drywall & Painting, Flooring, Doors & Windows, Appliances, Carpentry & Woodwork, Exterior (Decks, Fences, Siding), Landscaping & Yard Work, Pest Control & Wildlife, Insulation & Weatherproofing, Smart Home / Low Voltage, General / Unknown Issue.",
        examples=["Electrical", "Plumbing", "HVAC (Heating/Cooling)"]
    )
    issue: str = Field(
        description="A concise description of the user's specific problem. Be clear and specific.",
        examples=["Dead outlet", "Leaky kitchen faucet", "AC not cooling"]
    )
    information_gathering_plan: str = Field(
        description="A detailed plan describing which key information you will now collect based on the Knowledge Base checklist for this category. Reference the specific points from the 'Key Information to Collect' section.",
        examples=[
            "I will now ask about: 1. Any sparks/smell (IMMEDIATE SAFETY CHECK), 2. Breaker or GFCI status, 3. Location and scope of the problem, 4. Recent installations"]
    )


@tool(
    description="Call this tool AFTER identifying the problem category but BEFORE beginning focused information gathering. This establishes the diagnostic framework and stores your information gathering strategy.",
    args_schema=HomeIssueInput
)
def store_home_issue(category: str, issue: str, information_gathering_plan: str) -> str:
    """Store the home issue category and information gathering plan."""
    logger.info(f"Stored home issue - Category: {category}, Issue: {issue}")
    logger.info(f"Information gathering plan: {information_gathering_plan}")
    return f"✓ Stored: {category} - {issue}. Starting information gathering."


class SummaryInput(BaseModel):
    """Input schema for storing final diagnostic summary."""
    summary: str = Field(
        description="A comprehensive, structured summary of ALL facts gathered during the information gathering phase. Include: Category, Issue, Location, Duration, Specific symptoms/details, Safety concerns, Material/equipment info (if applicable). Format clearly with bullet points or structured text.",
        examples=[
            "Category: Electrical. Issue: Dead outlet. Location: Kitchen countertop, near sink. Details: No visible discoloration initially, GFCI reset did not resolve issue, breaker not tripped. Single outlet affected, others on circuit working fine."]
    )
    hypotheses: str = Field(
        description="Your expert hypothesis about the root cause. Be professional but informative. Include risk level assessment if relevant.",
        examples=[
            "Hypothesis: Likely a loose wire connection or faulty outlet mechanism. Medium risk due to location near water source. May need outlet replacement.",
            "Hypothesis: GFCI outlet failure or upstream connection problem. Low immediate risk, but should be addressed to prevent future hazards."]
    )


@tool(
    description="Call this tool at the END of the conversation, AFTER the user has confirmed your summary. This finalizes the diagnostic phase and hands off to the Solution Generation Agent.",
    args_schema=SummaryInput
)
def store_summary(summary: str, hypotheses: str) -> str:
    """Store the final summary and hypotheses before handoff to Solution Generation Agent."""
    logger.info("Stored final summary:")
    logger.info(f"Summary: {summary}")
    logger.info(f"Hypotheses: {hypotheses}")
    return "✓ Summary stored. Ready for handoff to Solution Generation Agent."
