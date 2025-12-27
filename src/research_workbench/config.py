from dataclasses import dataclass, fields
from enum import Enum
import os
from typing import Any, Optional

from langgraph.graph.state import RunnableConfig


class SearchEngine(Enum):
    TAVILY = "tavily"
    SEARX = "searx"


@dataclass
class Configuration:

    search_engine: SearchEngine = SearchEngine.TAVILY
    search_engine_max_results: int = 10
    searx_host: Optional[str] = "http://localhost:8001"

    @classmethod
    def from_runnable_config(
        cls, config: Optional[RunnableConfig] = None
    ) -> "Configuration":
        """Create a Configuration instance from a RunnableConfig."""
        configurable = (
            config["configurable"] if config and "configurable" in config else {}
        )
        values: dict[str, Any] = {
            f.name: os.environ.get(f.name.upper(), configurable.get(f.name))
            for f in fields(cls)
            if f.init
        }
        return cls(**{k: v for k, v in values.items() if v})
