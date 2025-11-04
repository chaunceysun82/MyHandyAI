from uuid import uuid4

from dotenv import load_dotenv
from loguru import logger

from business.agents.information_gathering_agent.information_gathering_agent import InformationGatheringAgent

load_dotenv()


class InformationGatheringAgentService:
    def __init__(self, information_gathering_agent: InformationGatheringAgent):
        self.information_gathering_agent = information_gathering_agent

    def initialize_conversation(self) -> tuple[str, str]:
        """
        Initialize a new conversation with the information gathering agent.
        
        Returns:
            tuple[str, str]: (thread_id, initial_response)
        """
        logger.info("Initializing new conversation")
        thread_id = str(uuid4())
        initial_message = "Hello"

        response = self.information_gathering_agent.process_text_response(
            message=initial_message,
            thread_id=thread_id
        )

        logger.info(f"Successfully initialized conversation with thread_id: {thread_id}")
        return thread_id, response

    def process_message(
            self,
            thread_id: str,
            text: str = None,
            image_base64: str = None,
            image_mime_type: str = None
    ) -> str:
        """
        Process a message from the user (text, image, or both).
        
        Args:
            thread_id: Conversation thread ID
            text: Optional text message
            image_base64: Optional base64-encoded image
            image_mime_type: Optional image MIME type
            
        Returns:
            Agent's response text
        """
        logger.info(f"Orchestrator processing message for thread_id: {thread_id}")
        logger.debug(f"Has text: {text is not None}, has image: {image_base64 is not None}")

        try:
            if image_base64:
                # Process image with optional text
                logger.debug("Processing image message")
                response = self.information_gathering_agent.process_image_response(
                    text=text,
                    image_base64=image_base64,
                    mime_type=image_mime_type or "image/jpeg",
                    thread_id=thread_id
                )
            elif text:
                # Process text only
                logger.debug("Processing text message")
                response = self.information_gathering_agent.process_text_response(
                    message=text,
                    thread_id=thread_id
                )
            else:
                raise ValueError("Either text or image must be provided")

            logger.info(f"Successfully processed message for thread_id: {thread_id}")
            return response

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            raise
