import asyncio
import uuid
import json
from typing import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_core.messages import HumanMessage

from frontend.api.dependencies import get_research_graph

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure graph is loaded on startup
    get_research_graph()
    yield

app = FastAPI(lifespan=lifespan)

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development convenience
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ResearchRequest(BaseModel):
    query: str

class ResearchResponse(BaseModel):
    run_id: str
    message: str

@app.post("/research/start", response_model=ResearchResponse)
async def start_research(request: ResearchRequest):
    """Start a new research session."""
    run_id = str(uuid.uuid4())
    # We don't actually start the graph here, we just generate the ID.
    # The graph execution will happen in the stream endpoint or triggered here.
    # Actually, standard pattern is to stream immediately or have a background task.
    # For this dashboard, simple pattern: client calls start -> gets ID -> connects to stream.
    # But enabling the stream to drive the execution requires the stream to call invoke/stream.
    
    # Better approach:
    # 1. Start: returns ID.
    # 2. Stream: Takes ID and query (or just ID if state saved, but here we are starting fresh).
    # TO KEEP IT SIMPLE: The client will connect to SSE with the query, OR
    # The client calls START, we kick off a background task? No, we want to stream the output.
    
    # Let's do: Start endpoint creates the thread ID.
    # Stream endpoint takes thread ID and input, and runs `astream_events`.
    
    return ResearchResponse(run_id=run_id, message="Research session initialized. Connect to stream to start.")

@app.get("/research/{run_id}/stream")
async def stream_research(run_id: str, query: str, graph=Depends(get_research_graph)):
    """
    Stream events from the research graph.
    This triggers the actual execution using the provided query and run_id as thread_id.
    """
    
    async def event_generator() -> AsyncGenerator[str, None]:
        config = {"configurable": {"thread_id": run_id}, "recursion_limit": 100}
        
        # Initial input to kick off the graph
        inputs = {"general_assistant_messages": [HumanMessage(content=query)]}
        
        try:
            async for event in graph.astream_events(inputs, config=config, version="v2"):
                # Filter out some noise if needed, or send everything.
                # Sending everything is safer for the visualization tool to filter.
                
                # We need to handle non-serializable objects.
                # astream_events yields dicts with some complex objects (Messages, Documents etc.)
                # We'll rely on a basic json dumper for now, may need custom encoder.
                
                try:
                    def custom_encoder(obj):
                        if hasattr(obj, "dict") and callable(obj.dict):
                            return obj.dict()
                        if hasattr(obj, "to_json") and callable(obj.to_json):
                            return obj.to_json()
                        return str(obj)

                    data = json.dumps(event, default=custom_encoder)
                    yield f"data: {data}\n\n"
                except Exception as e:
                    error_msg = json.dumps({"type": "error", "message": f"Serialization Error: {str(e)}"})
                    yield f"data: {error_msg}\n\n"
                    
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
