"use client";

import { useCallback, useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  Accessibility,
  Bike,
  Car,
  CheckCircle2,
  Crown,
  RefreshCw,
  Truck,
  Zap,
} from "lucide-react";
import { cn } from "@/lib/utils";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ─── Types ────────────────────────────────────────────────────────────────────

interface ParkingTypeOption {
  id: string;
  slug: string;
  name: string;
  description: string;
  hourly_price: number;
  daily_price: number;
  monthly_price: number | null;
  features: string[];
  available_slots: number;
  total_slots: number;
  availability_percentage: number;
  is_available: boolean;
}

// ─── Static display metadata ──────────────────────────────────────────────────

const TYPE_META: Record<
  string,
  { icon: React.ElementType; accent: string; bg: string; ring: string }
> = {
  standard: {
    icon: Car,
    accent: "text-blue-600 dark:text-blue-400",
    bg: "bg-blue-500/10",
    ring: "ring-blue-500/30",
  },
  large: {
    icon: Truck,
    accent: "text-amber-600 dark:text-amber-400",
    bg: "bg-amber-500/10",
    ring: "ring-amber-500/30",
  },
  ev: {
    icon: Zap,
    accent: "text-emerald-600 dark:text-emerald-400",
    bg: "bg-emerald-500/10",
    ring: "ring-emerald-500/30",
  },
  vip: {
    icon: Crown,
    accent: "text-purple-600 dark:text-purple-400",
    bg: "bg-purple-500/10",
    ring: "ring-purple-500/30",
  },
  disabled: {
    icon: Accessibility,
    accent: "text-sky-600 dark:text-sky-400",
    bg: "bg-sky-500/10",
    ring: "ring-sky-500/30",
  },
  bike: {
    icon: Bike,
    accent: "text-lime-600 dark:text-lime-400",
    bg: "bg-lime-500/10",
    ring: "ring-lime-500/30",
  },
};

const DEFAULT_META = {
  icon: Car,
  accent: "text-gray-600 dark:text-gray-400",
  bg: "bg-gray-500/10",
  ring: "ring-gray-500/30",
};

// ─── Availability badge ───────────────────────────────────────────────────────

function AvailabilityBadge({
  available,
  total,
  pct,
}: {
  available: number;
  total: number;
  pct: number;
}) {
  if (total === 0)
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-gray-500/10 px-2 py-0.5 text-[10px] font-semibold text-gray-500">
        Not configured
      </span>
    );

  const [cls, dot, label] =
    pct >= 50
      ? ["text-emerald-700 dark:text-emerald-400 bg-emerald-500/10", "bg-emerald-500 animate-pulse", "Available"]
      : pct > 0
        ? ["text-amber-700 dark:text-amber-400 bg-amber-500/10", "bg-amber-500 animate-pulse", "Limited"]
        : ["text-red-700 dark:text-red-400 bg-red-500/10", "bg-red-500", "Full"];

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[10px] font-semibold",
        cls
      )}
    >
      <span className={cn("h-1.5 w-1.5 rounded-full", dot)} />
      {available}/{total} slots · {label}
    </span>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

interface ParkingTypeSelectorProps {
  /** Currently selected slug */
  value: string;
  /** Called with (slug, humanName) on selection */
  onChange: (slug: string, name: string) => void;
  disabled?: boolean;
}

