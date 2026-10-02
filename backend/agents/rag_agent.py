"""
rag_agent.py - The RAG (Retrieval-Augmented Generation) Agent

WHAT IS RAG?
    RAG = Retrieval-Augmented Generation

    It's a technique where BEFORE generating an answer, you first:
    1. RETRIEVE relevant information from your knowledge base
    2. AUGMENT the LLM prompt with this retrieved information
    3. GENERATE an answer based on the retrieved context

    WHY IS THIS POWERFUL?
    - The LLM uses your actual company documents, not just training data
    - Answers are grounded in real, current information
    - Reduces "hallucinations" (LLM making things up)
    - You can cite sources!

FLOW:
    User Query → Retrieve Documents → Build Prompt → LLM → Answer
"""

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from backend.rag.retriever import DocumentRetriever


def create_rag_node(llm: ChatOpenAI, retriever: DocumentRetriever):
    """
    Create and return the RAG agent node function.

    Args:
        llm: The language model for generating answers
        retriever: The document retriever for finding relevant docs

    Returns:
        A function that can be used as a LangGraph node
    """

    # This prompt is carefully designed to:
    # 1. Ground the LLM in the retrieved documents
    # 2. Ask it to be honest when information isn't available
    # 3. Tell it to cite sources
    rag_prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a helpful enterprise knowledge assistant for employees.

Your job is to answer employee questions using the provided company documents.

INSTRUCTIONS:
1. Answer ONLY based on the provided context/documents
2. If the information is not in the context, say: "I couldn't find this information in our company documents. Please contact HR at hr@company.com for accurate information."
3. Be concise and clear
4. Use bullet points for lists when appropriate
5. Always maintain a professional and helpful tone
6. Do not make up information that is not in the documents

CONTEXT (Retrieved Company Documents):
{context}"""),
        ("human", "Employee Question: {query}")
    ])

    # Build the chain
    rag_chain = rag_prompt | llm

    def rag_node(state: dict) -> dict:
        """
        The RAG agent node function.

        This function:
        1. Takes the query from state
        2. Retrieves relevant documents
        3. Generates an answer using those documents
        4. Stores the answer and retrieved docs in state

        Args:
            state: Current agent state

        Returns:
            Updated state with 'answer' and 'retrieved_docs' filled in
        """
        query = state["query"]
        print(f"\n[RAG Agent] Processing query: '{query}'")

        try:
            # Step 1: Retrieve relevant documents
            print("[RAG Agent] Retrieving relevant documents...")
            retrieved_docs = retriever.retrieve(query)

            if not retrieved_docs:
                print("[RAG Agent] No documents retrieved")
                return {
                    "answer": (
                        "I couldn't find any relevant information in the company documents. "
                        "Please contact HR directly for assistance."
                    ),
                    "retrieved_docs": [],
                }

            # Step 2: Format documents into a single context string
            context = retriever.format_docs_for_llm(retrieved_docs)

            print(f"[RAG Agent] Context prepared from {len(retrieved_docs)} documents")
            print(f"[RAG Agent] Generating answer with LLM...")

            # Step 3: Generate answer using LLM with context
            response = rag_chain.invoke({
                "context": context,
                "query": query
            })

            answer = response.content
            print(f"[RAG Agent] Answer generated ({len(answer)} characters)")

            # Step 4: Return updated state
            return {
                "answer": answer,
                "retrieved_docs": retrieved_docs,
            }

        except Exception as e:
            print(f"[RAG Agent] Error: {e}")
            return {
                "answer": f"I encountered an error while searching the documents: {str(e)}",
                "retrieved_docs": [],
            }

    return rag_node


def create_general_node(llm: ChatOpenAI):
    """
    Create the general knowledge node for non-document queries.

    This handles questions that don't need document lookup.
    The LLM answers from its general training knowledge.

    Args:
        llm: The language model

    Returns:
        A function that can be used as a LangGraph node
    """

    general_prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a helpful enterprise assistant.

This question doesn't seem to require looking up company-specific documents.
Answer it helpfully using your general knowledge.

If the question DOES seem company-specific (about leave, benefits, policies, etc.),
mention that you couldn't find company documents and suggest contacting HR."""),
        ("human", "{query}")
    ])

    general_chain = general_prompt | llm

    def general_node(state: dict) -> dict:
        """
        General knowledge node - answers without document retrieval.

        Args:
            state: Current agent state

        Returns:
            Updated state with 'answer' filled in
        """
        query = state["query"]
        print(f"\n[General Agent] Handling general query: '{query}'")

        try:
            response = general_chain.invoke({"query": query})
            answer = response.content

            print(f"[General Agent] Answer generated ({len(answer)} characters)")

            return {
                "answer": answer,
                "retrieved_docs": [],  # No documents for general queries
            }

        except Exception as e:
            print(f"[General Agent] Error: {e}")
            return {
                "answer": f"I encountered an error: {str(e)}",
                "retrieved_docs": [],
            }

    return general_node


if __name__ == "__main__":
    # Run from the project root with: python -m backend.agents.rag_agent
    # (-m is needed because this file imports "backend.rag.retriever")
    import os
    from pathlib import Path
    from dotenv import load_dotenv
    from backend.rag.embeddings import load_vectorstore

    backend_dir = Path(__file__).resolve().parent.parent
    # override=True: the .env key wins over an OPENAI_API_KEY already set in the shell
    load_dotenv(backend_dir / ".env", override=True)

    llm = ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"), temperature=0)
    vectorstore = load_vectorstore(str(backend_dir / "data" / "vectorstore"))
    retriever = DocumentRetriever(vectorstore, top_k=4)

    rag_node = create_rag_node(llm, retriever)
    general_node = create_general_node(llm)

    # 1. RAG node: a company question, answered from the documents
    result = rag_node({"query": "How many days of annual leave do employees get?"})
    print("\n===== RAG node output =====")
    print(f"answer: {result['answer']}")
    print(f"retrieved_docs: {len(result['retrieved_docs'])} documents")
    for doc in result["retrieved_docs"]:
        print(f"  - {doc.metadata.get('source', 'unknown')}")

    # 2. General node: a general question, answered without documents
    result = general_node({"query": "What is the capital of France?"})
    print("\n===== General node output =====")
    print(f"answer: {result['answer']}")
    print(f"retrieved_docs: {result['retrieved_docs']}")
