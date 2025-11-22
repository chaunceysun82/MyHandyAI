# MyHandyAI Backend

Backend functionality for MyHandyAI, a multi-agent system for home repair assistance built with Python and FastAPI.

## Overview

MyHandyAI Backend is a FastAPI-based application that provides AI-powered home repair assistance through multiple specialized agents. The system uses LangChain and LangGraph for agent orchestration, with MongoDB for conversation persistence.

### Key Modules

- **[Information Gathering Agent](./information_gathering_agent/README.md)**: Diagnostic AI assistant that gathers comprehensive information about home repair issues through conversational dialogue
- **Chatbot**: Conversational interface for user interactions
- **Content Generation**: Step-by-step guidance generation for home repair tasks
- **Step Guidance**: Interactive step-by-step instructions

---

## Environment Requirements

- **Python**: 3.12 or higher
- **Operating System**: Windows, Linux, or macOS
- **MongoDB**: For conversation persistence (local or remote instance)

---

## Setup with uv

This project uses [uv](https://github.com/astral-sh/uv), a fast Python package installer and resolver, for dependency management. uv provides significant performance improvements over pip and integrates virtual environment management.

### Installing uv

**Linux/macOS:**

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows (PowerShell):**

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**Alternative (via pip):**

```bash
pip install uv
```

For more installation options, see the [uv installation guide](https://docs.astral.sh/uv/getting-started/installation/).

### Setting Up the Project

1. **Create a virtual environment:**

   ```bash
   uv venv
   ```

2. **Activate the virtual environment:**

   **Linux/macOS:**

   ```bash
   source .venv/bin/activate
   ```

   **Windows:**

   ```powershell
   .venv\Scripts\activate
   ```

3. **Install dependencies:**

   ```bash
   uv sync
   ```

   This will install all dependencies from `pyproject.toml` and create/update the `uv.lock` file.

4. **Add new dependencies (if needed):**

   ```bash
   uv add <package-name>
   ```

5. **Run the application:**

   ```bash
   uvicorn main:app --reload
   ```

For more information on uv, see the [uv documentation](https://docs.astral.sh/uv/).

---

## Environment Variables

The application requires the following environment variables, defined in `.env` (or `.env.{ENV}` if the `ENV` variable is set):

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `ENVIRONMENT` | Runtime environment name | `development`, `production` |
| `APP_NAME` | Application name | `MyHandyAI` |
| `APP_VERSION` | Application version | `0.1.0` |
| `APP_PORT` | Port number for the FastAPI server | `8000` |
| `OPENAI_API_KEY` | OpenAI API key for the language model | `sk-...` |
| `MONGODB_URI` | MongoDB connection string for conversation persistence | `mongodb://localhost:27017` or `mongodb://user:pass@host:port/db` |
| `MONGODB_DATABASE` | MongoDB database name | `MainHandyDB` |
| `LANGSMITH_TRACING` | Enable/disable LangSmith tracing | `true`, `false` |
| `LANGSMITH_ENDPOINT` | LangSmith API endpoint | `https://api.smith.langchain.com` |
| `LANGSMITH_API_KEY` | LangSmith API key for observability | `lsv2_...` |
| `LANGSMITH_PROJECT` | LangSmith project name | `myhandyai-dev` |
| `QDRANT_API_KEY` | Qdrant vector database API key | `...` |
| `QDRANT_URL` | Qdrant vector database URL | `https://...` |
| `SERPAPI_API_KEY` | SerpAPI key for web search | `...` |
| `SQS_URL` | AWS SQS queue URL | `https://...` |
| `INFORMATION_GATHERING_AGENT_MODEL` | OpenAI model for information gathering agent | `gpt-4o-mini` |
| `INFORMATION_GATHERING_AGENT_CHECKPOINT_DATABASE` | MongoDB database name for agent checkpoints | `myhandyai` |
| `INFORMATION_GATHERING_AGENT_CHECKPOINT_COLLECTION_NAME` | MongoDB collection for checkpoints | `checkpoints` |
| `INFORMATION_GATHERING_AGENT_CHECKPOINT_WRITES_COLLECTION_NAME` | MongoDB collection for checkpoint writes | `checkpoint_writes` |

### Example `.env` File

```env
ENVIRONMENT=development
APP_NAME=MyHandyAI
APP_VERSION=0.1.0
APP_PORT=8000
OPENAI_API_KEY=sk-your-openai-key-here
MONGODB_URI=mongodb://localhost:27017
MONGODB_DATABASE=MainHandyDB
LANGSMITH_TRACING=true
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGSMITH_API_KEY=lsv2-your-langsmith-key-here
LANGSMITH_PROJECT=myhandyai-dev
QDRANT_API_KEY=your-qdrant-key
QDRANT_URL=https://your-qdrant-url
SERPAPI_API_KEY=your-serpapi-key
SQS_URL=your-sqs-url
INFORMATION_GATHERING_AGENT_MODEL=gpt-5
INFORMATION_GATHERING_AGENT_CHECKPOINT_DATABASE=MainHandyDB
INFORMATION_GATHERING_AGENT_CHECKPOINT_COLLECTION_NAME=InformationGatheringAgentCheckpoints
INFORMATION_GATHERING_AGENT_CHECKPOINT_WRITES_COLLECTION_NAME=InformationGatheringAgentCheckpointWrites
```

---

## Codebase Structure

```text
Backend/
├── main.py                          # FastAPI application entry point
├── config/                          # Configuration management
│   ├── settings.py                  # Environment settings with Pydantic
│   └── logger.py                    # Logging configuration
├── routes/                          # API route handlers
│   ├── information_gathering_agent.py
│   ├── chatbot.py
│   ├── generation.py
│   └── schemas/                     # Request/response models
├── information_gathering_agent/     # Information Gathering Agent module
│   ├── agent/                       # Core agent implementation
│   ├── services/                    # Service layer
│   └── README.md                    # Module documentation
├── chatbot/                         # Chatbot module
├── content_generation/              # Content generation module
├── static/                          # Static files (UI)
└── pyproject.toml                   # Project dependencies (uv)
```

### Key Components

- **FastAPI Application**: Main application with CORS middleware, static file serving, and route registration
- **Configuration**: Centralized settings management using Pydantic Settings with environment-specific `.env` files
- **Logging**: Structured logging with Loguru
- **Routes**: RESTful API endpoints organized by feature
- **Agents**: AI agents built with LangChain and LangGraph
- **Services**: Business logic layer for agent orchestration

---

## Running the Application

1. **Start the FastAPI server:**

   ```bash
   uvicorn main:app --reload
   ```

2. **Access the API:**
   - API Base URL: `http://localhost:8000`
   - Swagger Documentation: `http://localhost:8000/docs`
   - ReDoc Documentation: `http://localhost:8000/redoc`
   - Static UI: `http://localhost:8000/static/`

---

## Technology Stack

- **FastAPI**: Modern web framework for building APIs
- **LangChain**: Framework for LLM application development
- **LangGraph**: Graph-based agent orchestration
- **OpenAI**: Language models for agent reasoning
- **MongoDB**: Conversation persistence via LangGraph checkpointer
- **Pydantic**: Data validation and settings management
- **Loguru**: Structured logging
- **uv**: Fast Python package manager and resolver
- **Mangum**: ASGI adapter for AWS Lambda

---
