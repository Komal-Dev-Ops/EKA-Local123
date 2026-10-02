"""
routes.py - FastAPI API Endpoints

THIS FILE DEFINES ALL THE URLS YOUR SERVER RESPONDS TO:

    GET  /api/health     → Check if server is running
    POST /api/query      → Ask a question
    POST /api/ingest     → Upload a new document
    GET  /api/documents  → List all ingested documents

HOW FASTAPI WORKS:
    FastAPI uses "decorators" (@router.get, @router.post) to define
    which function handles which URL and HTTP method.

    When a request comes in:
    1. FastAPI matches the URL to a function
    2. Validates the request data automatically
    3. Calls your function
    4. Returns the response as JSON
"""

import os
import shutil
from pathlib import Path
from typing import List

from fastapi import APIRouter, HTTPException, UploadFile, File, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

if __name__ == "__main__":
    # When run directly (python backend/api/routes.py), make the project root
    # importable so the `from backend...` imports below work
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.rag.document_loader import load_and_split_document
from backend.rag.embeddings import add_documents_to_vectorstore
from backend.agents.graph import run_agent
from backend.utils.helpers import (
    format_response,
    format_error_response,
    validate_query,
    is_supported_file,
    clean_filename
)


# ── API Router ────────────────────────────────────────────────
# This is like a mini-Flask app. We mount it onto the main FastAPI app.
router = APIRouter(prefix="/api", tags=["Knowledge Assistant"])


# ── Request/Response Models (Pydantic) ────────────────────────
# Pydantic automatically validates incoming request data
# If required fields are missing, FastAPI returns a 422 error automatically

class QueryRequest(BaseModel):
    """Model for incoming query requests."""
    query: str  # The user's question

    class Config:
        # Example data shown in API docs
        json_schema_extra = {
            "example": {
                "query": "How many days of annual leave do I get?"
            }
        }


class QueryResponse(BaseModel):
    """Model for query responses."""
    query: str
    answer: str
    citations: List[dict]
    timestamp: str
    citation_count: int


# ── Endpoints ─────────────────────────────────────────────────

@router.get("/health")
async def health_check(request: Request):
    """
    Health check endpoint.

    Used to verify the server is running and the components
    (vector store, agents) are initialized properly.

    Returns:
        Status information about the server
    """
    # Access the app state (set during startup in main.py)
    app_state = request.app.state

    # Check if graph is initialized
    graph_ready = hasattr(app_state, 'graph') and app_state.graph is not None
    vectorstore_ready = hasattr(app_state, 'vectorstore') and app_state.vectorstore is not None

    return {
        "status": "healthy" if (graph_ready and vectorstore_ready) else "degraded",
        "graph_initialized": graph_ready,
        "vectorstore_initialized": vectorstore_ready,
        "message": "Enterprise Knowledge Assistant is running!"
    }


@router.post("/query")
async def query_knowledge_base(request_data: QueryRequest, request: Request):
    """
    Main endpoint: Ask a question to the knowledge assistant.

    FLOW:
    1. Receive the query
    2. Validate it
    3. Run through multi-agent graph
    4. Return answer with citations

    Args:
        request_data: Contains the user's query
        request: FastAPI request object (for accessing app state)

    Returns:
        Answer with citations and metadata
    """
    query = request_data.query

    # Step 1: Validate the query
    is_valid, error_msg = validate_query(query)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)

    # Step 2: Check if the agent graph is initialized
    app_state = request.app.state
    if not hasattr(app_state, 'graph') or app_state.graph is None:
        raise HTTPException(
            status_code=503,
            detail="Knowledge assistant is not initialized yet. Please try again in a moment."
        )

    # Step 3: Run the multi-agent workflow
    try:
        final_state = run_agent(app_state.graph, query)

        # Step 4: Format and return the response
        response = format_response(
            answer=final_state.get("answer", "No answer generated"),
            citations=final_state.get("citations", []),
            query=query
        )

        return JSONResponse(content=response)

    except Exception as e:
        print(f"Error processing query: {e}")
        error_response = format_error_response(str(e), query)
        return JSONResponse(content=error_response, status_code=500)


