"use client";

import { motion } from "framer-motion";
import {
  Car,
  Truck,
  Zap,
  Crown,
  Accessibility,
  Bike,
  Shield,
  ChevronRight,
  Sparkles,
  RefreshCw,
} from "lucide-react";
import { useChatStore } from "@/store/chatStore";
import { useEffect, useState, useCallback } from "react";

// Shape returned by GET /api/parking/types
interface ParkingTypeAPI {
  id: string;
  name: string;
  description: string;
  hourly_price: number;
  daily_price: number;
  monthly_price: number;
  features: string[];
  available_slots: number;
  total_slots: number;
  availability_percentage: number;
  is_available: boolean;
}

// Static display metadata keyed by parking type id
const TYPE_META: Record<
  string,
  {
    number: number;
    icon: React.ElementType;
    gradient: string;
    glow: string;
    badge?: string;
  }
> = {
  standard: {
    number: 1,
    icon: Car,
    gradient: "from-blue-500/10 via-blue-500/5 to-transparent",
    glow: "group-hover:shadow-blue-500/20",
  },
  large: {
    number: 2,
    icon: Truck,
    gradient: "from-amber-500/10 via-amber-500/5 to-transparent",
    glow: "group-hover:shadow-amber-500/20",
  },
  ev: {
    number: 3,
    icon: Zap,
    gradient: "from-emerald-500/10 via-emerald-500/5 to-transparent",
    glow: "group-hover:shadow-emerald-500/20",
    badge: "Eco-Friendly",
  },
  vip: {
    number: 4,
    icon: Crown,
    gradient: "from-purple-500/10 via-purple-500/5 to-transparent",
    glow: "group-hover:shadow-purple-500/20",
    badge: "Premium",
  },
  disabled: {
    number: 5,
    icon: Accessibility,
    gradient: "from-sky-500/10 via-sky-500/5 to-transparent",
    glow: "group-hover:shadow-sky-500/20",
  },
  bike: {
    number: 6,
    icon: Bike,
    gradient: "from-lime-500/10 via-lime-500/5 to-transparent",
    glow: "group-hover:shadow-lime-500/20",
  },
};

// Display-order for the 4 primary types shown in the chat
const PRIMARY_TYPES = ["standard", "large", "ev", "vip"];

/** Colour-coded slot indicator based on availability % */
function SlotBadge({
  available,
  total,
  pct,
}: {
  available: number;
  total: number;
  pct: number;
}) {
  const colour =
    pct >= 50
      ? "text-emerald-600 dark:text-emerald-400"
      : pct > 0
        ? "text-amber-600 dark:text-amber-400"
        : "text-red-600 dark:text-red-400";
  const dot =
    pct >= 50
      ? "bg-emerald-500"
      : pct > 0
        ? "bg-amber-500"
        : "bg-red-500";

  return (
    <span className={`inline-flex items-center gap-1 text-[10px] font-medium ${colour}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${dot} ${pct > 0 ? "animate-pulse" : ""}`} />
      {available}/{total} slots
    </span>
  );
}

/** Format INR price with ₹ symbol */
function formatINR(amount: number): string {
  return `₹${amount.toLocaleString("en-IN")}`;
}

