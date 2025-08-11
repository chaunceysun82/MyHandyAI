# MyHandyAI Chatbot

This module contains the AI chatbot implementation for MyHandyAI using Grok (via Groq) and LangChain.

## Features

- **Grok AI Integration**: Uses xAI Grok API for language model capabilities
- **LangChain Framework**: Leverages LangChain for conversation management and memory
- **Conversation Memory**: Maintains context across conversation turns
- **Introductory Messages**: Starts with welcoming messages as shown in the design
- **Session Management**: Supports multiple chat sessions
- **Multiple Model Options**: Choose from grok-3-mini, grok-3, grok-3-fast, or grok-4
- **Streamlit Interface**: Test interface for development and testing

## Setup

### 1. Environment Variables

Create a `.env` file in the Backend directory with your Grok API key:

```bash
GROK_API_KEY=your_grok_api_key_here
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Test the Chatbot

#### Option A: Streamlit Interface (Recommended for testing)

```bash
cd MyHandyAI-clean/Backend
streamlit run test_chatbot.py
```

#### Option B: FastAPI Backend

```bash
cd MyHandyAI-clean/Backend
uvicorn main:app --reload
```

Then access the API endpoints:
- `POST /chatbot/chat` - Send a message to the chatbot
- `GET /chatbot/session/{session_id}` - Get or create a session
- `GET /chatbot/session/{session_id}/history` - Get conversation history
- `POST /chatbot/session/{session_id}/reset` - Reset conversation

## API Usage

### Chat with the bot

```python
import requests

# Send a message
response = requests.post("http://localhost:8000/chatbot/chat", 
    json={
        "message": "I want to hang a mirror",
        "session_id": "user123"
    }
)

print(response.json())
```

### Get session

```python
# Get or create a session
response = requests.get("http://localhost:8000/chatbot/session/user123")
session_data = response.json()
print(session_data["intro_messages"])
```

## Architecture

```
chatbot/
├── __init__.py
├── grok_chatbot.py      # Main chatbot implementation
└── README.md

routes/
└── chatbot.py           # FastAPI routes for chatbot

test_chatbot.py          # Streamlit test interface
```

## Key Components

### GrokChatbot Class

- **Initialization**: Sets up xAI Grok API with conversation memory
- **Intro Messages**: Provides welcoming messages as per design
- **Chat Method**: Processes user input and returns AI response
- **Memory Management**: Maintains conversation context
- **Model Selection**: Supports multiple Grok models (grok-3-mini, grok-3, grok-3-fast, grok-4)

### FastAPI Routes

- **Session Management**: Create and manage chat sessions
- **Chat Endpoint**: Process messages and return responses
- **History Endpoint**: Retrieve conversation history
- **Reset Endpoint**: Clear conversation memory

## Testing

The Streamlit interface provides a user-friendly way to test the chatbot:

1. **Start the app**: `streamlit run test_chatbot.py`
2. **Test scenarios**:
   - Ask about home improvement projects
   - Test conversation memory
   - Try the reset functionality
   - Upload images (future feature)

## Future Enhancements

- [ ] Image upload and analysis
- [ ] Agentic capabilities with tools
- [ ] Project-specific conversation flows
- [ ] Integration with user profiles
- [ ] Advanced prompt engineering
- [ ] Multi-modal responses

## Troubleshooting

### Common Issues

1. **GROK_API_KEY not found**
   - Make sure you have set the environment variable
   - Check that the `.env` file is in the correct location

2. **Import errors**
   - Ensure all dependencies are installed: `pip install -r requirements.txt`
   - Check Python path and module structure

3. **Streamlit not starting**
   - Verify Streamlit is installed: `pip install streamlit`
   - Check if port 8501 is available

### Debug Mode

For debugging, you can run the chatbot with verbose logging:

```python
# In grok_chatbot.py, set verbose=True
self.conversation = ConversationChain(
    llm=self.llm,
    memory=self.memory,
    verbose=True  # Enable verbose logging
)
``` 