from ast import Dict
from contextlib import contextmanager
from typing import List, Optional
from uuid import UUID
import msgpack

from pymongo import MongoClient

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.mongodb import MongoDBSaver
from loguru import logger

from config.settings import get_settings
from information_gathering_agent.agent.prompt_templates.v2.information_gathering_agent import \
    INFORMATION_GATHERING_AGENT_SYSTEM_PROMPT
from information_gathering_agent.agent.tools import store_home_issue, store_summary


class InformationGatheringAgent:
    def __init__(self):
        self.settings = get_settings()
        self.llm = ChatOpenAI(
            model=self.settings.INFORMATION_GATHERING_AGENT_MODEL,
            max_retries=5,
            reasoning_effort="low",
            api_key=self.settings.OPENAI_API_KEY
        )

    @contextmanager
    def get_checkpointer(self):
        """Context manager for MongoDB checkpointer."""
        with MongoDBSaver.from_conn_string(conn_string=self.settings.MONGODB_URI,
                                           db_name=self.settings.INFORMATION_GATHERING_AGENT_CHECKPOINT_DATABASE,
                                           checkpoint_collection_name=self.settings.INFORMATION_GATHERING_AGENT_CHECKPOINT_COLLECTION_NAME,
                                           writes_collection_name=self.settings.INFORMATION_GATHERING_AGENT_CHECKPOINT_WRITES_COLLECTION_NAME) as checkpointer:
            yield checkpointer

    def process_text_response(self, message: str, thread_id: UUID, project_id: str) -> str:
        """
        Process a text message from the user.
        
        Args:
            message: User's text message
            thread_id: Conversation thread ID for persistence
            project_id: Project ID to associate with this conversation
            
        Returns:
            Agent's response text
        """
        logger.info(f"Processing text response for thread_id: {thread_id}, project_id: {project_id}")
        logger.debug(f"User message: {message}")

        try:
            with self.get_checkpointer() as checkpointer:
                # Create agent with checkpointer
                agent = create_agent(
                    model=self.llm,
                    tools=[store_home_issue, store_summary],
                    system_prompt=INFORMATION_GATHERING_AGENT_SYSTEM_PROMPT,
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
                    logger.debug(f"Agent response: {last_message.content}")

                    # Log any tool calls
                    for msg in result["messages"]:
                        if hasattr(msg, 'tool_calls') and msg.tool_calls:
                            for tool_call in msg.tool_calls:
                                logger.info(
                                    f"Tool called: {tool_call.get('name')} with args: {tool_call.get('args', {})}")

                    return last_message.content
                else:
                    logger.error("No response from agent")
                    return "I apologize, but I encountered an issue processing your request."

        except Exception as e:
            logger.error(f"Error in process_text_response: {e}")
            return "I apologize, but I'm having trouble processing your request right now. Please try again."

    def process_image_response(self, text: Optional[str], image_base64: str, mime_type: str, thread_id: UUID,
                               project_id: str) -> str:
        """
        Process a message with an image from the user.
        
        Args:
            text: Optional text accompanying the image
            image_base64: Base64-encoded image data
            mime_type: MIME type of the image (e.g., 'image/jpeg')
            thread_id: Conversation thread ID for persistence
            project_id: Project ID to associate with this conversation
            
        Returns:
            Agent's response text
        """
        logger.info(f"Processing image response for thread_id: {thread_id}, project_id: {project_id}")
        logger.debug(f"Image MIME type: {mime_type}, has text: {text is not None}")

        try:
            with self.get_checkpointer() as checkpointer:
                # Create agent with checkpointer
                agent = create_agent(
                    model=self.llm,
                    tools=[store_home_issue, store_summary],
                    system_prompt=INFORMATION_GATHERING_AGENT_SYSTEM_PROMPT,
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
                    logger.debug(f"Agent response: {last_message.content}")

                    return last_message.content
                else:
                    logger.error("No response from agent")
                    return "I apologize, but I encountered an issue processing your request."

        except Exception as e:
            logger.error(f"Error in process_image_response: {e}")
            return "I apologize, but I'm having trouble processing your image. Please try again."


    def get_history(self, thread_id: UUID) -> List[Dict]:
            """
            Get conversation history for a thread_id by reading LangGraph
            MongoDBSaver writes (channel='messages').

            Returns a list of dicts: [{ "role": "...", "content": "..." }, ...]
            """
            client = MongoClient(self.settings.MONGODB_URI)
            db = client[self.settings.
                        INFORMATION_GATHERING_AGENT_CHECKPOINT_DATABASE]
            writes_col = db[self.settings.
                            INFORMATION_GATHERING_AGENT_CHECKPOINT_WRITES_COLLECTION_NAME]

            # Get the latest messages write for this thread
            doc = writes_col.find_one(
                {"thread_id": str(thread_id), "channel": "messages"},
                sort=[("checkpoint_id", -1), ("idx", -1)]
            )

            if not doc:
                return []

            if doc.get("type") != "msgpack":
                return []

            # value is a Binary; convert to bytes and unpack
            packed = bytes(doc["value"])
            raw_messages = msgpack.unpackb(packed, raw=False)

            # raw_messages is usually a list of serialized LC messages
            history: List[Dict] = []

            for m in raw_messages:
                # LangChain’s serialization usually has "type" and "content"
                msg_type = m.get("type") or m.get("role") or "unknown"
                role = {
                    "human": "user",
                    "ai": "assistant",
                    "system": "system",
                    "tool": "tool",
                }.get(msg_type, msg_type)

                content = m.get("content", "")

                # If content is a list of parts (e.g. images + text), flatten text
                if isinstance(content, list):
                    text_parts = [
                        c.get("text", "") if isinstance(c, dict) else str(c)
                        for c in content
                    ]
                    content = "\n".join(text_parts)

                history.append(
                    {
                        "role": role,
                        "content": content,
                    }
                )

            return history