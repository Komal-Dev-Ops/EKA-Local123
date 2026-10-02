"""
app.py - Streamlit Frontend

THIS IS THE USER INTERFACE OF THE KNOWLEDGE ASSISTANT.

Streamlit lets you build web apps using only Python.
No HTML/CSS/JavaScript needed!

HOW STREAMLIT WORKS:
    - Your Python code runs top to bottom
    - Every time user interacts, the ENTIRE script reruns
    - st.session_state persists data between reruns

FEATURES OF THIS UI:
    - Chat interface (like ChatGPT)
    - Sidebar for document management
    - Source citations shown below each answer
    - Agent routing info displayed
    - Upload new documents

HOW TO RUN:
    streamlit run frontend/app.py
"""

import os
import streamlit as st
import requests
import json
from datetime import datetime


# ============================================================
# CONFIGURATION
# ============================================================

# Backend API URL - should match where FastAPI is running
# Locally this is localhost:8000; in Docker Compose it is set to http://backend:8000
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


# ============================================================
# PAGE CONFIGURATION (must be first Streamlit call)
# ============================================================

st.set_page_config(
    page_title="Enterprise Knowledge Assistant",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================
# CUSTOM CSS STYLING
# ============================================================

st.markdown("""
<style>
    /* Main title styling */
    .main-title {
        font-size: 2.2em;
        font-weight: bold;
        color: #1f4e79;
        margin-bottom: 0px;
    }

    /* Subtitle styling */
    .subtitle {
        font-size: 1em;
        color: #666;
        margin-bottom: 20px;
    }

    /* User message bubble */
    .user-message {
        background-color: #e8f4fd;
        border-left: 4px solid #1f4e79;
        padding: 12px 16px;
        border-radius: 8px;
        margin: 10px 0;
    }

    /* Assistant message bubble */
    .assistant-message {
        background-color: #f0f7f0;
        border-left: 4px solid #2e7d32;
        padding: 12px 16px;
        border-radius: 8px;
        margin: 10px 0;
    }

    /* Citation card */
    .citation-card {
        background-color: #fff9e6;
        border: 1px solid #f0c040;
        border-radius: 6px;
        padding: 10px;
        margin: 5px 0;
        font-size: 0.85em;
    }

    /* Status badge */
    .status-badge {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.75em;
        font-weight: bold;
    }

    /* Route badge colors */
    .route-rag {
        background-color: #e3f2fd;
        color: #1565c0;
    }
    .route-general {
        background-color: #f3e5f5;
        color: #6a1b9a;
    }

    /* Stale sidebar text */
    .sidebar-section {
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)


# ============================================================
# SESSION STATE INITIALIZATION
# ============================================================

# Session state persists between Streamlit reruns (user interactions)
# We use it to store chat history

if "messages" not in st.session_state:
    # Start with a welcome message from the assistant
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": (
                "👋 Hello! I'm your Enterprise Knowledge Assistant.\n\n"
                "I can answer questions about:\n"
                "- 📋 **Company Policies** (leave, WFH, expenses, performance)\n"
                "- 💰 **Employee Benefits** (health insurance, 401k, equity)\n"
                "- 📚 **Employee Handbook** (onboarding, IT, facilities)\n"
                "- 🌍 **General Questions**\n\n"
                "What would you like to know?"
            ),
            "citations": [],
            "route": None,
            "timestamp": datetime.now().isoformat()
        }
    ]


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def check_backend_health() -> dict:
    """Check if the FastAPI backend is running and healthy."""
    try:
        response = requests.get(f"{BACKEND_URL}/api/health", timeout=5)
        if response.status_code == 200:
            return response.json()
        return {"status": "error", "message": f"HTTP {response.status_code}"}
    except requests.ConnectionError:
        return {"status": "offline", "message": "Cannot connect to backend"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def send_query(query: str) -> dict:
    """
    Send a query to the FastAPI backend and get a response.

    Args:
        query: The user's question

    Returns:
        Response dictionary with answer and citations
    """
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/query",
            json={"query": query},
            timeout=60  # Longer timeout since LLM can be slow
        )

        if response.status_code == 200:
            return response.json()
        else:
            return {
                "answer": f"Error from server: {response.text}",
                "citations": [],
                "route": None
            }

    except requests.ConnectionError:
        return {
            "answer": (
                "❌ Cannot connect to the backend server.\n\n"
                "Please make sure FastAPI is running:\n"
                "`uvicorn backend.main:app --reload --port 8000`"
            ),
            "citations": [],
            "route": None
        }
    except requests.Timeout:
        return {
            "answer": "⏱️ Request timed out. The server is taking too long to respond.",
            "citations": [],
            "route": None
        }
    except Exception as e:
        return {
            "answer": f"Unexpected error: {str(e)}",
            "citations": [],
            "route": None
        }


def upload_document(file) -> dict:
    """
    Upload a document to the FastAPI backend for ingestion.

    Args:
        file: Streamlit uploaded file object

    Returns:
        Response dictionary with success status
    """
    try:
        files = {"file": (file.name, file.getvalue(), file.type)}
        response = requests.post(
            f"{BACKEND_URL}/api/ingest",
            files=files,
            timeout=120  # Longer timeout for large files
        )

        if response.status_code == 200:
            return response.json()
        else:
            return {
                "success": False,
                "message": f"Upload failed: {response.text}"
            }

    except Exception as e:
        return {
            "success": False,
            "message": f"Upload error: {str(e)}"
        }


def get_documents() -> list:
    """Get list of documents from the backend."""
    try:
        response = requests.get(f"{BACKEND_URL}/api/documents", timeout=10)
        if response.status_code == 200:
            return response.json().get("documents", [])
        return []
    except:
        return []


def display_citations(citations: list, namespace: str = ""):
    """Display citation cards for retrieved sources."""
    if not citations:
        return

    st.markdown("**📚 Sources Used:**")

    for citation in citations:
        with st.expander(f"📄 {citation.get('source', 'Unknown Source')}", expanded=False):
            st.markdown(f"*{citation.get('preview', '')}*")
            # namespace makes the key unique across all chat messages
            unique_key = f"full_{namespace}_{citation.get('id', 0)}_{citation.get('source', '')}"
            if st.button(f"Show Full Text", key=unique_key):
                st.text(citation.get('full_text', ''))


def display_route_badge(route: str):
    """Display a colored badge showing which agent handled the query."""
    if route == "rag":
        st.markdown(
            '<span class="status-badge route-rag">🔍 RAG Search</span>',
            unsafe_allow_html=True
        )
    elif route == "general":
        st.markdown(
            '<span class="status-badge route-general">🌐 General Knowledge</span>',
            unsafe_allow_html=True
        )


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    st.markdown("## 🏢 Knowledge Assistant")
    st.markdown("---")

    # ── System Status ──────────────────────────────────
    st.markdown("### ⚡ System Status")

    health = check_backend_health()

    if health.get("status") == "healthy":
        st.success("✅ Backend: Online")
        if health.get("graph_initialized"):
            st.success("✅ AI Agents: Ready")
        else:
            st.warning("⚠️ AI Agents: Not Ready")
        if health.get("vectorstore_initialized"):
            st.success("✅ Vector Store: Ready")
        else:
            st.warning("⚠️ Vector Store: Not Ready")

    elif health.get("status") == "offline":
        st.error("❌ Backend: Offline")
        st.warning("Start the backend with:\n`uvicorn backend.main:app --reload`")

    else:
        st.warning(f"⚠️ Status: {health.get('status', 'unknown')}")

    st.markdown("---")

    # ── Document Management ────────────────────────────
    st.markdown("### 📁 Knowledge Base Documents")

    # Show current documents
    documents = get_documents()

    if documents:
        for doc in documents:
            st.markdown(f"📄 **{doc['filename']}** ({doc['size_kb']} KB)")
    else:
        st.info("No documents found")

    st.markdown("---")

    # ── Upload New Document ────────────────────────────
    st.markdown("### 📤 Upload New Document")

    uploaded_file = st.file_uploader(
        "Choose a file",
        type=["txt", "pdf"],
        help="Upload .txt or .pdf files to add to the knowledge base"
    )

    if uploaded_file is not None:
        if st.button("📥 Ingest Document", use_container_width=True):
            with st.spinner("Uploading and processing..."):
                result = upload_document(uploaded_file)

            if result.get("success"):
                st.success(f"✅ {result.get('message', 'Upload successful!')}")
                st.info(f"📊 Chunks created: {result.get('chunks_ingested', 0)}")
                st.rerun()  # Refresh the page to show new document
            else:
                st.error(f"❌ {result.get('message', 'Upload failed')}")

    st.markdown("---")

    # ── Clear Chat ────────────────────────────────────
    if st.button("🗑️ Clear Chat History", use_container_width=True):
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "Chat cleared! How can I help you?",
                "citations": [],
                "route": None,
                "timestamp": datetime.now().isoformat()
            }
        ]
        st.rerun()

    st.markdown("---")

    # ── Tips ──────────────────────────────────────────
    st.markdown("### 💡 Sample Questions")
    sample_questions = [
        "How many leave days do I get?",
        "What is the WFH policy?",
        "How does 401k matching work?",
        "What health insurance do we have?",
        "How do I submit expenses?",
        "What's the performance review cycle?",
    ]

    for q in sample_questions:
        if st.button(q, key=f"sample_{q}", use_container_width=True):
            st.session_state.pending_query = q
            st.rerun()


# ============================================================
# MAIN CHAT AREA
# ============================================================

# Title
st.markdown('<p class="main-title">🏢 Enterprise Knowledge Assistant</p>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Ask questions about company policies, benefits, and more — with citations!</p>', unsafe_allow_html=True)

# ── Display Chat History ───────────────────────────────────

for msg_idx, message in enumerate(st.session_state.messages):
    role = message["role"]
    content = message["content"]
    citations = message.get("citations", [])
    route = message.get("route")

    if role == "user":
        # User message - appears on the right
        with st.chat_message("user", avatar="👤"):
            st.markdown(content)

    else:
        # Assistant message - appears on the left
        with st.chat_message("assistant", avatar="🤖"):
            st.markdown(content)

            # Show which agent handled this (route info)
            if route:
                col1, col2 = st.columns([1, 4])
                with col1:
                    display_route_badge(route)

            # Show citations if available — msg_idx makes keys unique per message
            if citations:
                st.markdown("---")
                display_citations(citations, namespace=f"hist_{msg_idx}")


# ── Handle Pending Query (from sidebar sample questions) ──

if "pending_query" in st.session_state:
    pending = st.session_state.pop("pending_query")

    # Add to chat as user message
    st.session_state.messages.append({
        "role": "user",
        "content": pending,
        "citations": [],
        "route": None,
        "timestamp": datetime.now().isoformat()
    })

    # Get response from backend
    with st.spinner("🤔 Thinking..."):
        result = send_query(pending)

    # Add assistant response to chat
    st.session_state.messages.append({
        "role": "assistant",
        "content": result.get("answer", "No answer received"),
        "citations": result.get("citations", []),
        "route": result.get("route"),
        "timestamp": result.get("timestamp", datetime.now().isoformat())
    })

    st.rerun()


# ── Chat Input ─────────────────────────────────────────────

# st.chat_input creates the input box at the bottom of the page
user_input = st.chat_input(
    placeholder="Ask a question about company policies, benefits, HR, or anything else...",
)

if user_input:
    # Add user message to chat history
    st.session_state.messages.append({
        "role": "user",
        "content": user_input,
        "citations": [],
        "route": None,
        "timestamp": datetime.now().isoformat()
    })

    # Display user message immediately
    with st.chat_message("user", avatar="👤"):
        st.markdown(user_input)

    # Get response from backend with a spinner
    with st.chat_message("assistant", avatar="🤖"):
        with st.spinner("🔍 Searching knowledge base..."):
            result = send_query(user_input)

        answer = result.get("answer", "No answer received")
        citations = result.get("citations", [])
        route = result.get("route")

        # Display the answer
        st.markdown(answer)

        # Show route badge
        if route:
            col1, col2 = st.columns([1, 4])
            with col1:
                display_route_badge(route)

        # Show citations — use "live" namespace for the current response
        if citations:
            st.markdown("---")
            display_citations(citations, namespace="live")

    # Save to chat history
    st.session_state.messages.append({
        "role": "assistant",
        "content": answer,
        "citations": citations,
        "route": route,
        "timestamp": result.get("timestamp", datetime.now().isoformat())
    })
