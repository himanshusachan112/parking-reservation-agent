"use client";

import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  Calculator,
  Calendar,
  CalendarCheck,
  Car,
  Clock,
  IndianRupee,
  Layers,
  MapPin,
  RefreshCw,
  Tag,
  User,
} from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ─── Types ────────────────────────────────────────────────────────────────────

interface PriceResult {
  space_type?: string;
  total_inr: number;
  unit_price: number;
  duration_label: string;
  duration_hours: number;
  currency: string;
  formatted: string;
}

interface AvailabilityInfo {
  name: string;
  available_slots: number;
  total_slots: number;
  is_available: boolean;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatDisplayDate(dt: string): string {
  const d = new Date(dt.trim().replace(" ", "T"));
  if (isNaN(d.getTime())) return dt;
  return d.toLocaleString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: true,
  });
}

function formatDuration(hours: number): string {
  if (hours < 1) return "< 1 hour";
  const h = Math.floor(hours);
  const m = Math.round((hours - h) * 60);
  if (m === 0) return `${h} hour${h !== 1 ? "s" : ""}`;
  return `${h}h ${m}m`;
}

function getPricingModel(label: string): string {
  const l = label.toLowerCase();
  if (l.includes("/hr") || l.includes("hour")) return "Hourly";
  if (l.includes("/day") || l.includes("day")) return "Daily";
  if (l.includes("/month") || l.includes("month")) return "Monthly";
  return "Standard";
}

function formatRate(unitPrice: number, label: string): string {
  const l = label.toLowerCase();
  const fmt = `₹${unitPrice.toLocaleString("en-IN")}`;
  if (l.includes("/hr") || l.includes("hour")) return `${fmt}/hr`;
  if (l.includes("/day") || l.includes("day")) return `${fmt}/day`;
  if (l.includes("/month") || l.includes("month")) return `${fmt}/month`;
  return fmt;
}

