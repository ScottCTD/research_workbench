# Deep Research Frontend

A modern, heavy-interactive React application for the Deep Research Agent. It visualizes the agent's thought process as a dynamic graph and supports real-time chat interactions.

## Features
- **Dual View Modes**:
    - **Focus Mode**: A clean, chat-centric interface for initiating research and having conversations with the agent.
    - **Research Map (DAG)**: A node-based visualization (using React Flow) showing the parallel execution of research tasks, tool calls, and planning steps.
- **Real-time Updates**: Powered by Server-Sent Events (SSE) to display logs, thoughts, and partial outputs instantly.
- **Interactive Tool Bubbles**: Inspect tool inputs and outputs (e.g., search queries, browser results) in detail.
- **Multi-turn Chat**: Ask follow-up questions to your research agent directly from the UI.
- **Mock Mode Support**: Native support for visualizing the backend's "test_mock" simulation.

## Tech Stack
- **React 18**: Core UI library.
- **Vite**: Fast build tool and dev server.
- **Tailwind CSS**: Utility-first styling.
- **React Flow**: For rendering the research DAG (Directed Acyclic Graph).
- **Zustand**: State management (handling SSE events and graph state).
- **Framer Motion**: Smooth animations and transitions.
- **Lucide React**: Iconography.

## Setup & Running

### Prerequisites
- Node.js 18+
- npm

### Installation
Navigate to the frontend directory:
```bash
cd frontend
npm install
```

### Running the App
Start the development server:

```bash
npm run dev
```
The app will be available at `http://localhost:5173`.

> **Note**: This requires the Python backend to be running on `http://localhost:8000`.

## Architecture Highlights
- **State Management (`src/state`)**:
    - `store.ts`: Main Zustand store.
    - `reducers.ts`: Handles incoming SSE events (`NODE_CREATED`, `MESSAGE_APPENDED`, etc.) to update the graph and message history.
- **Components (`src/components`)**:
    - `views/FocusView.tsx`: The initial chat interface.
    - `views/ResearchView.tsx`: The graph visualization wrapper.
    - `canvas/GraphCanvas.tsx`: The React Flow canvas implementation.
- **Event Driven**: The UI is purely reactive to backend events. It does not "predict" the state; it renders exactly what the backend streams.

## Usage
1. **Start Research**: Enter a topic (e.g., "Quantum Computing trends") in the Focus View.
2. **Watch the Graph**: The UI switches to the Research Map as the agent plans and executes searches.
3. **Inspect Tools**: Click on any tool bubble (e.g., "Search", "Scrape") to see raw JSON inputs/outputs.
4. **Follow Up**: Click "Back to Chat" to review the final report and ask clarifying questions in the chat thread.
