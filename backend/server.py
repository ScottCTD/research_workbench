
import asyncio
import json
import time
import uuid
from collections import defaultdict
from typing import AsyncGenerator, Dict, Any, List

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel
from langchain_core.messages import HumanMessage

from loguru import logger

from research_workbench.deep_research import get_graph
from backend.mock_service import MockGraph

app = FastAPI()

STREAM_EMIT_INTERVAL = 0.1

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
    # Avoid logging per-event to prevent log storms during streaming.
    # Store in history
    history.append(event)
    
    # Broadcast
    for q in subscribers:
        await q.put(event)

def get_latest_node_id(kind: str) -> str | None:
    for event in reversed(history):
        if event.get("type") != "NODE_CREATED":
            continue
        payload = event.get("payload", {})
        if payload.get("kind") == kind:
            return payload.get("id")
    return None

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
    logger.info("Starting research on: {}", topic)
    
    # Map graph nodes to frontend node IDs
    node_mapping = {"general_assistant": ga_id}
    planner_id = None
    run_id_to_node_id: Dict[str, str] = {}
    
    # Default current node
    current_node_id = ga_id
    pending_researcher_ids: List[str] = []

    # Track runs to avoid processing "Generic" chains that are not relevant
    # We focus on chat models and tools.
    processed_msg_ids = {user_msg_id}
    pending_stream_chunks: Dict[str, str] = defaultdict(str)
    last_stream_emit: Dict[str, float] = {}
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
        node_hint = (
            meta.get("node_id")
            or meta.get("agent_node_id")
            or meta.get("researcher_id")
        )
        if node_hint:
            run_id_to_node_id[run_id] = node_hint
        
        if lg_node == "planner":
            latest_planner_id = node_mapping.get("planner")
            
            if latest_planner_id:
                # We have an existing planner.
                # Logic: Only create a NEW planner node if we are outputting TEXT (thought/speech)
                # AND we are currently positioned at a different node (e.g., returning from a specialized task).
                # This prevents creating empty planner nodes just for processing tool outputs.
                
                is_text_stream = (kind == "on_chat_model_stream")
                
                if is_text_stream and (pending_researcher_ids or current_node_id != latest_planner_id):
                     # Create Planner-Next
                    new_planner_id = f"planner-{str(uuid.uuid4())[:4]}"
                    node_mapping["planner"] = new_planner_id # Update latest mapping
                    
                    await emit_event("NODE_CREATED", {"id": new_planner_id, "kind": "planner", "title": "Research Planner"})
                    
                    # If we just finished researcher nodes, fork the planner after them.
                    sources: List[str] = [latest_planner_id]
                    if pending_researcher_ids:
                        sources.extend(pending_researcher_ids)
                    else:
                        sources.append(current_node_id)

                    seen_sources = set()
                    for source in sources:
                        if not source or source in seen_sources:
                            continue
                        seen_sources.add(source)
                        await emit_event("EDGE_CREATED", {"source": source, "target": new_planner_id})

                    pending_researcher_ids.clear()
                    
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

        elif lg_node == "write_report":
            writer_node_id = node_mapping.get("write_report")
            if writer_node_id:
                current_node_id = writer_node_id

        if run_id not in run_id_to_node_id:
            if lg_node and lg_node in node_mapping:
                run_id_to_node_id[run_id] = node_mapping[lg_node]
            else:
                parent_ids: List[str] = []
                parent_list = (
                    event.get("parent_ids")
                    or event.get("parent_run_ids")
                    or meta.get("parent_ids")
                    or meta.get("parent_run_ids")
                )
                if isinstance(parent_list, (list, tuple)):
                    parent_ids.extend([pid for pid in parent_list if pid])
                parent_id = (
                    event.get("parent_id")
                    or event.get("parent_run_id")
                    or meta.get("parent_id")
                    or meta.get("parent_run_id")
                )
                if parent_id:
                    parent_ids.append(parent_id)
                for parent in parent_ids:
                    if parent in run_id_to_node_id:
                        run_id_to_node_id[run_id] = run_id_to_node_id[parent]
                        break

        # Check for Nested Agents / Tools that should be Visualized as Nodes
        
        # 1. Start Research (Researcher Agent)
        if name == "start_research" and kind == "on_tool_start":
             # Create new Researcher node
             res_id = meta.get("node_id") or meta.get("researcher_id") or f"researcher-{run_id[:8]}"
             node_mapping[run_id] = res_id 
             pending_researcher_ids.append(res_id)
             run_id_to_node_id[run_id] = res_id
             
             await emit_event("NODE_CREATED", {"id": res_id, "kind": "researcher", "title": "Researcher"})
             # Connect from current node (usually Planner)
             await emit_event("EDGE_CREATED", {"source": current_node_id, "target": res_id})
             
             await emit_event("ACTIVE_NODE_SET", {"id": res_id})
             current_node_id = res_id # Switch context to this researcher

        # 2. Write Report (Writer Agent)
        if name == "write_report" and kind == "on_tool_start":
             writer_id = meta.get("node_id") or f"writer-{run_id[:8]}"
             # Create Writer Node
             await emit_event("NODE_CREATED", {"id": writer_id, "kind": "report_writer", "title": "Report Writer"})
             await emit_event("EDGE_CREATED", {"source": current_node_id, "target": writer_id})
             
             await emit_event("ACTIVE_NODE_SET", {"id": writer_id})
             current_node_id = writer_id
             run_id_to_node_id[run_id] = writer_id
             node_mapping["write_report"] = writer_id
        
        # 2. Handle Events
        
        # A. Chat Model Streaming (Text)
        if kind == "on_chat_model_stream":
            chunk = event["data"]["chunk"]
            # Only process if there is content (ignore tool call chunks for message text)
            if chunk.content:
                content = chunk.content
                event_node_id = run_id_to_node_id.get(run_id, current_node_id)
                # Check if we've seen this run_id before.
                # Since we don't keep checking a set for 'MESSAGE_UPDATED', checking 'processed_msg_ids' 
                # helps us decide if we Append (idx 0) or Update.
                # Actually, frontend reducer handles duplication safely now, but best valid logic is:
                # First time -> Append (empty or first chunk), Subsequent -> Update.
                
                # We'll use a local set to track initialized message IDs for this stream loop
                if run_id not in processed_msg_ids:
                    processed_msg_ids.add(run_id)
                    last_stream_emit[run_id] = time.monotonic()
                    await emit_event("MESSAGE_APPENDED", {
                        "id": run_id,
                        "nodeId": event_node_id,
                        "kind": "assistant",
                        "content": content,
                        "streaming": True,
                        "timestamp": 0
                    })
                else:
                    pending_stream_chunks[run_id] += content
                    now = time.monotonic()
                    if now - last_stream_emit.get(run_id, 0) >= STREAM_EMIT_INTERVAL:
                        pending_content = pending_stream_chunks[run_id]
                        if pending_content:
                            pending_stream_chunks[run_id] = ""
                            last_stream_emit[run_id] = now
                            await emit_event("MESSAGE_UPDATED", {
                                "id": run_id,
                                "content": pending_content,
                                "append": True
                            })

        elif kind == "on_chat_model_end":
            output = event["data"].get("output")
            output_text = ""
            if output is not None:
                if hasattr(output, "content"):
                    output_text = str(output.content)
                elif hasattr(output, "text"):
                    output_text = str(output.text)
                else:
                    output_text = str(output)

            pending_text = pending_stream_chunks.pop(run_id, "")
            last_stream_emit.pop(run_id, None)

            if output_text:
                await emit_event("MESSAGE_UPDATED", {
                    "id": run_id,
                    "content": output_text,
                    "append": False,
                    "streaming": False
                })
            elif pending_text:
                await emit_event("MESSAGE_UPDATED", {
                    "id": run_id,
                    "content": pending_text,
                    "append": True,
                    "streaming": False
                })
            else:
                await emit_event("MESSAGE_UPDATED", {
                    "id": run_id,
                    "streaming": False
                })

        # B. Tool Start
        elif kind == "on_tool_start":
            # Filter out internal LangChain tools or trivial ones if needed.
            # We want to show 'web_search', 'start_research', etc.
            # We skip 'start_deep_research' wrapper if we want, but actually it's fine to show it.
            tool_data = event["data"].get("input")
            event_node_id = run_id_to_node_id.get(run_id, current_node_id)
            
            processed_msg_ids.add(run_id)
            await emit_event("MESSAGE_APPENDED", {
                "id": run_id,
                "nodeId": event_node_id,
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
    logger.info("Research workflow completed")

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
    ga_id = get_latest_node_id("general_assistant") or "ga-1"
    
    await emit_event("MESSAGE_APPENDED", {
        "id": user_msg_id,
        "nodeId": ga_id,
        "kind": "human",
        "content": message,
        "timestamp": 0
    })

    logger.info("Continuing research with: {}", message)
    
    planner_seed_id = get_latest_node_id("planner")
    node_mapping = {"general_assistant": ga_id}
    if planner_seed_id:
         node_mapping["planner"] = planner_seed_id
    processed_msg_ids = {user_msg_id} 
    pending_stream_chunks: Dict[str, str] = defaultdict(str)
    last_stream_emit: Dict[str, float] = {}
    current_node_id = ga_id
    pending_researcher_ids: List[str] = []
    run_id_to_node_id: Dict[str, str] = {}
    
    inputs = {"general_assistant_messages": [HumanMessage(content=message)]}

    async for event in graph.astream_events(inputs, config=config, version="v2"):
        kind = event["event"]
        name = event["name"]
        run_id = event["run_id"]
        
        meta = event.get("metadata", {})
        lg_node = meta.get("langgraph_node")
        node_hint = (
            meta.get("node_id")
            or meta.get("agent_node_id")
            or meta.get("researcher_id")
        )
        if node_hint:
            run_id_to_node_id[run_id] = node_hint
        
        if lg_node == "planner":
             latest_planner_id = node_mapping.get("planner")
             
             if latest_planner_id:
                  is_text_stream = (kind == "on_chat_model_stream")
                  
                  if is_text_stream and (pending_researcher_ids or current_node_id != latest_planner_id):
                       new_planner_id = f"planner-{str(uuid.uuid4())[:4]}"
                       node_mapping["planner"] = new_planner_id
                       
                       await emit_event("NODE_CREATED", {"id": new_planner_id, "kind": "planner", "title": "Research Planner"})
                       
                       # If we just finished researcher nodes, fork the planner after them.
                       sources: List[str] = [latest_planner_id]
                       if pending_researcher_ids:
                            sources.extend(pending_researcher_ids)
                       else:
                            sources.append(current_node_id)
                       
                       seen_sources = set()
                       for source in sources:
                            if not source or source in seen_sources:
                                 continue
                            seen_sources.add(source)
                            await emit_event("EDGE_CREATED", {"source": source, "target": new_planner_id})
                       
                       pending_researcher_ids.clear()
                       
                       await emit_event("ACTIVE_NODE_SET", {"id": new_planner_id})
                       current_node_id = new_planner_id
                  else:
                       current_node_id = latest_planner_id
             
             else:
                  planner_id = "planner-1"
                  node_mapping["planner"] = planner_id
                  await emit_event("NODE_CREATED", {"id": planner_id, "kind": "planner", "title": "Research Planner"})
                  await emit_event("EDGE_CREATED", {"source": ga_id, "target": planner_id})
                  await emit_event("ACTIVE_NODE_SET", {"id": planner_id})
                  await emit_event("UI_MODE_SET", {"mode": "research"})
                  current_node_id = planner_id
        
        elif lg_node == "general_assistant":
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

        elif lg_node == "write_report":
             writer_node_id = node_mapping.get("write_report")
             if writer_node_id:
                  current_node_id = writer_node_id

        if run_id not in run_id_to_node_id:
             if lg_node and lg_node in node_mapping:
                  run_id_to_node_id[run_id] = node_mapping[lg_node]
             else:
                  parent_ids: List[str] = []
                  parent_list = (
                       event.get("parent_ids")
                       or event.get("parent_run_ids")
                       or meta.get("parent_ids")
                       or meta.get("parent_run_ids")
                  )
                  if isinstance(parent_list, (list, tuple)):
                       parent_ids.extend([pid for pid in parent_list if pid])
                  parent_id = (
                       event.get("parent_id")
                       or event.get("parent_run_id")
                       or meta.get("parent_id")
                       or meta.get("parent_run_id")
                  )
                  if parent_id:
                       parent_ids.append(parent_id)
                  for parent in parent_ids:
                       if parent in run_id_to_node_id:
                            run_id_to_node_id[run_id] = run_id_to_node_id[parent]
                            break

        if name == "start_research" and kind == "on_tool_start":
             res_id = meta.get("node_id") or meta.get("researcher_id") or f"researcher-{run_id[:8]}"
             node_mapping[run_id] = res_id
             pending_researcher_ids.append(res_id)
             run_id_to_node_id[run_id] = res_id
             
             await emit_event("NODE_CREATED", {"id": res_id, "kind": "researcher", "title": "Researcher"})
             await emit_event("EDGE_CREATED", {"source": current_node_id, "target": res_id})
             
             await emit_event("ACTIVE_NODE_SET", {"id": res_id})
             current_node_id = res_id

        if name == "write_report" and kind == "on_tool_start":
             writer_id = meta.get("node_id") or f"writer-{run_id[:8]}"
             await emit_event("NODE_CREATED", {"id": writer_id, "kind": "report_writer", "title": "Report Writer"})
             await emit_event("EDGE_CREATED", {"source": current_node_id, "target": writer_id})
             
             await emit_event("ACTIVE_NODE_SET", {"id": writer_id})
             current_node_id = writer_id
             run_id_to_node_id[run_id] = writer_id
             node_mapping["write_report"] = writer_id

        # A. Chat Model Streaming (Text)
        if kind == "on_chat_model_stream":
            chunk = event["data"]["chunk"]
            if chunk.content:
                content = chunk.content
                event_node_id = run_id_to_node_id.get(run_id, current_node_id)
                if run_id not in processed_msg_ids:
                    processed_msg_ids.add(run_id)
                    last_stream_emit[run_id] = time.monotonic()
                    await emit_event("MESSAGE_APPENDED", {
                        "id": run_id,
                        "nodeId": event_node_id,
                        "kind": "assistant",
                        "content": content,
                        "streaming": True,
                        "timestamp": 0
                    })
                else:
                    pending_stream_chunks[run_id] += content
                    now = time.monotonic()
                    if now - last_stream_emit.get(run_id, 0) >= STREAM_EMIT_INTERVAL:
                        pending_content = pending_stream_chunks[run_id]
                        if pending_content:
                            pending_stream_chunks[run_id] = ""
                            last_stream_emit[run_id] = now
                            await emit_event("MESSAGE_UPDATED", {
                                "id": run_id,
                                "content": pending_content,
                                "append": True
                            })

        elif kind == "on_chat_model_end":
            output = event["data"].get("output")
            output_text = ""
            if output is not None:
                if hasattr(output, "content"):
                    output_text = str(output.content)
                elif hasattr(output, "text"):
                    output_text = str(output.text)
                else:
                    output_text = str(output)

            pending_text = pending_stream_chunks.pop(run_id, "")
            last_stream_emit.pop(run_id, None)

            if output_text:
                await emit_event("MESSAGE_UPDATED", {
                    "id": run_id,
                    "content": output_text,
                    "append": False,
                    "streaming": False
                })
            elif pending_text:
                await emit_event("MESSAGE_UPDATED", {
                    "id": run_id,
                    "content": pending_text,
                    "append": True,
                    "streaming": False
                })
            else:
                await emit_event("MESSAGE_UPDATED", {
                    "id": run_id,
                    "streaming": False
                })

        # B. Tool Start
        elif kind == "on_tool_start":
            tool_data = event["data"].get("input")
            event_node_id = run_id_to_node_id.get(run_id, current_node_id)
            processed_msg_ids.add(run_id)
            await emit_event("MESSAGE_APPENDED", {
                "id": run_id,
                "nodeId": event_node_id,
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
