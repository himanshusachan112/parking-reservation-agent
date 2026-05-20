import { create } from "zustand";
import type { ChatMessage, ChatSession } from "@/types";
import { chatService } from "@/services/chatService";
import { generateId } from "@/lib/helpers";

interface ChatStore {
  // State
  sessions: ChatSession[];
  activeSessionId: string | null;
  isLoading: boolean;
  error: string | null;

  // Computed
  activeSession: () => ChatSession | undefined;
  activeMessages: () => ChatMessage[];

  // Actions
  createSession: () => string;
  setActiveSession: (id: string) => void;
  deleteSession: (id: string) => void;
  sendMessage: (content: string) => Promise<void>;
  clearError: () => void;
}

export const useChatStore = create<ChatStore>((set, get) => ({
  sessions: [],
  activeSessionId: null,
  isLoading: false,
  error: null,

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
    };
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

  sendMessage: async (content: string) => {
    const { activeSessionId, sessions } = get();
    let sessionId = activeSessionId;

    // Auto-create session if none active
    if (!sessionId) {
      sessionId = get().createSession();
    }

    const userMessage: ChatMessage = {
      id: generateId(),
      role: "user",
      content,
      timestamp: new Date(),
    };

    // Add user message
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
      const data = await chatService.sendMessage(content);

      const botMessage: ChatMessage = {
        id: generateId(),
        role: "assistant",
        content: data.response,
        timestamp: new Date(),
        reservationId: data.reservation_id,
        isBookingFlow: data.is_booking_flow,
      };

      set((state) => ({
        sessions: state.sessions.map((s) =>
          s.id === sessionId
            ? {
                ...s,
                messages: [...s.messages, botMessage],
                lastMessage: data.response.slice(0, 60),
              }
            : s
        ),
        isLoading: false,
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
}));
