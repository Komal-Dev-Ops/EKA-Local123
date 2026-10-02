"""
router_agent.py - The Router Agent

WHAT DOES THE ROUTER DO?
    The router is like a receptionist at a company.
    When you ask a question, it decides:
    - "This needs to be looked up in our documents" → route to RAG Agent
    - "This is a general question I can answer directly" → route to General Agent

WHY DO WE NEED A ROUTER?
    Not all questions need document lookup. For example:
    - "What is 2+2?" → General question, no documents needed
    - "How many leave days do I get?" → Needs our company documents
    - "What is the capital of France?" → General question
    - "What is our work from home policy?" → Needs our company documents

    By routing correctly, we:
    1. Save API costs (don't do retrieval when not needed)
    2. Get better answers (general questions don't need document context)
    3. Process queries faster
"""

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate


def create_router_node(llm: ChatOpenAI):
    """
    Create and return the router node function.

    We use a 'factory pattern' here - this function CREATES the node function.
    The benefit is that we can pass in the LLM and the returned function
    will remember it (this is called a 'closure' in Python).

    Args:
        llm: The language model to use for routing decisions

    Returns:
        A function that can be used as a LangGraph node
    """

    # This is the prompt we send to the LLM to make routing decisions
    # We give it clear rules and examples so it routes accurately
    router_prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a query router for an enterprise knowledge assistant.

Your job is to classify user queries into one of two categories:

1. "rag" - The query is about company-specific information that requires looking up internal documents.
   Use this for questions about:
   - Company policies (leave, expense, WFH, performance, etc.)
   - Employee benefits (health insurance, 401k, stock options, etc.)
   - HR procedures and guidelines
   - Office facilities and resources
   - Onboarding and career development
   - Payroll and compensation
   - IT systems and access

2. "general" - The query is a general knowledge question that does NOT need company documents.
   Use this for:
   - General factual questions
   - Programming or technical help
   - Math calculations
   - Common knowledge questions

Respond with ONLY one word: either "rag" or "general"
Do not explain your choice. Just respond with the single word."""),
        ("human", "Query: {query}")
    ])

    # Create the chain: prompt → LLM → extract text
    router_chain = router_prompt | llm

    def router_node(state: dict) -> dict:
        """
        The actual router node function that LangGraph will call.

        This function:
        1. Takes the current state (which has the user's query)
        2. Calls the LLM to decide the route
        3. Returns an updated state with the routing decision

        Args:
            state: Current agent state dictionary

        Returns:
            Updated state with 'route' key set to "rag" or "general"
        """
        query = state["query"]
        print(f"\n[Router Agent] Classifying query: '{query}'")

        try:
            # Ask the LLM to classify the query
            response = router_chain.invoke({"query": query})

            # Extract the text from the response
            route = response.content.strip().lower()

            # Validate the response - it should be "rag" or "general"
            if route not in ["rag", "general"]:
                print(f"[Router Agent] Unexpected route: '{route}', defaulting to 'rag'")
                route = "rag"  # Default to RAG when uncertain

            print(f"[Router Agent] Decision: Route to '{route}' agent")

            # Return the updated state
            return {"route": route}

        except Exception as e:
            print(f"[Router Agent] Error during routing: {e}")
            # On error, default to RAG (safer - tries to use documents)
            return {"route": "rag"}

    return router_node


if __name__ == "__main__":
    # Run this file directly to try the router on a few sample questions
    import os
    from pathlib import Path
    from dotenv import load_dotenv

    backend_dir = Path(__file__).resolve().parent.parent
    # override=True: the .env key wins over an OPENAI_API_KEY already set in the shell
    load_dotenv(backend_dir / ".env", override=True)

    llm = ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"), temperature=0)
    router_node = create_router_node(llm)

    sample_queries = [
        "How many days of annual leave do employees get?",  # expect: rag
        "What is our work from home policy?",               # expect: rag
        "What is the capital of France?",                   # expect: general
        "Write a Python function to reverse a string",      # expect: general
    ]

    for query in sample_queries:
        # LangGraph passes the whole state dict; the router only reads "query"
        result = router_node({"query": query})
        print(f"Output: {result}")
