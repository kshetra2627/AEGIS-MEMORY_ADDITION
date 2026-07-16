"""LangGraph StateGraph orchestrator. Every query executes START -> ... -> END through this graph;
Streamlit never calls tools or the LLM directly."""
import re
import time
from typing import TypedDict, Any
from langgraph.graph import StateGraph, END

from tools.compliance_tools import (
    classify_topic_tool, identify_owner_tool, retrieve_policy_documents_tool,
    generate_citations_tool, calculate_confidence_tool, classify_risk_tool,
    human_review_tool, log_audit_tool,
)
from agents.compliance_agent import generate_draft_answer
from agents.governance_agent import validate as governance_validate, REFUSAL_MESSAGE

FOLLOWUP_MARKERS = re.compile(r"\b(that|this|it|those|these)\b", re.IGNORECASE)


class GraphState(TypedDict, total=False):
    query: str
    effective_query: str
    chat_history: list
    topic: str
    in_domain: bool
    owner: str
    retrieved_chunks: list
    context_available: bool
    draft_answer: str
    llm_provider: str
    llm_attempts: list
    citations: list
    confidence: dict
    governance_passed: bool
    governance_reason: str
    final_text: str
    risk: str
    review_status: str
    escalated: bool
    final_answer: Any
    held_answer: str
    trace: list
    timings: dict
    row_id: int


def _trace(state: GraphState, node: str, tool: str, start: float, input_summary: str,
           output_summary: str, decision: str, status: str = "success",
           retrieved: list = None, scores: list = None):
    state.setdefault("trace", []).append({
        "node": node,
        "tool": tool,
        "execution_time_ms": round((time.time() - start) * 1000, 1),
        "input_summary": input_summary,
        "output_summary": output_summary,
        "decision": decision,
        "status": status,
        "retrieved_documents": retrieved or [],
        "similarity_scores": scores or [],
    })


def _resolve_followup(query: str, chat_history: list) -> str:
    if not chat_history:
        return query
    if FOLLOWUP_MARKERS.search(query) and len(query.split()) < 15:
        last = chat_history[-1]
        return f"(Context: previous topic was '{last.get('topic')}', previous question was '{last.get('query')}') {query}"
    return query


def node_classify_topic(state: GraphState) -> GraphState:
    t0 = time.time()
    effective_query = _resolve_followup(state["query"], state.get("chat_history", []))
    state["effective_query"] = effective_query
    result = classify_topic_tool.invoke({"query": effective_query})
    state["topic"] = result["topic"]
    state["in_domain"] = result["in_domain"]
    _trace(state, "Query Classification", "classify_topic", t0, effective_query,
           f"topic={result['topic']}, in_domain={result['in_domain']}",
           "in-domain" if result["in_domain"] else "out-of-domain")
    return state


def node_topic_routing(state: GraphState) -> GraphState:
    t0 = time.time()
    result = identify_owner_tool.invoke({"topic": state["topic"]})
    state["owner"] = result["owner"]
    _trace(state, "Topic Routing", "identify_owner", t0, state["topic"],
           f"owner={result['owner']}", f"routed to {result['owner']}")
    return state


def node_rag_retrieval(state: GraphState) -> GraphState:
    t0 = time.time()
    result = retrieve_policy_documents_tool.invoke({"query": state["effective_query"]})
    chunks = result["chunks"]
    state["retrieved_chunks"] = chunks
    latency = time.time() - t0
    state.setdefault("timings", {})["retrieval_latency"] = round(latency, 3)
    qualifying = [c for c in chunks if c["qualifies"]]
    _trace(state, "RAG Retrieval", "retrieve_policy_documents", t0, state["effective_query"],
           f"{len(chunks)} retrieved, {len(qualifying)} qualifying (>= threshold)",
           "sufficient candidates" if qualifying else "no qualifying chunks",
           retrieved=[c["filename"] for c in chunks],
           scores=[round(c["score"], 3) for c in chunks])
    return state


