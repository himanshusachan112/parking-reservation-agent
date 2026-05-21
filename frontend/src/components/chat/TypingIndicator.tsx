"use client";

import { motion } from "framer-motion";
import { Bot } from "lucide-react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";

export function TypingIndicator() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className="flex gap-3 px-4 md:px-6 py-3"
    >
      <Avatar className="h-8 w-8 shrink-0 mt-1 ring-2 ring-emerald-500/20 shadow-sm">
        <AvatarFallback className="bg-gradient-to-br from-emerald-500/15 to-emerald-600/10 text-emerald-600 dark:text-emerald-400 text-xs">
          <Bot className="h-4 w-4" />
        </AvatarFallback>
      </Avatar>
      <div className="bg-muted/60 backdrop-blur-sm border border-border/40 rounded-2xl rounded-bl-md px-4 py-3 flex items-center gap-1.5">
        {[0, 1, 2].map((i) => (
          <motion.span
            key={i}
            className="h-2 w-2 rounded-full bg-primary/40"
            animate={{ y: [0, -6, 0], opacity: [0.4, 1, 0.4] }}
            transition={{
              duration: 0.7,
              repeat: Infinity,
              delay: i * 0.15,
              ease: "easeInOut",
            }}
          />
        ))}
      </div>
    </motion.div>
  );
}
