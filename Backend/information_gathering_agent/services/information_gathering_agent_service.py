from uuid import UUID

from dotenv import load_dotenv
from langsmith import uuid7
from loguru import logger
from pymongo.database import Database
from pymongo.collection import Collection

from information_gathering_agent.agent.information_gathering_agent import InformationGatheringAgent

load_dotenv()


class InformationGatheringAgentService:
    def __init__(self, information_gathering_agent: InformationGatheringAgent, database: Database):
        self.information_gathering_agent = information_gathering_agent
        self.project_collection: Collection = database.get_collection("Project")

    def initialize_conversation(self, project_id: str) -> tuple[UUID, str]:
        """
        Initialize a new conversation with the information gathering agent.
        
        Args:
            project_id: Project ID to associate with this conversation
        
        Returns:
            tuple[str, str]: (thread_id, initial_response)
        """
        logger.info(f"Initializing new conversation for project_id: {project_id}")
        thread_id = uuid7()
        initial_message = "Hello"

        response = self.information_gathering_agent.process_text_response(
            message=initial_message,
            thread_id=thread_id,
            project_id=project_id
        )

        logger.info(f"Successfully initialized conversation with thread_id: {thread_id}")
        return thread_id, response

    def process_message(
            self,
            thread_id: UUID,
            project_id: str,
            text: str = None,
            image_base64: str = None,
            image_mime_type: str = None
    ) -> str:
        """
        Process a message from the user (text, image, or both).
        
        Args:
            thread_id: Conversation thread ID
            project_id: Project ID associated with this conversation
            text: Optional text message
            image_base64: Optional base64-encoded image
            image_mime_type: Optional image MIME type
            
        Returns:
            Agent's response text
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

            logger.info(f"Successfully processed message for thread_id: {thread_id}")
            return response

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            raise
