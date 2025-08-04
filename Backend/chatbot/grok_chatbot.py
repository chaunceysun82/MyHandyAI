import os, json, requests
import streamlit as st
from langchain_core.messages import HumanMessage, AIMessage
from langchain.memory import ConversationBufferMemory
from typing import List, Dict, Any
from dotenv import load_dotenv
from agents import AgenticChatbot

load_dotenv()


class OpenAIChatbot:
    """Top-level orchestrator: decides 'agentic flow' vs 'plain chat'."""

    # ─────────────────────── initialisation ────────────────────────────
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.api_url = "https://api.openai.com/v1/chat/completions"
        if not self.api_key:
            st.error("❌ OPENAI_API_KEY missing"); return
        self.headers = {"Authorization": f"Bearer {self.api_key}",
                        "Content-Type":  "application/json"}

        self.models = {
            "GPT-4.1":       "gpt-4.1",
            "GPT-4.1 Mini":  "gpt-4.1-mini",
            "GPT-4o":        "gpt-4o",
            "GPT-4o Mini":   "gpt-4o-mini",
        }

        self.agentic_chatbot = AgenticChatbot()          # DIY pipeline
        self.memory = ConversationBufferMemory()         # fallback chat
        self._initialize_conversation()

    # ─────────────────────── intro helpers ────────────────────────────
    def _initialize_conversation(self):
        for msg in (
            "Thanks for using MyHandyAI! Tell me what you'd like to do or fix.",
            "Hi User! Let's get started with your project!",
            "What home project can we help with today?"
        ):
            self.memory.chat_memory.add_ai_message(msg)

    def get_intro_messages(self) -> List[Dict[str, Any]]:
        return [{"role": "assistant", "content": m.content}
                for m in self.memory.chat_memory.messages[:3]]

    # ─────────────────────── low-level OpenAI call ──────────────────────
    def call_openai_chat(self, model_key: str, messages, max_tokens=500):
        try:
            r = requests.post(
                self.api_url, headers=self.headers,
                json={"model": model_key, "messages": messages,
                      "max_tokens": max_tokens},
                timeout=20
            )
            if r.status_code == 200:
                msg = r.json()["choices"][0]["message"]
                return msg.get("content", "").strip()
        except Exception as e:
            st.error(f"❌ OpenAI API error: {e}")
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
                json={"model": "gpt-4.1-mini", "messages": messages, "max_tokens": 20},
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
    def chat(self, user_msg: str, model="GPT-4.1", uploaded_image: bytes = None):
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
        resp = self.call_openai_chat(self.models[model], msgs)
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


# ───────────────────────── Streamlit UI ──────────────────────────
def create_streamlit_app():
    st.set_page_config("MyHandyAI Assistant", "🔧", layout="wide")
    st.title("MyHandyAI Assistant")

    # ───────────────────────────────
    # 1️⃣  STABLE FILE-UPLOADER FIRST
    #    (prevents 403 because no state
    #     changes occur until upload done)
    # ───────────────────────────────
    uploaded_file = st.file_uploader(
        "Upload problem photo (jpg / png)",
        type=["jpg", "jpeg", "png"],
        key="problem_photo_uploader"          # fixed key ➜ same presigned URL
    )

    # Cache bytes once, and only once
    if uploaded_file and "uploaded_img_bytes" not in st.session_state:
        try:
            uploaded_file.seek(0)
            img_bytes = uploaded_file.read()

            if len(img_bytes) > 8 * 1024 * 1024:          # 8 MB guard
                st.error("Image is larger than 8 MB – please upload a smaller photo.")
            else:
                st.session_state["uploaded_img_bytes"] = img_bytes
                st.success(f"✅ {uploaded_file.name} uploaded ({len(img_bytes)} bytes)")
        except Exception as e:
            st.error(f"❌ Error reading file: {e}")
            st.session_state["uploaded_img_bytes"] = None
    elif not uploaded_file:
        st.session_state.pop("uploaded_img_bytes", None)

    # ───────────────────────────────
    # 2️⃣  INIT CHATBOT / HISTORY
    # ───────────────────────────────
    if "chatbot" not in st.session_state:
        st.session_state.chatbot = OpenAIChatbot()

    if "messages" not in st.session_state:
        st.session_state.messages = st.session_state.chatbot.get_intro_messages()

    # ───────────────────────────────
    # 3️⃣  SIDEBAR CONTROLS
    # ───────────────────────────────
    with st.sidebar:
        st.header("Controls")
        model_name = st.selectbox(
            "OpenAI model",
            list(st.session_state.chatbot.models.keys()),
            index=0
        )
        if st.button("Reset conversation"):
            st.session_state.chatbot.reset_conversation()
            st.session_state.messages = st.session_state.chatbot.get_intro_messages()
            st.session_state.pop("uploaded_img_bytes", None)
            st.rerun()
        st.markdown("🖼️ *Upload an image first, then send your reply.*")

    # ───────────────────────────────
    # 4️⃣  RENDER CHAT HISTORY
    # ───────────────────────────────
    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    # ───────────────────────────────
    # 5️⃣  CHAT INPUT
    # ───────────────────────────────
    if prompt := st.chat_input("Describe your project or reply…"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            reply = st.session_state.chatbot.chat(
                prompt,
                model=model_name,
                uploaded_image=st.session_state.get("uploaded_img_bytes")
            )
            st.markdown(reply)

        st.session_state.messages.append({"role": "assistant", "content": reply})


if __name__ == "__main__":
    create_streamlit_app()
