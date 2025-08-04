# app_grok_test.py

import os, base64, time
from dotenv import load_dotenv
import streamlit as st
import requests

# ─── Configuration ─────────────────────────────────────────────────────────────

load_dotenv()
API_KEY = os.getenv("GROK_API_KEY")
API_URL = "https://api.x.ai/v1/chat/completions"

if not API_KEY:
    st.error("❌ Please set your GROK_API_KEY in a .env file")
    st.stop()

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

# Light models for summary & tools
SIMPLE_MODELS = {
    "grok-3-mini":        "grok-3-mini",
    "grok-3":             "grok-3",
    "grok-3-fast (us‑east‑1)": "grok-3-fast-us-east-1",
}

# Heavy models for steps & chat
MODEL_OPTIONS = {
    "grok-4-0709":        "grok-4-0709",
    "grok-3-mini-fast":   "grok-3-mini-fast",
    "grok-3-fast (eu‑west‑1)": "grok-3-fast-eu-west-1",
}

def call_grok_chat(model: str, messages: list, max_tokens: int):
    r = requests.post(
        API_URL,
        headers=HEADERS,
        json={"model": model, "messages": messages, "max_tokens": max_tokens}
    )
    if r.status_code != 200:
        st.error(f"❌ API error {r.status_code}:\n{r.text}")
        return None, None, None

    data = r.json()
    msg  = data["choices"][0]["message"]

    # Try the normal content first…
    text = (msg.get("content") or "").strip()
    # …then fall back to reasoning_content
    if not text:
        text = (msg.get("reasoning_content") or "").strip()

    latency = r.elapsed.total_seconds()
    tokens  = data["usage"]["total_tokens"]
    return text, latency, tokens


# ─── Streamlit UI ──────────────────────────────────────────────────────────────

st.set_page_config(page_title="Grok DIY End-to-End Tester", layout="wide")
st.title("🔧 Grok DIY End-to-End Tester")

ss = st.session_state
ss.setdefault("stage", "summary")
ss.setdefault("summary", None)
ss.setdefault("tools", None)
ss.setdefault("steps", None)
ss.setdefault("history", [])

# 1️⃣ Input
uploaded = st.file_uploader("Upload image (optional)", type=["png","jpg","jpeg"])
mode     = st.radio("Describe problem via", ["Text","Voice"], horizontal=True)
query    = st.text_input("Problem description:") if mode=="Text" else ""
info     = st.text_input("Additional details (optional):")

img_b64 = base64.b64encode(uploaded.read()).decode() if uploaded else None

# 2️⃣ Summary
if ss.stage == "summary":
    st.subheader("1️⃣ Generate Summary")
    model = st.selectbox("Model for summary", list(SIMPLE_MODELS.keys()), key="m1")

    if st.button("Run Summary"):
        messages = [
            {"role": "system", "content":
                "You are a concise DIY assistant. "
                "When asked to summarize, return exactly one complete sentence and nothing else."
            },
            {"role": "user", "content":
                f"Summarize this DIY issue.\nProblem: {query}\nDetails: {info or 'None'}"
            }
        ]
        out, lat, tok = call_grok_chat(SIMPLE_MODELS[model], messages, max_tokens=500)
        if out is None: st.stop()

        ss.summary = out
        st.markdown(f"**Summary:** {out}")
        st.write(f"⏱ {lat:.2f}s • 🔢 {tok} tokens")
        ss.stage = "tools"

# 3️⃣ Tools & Materials
if ss.stage == "tools" and ss.summary:
    st.subheader("2️⃣ Summary")
    st.markdown(f"> {ss.summary}")

    st.subheader("3️⃣ Generate Tools & Materials")
    model = st.selectbox("Model for tools", list(SIMPLE_MODELS.keys()), key="m2")
    if st.button("Run Tools"):
        messages = [
            {"role": "system", "content":
                "You are a helpful DIY assistant. "
                "List every tool and material needed, one per line, with no extra commentary."
            },
            {"role": "user", "content": f"Summary: {ss.summary}"}
        ]
        out, lat, tok = call_grok_chat(SIMPLE_MODELS[model], messages, max_tokens=500)
        if out is None: st.stop()

        ss.tools = out
        st.markdown(f"**Tools & Materials:**\n{out}")
        st.write(f"⏱ {lat:.2f}s • 🔢 {tok} tokens")
        ss.stage = "steps"

# 4️⃣ Step-by-Step Guide
if ss.stage == "steps" and ss.tools:
    st.subheader("2️⃣ Summary")
    st.markdown(f"> {ss.summary}")
    st.subheader("3️⃣ Tools & Materials")
    st.markdown(f"> {ss.tools}")

    st.subheader("4️⃣ Generate Step-by-Step Guide")
    model = st.selectbox("Model for steps", list(MODEL_OPTIONS.keys()), key="m3")
    if st.button("Run Steps"):
        messages = [
            {"role": "system", "content":
                "You are a methodical DIY assistant. "
                "Provide a clear, numbered step-by-step guide. "
                "Include safety tips in parentheses after each step."
            },
            {"role": "user", "content":
                f"Summary: {ss.summary}\nTools:\n{ss.tools}"
            }
        ]
        out, lat, tok = call_grok_chat(MODEL_OPTIONS[model], messages, max_tokens=1000)
        if out is None: st.stop()

        ss.steps = out
        st.markdown(f"**Guide:**\n{out}")
        st.write(f"⏱ {lat:.2f}s • 🔢 {tok} tokens")
        ss.stage = "chat"

# 5️⃣ Interactive Chat
if ss.stage == "chat" and ss.steps:
    st.subheader("5️⃣ Interactive Chat")
    model = st.selectbox("Model for chat", list(MODEL_OPTIONS.keys()), key="m4")

    if not ss.history:
        ss.history = [
            {"role": "system", "content": "You are an expert DIY assistant."},
            {"role": "assistant", "content":
                f"Summary: {ss.summary}\n\nTools:\n{ss.tools}\n\nSteps:\n{ss.steps}"
            }
        ]

    user_q = st.text_input("Ask a follow‑up question:")
    if st.button("Send"):
        ss.history.append({"role":"user","content":user_q})
        out, lat, tok = call_grok_chat(MODEL_OPTIONS[model], ss.history, max_tokens=500)
        if out is None: st.stop()
        ss.history.append({"role":"assistant","content":out})
        st.markdown(f"**Assistant:** {out}")
        st.write(f"⏱ {lat:.2f}s • 🔢 {tok} tokens")

    if len(ss.history) > 1:
        st.markdown("---")
        for msg in ss.history[1:]:
            icon = "🤖" if msg["role"]=="assistant" else "🗣️"
            st.markdown(f"{icon} {msg['content']}")
