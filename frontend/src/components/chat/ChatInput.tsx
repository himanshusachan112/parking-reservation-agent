"use client";

import { useState, useRef, useEffect } from "react";
import { Send } from "lucide-react";
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
    // Reset height
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

  return (
    <div className="border-t bg-background/80 backdrop-blur-sm p-3 md:p-4">
      <div className="relative flex items-end gap-2 max-w-3xl mx-auto">
        <Textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask about parking, rates, or make a reservation..."
          disabled={disabled}
          rows={1}
          className="min-h-[44px] max-h-[160px] resize-none rounded-xl pr-12 text-sm"
        />
        <Button
          size="icon"
          onClick={handleSend}
          disabled={!value.trim() || disabled}
          className="absolute right-2 bottom-1.5 h-8 w-8 rounded-lg"
        >
          <Send className="h-4 w-4" />
          <span className="sr-only">Send</span>
        </Button>
      </div>
      <p className="text-[11px] text-muted-foreground text-center mt-2">
        ParkSmart AI can make mistakes. Verify important information.
      </p>
    </div>
  );
}
