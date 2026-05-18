"""
Create Stage 4 PowerPoint Presentation — LangGraph Orchestration.

Generates a professional presentation covering:
1. Title Slide
2. Stage 4 Overview
3. Problem: Manual Orchestration
4. Solution: LangGraph StateGraph
5. GraphState Schema
6. Pipeline Architecture Diagram
7. Graph Nodes (6 nodes)
8. Conditional Edges & Routing
9. Human-in-the-Loop (Admin Node)
10. MCP Integration in the Graph
11. Unified CLI (`--graph` mode)
12. Test Results (124 tests)
13. Live Demo Summary
14. Summary & Key Takeaways
"""

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

# ── Color Palette ──
DARK_BG = RGBColor(0x1A, 0x1A, 0x2E)
ACCENT_BLUE = RGBColor(0x00, 0x96, 0xC7)
ACCENT_GREEN = RGBColor(0x2E, 0xCC, 0x71)
ACCENT_ORANGE = RGBColor(0xE6, 0x7E, 0x22)
ACCENT_RED = RGBColor(0xE7, 0x4C, 0x3C)
ACCENT_PURPLE = RGBColor(0x9B, 0x59, 0xB6)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
LIGHT_GRAY = RGBColor(0xCC, 0xCC, 0xCC)
DARK_GRAY = RGBColor(0x33, 0x33, 0x33)
CARD_BG = RGBColor(0x24, 0x24, 0x3E)


def set_slide_bg(slide, color):
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = color


def add_title_text(slide, text, left, top, width, height, font_size=28, color=WHITE, bold=True, alignment=PP_ALIGN.LEFT):
    txBox = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    tf = txBox.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = text
    p.font.size = Pt(font_size)
    p.font.color.rgb = color
    p.font.bold = bold
    p.alignment = alignment
    return txBox


def add_bullet_list(slide, items, left, top, width, height, font_size=16, color=WHITE, line_spacing=1.5):
    txBox = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    tf = txBox.text_frame
    tf.word_wrap = True
    for i, item in enumerate(items):
        if i == 0:
            p = tf.paragraphs[0]
        else:
            p = tf.add_paragraph()
        p.text = item
        p.font.size = Pt(font_size)
        p.font.color.rgb = color
        p.space_after = Pt(font_size * (line_spacing - 1) * 2)
        p.level = 0
    return txBox


def add_card(slide, left, top, width, height, title, items, title_color=ACCENT_BLUE):
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(left), Inches(top), Inches(width), Inches(height))
    shape.fill.solid()
    shape.fill.fore_color.rgb = CARD_BG
    shape.line.fill.background()

    add_title_text(slide, title, left + 0.15, top + 0.1, width - 0.3, 0.4, font_size=15, color=title_color, bold=True)
    add_bullet_list(slide, items, left + 0.15, top + 0.5, width - 0.3, height - 0.6, font_size=12, color=LIGHT_GRAY, line_spacing=1.3)


def add_divider(slide, top):
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.5), Inches(top), Inches(9), Inches(0.02))
    shape.fill.solid()
    shape.fill.fore_color.rgb = ACCENT_BLUE
    shape.line.fill.background()


def add_slide_number(slide, num, total):
    add_title_text(slide, f"{num}/{total}", 8.8, 7.1, 1, 0.3, font_size=10, color=LIGHT_GRAY, bold=False, alignment=PP_ALIGN.RIGHT)


# ════════════════════════════════════════════
# BUILD PRESENTATION
# ════════════════════════════════════════════

prs = Presentation()
prs.slide_width = Inches(10)
prs.slide_height = Inches(7.5)
TOTAL_SLIDES = 14

# ── SLIDE 1: Title ──
slide = prs.slides.add_slide(prs.slide_layouts[6])
set_slide_bg(slide, DARK_BG)
add_title_text(slide, "🚗 ParkSmart Chatbot", 0.5, 1.5, 9, 1, font_size=44, color=WHITE)
add_title_text(slide, "Stage 4: LangGraph Orchestration", 0.5, 2.5, 9, 0.8, font_size=30, color=ACCENT_BLUE)
add_divider(slide, 3.5)
add_bullet_list(slide, [
    "Unified pipeline with LangGraph StateGraph",
    "6 nodes • Conditional edges • Human-in-the-loop",
    "124 tests passing • Full end-to-end orchestration",
], 0.5, 3.8, 9, 2, font_size=18, color=LIGHT_GRAY)
add_title_text(slide, "Sanyam Sachan  |  EPAM Systems  |  May 2026", 0.5, 6.5, 9, 0.5, font_size=14, color=LIGHT_GRAY, bold=False, alignment=PP_ALIGN.CENTER)
add_slide_number(slide, 1, TOTAL_SLIDES)

