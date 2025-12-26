from typing import Literal, Optional

from langchain.tools import BaseTool, tool
from langchain_community.utilities import SearxSearchWrapper
from langchain_tavily.tavily_search import TavilySearch
from langgraph.graph.state import RunnableConfig
from loguru import logger

from research_workbench.config import Configuration, SearchEngine


def get_search_tool(configuration: Configuration) -> BaseTool:
    if configuration.search_engine == SearchEngine.TAVILY:
        return get_tavily_search_tool()
    elif configuration.search_engine == SearchEngine.SEARX:
        return searx_search
    else:
        raise ValueError(f"Invalid search engine: {configuration.search_engine}")


_TAVILY_SEARCH_TOOL: Optional[TavilySearch] = None


def get_tavily_search_tool() -> TavilySearch:
    """Lazily initialize Tavily tool to avoid import-time failures."""
    global _TAVILY_SEARCH_TOOL
    if _TAVILY_SEARCH_TOOL is None:
        _TAVILY_SEARCH_TOOL = TavilySearch(max_results=10)
        _TAVILY_SEARCH_TOOL.name = "web_search"
    return _TAVILY_SEARCH_TOOL


@tool("web_search")
async def tavily_search(
    query: str,
    time_range: Optional[Literal["day", "week", "month", "year"]] = None,
    topic: Optional[Literal["general", "news", "finance"]] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> str:
    """
    A search engine optimized for comprehensive, accurate, and trusted results.
    Useful for when you need to answer questions about current events.
    It not only retrieves URLs and snippets, but offers advanced search depths,
    domain management, time range filters, and image search, this tool delivers
    real-time, accurate, and citation-backed results.
    Input should be a search query.
    Args:
        query: The search query.
        time_range: The time range back from the current date to filter results based on publish date or last updated date. Useful when looking for sources that have published or updated data.
        topic: The category of the search. Can be "general", "news", or "finance". The category of the search "news" is useful for retrieving real-time updates, particularly about politics, sports, and major current events covered by mainstream media sources. "general" is for broader, more general-purpose searches that may include a wide range of sources.
        start_date: Will return all results after the specified start date based on publish date or last updated date. Required to be written in the format YYYY-MM-DD.
        end_date: Will return all results before the specified end date based on publish date or last updated date. Required to be written in the format YYYY-MM-DD.
    Returns:
        The formatted search results, containing title, url, and preview content if available.
    """
    logger.debug(
        f'web_search: Searching for "{query}" with time_range={time_range}, topic={topic}, start_date={start_date}, end_date={end_date}'
    )
    try:
        raw_results = await get_tavily_search_tool().ainvoke(
            query,
            time_range=time_range,
            topic=topic,
            start_date=start_date,
            end_date=end_date,
        )
        if isinstance(raw_results, str):
            logger.debug(f"web_search: raw_results is a string: {raw_results}")
            return f"web_search returned: {raw_results}"
        results = raw_results["results"]
        results.sort(key=lambda x: x["score"], reverse=True)
        results_str = ""
        for result in results:
            title, url, content = result["title"], result["url"], result["content"]
            results_str += f"Title: {title}\nURL: {url}\nContent: {content}"
            results_str += "\n----\n"
        # logger.debug(f"web_search: Web search results: {results_str}")
    except Exception as e:
        logger.error(f"web_search: Error calling web_search: {e}")
        return f"Error calling web_search. Please try again using valid arguments."
    return results_str


_SEARX_SEARCH_WRAPPER: Optional[SearxSearchWrapper] = None


def get_searx_search_wrapper(configuration: Configuration) -> SearxSearchWrapper:
    """Lazily initialize Searx tool to avoid import-time failures."""
    global _SEARX_SEARCH_WRAPPER
    if _SEARX_SEARCH_WRAPPER is None:
        _SEARX_SEARCH_WRAPPER = SearxSearchWrapper(searx_host=configuration.searx_host)
    return _SEARX_SEARCH_WRAPPER


@tool("web_search")
async def searx_search(
    query: str,
    pageno: int = 1,
    time_range: Optional[Literal["day", "month", "year"]] = None,
    config: RunnableConfig = None,
) -> str:
    """
    The SearXNG search engine. Useful for when you need to answer questions about current events.
    Useful for when you need extra context or to answer questions about current events.
    Args:
        query: The search query. This string is passed to external search services.
        pageno: Search page number. More results can be obtained by increasing the page number for the same query.
        time_range: Time range of search for engines which support it. Don't specify it if you don't need it.
    Returns:
        The formatted search results containing title, url, and preview content if available.
    """
    logger.debug(f"searx_search: {query = }")
    configuration = Configuration.from_runnable_config(config)

    if pageno < 1:
        return "Error: Page number must be greater than or equal to 1."
    if time_range is not None and time_range not in {"day", "month", "year"}:
        return "Error: Time range must be one of 'day', 'month', or 'year'."

    param_dict = {
        "query": query,
        "num_results": configuration.search_engine_max_results,
        "pageno": pageno,
    }
    if time_range in {"day", "month", "year"}:
        param_dict["time_range"] = time_range

    raw_results = await get_searx_search_wrapper(configuration).aresults(**param_dict)
    if len(raw_results) == 1 and raw_results[0].get("Result"):
        return "No search result found!"
    
    results_str = "" if raw_results else "No search result found!"
    for result in raw_results:
        title, url, content = (
            result.get("title", "No Title"),
            result.get("link", "No Link"),
            result.get("snippet", "No Preview"),
        )
        results_str += f"Title: {title}\nURL: {url}\nContent: {content}"
        results_str += "\n----\n"
    return results_str
