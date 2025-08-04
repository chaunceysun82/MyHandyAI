import os, json, requests
import streamlit as st
from langchain_core.messages import HumanMessage, AIMessage
from langchain.memory import ConversationBufferMemory
from typing import List, Dict, Any
from dotenv import load_dotenv
from agents import AgenticChatbot

load_dotenv()


class GrokChatbot:
    """Top-level orchestrator: decides ‘agentic flow’ vs ‘plain chat’."""

    # ─────────────────────── initialisation ────────────────────────────
    def __init__(self):
        self.api_key = os.getenv("GROK_API_KEY")
        self.api_url = "https://api.x.ai/v1/chat/completions"
        if not self.api_key:
            st.error("❌ GROK_API_KEY missing"); return
        self.headers = {"Authorization": f"Bearer {self.api_key}",
                        "Content-Type":  "application/json"}

        self.models = {
            "Grok 3 Mini":  "grok-3-mini",
            "Grok 3":       "grok-3",
            "Grok 3 Fast":  "grok-3-fast-us-east-1",
            "Grok 4":       "grok-4-0709",
        }

        self.agentic_chatbot = AgenticChatbot()          # DIY pipeline
        self.memory = ConversationBufferMemory()         # fallback chat
        self._initialize_conversation()

    # ─────────────────────── intro helpers ────────────────────────────
    def _initialize_conversation(self):
        for msg in (
            "Thanks for using MyHandyAI! Tell me what you’d like to do or fix.",
            "Hi User! Let’s get started with your project!",
            "What home project can we help with today?"
        ):
            self.memory.chat_memory.add_ai_message(msg)

    def get_intro_messages(self) -> List[Dict[str, Any]]:
        return [{"role": "assistant", "content": m.content}
                for m in self.memory.chat_memory.messages[:3]]

    # ─────────────────────── low-level Grok call ──────────────────────
    def call_grok_chat(self, model_key: str, messages, max_tokens=500):
        try:
            r = requests.post(
                self.api_url, headers=self.headers,
                json={"model": model_key, "messages": messages,
                      "max_tokens": max_tokens},
                timeout=20
            )
            if r.status_code == 200:
                msg = r.json()["choices"][0]["message"]
                return (msg.get("content") or msg.get("reasoning_content") or "").strip()
        except Exception as e:
            st.error(f"❌ Grok API error: {e}")
        return None

    # ─────────────────────── improved classifier ──────────────────────
    def _should_use_agentic_system(self, user_msg: str) -> bool:
        key = f"classify::{user_msg}"
        if key in st.session_state:                 # cached?
            return st.session_state[key]

        sys_prompt = """
You are a classifier for a DIY assistant.  Reply with **ONLY**:
  {"use_agentic": true}   – if the message describes a concrete DIY problem
  {"use_agentic": false}  – otherwise (chit-chat, meta, vague, etc.)
"""
        messages = [
            {"role": "system", "content": sys_prompt.strip()},
            {"role": "user",   "content": user_msg.strip()}
        ]
        try:
            r = requests.post(
                self.api_url, headers=self.headers,
                json={"model": "grok-3-mini", "messages": messages, "max_tokens": 20},
                timeout=10
            )
            if r.status_code == 200:
                content = r.json()["choices"][0]["message"]["content"].strip()
                result  = json.loads(content)
                flag    = bool(result.get("use_agentic", False))
                st.session_state[key] = flag
                return flag
        except Exception:
            pass

        # heuristic fallback
        words = ["problem", "issue", "broken", "leak", "clog", "hang",
                 "install", "fix", "repair", "not working", "mount"]
        flag = any(w in user_msg.lower() for w in words)
        st.session_state[key] = flag
        return flag

    # ─────────────────────── master chat method ───────────────────────
    def chat(self, user_msg: str, model="Grok 3", uploaded_image: bytes = None):
        # already inside agentic flow?
        if self.agentic_chatbot.current_state != "waiting_for_problem":
            return self.agentic_chatbot.process_message(user_msg, uploaded_image)

        # first turn → decide
        if self._should_use_agentic_system(user_msg):
            return self.agentic_chatbot.process_message(user_msg, uploaded_image)

        # fallback plain chat
        self.memory.chat_memory.add_user_message(user_msg)
        msgs = [{"role": "system",
                 "content":
                 "You are MyHandyAI, a friendly DIY helper. Give clear, practical advice."}]
        for m in self.memory.chat_memory.messages:
            msgs.append({"role": "user" if isinstance(m, HumanMessage) else "assistant",
                         "content": m.content})
        resp = self.call_grok_chat(self.models[model], msgs)
        if resp:
            self.memory.chat_memory.add_ai_message(resp)
            return resp
        return "Sorry, I hit an error trying to answer that."

    # ─────────────────────── house-keeping helpers ────────────────────
    def get_conversation_history(self):
        hist = self.get_intro_messages()
        for m in self.memory.chat_memory.messages[3:]:
            hist.append({"role": "user" if isinstance(m, HumanMessage) else "assistant",
                         "content": m.content})
        return hist

    def reset_conversation(self):
        self.memory.chat_memory.messages.clear()
        self.agentic_chatbot.reset()
        self._initialize_conversation()


# ─────────────────────────── Streamlit UI ─────────────────────────────
def create_streamlit_app():
    st.set_page_config("MyHandyAI Assistant", "🔧", layout="wide")
    st.title("MyHandyAI Assistant")

    if "chatbot" not in st.session_state:
        st.session_state.chatbot = GrokChatbot()

    with st.sidebar:
        st.header("Controls")
        model_name = st.selectbox("Grok model", list(st.session_state.chatbot.models.keys()), index=1)
        if st.button("Reset conversation"):
            st.session_state.chatbot.reset_conversation()
            st.session_state.messages = st.session_state.chatbot.get_intro_messages()
            st.rerun()
        st.markdown("Upload an image below *before* sending your answer to photo requests.")

    if "messages" not in st.session_state:
        st.session_state.messages = st.session_state.chatbot.get_intro_messages()

    # ─── render history ───
    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    # ─── file uploader (image bytes) ───
    uploaded_file = st.file_uploader("Upload problem photo (jpg / png)", type=["jpg", "jpeg", "png"])
    img_bytes = uploaded_file.read() if uploaded_file else None

    # ─── user input ───
    if prompt := st.chat_input("Describe your project or reply…"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            reply = st.session_state.chatbot.chat(prompt, model=model_name, uploaded_image=img_bytes)
            st.markdown(reply)

        st.session_state.messages.append({"role": "assistant", "content": reply})


if __name__ == "__main__":
    create_streamlit_app()
