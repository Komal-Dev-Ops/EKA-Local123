"""
helpers.py - Utility functions used across the project

Think of this file as a toolbox. It has small, reusable functions
that multiple parts of the project need.
"""

import os
import json
from datetime import datetime
from typing import List, Dict, Any


def format_response(answer: str, citations: List[Dict], query: str) -> Dict[str, Any]:
    """
    Format the final API response that gets sent back to the user.

    This creates a clean, consistent response structure every time.

    Args:
        answer: The generated answer text
        citations: List of source documents used
        query: The original user question

    Returns:
        A dictionary with all response data
    """
    return {
        "query": query,
        "answer": answer,
        "citations": citations,
        "timestamp": datetime.now().isoformat(),
        "citation_count": len(citations)
    }


def format_error_response(error_message: str, query: str = "") -> Dict[str, Any]:
    """
    Format error responses consistently.

    When something goes wrong, we always return the same structure
    so the frontend knows how to handle it.
    """
    return {
        "query": query,
        "answer": f"Sorry, I encountered an error: {error_message}",
        "citations": [],
        "timestamp": datetime.now().isoformat(),
        "citation_count": 0,
        "error": True
    }


def check_api_key() -> bool:
    """
    Check if the OpenAI API key is configured.

    This is called at startup to warn the user if they forgot
    to set their API key.
    """
    api_key = os.getenv("OPENAI_API_KEY", "")

    if not api_key or api_key == "your_openai_api_key_here":
        print("WARNING: OPENAI_API_KEY is not set or is still the placeholder value.")
        print("Please copy .env.example to .env and add your real API key.")
        return False

    return True


def validate_query(query: str) -> tuple[bool, str]:
    """
    Validate that a user query is acceptable.

    Returns:
        (is_valid, error_message)
    """
    # Check if query is empty
    if not query or not query.strip():
        return False, "Query cannot be empty"

    # Check if query is too short
    if len(query.strip()) < 3:
        return False, "Query is too short. Please ask a more detailed question."

    # Check if query is too long (protect against abuse)
    if len(query) > 2000:
        return False, "Query is too long. Please keep it under 2000 characters."

    return True, ""


def clean_filename(filename: str) -> str:
    """
    Clean a filename to remove unsafe characters.

    This is important when users upload files - we don't want
    filenames with special characters causing issues.
    """
    # Keep only alphanumeric, dots, hyphens, and underscores
    import re
    cleaned = re.sub(r'[^\w\-_\.]', '_', filename)
    return cleaned


def get_file_extension(filename: str) -> str:
    """Get the file extension in lowercase."""
    _, ext = os.path.splitext(filename)
    return ext.lower()


def is_supported_file(filename: str) -> bool:
    """
    Check if an uploaded file type is supported.

    Currently we support .txt and .pdf files.
    """
    supported_extensions = ['.txt', '.pdf', '.md']
    ext = get_file_extension(filename)
    return ext in supported_extensions


def truncate_text(text: str, max_length: int = 200) -> str:
    """
    Truncate text to a maximum length for display purposes.

    Adds "..." at the end if text was truncated.
    """
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."


def pretty_print_docs(docs: list) -> None:
    """
    Print retrieved documents in a readable format.

    Useful for debugging - helps you see what documents
    were retrieved for a query.
    """
    print(f"\n{'='*60}")
    print(f"Retrieved {len(docs)} documents:")
    print('='*60)

    for i, doc in enumerate(docs, 1):
        source = doc.metadata.get('source', 'Unknown')
        print(f"\nDocument {i}:")
        print(f"Source: {source}")
        print(f"Content: {truncate_text(doc.page_content, 300)}")
        print('-'*40)
