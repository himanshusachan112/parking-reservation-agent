"use client";

import { motion } from "framer-motion";
import {
  Car,
  Truck,
  Zap,
  Crown,
  Shield,
  Camera,
  ChevronRight,
  Sparkles,
} from "lucide-react";
import { useChatStore } from "@/store/chatStore";

interface ParkingType {
  id: string;
  number: number;
  name: string;
  price: string;
  priceUnit: string;
  description: string;
  features: string[];
  icon: React.ElementType;
  gradient: string;
  glow: string;
  slots: string;
  badge?: string;
}

const PARKING_TYPES: ParkingType[] = [
  {
    id: "standard",
    number: 1,
    name: "Standard Parking",
    price: "$3",
    priceUnit: "/hour",
    description: "Perfect for sedans, hatchbacks & small SUVs",
    features: ["Covered area", "CCTV security", "350 total spaces"],
    icon: Car,
    gradient: "from-blue-500/10 via-blue-500/5 to-transparent",
    glow: "group-hover:shadow-blue-500/20",
    slots: "45 available",
  },
  {
    id: "large",
    number: 2,
    name: "Large Vehicle",
    price: "$5",
    priceUnit: "/hour",
    description: "For SUVs, pickup trucks & small vans",
    features: ["Extra wide spaces", "Floor 4 dedicated", "80 total spaces"],
    icon: Truck,
    gradient: "from-amber-500/10 via-amber-500/5 to-transparent",
    glow: "group-hover:shadow-amber-500/20",
    slots: "55 available",
  },
  {
    id: "ev",
    number: 3,
    name: "EV Charging",
    price: "$4",
    priceUnit: "/hour",
    description: "Level 2 + Tesla Supercharger included",
    features: ["Free charging", "Floor 2 Section EV", "40 total spaces"],
    icon: Zap,
    gradient: "from-emerald-500/10 via-emerald-500/5 to-transparent",
    glow: "group-hover:shadow-emerald-500/20",
    slots: "22 available",
    badge: "Eco-Friendly",
  },
  {
    id: "vip",
    number: 4,
    name: "VIP Premium",
    price: "$500",
    priceUnit: "/month",
    description: "Premium covered parking near entrance",
    features: ["Covered & extra-wide", "Near main exit", "Priority access"],
    icon: Crown,
    gradient: "from-purple-500/10 via-purple-500/5 to-transparent",
    glow: "group-hover:shadow-purple-500/20",
    slots: "3 available",
    badge: "Premium",
  },
];

interface ParkingCardsProps {
  interactive?: boolean;
}

export function ParkingCards({ interactive = true }: ParkingCardsProps) {
  const sendMessage = useChatStore((s) => s.sendMessage);
  const isLoading = useChatStore((s) => s.isLoading);

  const handleSelect = (type: ParkingType) => {
    if (!interactive || isLoading) return;
    sendMessage(type.number.toString());
  };

  return (
    <div className="space-y-3 mt-2">
      <div className="flex items-center gap-2 mb-1">
        <Sparkles className="h-3.5 w-3.5 text-primary" />
        <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
          Select Parking Type
        </span>
      </div>
      <div className="grid grid-cols-1 gap-2.5">
        {PARKING_TYPES.map((type, i) => (
          <motion.button
            key={type.id}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: 0.06 * i }}
            whileHover={interactive ? { scale: 1.01, y: -1 } : undefined}
            whileTap={interactive ? { scale: 0.99 } : undefined}
            onClick={() => handleSelect(type)}
            disabled={!interactive || isLoading}
            className={`group relative overflow-hidden rounded-xl border bg-card text-left transition-all duration-300 hover:border-primary/30 hover:shadow-lg ${type.glow} disabled:opacity-70 disabled:pointer-events-none`}
          >
            {/* Gradient background */}
            <div
              className={`absolute inset-0 bg-gradient-to-r ${type.gradient} opacity-0 group-hover:opacity-100 transition-opacity duration-300`}
            />

            <div className="relative flex items-start gap-3 p-3.5">
              {/* Icon container */}
              <div
                className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br ${type.gradient} border border-border/50 transition-transform duration-300 group-hover:scale-105`}
              >
                <type.icon className="h-5 w-5 text-foreground/80" />
              </div>

              {/* Content */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-muted-foreground/60">
                      {type.number}.
                    </span>
                    <span className="font-semibold text-sm">{type.name}</span>
                    {type.badge && (
                      <span className="inline-flex items-center rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-semibold text-primary">
                        {type.badge}
                      </span>
                    )}
                  </div>
                  <div className="text-right shrink-0">
                    <span className="text-base font-bold text-primary">
                      {type.price}
                    </span>
                    <span className="text-[11px] text-muted-foreground">
                      {type.priceUnit}
                    </span>
                  </div>
                </div>

                <p className="text-xs text-muted-foreground mt-0.5">
                  {type.description}
                </p>

                {/* Features */}
                <div className="flex flex-wrap items-center gap-x-3 gap-y-0.5 mt-1.5">
                  {type.features.map((f) => (
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
                  <span className="inline-flex items-center gap-1 text-[10px] font-medium text-emerald-600 dark:text-emerald-400">
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
                    {type.slots}
                  </span>
                  {interactive && (
                    <span className="flex items-center gap-0.5 text-[10px] font-medium text-primary opacity-0 group-hover:opacity-100 transition-opacity">
                      Select
                      <ChevronRight className="h-3 w-3" />
                    </span>
                  )}
                </div>
              </div>
            </div>
          </motion.button>
        ))}
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
