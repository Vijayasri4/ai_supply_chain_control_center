"""
Orchestration & Routing Layer.

Classifies each user question as "contract", "data", or "hybrid" (via
a lightweight Groq call in utils.ai_engine.classify_question) and
dispatches it to the correct agent through a LangGraph state graph.

Built as a real, runnable graph rather than a plain if/else so the
routing is inspectable and it's easy to add a new agent and route
later (e.g. a supplier-directory agent) without restructuring the
dispatch logic.
"""

from __future__ import annotations

from typing import Optional, TypedDict

from langgraph.graph import StateGraph, END

from utils.ai_engine import ask_question, classify_question, AIEngineError
from utils.contract_rag import retrieve_relevant_clauses


class RouterState(TypedDict):
    question: str
    api_key: str
    model: str
    data_context: str
    contract_collection: Optional[object]
    route: str
    answer: str


def _classify_node(state: RouterState) -> dict:
    route = classify_question(state["question"], state["api_key"], state["model"])
    return {"route": route}


def _contract_agent(state: RouterState) -> dict:
    if state["contract_collection"] is None:
        return {
            "answer": (
                "I don't have a vendor contract loaded yet, so I can't "
                "answer contract-specific questions. Upload one in the "
                "Contract tab first."
            )
        }
    clauses = retrieve_relevant_clauses(state["contract_collection"], state["question"])
    context = "RELEVANT CONTRACT CLAUSES:\n" + "\n---\n".join(clauses)
    answer = ask_question(state["question"], context, state["api_key"], state["model"])
    return {"answer": answer}


def _data_agent(state: RouterState) -> dict:
    answer = ask_question(state["question"], state["data_context"], state["api_key"], state["model"])
    return {"answer": answer}


def _hybrid_agent(state: RouterState) -> dict:
    context = state["data_context"]
    if state["contract_collection"] is not None:
        clauses = retrieve_relevant_clauses(state["contract_collection"], state["question"])
        if clauses:
            context += "\n\nRELEVANT CONTRACT CLAUSES:\n" + "\n---\n".join(clauses)
    answer = ask_question(state["question"], context, state["api_key"], state["model"])
    return {"answer": answer}


def _route_selector(state: RouterState) -> str:
    return state["route"]


def build_router_graph():
    """Build and compile the LangGraph routing graph."""
    graph = StateGraph(RouterState)
    graph.add_node("classify", _classify_node)
    graph.add_node("contract_agent", _contract_agent)
    graph.add_node("data_agent", _data_agent)
    graph.add_node("hybrid_agent", _hybrid_agent)

    graph.set_entry_point("classify")
    graph.add_conditional_edges(
        "classify",
        _route_selector,
        {
            "contract": "contract_agent",
            "data": "data_agent",
            "hybrid": "hybrid_agent",
        },
    )
    graph.add_edge("contract_agent", END)
    graph.add_edge("data_agent", END)
    graph.add_edge("hybrid_agent", END)

    return graph.compile()


def answer_with_router(
    question: str,
    api_key: str,
    model: str,
    data_context: str,
    contract_collection: Optional[object],
) -> tuple[str, str]:
    """Run the routing graph for one question.

    Returns (answer, route_used) so the UI can show a routing trace.
    """
    app = build_router_graph()
    try:
        result = app.invoke({
            "question": question,
            "api_key": api_key,
            "model": model,
            "data_context": data_context,
            "contract_collection": contract_collection,
            "route": "",
            "answer": "",
        })
    except AIEngineError:
        raise
    except Exception as exc:
        raise AIEngineError(f"Router error: {exc}") from exc

    return result["answer"], result["route"]