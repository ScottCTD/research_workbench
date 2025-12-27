
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
    
    # 3. Stream the Graph execution using astream_events (V2)
    logger.info(f"Starting research on: {topic}")
    
    # Map graph nodes to frontend node IDs
    node_mapping = {"general_assistant": ga_id}
    planner_id = None
    
    # Default current node
    current_node_id = ga_id

    # Track runs to avoid processing "Generic" chains that are not relevant
    # We focus on chat models and tools.
    processed_msg_ids = {user_msg_id}
    inputs = {"general_assistant_messages": [HumanMessage(content=topic)]}
    
    async for event in graph.astream_events(inputs, config=config, version="v2"):
        kind = event["event"]
        name = event["name"]
        run_id = event["run_id"]
        
        # 1. Update Current Node Context
        # We rely on 'langgraph_node' metadata. 
        # CAUTION: Nested agents (start_research) might not have 'langgraph_node' set to 'planner' explicitly 
        # if they are in a sub-graph. But usually 'planner' stays active.
        # We'll use a heuristic: if we see 'langgraph_node' change to 'planner', we update.
        meta = event.get("metadata", {})
        lg_node = meta.get("langgraph_node")
        
        if lg_node == "planner":
            latest_planner_id = node_mapping.get("planner")
            
            if latest_planner_id:
                # We have an existing planner.
                # Logic: Only create a NEW planner node if we are outputting TEXT (thought/speech)
                # AND we are currently positioned at a different node (e.g., returning from a specialized task).
                # This prevents creating empty planner nodes just for processing tool outputs.
                
                is_text_stream = (kind == "on_chat_model_stream")
                
                if is_text_stream and current_node_id != latest_planner_id:
                     # Create Planner-Next
                    new_planner_id = f"planner-{str(uuid.uuid4())[:4]}"
                    node_mapping["planner"] = new_planner_id # Update latest mapping
                    
                    await emit_event("NODE_CREATED", {"id": new_planner_id, "kind": "planner", "title": "Research Planner"})
                    
                    # Edge from previous task
                    await emit_event("EDGE_CREATED", {"source": current_node_id, "target": new_planner_id})
                    # Edge from old planner (history)
                    await emit_event("EDGE_CREATED", {"source": latest_planner_id, "target": new_planner_id})
                    
                    await emit_event("ACTIVE_NODE_SET", {"id": new_planner_id})
                    current_node_id = new_planner_id
                else:
                    # Reuse existing planner node (Star Topology for parallel tools)
                    current_node_id = latest_planner_id
            
            else:
                # First time initialization
                planner_id = "planner-1"
                node_mapping["planner"] = planner_id
                await emit_event("NODE_CREATED", {"id": planner_id, "kind": "planner", "title": "Research Planner"})
                await emit_event("EDGE_CREATED", {"source": ga_id, "target": planner_id})
                await emit_event("ACTIVE_NODE_SET", {"id": planner_id})
                await emit_event("UI_MODE_SET", {"mode": "research"})
                current_node_id = planner_id

        elif lg_node == "general_assistant":
            # Similar logic for GA if we want GA-2, GA-3...
            # For now, let's just create GA-Next if coming back from Planner
            latest_ga_id = node_mapping.get("general_assistant", ga_id)
            if latest_ga_id and current_node_id != latest_ga_id:
                 new_ga_id = f"ga-{str(uuid.uuid4())[:4]}"
                 node_mapping["general_assistant"] = new_ga_id
                 await emit_event("NODE_CREATED", {"id": new_ga_id, "kind": "general_assistant", "title": "General Assistant"})
                 await emit_event("EDGE_CREATED", {"source": current_node_id, "target": new_ga_id})
                 await emit_event("EDGE_CREATED", {"source": latest_ga_id, "target": new_ga_id})
                 await emit_event("ACTIVE_NODE_SET", {"id": new_ga_id})
                 current_node_id = new_ga_id
            else:
                 current_node_id = latest_ga_id

        # Check for Nested Agents / Tools that should be Visualized as Nodes
        
        # 1. Start Research (Researcher Agent)
        if name == "start_research" and kind == "on_tool_start":
             # Create new Researcher node
             res_id = f"researcher-{run_id[:8]}"
             node_mapping[run_id] = res_id 
             
             await emit_event("NODE_CREATED", {"id": res_id, "kind": "researcher", "title": "Researcher"})
             # Connect from current node (usually Planner)
             await emit_event("EDGE_CREATED", {"source": current_node_id, "target": res_id})
             
             await emit_event("ACTIVE_NODE_SET", {"id": res_id})
             current_node_id = res_id # Switch context to this researcher

        # 2. Write Report (Writer Agent)
        if name == "write_report" and kind == "on_tool_start":
             writer_id = f"writer-{run_id[:8]}"
             # Create Writer Node
             await emit_event("NODE_CREATED", {"id": writer_id, "kind": "writer", "title": "Report Writer"})
             await emit_event("EDGE_CREATED", {"source": current_node_id, "target": writer_id})
             
             await emit_event("ACTIVE_NODE_SET", {"id": writer_id})
             current_node_id = writer_id
        
        # 2. Handle Events
        
        # A. Chat Model Streaming (Text)
        if kind == "on_chat_model_stream":
            chunk = event["data"]["chunk"]
            # Only process if there is content (ignore tool call chunks for message text)
            if chunk.content:
                content = chunk.content
                # Check if we've seen this run_id before.
                # Since we don't keep checking a set for 'MESSAGE_UPDATED', checking 'processed_msg_ids' 
                # helps us decide if we Append (idx 0) or Update.
                # Actually, frontend reducer handles duplication safely now, but best valid logic is:
                # First time -> Append (empty or first chunk), Subsequent -> Update.
                
                # We'll use a local set to track initialized message IDs for this stream loop
                if run_id not in processed_msg_ids:
                    processed_msg_ids.add(run_id)
                    await emit_event("MESSAGE_APPENDED", {
                        "id": run_id,
                        "nodeId": current_node_id,
                        "kind": "assistant",
                        "content": content,
                        "timestamp": 0
                    })
                else:
                    await emit_event("MESSAGE_UPDATED", {
                        "id": run_id,
                        "content": content
                    })

        # B. Tool Start
        elif kind == "on_tool_start":
            # Filter out internal LangChain tools or trivial ones if needed.
            # We want to show 'web_search', 'start_research', etc.
            # We skip 'start_deep_research' wrapper if we want, but actually it's fine to show it.
            tool_data = event["data"].get("input")
            
            processed_msg_ids.add(run_id)
            await emit_event("MESSAGE_APPENDED", {
                "id": run_id,
                "nodeId": current_node_id,
                "kind": "tool",
                "content": f"Running {name}...",
                "toolCall": {
                    "toolName": name,
                    "toolCallId": run_id,
                    "input": tool_data,
                    "status": "running",
                    "timestamp": 0
                },
                "timestamp": 0
            })

        # C. Tool End
        elif kind == "on_tool_end":
            output = event["data"].get("output")
            # Output can be ToolMessage or string or dict.
            # We sanitize it for display.
            output_str = str(output)
            if hasattr(output, "content"):
                output_str = str(output.content)
            
            await emit_event("TOOL_UPDATED", {
                "messageId": run_id,
                "status": "success", # or error if we detect it
                "output": output_str
            })
            
    await emit_event("WORKFLOW_COMPLETED", {})

