import api from "@/lib/api";
import type { ChatRequest, ChatResponse } from "@/types";

export const chatService = {
  checkReady: async (): Promise<{ ready: boolean; status: string; message: string }> => {
    const { data } = await api.get("/api/ready", { timeout: 5000 });
    return data;
  },

  sendMessage: async (message: string, sessionId?: string): Promise<ChatResponse> => {
    const payload: ChatRequest = { message, session_id: sessionId };
    const { data } = await api.post<ChatResponse>("/api/chat", payload);
    return data;
  },

  resetSession: async (sessionId?: string): Promise<void> => {
    await api.post("/api/chat/reset", null, {
      params: sessionId ? { session_id: sessionId } : undefined,
    });
  },

  cancelBooking: async (sessionId?: string): Promise<ChatResponse> => {
    const { data } = await api.post<ChatResponse>("/api/chat/cancel-booking", null, {
      params: sessionId ? { session_id: sessionId } : undefined,
    });
    return data;
  },
};
