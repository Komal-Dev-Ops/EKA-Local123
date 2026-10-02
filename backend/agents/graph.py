"""
graph.py - The Multi-Agent Workflow (LangGraph)

WHAT IS LANGGRAPH?
    LangGraph is a framework for building multi-agent AI applications.
    It lets you define:
    - NODES: Individual AI agents (each does one job)
    - EDGES: How agents connect and pass data to each other
    - STATE: Shared data that flows between agents

WHAT IS THE GRAPH IN THIS PROJECT?
    Our graph has 4 nodes:

    ┌─────────────────────────────────────────────────┐
    │                                                  │
    │    [START]                                       │
    │       ↓                                          │
    │    [Router Agent]  ←── Decides which path       │
    │       ↓        ↓                                 │
    │   [RAG Agent]  [General Agent]                  │
    │       ↓                                          │
    │   [Citation Agent] ←── Formats citations        │
    │       ↓                                          │
    │    [END]                                         │
    └─────────────────────────────────────────────────┘

STATE FLOW:
    Each node receives the full state, modifies its part, and passes it on.
    State: {query, route, retrieved_docs, answer, citations}
"""

import os
from typing import TypedDict, List, Optional, Any

from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END

from backend.rag.retriever import DocumentRetriever
from backend.agents.router_agent import create_router_node
from backend.agents.rag_agent import create_rag_node, create_general_node
from backend.agents.citation_agent import create_citation_node


# ============================================================
# STEP 1: Define the Agent State
# ============================================================

class AgentState(TypedDict):
    """
    The shared state that flows between all agents.

    Think of this as a "package" passed between agents.
    Each agent reads from it, adds its results, and passes it along.

    Fields:
        query: The user's original question (never changes)
        route: Where router decided to send the query ("rag" or "general")
        retrieved_docs: Documents found by the RAG agent
        answer: The generated answer text
        citations: Formatted citation information
    """
    query: str
    route: Optional[str]
    retrieved_docs: Optional[List[Any]]
    answer: Optional[str]
    citations: Optional[List[dict]]


# ============================================================
# STEP 2: Define the Routing Logic
# ============================================================

def route_decision(state: AgentState) -> str:
    """
    This function tells LangGraph which node to visit next
    based on the router agent's decision.

    This is a "conditional edge" - the path taken depends on state.

    Args:
        state: Current agent state (after router has run)

    Returns:
        Name of the next node to visit ("rag" or "general")
    """
    route = state.get("route", "rag")
    print(f"[Graph] Routing to: {route}")
    return route


# ============================================================
# STEP 3: Build the Graph
# ============================================================

def build_agent_graph(llm: ChatOpenAI, retriever: DocumentRetriever):
    """
    Build and compile the complete multi-agent workflow.

    This is called once at startup. The compiled graph is then
    used to process every user query.

    Args:
        llm: The language model
        retriever: The document retriever

    Returns:
        Compiled LangGraph workflow ready to use
    """
    print("\n[Graph] Building multi-agent workflow...")

    # ── Create all agent node functions ──────────────────────
    router_node    = create_router_node(llm)
    rag_node       = create_rag_node(llm, retriever)
    general_node   = create_general_node(llm)
    citation_node  = create_citation_node()

    # ── Create the state graph ────────────────────────────────
    # StateGraph takes our state type so it knows what data to track
    workflow = StateGraph(AgentState)

    # ── Add nodes to the graph ────────────────────────────────
    # Each node is: (name, function)
    workflow.add_node("router",   router_node)
    workflow.add_node("rag",      rag_node)
    workflow.add_node("general",  general_node)
    workflow.add_node("citation", citation_node)

    # ── Set the entry point ───────────────────────────────────
    # Every query starts at the router
    workflow.set_entry_point("router")

    # ── Add edges (connections between nodes) ─────────────────

    # Conditional edge from router:
    # - If route == "rag" → go to rag node
    # - If route == "general" → go to general node
    workflow.add_conditional_edges(
        "router",         # From this node
        route_decision,   # Use this function to decide
        {
            "rag":     "rag",      # If "rag" → go to rag node
            "general": "general",  # If "general" → go to general node
        }
    )

    # After RAG agent runs → go to citation agent
    workflow.add_edge("rag", "citation")

    # After citation agent → end the workflow
    workflow.add_edge("citation", END)

    # After general agent → end the workflow (no citations needed)
    workflow.add_edge("general", END)

    # ── Compile the graph ─────────────────────────────────────
    # Compiling validates the graph and prepares it for execution
    compiled_graph = workflow.compile()

    print("[Graph] Multi-agent workflow built successfully!")
    print("[Graph] Flow: Router → (RAG → Citation) OR (General) → END")

    return compiled_graph


