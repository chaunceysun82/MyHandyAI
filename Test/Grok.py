# app_grok_test.py

import os
import base64
import time
from dotenv import load_dotenv
import streamlit as st
import requests

# ─── Configuration ─────────────────────────────────────────────────────────────

load_dotenv()
API_KEY = os.getenv("GROK_API_KEY")
API_URL = "https://api.x.ai/v1"  # ← Correct base URL

if not API_KEY:
    st.error("❌ Please set your GROK_API_KEY in a .env file")
    st.stop()

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

# ← Define your model choices here
MODEL_OPTIONS = {
    "Grok Light": "grok-1-light",
    "Grok Full":  "grok-1"
}

# ─── Helper functions ──────────────────────────────────────────────────────────

def call_grok_completion(model: str, prompt: str, max_tokens: int = 150):
    payload = {"model": model, "prompt": prompt, "max_tokens": max_tokens}
    r = requests.post(f"{API_URL}/completions", headers=HEADERS, json=payload)
    if r.status_code != 200:
        st.error(f"❌ API error {r.status_code}:\n{r.text}")
        return None, None, None
    try:
        data = r.json()
    except ValueError:
        st.error(f"❌ Invalid JSON response:\n{r.text}")
        return None, None, None

    text = data["choices"][0]["text"].strip()
    latency = r.elapsed.total_seconds()
    tokens = data.get("usage", {}).get("total_tokens")
    return text, latency, tokens

def call_grok_chat(model: str, messages: list, max_tokens: int = 150):
    payload = {"model": model, "messages": messages, "max_tokens": max_tokens}
    r = requests.post(f"{API_URL}/chat/completions", headers=HEADERS, json=payload)
    if r.status_code != 200:
        st.error(f"❌ Chat API error {r.status_code}:\n{r.text}")
        return None, None, None
    try:
        data = r.json()
    except ValueError:
        st.error(f"❌ Invalid JSON response:\n{r.text}")
        return None, None, None

    msg = data["choices"][0]["message"]["content"].strip()
    latency = r.elapsed.total_seconds()
    tokens = data.get("usage", {}).get("total_tokens")
    return msg, latency, tokens

# ─── Streamlit UI ──────────────────────────────────────────────────────────────

st.set_page_config(page_title="Grok DIY End-to-End Tester", layout="wide")
st.title("🔧 Grok DIY End-to-End Tester")

# Session state
ss = st.session_state
ss.setdefault("stage", "summary")
ss.setdefault("summary", "")
ss.setdefault("tools", "")
ss.setdefault("steps", "")
ss.setdefault("chat_history", [])

# Step 1: Input
uploaded = st.file_uploader("Step 1: Upload image (optional)", type=["png", "jpg", "jpeg"])
mode     = st.radio("Describe problem via", ["Text", "Voice"], horizontal=True)
query    = st.text_input("Describe the problem:") if mode == "Text" else ""
info     = st.text_input("Additional details (optional):")

img_b64 = ""
if uploaded:
    img_b64 = base64.b64encode(uploaded.read()).decode()

# Stage: Summary
if ss.stage == "summary":
    st.subheader("1️⃣ Generate Summary")
    model = st.selectbox("Model for summary", list(MODEL_OPTIONS.keys()), key="m1")
    if st.button("Run Summary"):
        prompt = (
            f"Summarize this DIY issue in one sentence:\n\n"
            f"Problem: {query}\n"
            f"Details: {info or 'None'}\n"
            + (f"Image (base64): {img_b64}\n" if img_b64 else "")
        )
        out, lat, tok = call_grok_completion(MODEL_OPTIONS[model], prompt, max_tokens=60)
        if out is None:
            st.stop()
        ss.summary = out
        st.markdown(f"**Summary:** {out}")
        if lat is not None and tok is not None:
            st.write(f"⏱ {lat:.2f}s • 🔢 {tok} tokens")
        ss.stage = "tools"

# Stage: Tools & Materials
if ss.stage == "tools":
    st.subheader("2️⃣ Generate Tools & Materials")
    model = st.selectbox("Model for tools", list(MODEL_OPTIONS.keys()), key="m2")
    if st.button("Run Tools"):
        prompt = (
            f"List only the missing tools & materials needed to fix this issue.\n"
            f"Summary: {ss.summary}"
        )
        out, lat, tok = call_grok_completion(MODEL_OPTIONS[model], prompt, max_tokens=80)
        if out is None:
            st.stop()
        ss.tools = out
        st.markdown(f"**Tools & Materials:**\n{out}")
        if lat is not None and tok is not None:
            st.write(f"⏱ {lat:.2f}s • 🔢 {tok} tokens")
        ss.stage = "steps"

# Stage: Step-by-Step Guide
if ss.stage == "steps":
    st.subheader("3️⃣ Generate Step-by-Step Guide")
    model = st.selectbox("Model for steps", list(MODEL_OPTIONS.keys()), key="m3")
    if st.button("Run Steps"):
        prompt = (
            f"Write a numbered, safe, step-by-step DIY guide to fix the issue.\n"
            f"Summary: {ss.summary}\n"
            f"Tools: {ss.tools}"
        )
        out, lat, tok = call_grok_completion(MODEL_OPTIONS[model], prompt, max_tokens=300)
        if out is None:
            st.stop()
        ss.steps = out
        st.markdown(f"**Guide:**\n{out}")
        if lat is not None and tok is not None:
            st.write(f"⏱ {lat:.2f}s • 🔢 {tok} tokens")
        ss.stage = "chat"

# Stage: Interactive Chat
if ss.stage == "chat":
    st.subheader("4️⃣ Interactive Chat")
    model = st.selectbox("Model for chat", list(MODEL_OPTIONS.keys()), key="m4")

    if not ss.chat_history:
        ss.chat_history = [
            {"role": "system", "content": "You are a helpful DIY assistant."},
            {"role": "assistant", "content":
                f"Summary: {ss.summary}\nTools: {ss.tools}\nSteps: {ss.steps}"
            }
        ]

    user_q = st.text_input("Ask your question about this task:")
    if st.button("Send"):
        ss.chat_history.append({"role": "user", "content": user_q})
        reply, lat, tok = call_grok_chat(MODEL_OPTIONS[model], ss.chat_history, max_tokens=150)
        if reply is None:
            st.stop()
        ss.chat_history.append({"role": "assistant", "content": reply})
        st.markdown(f"**Assistant:** {reply}")
        if lat is not None and tok is not None:
            st.write(f"⏱ {lat:.2f}s • 🔢 {tok} tokens")

    # Display conversation
    if len(ss.chat_history) > 2:
        st.markdown("---")
        for msg in ss.chat_history[1:]:
            prefix = "🤖" if msg["role"] == "assistant" else "🗣️"
            st.markdown(f"{prefix} {msg['content']}")
## Testing with Grok models
