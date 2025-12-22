import asyncio
import os

from loguru import logger
import requests
from langchain.tools import BaseTool, tool


def jina_reader(url: str) -> str:
    headers = {
        "Accept": "application/json",  # returns JSON
        "X-Retain-Images": "none",  # don't retain images TODO: support images
    }
    jina_api_key = os.getenv("JINA_API_KEY")
    if jina_api_key:
        headers["Authorization"] = f"Bearer {jina_api_key}"

    response = requests.get(
        f"https://r.jina.ai/{url}",
        headers=headers,
    )

    if response.status_code != 200:
        return f"Error: Failed to extract content from {url}. Status code: {response.status_code}. Response: {response.text}"

    raw_result = response.json()
    data = raw_result.get("data", {})

    return f"Title: {data.get('title', 'No Title')}\nContent: {data.get('content', 'No Content')}"


@tool("web_extract")
async def web_extract(url: str) -> str:
    """
    A content extractor tool. Use this tool when you need to extract the full content from a web page.
    Args:
        url: The URL of the web page to extract the content from.
    Returns:
        The extracted content, containing title and content.
    """
    logger.debug(f"web_extract: {url = }")
    return await asyncio.to_thread(jina_reader, url)
