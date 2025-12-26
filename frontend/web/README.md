# Deep Research Frontend

A modern, hierarchical visualization frontend for the Deep Research agentic system.

## 🏗 Project Structure

This project follows a Monorepo-style structure where the frontend and backend are co-located but distinct in responsibility.

```
/
├── frontend/
│   ├── api/            # Backend-for-Frontend (FastAPI)
│   │   ├── main.py     # API Endpoints & SSE Streaming
│   │   └── ...
│   └── web/            # Frontend Application (Next.js)
│       ├── app/        # App Router Pages
│       ├── components/ # React Components (ResearchCanvas, AgentNode)
│       └── lib/        # Utilities & API Clients
└── src/
    └── research_workbench/ # Core Deep Research Logic (LangGraph)
```

## 🚀 Tech Stack

- **Framework**: [Next.js 15](https://nextjs.org/) (App Directory)
- **Styling**: Tailwind CSS (Notion-style aesthetic)
- **Visualization**: [React Flow](https://reactflow.dev/) (DAG visualization)
- **Backend API**: FastAPI (Python)
- **State Management**: React State + Hooks
- **Communication**: Server-Sent Events (SSE) for real-time agent streaming.

## 🛠 Features

- **Hierarchical Visualization**: Visualizes the LangGraph agent execution as a dynamic DAG (Directed Acyclic Graph).
- **Streaming Tool Outputs**: Watch agent thoughts and tool executions (web search, extraction) happen in real-time.
- **Human-in-the-Loop (HITL)**:
    - Persistent chat bar for continuous interaction.
    - User can reply to the agent to provide clarification or new instructions.
    - Graph state is preserved across turns (nodes are appended, not reset).
- **Expandable Nodes**: Agent details (logs, thoughts) can be collapsed or expanded to manage visual clutter.

## ⚡️ Getting Started

### 1. Backend Setup

The frontend relies on the FastAPI server to bridge the Next.js app with the LangGraph core.

```bash
# From the root project directory
# Ensure you have your python dependencies installed (fastapi, uvicorn)
uv run uvicorn frontend.api.main:app --port 8000 --reload
```
*The backend runs on `http://localhost:8000`.*

### 2. Frontend Setup

```bash
# Navigate to the frontend web directory
cd frontend/web

# Install dependencies
npm install

# Run the development server
npm run dev
```
*The web app runs on `http://localhost:3000`.*

## 🧩 Key Components

### `ResearchCanvas.tsx`
The core component managing the React Flow instance. It handles:
- **SSE Connection**: Streams events from `/research/{run_id}/stream`.
- **Graph Construction**: Dynamically adds nodes (`on_chain_start`) and edges.
- **Event Processing**: Updates node data with streaming tokens (`on_chat_model_stream`) and tool outputs (`on_tool_end`).
- **Layout**: Uses `dagre` for automatic top-down tree layout.

### `AgentNode.tsx`
A custom Node component for React Flow.
- Displays agent status (Running/Done).
- Renders a scrollable log of "Thoughts" (LLM generation) and "Tool Calls".
- Supports Notion-like light mode styling.

### `page.tsx`
The main entry point.
- manages the `started` state.
- Handles the initial query and subsequent chat messages.
- Floats the persistent chat input bar at the bottom of the screen.

## 🐛 Troubleshooting

- **Missing Content?** If nodes appear but are empty, check the browser console for connection errors.
- **Hydration Errors?** Ensure you are running the latest version with `suppressHydrationWarning` enabled in `layout.tsx`.
