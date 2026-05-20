"""
Main Entry Point - Parking Space Reservation Chatbot.

This script:
1. Initializes all components (vector DB, SQL DB, RAG chain)
2. Loads the knowledge base into the vector store
3. Starts an interactive chat session in the terminal

Usage:
    python main.py              # Start the chatbot
    python main.py --setup      # Setup databases only (first run)
    python main.py --evaluate   # Run RAG evaluation

HOW TO RUN:
1. Copy .env.example to .env and add your DIAL_API_KEY
2. Install dependencies: pip install -r requirements.txt
3. Download spacy model: python -m spacy download en_core_web_lg
4. Run: python main.py --setup  (first time only)
5. Run: python main.py          (start chatting)
"""

import sys
import os
import argparse

# Add project root to path so imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from config.settings import settings
from src.database.vector_store import VectorStore
from src.database.sql_store import SQLStore
from src.data.load_data import load_and_split_documents
from src.chatbot.chatbot import ParkingChatbot
from src.evaluation.evaluator import RAGEvaluator


def setup_databases():
    """
    Initialize and populate the databases.
    Run this once when setting up the system for the first time.
    
    Steps:
    1. Load parking info text file → Split into chunks
    2. Create vector store → Add chunks as embeddings
    3. Create SQL database → Populate with default dynamic data
    """
    print("=" * 50)
    print("  SETTING UP PARKING CHATBOT DATABASES")
    print("=" * 50)

    # Step 1: Load and chunk the static parking information
    print("\n[1/3] Loading and chunking parking information...")
    documents = load_and_split_documents()
    print(f"      Created {len(documents)} text chunks from parking_info.txt")

    # Step 2: Initialize vector store and add documents
    print("\n[2/3] Initializing vector database (Pinecone)...")
    vector_store = VectorStore()

    # Check if already populated
    existing_count = vector_store.get_collection_count()
    if existing_count > 0:
        print(f"      Vector store already has {existing_count} documents.")
        user_input = input("      Re-index? (y/n): ").strip().lower()
        if user_input == "y":
            vector_store.clear()
            vector_store.add_documents(documents)
        else:
            print("      Skipping re-indexing.")
    else:
        vector_store.add_documents(documents)

    # Step 3: Initialize SQL database
    print("\n[3/3] Initializing SQL database (dynamic data)...")
    sql_store = SQLStore()
    sql_store.initialize_default_data()

    print("\n" + "=" * 50)
    print("  ✓ SETUP COMPLETE!")
    print("=" * 50)
    print("\nYou can now run: python main.py")


def run_evaluation():
    """
    Run the RAG evaluation suite and print the report.
    
    This measures:
    - Response latency (how fast)
    - Retrieval precision and recall (how accurate)
    - Answer relevance (how good)
    """
    print("=" * 50)
    print("  RUNNING RAG EVALUATION")
    print("=" * 50)

    # Initialize the chatbot components
    vector_store = VectorStore()
    sql_store = SQLStore()

    from src.chatbot.rag_chain import RAGChain
    rag_chain = RAGChain(vector_store=vector_store, sql_store=sql_store)

    # Run evaluation
    evaluator = RAGEvaluator(rag_chain=rag_chain)

    print("\nRunning accuracy evaluation...")
    report = evaluator.run_evaluation()
    print(report.summary())

    # Print individual results
    print("\n--- DETAILED RESULTS ---")
    for i, result in enumerate(report.individual_results, 1):
        print(f"\nQ{i}: {result.question}")
        print(f"    Generated: {result.generated_answer[:100]}...")
        print(f"    Precision: {result.precision_at_k:.3f} | Recall: {result.recall_at_k:.3f}")
        print(f"    Relevance: {result.answer_relevance_score:.3f}")
        print(f"    Time: {result.total_time_ms:.1f}ms")

    # Run latency test
    print("\n\nRunning latency test (5 queries)...")
    latency = evaluator.run_latency_test(num_queries=5)
    print(f"\n  Min: {latency['min_latency_ms']:.1f}ms")
    print(f"  Max: {latency['max_latency_ms']:.1f}ms")
    print(f"  Avg: {latency['avg_latency_ms']:.1f}ms")
    print(f"  P95: {latency['p95_latency_ms']:.1f}ms")


