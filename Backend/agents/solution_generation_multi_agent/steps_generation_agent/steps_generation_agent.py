from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from loguru import logger

from agents.solution_generation_multi_agent.steps_generation_agent.schemas import StepsPlan
from config.settings import get_settings


class StepsGenerationAgent:
    """Agent for generating step-by-step DIY/repair plans using LangChain structured output."""

    def __init__(self, model: str = "gpt-5-mini"):
        """
        Initialize the Steps Generation Agent.
        
        Args:
            model: OpenAI model to use (defaults to "gpt-5-mini")
        """
        self.settings = get_settings()
        self.llm = ChatOpenAI(
            model=model,
            max_retries=5,
            reasoning_effort="low",
            api_key=self.settings.OPENAI_API_KEY
        )

    def generate_project_steps(
            self,
            system_prompt: str,
            user_instruction: str
    ) -> StepsPlan:
        """
        Generate step-by-step plan using LangChain agent with structured output.
        
        Args:
            system_prompt: Augmented system prompt with context and adaptation instructions
            user_instruction: User instruction with project summary, tools, and Q&A context
            
        Returns:
            StepsPlan: Validated Pydantic model with structured steps
        """
        logger.info("Generating project steps with structured output")

        try:
            # Create agent with structured output
            agent = create_agent(
                model=self.llm,
                system_prompt=system_prompt,
                response_format=StepsPlan  # Uses ProviderStrategy automatically
            )

            # Invoke agent with user instruction
            result = agent.invoke(
                input={"messages": [HumanMessage(content=user_instruction)]}
            )

            # Extract structured response
            if "structured_response" not in result:
                logger.error("No structured_response in agent result")
                raise ValueError("Agent did not return structured response")

            steps_plan: StepsPlan = result["structured_response"]
            logger.info(f"Successfully generated {len(steps_plan.steps)} steps")

            return steps_plan

        except Exception as e:
            logger.error(f"Error generating project steps: {e}")
            raise
