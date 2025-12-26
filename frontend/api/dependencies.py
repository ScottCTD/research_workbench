from research_workbench.deep_research import get_graph
from langgraph.graph.state import CompiledStateGraph

_graph: CompiledStateGraph | None = None

def get_research_graph() -> CompiledStateGraph:
    """Lazily load and return the compiled research graph."""
    global _graph
    if _graph is None:
        _graph = get_graph()
    return _graph
