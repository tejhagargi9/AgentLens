from functools import lru_cache

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from agentos.agents.nodes import (
    analyst,
    code_analysis,
    github,
    planner,
    rag,
    report,
    verifier,
)
from agentos.agents.state import AgentState


def build_graph() -> CompiledStateGraph:
    """planner -> (rag | github) -> code_analysis -> analyst -> verifier -> report"""
    graph = StateGraph(AgentState)

    graph.add_node("planner", planner.run)
    graph.add_node("rag", rag.run)
    graph.add_node("github", github.run)
    graph.add_node("code_analysis", code_analysis.run)
    graph.add_node("analyst", analyst.run)
    graph.add_node("verifier", verifier.run)
    graph.add_node("report", report.run)

    graph.add_edge(START, "planner")
    graph.add_edge("planner", "rag")
    graph.add_edge("planner", "github")
    # Code analysis waits for both evidence branches: it reads code from uploads and GitHub.
    graph.add_edge(["rag", "github"], "code_analysis")
    graph.add_edge("code_analysis", "analyst")
    graph.add_edge("analyst", "verifier")
    graph.add_edge("verifier", "report")
    graph.add_edge("report", END)

    return graph.compile()


@lru_cache
def get_graph() -> CompiledStateGraph:
    return build_graph()