# ── SLIDE 2: Stage 4 Overview ──
slide = prs.slides.add_slide(prs.slide_layouts[6])
set_slide_bg(slide, DARK_BG)
add_title_text(slide, "Stage 4 Overview", 0.5, 0.3, 9, 0.6, font_size=32, color=ACCENT_BLUE)
add_divider(slide, 0.95)
add_bullet_list(slide, [
    "🎯 Goal: Replace manually running separate programs with a single",
    "   orchestrated pipeline using LangGraph",
    "",
    "📦 What LangGraph provides:",
    "   • StateGraph — defines nodes (steps) and edges (connections)",
    "   • Conditional routing — different paths based on state values",
    "   • Human-in-the-loop — graph pauses for admin input",
    "   • State management — TypedDict flows through all nodes",
    "",
    "🔄 Before (Stages 1-3): Run chatbot CLI, then admin CLI, then MCP server",
    "   separately — YOU are the orchestrator",
    "",
    "✅ After (Stage 4): Run `python main.py --graph` — the GRAPH is the",
    "   orchestrator, routing automatically between steps",
], 0.5, 1.2, 9, 5.5, font_size=16, color=WHITE)
add_slide_number(slide, 2, TOTAL_SLIDES)

# ── SLIDE 3: Problem — Manual Orchestration ──
slide = prs.slides.add_slide(prs.slide_layouts[6])
set_slide_bg(slide, DARK_BG)
add_title_text(slide, "Problem: Manual Orchestration", 0.5, 0.3, 9, 0.6, font_size=32, color=ACCENT_ORANGE)
add_divider(slide, 0.95)

add_card(slide, 0.3, 1.3, 4.3, 2.8, "Before (Stages 1-3)", [
    "Terminal 1: python main.py (chatbot)",
    "Terminal 2: python main.py --admin",
    "Terminal 3: python main.py --mcp-server",
    "Human manually switches between terminals",
    "No unified state tracking across components",
    "If MCP fails, you have to notice yourself",
], title_color=ACCENT_RED)

add_card(slide, 5.3, 1.3, 4.3, 2.8, "After (Stage 4)", [
    "Single command: python main.py --graph",
    "Graph engine routes between nodes",
    "Shared state flows through pipeline",
    "Auto-switches user ↔ admin mode",
    "Each node handles its own errors",
    "Conditional paths (approve vs reject)",
], title_color=ACCENT_GREEN)

add_card(slide, 0.3, 4.5, 9.3, 2.3, "What Changed Functionally?", [
    "Same result — bookings still get submitted, reviewed, approved, and recorded",
    "The difference is WHO connects the steps: You (manual) vs Graph (automatic)",
    "Like upgrading from manual function calls to a workflow engine",
    "Adds: state visibility, conditional routing, unified error handling",
], title_color=ACCENT_PURPLE)
add_slide_number(slide, 3, TOTAL_SLIDES)

# ── SLIDE 4: LangGraph StateGraph ──
slide = prs.slides.add_slide(prs.slide_layouts[6])
set_slide_bg(slide, DARK_BG)
add_title_text(slide, "LangGraph StateGraph", 0.5, 0.3, 9, 0.6, font_size=32, color=ACCENT_BLUE)
add_divider(slide, 0.95)
add_bullet_list(slide, [
    "LangGraph extends LangChain with graph-based orchestration:",
    "",
    "📌 NODES — Processing steps (Python functions)",
    "   Each node receives the full state, modifies fields, returns updates",
    "",
    "📌 EDGES — Connections between nodes",
    "   Regular edge: A → B (always go to B after A)",
    "   Conditional edge: A → B or C (depends on state values)",
    "",
    "📌 STATE — TypedDict shared across all nodes",
    "   Like a conveyor belt — each station reads/writes to same object",
    "",
    "📌 ENTRY POINT — Where the graph starts execution",
    "",
    "📌 END — Special marker that terminates graph execution",
    "",
    "NOT a network protocol (no WebSocket). Just Python functions",
    "calling each other through a state dict — all in one process.",
], 0.5, 1.2, 9, 5.8, font_size=15, color=WHITE)
add_slide_number(slide, 4, TOTAL_SLIDES)