def run_chatbot():
    """
    Start the interactive chatbot in the terminal.
    
    The chatbot will:
    - Answer questions about ParkSmart parking
    - Guide users through the reservation process
    - Protect sensitive data via guardrails
    """
    print("=" * 50)
    print("  🚗 PARKSMART PARKING ASSISTANT")
    print("=" * 50)
    print("\nHello! I'm the ParkSmart Parking Assistant.")
    print("I can help you with:")
    print("  • Parking information (location, hours, prices)")
    print("  • Space availability")
    print("  • Making a reservation")
    print("\nType 'quit' to exit, 'reset' to start a new conversation.")
    print("-" * 50)

    # Initialize the chatbot
    try:
        chatbot = ParkingChatbot()
    except Exception as e:
        print(f"\n❌ Error initializing chatbot: {e}")
        print("\nMake sure you have:")
        print("  1. Set your DIAL_API_KEY in the .env file")
        print("  2. Run 'python main.py --setup' first")
        return

    # Main chat loop
    while True:
        try:
            user_input = input("\n👤 You: ").strip()

            if not user_input:
                continue

            if user_input.lower() == "quit":
                print("\nThank you for using ParkSmart! Have a great day. 👋")
                break

            if user_input.lower() == "reset":
                chatbot.reset()
                print("\n🔄 Conversation reset. How can I help you?")
                continue

            # Get chatbot response
            response = chatbot.chat(user_input)
            print(f"\n🤖 ParkSmart: {response}")

        except KeyboardInterrupt:
            print("\n\nGoodbye! 👋")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            print("Please try again or type 'reset' to start over.")


def run_admin_panel():
    """
    Start the admin panel for reviewing reservations.

    This launches the Stage 2 admin agent — a CLI interface where
    the administrator can view pending reservations, check availability,
    and approve or reject booking requests.
    """
    from src.agents.admin_agent import run_admin_cli
    run_admin_cli()


def run_api_server():
    """
    Start the FastAPI REST API server.

    This launches the REST API that serves as the communication bridge
    between the user chatbot and the admin agent. Provides endpoints
    for submitting, reviewing, and processing reservations.

    Visit http://localhost:8000/docs for interactive Swagger documentation.
    """
    import uvicorn
    print("Starting ParkSmart REST API server...")
    print("Swagger UI: http://localhost:8000/docs")
    print("Press Ctrl+C to stop.\n")
    uvicorn.run("src.api.server:app", host="0.0.0.0", port=8000, reload=True)


def run_mcp_server():
    """
    Start the MCP (Model Context Protocol) server.

    This is the Stage 3 MCP server — a separate FastAPI service on port 8001.
    It exposes tools via the MCP protocol that agents can discover and call.

    The admin agent and REST API call this server when a reservation is approved
    to write the record to data/approved_reservations.txt.

    Visit http://localhost:8001/docs for interactive Swagger documentation.
    """
    import uvicorn
    print("Starting ParkSmart MCP Server...")
    print("MCP Swagger UI: http://localhost:8001/docs")
    print("Health Check: http://localhost:8001/mcp/health")
    print("Press Ctrl+C to stop.\n")
    uvicorn.run("src.mcp.mcp_server:mcp_app", host="0.0.0.0", port=8001, reload=True)