function Row({
  icon: Icon,
  label,
  value,
  valueClass,
}: {
  icon: React.ElementType;
  label: string;
  value: string;
  valueClass?: string;
}) {
  return (
    <div className="flex items-center justify-between gap-3">
      <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground shrink-0">
        <Icon className="h-3 w-3 shrink-0" />
        {label}
      </div>
      <span className={`text-[11px] font-medium text-foreground text-right ${valueClass ?? ""}`}>
        {value}
      </span>
    </div>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

export interface BookingSummaryCardProps {
  spaceType: string;
  spaceName?: string;
  startDatetime: string;
  endDatetime: string;
  name?: string;
  vehicle?: string;
}

export function BookingSummaryCard({
  spaceType,
  spaceName,
  startDatetime,
  endDatetime,
  name,
  vehicle,
}: BookingSummaryCardProps) {
  const [result, setResult] = useState<PriceResult | null>(null);
  const [avail, setAvail] = useState<AvailabilityInfo | null>(null);
  const [loading, setLoading] = useState<boolean>(
    Boolean(spaceType && startDatetime && endDatetime)
  );
  const [error, setError] = useState<string | null>(null);
  // Increment to force a retry fetch
  const [retryCount, setRetryCount] = useState(0);

  useEffect(() => {
    if (!spaceType || !startDatetime || !endDatetime) return;

    // Normalise to "YYYY-MM-DD HH:MM" (strip T, seconds, timezone)
    const normalise = (s: string) => s.replace("T", " ").slice(0, 16);
    const start = normalise(startDatetime);
    const end = normalise(endDatetime);

    const startMs = Date.parse(start.replace(" ", "T"));
    const endMs = Date.parse(end.replace(" ", "T"));
    if (isNaN(startMs) || isNaN(endMs) || endMs <= startMs) return;
    if ((endMs - startMs) / 3_600_000 < 1) return;

    // AbortController lets cleanup cancel in-flight requests (handles React
    // Strict Mode double-invocation and dep-change races).
    const controller = new AbortController();
    const { signal } = controller;

    setResult(null);
    setAvail(null);
    setLoading(true);
    setError(null);

    const payload = { space_type: spaceType, start_datetime: start, end_datetime: end };
    console.log("[BookingSummary] Pricing request →", payload);

    Promise.all([
      // ── Pricing (backend has sql_store fallback for legacy types) ──────
      fetch(`${API_BASE}/api/parking/calculate-price`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
        signal,
      }).then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status} from pricing API`);
        return r.json() as Promise<PriceResult>;
      }),
      // ── Availability (non-fatal) ──────────────────────────────────────
      fetch(`${API_BASE}/api/parking/types`, { signal })
        .then((r) => (r.ok ? r.json() : null))
        .catch(() => null),
    ])
      .then(([priceData, typesData]) => {
        // Discard results if this effect was cleaned up while awaiting
        if (signal.aborted) return;

        console.log("[BookingSummary] Pricing response ←", priceData);
        setResult(priceData);

        const apiTypes: {
          slug?: string;
          id?: string;
          name: string;
          available_slots: number;
          total_slots: number;
          is_available: boolean;
        }[] = typesData?.types ?? [];
        const found = apiTypes.find((t) => (t.slug ?? t.id) === spaceType);
        if (found) {
          setAvail({
            name: found.name,
            available_slots: found.available_slots,
            total_slots: found.total_slots,
            is_available: found.is_available,
          });
        }
      })
      .catch((err: Error) => {
        if (signal.aborted) return; // cleaned up — next run will retry
        console.error("[BookingSummary] Pricing error:", err.message);
        setError("Unable to calculate pricing right now.");
      })
      .finally(() => {
        // Always release the loading spinner — but only for THIS invocation.
        // If the signal was aborted the next effect run will reset loading itself.
        if (!signal.aborted) setLoading(false);
      });

    return () => {
      controller.abort();
    };
    // retryCount is intentionally included so the user's Retry button re-runs the fetch
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [spaceType, startDatetime, endDatetime, retryCount]);

  if (!spaceType || !startDatetime || !endDatetime) return null;

  const displayTypeName =
    spaceName ||
    avail?.name ||
    spaceType.charAt(0).toUpperCase() + spaceType.slice(1);

  return (
    <AnimatePresence>
      <motion.div
        key="booking-summary"
        initial={{ opacity: 0, y: 10, scale: 0.98 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: -10, scale: 0.98 }}
        transition={{ duration: 0.3, ease: [0.25, 0.46, 0.45, 0.94] }}
        className="mt-3 rounded-xl border border-primary/20 bg-gradient-to-br from-primary/[0.04] via-transparent to-primary/[0.02] p-4 space-y-3"
      >
        {/* Header */}
        <div className="flex items-center gap-2">
          <div className="h-7 w-7 rounded-lg bg-primary/10 flex items-center justify-center">
            <Calculator className="h-3.5 w-3.5 text-primary" />
          </div>
          <p className="text-sm font-semibold text-foreground">Booking Summary</p>
        </div>

        {/* ── Loading skeleton ── */}
        {loading && (
          <div className="space-y-2">
            {[80, 65, 70, 75, 55, 60, 70, 65].map((w, i) => (
              <div
                key={i}
                className="h-3.5 rounded bg-muted/70 animate-pulse"
                style={{ width: `${w}%` }}
              />
            ))}
            <p className="text-[10px] text-muted-foreground animate-pulse pt-1">
              Calculating pricing…
            </p>
          </div>
        )}

        {/* ── Error state with retry ── */}
        {!loading && error && (
          <div className="space-y-2">
            <p className="text-xs text-amber-600 dark:text-amber-400">{error}</p>
            <button
              onClick={() => setRetryCount((n) => n + 1)}
              className="inline-flex items-center gap-1.5 text-[11px] text-primary font-medium hover:underline"
            >
              <RefreshCw className="h-3 w-3" />
              Retry
            </button>
          </div>
        )}

        {/* ── Full summary ── */}
        {!loading && !error && result && (
          <div className="space-y-2">
            {/* Personal details */}
            {name && <Row icon={User} label="Name" value={name} />}
            {vehicle && <Row icon={Car} label="Vehicle" value={vehicle} />}
            {(name || vehicle) && <div className="h-px bg-border/60" />}

            {/* Booking details */}
            <Row icon={Tag} label="Parking Type" value={displayTypeName} />
            <Row icon={Calendar} label="Start Time" value={formatDisplayDate(startDatetime)} />
            <Row icon={CalendarCheck} label="End Time" value={formatDisplayDate(endDatetime)} />
            <Row icon={Clock} label="Duration" value={formatDuration(result.duration_hours)} />
            <Row icon={Layers} label="Pricing Model" value={getPricingModel(result.duration_label)} />
            <Row icon={IndianRupee} label="Rate" value={formatRate(result.unit_price, result.duration_label)} />

            {/* Availability */}
            {avail && (
              <Row
                icon={MapPin}
                label="Availability"
                value={
                  avail.is_available
                    ? `${avail.available_slots} slot${avail.available_slots !== 1 ? "s" : ""} available`
                    : "No slots available"
                }
                valueClass={
                  avail.is_available
                    ? "text-emerald-600 dark:text-emerald-400"
                    : "text-red-500"
                }
              />
            )}

            {/* Total */}
            <div className="h-px bg-border/60" />
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5 text-[11px] font-semibold text-foreground">
                <IndianRupee className="h-3.5 w-3.5 text-primary" />
                Estimated Total
              </div>
              <span className="text-xl font-bold text-primary tabular-nums">
                {result.formatted}
              </span>
            </div>

            <p className="text-[10px] text-muted-foreground leading-relaxed">
              Taxes included · Best tier auto-selected · Final amount at checkout
            </p>
          </div>
        )}
      </motion.div>
    </AnimatePresence>
  );
}
