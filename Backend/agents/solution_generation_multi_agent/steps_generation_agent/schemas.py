from typing import List

from pydantic import BaseModel, Field


class Step(BaseModel):
    """A single step in the DIY/repair plan."""
    step_no: int = Field(..., description="Step number (1-indexed)", ge=1)
    step_title: str = Field(..., description="Title of the step")
    time_minutes: int = Field(..., description="Estimated time for this step in minutes", ge=1)
    instructions: List[str] = Field(..., description="List of specific actionable instructions for this step",
                                    min_length=1)
    tools_needed: List[str] = Field(default=[], description="List of tools required for this specific step")
    safety_warnings: List[str] = Field(default=[],
                                       description="List of safety considerations and precautions for this step")
    tips: List[str] = Field(default=[], description="List of helpful tips and tricks for this step")


class StepsPlan(BaseModel):
    """Complete step-by-step plan for a DIY/repair project."""
    total_steps: int = Field(..., description="Total number of steps in the plan", ge=1)
    estimated_time_minutes: int = Field(..., description="Total estimated time for the entire project in minutes", ge=1)
    steps: List[Step] = Field(..., description="List of steps in sequential order", min_length=1)