# ============================================================
# STEP 4: Initialize Everything
# ============================================================

def initialize_llm() -> ChatOpenAI:
    """
    Initialize the OpenAI language model.

    Uses the model name from environment variables.
    Defaults to gpt-3.5-turbo if not set.
    """
    model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
    temperature = 0  # 0 = more factual/consistent, 1 = more creative

    print(f"[LLM] Initializing {model}...")

    llm = ChatOpenAI(
        model=model,
        temperature=temperature
    )

    return llm


def run_agent(graph, query: str) -> dict:
    """
    Run the multi-agent graph with a user query.

    This is the main function called for each user question.

    Args:
        graph: The compiled LangGraph workflow
        query: The user's question

    Returns:
        Final state dictionary with answer and citations
    """
    print(f"\n{'='*60}")
    print(f"[Agent] Processing query: '{query}'")
    print('='*60)

    # Initial state: only query is set, everything else starts as None
    initial_state = {
        "query": query,
        "route": None,
        "retrieved_docs": [],
        "answer": None,
        "citations": [],
    }

    # Run the graph - this executes all agents in sequence
    # The graph handles the routing automatically
    final_state = graph.invoke(initial_state)

    print(f"\n[Agent] Processing complete!")
    print(f"[Agent] Route taken: {final_state.get('route', 'unknown')}")
    print(f"[Agent] Answer length: {len(final_state.get('answer', ''))} chars")
    print(f"[Agent] Citations: {len(final_state.get('citations', []))}")
    print('='*60)

    return final_state


if __name__ == "__main__":
    # Run from the project root with: python -m backend.agents.graph
    # (-m is needed because this file imports "backend.rag..." and "backend.agents...")
    from pathlib import Path
    from dotenv import load_dotenv
    from backend.rag.embeddings import load_vectorstore

    backend_dir = Path(__file__).resolve().parent.parent
    # override=True: the .env key wins over an OPENAI_API_KEY already set in the shell
    load_dotenv(backend_dir / ".env", override=True)

    # 1. route_decision: pure function, no LLM needed - just reads state["route"]
    print("\n===== route_decision =====")
    print(f"Output: {route_decision({'query': 'leave days?', 'route': 'rag'})}")
    print(f"Output: {route_decision({'query': 'capital of France?', 'route': 'general'})}")

    # 2. initialize_llm: builds the ChatOpenAI client from OPENAI_MODEL in .env
    llm = initialize_llm()
    print(f"Output: {type(llm).__name__}(model={llm.model_name})")

    # 3. build_agent_graph: wires router → rag/general → citation into one workflow
    vectorstore = load_vectorstore(str(backend_dir / "data" / "vectorstore"))
    retriever = DocumentRetriever(vectorstore, top_k=4)
    graph = build_agent_graph(llm, retriever)
    print(f"Output: nodes = {list(graph.get_graph().nodes)}")

    # 4. run_agent: one company question (RAG path) and one general question
    for query in [
        "How many days of annual leave do employees get?",  # expect: rag → citation
        "What is the capital of France?",                   # expect: general
    ]:
        final_state = run_agent(graph, query)
        print("\n----- Final state -----")
        print(f"route: {final_state['route']}")
        print(f"answer: {final_state['answer']}")
        print(f"retrieved_docs: {len(final_state['retrieved_docs'])} documents")
        for c in final_state["citations"]:
            print(f"  [{c['id']}] {c['source']}: {c['preview'][:100]}...")