# ── SLIDE 5: GraphState Schema ──
slide = prs.slides.add_slide(prs.slide_layouts[6])
set_slide_bg(slide, DARK_BG)
add_title_text(slide, "GraphState Schema", 0.5, 0.3, 9, 0.6, font_size=32, color=ACCENT_GREEN)
add_divider(slide, 0.95)
add_title_text(slide, "src/graph/state.py", 0.5, 1.1, 3, 0.4, font_size=14, color=LIGHT_GRAY, bold=False)

add_card(slide, 0.3, 1.5, 4.3, 3.0, "GraphState (TypedDict)", [
    "user_message: str — current user input",
    "bot_response: str — chatbot's response",
    "conversation_phase: str — pipeline phase",
    "reservation_id: int — DB ID after save",
    "admin_decision: str — approve/reject",
    "admin_notes: str — admin's reason",
    "notification_sent: bool — email status",
    "mcp_recorded: bool — MCP write status",
    "is_booking_flow: bool — mid-booking?",
], title_color=ACCENT_GREEN)

add_card(slide, 5.3, 1.5, 4.3, 3.0, "PipelinePhase (Enum)", [
    "USER_INTERACTION — chatbot talking",
    "BOOKING_COMPLETE — user confirmed",
    "AWAITING_ADMIN — waiting for admin",
    "ADMIN_REVIEWING — admin viewing",
    "APPROVED — admin approved",
    "REJECTED — admin rejected",
    "NOTIFYING — sending emails",
    "RECORDING — MCP file write",
    "COMPLETED — pipeline done",
    "ERROR — something went wrong",
], title_color=ACCENT_ORANGE)

add_card(slide, 0.3, 4.8, 9.3, 1.8, "Why TypedDict?", [
    "LangGraph requires a typed state schema so it knows what data flows between nodes",
    "Every node receives the FULL state, modifies its fields, returns ONLY changed fields",
    "LangGraph merges the returned dict into the full state automatically",
    "total=False means not all keys are required — nodes can set only what they need",
], title_color=ACCENT_BLUE)
add_slide_number(slide, 5, TOTAL_SLIDES)

# ── SLIDE 6: Pipeline Architecture ──
slide = prs.slides.add_slide(prs.slide_layouts[6])
set_slide_bg(slide, DARK_BG)
add_title_text(slide, "Pipeline Architecture", 0.5, 0.3, 9, 0.6, font_size=32, color=ACCENT_BLUE)
add_divider(slide, 0.95)

# Visual flow diagram using text
flow_text = (
    "user_interaction\n"
    "       │\n"
    "  booking complete?\n"
    "  ├── No ──► END\n"
    "  └── Yes\n"
    "       │\n"
    "  save_reservation\n"
    "       │\n"
    "  admin_review  ◄── Human Input\n"
    "  ┌────┴────┐\n"
    "approve   reject\n"
    "  │         │\n"
    "notify    notify\n"
    "  │         │\n"
    " MCP        │\n"
    "  │         │\n"
    "  └────┬────┘\n"
    "  completion"
)
add_title_text(slide, flow_text, 0.5, 1.2, 4.5, 5.5, font_size=15, color=ACCENT_GREEN, bold=False)

add_card(slide, 5.0, 1.2, 4.5, 5.5, "Key Design Decisions", [
    "✅ Entry point: user_interaction",
    "   (all messages start here)",
    "",
    "✅ Conditional after user_interaction:",
    "   booking → save, else → END",
    "",
    "✅ Conditional after admin_review:",
    "   decided → notify, else → END (wait)",
    "",
    "✅ Conditional after notification:",
    "   approved → MCP, rejected → completion",
    "",
    "✅ admin_review is human-in-the-loop:",
    "   graph pauses until admin inputs",
    "",
    "✅ MCP only for approvals:",
    "   rejected reservations skip file write",
], title_color=ACCENT_BLUE)
add_slide_number(slide, 6, TOTAL_SLIDES)

