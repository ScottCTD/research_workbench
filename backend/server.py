
import asyncio
import json
import uuid
from typing import AsyncGenerator, Dict, Any, List
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage

from research_workbench.deep_research import get_graph, AgentState
from backend.mock_service import MockGraph

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("backend")

app = FastAPI()

# Configure CORS for local frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ResearchRequest(BaseModel):
    topic: str

# Global event subscribers
# Global event subscribers
subscribers: List[asyncio.Queue] = []
history: List[Dict[str, Any]] = []
active_thread_id: str | None = None
is_active_session_mock: bool = False

# Helper to emit events to frontend
async def emit_event(event_type: str, payload: Dict[str, Any]):
    event = {
        "id": str(uuid.uuid4()),
        "type": event_type,
        "payload": payload,
        "timestamp": 0
    }
    logger.info(f"Emitting event: {event_type} to {len(subscribers)} subscribers")
    
    # Store in history
    history.append(event)
    
    # Broadcast
    for q in subscribers:
        await q.put(event)

async def subscribe() -> AsyncGenerator[Dict[str, Any], None]:
    q = asyncio.Queue()
    # Replay history first
    for event in history:
        # We need to yield immediately, but this is an async generator.
        # We can just put them in the queue or yield directly.
        # Yielding directly in the generator loop is safer.
        yield {"data": json.dumps(event)}
        
    subscribers.append(q)
    try:
        while True:
            event = await q.get()
            yield {"data": json.dumps(event)}
    except asyncio.CancelledError:
        subscribers.remove(q)
        raise

