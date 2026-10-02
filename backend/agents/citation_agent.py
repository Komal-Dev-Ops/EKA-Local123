"""
citation_agent.py - The Citation Agent

WHAT DOES THE CITATION AGENT DO?
    After the RAG agent generates an answer, the citation agent:
    1. Takes the retrieved documents
    2. Formats them into clean, readable citations
    3. Adds them to the response

WHY ARE CITATIONS IMPORTANT?
    In an enterprise setting, employees need to:
    - Verify information is accurate
    - Know which official document to refer to
    - Audit trail for compliance
    - Trust the answers more (they can see the source)

CITATION FORMAT:
    📄 Source: company_policy.txt
    📌 Relevant excerpt: "Annual Leave: 0-2 years of service: 15 days..."
"""

from typing import List, Dict, Any
from langchain_core.documents import Document


def create_citation_node():
    """
    Create and return the citation node function.

    Unlike the router and RAG nodes, the citation node doesn't need
    the LLM - it just processes the already-retrieved documents.

    Returns:
        A function that can be used as a LangGraph node
    """

    def citation_node(state: dict) -> dict:
        """
        Format citations from retrieved documents.

        Args:
            state: Current agent state (contains retrieved_docs)

        Returns:
            Updated state with 'citations' filled in
        """
        retrieved_docs = state.get("retrieved_docs", [])
        print(f"\n[Citation Agent] Formatting citations from {len(retrieved_docs)} documents")

        # If no documents were retrieved, return empty citations
        if not retrieved_docs:
            print("[Citation Agent] No documents to cite")
            return {"citations": []}

        # Format each document into a citation
        citations = format_citations(retrieved_docs)

        print(f"[Citation Agent] Created {len(citations)} citations")

        return {"citations": citations}

    return citation_node


def format_citations(documents: List[Document]) -> List[Dict[str, Any]]:
    """
    Convert raw Document objects into formatted citation dictionaries.

    Each citation has:
    - source: The filename (e.g., "company_policy.txt")
    - preview: First 200 chars of the relevant section
    - full_text: The complete chunk content

    Args:
        documents: List of Document objects from retrieval

    Returns:
        List of citation dictionaries
    """
    citations = []

    for i, doc in enumerate(documents, 1):
        # Get source filename from metadata
        source = doc.metadata.get('source', f'Document {i}')

        # Create a clean preview (first 200 characters)
        full_text = doc.page_content.strip()
        preview = full_text[:300].replace('\n', ' ')

        # Add "..." if text was truncated
        if len(full_text) > 300:
            preview += "..."

        citation = {
            "id": i,
            "source": source,
            "preview": preview,
            "full_text": full_text,
        }

        citations.append(citation)

    return citations


def format_citations_for_display(citations: List[Dict[str, Any]]) -> str:
    """
    Convert citations to a nicely formatted string for display.

    This is used when you want to show citations as plain text
    (e.g., in terminal output or simple text responses).

    Args:
        citations: List of citation dictionaries

    Returns:
        Formatted string with all citations
    """
    if not citations:
        return "No citations available."

    lines = ["\n📚 SOURCES:", "=" * 50]

    for citation in citations:
        lines.append(f"\n[{citation['id']}] 📄 {citation['source']}")
        lines.append(f"    {citation['preview']}")
        lines.append("-" * 50)

    return "\n".join(lines)


if __name__ == "__main__":
    # Run this file directly to try the citation node on hand-made documents.
    # No LLM or vector store needed - these stand in for what the RAG agent retrieves.
    sample_docs = [
        Document(
            page_content=(
                "Annual Leave:\n"
                "0-2 years of service: 15 days\n"
                "3-5 years of service: 20 days\n"
                "6+ years of service: 25 days\n"
                "Unused leave of up to 5 days can be carried over to the next calendar year. "
                "Leave requests must be submitted at least two weeks in advance through the HR portal, "
                "and approved by your direct manager. "
                "Sick leave is separate and does not count against annual leave."
            ),
            metadata={"source": "company_policy.txt"},
        ),
        Document(
            page_content="All laptops must use full-disk encryption and lock after 5 minutes of inactivity.",
            metadata={"source": "it_security_policy.txt"},
        ),
        # No 'source' in metadata - shows the "Document N" fallback
        Document(page_content="Employees may work from home up to 2 days per week."),
    ]

    citation_node = create_citation_node()

    # 1. citation_node: what LangGraph calls, with documents in the state
    result = citation_node({"retrieved_docs": sample_docs})
    print("\n===== citation_node output =====")
    for c in result["citations"]:
        print(f"id={c['id']}  source={c['source']}")
        print(f"  preview ({len(c['preview'])} chars): {c['preview']}")

    # 2. citation_node with no documents (what happens after the General Agent)
    print("\n===== citation_node with no documents =====")
    print(citation_node({"retrieved_docs": []}))

    # 3. format_citations_for_display: the plain-text version
    print("\n===== format_citations_for_display =====")
    print(format_citations_for_display(result["citations"]))
