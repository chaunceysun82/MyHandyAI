import os
import streamlit as st
import requests
from langchain_core.messages import HumanMessage, AIMessage
from langchain.memory import ConversationBufferMemory
from typing import List, Dict, Any
from dotenv import load_dotenv
from agents import AgenticChatbot

# Load environment variables
load_dotenv()


class GrokChatbot:
    def __init__(self):
        """Initialize the Grok chatbot with agentic system"""
        self.api_key = os.getenv("GROK_API_KEY")
        self.api_url = "https://api.x.ai/v1/chat/completions"

        if not self.api_key:
            st.error("❌ GROK_API_KEY not found in environment variables")
            return

        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # Available Grok models
        self.models = {
            "Grok 3 Mini": "grok-3-mini",
            "Grok 3": "grok-3",
            "Grok 3 Fast": "grok-3-fast-us-east-1",
            "Grok 4": "grok-4-0709"
        }

        # Initialize agentic system
        self.agentic_chatbot = AgenticChatbot()
        
        # Initialize memory for traditional chat
        self.memory = ConversationBufferMemory()

        # Start conversation with intro messages
        self._initialize_conversation()

    def _initialize_conversation(self):
        intro_messages = [
            "Thanks for using MyHandyAI chat! Could you please describe what you would like to do today? You can also upload a photo for your problem.",
            "Hi User! Let's get started with your project!",
            "What home project or home problem can we help with today?"
        ]

        for msg in intro_messages:
            self.memory.chat_memory.add_ai_message(msg)

    def get_intro_messages(self) -> List[Dict[str, Any]]:
        return [
            {"role": "assistant", "content": msg}
            for msg in [
                "Thanks for using MyHandyAI chat! Could you please describe what you would like to do today? You can also upload a photo for your problem.",
                "Hi User! Let's get started with your project!",
                "What home project or home problem can we help with today?"
            ]
        ]

    def call_grok_chat(self, model: str, messages: list, max_tokens: int = 500):
        try:
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json={"model": model, "messages": messages, "max_tokens": max_tokens}
            )

            if response.status_code != 200:
                st.error(f"❌ API error {response.status_code}:\n{response.text}")
                return None

            data = response.json()
            msg = data["choices"][0]["message"]
            text = (msg.get("content") or msg.get("reasoning_content") or "").strip()
            return text

        except Exception as e:
            st.error(f"❌ Error calling Grok API: {str(e)}")
            return None

    def _should_use_agentic_system(self, user_message: str) -> bool:
        """Use AI to determine if the user message describes a problem that needs the agentic system"""
        
        system_prompt = """You are a problem classifier for a DIY home improvement chatbot. 

Determine if the user's message describes a specific home improvement problem or project that would benefit from:
1. Asking for photos/images of the problem area
2. Asking clarifying questions one by one
3. Providing step-by-step DIY instructions

Return ONLY "true" if the message describes a specific problem/project, or "false" if it's:
- General conversation
- Questions about the chatbot itself
- Non-DIY topics
- Vague statements without specific problems

Examples:
- "I have a pipe which is leaking" → true
- "I want to hang a mirror" → true  
- "How are you?" → false
- "What can you help me with?" → false
- "I need help" → false (too vague)
- "My sink is clogged" → true"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"User message: {user_message}"}
        ]
        
        try:
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json={"model": "grok-3-mini", "messages": messages, "max_tokens": 10}
            )
            
            if response.status_code == 200:
                data = response.json()
                text = data["choices"][0]["message"]["content"].strip().lower()
                return "true" in text
            else:
                # Fallback: use simple heuristics if API fails
                problem_indicators = ["problem", "issue", "broken", "leaking", "clogged", "not working", "need help", "fix", "repair"]
                return any(indicator in user_message.lower() for indicator in problem_indicators)
                
        except Exception as e:
            # Fallback: use simple heuristics if API fails
            problem_indicators = ["problem", "issue", "broken", "leaking", "clogged", "not working", "need help", "fix", "repair"]
            return any(indicator in user_message.lower() for indicator in problem_indicators)

    def chat(self, user_message: str, model: str = "Grok 3", uploaded_image: bytes = None) -> str:
        try:
            # Use agentic system for problem-specific interactions
            if self.agentic_chatbot.current_state != "waiting_for_problem":
                return self.agentic_chatbot.process_message(user_message, uploaded_image)
            
            # Use AI to determine if this is a problem that needs the agentic system
            if self._should_use_agentic_system(user_message):
                return self.agentic_chatbot.process_message(user_message, uploaded_image)
            
            # Fall back to traditional chat
            self.memory.chat_memory.add_user_message(user_message)

            messages = [
                {
                    "role": "system",
                    "content": "You are MyHandyAI, a helpful DIY assistant. You help users with home improvement projects and problems. Be friendly, knowledgeable, and provide practical advice."
                }
            ]

            for msg in self.memory.chat_memory.messages:
                if isinstance(msg, HumanMessage):
                    messages.append({"role": "user", "content": msg.content})
                elif isinstance(msg, AIMessage):
                    messages.append({"role": "assistant", "content": msg.content})

            response = self.call_grok_chat(self.models[model], messages)

            if response:
                self.memory.chat_memory.add_ai_message(response)
                return response
            else:
                return "Sorry, I encountered an error processing your request."

        except Exception as e:
            return f"Sorry, I encountered an error: {str(e)}"

    def get_conversation_history(self) -> List[Dict[str, Any]]:
        history = self.get_intro_messages()
        for message in self.memory.chat_memory.messages:
            if isinstance(message, HumanMessage):
                history.append({"role": "user", "content": message.content})
            elif isinstance(message, AIMessage):
                history.append({"role": "assistant", "content": message.content})
        return history

    def reset_conversation(self):
        self.memory.chat_memory.messages.clear()
        self._initialize_conversation()


def create_streamlit_app():
    st.set_page_config(
        page_title="MyHandyAI Assistant",
        page_icon="🔧",
        layout="wide"
    )

    st.title("MyHandyAI Assistant")

    # Initialize chatbot
    if 'chatbot' not in st.session_state:
        st.session_state.chatbot = GrokChatbot()

    # Sidebar controls
    with st.sidebar:
        st.header("Controls")
        st.subheader("Model Selection")
        model_options = list(st.session_state.chatbot.models.keys())
        selected_model = st.selectbox(
            "Choose Grok Model:",
            model_options,
            index=1
        )

        if st.button("Reset Conversation"):
            st.session_state.chatbot.reset_conversation()
            st.session_state.chatbot.agentic_chatbot.reset()
            st.session_state.messages = st.session_state.chatbot.get_intro_messages()
            st.rerun()

        st.header("About")
        st.markdown("""
        This is a test interface for the MyHandyAI Assistant chatbot.
        
        The chatbot uses:
        - **Grok API** from xAI for LLM capabilities  
        - **LangChain** for memory handling  
        - **Streamlit** for quick testing interface

        Features:
        - Conversation memory
        - Introductory messages
        - Home improvement help
        - Grok model selection
        """)

    # Initialize chat history
    if 'messages' not in st.session_state:
        st.session_state.messages = st.session_state.chatbot.get_intro_messages()

    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input
    if prompt := st.chat_input("What would you like to do today?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            response = st.session_state.chatbot.chat(prompt, model=selected_model)
            st.markdown(response)

        st.session_state.messages.append({"role": "assistant", "content": response})


if __name__ == "__main__":
    create_streamlit_app()
