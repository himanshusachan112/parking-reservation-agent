import { create } from "zustand";
import type { BookingProgress, ChatMessage, ChatSession } from "@/types";
import { chatService } from "@/services/chatService";
import { generateId } from "@/lib/helpers";

/** Quick-action suggestions shown after out-of-domain or empty state */
export const DEFAULT_SUGGESTIONS = [
  "What are your parking rates?",
  "Book a parking slot",
  "Check parking availability",
  "What are your working hours?",
  "Tell me about VIP parking",
];

interface ChatStore {
  // State
  sessions: ChatSession[];
  activeSessionId: string | null;
  isLoading: boolean;
  error: string | null;
  bookingProgress: BookingProgress | null;

  // Computed
  activeSession: () => ChatSession | undefined;
  activeMessages: () => ChatMessage[];

  // Actions
  createSession: () => string;
  setActiveSession: (id: string) => void;
  deleteSession: (id: string) => void;
  renameSession: (id: string, title: string) => void;
  sendMessage: (content: string) => Promise<void>;
  cancelBooking: () => Promise<void>;
  clearError: () => void;
}

export const useChatStore = create<ChatStore>((set, get) => ({
  sessions: [],
  activeSessionId: null,
  isLoading: false,
  error: null,
  bookingProgress: null,

  activeSession: () => {
    const { sessions, activeSessionId } = get();
    return sessions.find((s) => s.id === activeSessionId);
  },

  activeMessages: () => {
    const session = get().activeSession();
    return session?.messages || [];
  },

  createSession: () => {
    const id = generateId();
    const session: ChatSession = {
      id,
      title: "New Chat",
      lastMessage: "",
      timestamp: new Date(),
      messages: [],
      backendSessionId: undefined,
    };

    // Reset backend state for the previous session (fire-and-forget)
    const prev = get().activeSession();
    if (prev?.backendSessionId) {
      chatService.resetSession(prev.backendSessionId).catch(() => {});
    }

    set((state) => ({
      sessions: [session, ...state.sessions],
      activeSessionId: id,
    }));
    return id;
  },

  setActiveSession: (id) => {
    set({ activeSessionId: id });
  },

  deleteSession: (id) => {
    // Clean up backend session
    const session = get().sessions.find((s) => s.id === id);
    if (session?.backendSessionId) {
      chatService.resetSession(session.backendSessionId).catch(() => {});
    }

    set((state) => {
      const filtered = state.sessions.filter((s) => s.id !== id);
      return {
        sessions: filtered,
        activeSessionId:
          state.activeSessionId === id
            ? filtered[0]?.id || null
            : state.activeSessionId,
      };
    });
  },

  renameSession: (id, title) => {
    set((state) => ({
      sessions: state.sessions.map((s) =>
        s.id === id ? { ...s, title } : s
      ),
    }));
  },

  sendMessage: async (content: string) => {
    const { activeSessionId } = get();
    let sessionId = activeSessionId;

    // Auto-create session if none active
    if (!sessionId) {
      sessionId = get().createSession();
    }

    const session = get().sessions.find((s) => s.id === sessionId);

    const userMessage: ChatMessage = {
      id: generateId(),
      role: "user",
      content,
      timestamp: new Date(),
    };

    // Add user message and auto-title from first message
    set((state) => ({
      sessions: state.sessions.map((s) =>
        s.id === sessionId
          ? {
              ...s,
              messages: [...s.messages, userMessage],
              lastMessage: content,
              timestamp: new Date(),
              title:
                s.messages.length === 0
                  ? content.slice(0, 40) + (content.length > 40 ? "…" : "")
                  : s.title,
            }
          : s
      ),
      isLoading: true,
      error: null,
    }));

    try {
      const data = await chatService.sendMessage(
        content,
        session?.backendSessionId
      );

      // Detect out-of-domain / suggestion-worthy responses
      const suggestions = detectSuggestions(data.response, data.is_booking_flow);

      const botMessage: ChatMessage = {
        id: generateId(),
        role: "assistant",
        content: data.response,
        timestamp: new Date(),
        reservationId: data.reservation_id,
        isBookingFlow: data.is_booking_flow,
        suggestions: suggestions.length > 0 ? suggestions : undefined,
      };

      set((state) => ({
        sessions: state.sessions.map((s) =>
          s.id === sessionId
            ? {
                ...s,
                messages: [...s.messages, botMessage],
                lastMessage: data.response.slice(0, 60),
                backendSessionId: data.session_id || s.backendSessionId,
              }
            : s
        ),
        isLoading: false,
        bookingProgress: data.booking_progress ?? null,
      }));
    } catch (err: unknown) {
      const errorMessage =
        err && typeof err === "object" && "detail" in err
          ? (err as { detail: string }).detail
          : "Failed to send message. Is the backend running?";
      set({ isLoading: false, error: errorMessage });
    }
  },

  clearError: () => set({ error: null }),

  cancelBooking: async () => {
    const session = get().activeSession();
    if (!session?.backendSessionId) return;

    set({ isLoading: true });
    try {
      const data = await chatService.cancelBooking(session.backendSessionId);

      const botMessage: ChatMessage = {
        id: generateId(),
        role: "assistant",
        content: data.response,
        timestamp: new Date(),
        isBookingFlow: false,
        suggestions: DEFAULT_SUGGESTIONS,
      };

      set((state) => ({
        sessions: state.sessions.map((s) =>
          s.id === session.id
            ? {
                ...s,
                messages: [...s.messages, botMessage],
                lastMessage: data.response.slice(0, 60),
              }
            : s
        ),
        isLoading: false,
        bookingProgress: null,
      }));
    } catch {
      set({ isLoading: false, error: "Failed to cancel booking" });
    }
  },
}));

/**
 * Detect contextual suggestion chips for every bot response.
 * During booking flow: show booking-relevant suggestions.
 * Out-of-domain: show default parking suggestions.
 * Otherwise: show default parking suggestions (always visible).
 */
function detectSuggestions(response: string, isBookingFlow?: boolean): string[] {
  if (isBookingFlow) {
    return ["Cancel Booking"];
  }

  const lower = response.toLowerCase();

  // Out-of-domain indicators — keep defaults
  const outOfDomain = [
    "i can only help with parking",
    "i'm designed to assist with parking",
    "i specialize in parking",
    "outside my scope",
    "i can't help with that",
    "parking-related",
    "not related to parking",
    "i'm a parking assistant",
    "beyond my capabilities",
    "i don't have information about that",
    "i'm not able to help with",
    "my expertise is limited to parking",
  ];

  if (outOfDomain.some((phrase) => lower.includes(phrase))) {
    return DEFAULT_SUGGESTIONS;
  }

  // Always show default suggestions on non-booking messages
  return DEFAULT_SUGGESTIONS;
}