async def continue_research_task(message: str):
    """
    Continues the conversation on the active thread.
    """
    global active_thread_id
    if not active_thread_id:
        return

    global is_active_session_mock
    if is_active_session_mock:
         graph = MockGraph()
    else:
         graph = get_graph()

    config = {"configurable": {"thread_id": active_thread_id}}
    
    # Emit User Message
    user_msg_id = str(uuid.uuid4())
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
    processed_msg_ids = {user_msg_id} 
    current_node_id = ga_id
    
    inputs = {"general_assistant_messages": [HumanMessage(content=message)]}

    async for event in graph.astream_events(inputs, config=config, version="v2"):
        kind = event["event"]
        name = event["name"]
        run_id = event["run_id"]
        
        meta = event.get("metadata", {})
        lg_node = meta.get("langgraph_node")
        
        if lg_node == "planner":
             current_node_id = node_mapping.get("planner", "planner-1")
        elif lg_node == "general_assistant":
             current_node_id = node_mapping.get("general_assistant", ga_id)

        # A. Chat Model Streaming (Text)
        if kind == "on_chat_model_stream":
            chunk = event["data"]["chunk"]
            if chunk.content:
                content = chunk.content
                if run_id not in processed_msg_ids:
                    processed_msg_ids.add(run_id)
                    await emit_event("MESSAGE_APPENDED", {
                        "id": run_id,
                        "nodeId": current_node_id,
                        "kind": "assistant",
                        "content": content,
                        "timestamp": 0
                    })
                else:
                    await emit_event("MESSAGE_UPDATED", {
                        "id": run_id,
                        "content": content
                    })

        # B. Tool Start
        elif kind == "on_tool_start":
            tool_data = event["data"].get("input")
            processed_msg_ids.add(run_id)
            await emit_event("MESSAGE_APPENDED", {
                "id": run_id,
                "nodeId": current_node_id,
                "kind": "tool",
                "content": f"Running {name}...",
                "toolCall": {
                    "toolName": name,
                    "toolCallId": run_id,
                    "input": tool_data,
                    "status": "running",
                    "timestamp": 0
                },
                "timestamp": 0
            })

        # C. Tool End
        elif kind == "on_tool_end":
            output = event["data"].get("output")
            output_str = str(output)
            if hasattr(output, "content"):
                output_str = str(output.content)
            
            await emit_event("TOOL_UPDATED", {
                "messageId": run_id,
                "status": "success",
                "output": output_str
            })

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
