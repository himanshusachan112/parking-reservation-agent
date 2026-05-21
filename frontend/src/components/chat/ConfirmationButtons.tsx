"use client";

import { motion } from "framer-motion";
import { Check, X, RotateCcw } from "lucide-react";
import { useChatStore } from "@/store/chatStore";

export function ConfirmationButtons() {
  const sendMessage = useChatStore((s) => s.sendMessage);
  const isLoading = useChatStore((s) => s.isLoading);

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: 0.1 }}
      className="flex items-center gap-2 mt-3"
    >
      <motion.button
        whileHover={{ scale: 1.03 }}
        whileTap={{ scale: 0.97 }}
        disabled={isLoading}
        onClick={() => sendMessage("yes")}
        className="inline-flex items-center gap-2 rounded-xl border border-emerald-500/30 bg-emerald-500/5 px-5 py-2.5 text-sm font-semibold text-emerald-600 dark:text-emerald-400 shadow-sm transition-all duration-200 hover:bg-emerald-500/10 hover:border-emerald-500/50 hover:shadow-md hover:shadow-emerald-500/10 disabled:opacity-50"
      >
        <Check className="h-4 w-4" />
        Confirm Booking
      </motion.button>
      <motion.button
        whileHover={{ scale: 1.03 }}
        whileTap={{ scale: 0.97 }}
        disabled={isLoading}
        onClick={() => sendMessage("no")}
        className="inline-flex items-center gap-2 rounded-xl border border-border px-4 py-2.5 text-sm font-medium text-muted-foreground shadow-sm transition-all duration-200 hover:bg-muted hover:text-foreground disabled:opacity-50"
      >
        <RotateCcw className="h-3.5 w-3.5" />
        Start Over
      </motion.button>
    </motion.div>
  );
}

/** Detect if a bot message is asking for booking confirmation. */
export function isConfirmationPrompt(content: string): boolean {
  const lower = content.toLowerCase();
  return (
    lower.includes("is this correct?") &&
    lower.includes("reservation summary")
  );
}
