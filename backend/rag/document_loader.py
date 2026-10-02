"""
document_loader.py - Handles loading and splitting documents

WHAT THIS FILE DOES:
    1. Reads documents from files (.txt, .pdf)
    2. Splits them into smaller chunks (because LLMs have token limits)
    3. Returns these chunks ready to be embedded into vectors

THINK OF IT LIKE:
    Imagine you have a big encyclopedia. Before you can index it,
    you cut it into individual pages or sections. That's what this does.
"""

import os
from typing import List
from pathlib import Path

# LangChain document loaders - these know how to read different file types
from langchain_community.document_loaders import TextLoader, PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document


def load_single_document(file_path: str) -> List[Document]:
    """
    Load a single document from a file path.

    Supports .txt and .pdf files.

    Args:
        file_path: Path to the file on disk

    Returns:
        List of Document objects (one document may become multiple if it's a PDF)
    """
    file_path = str(file_path)  # Convert Path objects to string
    ext = Path(file_path).suffix.lower()

    print(f"Loading document: {file_path}")

    if ext == '.txt':
        # TextLoader reads plain text files
        loader = TextLoader(file_path, encoding='utf-8')

    elif ext == '.pdf':
        # PyPDFLoader reads PDF files, one Document per page
        loader = PyPDFLoader(file_path)

    elif ext == '.md':
        # Markdown files are also plain text
        loader = TextLoader(file_path, encoding='utf-8')

    else:
        raise ValueError(f"Unsupported file type: {ext}")

    documents = loader.load()

    # Add the filename to metadata so we know where each chunk came from
    source_name = Path(file_path).name
    for doc in documents:
        doc.metadata['source'] = source_name
        doc.metadata['file_path'] = file_path

    print(f"  Loaded {len(documents)} page(s) from {source_name}")
    return documents

def load_documents_from_directory(directory_path: str) -> List[Document]:
    """
    Load ALL documents from a directory.

    This is used during startup to load the sample documents,
    and also when you add new documents to the knowledge base.

    Args:
        directory_path: Path to folder containing documents

    Returns:
        All documents from all supported files in the directory
    """
    all_documents = []
    directory = Path(directory_path)

    # Check if directory exists
    if not directory.exists():
        print(f"Warning: Directory {directory_path} does not exist")
        return []

    # Find all supported files
    supported_extensions = ['.txt', '.pdf', '.md']
    files_found = []

    for ext in supported_extensions:
        files_found.extend(directory.glob(f"*{ext}"))

    if not files_found:
        print(f"No supported documents found in {directory_path}")
        return []

    print(f"Found {len(files_found)} document(s) to load...")

    # Load each file
    for file_path in files_found:
        try:
            docs = load_single_document(str(file_path))
            all_documents.extend(docs)
        except Exception as e:
            print(f"Error loading {file_path}: {e}")
            continue  # Skip problematic files and continue with others

    print(f"Total: Loaded {len(all_documents)} page(s) from {len(files_found)} file(s)")
    return all_documents


def split_documents(documents: List[Document], chunk_size: int = 1000, chunk_overlap: int = 200) -> List[Document]:
    """
    Split large documents into smaller chunks.

    WHY DO WE SPLIT DOCUMENTS?
    - LLMs have limits on how much text they can process at once
    - Smaller chunks = more precise retrieval
    - We can find the EXACT section that answers the question

    HOW DOES SPLITTING WORK?
    - chunk_size=1000: Each chunk is ~1000 characters
    - chunk_overlap=200: Chunks overlap by 200 characters so we don't
      lose context at chunk boundaries

    Example:
        Original: "...The company policy is ABC. Employees must XYZ..."
        Chunk 1:  "...The company policy is ABC. Employees..."  (1000 chars)
        Chunk 2:  "...Employees must XYZ..."                    (1000 chars, overlapping 200)

    Args:
        documents: List of Document objects
        chunk_size: Maximum characters per chunk
        chunk_overlap: How many characters chunks share at boundaries

    Returns:
        Many smaller Document chunks
    """
    # RecursiveCharacterTextSplitter is the recommended splitter
    # It tries to split on: paragraphs → sentences → words → characters
    # This preserves meaning better than just cutting at fixed lengths
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,  # Use character count
        separators=["\n\n", "\n", " ", ""]  # Try these separators in order
    )

    chunks = text_splitter.split_documents(documents)

    print(f"Split {len(documents)} document(s) into {len(chunks)} chunks")
    print(f"Settings: chunk_size={chunk_size}, chunk_overlap={chunk_overlap}")

    return chunks


def load_and_split_document(file_path: str) -> List[Document]:
    """
    Convenience function: Load a single file AND split it into chunks.

    This is what the API calls when a user uploads a new document.

    Args:
        file_path: Path to the document file

    Returns:
        List of Document chunks ready for embedding
    """
    # Step 1: Load the raw document
    documents = load_single_document(file_path)

    # Step 2: Split into chunks
    chunks = split_documents(documents)

    return chunks


def load_and_split_directory(directory_path: str) -> List[Document]:
    """
    Convenience function: Load ALL files from a directory AND split them.

    This is called at startup to load the initial knowledge base.

    Args:
        directory_path: Path to the documents folder

    Returns:
        All document chunks from all files in the directory
    """
    # Step 1: Load all documents from the directory
    documents = load_documents_from_directory(directory_path)

    if not documents:
        return []

    # Step 2: Split into chunks
    chunks = split_documents(documents)

    return chunks


if __name__ == "__main__":
    # Run this file directly to try it out on the sample documents
    sample_dir = Path(__file__).resolve().parent.parent / "data" / "sample_docs"

    chunks = load_and_split_directory(str(sample_dir))

    print(f"\nGot {len(chunks)} chunks in total\n")
    for i, chunk in enumerate(chunks[:3], start=1):
        print(f"--- Chunk {i} ---")
        print(f"Metadata: {chunk.metadata}")
        print(f"Length:   {len(chunk.page_content)} characters")
        print(f"Content:\n{chunk.page_content[:300]}...\n")