# ── SLIDE 7: Graph Nodes ──
slide = prs.slides.add_slide(prs.slide_layouts[6])
set_slide_bg(slide, DARK_BG)
add_title_text(slide, "6 Graph Nodes", 0.5, 0.3, 9, 0.6, font_size=32, color=ACCENT_GREEN)
add_divider(slide, 0.95)

nodes = [
    ("1. user_interaction", ["Passes message to ParkingChatbot", "Detects booking completion", "Updates history"], ACCENT_BLUE),
    ("2. save_reservation", ["Confirms DB save", "Transitions to AWAITING_ADMIN", "Sets needs_admin_input=True"], ACCENT_GREEN),
    ("3. admin_review", ["Parses approve/reject/review", "Human-in-the-loop node", "Preserves case in notes"], ACCENT_ORANGE),
    ("4. notification", ["Updates DB status", "Sends email to user", "Handles email failures"], ACCENT_PURPLE),
    ("5. mcp_recording", ["Writes to file via MCP client", "Falls back to local write", "Only for approvals"], ACCENT_BLUE),
    ("6. completion", ["Generates pipeline summary", "Shows ✅/⚠ for each step", "Sets phase=COMPLETED"], ACCENT_GREEN),
]

for i, (title, items, color) in enumerate(nodes):
    col = i % 3
    row = i // 3
    left = 0.3 + col * 3.2
    top = 1.2 + row * 2.8
    add_card(slide, left, top, 3.0, 2.5, title, items, title_color=color)
add_slide_number(slide, 7, TOTAL_SLIDES)

# ── SLIDE 8: Conditional Edges ──
slide = prs.slides.add_slide(prs.slide_layouts[6])
set_slide_bg(slide, DARK_BG)
add_title_text(slide, "Conditional Edges & Routing", 0.5, 0.3, 9, 0.6, font_size=32, color=ACCENT_ORANGE)
add_divider(slide, 0.95)

add_card(slide, 0.3, 1.2, 4.3, 2.0, "after_user_interaction()", [
    "If phase == BOOKING_COMPLETE → save_reservation",
    "Otherwise → END (return response to user)",
    "Keeps Q&A responses from entering pipeline",
], title_color=ACCENT_BLUE)

add_card(slide, 5.3, 1.2, 4.3, 2.0, "after_admin_review()", [
    "If needs_admin_input → END (pause graph)",
    "If phase == APPROVED → notification",
    "If phase == REJECTED → notification",
], title_color=ACCENT_GREEN)

add_card(slide, 0.3, 3.5, 4.3, 2.0, "after_notification()", [
    "If decision == 'approve' → mcp_recording",
    "If decision == 'reject' → completion",
    "Rejected reservations skip MCP file write",
], title_color=ACCENT_ORANGE)

add_card(slide, 5.3, 3.5, 4.3, 2.0, "Fixed Edges", [
    "save_reservation → admin_review (always)",
    "mcp_recording → completion (always)",
    "These never vary — they always run in sequence",
], title_color=ACCENT_PURPLE)

add_card(slide, 0.3, 5.8, 9.3, 1.2, "How It Works in Code", [
    "graph.add_conditional_edges('user_interaction', after_user_interaction, {'save_reservation': 'save_reservation', END: END})",
    "Each conditional function receives the full state and returns a string key → LangGraph routes to that node",
], title_color=LIGHT_GRAY)
add_slide_number(slide, 8, TOTAL_SLIDES)

# ── SLIDE 9: Human-in-the-Loop ──
slide = prs.slides.add_slide(prs.slide_layouts[6])
set_slide_bg(slide, DARK_BG)
add_title_text(slide, "Human-in-the-Loop Admin", 0.5, 0.3, 9, 0.6, font_size=32, color=ACCENT_PURPLE)
add_divider(slide, 0.95)

add_bullet_list(slide, [
    "The admin_review node is the HUMAN-IN-THE-LOOP point:",
    "",
    "1️⃣  User completes booking → graph auto-advances to admin_review",
    "",
    "2️⃣  admin_review generates a review summary (availability check)",
    "    CLI prompt switches from '👤 You:' to '🔧 Admin:'",
    "",
    "3️⃣  Graph PAUSES — returns END, waits for admin input",
    "    (needs_admin_input = True)",
    "",
    "4️⃣  Admin types 'approve [notes]' or 'reject [reason]'",
    "",
    "5️⃣  run_admin_decision() resumes the pipeline:",
    "    admin_review → notification → mcp_recording → completion",
    "",
    "6️⃣  Pipeline completes — CLI switches back to '👤 You:' mode",
    "",
    "The admin always makes the final decision — the graph just routes it.",
], 0.5, 1.2, 9, 5.8, font_size=15, color=WHITE)
add_slide_number(slide, 9, TOTAL_SLIDES)

