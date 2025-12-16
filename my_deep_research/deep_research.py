import asyncio
from datetime import datetime

from langchain.agents import create_agent
from langchain.chat_models import BaseChatModel, init_chat_model
from langchain.messages import ToolMessage
from langchain.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage, get_buffer_string
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.types import Command, interrupt
from pydantic import BaseModel
from langchain_tavily.tavily_search import TavilySearch

import prompts

model: BaseChatModel = init_chat_model(model="xai:grok-4-1-fast-non-reasoning")


class AgentState(MessagesState):
    final_report: str


def get_formatted_date():
    return datetime.now().strftime("%Y-%m-%d")


@tool
def clarify_with_user(question: str) -> str:
    """
    Clarify with the user to get more information.
    Args:
        question: The question to the user for further clarification.
    Returns:
        The clarification from the user.
    """
    return interrupt({"type": "clarify_with_user", "question": question})

@tool
def start_deep_research(query: str) -> str:
    """
    Start a deep research on the query.
    Args:
        query: The query to start the research on.
    Returns:
        The research report.
    """
    return ""


async def node_general_assistant(state: AgentState):
    system_prompt = prompts.GENERAL_ASSISTANT_SYSTEM_PROMPT.format(date=get_formatted_date())
    messages = [SystemMessage(content=system_prompt), *state["messages"]]

    tavily_search_tool = TavilySearch(max_results=10)
    tavily_search_tool.name = "web_search"
    general_assistant_model = model.bind_tools([clarify_with_user, tavily_search_tool, start_deep_research])

    response = await general_assistant_model.ainvoke(messages)

    tool_calls = response.tool_calls

    if tool_calls:
        tool = tool_calls[0]["name"]
        print(f"{tool}: {tool_calls[0]['args']}")
        if tool == "clarify_with_user":
            clarification = await clarify_with_user.ainvoke(tool_calls[0]["args"])
            return Command(
                update={"messages": [response, HumanMessage(content=clarification)]},
                goto="general_assistant",
            )
        elif tool == "web_search":
            results = await tavily_search_tool.ainvoke(tool_calls[0]["args"])
            results = results["results"]
            results.sort(key=lambda x: x["score"], reverse=True)
            results_str = ""
            for result in results:
                title, url, content = result["title"], result["url"], result["content"]
                results_str += f"Title: {title}\nURL: {url}\nContent: {content}\n"
                results_str += "\n----\n"

            result_msg = ToolMessage(tool_call_id=tool_calls[0]["id"], name=tool, content=results_str)
            return Command(
                update={"messages": [response, result_msg]},
                goto="general_assistant",
            )
        else:
            raise NotImplementedError(f"Tool {tool} not implemented")
    else:
        return Command(
            update={"messages": [response], "final_report": response.content},
            goto=END,
        )


graph_builder = StateGraph(AgentState)
graph_builder.add_node("general_assistant", node_general_assistant)

graph_builder.add_edge(START, "general_assistant")
graph_builder.add_edge("general_assistant", END)

graph = graph_builder.compile(checkpointer=InMemorySaver())


async def main():
    config = {
        "configurable": {
            "thread_id": "main"
        }
    }
    initial_message = input("Enter the initial query: ")
    response = await graph.ainvoke(
        {"messages": [HumanMessage(content=initial_message)]}, config=config
    )
    while "__interrupt__" in response:
        for item in response["__interrupt__"]:
            payload = item.value
            print("Interrupted with payload: ", payload)
            if payload["type"] == "clarify_with_user":
                question = payload["question"]
                clarification = input(f"System asked a clarifying question: {question}\nYou: ")
                response = await graph.ainvoke(Command(resume=clarification), config=config)
            else:
                raise NotImplementedError(f"Interrupted type {payload['type']} not implemented")
    print(response["final_report"])

if __name__ == "__main__":
    asyncio.run(main())
