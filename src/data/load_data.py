"""
Data loading utilities for the Parking Space Reservation Chatbot.

This module handles:
1. Loading static text data and splitting it into chunks for the vector store
2. Initializing the SQL database with dynamic data (prices, availability, hours)

WHY SPLIT DATA?
- Static data (location, rules, facilities) rarely changes → vector DB is ideal
  because it enables semantic search (finding relevant info by meaning)
- Dynamic data (prices, availability, working hours) changes frequently → SQL DB
  is better because it allows precise queries and easy updates
"""

import os
from pathlib import Path

from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Path to the static parking info file
DATA_DIR = Path(__file__).parent
PARKING_INFO_FILE = DATA_DIR / "parking_info.txt"


def load_and_split_documents(file_path: str = None, chunk_size: int = 500, chunk_overlap: int = 50):
    """
    Load a text file and split it into smaller chunks for vector storage.

    WHY CHUNKING?
    - LLMs have token limits, so we can't feed entire documents
    - Smaller chunks allow more precise retrieval (find the exact relevant piece)
    - Overlap ensures we don't lose context at chunk boundaries

    Args:
        file_path: Path to the text file to load
        chunk_size: Maximum characters per chunk (500 is a good balance)
        chunk_overlap: Characters to overlap between chunks (prevents context loss)

    Returns:
        List of Document objects, each containing a chunk of text + metadata
    """
    if file_path is None:
        file_path = str(PARKING_INFO_FILE)

    # Load the raw text file
    loader = TextLoader(file_path, encoding="utf-8")
    documents = loader.load()

    # Split into chunks using RecursiveCharacterTextSplitter
    # This splitter tries to split at natural boundaries (paragraphs, sentences)
    # before resorting to character-level splitting
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n## ", "\n\n", "\n", ". ", " ", ""],
        length_function=len,
    )

    chunks = text_splitter.split_documents(documents)

    # Add metadata to each chunk for traceability
    for i, chunk in enumerate(chunks):
        chunk.metadata["chunk_id"] = i
        chunk.metadata["source"] = "parking_info"

    return chunks


def get_sample_questions():
    """
    Returns sample questions for testing and evaluation.
    These represent typical user queries the chatbot should handle.
    """
    return [
        "What are the working hours of the parking?",
        "How much does standard parking cost?",
        "Where is the parking located?",
        "Do you have electric vehicle charging?",
        "How do I make a reservation?",
        "What are the payment methods?",
        "Is there disabled parking available?",
        "What is the maximum vehicle size allowed?",
        "Can I cancel my reservation?",
        "Is there overnight parking available?",
    ]


def get_ground_truth_answers():
    """
    Returns expected answers for evaluation metrics.
    Paired with get_sample_questions() for accuracy measurement.
    """
    return [
        "The parking is open Monday to Friday 6:00 AM to 11:00 PM, Saturday 7:00 AM to 11:00 PM, and Sunday 8:00 AM to 10:00 PM.",
        "Standard parking costs $3 per hour, $15 for a full day, and $60 per week or $200 per month.",
        "ParkSmart is located at 123 Main Street, Downtown Business District, City Center.",
        "Yes, there are 40 electric vehicle spaces on Floor 2 with Level 2 charging stations and Tesla Supercharger compatibility.",
        "To reserve, provide your name, vehicle registration number, and desired reservation period. An administrator will review and confirm.",
        "Payment methods include Credit/Debit Cards, Mobile payments (Apple Pay, Google Pay), monthly invoicing for corporate accounts, and cash at the exit booth.",
        "Yes, there are 20 disabled parking spaces on Floor 1 closest to elevators with extra-wide spaces for wheelchair accessibility.",
        "Standard spaces allow up to 5.0m x 2.0m x 1.8m and large vehicle spaces allow up to 6.0m x 2.5m x 2.2m.",
        "Cancellations are free up to 2 hours before start time. Late cancellations incur a 50% fee.",
        "Yes, overnight parking is available. The facility operates during posted hours but overnight arrangements can be made.",
    ]
