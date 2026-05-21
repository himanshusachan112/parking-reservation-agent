"use client";

import { useState, useRef, useEffect } from "react";
import { Send, Loader2, Mic } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
}

export function ChatInput({ onSend, disabled }: ChatInputProps) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = () => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Auto-resize textarea
  useEffect(() => {
    const ta = textareaRef.current;
    if (ta) {
      ta.style.height = "auto";
      ta.style.height = `${Math.min(ta.scrollHeight, 160)}px`;
    }
  }, [value]);

  // Focus input when loading finishes
  useEffect(() => {
    if (!disabled && textareaRef.current) {
      textareaRef.current.focus();
    }
  }, [disabled]);

  return (
    <div className="shrink-0 border-t bg-background/90 backdrop-blur-xl p-3 md:p-4">
      <div className="relative max-w-3xl mx-auto">
        <div className="relative flex items-end gap-2 rounded-2xl border bg-card shadow-sm focus-within:ring-2 focus-within:ring-primary/20 focus-within:border-primary/40 transition-all duration-200">
          <Textarea
            ref={textareaRef}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              disabled
                ? "ParkSmart AI is thinking..."
                : "Ask about parking, rates, or make a reservation..."
            }
            disabled={disabled}
            rows={1}
            className="min-h-[48px] max-h-[160px] resize-none border-0 bg-transparent pr-24 text-sm focus-visible:ring-0 focus-visible:ring-offset-0 rounded-2xl pl-4 py-3.5"
          />
          <div className="absolute right-2 bottom-2 flex items-center gap-1">
            <Button
              size="icon"
              variant="ghost"
              className="h-8 w-8 rounded-xl text-muted-foreground hover:text-foreground"
              disabled
              title="Voice input coming soon"
            >
              <Mic className="h-4 w-4" />
            </Button>
            <Button
              size="icon"
              onClick={handleSend}
              disabled={!value.trim() || disabled}
              className="h-8 w-8 rounded-xl bg-primary hover:bg-primary/90 shadow-sm"
            >
              {disabled ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
              <span className="sr-only">Send</span>
            </Button>
          </div>
        </div>
        <p className="text-[10px] text-muted-foreground/50 text-center mt-2">
          ParkSmart AI can make mistakes. Verify important information.
        </p>
      </div>
    </div>
  );
}
