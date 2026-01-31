from contextlib import contextmanager
from typing import Dict, List, Optional
from uuid import UUID

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.mongodb import MongoDBSaver
from loguru import logger

from agents.project_assistant_agent.agent.prompt_templates.v1.project_assistant_agent import \
    build_system_prompt
from config.settings import get_settings


class ProjectAssistantAgent:
    def __init__(self):
        self.settings = get_settings()
        self.llm = ChatOpenAI(
            model=self.settings.PROJECT_ASSISTANT_AGENT_MODEL,
            max_retries=5,
            reasoning_effort="low",
            api_key=self.settings.OPENAI_API_KEY
        )

    @contextmanager
    def get_checkpointer(self):
        """Context manager for MongoDB checkpointer."""
        with MongoDBSaver.from_conn_string(
                conn_string=self.settings.MONGODB_URI,
                db_name=self.settings.MYHANDYAI_AGENTS_CHECKPOINT_DATABASE,
                checkpoint_collection_name=self.settings.MYHANDYAI_AGENTS_CHECKPOINT_COLLECTION_NAME,
                writes_collection_name=self.settings.MYHANDYAI_AGENTS_CHECKPOINT_WRITES_COLLECTION_NAME
        ) as checkpointer:
            yield checkpointer

    def process_text_response(
            self,
            message: str,
            thread_id: UUID,
            project_id: str,
            context: str
    ) -> str:
        """
        Process a text message from the user.
        
        Args:
            message: User's text message
            thread_id: Conversation thread ID for persistence
            project_id: Project ID associated with this conversation
            context: Formatted project and step context string
            
        Returns:
            Agent's response text
        """
        logger.info(f"Processing text response for thread_id: {thread_id}, project_id: {project_id}")
        logger.debug(f"User message: {message}")

        try:
            with self.get_checkpointer() as checkpointer:
                # Build system prompt with context injected
                system_prompt = build_system_prompt(context)

                # Create agent with checkpointer (no tools needed)
                agent = create_agent(
                    model=self.llm,
                    tools=[],  # No tools for project assistant
                    system_prompt=system_prompt,
                    checkpointer=checkpointer,
                )

                config: RunnableConfig = {
                    "configurable": {
                        "thread_id": str(thread_id),
                        "project_id": project_id,
                        "recursion_limit": 20
                    }
                }

                result = agent.invoke(
                    input={"messages": [HumanMessage(content=message)]},
                    config=config
                )

                if result and "messages" in result:
                    last_message = result["messages"][-1]
                    logger.info(f"Agent responded successfully for thread_id: {thread_id}")
                    logger.debug(f"Project Assistant Agent response: {last_message.content}")

                    return last_message.content
                else:
                    logger.error("No response from agent")
                    return "I apologize, but I encountered an issue processing your request."

        except Exception as e:
            logger.error(f"Error in process_text_response: {e}")
            return "I apologize, but I'm having trouble processing your request right now. Please try again."

    def process_image_response(
            self,
            text: Optional[str],
            image_base64: str,
            mime_type: str,
            thread_id: UUID,
            project_id: str,
            context: str
    ) -> str:
        """
        Process a message with an image from the user.
        
        Args:
            text: Optional text accompanying the image
            image_base64: Base64-encoded image data
            mime_type: MIME type of the image (e.g., 'image/jpeg')
            thread_id: Conversation thread ID for persistence
            project_id: Project ID associated with this conversation
            context: Formatted project and step context string
            
        Returns:
            Agent's response text
        """
        logger.info(f"Processing image response for thread_id: {thread_id}, project_id: {project_id}")
        logger.debug(f"Image MIME type: {mime_type}, has text: {text is not None}")

        try:
            with self.get_checkpointer() as checkpointer:
                # Build system prompt with context injected
                system_prompt = build_system_prompt(context)

                # Create agent with checkpointer (no tools needed)
                agent = create_agent(
                    model=self.llm,
                    tools=[],  # No tools for project assistant
                    system_prompt=system_prompt,
                    checkpointer=checkpointer,
                )

                # Create message with image
                content = []
                if text:
                    content.append({"type": "text", "text": text})
                    logger.debug(f"Accompanying text: {text}")

                content.append({
                    "type": "image",
                    "base64": image_base64,
                    "mime_type": mime_type
                })

                config: RunnableConfig = {
                    "configurable": {
                        "thread_id": str(thread_id),
                        "project_id": project_id,
                        "recursion_limit": 20
                    }
                }

                result = agent.invoke(
                    input={"messages": [HumanMessage(content=content)]},
                    config=config
                )

                if result and "messages" in result:
                    last_message = result["messages"][-1]
                    logger.info(f"Agent responded successfully to image for thread_id: {thread_id}")
                    logger.debug(f"Project Assistant Agent response: {last_message.content}")

                    return last_message.content
                else:
                    logger.error("No response from agent")
                    return "I apologize, but I encountered an issue processing your request."

        except Exception as e:
            logger.error(f"Error in process_image_response: {e}")
            return "I apologize, but I'm having trouble processing your image. Please try again."

    def get_history(self, thread_id: UUID) -> List[Dict]:
        """
        Read conversation history for a thread using LangGraph's get_state.
        Extracts text content from messages, handling both string and multimodal content.
        """
        with self.get_checkpointer() as checkpointer:
            # Use minimal context for history retrieval
            minimal_context = "## Project Information\n(No specific context loaded for history retrieval)"
            system_prompt = build_system_prompt(minimal_context)

            agent = create_agent(
                model=self.llm,
                tools=[],
                system_prompt=system_prompt,
                checkpointer=checkpointer,
            )

            config: RunnableConfig = {
                "configurable": {
                    "thread_id": str(thread_id),
                }
            }

            # LangGraph handles Mongo + msgpack for you here
            snapshot = agent.get_state(config)

            # snapshot.values is your graph state; in your case it should contain "messages"
            messages = snapshot.values.get("messages", [])

            history: List[Dict] = []
            for m in messages:
                # Skip tool messages as they're not part of user-facing conversation
                msg_type = getattr(m, "type", None) or m.__class__.__name__.lower()
                if msg_type == "tool":
                    continue

                # Map message type to role
                role = {
                    "human": "user",
                    "ai": "assistant",
                    "system": "system",
                }.get(msg_type, "user")

                # Extract text content - handle both string and list (multimodal) content
                content = m.content
                if isinstance(content, str):
                    text_content = content
                elif isinstance(content, list):
                    # Extract text from content blocks (multimodal messages)
                    text_parts = []
                    for item in content:
                        if isinstance(item, dict):
                            if item.get("type") == "text" and "text" in item:
                                text_parts.append(item["text"])
                            elif item.get("type") == "image":
                                # Extract base64 content from image block
                                base64_data = item.get("base64")
                                mime_type = item.get("mime_type", "image/jpeg")
                                if base64_data:
                                    # Format as data URI for easy use in frontend
                                    text_parts.append(f"data:{mime_type};base64,{base64_data}")
                                elif item.get("url"):
                                    # Fallback to URL if base64 not available
                                    text_parts.append(f"[Image URL: {item.get('url')}]")
                                else:
                                    text_parts.append("[Image attached]")
                        elif isinstance(item, str):
                            text_parts.append(item)
                    text_content = " ".join(text_parts) if text_parts else ""
                else:
                    # Fallback: convert to string
                    text_content = str(content) if content else ""

                history.append({"role": role, "content": text_content})

            return history
