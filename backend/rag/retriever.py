"""
retriever.py - Handles searching the vector store for relevant documents

WHAT IS RETRIEVAL?
    Given a user's question, retrieval finds the most relevant document
    chunks from our vector store.

    Example:
        User asks: "How many days of annual leave do I get?"
        Retriever searches vectors and finds:
        → "Annual Leave: 0-2 years: 15 days, 2-5 years: 20 days..."
        → "Leave Policy: All full-time employees receive..."

HOW DOES IT WORK?
    1. Convert the query to a vector (embedding)
    2. Find the vectors in FAISS that are most similar
    3. Return those documents
"""

from typing import List, Dict, Any
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document


class DocumentRetriever:
    """
    A class that wraps FAISS to provide easy document retrieval.

    Think of this as your smart search engine for internal documents.
    """

    def __init__(self, vectorstore: FAISS, top_k: int = 4):
        """
        Initialize the retriever.

        Args:
            vectorstore: The FAISS vector store containing embedded documents
            top_k: How many documents to retrieve for each query
                   (4 is a good default - enough context without overwhelming the LLM)
        """
        self.vectorstore = vectorstore
        self.top_k = top_k

        print(f"Retriever initialized. Will return top {top_k} documents per query.")

    def retrieve(self, query: str) -> List[Document]:
        """
        Find the most relevant documents for a given query.

        This is the main search function.

        Args:
            query: The user's question

        Returns:
            List of relevant Document objects
        """
        print(f"\nSearching for: '{query}'")

        # similarity_search converts query to vector and finds closest matches
        # This is a single API call to OpenAI (for the query embedding)
        documents = self.vectorstore.similarity_search(
            query=query,
            k=self.top_k
        )

        print(f"Found {len(documents)} relevant document chunks")

        # Print what we found (helpful for debugging)
        for i, doc in enumerate(documents, 1):
            source = doc.metadata.get('source', 'Unknown')
            preview = doc.page_content[:100].replace('\n', ' ')
            print(f"  {i}. [{source}] {preview}...")

        return documents

    def retrieve_with_scores(self, query: str) -> List[tuple]:
        """
        Retrieve documents WITH their similarity scores.

        The score is a distance (FAISS default: squared L2), so LOWER = more
        similar/relevant. 0 means identical; there is no fixed upper limit
        (values above 1 are normal for weak matches).
        This helps you understand HOW relevant each result is.

        Args:
            query: The user's question

        Returns:
            List of (Document, score) tuples
        """
        docs_with_scores = self.vectorstore.similarity_search_with_score(
            query=query,
            k=self.top_k
        )

        print(f"\nRetrieved {len(docs_with_scores)} documents with scores:")
        for doc, score in docs_with_scores:
            source = doc.metadata.get('source', 'Unknown')
            print(f"  Score: {score:.4f} | Source: {source}")

        return docs_with_scores

    def format_docs_for_llm(self, documents: List[Document]) -> str:
        """
        Format retrieved documents into a single string for the LLM.

        The LLM needs all the context in a readable format so it can
        generate an accurate answer.

        Example output:
            [Source: company_policy.txt]
            Annual leave policy: 15 days for...

            [Source: employee_handbook.txt]
            Leave requests should be submitted...

        Args:
            documents: List of retrieved Document objects

        Returns:
            Formatted string of all document contents
        """
        if not documents:
            return "No relevant documents found."

        formatted_parts = []

        for i, doc in enumerate(documents, 1):
            source = doc.metadata.get('source', 'Unknown Source')
            content = doc.page_content.strip()

            formatted_part = f"[Document {i} - Source: {source}]\n{content}"
            formatted_parts.append(formatted_part)

        # Join all documents with separator
        return "\n\n---\n\n".join(formatted_parts)

    def extract_citations(self, documents: List[Document]) -> List[Dict[str, Any]]:
        """
        Extract citation information from retrieved documents.

        Citations tell the user WHERE the answer came from.
        This is critical for an enterprise knowledge system -
        employees need to verify information in the original documents.

        Args:
            documents: List of retrieved Document objects

        Returns:
            List of citation dictionaries with source info and preview text
        """
        citations = []
        seen_sources = set()  # Track sources to avoid duplicate citations

        for doc in documents:
            source = doc.metadata.get('source', 'Unknown Source')

            # Create a citation entry
            citation = {
                "source": source,
                "preview": doc.page_content[:200].strip().replace('\n', ' '),
                "full_text": doc.page_content.strip()
            }

            citations.append(citation)

        return citations


if __name__ == "__main__":
    # Run this file directly to try it out on the saved vector store
    from pathlib import Path
    from dotenv import load_dotenv
    from embeddings import load_vectorstore

    backend_dir = Path(__file__).resolve().parent.parent
    # override=True: the .env key wins over an OPENAI_API_KEY already set in the shell
    load_dotenv(backend_dir / ".env", override=True)

    vectorstore = load_vectorstore(str(backend_dir / "data" / "vectorstore"))
    retriever = DocumentRetriever(vectorstore, top_k=4)

    question = "How many days of annual leave do employees get?"

    # 1. retrieve: the plain search
    documents = retriever.retrieve(question)

    # 2. retrieve_with_scores: same search, plus a score for each match
    retriever.retrieve_with_scores(question)

    # 3. format_docs_for_llm: the text block that gets sent to the LLM
    context = retriever.format_docs_for_llm(documents)
    print("\n===== Context for the LLM (first 800 characters) =====")
    print(context[:800] + "...")

    # 4. extract_citations: the "sources" list shown to the user
    citations = retriever.extract_citations(documents)
    print(f"\n===== {len(citations)} citations =====")
    for i, c in enumerate(citations, start=1):
        print(f"{i}. {c['source']}: {c['preview'][:120]}...")
