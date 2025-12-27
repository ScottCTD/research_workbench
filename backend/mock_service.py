
import asyncio
import uuid
from typing import Any, Dict
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

class MockGraph:
    """
    Simulates a LangGraph compiled graph for Deep Research.
    Generates a fixed sequence of events to test the UI.
    """
    def __init__(self):
        pass

    async def astream(self, inputs: Dict[str, Any], config: Dict[str, Any], stream_mode: str = "updates"):
        """
        Simulates the streaming of graph events.
        """
        topic = "Unknown Topic"
        if "general_assistant_messages" in inputs:
            last_msg = inputs["general_assistant_messages"][-1]
            if isinstance(last_msg, HumanMessage):
                topic = last_msg.content

        # 1. General Assistant acknowledgment and deep research tool call
        yield {
            "general_assistant": {
                "general_assistant_messages": [
                    AIMessage(
                        content=(
                            "I will start a deep research workflow. I'll outline a plan, "
                            "run searches, and synthesize a report."
                        )
                    )
                ]
            }
        }
        await asyncio.sleep(1.2)

        deep_research_call_id = str(uuid.uuid4())
        yield {
            "general_assistant": {
                "general_assistant_messages": [
                    AIMessage(
                        content="",
                        tool_calls=[{
                            "name": "start_deep_research",
                            "args": {"query": topic},
                            "id": deep_research_call_id
                        }]
                    )
                ]
            }
        }
        await asyncio.sleep(0.8)

        # 2. Planner Node - plan and initial tool calls
        yield {
            "planner": {
                "planner_messages": [
                    AIMessage(
                        content=(
                            "**Research Plan**\n"
                            "1. Identify key sources and benchmarks.\n"
                            "2. Extract primary facts and constraints.\n"
                            "3. Synthesize findings into a structured report."
                        )
                    )
                ]
            }
        }
        await asyncio.sleep(1.5)

        # 3. Planner executes web_search
        search_call_id = str(uuid.uuid4())
        yield {
            "planner": {
                "planner_messages": [
                    AIMessage(
                        content="Running initial searches for sources and benchmarks.",
                        tool_calls=[{
                            "name": "web_search",
                            "args": {"query": f"{topic} benchmarks and evaluations"},
                            "id": search_call_id
                        }]
                    )
                ]
            }
        }
        await asyncio.sleep(1.2)

        yield {
            "planner": {
                "planner_messages": [
                    ToolMessage(
                        content=(
                            "[Mock Search Results]\n"
                            "- Benchmark A summary\n"
                            "- Benchmark B summary\n"
                            "- Industry whitepaper overview"
                        ),
                        tool_call_id=search_call_id,
                        name="web_search"
                    )
                ]
            }
        }
        await asyncio.sleep(1.0)

        # 4. Planner executes web_extract for a key source
        extract_call_id = str(uuid.uuid4())
        yield {
            "planner": {
                "planner_messages": [
                    AIMessage(
                        content="Extracting details from a primary source.",
                        tool_calls=[{
                            "name": "web_extract",
                            "args": {"url": "https://example.com/deep-research-source"},
                            "id": extract_call_id
                        }]
                    )
                ]
            }
        }
        await asyncio.sleep(1.2)

        yield {
            "planner": {
                "planner_messages": [
                    ToolMessage(
                        content=(
                            "[Mock Extract]\n"
                            "Key metrics, constraints, and comparative notes extracted."
                        ),
                        tool_call_id=extract_call_id,
                        name="web_extract"
                    )
                ]
            }
        }
        await asyncio.sleep(1.0)

        # 5. Planner runs start_research synthesis
        research_call_id = str(uuid.uuid4())
        yield {
            "planner": {
                "planner_messages": [
                    AIMessage(
                        content="Delegating synthesis to research agent.",
                        tool_calls=[{
                            "name": "start_research",
                            "args": {
                                "research_proposal": (
                                    f"Summarize findings about {topic} with comparisons and risks."
                                )
                            },
                            "id": research_call_id
                        }]
                    )
                ]
            }
        }
        await asyncio.sleep(1.6)

        yield {
            "planner": {
                "planner_messages": [
                    ToolMessage(
                        content=(
                            "Synthesis complete:\n"
                            "- Strengths and weaknesses identified\n"
                            "- Benchmarks highlight tradeoffs\n"
                            "- Key risks summarized"
                        ),
                        tool_call_id=research_call_id,
                        name="start_research"
                    )
                ]
            }
        }
        await asyncio.sleep(1.1)

        # 6. Planner routes to report writer
        write_report_call_id = str(uuid.uuid4())
        yield {
            "planner": {
                "planner_messages": [
                    AIMessage(
                        content="Preparing final report.",
                        tool_calls=[{
                            "name": "write_report",
                            "args": {"additional_instructions": "Keep the report concise and structured."},
                            "id": write_report_call_id
                        }]
                    )
                ]
            }
        }
        await asyncio.sleep(1.0)

        # 7. Report writer returns final tool result back to GA tool call
        yield {
            "general_assistant": {
                "general_assistant_messages": [
                    ToolMessage(
                        content=(
                            f"# Research Report: {topic}\n\n"
                            "## Executive Summary\n"
                            "- Scope: comparative assessment\n"
                            "- Outcome: tradeoffs identified across benchmarks\n\n"
                            "## Key Findings\n"
                            "- Finding 1: Performance differs by workload profile\n"
                            "- Finding 2: Reliability hinges on data freshness\n"
                            "- Finding 3: Cost scaling is the primary constraint\n\n"
                            "## Risks\n"
                            "- Coverage gaps in available benchmarks\n"
                            "- Potential bias in reported metrics\n\n"
                            "## Recommendations\n"
                            "- Validate with a targeted pilot\n"
                            "- Track metrics continuously during rollout"
                        ),
                        tool_call_id=deep_research_call_id,
                        name="start_deep_research"
                    )
                ]
            }
        }
