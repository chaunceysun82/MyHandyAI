from typing import Dict, List, Tuple
from uuid import UUID

from bson import ObjectId
from langsmith import uuid7
from loguru import logger
from pymongo.collection import Collection

from agents.information_gathering_agent.agent.information_gathering_agent import InformationGatheringAgent
from database.enums.project import InformationGatheringConversationStatus
from database.mongodb import MongoDB


class InformationGatheringAgentService:
    def __init__(self, information_gathering_agent: InformationGatheringAgent, mongodb: MongoDB):
        self.information_gathering_agent = information_gathering_agent
        self.mongodb = mongodb
        self.project_collection: Collection = mongodb.get_collection("Project")
        self.user_collection: Collection = mongodb.get_collection("User")

    def initialize_conversation(self, project_id: str) -> Tuple[UUID, str, str]:
        """
        Initialize a new conversation with the information gathering agent.
        
        Args:
            project_id: Project ID to associate with this conversation
        
        Returns:
            Tuple of (thread_id, initial_response, conversation_status)
        """
        logger.info(f"Initializing new conversation for project_id: {project_id}")
        thread_id = uuid7()
        project = self.project_collection.find_one({"_id": ObjectId(project_id)})
        initial_message = f'Hello, I want to gather information regarding my project titled {project.get("projectTitle", "No Title")}.'

        # Set conversation status to PENDING and store thread_id
        self.project_collection.update_one(
            {"_id": ObjectId(project_id)},
            {
                "$set": {
                    "information_gathering_conversation_status": InformationGatheringConversationStatus.PENDING.value,
                    "thread_id": str(thread_id)
                }
            }
        )
        logger.info(f"Set conversation status to PENDING and stored thread_id for project_id: {project_id}")

        # Build user context
        context = self._build_context(project_id)

        response = self.information_gathering_agent.process_text_response(
            message=initial_message,
            thread_id=thread_id,
            project_id=project_id,
            context=context
        )

        # Get the conversation status (should be PENDING at this point)
        conversation_status = InformationGatheringConversationStatus.PENDING.value

        logger.info(f"Successfully initialized conversation with thread_id: {thread_id}")
        return thread_id, response, conversation_status

    def process_message(
            self,
            thread_id: UUID,
            project_id: str,
            text: str = None,
            image_base64: str = None,
            image_mime_type: str = None
    ) -> Tuple[str, str]:
        """
        Process a message from the user (text, image, or both).
        
        Args:
            thread_id: Conversation thread ID
            project_id: Project ID associated with this conversation
            text: Optional text message
            image_base64: Optional base64-encoded image
            image_mime_type: Optional image MIME type
            
        Returns:
            Tuple of (agent_response, conversation_status)
        """
        logger.info(f"Orchestrator processing message for thread_id: {thread_id}, project_id: {project_id}")
        logger.debug(f"Has text: {text is not None}, has image: {image_base64 is not None}")

        try:
            # Build user context
            context = self._build_context(project_id)

            if image_base64:
                # Process image with optional text
                logger.debug("Processing image message")
                response = self.information_gathering_agent.process_image_response(
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
                response = self.information_gathering_agent.process_text_response(
                    message=text,
                    thread_id=thread_id,
                    project_id=project_id,
                    context=context
                )
            else:
                raise ValueError("Either text or image must be provided")

            # Get current conversation status from project
            project = self.project_collection.find_one({"_id": ObjectId(project_id)})
            status = project.get("information_gathering_conversation_status",
                                 InformationGatheringConversationStatus.PENDING.value)

            logger.info(f"Successfully processed message for thread_id: {thread_id}, status: {status}")
            return response, status

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            raise

    def get_conversation_status(self, project_id: str) -> str:
        """
        Get the current conversation status for a project.
        
        Args:
            project_id: Project ID
            
        Returns:
            Current conversation status
        """
        project = self.project_collection.find_one({"_id": ObjectId(project_id)})
        if not project:
            return InformationGatheringConversationStatus.PENDING.value

        return project.get("information_gathering_conversation_status",
                           InformationGatheringConversationStatus.PENDING.value)

    def get_history(self, thread_id: UUID) -> List[Dict]:
        return self.information_gathering_agent.get_history(thread_id)

    def get_thread_id(self, project_id: str) -> Dict:
        """
        Get thread_id and conversation_status for a project.
        
        Args:
            project_id: Project ID
            
        Returns:
            Dictionary with thread_id and conversation_status
        """
        project = self.project_collection.find_one({"_id": ObjectId(project_id)})

        if not project:
            return {
                "thread_id": None,
                "conversation_status": InformationGatheringConversationStatus.PENDING.value
            }

        thread_id = project.get("thread_id")
        conversation_status = project.get(
            "information_gathering_conversation_status",
            InformationGatheringConversationStatus.PENDING.value
        )

        return {
            "thread_id": thread_id,
            "conversation_status": conversation_status
        }

    def _build_context(self, project_id: str) -> str:
        """
        Build formatted context string from user data.
        
        Args:
            project_id: Project ID
            
        Returns:
            Formatted context string for the agent
        """
        try:
            # Fetch project data to get user ID
            project = self.project_collection.find_one({"_id": ObjectId(project_id)})
            if not project:
                logger.warning(f"Project not found: {project_id}")
                return "User information not available."

            # Get user information
            user_id = project.get("userId")
            user_name = None
            user_email = None
            user_state = None
            user_country = None
            user_experience = None
            user_tools = None
            user_confidence = None

            if user_id:
                user = self.user_collection.find_one({"_id": ObjectId(user_id)})
                if user:
                    user_name = user.get("name") or user.get(
                        "displayName") or f"{user.get('firstname', '')} {user.get('lastname', '')}".strip() or None
                    user_email = user.get("email")
                    user_state = user.get("state")
                    user_country = user.get("country")
                    user_experience = user.get("experienceLevel")
                    user_tools = user.get("tools")
                    user_confidence = user.get("confidence")

            # Build context sections
            context_parts = []

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
            if user_tools:
                context_parts.append(f"**Tools Available:** {user_tools}")
            if user_confidence is not None:
                context_parts.append(f"**Confidence Level:** {user_confidence}")
            context_parts.append("")

            return "\n".join(context_parts)

        except Exception as e:
            logger.error(f"Error building context: {e}")
            return f"Error loading user context: {str(e)}"
