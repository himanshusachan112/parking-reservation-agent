"use client";

import { useMemo } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  Clock,
  CreditCard,
  Zap,
  Crown,
  MapPin,
  ArrowRight,
  Car,
} from "lucide-react";
import { ChatMessage } from "./ChatMessage";
import { TypingIndicator } from "./TypingIndicator";
import { BookingProgressBar } from "./BookingProgressBar";
import { useAutoScroll } from "@/hooks/useAutoScroll";
import { useChatStore } from "@/store/chatStore";

const QUICK_ACTIONS = [
  {
    text: "What are your parking rates?",
    icon: CreditCard,
    description: "View pricing for all parking types",
    gradient: "from-blue-500/10 to-blue-600/5",
    iconColor: "text-blue-600 dark:text-blue-400",
  },
  {
    text: "I'd like to book a parking space",
    icon: Car,
    description: "Reserve your spot in minutes",
    gradient: "from-emerald-500/10 to-emerald-600/5",
    iconColor: "text-emerald-600 dark:text-emerald-400",
  },
  {
    text: "Is there EV charging available?",
    icon: Zap,
    description: "Level 2 + Tesla Supercharger",
    gradient: "from-amber-500/10 to-amber-600/5",
    iconColor: "text-amber-600 dark:text-amber-400",
  },
  {
    text: "What are your working hours?",
    icon: Clock,
    description: "Operating schedule & holidays",
    gradient: "from-violet-500/10 to-violet-600/5",
    iconColor: "text-violet-600 dark:text-violet-400",
  },
  {
    text: "Tell me about VIP parking",
    icon: Crown,
    description: "Premium covered spots near entrance",
    gradient: "from-purple-500/10 to-purple-600/5",
    iconColor: "text-purple-600 dark:text-purple-400",
  },
  {
    text: "Check parking availability",
    icon: MapPin,
    description: "Real-time space availability",
    gradient: "from-rose-500/10 to-rose-600/5",
    iconColor: "text-rose-600 dark:text-rose-400",
  },
];

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
      <div className="flex-1 flex flex-col items-center justify-center p-6 overflow-y-auto">
        {/* Hero */}
        <motion.div
          initial={{ opacity: 0, scale: 0.92 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5, ease: [0.25, 0.46, 0.45, 0.94] }}
          className="flex flex-col items-center"
        >
          <h3 className="text-3xl sm:text-4xl font-extrabold tracking-tight bg-gradient-to-r from-emerald-600 via-primary to-emerald-500 bg-clip-text text-transparent">
            ParkSmart AI
          </h3>
          <p className="text-sm text-muted-foreground mt-3 max-w-md text-center leading-relaxed">
            Your intelligent parking assistant — ask about availability,
            pricing, hours, or book a space in seconds.
          </p>
        </motion.div>

        {/* Quick actions grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 mt-8 max-w-2xl w-full">
          {QUICK_ACTIONS.map((action, i) => (
            <motion.button
              key={action.text}
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.35, delay: 0.06 * i }}
              whileHover={{ scale: 1.02, y: -2 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => useChatStore.getState().sendMessage(action.text)}
              className="group relative overflow-hidden text-left rounded-xl border bg-card p-4 transition-all duration-300 hover:border-primary/30 hover:shadow-lg hover:shadow-primary/5"
            >
              <div
                className={`absolute inset-0 bg-gradient-to-br ${action.gradient} opacity-0 group-hover:opacity-100 transition-opacity duration-300`}
              />
              <div className="relative flex items-start gap-3">
                <div
                  className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br ${action.gradient} border border-border/50`}
                >
                  <action.icon
                    className={`h-4 w-4 ${action.iconColor}`}
                  />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-foreground">
                    {action.text}
                  </p>
                  <p className="text-[11px] text-muted-foreground mt-0.5">
                    {action.description}
                  </p>
                </div>
                <ArrowRight className="h-4 w-4 text-muted-foreground/40 group-hover:text-primary transition-colors mt-0.5 shrink-0 opacity-0 group-hover:opacity-100" />
              </div>
            </motion.button>
          ))}
        </div>

        {/* Powered by badge */}
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
          className="text-[10px] text-muted-foreground/50 mt-8"
        >
          Powered by LangGraph + RAG
        </motion.p>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      <BookingProgressBar />
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto py-4 scroll-smooth scrollbar-thin"
      >
        <div className="max-w-3xl mx-auto">
          <AnimatePresence mode="popLayout">
            {messages.map((msg, i) => (
              <ChatMessage
                key={msg.id}
                message={msg}
                isLatest={i === messages.length - 1}
              />
            ))}
          </AnimatePresence>
          <AnimatePresence>
            {isLoading && <TypingIndicator />}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