# ── SLIDE 10: MCP in the Graph ──
slide = prs.slides.add_slide(prs.slide_layouts[6])
set_slide_bg(slide, DARK_BG)
add_title_text(slide, "MCP Integration in Pipeline", 0.5, 0.3, 9, 0.6, font_size=32, color=ACCENT_BLUE)
add_divider(slide, 0.95)

add_card(slide, 0.3, 1.2, 4.3, 2.5, "mcp_recording Node", [
    "Only runs for APPROVED reservations",
    "Calls MCPClient.write_reservation_to_file()",
    "Sends name, car, period to MCP server",
    "Sets mcp_recorded = True on success",
    "Falls back to local file if server down",
], title_color=ACCENT_BLUE)

add_card(slide, 5.3, 1.2, 4.3, 2.5, "MCP Server (Port 8001)", [
    "Started separately: --mcp-server",
    "Receives tool call via POST /mcp/tools/call",
    "Writes to data/approved_reservations.txt",
    "API key authentication (X-MCP-API-KEY)",
    "Health check at /mcp/health",
], title_color=ACCENT_GREEN)

add_card(slide, 0.3, 4.0, 9.3, 2.5, "Flow: Approval → MCP Recording", [
    "admin_review (approve) → notification (update DB + email) → mcp_recording",
    "",
    "mcp_recording node reads reservation data from state.reservation_data",
    "If empty, falls back to fetching from DB via state.reservation_id",
    "",
    "MCPClient tries server first, falls back to local file write",
    "Record format: Name | Car Number | Reservation Period | Approval Time",
], title_color=ACCENT_ORANGE)
add_slide_number(slide, 10, TOTAL_SLIDES)

# ── SLIDE 11: Unified CLI ──
slide = prs.slides.add_slide(prs.slide_layouts[6])
set_slide_bg(slide, DARK_BG)
add_title_text(slide, "Unified CLI: --graph Mode", 0.5, 0.3, 9, 0.6, font_size=32, color=ACCENT_GREEN)
add_divider(slide, 0.95)

add_bullet_list(slide, [
    "python main.py --graph",
    "",
    "Available CLI modes (all stages):",
    "",
    "  python main.py              # Stage 1: Chatbot Q&A",
    "  python main.py --setup      # Stage 1: Initialize databases",
    "  python main.py --evaluate   # Stage 1: RAG evaluation metrics",
    "  python main.py --server     # Stage 2: REST API (port 8000)",
    "  python main.py --admin      # Stage 2: Admin CLI agent",
    "  python main.py --mcp-server # Stage 3: MCP server (port 8001)",
    "  python main.py --graph      # Stage 4: LangGraph pipeline ✨",
    "",
    "In --graph mode, special commands:",
    "  'status'  — Show current pipeline phase and state",
    "  'reset'   — Reset pipeline and chatbot",
    "  'quit'    — Exit the program",
], 0.5, 1.2, 9, 5.5, font_size=16, color=WHITE)
add_slide_number(slide, 11, TOTAL_SLIDES)

# ── SLIDE 12: Test Results ──
slide = prs.slides.add_slide(prs.slide_layouts[6])
set_slide_bg(slide, DARK_BG)
add_title_text(slide, "Test Results: 124 Tests Passing", 0.5, 0.3, 9, 0.6, font_size=32, color=ACCENT_GREEN)
add_divider(slide, 0.95)

test_data = [
    ("Stage 1", "35 tests", "Vector, SQL, Chatbot, Guardrails, Evaluator"),
    ("Stage 2", "27 tests", "API Server, Admin Agent, Email Service"),
    ("Stage 3", "21 tests", "MCP Server, MCP Client, Fallback"),
    ("Stage 4", "38 tests", "State, Nodes, Edges, Pipeline, E2E"),
]

