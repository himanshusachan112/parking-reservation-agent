"use client";

import { motion } from "framer-motion";
import {
  Sparkles,
  CreditCard,
  Car,
  Crown,
  Zap,
  MapPin,
  XCircle,
  type LucideIcon,
} from "lucide-react";
import { useChatStore } from "@/store/chatStore";

const CHIP_ICONS: Record<string, LucideIcon> = {
  "What are your parking rates?": CreditCard,
  "Book a parking slot": Car,
  "Check parking availability": MapPin,
  "What are your working hours?": Sparkles,
  "Tell me about VIP parking": Crown,
  "Cancel Booking": XCircle,
};

interface SuggestionChipsProps {
  suggestions: string[];
}

export function SuggestionChips({ suggestions }: SuggestionChipsProps) {
  const sendMessage = useChatStore((s) => s.sendMessage);
  const cancelBooking = useChatStore((s) => s.cancelBooking);
  const isLoading = useChatStore((s) => s.isLoading);

  const handleClick = (text: string) => {
    if (text === "Cancel Booking") {
      cancelBooking();
    } else {
      sendMessage(text);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: 0.15 }}
      className="flex flex-wrap gap-1.5 mt-3"
    >
      <div className="flex items-center gap-1.5 text-[10px] text-muted-foreground/60 w-full mb-0.5">
        <Sparkles className="h-3 w-3" />
        <span className="uppercase tracking-wider font-medium">Quick Actions</span>
      </div>
      {suggestions.map((text, i) => {
        const Icon = CHIP_ICONS[text];
        const isCancel = text === "Cancel Booking";
        return (
          <motion.button
            key={text}
            initial={{ opacity: 0, scale: 0.92 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.2, delay: 0.04 * i }}
            whileHover={{ scale: 1.04, y: -1 }}
            whileTap={{ scale: 0.96 }}
            disabled={isLoading}
            onClick={() => handleClick(text)}
            className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-[11px] font-medium shadow-sm transition-all duration-200 disabled:opacity-50 disabled:pointer-events-none ${
              isCancel
                ? "border-destructive/30 text-destructive hover:bg-destructive/5 hover:border-destructive/50"
                : "bg-background text-foreground/80 hover:bg-accent hover:text-accent-foreground hover:border-primary/30 hover:shadow-md hover:shadow-primary/5"
            }`}
          >
            {Icon && <Icon className="h-3 w-3" />}
            {text}
          </motion.button>
        );
      })}
    </motion.div>
  );
}
