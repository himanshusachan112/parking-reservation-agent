"use client";

import { motion } from "framer-motion";
import {
  Check,
  Circle,
  ChevronRight,
  X,
  User,
  Mail,
  Car,
  Tag,
  Clock,
  CalendarCheck,
  Shield,
} from "lucide-react";
import { useChatStore } from "@/store/chatStore";

const STEP_ICONS: Record<string, React.ElementType> = {
  name: User,
  email: Mail,
  car_number: Car,
  space_type: Tag,
  start_datetime: Clock,
  end_datetime: CalendarCheck,
  confirmation: Shield,
};

export function BookingProgressBar() {
  const bookingProgress = useChatStore((s) => s.bookingProgress);
  const cancelBooking = useChatStore((s) => s.cancelBooking);
  const isLoading = useChatStore((s) => s.isLoading);

  if (!bookingProgress?.is_booking) return null;

  const { steps, current_step } = bookingProgress;
  const progress = Math.round(
    (steps.filter((s) => s.done).length / steps.length) * 100
  );

  return (
    <motion.div
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: "auto" }}
      exit={{ opacity: 0, height: 0 }}
      transition={{ duration: 0.35, ease: [0.25, 0.46, 0.45, 0.94] }}
      className="shrink-0 border-b border-border/60 bg-gradient-to-r from-primary/[0.03] via-transparent to-primary/[0.03]"
    >
      <div className="max-w-3xl mx-auto px-4 md:px-6 py-3">
        {/* Header row */}
        <div className="flex items-center justify-between mb-2.5">
          <div className="flex items-center gap-2.5">
            <span className="text-xs font-semibold text-foreground">
              Booking Progress
            </span>
            <span className="inline-flex items-center rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-semibold text-primary tabular-nums">
              {progress}%
            </span>
          </div>
          <button
            onClick={() => cancelBooking()}
            disabled={isLoading}
            className="flex items-center gap-1 text-xs font-medium text-destructive/80 hover:text-destructive transition-colors disabled:opacity-50 cursor-pointer rounded-lg px-2 py-1 hover:bg-destructive/5"
          >
            <X className="h-3 w-3" />
            Cancel
          </button>
        </div>

        {/* Progress bar */}
        <div className="h-1 rounded-full bg-muted mb-3 overflow-hidden">
          <motion.div
            className="h-full rounded-full bg-gradient-to-r from-primary to-primary/80"
            initial={{ width: 0 }}
            animate={{ width: `${progress}%` }}
            transition={{ duration: 0.5, ease: "easeOut" }}
          />
        </div>

        {/* Steps */}
        <div className="flex items-center gap-1 overflow-x-auto pb-0.5 scrollbar-none">
          {steps.map((step, i) => {
            const isDone = step.done;
            const isCurrent = i === current_step;
            const Icon = STEP_ICONS[step.field] || Circle;

            return (
              <div key={step.field} className="flex items-center">
                {i > 0 && (
                  <div
                    className={`w-5 h-px mx-0.5 transition-colors duration-300 ${
                      isDone ? "bg-primary/50" : "bg-border"
                    }`}
                  />
                )}
                <div
                  className={`flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-[11px] font-medium whitespace-nowrap transition-all duration-300 ${
                    isDone
                      ? "bg-primary/10 text-primary"
                      : isCurrent
                        ? "bg-primary/10 text-primary ring-1 ring-primary/30 shadow-sm"
                        : "bg-muted/60 text-muted-foreground/60"
                  }`}
                >
                  {isDone ? (
                    <Check className="h-3 w-3" />
                  ) : isCurrent ? (
                    <ChevronRight className="h-3 w-3 animate-pulse" />
                  ) : (
                    <Icon className="h-3 w-3" />
                  )}
                  <span className="hidden sm:inline">{step.label}</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </motion.div>
  );
}
