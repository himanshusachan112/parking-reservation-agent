"use client";

import { motion } from "framer-motion";
import { CheckCircle2, XCircle, Clock } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useAdminStore } from "@/store/adminStore";
import { formatRelativeTime } from "@/lib/helpers";
import type { Reservation } from "@/types";

const statusConfig = {
  approved: {
    icon: CheckCircle2,
    color: "text-emerald-600 dark:text-emerald-400",
    bg: "bg-emerald-500/10",
    label: "approved",
  },
  rejected: {
    icon: XCircle,
    color: "text-red-600 dark:text-red-400",
    bg: "bg-red-500/10",
    label: "rejected",
  },
  pending: {
    icon: Clock,
    color: "text-yellow-600 dark:text-yellow-400",
    bg: "bg-yellow-500/10",
    label: "submitted",
  },
};

export function ActivityFeed() {
  const reservations = useAdminStore((s) => s.reservations);

  // Show the 10 most recent
  const recent = [...reservations]
    .sort(
      (a, b) =>
        new Date(b.updated_at || b.created_at || "").getTime() -
        new Date(a.updated_at || a.created_at || "").getTime()
    )
    .slice(0, 10);

  return (
    <Card className="border bg-card/50 backdrop-blur-sm">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium">Recent Activity</CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        <ScrollArea className="h-[320px]">
          <div className="px-4 pb-4 space-y-1">
            {recent.map((r, i) => (
              <ActivityItem key={r.id} reservation={r} index={i} />
            ))}
            {recent.length === 0 && (
              <p className="text-sm text-muted-foreground text-center py-8">
                No activity yet
              </p>
            )}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}

function ActivityItem({
  reservation: r,
  index,
}: {
  reservation: Reservation;
  index: number;
}) {
  const config = statusConfig[r.status];
  const Icon = config.icon;
  const timestamp = r.updated_at || r.created_at || "";

  return (
    <motion.div
      initial={{ opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.04 }}
      className="flex items-start gap-3 rounded-lg p-2 hover:bg-muted/50 transition-colors"
    >
      <div
        className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full ${config.bg}`}
      >
        <Icon className={`h-3.5 w-3.5 ${config.color}`} />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm">
          <span className="font-medium">
            {r.first_name} {r.last_name}
          </span>{" "}
          <span className="text-muted-foreground">
            reservation {config.label}
          </span>
        </p>
        <p className="text-xs text-muted-foreground mt-0.5">
          #{r.id} &middot; {r.car_number} &middot;{" "}
          {timestamp ? formatRelativeTime(timestamp) : "—"}
        </p>
      </div>
    </motion.div>
  );
}
