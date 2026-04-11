# Project Assistant Agent

## Description

The Project Assistant Agent is a supportive AI assistant that helps users during the execution phase of their DIY
projects. It operates after the Information Gathering Agent and Planner Agent have completed their work, providing
step-by-step guidance and troubleshooting support as users work through their project.

### Key Features

- **Multimodal Input Support**: Accepts both text messages and images from users
- **Step-Specific Guidance**: Provides contextual help based on the current step the user is working on
- **Image Analysis**: Analyzes uploaded images to assess progress, identify issues, and provide specific guidance
- **Context-Aware Responses**: Understands project context including steps, tools, safety warnings, and tips
- **Persistent Conversations**: Uses MongoDB checkpointer (shared with Information Gathering Agent) to maintain
  conversation context
- **No Tools Required**: Provides guidance through conversation only, no external tools needed

### Agent Workflow

1. **Context Loading**: Receives project data including steps, tools, and current step information
2. **User Query Processing**: Processes user questions or images in the context of the current step
3. **Response Generation**: Provides helpful, actionable guidance based on project context
4. **Image Analysis** (if image provided): Analyzes images to assess progress and provide specific feedback

### Step Number Context

The agent adapts its behavior based on the step number:

- **`step_number = -1`**: User is on the project overview page (can answer general questions about the project)
- **`step_number = 0`**: User is on the tools page (provides detailed tool information including descriptions, prices,
  risk factors, and safety measures)
- **`step_number >= 1`**: User is on a specific project step (provides step-specific guidance including instructions,
  tools needed, safety warnings, and tips)

---

## Configuration

This module requires the following environment variables (see main [README.md](../../README.md) for full environment
setup):

- `OPENAI_API_KEY`: OpenAI API key for the language model
- `MONGODB_URI`: MongoDB connection string for conversation persistence
- `MONGODB_DATABASE`: MongoDB database name for project data storage
- `STEP_GUIDANCE_MODEL`: OpenAI model name (e.g., `gpt-5-nano`)
- `MYHANDYAI_AGENTS_CHECKPOINT_DATABASE`: MongoDB database name for agent checkpoints (shared with Information Gathering
  Agent)
- `MYHANDYAI_AGENTS_CHECKPOINT_COLLECTION_NAME`: MongoDB collection for checkpoints
- `MYHANDYAI_AGENTS_CHECKPOINT_WRITES_COLLECTION_NAME`: MongoDB collection for checkpoint writes

---

## Module Structure

```text
project_assistant_agent/
├── agent/
│   ├── project_assistant_agent.py    # Main agent class with text/image processing
│   └── prompt_templates/
│       └── v1/
│           └── project_assistant_agent.py  # System prompt template
├── services/
│   └── project_assistant_agent_service.py  # Service layer with context building
├── dependencies.py                      # Dependency injection for agent instances
└── step_guidance_chatbot.py            # Legacy implementation (to be moved)
```

### Key Components

- **`ProjectAssistantAgent`**: Core agent class that processes text and image messages, manages MongoDB checkpointer,
  and interacts with the LLM
- **`ProjectAssistantAgentService`**: Service layer that builds project context, routes messages, and manages
  conversation state
- **`_build_context()`**: Method that fetches and formats project data, user information, and step details into a
  structured context string
- **Prompt Templates**: System prompts defining agent personality, environment awareness, tone, context handling, goals,
  and guardrails

---

## API Endpoints

The Project Assistant Agent exposes the following REST API endpoints (mounted at `/api/v1/project-assistant-agent`):

### Send Chat Message

Sends a message (text and/or image) to the agent within an existing conversation thread. Uses the same thread_id as the
Information Gathering Agent.

```http
POST /api/v1/project-assistant-agent/chat/{thread_id}
Content-Type: application/json

Request:
{
  "project_id": "project-id-string",
  "text": "Optional text message",
  "image_base64": "Optional base64-encoded image",
  "image_mime_type": "Optional MIME type (e.g., 'image/jpeg')",
  "step_number": -1  // -1 for overview, 0 for tools, >=1 for specific step
}

Response:
{
  "thread_id": "uuid-string",
  "agent_response": "Agent's response message"
}
```

**Note**: At least one of `text` or `image_base64` must be provided in the request. The `step_number` parameter
determines what context is provided to the agent.

### Get Conversation History

Retrieves the full conversation history for a given thread.

```http
GET /api/v1/project-assistant-agent/chat/{thread_id}/history

Response:
{
  "thread_id": "uuid-string",
  "messages": [
    {
      "role": "user",
      "content": "User message"
    },
    {
      "role": "assistant",
      "content": "Agent response"
    }
  ]
}
```

---

## Context Building

The `_build_context()` method in `ProjectAssistantAgentService` structures project data into a formatted context string
that includes:

1. **Project Information**: Title, problem summary, total steps
2. **User Information**: Name, email, state, country, and experience level (for context-aware guidance)
3. **Tools and Materials**: List of required tools (with full details if step_number=0, including descriptions, prices,
   risk factors, and safety measures)
4. **All Project Steps (Complete Context)**: **ALL steps** in the project are included, whether completed or pending,
   providing complete context awareness:
    - Step title and number
    - Estimated time
    - Tools needed
    - Instructions
    - Safety warnings
    - Tips
    - Completion status
5. **Current Step Context**: Additional context highlighting which step the user is currently on

The context is injected into the system prompt using string formatting (`build_system_prompt()` function) under the "
Context" section, providing the agent with comprehensive project awareness to assist users effectively.

---

## Migration from Step Guidance Chatbot

This agent replaces the legacy `step_guidance_chatbot.py` implementation with:

- **LangChain Integration**: Uses LangChain agents and LangGraph for state management
- **MongoDB Checkpointer**: Uses shared checkpoint database with Information Gathering Agent
- **Structured Prompts**: Versioned prompt templates with clear sections
- **Service Layer**: Separated business logic into service layer with context building
- **No Pickle**: Removed pickle-based state serialization in favor of LangGraph state management
- **Unified Threading**: Uses same thread_id as Information Gathering Agent for seamless conversation flow

---

## Usage Example

```python
from agents.project_assistant_agent.dependencies import ProjectAssistantAgentServiceDependency


# In a FastAPI route
@router.post("/chat/{thread_id}")
async def chat(
        thread_id: UUID,
        request: ChatMessageRequest,
        service: ProjectAssistantAgentServiceDependency
):
    response, _ = service.process_message(
        thread_id=thread_id,
        project_id=request.project_id,
        text=request.text,
        image_base64=request.image_base64,
        image_mime_type=request.image_mime_type,
        step_number=request.step_number
    )
    return ChatMessageResponse(thread_id=thread_id, agent_response=response)
```