export function ParkingTypeSelector({
  value,
  onChange,
  disabled = false,
}: ParkingTypeSelectorProps) {
  const [types, setTypes] = useState<ParkingTypeOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const fetchTypes = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/parking/types`, {
        cache: "no-store",
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setTypes(data.types ?? []);
      setError(false);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchTypes();
    const interval = setInterval(fetchTypes, 30_000);
    window.addEventListener("parksmart:slot-stats-refresh", fetchTypes);
    return () => {
      clearInterval(interval);
      window.removeEventListener("parksmart:slot-stats-refresh", fetchTypes);
    };
  }, [fetchTypes]);

  // ── Skeleton ────────────────────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-28 rounded-xl bg-muted animate-pulse" />
        ))}
      </div>
    );
  }

  // ── Error state ─────────────────────────────────────────────────────────────
  if (error) {
    return (
      <div className="flex items-center gap-2 rounded-xl border border-amber-200 bg-amber-50 dark:bg-amber-950/20 dark:border-amber-800 p-3 text-xs text-amber-700 dark:text-amber-400">
        <RefreshCw className="h-3.5 w-3.5 shrink-0" />
        Could not load live parking data. Check your connection.
      </div>
    );
  }

  // ── Cards grid ──────────────────────────────────────────────────────────────
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
      {types.map((type, i) => {
        const meta = TYPE_META[type.slug] ?? DEFAULT_META;
        const Icon = meta.icon;
        const isSelected = value === type.slug;
        const isFull = !type.is_available && type.total_slots > 0;
        const isUnconfigured = type.total_slots === 0;
        const isDisabled = disabled || isFull || isUnconfigured;

        return (
          <motion.button
            key={type.slug}
            type="button"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.25, delay: i * 0.04 }}
            whileHover={isDisabled ? undefined : { y: -1 }}
            onClick={() => !isDisabled && onChange(type.slug, type.name)}
            disabled={isDisabled}
            className={cn(
              "relative text-left rounded-xl border-2 p-3.5 transition-all duration-200",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40",
              isSelected
                ? [
                    "border-primary bg-primary/[0.04]",
                    "shadow-sm shadow-primary/10",
                  ]
                : isDisabled
                  ? "border-border/40 bg-muted/20 opacity-50 cursor-not-allowed"
                  : [
                      "border-border/60 bg-card cursor-pointer",
                      "hover:border-primary/40 hover:bg-primary/[0.02]",
                      "hover:shadow-md hover:shadow-black/5",
                    ]
            )}
          >
            {/* Selected indicator */}
            {isSelected && (
              <motion.div
                initial={{ scale: 0, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                className="absolute top-2.5 right-2.5"
              >
                <CheckCircle2 className="h-4 w-4 text-primary" />
              </motion.div>
            )}

            {/* Icon + name row */}
            <div className="flex items-start gap-3">
              <div
                className={cn(
                  "h-10 w-10 rounded-lg flex items-center justify-center shrink-0",
                  meta.bg
                )}
              >
                <Icon className={cn("h-5 w-5", meta.accent)} />
              </div>

              <div className="min-w-0 flex-1 pr-5">
                <p className="text-sm font-semibold text-foreground leading-tight">
                  {type.name}
                </p>
                {type.description && (
                  <p className="text-[11px] text-muted-foreground mt-0.5 line-clamp-1">
                    {type.description}
                  </p>
                )}

                {/* Pricing */}
                <div className="flex items-baseline gap-1.5 mt-1.5">
                  <span className="text-sm font-bold text-foreground">
                    ₹{type.hourly_price.toLocaleString("en-IN")}
                    <span className="text-xs font-normal text-muted-foreground">
                      /hr
                    </span>
                  </span>
                  {type.daily_price > 0 && (
                    <span className="text-[11px] text-muted-foreground">
                      · ₹{type.daily_price.toLocaleString("en-IN")}/day
                    </span>
                  )}
                </div>
              </div>
            </div>

            {/* Availability badge */}
            <div className="mt-2.5">
              <AvailabilityBadge
                available={type.available_slots}
                total={type.total_slots}
                pct={type.availability_percentage}
              />
            </div>

            {/* Feature pills */}
            {type.features && type.features.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1">
                {type.features.slice(0, 3).map((f) => (
                  <span
                    key={f}
                    className="inline-block rounded-md bg-muted px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground"
                  >
                    {f}
                  </span>
                ))}
              </div>
            )}
          </motion.button>
        );
      })}
    </div>
  );
}
