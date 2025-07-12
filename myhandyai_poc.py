import streamlit as st
from openai import OpenAI

client = OpenAI()
#  OpenAI_API_KEY = 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

st.title("MyHandyAI POC")
st.write("Test: Upload an image and ask your DIY question")

# Image upload
image = st.file_uploader("Upload an image of your DIY task", type=["jpg", "jpeg", "png"])

# Voice or text input
input_mode = st.radio("Input mode", ["Text", "Voice"])

if input_mode == "Text":
    user_query = st.text_input("What do you want to do?")
else:
    audio_file = st.file_uploader("Upload voice query (wav, mp3, m4a)", type=["wav", "mp3", "m4a"])
    if audio_file:
        st.write("Transcribing...")
        transcription = client.audio.transcriptions.create(
            file=audio_file,
            model="whisper-1"
        )
        user_query = transcription.text
        st.write("You said:", user_query)


# Generate instructions
if image and user_query:
    st.write("Generating step-by-step instructions...")
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": f"Provide detailed, step-by-step instructions for: {user_query}. Be precise, safe, and practical."},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image.getvalue().decode('latin1')}"
                        }
                    }
                ]
            }
        ]
    )
    st.write(response.choices[0].message.content)
