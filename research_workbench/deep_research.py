import asyncio
import json
from datetime import datetime
from typing import Annotated, List, Literal, Optional, TypedDict

import prompts
from config import Configuration
from langchain.agents import create_agent
from langchain.chat_models import BaseChatModel, init_chat_model
from langchain.tools import BaseTool, tool
from langchain_core.messages import AnyMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langchain_tavily.tavily_search import TavilySearch
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph, add_messages
from langgraph.types import Command
from loguru import logger
from tools.web_search import get_search_tool
from tools.web_extract import web_extract

_MODEL: Optional[BaseChatModel] = None


def get_model() -> BaseChatModel:
    """Lazily initialize the chat model to avoid import-time failures."""
    global _MODEL
    if _MODEL is None:
        _MODEL = init_chat_model(model="xai:grok-4-1-fast-non-reasoning")
    return _MODEL


class AgentState(TypedDict, total=False):
    # Main conversation history (user + assistant + tools)
    general_assistant_messages: Annotated[List[AnyMessage], add_messages]

    # Internal planner/research trajectory
    planner_messages: Annotated[List[AnyMessage], add_messages]

    deep_research_query: str
    deep_research_tool_call_id: str
    report_writing_instructions: Optional[str]
    final_report: str


def get_formatted_date():
    return datetime.now().strftime("%Y-%m-%d")


@tool
def start_deep_research(query: str):
    """
    Start a deep research on the query.
    Args:
        query: The query to start the research on.
    Returns:
        The research report.
    """
    logger.debug(f"start_deep_research: {query = }")
    return Command(
        update={"deep_research_query": query},
        goto="planner",
    )


@tool
async def start_research(research_proposal: str, config: RunnableConfig) -> str:
    """
    Start a research on the research proposal.
    Args:
        research_proposal: The research proposal to start the research on.
    Returns:
        Synthesized research findings.
    """
    react_agent = create_agent(
        model=get_model(),
        tools=[get_tool("web_search", config), get_tool("web_extract", config)],
        system_prompt=prompts.RESEARCHER_SYSTEM_PROMPT.format(
            date=get_formatted_date()
        ),
    )
    output_state = await react_agent.ainvoke(
        {"messages": [HumanMessage(content=research_proposal)]},
        config=config,
    )
    response = output_state["messages"][-1]
    logger.debug(f"start_research: {response.content = }")
    return response.content


@tool
async def write_report(additional_instructions: Optional[str] = None):
    """
    Write the final report based on the research trajectory and the additional instructions.
    Args:
        additional_instructions: Additional instructions for the report writer.
    Returns:
        None
    """
    return Command(
        update={"report_writing_instructions": additional_instructions},
        goto="write_report",
    )


def get_tool(name: str, config: RunnableConfig) -> BaseTool:
    if name == "web_search":
        return get_search_tool(Configuration.from_runnable_config(config))
    elif name == "start_deep_research":
        return start_deep_research
    elif name == "start_research":
        return start_research
    elif name == "write_report":
        return write_report
    elif name == "web_extract":
        return web_extract
    else:
        raise ValueError(f"Invalid tool name: {name}")


async def node_general_assistant(state: AgentState, config: RunnableConfig):
    system_prompt = prompts.GENERAL_ASSISTANT_SYSTEM_PROMPT.format(
        date=get_formatted_date()
    )
    messages = [
        SystemMessage(content=system_prompt),
        *state.get("general_assistant_messages", []),
    ]

    general_assistant_model = get_model().bind_tools(
        [get_tool("web_search", config), get_tool("web_extract", config), get_tool("start_deep_research", config)]
    )

    response = await general_assistant_model.ainvoke(messages)

    tool_calls = response.tool_calls

    if tool_calls:
        names = set(tool_call["name"] for tool_call in tool_calls)
        if "web_search" in names and len(names) > 1:
            logger.warning(
                "general_assistant: web_search is not the only tool call! Keeping web_search tools only ..."
            )
            tool_calls = [
                tool_call
                for tool_call in tool_calls
                if tool_call["name"] == "web_search"
            ]
            response.tool_calls = tool_calls
            names = {"web_search"}

        if "start_deep_research" in names:
            tool_call = tool_calls[0]
            if len(tool_calls) > 1:
                logger.warning(
                    "general_assistant: start_deep_research is not the only tool call! Executing the first start_deep_research ..."
                )
                for t in tool_calls:
                    if t["name"] == "start_deep_research":
                        tool_call = t
                        break
                response.tool_calls = [tool_call]

            command = await get_tool(tool_call["name"], config).ainvoke(
                tool_call["args"]
            )
            return Command(
                update={
                    "general_assistant_messages": [response],
                    "deep_research_tool_call_id": tool_call["id"],
                    **command.update,
                },
                goto=command.goto,
            )
        else:  # general tool calls like web_search
            results = await asyncio.gather(
                *[
                    get_tool(tool_call["name"], config).ainvoke(
                        tool_call["args"], config=config
                    )
                    for tool_call in tool_calls
                ]
            )
            result_msgs = [
                ToolMessage(
                    content=result, tool_call_id=tool_call["id"], name=tool_call["name"]
                )
                for result, tool_call in zip(results, tool_calls)
            ]

            return Command(
                update={"general_assistant_messages": [response, *result_msgs]},
                goto="general_assistant",
            )

    else:  # no tool calls, clarification/direct answer
        # plain response, end this invocation with the response
        return Command(
            update={"general_assistant_messages": [response]},
            goto=END,
        )


