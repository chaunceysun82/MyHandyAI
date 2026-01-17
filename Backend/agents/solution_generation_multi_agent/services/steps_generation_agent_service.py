import json
from typing import Dict, Any, List, Optional

from loguru import logger

from agents.solution_generation_multi_agent.prompt_templates.v1.steps_generation_agent import GENERATION_STEPS_PROMPT
from agents.solution_generation_multi_agent.steps_generation_agent.schemas import StepsPlan
from agents.solution_generation_multi_agent.steps_generation_agent.steps_generation_agent import StepsGenerationAgent
from agents.solution_generation_multi_agent.steps_generation_agent.utils import minutes_to_human, assess_complexity


class StepsGenerationAgentService:
    """Service for steps generation with business logic for context building and prompt augmentation."""

    def __init__(self, steps_generation_agent: StepsGenerationAgent):
        self.steps_generation_agent = steps_generation_agent

    def generate_steps(
            self,
            tools: Dict[str, Any],
            summary: str,
            user_answers: Optional[Dict[int, str]] = None,
            questions: Optional[List[str]] = None,
            matched_summary: Optional[str] = None,
            matched_steps: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Generate step-by-step plan with context building and prompt augmentation.
        
        Args:
            tools: Generated tools from ToolsAgent (format: {"tools": [...]})
            summary: Project summary from information gathering
            user_answers: Q&A pairs from conversation (optional)
            questions: Questions that were asked (optional)
            matched_summary: Similar project summary for adaptation (optional)
            matched_steps: Similar project steps for adaptation (optional)
            
        Returns:
            Dictionary with steps array and metadata in the format expected by worker_lambda
        """
        logger.info("Starting steps generation with context building")

        # Build system prompt with adaptation instructions if needed
        system_prompt = self._build_system_prompt(matched_summary, matched_steps)

        # Build user instruction with all context
        user_instruction = self._build_user_instruction(
            summary=summary,
            tools=tools,
            user_answers=user_answers,
            questions=questions
        )

        # Generate steps using agent
        steps_plan: StepsPlan = self.steps_generation_agent.generate_project_steps(
            system_prompt=system_prompt,
            user_instruction=user_instruction
        )

        # Convert to expected format
        return self._convert_to_worker_format(steps_plan)

    def _build_system_prompt(
            self,
            matched_summary: Optional[str] = None,
            matched_steps: Optional[Any] = None
    ) -> str:
        """Build augmented system prompt with adaptation instructions if needed."""
        # Use v1 prompt as base (already adapted for structured output)
        prompt = GENERATION_STEPS_PROMPT

        if matched_steps:
            try:
                matched_steps_text = json.dumps(matched_steps, indent=2)
            except Exception:
                matched_steps_text = str(matched_steps)

            prompt += (
                "\n\nADAPTATION INSTRUCTIONS:\n"
                "The user provided an EXISTING set of steps from a matched project below. "
                "Modify and adapt those steps so they match the NEW project summary and context provided. "
                "Update time estimates, instructions, tools needed, safety warnings, and tips where appropriate. "
                "If a step is no longer relevant, adjust or remove it, but ensure the final output lists steps numbered sequentially starting at 1. "
                "If some steps are common to both projects, you can keep them with minor adjustments. "
                "Overall, ensure the final plan is coherent, practical, and tailored to the new project summary and any user answers provided. "
                "Maintain practical ordering and clarity.\n\n"
                f"Existing matched steps:\n{matched_steps_text}\n"
            )

        if matched_summary:
            prompt += f"\n\nMatched Summary (for reference):\n{matched_summary}\n"

        return prompt

    def _build_user_instruction(
            self,
            summary: str,
            tools: Dict[str, Any],
            user_answers: Optional[Dict[int, str]] = None,
            questions: Optional[List[str]] = None
    ) -> str:
        """Build user instruction with project context, tools, and Q&A."""
        instruction_parts = [f"Project Summary:\n{summary}\n"]

        # Add tools context
        if tools and "tools" in tools:
            instruction_parts.append("Tools Context:\n")
            for tool in tools["tools"]:
                instruction_parts.append(f"- {tool.get('name', 'Unknown')}")
                instruction_parts.append(f"  Description: {tool.get('description', '')}")
                instruction_parts.append(f"  Risk Factors: {tool.get('risk_factors', '')}")
                instruction_parts.append(f"  Safety Measures: {tool.get('safety_measures', '')}")
                instruction_parts.append("")

        # Add Q&A context
        if user_answers and questions:
            instruction_parts.append("User's Answers to Questions:\n")
            skipped_questions = []

            for k, answer in user_answers.items():
                try:
                    idx = int(k)
                except Exception:
                    idx = k

                if isinstance(idx, int) and idx < len(questions):
                    question = questions[idx]
                    if answer.lower() == "skipped":
                        skipped_questions.append((idx, question))
                        instruction_parts.append(f"Q{idx + 1}: {question} - SKIPPED (will consider all possibilities)")
                    else:
                        instruction_parts.append(f"Q{idx + 1}: {question} - {answer}")

            if skipped_questions:
                instruction_parts.append(
                    "\nFor skipped questions, consider all reasonable possibilities and provide steps that cover different scenarios."
                )

        instruction_parts.append(
            "\nGenerate a comprehensive step-by-step plan for this project. "
            "Return the plan in the structured format with all required fields."
        )

        return "\n".join(instruction_parts)

    def _convert_to_worker_format(self, steps_plan: StepsPlan) -> Dict[str, Any]:
        """Convert StepsPlan to the format expected by worker_lambda."""
        steps_json = []
        for step in steps_plan.steps:
            steps_json.append({
                "order": step.step_no,
                "title": step.step_title,
                "est_time_min": step.time_minutes,
                "time_text": minutes_to_human(step.time_minutes),
                "instructions": step.instructions,
                "status": "pending",
                "tools_needed": step.tools_needed,
                "safety_warnings": step.safety_warnings,
                "tips": step.tips,
                "completed": False
            })

        # Generate project summary card
        project_summary = {
            "step_count": f"Step {1}/{steps_plan.total_steps}",
            "estimated_duration": minutes_to_human(steps_plan.estimated_time_minutes),
            "status": "Ongoing",
            "complexity": assess_complexity(steps_plan.estimated_time_minutes, steps_plan.total_steps)
        }

        return {
            "steps": steps_json,
            "total_est_time_min": steps_plan.estimated_time_minutes,
            "total_steps": steps_plan.total_steps,
            "notes": f"Total estimated time: {minutes_to_human(steps_plan.estimated_time_minutes)}",
            "project_status": "pending",
            "current_step": 1,
            "progress_percentage": 0,
            "estimated_completion": "TBD",
            "project_summary": project_summary
        }
