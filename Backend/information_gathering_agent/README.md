# Information Gathering Agent

## Description

The Information Gathering Agent is a diagnostic AI assistant that serves as the first point of contact in the MyHandyAI
multi-agent system. It acts as a virtual handyman diagnostician, gathering comprehensive information about home repair
issues through conversational dialogue with users.

### Key Features

- **Multimodal Input Support**: Accepts both text messages and images from users
- **Conversational Diagnostics**: Conducts natural, dynamic conversations to understand home repair problems
- **Safety-First Triage**: Automatically detects and prioritizes safety-critical issues (gas leaks, electrical sparks,
  flooding)
- **Structured Information Gathering**: Systematically collects key information based on a Home Issue Knowledge Base
  covering 15+ categories
- **Persistent Conversations**: Uses MongoDB checkpointer to maintain conversation context across sessions
- **Tool-Based Workflow**: Uses LangChain tools (`store_home_issue` and `store_summary`) to structure and hand off
  information to downstream agents

### Agent Workflow

1. **Greeting**: Introduces itself and asks about the user's problem
2. **Triage**: Scans for safety risks and provides immediate safety instructions if needed
3. **Problem Identification**: Understands the core complaint through conversation
4. **Categorization**: Classifies the issue using the Home Issue Knowledge Base
5. **Focused Information Gathering**: Asks targeted questions based on the category
6. **Summary & Confirmation**: Creates and confirms a comprehensive summary
7. **Handoff**: Passes the structured information to the Solution Generation Agent

### Supported Home Issue Categories

- Plumbing
- Electrical
- HVAC (Heating/Cooling)
- Roofing & Gutters
- Drywall & Painting
- Flooring
- Doors & Windows
- Appliances
- Carpentry & Woodwork
- Exterior (Decks, Fences, Siding)
- Landscaping & Yard Work
- Pest Control & Wildlife
- Insulation & Weatherproofing
- Smart Home / Low Voltage
- General / Unknown Issue

---

## Configuration

This module requires the following environment variables (see main [README.md](../README.md) for full environment
setup):

- `OPENAI_API_KEY`: OpenAI API key for the language model
- `MONGODB_URI`: MongoDB connection string for conversation persistence
- `INFORMATION_GATHERING_AGENT_MODEL`: OpenAI model name (e.g., `gpt-5`)
- `INFORMATION_GATHERING_AGENT_CHECKPOINT_DATABASE`: MongoDB database name for checkpoints
- `INFORMATION_GATHERING_AGENT_CHECKPOINT_COLLECTION_NAME`: MongoDB collection for checkpoints
- `INFORMATION_GATHERING_AGENT_CHECKPOINT_WRITES_COLLECTION_NAME`: MongoDB collection for checkpoint writes

---

## Module Structure

```text
information_gathering_agent/
├── agent/
│   ├── information_gathering_agent.py    # Main agent class with text/image processing
│   ├── tools.py                          # LangChain tools (store_home_issue, store_summary)
│   └── prompt_templates/
│       ├── v1/                           # Legacy prompt template
│       └── v2/                           # Current prompt template with system prompt
├── services/
│   └── information_gathering_agent_service.py  # Service layer for conversation orchestration
└── dependencies.py                      # Dependency injection for agent instances
```

### Key Components

- **`InformationGatheringAgent`**: Core agent class that processes text and image messages, manages MongoDB
  checkpointer, and interacts with the LLM
- **`InformationGatheringAgentService`**: Service layer that initializes conversations, routes messages, and manages
  conversation state
- **Tools**: LangChain tools for storing structured information:
    - `store_home_issue`: Stores categorized home issue information
    - `store_summary`: Stores conversation summaries for handoff
- **Prompt Templates**: System prompts defining agent personality, workflow, and knowledge base (v2 is current)

---

## API Endpoints

The Information Gathering Agent exposes the following REST API endpoints (mounted at
`/api/v1/information-gathering-agent`):

### Initialize Conversation

Creates a new conversation thread and returns the agent's initial greeting.

```http
POST /api/v1/information-gathering-agent/initialize
Content-Type: application/json

Response:
{
  "thread_id": "uuid-string",
  "initial_message": "Agent greeting message"
}
```

### Send Chat Message

Sends a message (text and/or image) to the agent within an existing conversation thread.

```http
POST /api/v1/information-gathering-agent/chat/{thread_id}
Content-Type: application/json

Request:
{
  "text": "Optional text message",
  "image_base64": "Optional base64-encoded image",
  "image_mime_type": "Optional MIME type (e.g., 'image/jpeg')"
}

Response:
{
  "thread_id": "uuid-string",
  "agent_response": "Agent's response message"
}
```

**Note**: At least one of `text` or `image_base64` must be provided in the request.