interface ParkingCardsProps {
  interactive?: boolean;
}

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function ParkingCards({ interactive = true }: ParkingCardsProps) {
  const sendMessage = useChatStore((s) => s.sendMessage);
  const isLoading = useChatStore((s) => s.isLoading);

  const [types, setTypes] = useState<ParkingTypeAPI[]>([]);
  const [fetchError, setFetchError] = useState(false);

  const fetchTypes = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/parking/types`, { cache: "no-store" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const ordered: ParkingTypeAPI[] = PRIMARY_TYPES
        .map((id) => (data.types as ParkingTypeAPI[]).find((t) => t.id === id))
        .filter(Boolean) as ParkingTypeAPI[];
      setTypes(ordered);
      setFetchError(false);
    } catch {
      setFetchError(true);
    }
  }, []);

  useEffect(() => {
    fetchTypes();
    // Poll every 30 s for real-time slot updates
    const timer = setInterval(fetchTypes, 30_000);
    return () => clearInterval(timer);
  }, [fetchTypes]);

  const handleSelect = (type: ParkingTypeAPI, number: number) => {
    if (!interactive || isLoading) return;
    sendMessage(number.toString());
  };

  // Skeleton while loading
  if (types.length === 0 && !fetchError) {
    return (
      <div className="space-y-2.5 mt-2">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-20 rounded-xl bg-muted animate-pulse" />
        ))}
      </div>
    );
  }

  // If API unavailable, fall back to simple static list
  if (fetchError) {
    return (
      <div className="space-y-2 mt-2 p-3 rounded-xl border border-amber-200 bg-amber-50 dark:bg-amber-950/20 dark:border-amber-800">
        <div className="flex items-center gap-2 text-amber-700 dark:text-amber-400 text-xs font-medium">
          <RefreshCw className="h-3.5 w-3.5" />
          Pricing unavailable — please type your choice (1–4):
        </div>
        <ol className="text-xs text-muted-foreground space-y-1 ml-2 list-decimal list-inside">
          <li>Standard — ₹50/hr</li>
          <li>Large Vehicle — ₹80/hr</li>
          <li>EV Charging — ₹120/hr</li>
          <li>VIP Premium — ₹200/hr</li>
        </ol>
      </div>
    );
  }

  return (
    <div className="space-y-3 mt-2">
      <div className="flex items-center gap-2 mb-1">
        <Sparkles className="h-3.5 w-3.5 text-primary" />
        <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
          Select Parking Type
        </span>
      </div>
      <div className="grid grid-cols-1 gap-2.5">
        {types.map((type, i) => {
          const meta = TYPE_META[type.id] ?? {
            number: i + 1,
            icon: Car,
            gradient: "from-slate-500/10 via-slate-500/5 to-transparent",
            glow: "group-hover:shadow-slate-500/20",
          };
          const IconComp = meta.icon;

          return (
            <motion.button
              key={type.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: 0.06 * i }}
              whileHover={interactive ? { scale: 1.01, y: -1 } : undefined}
              whileTap={interactive ? { scale: 0.99 } : undefined}
              onClick={() => handleSelect(type, meta.number)}
              disabled={!interactive || isLoading || !type.is_available}
              className={`group relative overflow-hidden rounded-xl border bg-card text-left transition-all duration-300 hover:border-primary/30 hover:shadow-lg ${meta.glow} disabled:opacity-60 disabled:pointer-events-none`}
            >
              {/* Gradient background */}
              <div
                className={`absolute inset-0 bg-gradient-to-r ${meta.gradient} opacity-0 group-hover:opacity-100 transition-opacity duration-300`}
              />

              <div className="relative flex items-start gap-3 p-3.5">
                {/* Icon */}
                <div
                  className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br ${meta.gradient} border border-border/50 transition-transform duration-300 group-hover:scale-105`}
                >
                  <IconComp className="h-5 w-5 text-foreground/80" />
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold text-muted-foreground/60">
                        {meta.number}.
                      </span>
                      <span className="font-semibold text-sm">{type.name}</span>
                      {meta.badge && (
                        <span className="inline-flex items-center rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-semibold text-primary">
                          {meta.badge}
                        </span>
                      )}
                    </div>
                    <div className="text-right shrink-0">
                      <span className="text-base font-bold text-primary">
                        {formatINR(type.hourly_price)}
                      </span>
                      <span className="text-[11px] text-muted-foreground">/hr</span>
                    </div>
                  </div>

                  <p className="text-xs text-muted-foreground mt-0.5">
                    {type.description}
                  </p>

                  {/* Features */}
                  <div className="flex flex-wrap items-center gap-x-3 gap-y-0.5 mt-1.5">
                    {type.features.slice(0, 3).map((f) => (
                      <span
                        key={f}
                        className="inline-flex items-center gap-1 text-[10px] text-muted-foreground/80"
                      >
                        <Shield className="h-2.5 w-2.5 text-emerald-500" />
                        {f}
                      </span>
                    ))}
                  </div>

                  {/* Bottom row */}
                  <div className="flex items-center justify-between mt-2">
                    <SlotBadge
                      available={type.available_slots}
                      total={type.total_slots}
                      pct={type.availability_percentage}
                    />
                    {interactive && type.is_available && (
                      <span className="flex items-center gap-0.5 text-[10px] font-medium text-primary opacity-0 group-hover:opacity-100 transition-opacity">
                        Select
                        <ChevronRight className="h-3 w-3" />
                      </span>
                    )}
                    {!type.is_available && (
                      <span className="text-[10px] font-semibold text-red-500">
                        FULL
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </motion.button>
          );
        })}
      </div>
    </div>
  );
}

/**
 * Detect if a bot message is asking the user to select a parking type.
 */
export function isParkingTypePrompt(content: string): boolean {
  const lower = content.toLowerCase();
  return (
    (lower.includes("what type of parking") ||
      lower.includes("type of parking space")) &&
    lower.includes("standard") &&
    lower.includes("vip")
  );
}

