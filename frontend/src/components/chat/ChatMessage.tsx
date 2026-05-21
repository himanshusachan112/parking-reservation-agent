"use client";

import { motion } from "framer-motion";
import { Bot, User, CheckCircle2 } from "lucide-react";
import ReactMarkdown from "react-markdown";
import { cn } from "@/lib/utils";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { SuggestionChips } from "./SuggestionChips";
import { ParkingCards, isParkingTypePrompt } from "./ParkingCards";
import {
  DateTimePicker,
  isStartDatePrompt,
  isEndDatePrompt,
} from "./DateTimePicker";
import {
  ConfirmationButtons,
  isConfirmationPrompt,
} from "./ConfirmationButtons";
import { BookingSummaryCard } from "./BookingSummaryCard";
import type { ChatMessage as ChatMessageType } from "@/types";

interface ChatMessageProps {
  message: ChatMessageType;
  isLatest?: boolean;
}

/** Parse booking details out of the chatbot's confirmation message. */
function extractBookingDetails(content: string) {
  const typeMatch = content.match(/Space Type:\s*(\S+)/i);
  const fromMatch = content.match(/From:\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})/i);
  const toMatch = content.match(/To:\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})/i);
  if (!typeMatch || !fromMatch || !toMatch) return null;
  // Extract name and vehicle (stop at bullet • or newline)
  const nameMatch = content.match(/Name:\s*([^\u2022\n\r]+)/i);
  const vehicleMatch = content.match(/Vehicle:\s*([^\u2022\n\r]+)/i);
  return {
    spaceType: typeMatch[1].toLowerCase().trim(),
    startDatetime: fromMatch[1].trim(),
    endDatetime: toMatch[1].trim(),
    name: nameMatch ? nameMatch[1].trim() : undefined,
    vehicle: vehicleMatch ? vehicleMatch[1].trim() : undefined,
  };
}

export function ChatMessage({ message, isLatest }: ChatMessageProps) {
  const isUser = message.role === "user";
  const showParkingCards =
    !isUser && isLatest && isParkingTypePrompt(message.content);
  const showStartDatePicker =
    !isUser && isLatest && isStartDatePrompt(message.content);
  const showEndDatePicker =
    !isUser && isLatest && isEndDatePrompt(message.content);
  const showConfirmation =
    !isUser && isLatest && isConfirmationPrompt(message.content);
  const isConfirmation =
    !isUser && message.content.includes("reservation request has been submitted");

  // Extract booking details for price estimate on confirmation step
  const confirmationDetails =
    showConfirmation ? extractBookingDetails(message.content) : null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: [0.25, 0.46, 0.45, 0.94] }}
      className={cn(
        "flex gap-3 px-4 md:px-6 py-3",
        isUser && "flex-row-reverse"
      )}
    >
      {/* Avatar */}
      <Avatar className={cn("h-8 w-8 shrink-0 mt-1 shadow-sm", isUser ? "ring-2 ring-primary/20" : "ring-2 ring-emerald-500/20")}>
        <AvatarFallback
          className={cn(
            "text-xs font-semibold",
            isUser
              ? "bg-gradient-to-br from-primary to-primary/80 text-primary-foreground"
              : "bg-gradient-to-br from-emerald-500/15 to-emerald-600/10 text-emerald-600 dark:text-emerald-400"
          )}
        >
          {isUser ? (
            <User className="h-4 w-4" />
          ) : (
            <Bot className="h-4 w-4" />
          )}
        </AvatarFallback>
      </Avatar>

      {/* Message bubble */}
      <div
        className={cn(
          "max-w-[80%] md:max-w-[75%] text-sm leading-relaxed",
          isUser
            ? "rounded-2xl rounded-br-md bg-primary text-primary-foreground px-4 py-2.5 shadow-sm shadow-primary/10"
            : "rounded-2xl rounded-bl-md bg-muted/60 backdrop-blur-sm border border-border/40 px-4 py-3",
          isConfirmation &&
            "border-emerald-500/30 bg-emerald-500/5"
        )}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap">{message.content}</p>
        ) : (
          <div className="space-y-2">
            {/* Success icon for confirmations */}
            {isConfirmation && (
              <div className="flex items-center gap-2 text-emerald-600 dark:text-emerald-400 mb-1">
                <CheckCircle2 className="h-4 w-4" />
                <span className="text-xs font-semibold uppercase tracking-wider">
                  Booking Confirmed
                </span>
              </div>
            )}

            {/* Markdown content */}
            <div className="prose prose-sm dark:prose-invert max-w-none prose-p:my-1.5 prose-ul:my-1.5 prose-li:my-0.5 prose-headings:my-2 prose-strong:text-foreground prose-a:text-primary">
              <ReactMarkdown>{message.content}</ReactMarkdown>
            </div>

            {/* Parking type cards (replaces plain text list) */}
            {showParkingCards && <ParkingCards />}

            {/* Date/time picker for reservation dates */}
            {showStartDatePicker && <DateTimePicker mode="start" />}
            {showEndDatePicker && <DateTimePicker mode="end" />}

            {/* Price estimate on confirmation step */}
            {showConfirmation && confirmationDetails && (
              <BookingSummaryCard
                spaceType={confirmationDetails.spaceType}
                startDatetime={confirmationDetails.startDatetime}
                endDatetime={confirmationDetails.endDatetime}
                name={confirmationDetails.name}
                vehicle={confirmationDetails.vehicle}
              />
            )}

            {/* Confirmation buttons for booking review */}
            {showConfirmation && <ConfirmationButtons />}
          </div>
        )}

        {/* Timestamp */}
        <p
          className={cn(
            "text-[10px] mt-2 select-none",
            isUser
              ? "text-primary-foreground/50 text-right"
              : "text-muted-foreground/60"
          )}
        >
          {message.timestamp.toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
          })}
        </p>

        {/* Suggestion chips */}
        {!isUser &&
          isLatest &&
          message.suggestions &&
          message.suggestions.length > 0 && (
            <SuggestionChips suggestions={message.suggestions} />
          )}
      </div>
    </motion.div>
  );
}

