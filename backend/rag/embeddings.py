"""
embeddings.py - Handles converting text to vectors and managing FAISS vector store

WHAT IS AN EMBEDDING?
    An embedding is a way to convert text into a list of numbers (a vector).
    Similar texts will have similar vectors. This lets us find relevant
    documents by comparing numbers instead of reading full text.

    Example:
        "What is the leave policy?" → [0.23, -0.45, 0.89, ...] (1536 numbers)
        "Annual leave entitlement" → [0.24, -0.44, 0.91, ...] (very similar!)

WHAT IS FAISS?
    FAISS (Facebook AI Similarity Search) is a library that stores these
    vectors and lets us find the most similar ones super fast.
    Think of it as a specialized database for vectors.
"""

import os
import pickle
from typing import List, Optional
from pathlib import Path

from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document


def get_embeddings_model() -> OpenAIEmbeddings:
    """
    Create and return the OpenAI embeddings model.

    The embeddings model converts text into vectors.
    We use OpenAI's model because it's high quality and easy to use.

    Returns:
        OpenAIEmbeddings instance
    """
    model_name = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")

    # OpenAIEmbeddings will automatically use the OPENAI_API_KEY from environment
    embeddings = OpenAIEmbeddings(
        model=model_name
    )

    print(f"Initialized embeddings model: {model_name}")
    return embeddings


def create_vectorstore(documents: List[Document], save_path: str) -> FAISS:
    """
    Create a new FAISS vector store from documents.

    This is called when:
    1. Starting the app for the first time
    2. After adding new documents to the knowledge base

    What happens here:
    1. Each document chunk gets converted to a vector using OpenAI
    2. All vectors are stored in FAISS
    3. The vector store is saved to disk so we don't recreate it every time

    Args:
        documents: List of Document chunks
        save_path: Where to save the vector store on disk

    Returns:
        FAISS vector store
    """
    if not documents:
        raise ValueError("Cannot create vector store: no documents provided")

    print(f"Creating vector store from {len(documents)} document chunks...")
    print("Note: This calls the OpenAI API to create embeddings. This costs a small amount.")

    # Get embeddings model
    embeddings = get_embeddings_model()

    # Create FAISS vector store from documents
    # This sends all document text to OpenAI API and gets vectors back
    vectorstore = FAISS.from_documents(
        documents=documents,
        embedding=embeddings
    )

    # Save to disk so we can reuse it next time
    save_vectorstore(vectorstore, save_path)

    print(f"Vector store created with {vectorstore.index.ntotal} vectors")
    return vectorstore


def save_vectorstore(vectorstore: FAISS, save_path: str) -> None:
    """
    Save the FAISS vector store to disk.

    Without saving, we'd have to recreate the vector store (and pay
    for OpenAI API calls) every time we restart the server.

    Args:
        vectorstore: The FAISS vector store to save
        save_path: Directory path where to save the files
    """
    # Create the directory if it doesn't exist
    Path(save_path).mkdir(parents=True, exist_ok=True)

    # FAISS saves two files:
    # - index.faiss: The vector index (the numbers)
    # - index.pkl: The metadata (which vector belongs to which document)
    vectorstore.save_local(save_path)
    print(f"Vector store saved to: {save_path}")


def load_vectorstore(save_path: str) -> Optional[FAISS]:
    """
    Load an existing FAISS vector store from disk.

    This is called at startup if a vector store already exists,
    so we don't have to recreate it.

    Args:
        save_path: Directory where the vector store files are saved

    Returns:
        FAISS vector store, or None if no saved store exists
    """
    # Check if the saved files exist
    index_file = Path(save_path) / "index.faiss"
    pkl_file = Path(save_path) / "index.pkl"

    if not index_file.exists() or not pkl_file.exists():
        print(f"No existing vector store found at: {save_path}")
        return None

    print(f"Loading existing vector store from: {save_path}")

    embeddings = get_embeddings_model()

    # allow_dangerous_deserialization=True is needed because we're loading pickle files
    # This is safe here because WE created these files
    vectorstore = FAISS.load_local(
        save_path,
        embeddings,
        allow_dangerous_deserialization=True
    )

    print(f"Vector store loaded: {vectorstore.index.ntotal} vectors")
    return vectorstore


def add_documents_to_vectorstore(
    vectorstore: FAISS,
    new_documents: List[Document],
    save_path: str
) -> FAISS:
    """
    Add new documents to an existing vector store.

    When a user uploads a new document, we don't recreate the entire
    vector store from scratch. Instead, we just ADD the new documents.

    Args:
        vectorstore: Existing FAISS vector store
        new_documents: New document chunks to add
        save_path: Where to save the updated vector store

    Returns:
        Updated FAISS vector store
    """
    print(f"Adding {len(new_documents)} new chunks to vector store...")

    # Add new documents to the existing vector store
    vectorstore.add_documents(new_documents)

    # Save the updated vector store
    save_vectorstore(vectorstore, save_path)

    print(f"Vector store now has {vectorstore.index.ntotal} total vectors")
    return vectorstore


def get_or_create_vectorstore(documents: List[Document], save_path: str) -> FAISS:
    """
    Load existing vector store OR create a new one.

    This is the main function called at startup.

    Logic:
    - If saved vector store exists → Load it (fast, no API calls)
    - If no saved vector store → Create from documents (slower, uses API)

    Args:
        documents: Documents to use if creating new store
        save_path: Path to load/save the vector store

    Returns:
        FAISS vector store (loaded or newly created)
    """
    # Try to load existing vector store
    vectorstore = load_vectorstore(save_path)

    if vectorstore is not None:
        print("Using existing vector store")
        return vectorstore

    # No existing store - create a new one
    print("No existing vector store found. Creating new one...")

    if not documents:
        raise ValueError(
            "No documents available and no existing vector store. "
            "Please add documents to the data/sample_docs folder first."
        )

    vectorstore = create_vectorstore(documents, save_path)
    return vectorstore


if __name__ == "__main__":
    # Run this file directly to try it out on the sample documents
    from dotenv import load_dotenv
    from document_loader import load_and_split_directory

    backend_dir = Path(__file__).resolve().parent.parent
    # override=True: the .env key wins over an OPENAI_API_KEY already set in the shell
    load_dotenv(backend_dir / ".env", override=True)

    chunks = load_and_split_directory(str(backend_dir / "data" / "sample_docs"))
    vectorstore = get_or_create_vectorstore(chunks, str(backend_dir / "data" / "vectorstore"))

    print(f"\nVector store ready with {vectorstore.index.ntotal} vectors")

    # Quick check: find the chunks closest in meaning to a question
    question = "How many days of annual leave do employees get?"
    results = vectorstore.similarity_search_with_score(question, k=3)

    print(f"\nQuestion: {question}\n")
    for i, (doc, score) in enumerate(results, start=1):
        print(f"--- Match {i} (distance {score:.4f}, lower = closer) ---")
        print(f"Source:  {doc.metadata['source']}")
        print(f"Content: {doc.page_content[:250]}...\n")
