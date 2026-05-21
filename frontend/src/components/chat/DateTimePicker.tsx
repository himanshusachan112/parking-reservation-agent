"use client";

import { useState, useMemo } from "react";
import { motion } from "framer-motion";
import { DayPicker } from "react-day-picker";
import { format, addHours, startOfHour, isBefore, startOfDay } from "date-fns";
import {
  CalendarDays,
  Clock,
  ChevronLeft,
  ChevronRight,
  Check,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useChatStore } from "@/store/chatStore";

// Generate time slots from 00:00 to 23:30 in 30-min increments
const TIME_SLOTS = Array.from({ length: 48 }, (_, i) => {
  const h = Math.floor(i / 2);
  const m = i % 2 === 0 ? "00" : "30";
  return `${String(h).padStart(2, "0")}:${m}`;
});

interface DateTimePickerProps {
  /** "start" or "end" — controls validation and label */
  mode: "start" | "end";
  /** Minimum selectable date (for end picker, this is the start date) */
  minDate?: Date;
}

export function DateTimePicker({ mode, minDate }: DateTimePickerProps) {
  const sendMessage = useChatStore((s) => s.sendMessage);
  const isLoading = useChatStore((s) => s.isLoading);

  const [selectedDate, setSelectedDate] = useState<Date | undefined>(undefined);
  const [selectedTime, setSelectedTime] = useState<string | undefined>(
    undefined
  );
  const [step, setStep] = useState<"date" | "time">("date");

  const isStart = mode === "start";
  const now = new Date();
  // Can't book in the past — minimum is today or minDate (whichever is later)
  const effectiveMinDate = useMemo(() => {
    const today = startOfDay(now);
    if (minDate && isBefore(today, startOfDay(minDate))) {
      return startOfDay(minDate);
    }
    return today;
  }, [minDate, now]);

  // Filter time slots: if selected date is today, disable past times
  const availableTimeSlots = useMemo(() => {
    if (!selectedDate) return TIME_SLOTS;
    const isToday =
      format(selectedDate, "yyyy-MM-dd") === format(now, "yyyy-MM-dd");
    if (!isToday) return TIME_SLOTS;

    const currentHour = now.getHours();
    const currentMin = now.getMinutes();
    return TIME_SLOTS.filter((slot) => {
      const [h, m] = slot.split(":").map(Number);
      return h > currentHour || (h === currentHour && m > currentMin);
    });
  }, [selectedDate, now]);

  const handleDateSelect = (date: Date | undefined) => {
    if (!date) return;
    setSelectedDate(date);
    setStep("time");
  };

  const handleTimeSelect = (time: string) => {
    setSelectedTime(time);
  };

  const handleConfirm = () => {
    if (!selectedDate || !selectedTime || isLoading) return;
    const formatted = `${format(selectedDate, "yyyy-MM-dd")} ${selectedTime}`;
    sendMessage(formatted);
  };

  const formattedPreview = selectedDate
    ? `${format(selectedDate, "EEE, MMM d, yyyy")}${selectedTime ? ` at ${selectedTime}` : ""}`
    : "";

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: [0.25, 0.46, 0.45, 0.94] }}
      className="mt-3 rounded-xl border bg-card overflow-hidden shadow-sm"
    >
      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-3 border-b bg-gradient-to-r from-primary/[0.04] to-transparent">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10">
          {step === "date" ? (
            <CalendarDays className="h-4 w-4 text-primary" />
          ) : (
            <Clock className="h-4 w-4 text-primary" />
          )}
        </div>
        <div>
          <p className="text-xs font-semibold text-foreground">
            {isStart ? "Select Start" : "Select End"}{" "}
            {step === "date" ? "Date" : "Time"}
          </p>
          {formattedPreview && (
            <p className="text-[10px] text-muted-foreground">
              {formattedPreview}
            </p>
          )}
        </div>
        {/* Step indicator */}
        <div className="ml-auto flex items-center gap-1.5">
          <button
            onClick={() => setStep("date")}
            className={cn(
              "h-6 w-6 rounded-full text-[10px] font-bold flex items-center justify-center transition-all",
              step === "date" || selectedDate
                ? "bg-primary text-primary-foreground"
                : "bg-muted text-muted-foreground"
            )}
          >
            {selectedDate ? <Check className="h-3 w-3" /> : "1"}
          </button>
          <div className="w-4 h-px bg-border" />
          <button
            onClick={() => selectedDate && setStep("time")}
            disabled={!selectedDate}
            className={cn(
              "h-6 w-6 rounded-full text-[10px] font-bold flex items-center justify-center transition-all",
              step === "time"
                ? "bg-primary text-primary-foreground"
                : selectedTime
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted text-muted-foreground"
            )}
          >
            {selectedTime ? <Check className="h-3 w-3" /> : "2"}
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="p-3">
        {step === "date" ? (
          <DayPicker
            mode="single"
            selected={selectedDate}
            onSelect={handleDateSelect}
            disabled={{ before: effectiveMinDate }}
            className="mx-auto"
            classNames={{
              root: "w-full",
              months: "flex flex-col",
              month: "space-y-2",
              month_caption: "flex justify-center pt-1 relative items-center text-sm font-semibold",
              nav: "flex items-center gap-1",
              button_previous:
                "absolute left-1 top-0 h-7 w-7 inline-flex items-center justify-center rounded-md border bg-transparent hover:bg-accent text-muted-foreground hover:text-foreground transition-colors",
              button_next:
                "absolute right-1 top-0 h-7 w-7 inline-flex items-center justify-center rounded-md border bg-transparent hover:bg-accent text-muted-foreground hover:text-foreground transition-colors",
              weekdays: "flex",
              weekday:
                "text-muted-foreground/60 text-[11px] font-medium w-9 text-center",
              week: "flex mt-1",
              day: "h-9 w-9 text-center text-sm relative",
              day_button:
                "h-9 w-9 rounded-lg font-medium transition-all duration-150 hover:bg-primary/10 hover:text-primary aria-selected:bg-primary aria-selected:text-primary-foreground",
              today: "font-bold text-primary",
              selected: "bg-primary text-primary-foreground rounded-lg",
              disabled: "text-muted-foreground/30 cursor-not-allowed",
              outside: "text-muted-foreground/20",
            }}
            components={{
              Chevron: ({ orientation }) =>
                orientation === "left" ? (
                  <ChevronLeft className="h-4 w-4" />
                ) : (
                  <ChevronRight className="h-4 w-4" />
                ),
            }}
          />
        ) : (
          <div className="space-y-2">
            <div className="grid grid-cols-4 sm:grid-cols-6 gap-1.5 max-h-[220px] overflow-y-auto scrollbar-thin pr-1">
              {availableTimeSlots.map((time) => (
                <button
                  key={time}
                  onClick={() => handleTimeSelect(time)}
                  className={cn(
                    "rounded-lg py-2 px-1 text-xs font-medium transition-all duration-150",
                    selectedTime === time
                      ? "bg-primary text-primary-foreground shadow-sm"
                      : "bg-muted/60 text-foreground hover:bg-primary/10 hover:text-primary"
                  )}
                >
                  {time}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between border-t px-4 py-3 bg-muted/20">
        {step === "time" && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setStep("date")}
            className="text-xs gap-1"
          >
            <ChevronLeft className="h-3 w-3" />
            Change Date
          </Button>
        )}
        {step === "date" && <div />}
        <Button
          size="sm"
          onClick={handleConfirm}
          disabled={!selectedDate || !selectedTime || isLoading}
          className="text-xs gap-1.5 rounded-lg shadow-sm ml-auto"
        >
          <Check className="h-3.5 w-3.5" />
          Confirm {isStart ? "Start" : "End"} Time
        </Button>
      </div>
    </motion.div>
  );
}

/** Detect if a bot message is asking for a start date/time. */
export function isStartDatePrompt(content: string): boolean {
  const lower = content.toLowerCase();
  return (
    lower.includes("when would you like to start") ||
    (lower.includes("start") && lower.includes("reservation") && lower.includes("date"))
  );
}

/** Detect if a bot message is asking for an end date/time. */
export function isEndDatePrompt(content: string): boolean {
  const lower = content.toLowerCase();
  return (
    lower.includes("when should the reservation end") ||
    (lower.includes("end") && lower.includes("date") && lower.includes("time"))
  );
}