def run_graph_pipeline():
    """
    Run the LangGraph-orchestrated pipeline (Stage 4).

    This replaces running chatbot + admin CLI as separate programs.
    Instead, LangGraph orchestrates the entire flow in one process:

    1. USER PHASE: Chat with the bot, ask questions, make a reservation
    2. ADMIN PHASE: When a booking is submitted, switch to admin mode
       to review, approve, or reject
    3. AUTO PIPELINE: After admin decides, the graph automatically
       routes through notification → MCP recording → completion

    The graph engine handles all the routing — no manual switching needed.
    """
    from src.graph.pipeline import create_pipeline, run_user_message, run_admin_decision
    from src.graph.state import PipelinePhase

    print("=" * 60)
    print("  🚗 PARKSMART — LangGraph Orchestrated Pipeline (Stage 4)")
    print("=" * 60)
    print("\nThis mode runs the FULL pipeline in one process:")
    print("  User Chat → Booking → Admin Review → Notify → MCP Record")
    print("\nCommands:")
    print("  Type messages to chat with ParkSmart")
    print("  After a booking, you'll be switched to admin mode")
    print("  'quit' to exit, 'reset' to restart, 'status' for pipeline state")
    print("-" * 60)

    # Initialize the pipeline
    try:
        pipeline = create_pipeline()
    except Exception as e:
        print(f"\n❌ Error initializing pipeline: {e}")
        print("Make sure you have run 'python main.py --setup' first.")
        return

    state = None       # Current pipeline state
    admin_mode = False  # Are we in admin review mode?

    while True:
        try:
            if admin_mode:
                user_input = input("\n🔧 Admin: ").strip()
            else:
                user_input = input("\n👤 You: ").strip()

            if not user_input:
                continue

            if user_input.lower() == "quit":
                print("\nThank you for using ParkSmart! 👋")
                break

            if user_input.lower() == "reset":
                state = None
                admin_mode = False
                # Re-create pipeline to reset chatbot state
                pipeline = create_pipeline()
                print("\n🔄 Pipeline reset. How can I help you?")
                continue

            if user_input.lower() == "status":
                if state:
                    phase = state.get("conversation_phase", "unknown")
                    rid = state.get("reservation_id", 0)
                    decision = state.get("admin_decision", "none")
                    print(f"\n📊 Pipeline Status:")
                    print(f"   Phase: {phase}")
                    print(f"   Reservation ID: #{rid}" if rid else "   No active reservation")
                    print(f"   Admin Decision: {decision}" if decision else "   No decision yet")
                    print(f"   MCP Recorded: {state.get('mcp_recorded', False)}")
                    print(f"   Notification Sent: {state.get('notification_sent', False)}")
                else:
                    print("\n📊 No active pipeline. Start chatting!")
                continue

            if admin_mode:
                # ── ADMIN MODE: Process admin decision through the graph ──
                state = run_admin_decision(pipeline, state, user_input)
                phase = state.get("conversation_phase", "")

                # Show the result
                print(f"\n{state.get('bot_response', '')}")

                # Check if admin still needs to provide input
                if state.get("needs_admin_input", False):
                    continue

                # Pipeline completed — switch back to user mode
                if phase == PipelinePhase.COMPLETED.value:
                    admin_mode = False
                    state = None
                    print("\n" + "-" * 60)
                    print("Pipeline complete! Switching back to user chat mode.")
                    print("Type a message to continue chatting or 'quit' to exit.")
                    print("-" * 60)
                    # Re-create pipeline for fresh chatbot state
                    pipeline = create_pipeline()

            else:
                # ── USER MODE: Process user message through the graph ──
                state = run_user_message(pipeline, user_input, state)

                # Show the response
                print(f"\n🤖 ParkSmart: {state.get('bot_response', '')}")

                # Check if booking was just completed → switch to admin mode
                # The graph auto-advances: save_reservation → admin_review,
                # so the phase will be "admin_reviewing" (not "awaiting_admin")
                # when it returns. We check for both phases.
                phase = state.get("conversation_phase", "")
                if phase in [
                    PipelinePhase.AWAITING_ADMIN.value,
                    PipelinePhase.ADMIN_REVIEWING.value,
                ]:
                    rid = state.get("reservation_id", 0)
                    print("\n" + "=" * 60)
                    print(f"  📋 BOOKING #{rid} SUBMITTED — SWITCHING TO ADMIN MODE")
                    print("=" * 60)
                    print("\nYou are now the admin. Review the reservation:")
                    print("  'review'  — See detailed review with availability")
                    print("  'approve [notes]' — Approve the reservation")
                    print("  'reject [reason]' — Reject the reservation")
                    print("-" * 60)
                    admin_mode = True

                    # If the review was already auto-generated, show it
                    bot_resp = state.get("bot_response", "")
                    if "RESERVATION REVIEW" in bot_resp:
                        print(f"\n{bot_resp}")
                    else:
                        # Generate review if not already shown
                        state = run_admin_decision(pipeline, state, "review")
                        print(f"\n{state.get('bot_response', '')}")

        except KeyboardInterrupt:
            print("\n\nGoodbye! 👋")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
            print("Type 'reset' to start over or 'quit' to exit.")


def main():
    """Parse arguments and run the appropriate command."""
    parser = argparse.ArgumentParser(
        description="ParkSmart Parking Space Reservation Chatbot"
    )
    parser.add_argument(
        "--setup",
        action="store_true",
        help="Initialize databases with parking data (run once)",
    )
    parser.add_argument(
        "--evaluate",
        action="store_true",
        help="Run RAG evaluation and print performance report",
    )
    parser.add_argument(
        "--admin",
        action="store_true",
        help="Open the admin panel to review/approve reservations (Stage 2)",
    )
    parser.add_argument(
        "--server",
        action="store_true",
        help="Start the REST API server for reservation management (Stage 2)",
    )
    parser.add_argument(
        "--mcp-server",
        action="store_true",
        help="Start the MCP server for file-based reservation logging (Stage 3)",
    )
    parser.add_argument(
        "--graph",
        action="store_true",
        help="Run the LangGraph orchestrated pipeline — full flow in one process (Stage 4)",
    )

    args = parser.parse_args()

    if args.setup:
        setup_databases()
    elif args.evaluate:
        run_evaluation()
    elif args.admin:
        run_admin_panel()
    elif args.server:
        run_api_server()
    elif getattr(args, 'mcp_server', False):
        run_mcp_server()
    elif args.graph:
        run_graph_pipeline()
    else:
        run_chatbot()


if __name__ == "__main__":
    main()
