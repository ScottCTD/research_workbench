
import asyncio
import uuid
import time
from typing import Any, Dict, AsyncGenerator

class MockGraph:
    """
    Simulates a LangGraph compiled graph for Deep Research using the V2 astream_events API.
    Provides a complex, multi-step research scenario.
    """
    def __init__(self):
        pass

    async def astream_events(self, inputs: Dict[str, Any], config: Dict[str, Any], version: str = "v2") -> AsyncGenerator[Dict[str, Any], None]:
        """
        Simulates the streaming of granular graph events (V2 API).
        """
        run_id_map = {}
        
        def get_run_id(key: str) -> str:
            if key not in run_id_map:
                run_id_map[key] = str(uuid.uuid4())
            return run_id_map[key]

        async def yield_text(content: str, run_id: str, name: str, node: str):
            # Split text effectively to simulate token streaming
            tokens = content.split(" ")
            
            # Construct chunk object structure similar to LangChain's AIMessageChunk
            class MockChunk:
                def __init__(self, txt):
                    self.content = txt
            
            for i, token in enumerate(tokens):
                # Add space if not last
                chunk_text = token + (" " if i < len(tokens) - 1 else "")
                
                yield {
                    "event": "on_chat_model_stream",
                    "name": name,
                    "run_id": run_id,
                    "metadata": {"langgraph_node": node},
                    "data": {"chunk": MockChunk(chunk_text)}
                }
                await asyncio.sleep(0.05) # fast typing

        async def yield_tool_start(name: str, args: Dict, run_id: str, node: str):
            yield {
                "event": "on_tool_start",
                "name": name,
                "run_id": run_id,
                "metadata": {"langgraph_node": node},
                "data": {"input": args}
            }
            await asyncio.sleep(0.5)

        async def yield_tool_end(name: str, output: Any, run_id: str, node: str):
            yield {
                "event": "on_tool_end",
                "name": name,
                "run_id": run_id,
                "metadata": {"langgraph_node": node},
                "data": {"output": output}
            }
            await asyncio.sleep(0.5)

        # === SCENARIO START ===
        
        # 1. General Assistant (GA)
        # -------------------------
        ga_run_id = get_run_id("ga_turn_1")
        async for e in yield_text(
            "I'll start a deep research process on Liquid Neural Networks to uncover their architecture and use cases.",
            ga_run_id, "Grok", "general_assistant"
        ): yield e
        
        # GA calls start_deep_research
        dr_tool_id = get_run_id("start_deep_research")
        async for e in yield_tool_start("start_deep_research", {"query": "Liquid Neural Networks"}, dr_tool_id, "general_assistant"): yield e
        
        # 2. Planner
        # ----------
        # Planner receives the ball
        planner_run_id = get_run_id("planner_msg_1")
        async for e in yield_text(
            "I am generating a research plan. I will investigate the core architecture of LNNs and then look into their robotic control applications.",
            planner_run_id, "Grok", "planner"
        ): yield e

        # 3. Researcher 1: Architecture
        # -----------------------------
        # Planner calls start_research (Nested Agent)
        res1_tool_id = get_run_id("res1_call")
        async for e in yield_tool_start("start_research", {"proposal": "Investigate LNN Architecture (LTCs)"}, res1_tool_id, "planner"): yield e

        # Start streaming events *as* the nested agent (which runs under planner's scope usually)
        # We simulate the inner workings:
        res1_run_id = get_run_id("res1_inner_thought")
        async for e in yield_text(
            "Searching for Liquid Time-constant Networks papers and documentation...",
            res1_run_id, "Grok", "researcher" 
        ): yield e
        
        # Inner Tool: Web Search
        ws1_id = get_run_id("web_search_1")
        async for e in yield_tool_start("web_search", {"query": "Liquid Time-constant Networks architecture"}, ws1_id, "researcher"): yield e
        async for e in yield_tool_end("web_search", 
            "Found papers by Ramin Hasani/MIT CSAIL. Key concept: equations that adapt to time-series ticks.", 
            ws1_id, "researcher"
        ): yield e
        
        # Inner Tool: Web Extract
        we1_id = get_run_id("web_extract_1")
        async for e in yield_tool_start("web_extract", {"url": "https://arxiv.org/abs/2006.04439"}, we1_id, "researcher"): yield e
        async for e in yield_tool_end("web_extract", "Abstract: LTCs exhibit stable behavior and superior expressivity...", we1_id, "researcher"): yield e
        
        # Researcher 1 Conclusion
        async for e in yield_tool_end("start_research", 
            "Liquid Neural Networks (LNNs) are based on Liquid Time-constant (LTC) layers. They are causal, continuous-time RNNs.", 
            res1_tool_id, "planner"
        ): yield e

        # 4. Researcher 2: Applications
        # -----------------------------
        res2_tool_id = get_run_id("res2_call")
        async for e in yield_tool_start("start_research", {"proposal": "Investigate LNN Applications in Robotics"}, res2_tool_id, "planner"): yield e
        
        res2_run_id = get_run_id("res2_inner_thought")
        async for e in yield_text(
            "Looking for autonomous driving and drone flight tests...",
            res2_run_id, "Grok", "researcher"
        ): yield e
        
        ws2_id = get_run_id("web_search_2")
        async for e in yield_tool_start("web_search", {"query": "Liquid Neural Networks drone navigation"}, ws2_id, "researcher"): yield e
        async for e in yield_tool_end("web_search", "Results: LNNs successfully piloted drones in unknown environments with high robustness.", ws2_id, "researcher"): yield e
        
        async for e in yield_tool_end("start_research", 
            "LNNs excel in robotics and autonomous driving due to their robustness to distributional shifts.", 
            res2_tool_id, "planner"
        ): yield e

        # 5. Planner Synthesis & Report
        # -----------------------------
        planner_final_run_id = get_run_id("planner_final")
        async for e in yield_text(
            "I have gathered sufficient information on architecture and specific applications. Writing report now.",
            planner_final_run_id, "Grok", "planner"
        ): yield e
        
        wr_tool_id = get_run_id("write_report")
        async for e in yield_tool_start("write_report", {}, wr_tool_id, "planner"): yield e
        async for e in yield_tool_end("write_report", "Report generated.", wr_tool_id, "planner"): yield e

        # 6. Final Loop Closure (GA)
        # --------------------------
        # The GA's tool call (start_deep_research) finishes now
        report_content = (
            "# Liquid Neural Networks (LNNs)\n\n"
            "## Executive Summary\n"
            "LNNs represent a significant shift in continuous-time deep learning.\n\n"
            "## Key Findings\n"
            "1. **Architecture**: Built on Liquid Time-constant (LTC) differential equations.\n"
            "2. **Applications**: Proven highly effective in drone navigation and autonomous driving.\n"
            "3. **Efficiency**: requires significantly fewer neurons than comparable LSTMs."
        )
        
        async for e in yield_tool_end("start_deep_research", report_content, dr_tool_id, "general_assistant"): yield e
        
        # GA Final Comment
        ga_final_run_id = get_run_id("ga_final")
        async for e in yield_text(
            "Here is the report on Liquid Neural Networks.",
            ga_final_run_id, "Grok", "general_assistant"
        ): yield e
