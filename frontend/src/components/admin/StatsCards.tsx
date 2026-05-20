"use client";

import { motion } from "framer-motion";
import {
  Clock,
  CheckCircle2,
  XCircle,
  LayoutList,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { useAdminStore } from "@/store/adminStore";
import { useMemo } from "react";

const statConfig = [
  {
    key: "total" as const,
    label: "Total",
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

export function StatsCards() {
  const reservations = useAdminStore((s) => s.reservations);
  const stats = useMemo(() => ({
    total: reservations.length,
    pending: reservations.filter((r) => r.status === "pending").length,
    approved: reservations.filter((r) => r.status === "approved").length,
    rejected: reservations.filter((r) => r.status === "rejected").length,
  }), [reservations]);

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      {statConfig.map((item, i) => (
        <motion.div
          key={item.key}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: i * 0.08 }}
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
            {/* Decorative gradient */}
            <div
              className={`absolute bottom-0 left-0 right-0 h-0.5 ${item.bg}`}
            />
          </Card>
        </motion.div>
      ))}
    </div>
  );
}
