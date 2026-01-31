from typing import Dict, List, Tuple, Optional
from uuid import UUID

from bson import ObjectId
from loguru import logger
from pymongo.collection import Collection

from agents.project_assistant_agent.agent.project_assistant_agent import ProjectAssistantAgent
from database.mongodb import MongoDB


class ProjectAssistantAgentService:
    def __init__(self, project_assistant_agent: ProjectAssistantAgent, mongodb: MongoDB):
        self.project_assistant_agent = project_assistant_agent
        self.mongodb = mongodb
        self.project_collection: Collection = mongodb.get_collection("Project")
        self.user_collection: Collection = mongodb.get_collection("User")

    def _build_context(
            self,
            project_id: str,
            step_number: Optional[int] = None
    ) -> str:
        """
        Build formatted context string from project and user data.
        Includes ALL steps (completed and pending) for complete context awareness.
        
        Args:
            project_id: Project ID
            step_number: Current step number (-1 for overview, 0 for tools, >=1 for specific step)
            
        Returns:
            Formatted context string for the agent
        """
        try:
            # Fetch project data
            project = self.project_collection.find_one({"_id": ObjectId(project_id)})
            if not project:
                logger.warning(f"Project not found: {project_id}")
                return "Project data not available."

            # Get user information
            user_id = project.get("userId")
            user_name = None
            user_email = None
            user_state = None
            user_country = None
            user_experience = None

            if user_id:
                user = self.user_collection.find_one({"_id": ObjectId(user_id)})
                if user:
                    user_name = user.get("name") or user.get(
                        "displayName") or f"{user.get('firstname', '')} {user.get('lastname', '')}".strip() or None
                    user_email = user.get("email")
                    user_state = user.get("state")
                    user_country = user.get("country")
                    user_experience = user.get("experienceLevel")

            # Extract project information
            problem_summary = project.get("summary") or project.get("user_description") or ""
            project_title = project.get("projectTitle") or "Untitled Project"

            # Extract steps data
            step_generation = project.get("step_generation", {})
            steps = step_generation.get("steps", [])
            total_steps = len(steps) if steps else 0

            # Extract tools data
            tools_data = project.get("tools", {}) or project.get("tool_generation", {}) or {}
            tools_list = tools_data.get("tools", []) if isinstance(tools_data, dict) else []

            # Build context sections
            context_parts = []

            # Project Overview Section
            context_parts.append("## Project Information")
            context_parts.append(f"**Project Title:** {project_title}")
            if problem_summary:
                context_parts.append(f"**Problem Summary:** {problem_summary}")
            context_parts.append(f"**Total Steps:** {total_steps}")
            context_parts.append("")

            # User Information Section
            context_parts.append("## User Information")
            if user_name:
                context_parts.append(f"**Name:** {user_name}")
            if user_email:
                context_parts.append(f"**Email:** {user_email}")
            if user_state:
                context_parts.append(f"**State:** {user_state}")
            if user_country:
                context_parts.append(f"**Country:** {user_country}")
            if user_experience:
                context_parts.append(f"**Experience Level:** {user_experience}")
            context_parts.append("")

            # Tools and Materials Section
            if tools_list:
                context_parts.append("## Tools and Materials Required")
                for tool in tools_list:
                    tool_name = tool.get("name", "Unknown Tool")
                    context_parts.append(f"**{tool_name}**")

                    if step_number == 0:  # Show full details on tools page
                        description = tool.get("description", "")
                        price = tool.get("price", "")
                        risk_factors = tool.get("risk_factors", "")
                        safety_measures = tool.get("safety_measures", "")

                        if description:
                            context_parts.append(f"  - Description: {description}")
                        if price:
                            context_parts.append(f"  - Estimated Price: {price}")
                        if risk_factors:
                            context_parts.append(f"  - Risk Factors: {risk_factors}")
                        if safety_measures:
                            context_parts.append(f"  - Safety Measures: {safety_measures}")
                context_parts.append("")

            # ALL Project Steps (Complete Context Awareness)
            if steps:
                context_parts.append("## All Project Steps (Complete Context)")
                context_parts.append(
                    "You have access to ALL steps in the project, whether completed or pending. Use this information to provide comprehensive guidance.")
                context_parts.append("")

                for idx, step in enumerate(steps, 1):
                    step_title = step.get("title", f"Step {idx}")
                    step_time = step.get("time_text", "")
                    completed = step.get("completed", False)
                    status = "✓ Completed" if completed else "○ Pending"

                    context_parts.append(f"### Step {idx}: {step_title} - {status}")

                    if step_time:
                        context_parts.append(f"**Estimated Time:** {step_time}")

                    tools_needed = step.get("tools_needed", [])
                    if tools_needed:
                        tools_str = ", ".join([str(t) for t in tools_needed[:15]])
                        context_parts.append(f"**Tools Needed:** {tools_str}")

                    instructions = step.get("instructions", [])
                    if instructions:
                        context_parts.append("**Instructions:**")
                        for i, instruction in enumerate(instructions, 1):
                            context_parts.append(f"  {i}. {instruction}")

                    safety_warnings = step.get("safety_warnings", [])
                    if safety_warnings:
                        context_parts.append("**Safety Warnings:**")
                        for warning in safety_warnings:
                            context_parts.append(f"  ⚠️ {warning}")

                    tips = step.get("tips", [])
                    if tips:
                        context_parts.append("**Tips:**")
                        for tip in tips:
                            context_parts.append(f"  💡 {tip}")

                    context_parts.append("")

                context_parts.append("")

            # Current Step Context (if on a specific step)
            if step_number is not None and step_number >= 1:
                # Convert to 0-based index
                step_index = step_number - 1
                if 0 <= step_index < len(steps):
                    step = steps[step_index]
                    context_parts.append("## Current Step Context")
                    context_parts.append(f"**You are currently assisting with Step {step_number}.**")
                    context_parts.append(f"**Step Title:** {step.get('title', f'Step {step_number}')}")
                    context_parts.append("")
                elif step_index < 0:
                    context_parts.append("## Current Step Context")
                    context_parts.append("**You are on the project overview page.**")
                    context_parts.append("")
            elif step_number == 0:
                context_parts.append("## Current Step Context")
                context_parts.append("**You are on the Tools and Materials page.**")
                context_parts.append("The user is reviewing the tools and materials needed for this project.")
                context_parts.append(
                    "Provide detailed information about each tool including descriptions, prices, risk factors, and safety measures.")
                context_parts.append("")
            elif step_number == -1 or step_number is None:
                context_parts.append("## Current Step Context")
                context_parts.append("**You are on the project overview page.**")
                context_parts.append("The user can ask general questions about the project, steps, or tools.")
                context_parts.append("")

            return "\n".join(context_parts)

        except Exception as e:
            logger.error(f"Error building context: {e}")
            return f"Error loading project context: {str(e)}"

    def _create_initial_message(self, project_id: str, step_number: Optional[int] = None) -> str:
        """
        Create a contextual initial user message based on the current step number.
        Similar to information gathering agent's pattern - creates a message FROM the user.
        
        Args:
            project_id: Project ID to get project title
            step_number: Current step number (-1 for overview, 0 for tools, >=1 for specific step)
            
        Returns:
            Contextual initial user message string
        """
        # Fetch project to get title
        project = self.project_collection.find_one({"_id": ObjectId(project_id)})
        project_title = project.get("projectTitle", "my project") if project else "my project"

        if step_number is None or step_number == -1:
            return f"Hello, I need help with my project titled {project_title}."
        elif step_number == 0:
            return f"Hello, I need help understanding the tools and materials needed for my project titled {project_title}."
        elif step_number >= 1:
            return f"Hello, I need help with Step {step_number} of my project titled {project_title}."
        else:
            return f"Hello, I need help with my project titled {project_title}."

    def initialize_conversation(
            self,
            thread_id: UUID,
            project_id: str,
            step_number: Optional[int] = None
    ) -> str:
        """
        Initialize a conversation with the project assistant agent by sending a default initial message.
        Uses an existing thread_id from the information gathering agent.
        
        Args:
            thread_id: Existing thread ID from information gathering agent
            project_id: Project ID associated with this conversation
            step_number: Current step number (-1 for overview, 0 for tools, >=1 for specific step)
            
        Returns:
            Agent's initial response message
        """
        logger.info(
            f"Initializing project assistant conversation for thread_id: {thread_id}, project_id: {project_id}, step_number: {step_number}")

        # Build context for the agent
        context = self._build_context(project_id, step_number)

        # Create a contextual initial user message based on step_number
        initial_message = self._create_initial_message(project_id, step_number)

        # Process the initial message through the agent
        response = self.project_assistant_agent.process_text_response(
            message=initial_message,
            thread_id=thread_id,
            project_id=project_id,
            context=context
        )

        logger.info(f"Successfully initialized conversation with thread_id: {thread_id}")
        return response

    def process_message(
            self,
            thread_id: UUID,
            project_id: str,
            text: str = None,
            image_base64: str = None,
            image_mime_type: str = None,
            step_number: Optional[int] = None
    ) -> Tuple[str, str]:
        """
        Process a message from the user (text, image, or both).
        
        Args:
            thread_id: Conversation thread ID
            project_id: Project ID associated with this conversation
            text: Optional text message
            image_base64: Optional base64-encoded image
            image_mime_type: Optional image MIME type
            step_number: Current step number (-1 for overview, 0 for tools, >=1 for specific step)
            
        Returns:
            Tuple of (agent_response, conversation_status)
        """
        logger.info(
            f"Processing message for thread_id: {thread_id}, project_id: {project_id}, step_number: {step_number}")
        logger.debug(f"Has text: {text is not None}, has image: {image_base64 is not None}")

        try:
            # Build context for the agent
            context = self._build_context(project_id, step_number)

            if image_base64:
                # Process image with optional text
                logger.debug("Processing image message")
                response = self.project_assistant_agent.process_image_response(
                    text=text,
                    image_base64=image_base64,
                    mime_type=image_mime_type or "image/jpeg",
                    thread_id=thread_id,
                    project_id=project_id,
                    context=context
                )
            elif text:
                # Process text only
                logger.debug("Processing text message")
                response = self.project_assistant_agent.process_text_response(
                    message=text,
                    thread_id=thread_id,
                    project_id=project_id,
                    context=context
                )
            else:
                raise ValueError("Either text or image must be provided")

            logger.info(f"Successfully processed message for thread_id: {thread_id}")
            # Project assistant doesn't have conversation status, return empty string
            return response, ""

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            raise

    def get_history(self, thread_id: UUID) -> List[Dict]:
        """Get conversation history for a thread."""
        return self.project_assistant_agent.get_history(thread_id)

    def get_thread_id(self, project_id: str) -> Dict:
        """
        Get thread_id for a project.
        Uses the same thread_id as the information gathering agent since they share the same conversation thread.
        
        Args:
            project_id: Project ID
            
        Returns:
            Dictionary with thread_id
        """
        project = self.project_collection.find_one({"_id": ObjectId(project_id)})
        
        if not project or "thread_id" not in project:
            return {"thread_id": None}
        
        return {"thread_id": project["thread_id"]}