async def run_research_task(topic: str):
    """
    Runs the LangGraph agent and translates state updates to frontend events.
    """
    global active_thread_id
    
    is_mock = topic.strip().lower() == "test_mock"
    
    global is_active_session_mock
    is_active_session_mock = is_mock
    
    if is_mock:
        graph = MockGraph()
        logger.info("Using MockGraph for research task")
    else:
        graph = get_graph()
        
    thread_id = str(uuid.uuid4())
    active_thread_id = thread_id
    config = {"configurable": {"thread_id": thread_id}}
    
    # 1. Initialize Graph UI: Create GA Node
    ga_id = "ga-1"
    await emit_event("NODE_CREATED", {"id": ga_id, "kind": "general_assistant", "title": "General Assistant"})
    await emit_event("ACTIVE_NODE_SET", {"id": ga_id})

    # 2. Add User Message
    user_msg_id = str(uuid.uuid4())
    await emit_event("MESSAGE_APPENDED", {
        "id": user_msg_id,
        "nodeId": ga_id,
        "kind": "human",
        "content": topic,
        "timestamp": 0
    })

    # 3. Stream the Graph execution
    # We use astream_events or just astream to watch for tokens/state changes.
    # For this MVP, let's just use astream and look at state snapshots or node outputs.
    # astream yields the output of the node that just finished.
    
    logger.info(f"Starting research on: {topic}")
    
    # Track processed messages to avoid duplicates if we inspect full state
    processed_msg_ids = {user_msg_id}
    
    # Map graph nodes to frontend node IDs
    node_mapping = {"general_assistant": ga_id}
    planner_id = None
    
    # Initial input
    inputs = {"general_assistant_messages": [HumanMessage(content=topic)]}

    async for event in graph.astream(inputs, config=config, stream_mode="updates"):
        # event is a dict like { 'node_name': { 'key': value } }
        for node_name, updates in event.items():
            logger.info(f"Node finished: {node_name}")
            
            # Determine the current frontend node ID
            current_node_id = node_mapping.get(node_name)
            
            # Setup Planner node if needed
            if node_name == "planner" and "planner" not in node_mapping:
                planner_id = "planner-1"
                node_mapping["planner"] = planner_id
                await emit_event("NODE_CREATED", {"id": planner_id, "kind": "planner", "title": "Research Planner"})
                await emit_event("EDGE_CREATED", {"source": ga_id, "target": planner_id})
                await emit_event("ACTIVE_NODE_SET", {"id": planner_id})
                # Switch UI mode to research
                await emit_event("UI_MODE_SET", {"mode": "research"})
                current_node_id = planner_id
            
            if node_name == "general_assistant":
                 await emit_event("ACTIVE_NODE_SET", {"id": ga_id})

            if node_name == "write_report" and "write_report" not in node_mapping:
                 # Usually write_report goes back to GA, but if we wanted a node:
                 pass

            # Extract messages from the updates
            # The structure of updates depends on the node's return value.
            # In deep_research.py, they return Command(update={ "key": [...] })
            # astream(stream_mode="updates") yields the update dict.
            
            msgs = []
            if "general_assistant_messages" in updates:
                msgs = updates["general_assistant_messages"]
            elif "planner_messages" in updates:
                msgs = updates["planner_messages"]
                
            # 'msgs' could be a list or a single message depending on how `add_messages` works
            if not isinstance(msgs, list):
                msgs = [msgs]
            
            for m in msgs:
                if not isinstance(m, BaseMessage):
                    continue
                    
                # HACK: dedup based on content hash or similar if ID not present? 
                # LangChain messages usually have 'id' if persistent, but here they might be new.
                # Let's simple check if we've seen this object or create a new ID.
                if hasattr(m, "id") and m.id and m.id in processed_msg_ids:
                    continue
                
                mid = getattr(m, "id", None) or str(uuid.uuid4())
                processed_msg_ids.add(mid)
                
                kind = "assistant"
                if isinstance(m, HumanMessage): kind = "human"
                elif isinstance(m, ToolMessage): kind = "tool"
                
                try:
                    # Emit flatten message matching frontend Message interface
                    payload = {
                        "id": mid,
                        "nodeId": current_node_id,
                        "kind": kind,
                        "content": str(m.content),
                        "timestamp": 0
                    }
                    
                    # Handle Tool Calls
                    if hasattr(m, "tool_calls") and m.tool_calls:
                        # 1. Emit text part if any
                        if m.content:
                             await emit_event("MESSAGE_APPENDED", payload)

                        # 2. Emit tool calls
                        for tc in m.tool_calls:
                            tc_id = tc["id"]
                            tool_msg_payload = {
                                "id": tc_id,
                                "nodeId": current_node_id,
                                "kind": "tool",
                                "content": "", # Tool call bubble info is in toolCall
                                "toolCall": {
                                    "toolName": tc["name"],
                                    "toolCallId": tc["id"],
                                    "input": tc["args"], # Mapped to 'input' for frontend
                                    "status": "running",
                                    "timestamp": 0
                                },
                                "timestamp": 0
                            }
                            await emit_event("MESSAGE_APPENDED", tool_msg_payload)
                    
                    elif isinstance(m, ToolMessage):
                        # Update the status of the tool call
                        await emit_event("TOOL_UPDATED", {
                            "messageId": m.tool_call_id,
                            "status": "success",
                            "output": str(m.content)
                        })
                    else:
                        # Normal message
                        await emit_event("MESSAGE_APPENDED", payload)
                except Exception as e:
                    logger.error(f"Error processing message {mid}: {e}")
    
    await emit_event("WORKFLOW_COMPLETED", {})

