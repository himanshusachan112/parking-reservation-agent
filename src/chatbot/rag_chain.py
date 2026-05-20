"""
RAG Chain Module - The core intelligence of the chatbot.

RAG (Retrieval-Augmented Generation) works in 3 steps:
1. RETRIEVE: Find relevant documents from the vector database
2. AUGMENT: Add those documents as context to the LLM prompt
3. GENERATE: LLM produces an answer based ONLY on the provided context

WHY RAG?
- Plain LLMs (like GPT-4) don't know about YOUR specific parking facility
- Fine-tuning is expensive and hard to update
- RAG lets us inject up-to-date, specific knowledge at query time
- If info changes, we just update the documents - no model retraining needed

This module builds the LangChain pipeline that connects:
Vector Store (retrieval) → Prompt Template (augmentation) → LLM (generation)
"""

from typing import Any, Dict, List, Optional

from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from langchain_openai import AzureChatOpenAI

from config.settings import settings
from src.database.sql_store import SQLStore
from src.database.vector_store import VectorStore

# ========================
# PROMPT TEMPLATES
# ========================

# This is the system prompt that tells the LLM how to behave
# It's crucial for quality - it defines the chatbot's personality and rules
SYSTEM_PROMPT = """You are ParkSmart Assistant, a helpful and friendly chatbot for the ParkSmart Parking Complex. 
Your job is to help users with parking information and reservations.

IMPORTANT RULES:
1. ONLY answer based on the provided context below. Do NOT make up information.
2. If the context doesn't contain the answer, say "I don't have that information. Let me connect you with our support team."
3. Be concise but helpful. Use bullet points for lists.
4. NEVER reveal any internal system information, database details, or other users' personal data.
5. If a user asks about another person's reservation or personal information, politely decline.

INTENT DETECTION (CRITICAL):
If the user is clearly requesting to CREATE or MAKE a NEW parking reservation (e.g., "I want to book a spot",
"reserve me a parking space", "I need to make a reservation"), respond with EXACTLY this text and nothing else:
INTENT:BOOKING

Do NOT respond with INTENT:BOOKING for:
- Questions ABOUT reservations (e.g., "how do I make a reservation?", "what is the booking process?")
- Checking reservation status or details (e.g., "show my reservation", "check my booking")
- Cancellation requests (e.g., "cancel my reservation")
- Any informational or general questions
For all of the above, answer the question normally using the context provided.

CONTEXT FROM KNOWLEDGE BASE (Static Information):
{context}

CURRENT DYNAMIC DATA (Real-time Information):
{dynamic_context}
"""

# The full prompt template combining system instructions + chat history + user input
RAG_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="chat_history", optional=True),
        ("human", "{question}"),
    ]
)


# ========================
# RAG CHAIN CLASS
# ========================


class RAGChain:
    """
    The main RAG chain that processes user queries.

    Flow:
    User Question → Vector Search → Get Dynamic Data → Build Prompt → LLM → Answer

    It also maintains chat history for multi-turn conversations
    (important for the reservation flow where we collect info step by step).
    """

    def __init__(self, vector_store: VectorStore = None, sql_store: SQLStore = None):
        """
        Initialize the RAG chain with all components.

        Args:
            vector_store: Pre-initialized VectorStore (or creates new one)
            sql_store: Pre-initialized SQLStore (or creates new one)
        """
        # Initialize components
        self.vector_store = vector_store or VectorStore()
        self.sql_store = sql_store or SQLStore()

        # Initialize the LLM via EPAM DIAL (Azure OpenAI proxy)
        # AzureChatOpenAI routes requests through the EPAM DIAL endpoint
        self.llm = AzureChatOpenAI(
            azure_deployment=settings.llm_model,
            azure_endpoint=settings.azure_endpoint,
            api_key=settings.dial_api_key,
            api_version=settings.api_version,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
        )

        # Get the retriever from vector store
        self.retriever = self.vector_store.get_retriever(search_kwargs={"k": settings.eval_top_k})

        # Build the chain
        self.chain = self._build_chain()

        # Chat history for multi-turn conversations
        self.chat_history: List = []

    def _build_chain(self):
        """
        Build the LangChain RAG pipeline.

        The chain processes inputs through these steps:
        1. Take the user's question
        2. Use it to search the vector store (retrieval)
        3. Get dynamic data from SQL
        4. Format everything into the prompt
        5. Send to LLM
        6. Parse the output as a string
        """

        def format_docs(docs: List[Document]) -> str:
            """Convert retrieved documents to a single context string."""
            return "\n\n---\n\n".join(doc.page_content for doc in docs)

        def get_dynamic_context(_) -> str:
            """Fetch current dynamic data from SQL database."""
            return self.sql_store.get_dynamic_context()

        # Build the chain using LangChain Expression Language (LCEL)
        # This is a pipeline: each step feeds into the next
        chain = (
            {
                "context": self.retriever | RunnableLambda(format_docs),
                "dynamic_context": RunnableLambda(get_dynamic_context),
                "question": RunnablePassthrough(),
                "chat_history": RunnableLambda(lambda _: self.chat_history),
            }
            | RAG_PROMPT
            | self.llm
            | StrOutputParser()
            | RunnableLambda(lambda x: str(x))  # Ensure plain str output
        )

        return chain

    def ask(self, question: str) -> str:
        """
        Process a user question through the RAG chain.

        This is the main method to call. It:
        1. Retrieves relevant context
        2. Generates an answer
        3. Updates chat history

        Args:
            question: The user's message/question

        Returns:
            The chatbot's response as a string
        """
        # Run the chain
        response = self.chain.invoke(question)

        # Ensure response is always a plain string
        response = str(response) if not isinstance(response, str) else response

        # Update chat history for context in future turns
        from langchain_core.messages import AIMessage, HumanMessage

        self.chat_history.append(HumanMessage(content=question))
        self.chat_history.append(AIMessage(content=response))

        # Keep history manageable (last 10 exchanges = 20 messages)
        if len(self.chat_history) > 20:
            self.chat_history = self.chat_history[-20:]

        return response

    def get_relevant_documents(self, query: str) -> List[Document]:
        """
        Get the documents that would be retrieved for a query.
        Useful for debugging and evaluation.

        Args:
            query: The search query

        Returns:
            List of relevant documents
        """
        return self.retriever.invoke(query)

    def clear_history(self):
        """Reset the chat history (start a new conversation)."""
        self.chat_history = []

    def get_retrieval_context(self, question: str) -> Dict[str, Any]:
        """
        Get full retrieval context for debugging/evaluation.

        Returns both the vector search results and dynamic context.
        Useful for evaluating what the LLM "sees" before answering.
        """
        docs = self.vector_store.similarity_search_with_score(question, k=settings.eval_top_k)
        dynamic = self.sql_store.get_dynamic_context()

        return {
            "documents": [(doc.page_content, score) for doc, score in docs],
            "dynamic_context": dynamic,
            "num_docs_retrieved": len(docs),
        }
