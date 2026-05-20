import api from "@/lib/api";
import type { ChatRequest, ChatResponse } from "@/types";

export const chatService = {
  sendMessage: async (message: string): Promise<ChatResponse> => {
    const payload: ChatRequest = { message };
    const { data } = await api.post<ChatResponse>("/api/chat", payload);
    return data;
  },
};
