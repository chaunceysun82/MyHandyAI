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

        response = self.information_gathering_agent.process_text_response(
            message=initial_message,
            thread_id=thread_id,
            project_id=project_id
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
            if image_base64:
                # Process image with optional text
                logger.debug("Processing image message")
                response = self.information_gathering_agent.process_image_response(
                    text=text,
                    image_base64=image_base64,
                    mime_type=image_mime_type or "image/jpeg",
                    thread_id=thread_id,
                    project_id=project_id
                )
            elif text:
                # Process text only
                logger.debug("Processing text message")
                response = self.information_gathering_agent.process_text_response(
                    message=text,
                    thread_id=thread_id,
                    project_id=project_id
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
