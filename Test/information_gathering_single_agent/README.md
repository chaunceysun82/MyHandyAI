# MyHandyAI Information Gathering Agent

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

## Environment Variables

The application requires the following environment variables, defined in `.env` (or `.env.{ENV}` if the `ENV` variable
is set):

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `ENVIRONMENT` | Runtime environment name | `development`, `production` |
| `APP_NAME` | Application name | `MyHandyAI` |
| `APP_VERSION` | Application version | `0.1.0` |
| `APP_PORT` | Port number for the FastAPI server | `8000` |
| `OPENAI_API_KEY` | OpenAI API key for the language model | `sk-...` |
| `MONGODB_URI` | MongoDB connection string for conversation persistence | `mongodb://localhost:27017` or `mongodb://user:pass@host:port/db` |
| `LANGSMITH_TRACING` | Enable/disable LangSmith tracing | `true`, `false` |
| `LANGSMITH_ENDPOINT` | LangSmith API endpoint | `https://api.smith.langchain.com` |
| `LANGSMITH_API_KEY` | LangSmith API key for observability | `lsv2_...` |
| `LANGSMITH_PROJECT` | LangSmith project name | `myhandyai-dev` |

### Example `.env` File

```env
ENVIRONMENT=development
APP_NAME=MyHandyAI
APP_VERSION=0.1.0
APP_PORT=8000
OPENAI_API_KEY=sk-your-openai-key-here
MONGODB_URI=mongodb://localhost:27017
LANGSMITH_TRACING=true
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGSMITH_API_KEY=lsv2-your-langsmith-key-here
LANGSMITH_PROJECT=myhandyai-dev
```

---

## Module Descriptions

### `main.py`

- **Purpose**: FastAPI application entry point
- **Key Responsibilities**:
    - Initializes FastAPI app with lifespan management
    - Sets up logging on startup
    - Mounts static files directory
    - Registers API routers (health check, information gathering agent)
    - Configures server settings from environment variables

### `config/settings.py`

- **Purpose**: Centralized configuration management
- **Key Features**:
    - Uses Pydantic Settings for type-safe configuration
    - Supports environment-specific `.env` files (`.env.{ENV}`)
    - Caches settings using `@lru_cache` for performance
    - Loads all required environment variables

### `config/logger.py`

- **Purpose**: Application-wide logging configuration
- **Key Features**:
    - Configures Loguru logger with colorized output
    - Sets up stdout logging with formatted timestamps

### `business/agents/information_gathering_agent/`

- **Purpose**: Core AI agent implementation
- **Components**:
    - **`information_gathering_agent.py`**: Main agent class with methods for processing text and image messages,
      managing MongoDB checkpointer
    - **`tools.py`**: LangChain tools (`store_home_issue`, `store_summary`) with Pydantic schemas
    - **`prompt_templates/v2/`**: System prompt defining agent personality, workflow, and knowledge base

### `business/services/information_gathering_agent_service.py`

- **Purpose**: Service layer orchestrating agent interactions
- **Key Responsibilities**:
    - Initializes conversations with unique thread IDs
    - Routes messages (text/image/both) to appropriate agent methods
    - Handles conversation state management

### `business/dependencies.py`

- **Purpose**: Dependency injection for business layer components
- **Key Features**:
    - Provides factory functions for creating agent instances
    - Enables testability through dependency injection

### `presentation/routers/v1/information_gathering_agent.py`

- **Purpose**: REST API endpoints for agent interactions
- **Endpoints**:
    - `POST /api/v1/information-gathering-agent/initialize`: Start a new conversation
    - `POST /api/v1/information-gathering-agent/chat`: Send messages to the agent

### `presentation/routers/health.py`

- **Purpose**: Health check endpoint
- **Endpoint**: `GET /api/v1/healthy`

### `presentation/schemas/`

- **Purpose**: Request/response validation and serialization
- **Components**:
    - **`request/information_gathering_agent.py`**: Request models (ChatMessageRequest)
    - **`response/information_gathering_agent.py`**: Response models (InitializeConversationResponse,
      ChatMessageResponse)

### `presentation/dependencies.py`

- **Purpose**: Dependency injection for presentation layer
- **Key Features**:
    - Wires business layer dependencies to presentation layer
    - Provides type-annotated dependency aliases for FastAPI

---

## API Endpoints

### Initialize Conversation

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

```http
POST /api/v1/information-gathering-agent/chat
Content-Type: application/json

Request:
{
  "thread_id": "uuid-string",
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

### Health Check

```http
GET /api/v1/healthy

Response:
{
  "status": "Healthy"
}
```

---

## Access the Swagger Docs

Navigate to `http://localhost:8000/docs` in your browser

## Access the UI

Navigate to `http://localhost:8000/static/` in your browser

---

## Technology Stack

- **FastAPI**: Web framework for building APIs
- **LangChain**: Framework for LLM application development
- **LangGraph**: Graph-based agent orchestration
- **OpenAI GPT-5-mini**: Language model for agent reasoning
- **MongoDB**: Conversation persistence via LangGraph checkpointer
- **Pydantic**: Data validation and settings management
- **Loguru**: Structured logging