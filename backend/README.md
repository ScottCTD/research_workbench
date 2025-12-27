# Deep Research Backend

This directory contains the FastAPI backend service that orchestrates the deep research agent using LangGraph. It is responsible for executing the research workflow, managing session state, and streaming real-time events to the frontend.

## Features
- **LangGraph Integration**: Runs the core research agent loop (Planner, Researcher, General Assistant).
- **Real-time Streaming**: Uses Server-Sent Events (SSE) to push state updates (logs, messages, tool calls) to the React frontend.
- **Session Management**: Supports multi-turn conversations and context persistence via `active_thread_id`.
- **Mock Mode**: Includes a `MockGraph` fixture (`test_mock` topic) to simulate research workflows for UI testing without LLM costs.

## Tech Stack
- **FastAPI**: High-performance web framework.
- **LangGraph**: Framework for building stateful, multi-actor applications with LLMs.
- **SSE-Starlette**: For streaming server-sent events.
- **Uvicorn**: ASGI server implementation.

## Setup & Running

### Prerequisites
- Python 3.10+
- `uv` (recommended) or `pip`

### Installation
Ensure you are in the project root (not just `backend/`).

```bash
# Using uv (Recommended)
uv sync
```

### Running the Server
Run the backend server from the project root:

```bash
uv run uvicorn backend.server:app --reload --port 8000
```
Key flags:
- `--reload`: Auto-reload on code changes (dev mode).
- `--port 8000`: Default port expected by the frontend proxy.

## API Endpoints

### `POST /api/research`
Starts a new research session.
- **Body**: `{ "topic": "string" }`
- **Behavior**: Resets the graph state and kicks off the background research task.
- **Special Trigger**: If `topic` is `"test_mock"`, it runs the **Mock Fixture** instead of the real LLM agent.

### `POST /api/chat`
Sends a follow-up message to the *active* research thread.
- **Body**: `{ "message": "string" }`
- **Behavior**: Appends the user message to the existing LangGraph thread and streams the response.

### `GET /api/events`
Subscribe to real-time updates.
- **Protocol**: Server-Sent Events (SSE).
- **Event Types**:
    - `NODE_CREATED`: New agent node (Planner, Researcher) active.
    - `MESSAGE_APPENDED`: Chat messages (Human, AI, Tool).
    - `TOOL_UPDATED`: Tool execution status/result.
    - `UI_MODE_SET`: Switch between Focus (Chat) and Research (Map) views.
    - `GRAPH_RESET`: Clear frontend state.

## Mock Mode
To test the UI without invoking OpenAI/LLMs:
1. Start the server.
2. In the Frontend, enter **"test_mock"** as the research topic.
3. The backend will simulate a plan, a search tool call, and a final report.