async def node_planner(state: AgentState, config: RunnableConfig):
    system_prompt = prompts.PLANNER_SYSTEM_PROMPT.format(date=get_formatted_date())
    existing_history = state.get("planner_messages", [])
    seed_messages: List[AnyMessage] = []
    if not existing_history:
        seed_messages = [
            HumanMessage(
                content=f"<user_query>\n{state.get('deep_research_query','')}\n</user_query>\n"
            )
        ]
    planner_history = [*existing_history, *seed_messages]
    messages = [
        SystemMessage(content=system_prompt),
        *planner_history,
    ]

    planner_model = get_model().bind_tools(
        [
            get_tool("web_search", config),
            get_tool("web_extract", config),
            get_tool("start_research", config),
            get_tool("write_report", config),
        ]
    )
    response = await planner_model.ainvoke(messages)

    tool_calls = response.tool_calls
    if tool_calls:
        logger.debug(f"planner: tool calls: {json.dumps(tool_calls, indent=2)}")
        # write_report is a routing tool (returns Command), so handle it explicitly.
        if any(tc["name"] == "write_report" for tc in tool_calls):
            tool_call = next(tc for tc in tool_calls if tc["name"] == "write_report")
            if len(tool_calls) > 1:
                logger.warning(
                    "planner: write_report is not the only tool call! Executing write_report only ..."
                )
                response.tool_calls = [tool_call]

            command = await get_tool(tool_call["name"], config).ainvoke(
                tool_call["args"], config=config
            )
            return Command(
                update={
                    "planner_messages": [*seed_messages, response],
                    **command.update,
                },
                goto=command.goto,
            )

        results = await asyncio.gather(
            *[
                get_tool(tool_call["name"], config).ainvoke(
                    tool_call["args"], config=config
                )
                for tool_call in tool_calls
            ]
        )
        result_msgs = [
            ToolMessage(
                content=result, tool_call_id=tool_call["id"], name=tool_call["name"]
            )
            for result, tool_call in zip(results, tool_calls)
        ]
        return Command(
            update={"planner_messages": [*seed_messages, response, *result_msgs]},
            goto="planner",
        )
    else:
        logger.warning(
            f"planner: No tool calls! Ending planner with response: {response.content}"
        )
        return Command(
            update={"planner_messages": [*seed_messages, response]}, goto=END
        )


async def node_write_report(state: AgentState, config: RunnableConfig):
    report_writer_model = get_model()

    # synthesize the research trajectory
    research_trajectory = ""
    tool_call_to_results = []
    for msg in state["planner_messages"]:
        if msg.type == "ai":
            call_to_result = {}
            tool_calls = msg.tool_calls
            if tool_calls:
                for tool_call in tool_calls:
                    call_to_result[(tool_call["name"], tool_call["id"])] = {
                        "name": tool_call["name"],
                        "args": tool_call["args"],
                        "result": None,
                    }
            tool_call_to_results.append((msg.content, call_to_result))
        elif msg.type == "tool":
            call_to_result = tool_call_to_results[-1][1]
            key = (msg.name, msg.tool_call_id)
            if key not in call_to_result:
                logger.warning(
                    f"write_report: Tool result without matching tool call: {key}"
                )
            else:
                call_to_result[key]["result"] = msg.content
        elif msg.type == "human":
            research_trajectory += f"<user>\n{msg.content}\n</user>\n"
        else:
            raise ValueError(f"write_report: Unexpected message type: {msg.type}")

    for reasoning, call_to_result in tool_call_to_results:
        research_trajectory += f"<reasoning>\n{reasoning}\n</reasoning>\n"
        for (name, _), result in call_to_result.items():
            research_trajectory += (
                f"<call_{name}>\n{json.dumps(result['args'])}\n</call_{name}>\n"
            )
            research_trajectory += (
                f"<result_{name}>\n{result['result']}\n</result_{name}>\n"
            )

    research_trajectory += f"<additional_instructions>\n{state.get('report_writing_instructions')}\n</additional_instructions>\n"
    logger.debug(f"write_report: research_trajectory: {research_trajectory}")

    messages = [
        SystemMessage(
            content=prompts.REPORT_WRITER_SYSTEM_PROMPT.format(
                date=get_formatted_date()
            )
        ),
        HumanMessage(content=research_trajectory),
    ]

    response = await report_writer_model.ainvoke(messages)

    prev_tool_call_id = state["deep_research_tool_call_id"]
    assistant_tool_result = ToolMessage(
        content=response.content,
        tool_call_id=prev_tool_call_id,
        name="start_deep_research",
    )

    return Command(
        update={
            "final_report": response.content,
            "general_assistant_messages": [assistant_tool_result],
        },
        goto="general_assistant",
    )


async def main(initial_user_query: Optional[str] = None):
    graph_builder = StateGraph(AgentState)
    graph_builder.add_node("general_assistant", node_general_assistant)
    graph_builder.add_node("planner", node_planner)
    graph_builder.add_node("write_report", node_write_report)

    graph_builder.add_edge(START, "general_assistant")

    graph = graph_builder.compile(checkpointer=InMemorySaver())

    config = {"configurable": {"thread_id": "main"}}

    user = initial_user_query or input("You: ").strip()
    while True:
        if user.lower() in {"exit", "quit"}:
            break

        state = await graph.ainvoke(
            {"general_assistant_messages": [HumanMessage(content=user)]}, config=config
        )
        print("Assistant:", state["general_assistant_messages"][-1].content)
        user = input("You: ").strip()


if __name__ == "__main__":
    asyncio.run(main())
