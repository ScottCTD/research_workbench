import asyncio
import random
import string
import uuid
from typing import Any, AsyncGenerator, Dict


class MockGraph:
    """
    Simulates a LangGraph compiled graph for Deep Research using the V2 astream_events API.
    Provides a complex, multi-step research scenario.
    """

    def __init__(self):
        pass

    async def astream_events(
        self, inputs: Dict[str, Any], config: Dict[str, Any], version: str = "v2"
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Simulates the streaming of granular graph events (V2 API).
        """
        run_id_map = {}

        def get_run_id(key: str) -> str:
            if key not in run_id_map:
                run_id_map[key] = str(uuid.uuid4())
            return run_id_map[key]

        def make_garbage(
            seed: int, words: int, min_len: int = 3, max_len: int = 10
        ) -> str:
            rng = random.Random(seed)
            alphabet = string.ascii_lowercase
            tokens = []
            for i in range(words):
                token_len = rng.randint(min_len, max_len)
                token = "".join(rng.choice(alphabet) for _ in range(token_len))
                if i % 29 == 0:
                    token += str(rng.randint(0, 999))
                if i % 37 == 0:
                    token += rng.choice([".", ",", ";", ":"])
                tokens.append(token)
            return " ".join(tokens)

        async def yield_text(
            content: str,
            run_id: str,
            name: str,
            node: str,
            node_id: str | None = None,
            token_delay: float = 0.02,
        ):
            # Split text effectively to simulate token streaming
            tokens = content.split(" ")

            # Construct chunk object structure similar to LangChain's AIMessageChunk
            class MockChunk:
                def __init__(self, txt):
                    self.content = txt

            class MockOutput:
                def __init__(self, txt):
                    self.content = txt

            for i, token in enumerate(tokens):
                # Add space if not last
                chunk_text = token + (" " if i < len(tokens) - 1 else "")
                metadata = {"langgraph_node": node}
                if node_id:
                    metadata["node_id"] = node_id
                yield {
                    "event": "on_chat_model_stream",
                    "name": name,
                    "run_id": run_id,
                    "metadata": metadata,
                    "data": {"chunk": MockChunk(chunk_text)},
                }
                await asyncio.sleep(token_delay)  # fast typing

            end_metadata = {"langgraph_node": node}
            if node_id:
                end_metadata["node_id"] = node_id
            yield {
                "event": "on_chat_model_end",
                "name": name,
                "run_id": run_id,
                "metadata": end_metadata,
                "data": {"output": MockOutput(content)},
            }

        async def yield_tool_start(
            name: str, args: Dict, run_id: str, node: str, node_id: str | None = None
        ):
            metadata = {"langgraph_node": node}
            if node_id:
                metadata["node_id"] = node_id
            yield {
                "event": "on_tool_start",
                "name": name,
                "run_id": run_id,
                "metadata": metadata,
                "data": {"input": args},
            }
            await asyncio.sleep(0.5)

        async def yield_tool_end(
            name: str, output: Any, run_id: str, node: str, node_id: str | None = None
        ):
            metadata = {"langgraph_node": node}
            if node_id:
                metadata["node_id"] = node_id
            yield {
                "event": "on_tool_end",
                "name": name,
                "run_id": run_id,
                "metadata": metadata,
                "data": {"output": output},
            }
            await asyncio.sleep(0.5)

        async def merge_streams(streams):
            queue: asyncio.Queue = asyncio.Queue()
            done = 0

            async def pump(stream):
                async for item in stream:
                    await queue.put(item)
                await queue.put(None)

            tasks = [asyncio.create_task(pump(stream)) for stream in streams]
            try:
                while done < len(tasks):
                    item = await queue.get()
                    if item is None:
                        done += 1
                        continue
                    yield item
            finally:
                for task in tasks:
                    if not task.done():
                        task.cancel()

        async def researcher_flow(
            proposal: str,
            thought: str,
            analysis: str,
            summary: str,
            res_tool_id: str,
            res_run_id: str,
            res_analysis_run_id: str,
            ws_id: str,
            ws_query: str,
            ws_result: str,
            res_node_id: str,
            we_id: str | None = None,
            we_url: str | None = None,
            we_result: str | None = None,
            thought_delay: float = 0.01,
        ):
            async for e in yield_tool_start(
                "start_research",
                {"proposal": proposal},
                res_tool_id,
                "planner",
                node_id=res_node_id,
            ):
                yield e

            async for e in yield_text(
                thought,
                res_run_id,
                "Grok",
                "researcher",
                node_id=res_node_id,
                token_delay=thought_delay,
            ):
                yield e

            async for e in yield_tool_start(
                "web_search",
                {"query": ws_query},
                ws_id,
                "researcher",
                node_id=res_node_id,
            ):
                yield e
            async for e in yield_tool_end(
                "web_search", ws_result, ws_id, "researcher", node_id=res_node_id
            ):
                yield e

            async for e in yield_text(
                analysis,
                res_analysis_run_id,
                "Grok",
                "researcher",
                node_id=res_node_id,
                token_delay=thought_delay,
            ):
                yield e

            if we_id and we_url and we_result is not None:
                async for e in yield_tool_start(
                    "web_extract",
                    {"url": we_url},
                    we_id,
                    "researcher",
                    node_id=res_node_id,
                ):
                    yield e
                async for e in yield_tool_end(
                    "web_extract", we_result, we_id, "researcher", node_id=res_node_id
                ):
                    yield e

            async for e in yield_tool_end(
                "start_research", summary, res_tool_id, "planner", node_id=res_node_id
            ):
                yield e

        # === SCENARIO START ===

        # 1. General Assistant (GA)
        # -------------------------
        ga_run_id = get_run_id("ga_turn_1")
        ga_garbage = make_garbage(101, 650)
        async for e in yield_text(
            (
                "I'll start a deep research process on Liquid Neural Networks to uncover their "
                "architecture, dynamics, and real-world use cases. Stress payload follows. "
                f"{ga_garbage}"
            ),
            ga_run_id,
            "Grok",
            "general_assistant",
            token_delay=0.002,
        ):
            yield e

        # GA calls start_deep_research
        dr_tool_id = get_run_id("start_deep_research")
        async for e in yield_tool_start(
            "start_deep_research",
            {"query": "Liquid Neural Networks"},
            dr_tool_id,
            "general_assistant",
        ):
            yield e

        # 2. Planner
        # ----------
        # Planner receives the ball
        planner_run_id = get_run_id("planner_msg_1")
        planner_garbage = make_garbage(202, 500)
        async for e in yield_text(
            (
                "I am generating a research plan. I will investigate core architecture, "
                "continuous-time dynamics, control theory alignment, and multi-domain applications. "
                f"{planner_garbage}"
            ),
            planner_run_id,
            "Grok",
            "planner",
            token_delay=0.002,
        ):
            yield e

        # 3. Researchers in parallel
        # ---------------------------
        researcher_specs = [
            {
                "key": "res_arch",
                "proposal": "Investigate LNN Architecture (LTCs)",
                "ws_query": "Liquid Time-constant Networks architecture equations",
                "ws_intro": "Collected math notes and system dynamics references.",
                "we_url": "https://arxiv.org/abs/2006.04439",
                "we_intro": "Paper excerpt payload:",
            },
            {
                "key": "res_control",
                "proposal": "Investigate stability/control theory alignment",
                "ws_query": "continuous-time RNN stability proofs",
                "ws_intro": "Control-theory alignment notes and proofs.",
                "we_url": "https://arxiv.org/abs/2006.04439",
                "we_intro": "Supplementary stability excerpt:",
            },
            {
                "key": "res_robotics",
                "proposal": "Investigate robotics and autonomous navigation use cases",
                "ws_query": "Liquid Neural Networks drone navigation results",
                "ws_intro": "Robotics case studies and benchmarks summary.",
            },
            {
                "key": "res_efficiency",
                "proposal": "Investigate parameter efficiency vs. LSTM/GRU",
                "ws_query": "LNN parameter efficiency comparison LSTM GRU",
                "ws_intro": "Parameter count and compute comparisons.",
            },
            {
                "key": "res_benchmarks",
                "proposal": "Investigate benchmark performance and data regimes",
                "ws_query": "LNN benchmarks time series datasets",
                "ws_intro": "Benchmark suite summaries and dataset notes.",
                "we_url": "https://arxiv.org/abs/2006.04439",
                "we_intro": "Benchmark excerpt payload:",
            },
            {
                "key": "res_edge",
                "proposal": "Investigate edge deployment and latency constraints",
                "ws_query": "LNN edge deployment latency hardware",
                "ws_intro": "Edge runtime and latency observations.",
            },
        ]

        researcher_streams = []
        for idx, spec in enumerate(researcher_specs, start=1):
            res_tool_id = get_run_id(f"{spec['key']}_call")
            res_run_id = get_run_id(f"{spec['key']}_thought")
            res_analysis_run_id = get_run_id(f"{spec['key']}_analysis")
            ws_id = get_run_id(f"{spec['key']}_web_search")
            we_id = (
                get_run_id(f"{spec['key']}_web_extract") if spec.get("we_url") else None
            )
            res_node_id = f"researcher-{res_tool_id[:8]}"

            thought = f"{spec['proposal']} kickoff. {make_garbage(1000 + idx, 700)}"
            analysis = f"Interim synthesis. {make_garbage(2000 + idx, 650)}"
            summary = f"{spec['proposal']} summary. {make_garbage(3000 + idx, 550)}"
            ws_query = f"{spec['ws_query']} {make_garbage(4000 + idx, 45)}"
            ws_result = f"{spec['ws_intro']} {make_garbage(5000 + idx, 320)}"
            we_result = None
            if we_id and spec.get("we_url"):
                we_result = f"{spec['we_intro']} {make_garbage(6000 + idx, 300)}"

            researcher_streams.append(
                researcher_flow(
                    proposal=spec["proposal"],
                    thought=thought,
                    analysis=analysis,
                    summary=summary,
                    res_tool_id=res_tool_id,
                    res_run_id=res_run_id,
                    res_analysis_run_id=res_analysis_run_id,
                    ws_id=ws_id,
                    ws_query=ws_query,
                    ws_result=ws_result,
                    res_node_id=res_node_id,
                    we_id=we_id,
                    we_url=spec.get("we_url"),
                    we_result=we_result,
                    thought_delay=0.002,
                )
            )

        async for e in merge_streams(researcher_streams):
            yield e

        # 5. Planner Synthesis & Report
        # -----------------------------
        planner_final_run_id = get_run_id("planner_final")
        planner_final_garbage = make_garbage(303, 500)
        async for e in yield_text(
            (
                "I have gathered sufficient information across architecture, control theory, "
                "benchmarks, and applications. Writing report now. "
                f"{planner_final_garbage}"
            ),
            planner_final_run_id,
            "Grok",
            "planner",
            token_delay=0.002,
        ):
            yield e

        wr_tool_id = get_run_id("write_report")
        async for e in yield_tool_start("write_report", {}, wr_tool_id, "planner"):
            yield e
        async for e in yield_tool_end(
            "write_report", "Report generated.", wr_tool_id, "planner"
        ):
            yield e

        # 6. Final Loop Closure (GA)
        # --------------------------
        # The GA's tool call (start_deep_research) finishes now
        report_garbage = make_garbage(404, 900)
        report_content = (
            "# Liquid Neural Networks (LNNs)\n\n"
            "## Executive Summary\n"
            "LNNs represent a significant shift in continuous-time deep learning.\n\n"
            "## Key Findings\n"
            "1. **Architecture**: Built on Liquid Time-constant (LTC) differential equations.\n"
            "2. **Applications**: Proven highly effective in drone navigation and autonomous driving.\n"
            "3. **Efficiency**: requires significantly fewer neurons than comparable LSTMs.\n\n"
            "## Raw Payload\n"
            f"{report_garbage}"
        )

        async for e in yield_tool_end(
            "start_deep_research", report_content, dr_tool_id, "general_assistant"
        ):
            yield e

        # GA Final Comment
        ga_final_run_id = get_run_id("ga_final")
        ga_final_garbage = make_garbage(505, 500)
        async for e in yield_text(
            f"Here is the report on Liquid Neural Networks. {ga_final_garbage}",
            ga_final_run_id,
            "Grok",
            "general_assistant",
            token_delay=0.002,
        ):
            yield e