async def continue_research_task(message: str):
    """
    Continues the conversation on the active thread.
    """
    global active_thread_id
    if not active_thread_id:
        return

    # In a real app we would persist "is_mock" state. 
    # For MVP, we can just check if we are in a 'test_mock' flow or use a global flag.
    # Let's check a global flag for simplicity or just try to get graph.
    # Hack: If the active thread was created by mock, we should use mock.
    # But since we re-get graph here, we need to know.
    # Quick fix: If message is "test_mock" (unlikely in chat) or we store it.
    
    # Better: Global 'is_active_session_mock'
    global is_active_session_mock
    
    if is_active_session_mock:
         graph = MockGraph()
    else:
         graph = get_graph()

    config = {"configurable": {"thread_id": active_thread_id}}
    
    # 1. Emit User Message
    user_msg_id = str(uuid.uuid4())
    # We need to know the active node to append message to... 
    # For MVP assume we are chatting with General Assistant (ga-1)
    # Ideally frontend sends activeNodeId with request.
    ga_id = "ga-1" 
    
    await emit_event("MESSAGE_APPENDED", {
        "id": user_msg_id,
        "nodeId": ga_id,
        "kind": "human",
        "content": message,
        "timestamp": 0
    })

    logger.info(f"Continuing research with: {message}")
    
    node_mapping = {"general_assistant": ga_id, "planner": "planner-1"} 
    processed_msg_ids = {user_msg_id} # simple local dedup for this run
    
    inputs = {"general_assistant_messages": [HumanMessage(content=message)]}

    async for event in graph.astream(inputs, config=config, stream_mode="updates"):
        for node_name, updates in event.items():
            logger.info(f"Node finished: {node_name}")
            current_node_id = node_mapping.get(node_name, ga_id)

            msgs = []
            if "general_assistant_messages" in updates:
                msgs = updates["general_assistant_messages"]
            elif "planner_messages" in updates:
                msgs = updates["planner_messages"]
                
            if not isinstance(msgs, list): msgs = [msgs]
            
            for m in msgs:
                if not isinstance(m, BaseMessage): continue
                
                mid = getattr(m, "id", None) or str(uuid.uuid4())
                if mid in processed_msg_ids: continue
                processed_msg_ids.add(mid)
                
                kind = "assistant"
                if isinstance(m, HumanMessage): kind = "human"
                elif isinstance(m, ToolMessage): kind = "tool"
                
                payload = {
                    "id": mid,
                    "nodeId": current_node_id,
                    "kind": kind,
                    "content": str(m.content),
                    "timestamp": 0
                }
                
                if hasattr(m, "tool_calls") and m.tool_calls:
                    if m.content: await emit_event("MESSAGE_APPENDED", payload)
                    for tc in m.tool_calls:
                        tc_id = tc["id"]
                        tool_msg_payload = {
                            "id": tc_id,
                            "nodeId": current_node_id,
                            "kind": "tool",
                            "content": "",
                            "toolCall": {
                                "toolName": tc["name"],
                                "toolCallId": tc["id"],
                                "input": tc["args"],
                                "status": "running",
                                "timestamp": 0
                            },
                            "timestamp": 0
                        }
                        await emit_event("MESSAGE_APPENDED", tool_msg_payload)
                elif isinstance(m, ToolMessage):
                    await emit_event("TOOL_UPDATED", {
                        "messageId": m.tool_call_id,
                        "status": "success",
                        "output": str(m.content)
                    })
                else:
                    await emit_event("MESSAGE_APPENDED", payload)

@app.post("/api/research")
async def start_research(request: ResearchRequest):
    """
    Start a new research task.
    """
    # Clear history for fresh session
    history.clear()
    
    # Notify clients to reset UI
    await emit_event("GRAPH_RESET", {})
    
    # Start the task in background
    asyncio.create_task(run_research_task(request.topic))
    return {"status": "started", "topic": request.topic}

class ChatRequest(BaseModel):
    message: str

@app.post("/api/chat")
async def chat(request: ChatRequest):
    """
    Send a follow-up message to the active research task.
    """
    global active_thread_id
    if not active_thread_id:
        return {"status": "error", "message": "No active research session"}
        
    # Run the graph with new input on existing thread
    asyncio.create_task(continue_research_task(request.message))
    return {"status": "sent", "message": request.message}

@app.get("/api/events")
async def event_stream(request: Request):
    """
    SSE Endpoint.
    """
    return EventSourceResponse(subscribe())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
