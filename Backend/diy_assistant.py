import streamlit as st
import os
from dotenv import load_dotenv
from PIL import Image
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.memory import ConversationBufferWindowMemory
from langchain.chains import LLMChain
from langchain_xai import ChatXAI
import base64

load_dotenv()

st.set_page_config(
    page_title="DIY Expert Chatbot 🛠️",
    page_icon="🛠️",
    layout="centered",
    initial_sidebar_state="auto",
)

st.markdown("""
<style>
    /* Overall app background */
    .stApp { background-color: #F0F2F6; }

    /* Chat bubbles */
    .stChatMessage { border-radius: 10px; padding: 1rem 1.25rem; margin-bottom: 1rem; }

    /* Text in chat messages */
    [data-testid="stChatMessageContent"] p { color: #000000 !important; }
    [data-testid="stChatMessageContent"] ul li { color: #000000 !important; }

    /* Assistant vs user bubble backgrounds */
    .st-emotion-cache-janbn0 { background-color: #FFFFFF; }
    .st-emotion-cache-4oy321 { background-color: #E6E6FA; }

    /* Headings and other text */
    h1, p, .st-emotion-cache-s4p5hm { color: #000000 !important; }

    /* ChatGPT-style input row */
    .chat-input-container {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0 1rem;
        margin-top: 1rem;
    }
    .chat-input-container .stChatInput {
        flex: 1;
    }

    /* Compact uploader wrapper */
    .chat-input-container [data-testid="stFileUploader"] {
        width: 24px !important;
        min-width: auto !important;
        padding: 0 !important;
        margin: 0 !important;
    }

    /* Icon-only drop area */
    .chat-input-container [data-testid="stFileUploader"] div[role="button"] {
        width: 24px !important;
        height: 24px !important;
        background: url('https://upload.wikimedia.org/wikipedia/commons/3/3e/Image_icon_%28the_Noun_Project_43084%29.svg')
                    no-repeat center !important;
        background-size: contain !important;
        cursor: pointer;
        border: none !important;
        box-shadow: none !important;
    }

    /* Hide default uploader label */
    .chat-input-container [data-testid="stFileUploader"] label {
        display: none !important;
    }
</style>
""", unsafe_allow_html=True)

def get_llm_chain():
    system_prompt="""
You are a helpful, patient, and highly skilled DIY Expert chatbot. Your primary goal is to deeply understand the user's DIY problem before suggesting any solutions. You can now process and understand images.

**Your Conversation Flow:**
1. **Greeting:** If the user starts with a simple greeting like "hi", "hello", or "hey", respond ONLY with: "How can I help you with your DIY project today?"
2. **Problem Diagnosis & Image Analysis:** Once the user describes their problem, your main task begins...
3. **Guiding the User:** If a user is unsure how to answer your question, provide guidance or ask for images if the user faces any confusion...
4. **Clarification by Image:** If the text answer is not clear or the user's problem cannot be understood properly ask for images for better understanding.
5. **Description of the Problem:** Ask for the description of the problem; if it's about any object ask for its dimensions and an image to know about it. If it's a problematic situation, ask for an image of it.
6. **Handling Skips:** If the user asks to "skip" a question, acknowledge it and move on.
7. **Maintaining Context:** Use the entire chat history (text and images) to inform your questions.

Do not ask about tools or materials—just focus on the problem. Ask one question at a time and wait for the user's answer. When you have enough information, generate a structured summary with your expert insights:

SUMMARY: <Descriptive and Informative summary of the conversation with insights>
"""
    prompt=ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{user_input}"),
        ]
    )
    llm=ChatXAI(
        model="grok-4",
        api_key=os.getenv("GROK_API_KEY")
    )
    memory=ConversationBufferWindowMemory(memory_key="chat_history", return_messages=True, k=10)
    return LLMChain(llm=llm, prompt=prompt, memory=memory, verbose=False)

st.title("DIY Expert Chatbot 🛠️")
st.markdown("Your AI-powered assistant for all things Do-It-Yourself!")

if "messages" not in st.session_state:
    st.session_state.messages=[]
if "conversation_chain" not in st.session_state:
    st.session_state.conversation_chain=get_llm_chain()
if "uploader_key" not in st.session_state:
    st.session_state.uploader_key=0
if "last_prompt" not in st.session_state:
    st.session_state.last_prompt=None


for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        for part in msg["parts"]:
            if part["type"]=="text":
                st.markdown(part["content"])
            else:
                st.image(part["content"], width=250)

st.markdown('<div class="chat-input-container">', unsafe_allow_html=True)

user_prompt=st.chat_input("Describe your DIY problem here…", key="chat_input")

uploaded_file=st.file_uploader(
    "Upload Image",
    type=["png", "jpg", "jpeg"],
    label_visibility="hidden",
    key=f"image_uploader_{st.session_state.uploader_key}"
)

st.markdown('</div>', unsafe_allow_html=True)

if user_prompt and user_prompt!=st.session_state.last_prompt:
    parts=[{"type": "text", "content": user_prompt}]
    if uploaded_file:
        raw=uploaded_file.read()
        img_b64=base64.b64encode(raw).decode()
        img=Image.open(uploaded_file)
        parts.append({"type": "image", "content": img})
        image_to_display=img
        image_input=f"[ImageAttached base64={img_b64}]"
    else:
        image_to_display=None
        image_input=""

    combined_input=user_prompt+image_input

    st.session_state.messages.append({"role": "user", "parts": parts})
    with st.chat_message("user"):
        st.markdown(user_prompt)
        if image_to_display:
            st.image(image_to_display, width=250)

    with st.spinner("The DIY Expert is analyzing..."):
        ai_text=st.session_state.conversation_chain.predict(user_input=combined_input)

    st.session_state.messages.append({"role": "assistant", "parts": [{"type": "text", "content": ai_text}]})
    with st.chat_message("assistant"):
        st.markdown(ai_text)

    st.session_state.last_prompt=user_prompt
    if uploaded_file:
        st.session_state.uploader_key+=1
        st.rerun()
