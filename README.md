# Enterprise Knowledge Assistant

A multi-agent RAG system that answers employee queries using internal documents and provides answers with citations.

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set your API key
# Edit .env and replace "your_openai_api_key_here" with your real key

# 3. Run backend (Terminal 1)
uvicorn backend.main:app --reload --port 8000

# 4. Run frontend (Terminal 2)
streamlit run frontend/app.py
```

## Project Structure

```
enterprise_knowledge_assistant/
├── backend/
│   ├── main.py                    # FastAPI app entry point
│   ├── api/
│   │   └── routes.py              # API endpoints
│   ├── rag/
│   │   ├── document_loader.py     # Load & chunk documents
│   │   ├── embeddings.py          # FAISS vector store
│   │   └── retriever.py           # Search documents
│   ├── agents/
│   │   ├── graph.py               # LangGraph multi-agent workflow
│   │   ├── router_agent.py        # Routes queries
│   │   ├── rag_agent.py           # RAG + General agents
│   │   └── citation_agent.py      # Formats citations
│   ├── utils/
│   │   └── helpers.py             # Utility functions
│   └── data/
│       ├── sample_docs/           # Your company documents go here
│       └── vectorstore/           # Auto-created FAISS index
├── frontend/
│   └── app.py                     # Streamlit chat UI
├── .env                           # Your API keys (create from .env.example)
├── .env.example                   # Template for .env
└── requirements.txt               # Python dependencies
```

## API Endpoints

| Method | URL | Description |
|--------|-----|-------------|
| GET | `/api/health` | Check server status |
| POST | `/api/query` | Ask a question |
| POST | `/api/ingest` | Upload a document |
| GET | `/api/documents` | List documents |
| GET | `/docs` | Interactive API docs |
