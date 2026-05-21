"use client";

import { motion } from "framer-motion";
import {
  Clock,
  CheckCircle2,
  XCircle,
  LayoutList,
  Car,
  ParkingCircle,
  AlertCircle,
  CircleDot,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { useAdminStore } from "@/store/adminStore";
import { useMemo, useEffect, useState } from "react";
import api from "@/lib/api";

const reservationStatConfig = [
  {
    key: "total" as const,
    label: "Total Reservations",
    icon: LayoutList,
    color: "text-blue-600 dark:text-blue-400",
    bg: "bg-blue-500/10",
  },
  {
    key: "pending" as const,
    label: "Pending",
    icon: Clock,
    color: "text-yellow-600 dark:text-yellow-400",
    bg: "bg-yellow-500/10",
  },
  {
    key: "approved" as const,
    label: "Approved",
    icon: CheckCircle2,
    color: "text-emerald-600 dark:text-emerald-400",
    bg: "bg-emerald-500/10",
  },
  {
    key: "rejected" as const,
    label: "Rejected",
    icon: XCircle,
    color: "text-red-600 dark:text-red-400",
    bg: "bg-red-500/10",
  },
];

interface DashboardTotals {
  total_slots: number;
  available_slots: number;
  occupied_slots: number;
  pending_slots: number;
}

export function StatsCards() {
  const reservations = useAdminStore((s) => s.reservations);
  const stats = useMemo(() => ({
    total: reservations.length,
    pending: reservations.filter((r) => r.status === "pending").length,
    approved: reservations.filter((r) => r.status === "approved").length,
    rejected: reservations.filter((r) => r.status === "rejected").length,
  }), [reservations]);

  const [slotTotals, setSlotTotals] = useState<DashboardTotals | null>(null);

  useEffect(() => {
    const fetchSlots = async () => {
      try {
        const { data } = await api.get("/api/admin/dashboard");
        setSlotTotals(data.totals);
      } catch {
        // non-critical
      }
    };
    fetchSlots();
    const interval = setInterval(fetchSlots, 10_000);

    // Immediate refresh when admin approves / rejects
    window.addEventListener("parksmart:slot-stats-refresh", fetchSlots);
    return () => {
      clearInterval(interval);
      window.removeEventListener("parksmart:slot-stats-refresh", fetchSlots);
    };
  }, []);

  const slotStatConfig = [
    {
      label: "Total Slots",
      value: slotTotals?.total_slots ?? "—",
      icon: Car,
      color: "text-indigo-600 dark:text-indigo-400",
      bg: "bg-indigo-500/10",
    },
    {
      label: "Available",
      value: slotTotals?.available_slots ?? "—",
      icon: ParkingCircle,
      color: "text-emerald-600 dark:text-emerald-400",
      bg: "bg-emerald-500/10",
    },
    {
      label: "Occupied",
      value: slotTotals?.occupied_slots ?? "—",
      icon: CircleDot,
      color: "text-orange-600 dark:text-orange-400",
      bg: "bg-orange-500/10",
    },
    {
      label: "Pending Slots",
      value: slotTotals?.pending_slots ?? "—",
      icon: AlertCircle,
      color: "text-yellow-600 dark:text-yellow-400",
      bg: "bg-yellow-500/10",
    },
  ];

  return (
    <div className="space-y-4">
      {/* Reservation stats */}
      <div>
        <p className="text-xs font-semibold text-muted-foreground uppercase tracking-widest mb-2 px-0.5">
          Reservations
        </p>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {reservationStatConfig.map((item, i) => (
            <motion.div
              key={item.key}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.06 }}
            >
              <Card className="relative overflow-hidden border bg-card/50 backdrop-blur-sm">
                <CardContent className="p-4 md:p-5">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                        {item.label}
                      </p>
                      <p className="text-2xl md:text-3xl font-bold mt-1">
                        {stats[item.key]}
                      </p>
                    </div>
                    <div className={`flex h-10 w-10 items-center justify-center rounded-xl ${item.bg}`}>
                      <item.icon className={`h-5 w-5 ${item.color}`} />
                    </div>
                  </div>
                </CardContent>
                <div className={`absolute bottom-0 left-0 right-0 h-0.5 ${item.bg}`} />
              </Card>
            </motion.div>
          ))}
        </div>
      </div>

      {/* Live slot inventory */}
      <div>
        <p className="text-xs font-semibold text-muted-foreground uppercase tracking-widest mb-2 px-0.5">
          Live Slot Inventory
        </p>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {slotStatConfig.map((item, i) => (
            <motion.div
              key={item.label}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.24 + i * 0.06 }}
            >
              <Card className="relative overflow-hidden border bg-card/50 backdrop-blur-sm">
                <CardContent className="p-4 md:p-5">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                        {item.label}
                      </p>
                      <p className="text-2xl md:text-3xl font-bold mt-1">
                        {item.value}
                      </p>
                    </div>
                    <div className={`flex h-10 w-10 items-center justify-center rounded-xl ${item.bg}`}>
                      <item.icon className={`h-5 w-5 ${item.color}`} />
                    </div>
                  </div>
                </CardContent>
                <div className={`absolute bottom-0 left-0 right-0 h-0.5 ${item.bg}`} />
              </Card>
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  );
}