for i, (stage, count, desc) in enumerate(test_data):
    top = 1.3 + i * 1.4
    add_card(slide, 0.3, top, 2.2, 1.2, stage, [count], title_color=ACCENT_BLUE)
    add_card(slide, 2.7, top, 6.9, 1.2, desc, [
        f"Comprehensive coverage: {desc}"
    ], title_color=ACCENT_GREEN)

add_card(slide, 0.3, 6.1, 9.3, 0.9, "Stage 4 Test Categories (38 tests)", [
    "State Schema (4) • User Interaction (4) • Save (2) • Admin Review (5) • Notification (4) • MCP (3) • Completion (2) • Edges (7) • Pipeline (2) • Helpers (2) • E2E (2) • User Message (1)",
], title_color=ACCENT_ORANGE)
add_slide_number(slide, 12, TOTAL_SLIDES)

# ── SLIDE 13: Live Demo Summary ──
slide = prs.slides.add_slide(prs.slide_layouts[6])
set_slide_bg(slide, DARK_BG)
add_title_text(slide, "Live Demo Results", 0.5, 0.3, 9, 0.6, font_size=32, color=ACCENT_BLUE)
add_divider(slide, 0.95)

add_bullet_list(slide, [
    "Live test (test_graph_live.py) confirmed full pipeline:",
    "",
    "  ✅ Q&A: 'What are parking hours?' → correct response, stays in user_interaction",
    "",
    "  ✅ Booking: Collected name, email, car, type, start, end → confirmed",
    "",
    "  ✅ Auto-transition: Prompt switched from '👤 You:' to '🔧 Admin:'",
    "",
    "  ✅ Admin review: Auto-generated availability check + reservation details",
    "",
    "  ✅ Admin approve: 'approve Stage 4 test' → pipeline continued automatically",
    "",
    "  ✅ Notification: Email sent to user (notification_sent: True)",
    "",
    "  ✅ MCP Recording: Written to approved_reservations.txt (mcp_recorded: True)",
    "",
    "  ✅ Completion: Pipeline summary with ✅ for all steps",
    "",
    "  Pipeline Phase: COMPLETED | Admin Decision: approve",
], 0.5, 1.2, 9, 5.8, font_size=15, color=WHITE)
add_slide_number(slide, 13, TOTAL_SLIDES)

# ── SLIDE 14: Key Takeaways ──
slide = prs.slides.add_slide(prs.slide_layouts[6])
set_slide_bg(slide, DARK_BG)
add_title_text(slide, "Summary & Key Takeaways", 0.5, 0.3, 9, 0.6, font_size=32, color=ACCENT_BLUE)
add_divider(slide, 0.95)

add_card(slide, 0.3, 1.2, 4.3, 2.5, "What Stage 4 Added", [
    "LangGraph StateGraph with 6 nodes",
    "3 conditional edge functions",
    "10-phase PipelinePhase enum",
    "GraphState TypedDict (13 fields)",
    "Unified CLI with --graph flag",
    "38 new tests (124 total)",
], title_color=ACCENT_GREEN)

add_card(slide, 5.3, 1.2, 4.3, 2.5, "All 4 Stages Complete", [
    "Stage 1: RAG + Guardrails + Eval",
    "Stage 2: Admin Agent + REST API + Email",
    "Stage 3: MCP Server + Client + Fallback",
    "Stage 4: LangGraph Orchestration",
    "124 tests passing across all stages",
    "Full CI/CD on GitHub Actions",
], title_color=ACCENT_BLUE)

add_card(slide, 0.3, 4.0, 9.3, 2.0, "Technology Stack", [
    "Python 3.13  •  LangChain + LangGraph  •  EPAM DIAL (GPT-4o)  •  ChromaDB  •  SQLite",
    "FastAPI  •  Presidio (PII)  •  HuggingFace Embeddings  •  Gmail SMTP  •  MCP Protocol",
    "pytest (124 tests)  •  GitHub Actions CI/CD  •  python-pptx",
], title_color=ACCENT_PURPLE)

add_title_text(slide, "Thank You!", 0.5, 6.3, 9, 0.7, font_size=28, color=ACCENT_GREEN, alignment=PP_ALIGN.CENTER)
add_slide_number(slide, 14, TOTAL_SLIDES)

# ── SAVE ──
output_path = "ParkSmart_Stage4_Presentation.pptx"
prs.save(output_path)
print(f"✅ Stage 4 presentation saved: {output_path} ({TOTAL_SLIDES} slides)")