@router.post("/ingest")
async def ingest_document(request: Request, file: UploadFile = File(...)):
    """
    Upload and ingest a new document into the knowledge base.

    FLOW:
    1. Receive uploaded file
    2. Validate file type
    3. Save file to disk
    4. Load and chunk the document
    5. Add chunks to vector store
    6. Return success confirmation

    Args:
        request: FastAPI request object
        file: The uploaded file

    Returns:
        Confirmation with number of chunks ingested
    """
    # Step 1: Validate the file
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    if not is_supported_file(file.filename):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Supported: .txt, .pdf, .md"
        )

    # Step 2: Clean the filename and set save path
    clean_name = clean_filename(file.filename)
    docs_path = os.getenv("DOCUMENTS_PATH", "backend/data/sample_docs")
    save_path = os.path.join(docs_path, clean_name)

    # Step 3: Save the file to disk
    try:
        # Read the uploaded file content
        content = await file.read()

        # Write it to our documents folder
        with open(save_path, "wb") as f:
            f.write(content)

        print(f"File saved: {save_path} ({len(content)} bytes)")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    # Step 4: Load and chunk the document
    try:
        chunks = load_and_split_document(save_path)
        print(f"Document split into {len(chunks)} chunks")

    except Exception as e:
        # If loading fails, remove the saved file to keep things clean
        os.remove(save_path)
        raise HTTPException(status_code=500, detail=f"Failed to process document: {str(e)}")

    # Step 5: Add to vector store
    try:
        app_state = request.app.state
        vectorstore_path = os.getenv("VECTORSTORE_PATH", "backend/data/vectorstore")

        app_state.vectorstore = add_documents_to_vectorstore(
            vectorstore=app_state.vectorstore,
            new_documents=chunks,
            save_path=vectorstore_path
        )

        print(f"Added {len(chunks)} chunks to vector store")

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to add to knowledge base: {str(e)}"
        )

    # Step 6: Return success response
    return {
    "success": True,
    "filename": clean_name,
    "chunks_ingested": len(chunks),
    "message": f"Successfully ingested '{clean_name}' into the knowledge base"
}


@router.get("/documents")
async def list_documents():
    """
    List all documents in the knowledge base.

    Returns a list of document files that have been ingested.
    Useful for the frontend to show what documents are available.
    """
    docs_path = os.getenv("DOCUMENTS_PATH", "backend/data/sample_docs")
    docs_dir = Path(docs_path)

    if not docs_dir.exists():
        return {"documents": [], "count": 0}

    # Find all supported files in the documents directory
    documents = []
    supported_extensions = ['.txt', '.pdf', '.md']

    for ext in supported_extensions:
        for file_path in docs_dir.glob(f"*{ext}"):
            # Get file size in KB
            size_kb = round(file_path.stat().st_size / 1024, 2)

            documents.append({
                "filename": file_path.name,
                "size_kb": size_kb,
                "type": file_path.suffix.upper()
            })

    return {
        "documents": documents,
        "count": len(documents)
    }


if __name__ == "__main__":
    # Run this file directly to call every endpoint without starting a server.
    # TestClient runs the real app from main.py (including its startup steps)
    # and sends it requests in-process.
    import json     
    from fastapi.testclient import TestClient

    # The paths in .env (backend/data/...) are relative to the project root
    os.chdir(Path(__file__).resolve().parents[2])

    from backend.main import app

    def show(title, response):
        print(f"\n===== {title} -> HTTP {response.status_code} =====")
        print(json.dumps(response.json(), indent=2)[:1500])

    with TestClient(app) as client:  # "with" runs the startup code in main.py
        show("GET /api/health", client.get("/api/health"))

        show("GET /api/documents", client.get("/api/documents"))

        show("POST /api/query", client.post(
            "/api/query",
            json={"query": "How many days of annual leave do employees get?"},
        ))

        # Unsupported file type: rejected before anything is saved, so this
        # shows /api/ingest's validation without changing the knowledge base
        show("POST /api/ingest (bad file type)", client.post(
            "/api/ingest",
            files={"file": ("notes.csv", b"a,b\n1,2\n", "text/csv")},
        ))
