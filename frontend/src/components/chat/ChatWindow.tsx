"use client";

import { useMemo } from "react";
import { AnimatePresence } from "framer-motion";
import { MessageSquare } from "lucide-react";
import { ChatMessage } from "./ChatMessage";
import { TypingIndicator } from "./TypingIndicator";
import { EmptyState } from "@/components/shared/EmptyState";
import { useAutoScroll } from "@/hooks/useAutoScroll";
import { useChatStore } from "@/store/chatStore";

export function ChatWindow() {
  const sessions = useChatStore((s) => s.sessions);
  const activeSessionId = useChatStore((s) => s.activeSessionId);
  const isLoading = useChatStore((s) => s.isLoading);
  const messages = useMemo(
    () => sessions.find((s) => s.id === activeSessionId)?.messages || [],
    [sessions, activeSessionId]
  );
  const scrollRef = useAutoScroll([messages, isLoading]);

  if (messages.length === 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-6">
        <EmptyState
          icon={MessageSquare}
          title="Welcome to ParkSmart AI"
          description="Ask me about parking availability, rates, working hours, or book a parking space."
        />
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-6 max-w-lg w-full">
          {[
            "What are your parking rates?",
            "Is there EV charging available?",
            "I'd like to book a parking space",
            "What are your working hours?",
          ].map((q) => (
            <button
              key={q}
              onClick={() => useChatStore.getState().sendMessage(q)}
              className="text-left text-sm rounded-xl border bg-card p-3 text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors"
            >
              {q}
            </button>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div ref={scrollRef} className="flex-1 overflow-y-auto py-4">
      <div className="max-w-3xl mx-auto">
        <AnimatePresence mode="popLayout">
          {messages.map((msg) => (
            <ChatMessage key={msg.id} message={msg} />
          ))}
        </AnimatePresence>
        <AnimatePresence>
          {isLoading && <TypingIndicator />}
        </AnimatePresence>
      </div>
    </div>
  );
}