def node_context_validation(state: GraphState) -> GraphState:
    t0 = time.time()
    qualifying = [c for c in state["retrieved_chunks"] if c["qualifies"]]
    state["context_available"] = len(qualifying) > 0
    _trace(state, "Context Validation", "-", t0, f"{len(qualifying)} qualifying chunks",
           f"context_available={state['context_available']}",
           "proceed" if state["context_available"] else "likely refusal")
    return state


def node_compliance_reasoning(state: GraphState) -> GraphState:
    t0 = time.time()
    if state["in_domain"] and state["context_available"]:
        history_summary = ""
        if state.get("chat_history"):
            last = state["chat_history"][-1]
            history_summary = f"previous topic={last.get('topic')}, previous owner={last.get('owner')}"
        result = generate_draft_answer(state["effective_query"], state["retrieved_chunks"], history_summary)
        state["draft_answer"] = result["text"]
        state["llm_provider"] = result["provider"]
        state["llm_attempts"] = result.get("attempts", [])
        decision = f"answered via {result['provider']}" if result["text"] else "generation failed"
    else:
        state["draft_answer"] = ""
        state["llm_provider"] = "skipped"
        state["llm_attempts"] = []
        decision = "skipped (out-of-domain or no context)"
    _trace(state, "Compliance Reasoning", "-", t0, state["effective_query"],
           f"draft length={len(state['draft_answer'])} chars, provider={state['llm_provider']}",
           decision)
    return state


def node_citation_generation(state: GraphState) -> GraphState:
    t0 = time.time()
    result = generate_citations_tool.invoke({"chunks": state["retrieved_chunks"]})
    state["citations"] = result["citations"]
    _trace(state, "Citation Generation", "generate_citations", t0,
           f"{len(state['retrieved_chunks'])} chunks", f"{len(result['citations'])} citations generated",
           "citations built")
    return state


def node_confidence_calculation(state: GraphState) -> GraphState:
    t0 = time.time()
    result = calculate_confidence_tool.invoke({"chunks": state["retrieved_chunks"], "citations": state["citations"]})
    state["confidence"] = result
    _trace(state, "Confidence Calculation", "calculate_confidence", t0,
           f"{len(state['retrieved_chunks'])} chunks, {len(state['citations'])} citations",
           f"confidence={result['score']}% ({result['level']})", result["level"])
    return state


def node_governance_validation(state: GraphState) -> GraphState:
    t0 = time.time()
    result = governance_validate(state["in_domain"], state["retrieved_chunks"], state["draft_answer"], state["confidence"])
    state["governance_passed"] = result["passed"]
    state["governance_reason"] = result["reason"]
    state["final_text"] = result["final_text"]
    _trace(state, "Governance Validation", "-", t0,
           f"draft present={bool(state['draft_answer'])}", f"reason={result['reason']}",
           "PASSED" if result["passed"] else "REFUSED")
    return state


def node_risk_classification(state: GraphState) -> GraphState:
    t0 = time.time()
    if not state["in_domain"]:
        state["risk"] = "N/A"
        _trace(state, "Risk Classification", "classify_risk", t0, "out-of-domain", "risk=N/A", "skipped")
        return state
    result = classify_risk_tool.invoke({"query": state["effective_query"], "topic": state["topic"]})
    state["risk"] = result["risk"]
    _trace(state, "Risk Classification", "classify_risk", t0, state["effective_query"],
           f"risk={result['risk']}", result["risk"])
    return state


def node_human_review_gate(state: GraphState) -> GraphState:
    t0 = time.time()
    if state["risk"] == "High" and state["in_domain"]:
        result = human_review_tool.invoke({"risk": state["risk"], "owner": state["owner"]})
        state["review_status"] = result["status"]
        state["held_answer"] = state["final_text"]
        state["final_answer"] = None
        _trace(state, "Human Review Gate", "human_review", t0, f"risk={state['risk']}",
               f"status={result['status']}, owner={state['owner']}", "AWAITING APPROVAL")
    else:
        state["review_status"] = "Not Required"
        state["final_answer"] = state["final_text"]
        _trace(state, "Human Review Gate", "human_review", t0, f"risk={state['risk']}",
               "no review required", "auto-finalized")
    return state


