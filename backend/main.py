"""
main.py - FastAPI Application Entry Point

THIS IS WHERE EVERYTHING COMES TOGETHER.

This file:
1. Creates the FastAPI application
2. Sets up CORS (so Streamlit frontend can talk to the API)
3. Initializes all components at startup (vector store, agents, graph)
4. Registers API routes
5. Runs the server

HOW TO RUN:
    From the enterprise_knowledge_assistant/ folder:
    uvicorn backend.main:app --reload --port 8000
"""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

if __name__ == "__main__":
    # When run directly (python backend/main.py), make the project root
    # importable so the `from backend...` imports below work, and make it the
    # working directory because the paths in .env (backend/data/...) are relative to it
    import sys
    project_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(project_root))
    os.chdir(project_root)

# Load environment variables from .env file FIRST (before any other imports)
# override=True: the .env key wins over an OPENAI_API_KEY already set in the shell
load_dotenv(Path(__file__).resolve().parent / ".env", override=True)

from backend.rag.document_loader import load_and_split_directory
from backend.rag.embeddings import get_or_create_vectorstore
from backend.rag.retriever import DocumentRetriever
from backend.agents.graph import build_agent_graph, initialize_llm
from backend.api.routes import router
from backend.utils.helpers import check_api_key


# ============================================================
# STARTUP & SHUTDOWN LOGIC
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    This function runs when the server STARTS and when it SHUTS DOWN.

    The code BEFORE `yield` runs at startup.
    The code AFTER `yield` runs at shutdown.

    This is where we initialize all our heavy components:
    - Load documents
    - Create/load vector store
    - Initialize the LLM
    - Build the agent graph
    """

    # ── STARTUP ──────────────────────────────────────────────
    print("\n" + "="*60)
    print("   ENTERPRISE KNOWLEDGE ASSISTANT - STARTING UP")
    print("="*60)

    # Check API key first
    if not check_api_key():
        print("\n⚠️  WARNING: OpenAI API key not configured!")
        print("   The server will start but queries will fail.")
        print("   Please create a .env file with your OPENAI_API_KEY\n")

    # Get paths from environment variables
    docs_path = os.getenv("DOCUMENTS_PATH", "backend/data/sample_docs")
    vectorstore_path = os.getenv("VECTORSTORE_PATH", "backend/data/vectorstore")
    top_k = int(os.getenv("RETRIEVAL_TOP_K", "4"))

    # Step 1: Load documents from the sample_docs folder
    print(f"\n[Startup] Step 1: Loading documents from '{docs_path}'...")
    documents = load_and_split_directory(docs_path)

    if not documents:
        print("[Startup] Warning: No documents found in sample_docs folder!")
        print("[Startup] You can upload documents via the /api/ingest endpoint")

    # Step 2: Create or load the FAISS vector store
    print(f"\n[Startup] Step 2: Initializing vector store at '{vectorstore_path}'...")
    try:
        vectorstore = get_or_create_vectorstore(
            documents=documents,
            save_path=vectorstore_path
        )
        # Store in app state so routes can access it
        app.state.vectorstore = vectorstore
        print("[Startup] Vector store ready!")

    except Exception as e:
        print(f"[Startup] Failed to initialize vector store: {e}")
        print("[Startup] Server will start but document search will not work")
        app.state.vectorstore = None

    # Step 3: Initialize the LLM
    print(f"\n[Startup] Step 3: Initializing Language Model...")
    try:
        llm = initialize_llm()
        app.state.llm = llm
        print("[Startup] LLM ready!")

    except Exception as e:
        print(f"[Startup] Failed to initialize LLM: {e}")
        app.state.llm = None
        app.state.graph = None

        yield  # Server runs even if LLM fails (so we can show error messages)

        print("\n[Shutdown] Server shutting down...")
        return

    # Step 4: Create the document retriever
    print(f"\n[Startup] Step 4: Setting up retriever (top_k={top_k})...")
    if app.state.vectorstore:
        retriever = DocumentRetriever(
            vectorstore=app.state.vectorstore,
            top_k=top_k
        )
        app.state.retriever = retriever
        print("[Startup] Retriever ready!")
    else:
        app.state.retriever = None

    # Step 5: Build the multi-agent graph
    print(f"\n[Startup] Step 5: Building multi-agent workflow...")
    if app.state.vectorstore and app.state.llm:
        agent_graph = build_agent_graph(
            llm=app.state.llm,
            retriever=app.state.retriever
        )
        app.state.graph = agent_graph
        print("[Startup] Agent graph ready!")
    else:
        app.state.graph = None
        print("[Startup] Warning: Agent graph could not be built")

    print("\n" + "="*60)
    print("   SERVER READY! All components initialized.")
    print("   API docs: http://localhost:8000/docs")
    print("="*60 + "\n")

    yield  # Server runs here (handles all requests)

    # ── SHUTDOWN ──────────────────────────────────────────────
    print("\n[Shutdown] Server shutting down gracefully...")
    print("[Shutdown] Goodbye!")


# ============================================================
# CREATE THE FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title="Enterprise Knowledge Assistant API",
    description="""
    A multi-agent RAG system that answers employee queries using internal documents.

    ## Features
    * 🔍 **Smart Document Search**: Finds relevant sections from company documents
    * 🤖 **Multi-Agent AI**: Router + RAG + Citation agents work together
    * 📚 **Cited Answers**: Every answer includes source citations
    * 📄 **Document Upload**: Add new documents on the fly

    ## How to use
    1. Use `POST /api/query` to ask questions
    2. Use `POST /api/ingest` to upload new documents
    3. Use `GET /api/documents` to see what's in the knowledge base
    """,
    version="1.0.0",
    lifespan=lifespan  # Register our startup/shutdown logic
)


# ============================================================
# CORS MIDDLEWARE
# ============================================================

# CORS = Cross-Origin Resource Sharing
# Without this, the Streamlit frontend (on port 8501) cannot
# make requests to our API (on port 8000) - browser security blocks it

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # Allow requests from any origin
    allow_credentials=True,
    allow_methods=["*"],       # Allow GET, POST, PUT, DELETE, etc.
    allow_headers=["*"],       # Allow any headers
)


# ============================================================
# REGISTER ROUTES
# ============================================================

# Include all the API routes defined in routes.py
app.include_router(router)


# ============================================================
# ROOT ENDPOINT
# ============================================================

@app.get("/")
async def root():
    """Root endpoint - shows basic info about the API."""
    return {
        "name": "Enterprise Knowledge Assistant",
        "version": "1.0.0",
        "description": "Multi-agent RAG system for employee queries",
        "docs": "/docs",
        "health": "/api/health"
    }


# ============================================================
# RUN THE SERVER (when running this file directly)
# ============================================================

if __name__ == "__main__":
    # python backend/main.py        → call lifespan and root directly (debug-friendly)
    # python backend/main.py serve  → start the real server on port 8000
    if len(sys.argv) > 1 and sys.argv[1] == "serve":
        import uvicorn

        uvicorn.run(
            "backend.main:app",   # Import string for the app
            host="0.0.0.0",       # Listen on all interfaces
            port=8000,            # Port number
            reload=True,          # Auto-reload when code changes (development only)
            log_level="info"
        )
    else:
        import asyncio
        from backend.agents.graph import run_agent

        async def demo():
            # 1. lifespan: everything before `yield` (startup) runs on entering the block,
            #    everything after `yield` (shutdown) runs on leaving it
            async with lifespan(app):
                print("\n===== app.state after startup =====")
                print(f"vectorstore: {app.state.vectorstore.index.ntotal} vectors")
                print(f"llm:         {type(app.state.llm).__name__}(model={app.state.llm.model_name})")
                print(f"retriever:   top_k={app.state.retriever.top_k}")
                print(f"graph:       nodes={list(app.state.graph.get_graph().nodes)}")

                # 2. root: the GET / endpoint - an async function, so it is awaited
                print("\n===== root() =====")
                print(await root())

                # 3. Use the graph that startup built, as /api/query does
                final_state = run_agent(app.state.graph, "What is our work from home policy?")
                print("\n===== Answer from app.state.graph =====")
                print(final_state["answer"])
                for c in final_state["citations"]:
                    print(f"  [{c['id']}] {c['source']}")

        asyncio.run(demo())
