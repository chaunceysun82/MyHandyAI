import streamlit as st
from dotenv import load_dotenv
import os, base64, time
import openai

# ─── ENV ──────────────────────────────────────────────────────────────────
load_dotenv()
OPENAI_KEY   = os.getenv("OPENAI_API_KEY")

openai_client = openai.OpenAI(api_key=OPENAI_KEY)   # v≥1.55.3

# ─── UI ───────────────────────────────────────────────────────────────────
st.title("MyHandyAI POC • Multi-Model Benchmark")

img_file = st.file_uploader("Upload a photo (jpg / png)", ["jpg", "jpeg", "png"])
mode     = st.radio("Input mode", ["Text", "Voice"])
query    = st.text_input("What do you want to do?") if mode=="Text" else ""
image_info = st.text_input("Additional info about the image (optional)")

openai_models = [
    ("GPT-4o", "gpt-4o"),
    ("GPT-4.1", "gpt-4.1"),
    ("GPT-4 Turbo", "gpt-4-turbo"),
]
model_names = [name for name, _ in openai_models]
model_dict = dict(openai_models)

# Section state persistence
if "summary_answer" not in st.session_state:
    st.session_state["summary_answer"] = {}
if "fix_answer" not in st.session_state:
    st.session_state["fix_answer"] = {}

if img_file and query:
    st.info("Image and text loaded. Ready for summary.")
    img_b64 = base64.b64encode(img_file.read()).decode()

    # 1. Summary Section
    st.subheader("1. Problem Summary (Image + Text)")
    selected_summary_model = st.selectbox("Choose model for summary", model_names, key="summary_model")
    if selected_summary_model in st.session_state["summary_answer"]:
        st.write(st.session_state["summary_answer"][selected_summary_model])
    if st.button("Get Summary", key="summary_btn"):
        try:
            prompt_content = [
                {"type": "text", "text": f"Summarize the problem described in the following text and image."},
                {"type": "text", "text": query},
            ]
            if image_info:
                prompt_content.append({"type": "text", "text": f"Image info: {image_info}"})
            prompt_content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}})
            summary = openai_client.chat.completions.create(
                model=model_dict[selected_summary_model],
                messages=[{"role": "user", "content": prompt_content}]
            ).choices[0].message.content
            st.session_state["summary_answer"][selected_summary_model] = summary
            st.write(summary)
        except Exception as e:
            st.write(f"⚠️ {e}")

    # 2. Step-by-Step Fix Section
    st.subheader("2. Step-by-Step Fix (Image + Text)")
    selected_fix_model = st.selectbox("Choose model for fix", model_names, key="fix_model")
    if selected_fix_model in st.session_state["fix_answer"]:
        st.write(st.session_state["fix_answer"][selected_fix_model])
    if st.button("Get Step-by-Step Fix", key="fix_btn"):
        try:
            prompt_content = [
                {"type": "text", "text": f"Give a step-by-step solution to fix the problem described in the following text and image."},
                {"type": "text", "text": query},
            ]
            if image_info:
                prompt_content.append({"type": "text", "text": f"Image info: {image_info}"})
            prompt_content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}})
            fix = openai_client.chat.completions.create(
                model=model_dict[selected_fix_model],
                messages=[{"role": "user", "content": prompt_content}]
            ).choices[0].message.content
            st.session_state["fix_answer"][selected_fix_model] = fix
            st.write(fix)
        except Exception as e:
            st.write(f"⚠️ {e}")

    # 3. Chatbot Section
    st.subheader("3. Chatbot (Ask follow-up questions)")
    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []
    chat_input_col, chat_model_col, chat_btn_col = st.columns([4,2,2])
    with chat_input_col:
        user_question = st.text_input("Your question", key="chat_input")
    with chat_model_col:
        selected_chat_model = st.selectbox("Model", model_names, key="chatbot_model")
    with chat_btn_col:
        ask_btn = st.button("Ask", key="chat_btn")
    if ask_btn and user_question:
        chat_msgs = st.session_state["chat_history"][:]
        # Compose a comprehensive system prompt with all context
        summary = st.session_state["summary_answer"].get(selected_chat_model, "")
        fix = st.session_state["fix_answer"].get(selected_chat_model, "")
        system_content = (
            "You are a helpful assistant. Here is all the context you should use to answer the user's questions.\n"
            f"Summary: {summary}\n"
            f"Step-by-step fix: {fix}\n"
            f"User's main request: {query}\n"
            f"Image info: {image_info}\n"
            "You also have access to the input image."
        )
        # Only add system prompt at the start of the chat
        if not chat_msgs or chat_msgs[0].get("role") != "system":
            chat_msgs.insert(0, {"role": "system", "content": system_content})
        # Compose the user message as a list for vision models
        user_content = [
            {"type": "text", "text": user_question}
        ]
        if query:
            user_content.append({"type": "text", "text": f"Original request: {query}"})
        if image_info:
            user_content.append({"type": "text", "text": f"Image info: {image_info}"})
        user_content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}})
        chat_msgs.append({"role": "user", "content": user_content})
        try:
            response = openai_client.chat.completions.create(
                model=model_dict[selected_chat_model],
                messages=chat_msgs
            ).choices[0].message.content
            st.session_state["chat_history"].append({"role": "user", "content": user_question})
            st.session_state["chat_history"].append({"role": "assistant", "content": response})
        except Exception as e:
            st.session_state["chat_history"].append({"role": "user", "content": user_question})
            st.session_state["chat_history"].append({"role": "assistant", "content": f"⚠️ {e}"})
    # Display chat history
    for msg in st.session_state["chat_history"]:
        if msg["role"] == "user":
            st.markdown(f"**You:** {msg['content']}")
        elif msg["role"] == "assistant":
            st.markdown(f"**Assistant:** {msg['content']}")