def node_audit_logging(state: GraphState) -> GraphState:
    t0 = time.time()
    escalated = bool((state["in_domain"] and not state["governance_passed"]) or state["risk"] == "High")
    state["escalated"] = escalated
    total_latency = sum(n["execution_time_ms"] for n in state["trace"]) / 1000
    record = {
        "question": state["query"],
        "retrieved_documents": list({c["filename"] for c in state["retrieved_chunks"]}),
        "retrieved_chunks": [c["chunk_id"] for c in state["retrieved_chunks"]],
        "topic": state["topic"],
        "owner": state["owner"],
        "risk": state["risk"],
        "confidence": state["confidence"]["score"],
        "answer": state.get("held_answer") or state.get("final_answer") or state["final_text"],
        "citations": state["citations"],
        "escalated": escalated,
        "approval_status": state.get("review_status", "N/A"),
        "llm_provider": state.get("llm_provider", "none"),
        "retrieval_latency": state.get("timings", {}).get("retrieval_latency", 0),
        "total_latency": round(total_latency, 3),
        "execution_status": "success",
    }
    result = log_audit_tool.invoke({"record": record})
    state["row_id"] = result["row_id"]
    _trace(state, "Audit Logging", "log_audit", t0, "final record", f"row_id={result['row_id']}", "logged")
    return state


def _route_after_governance(state: GraphState) -> str:
    return "risk_classification" if state["in_domain"] else "audit_logging"


def _route_after_risk(state: GraphState) -> str:
    return "human_review_gate" if state["risk"] == "High" else "audit_logging"


def build_graph():
    graph = StateGraph(GraphState)
    graph.add_node("classify_topic", node_classify_topic)
    graph.add_node("topic_routing", node_topic_routing)
    graph.add_node("rag_retrieval", node_rag_retrieval)
    graph.add_node("context_validation", node_context_validation)
    graph.add_node("compliance_reasoning", node_compliance_reasoning)
    graph.add_node("citation_generation", node_citation_generation)
    graph.add_node("confidence_calculation", node_confidence_calculation)
    graph.add_node("governance_validation", node_governance_validation)
    graph.add_node("risk_classification", node_risk_classification)
    graph.add_node("human_review_gate", node_human_review_gate)
    graph.add_node("audit_logging", node_audit_logging)

    graph.set_entry_point("classify_topic")
    graph.add_edge("classify_topic", "topic_routing")
    graph.add_edge("topic_routing", "rag_retrieval")
    graph.add_edge("rag_retrieval", "context_validation")
    graph.add_edge("context_validation", "compliance_reasoning")
    graph.add_edge("compliance_reasoning", "citation_generation")
    graph.add_edge("citation_generation", "confidence_calculation")
    graph.add_edge("confidence_calculation", "governance_validation")
    graph.add_conditional_edges("governance_validation", _route_after_governance,
                                 {"risk_classification": "risk_classification", "audit_logging": "audit_logging"})
    graph.add_conditional_edges("risk_classification", _route_after_risk,
                                 {"human_review_gate": "human_review_gate", "audit_logging": "audit_logging"})
    graph.add_edge("human_review_gate", "audit_logging")
    graph.add_edge("audit_logging", END)

    return graph.compile()


_compiled_graph = None


def get_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    return _compiled_graph


def run_query(query: str, chat_history: list = None) -> dict:
    """Executes one query through the full LangGraph StateGraph, START to END."""
    graph = get_graph()
    initial_state: GraphState = {"query": query, "chat_history": chat_history or [], "trace": [], "risk": "N/A"}
    final_state = graph.invoke(initial_state)
    return final_state


def run_query_streaming(query: str, chat_history: list = None, on_step=None) -> dict:
    """Identical execution to run_query -- same compiled graph, same node sequence,
    same tool bindings -- but streamed node-by-node so the UI can render live status
    as each LangGraph node actually completes, instead of a generic spinner.
    """
    graph = get_graph()
    initial_state: GraphState = {"query": query, "chat_history": chat_history or [], "trace": [], "risk": "N/A"}
    final_state = dict(initial_state)
    for update in graph.stream(initial_state, stream_mode="updates"):
        for node_name, node_output in update.items():
            final_state.update(node_output)
            if on_step:
                on_step(node_name, final_state)
    return final_state
