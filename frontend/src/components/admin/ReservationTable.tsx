"use client";

import { useMemo } from "react";
import { Eye, CheckCircle, XCircle } from "lucide-react";
import { motion } from "framer-motion";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { EmptyState } from "@/components/shared/EmptyState";
import { useAdminStore } from "@/store/adminStore";
import { formatDateTime, maskEmail, spaceTypeLabels } from "@/lib/helpers";
import { Inbox } from "lucide-react";
import type { Reservation } from "@/types";

export function ReservationTable() {
  const allReservations = useAdminStore((s) => s.reservations);
  const filterStatus = useAdminStore((s) => s.filterStatus);
  const searchQuery = useAdminStore((s) => s.searchQuery);
  const isLoading = useAdminStore((s) => s.isLoading);

  const reservations = useMemo(() => {
    let filtered = allReservations;
    if (filterStatus !== "all") {
      filtered = filtered.filter((r) => r.status === filterStatus);
    }
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      filtered = filtered.filter(
        (r) =>
          r.first_name.toLowerCase().includes(q) ||
          r.last_name.toLowerCase().includes(q) ||
          r.car_number.toLowerCase().includes(q) ||
          r.id.toString().includes(q)
      );
    }
    return filtered.sort(
      (a, b) =>
        new Date(b.created_at || "").getTime() -
        new Date(a.created_at || "").getTime()
    );
  }, [allReservations, filterStatus, searchQuery]);
  const setSelected = useAdminStore((s) => s.setSelectedReservation);

  if (isLoading && reservations.length === 0) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-14 w-full rounded-lg" />
        ))}
      </div>
    );
  }

  if (reservations.length === 0) {
    return (
      <EmptyState
        icon={Inbox}
        title="No reservations found"
        description="No reservations match your current filters."
      />
    );
  }

  return (
    <div className="rounded-xl border bg-card/50 backdrop-blur-sm overflow-hidden">
      <Table>
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            <TableHead className="w-[60px]">ID</TableHead>
            <TableHead>Name</TableHead>
            <TableHead className="hidden md:table-cell">Email</TableHead>
            <TableHead className="hidden sm:table-cell">Vehicle</TableHead>
            <TableHead className="hidden lg:table-cell">Type</TableHead>
            <TableHead className="hidden lg:table-cell">Period</TableHead>
            <TableHead>Status</TableHead>
            <TableHead className="text-right">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {reservations.map((r, i) => (
            <ReservationRow
              key={r.id}
              reservation={r}
              index={i}
              onView={() => setSelected(r)}
            />
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

function ReservationRow({
  reservation: r,
  index,
  onView,
}: {
  reservation: Reservation;
  index: number;
  onView: () => void;
}) {
  const approve = useAdminStore((s) => s.approveReservation);
  const reject = useAdminStore((s) => s.rejectReservation);

  return (
    <motion.tr
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.03 }}
      className="group border-b transition-colors hover:bg-muted/50"
    >
      <TableCell className="font-mono text-xs text-muted-foreground">
        #{r.id}
      </TableCell>
      <TableCell className="font-medium">
        {r.first_name} {r.last_name}
      </TableCell>
      <TableCell className="hidden md:table-cell text-muted-foreground text-sm">
        {r.email ? maskEmail(r.email) : "—"}
      </TableCell>
      <TableCell className="hidden sm:table-cell font-mono text-sm">
        {r.car_number}
      </TableCell>
      <TableCell className="hidden lg:table-cell text-sm">
        {spaceTypeLabels[r.space_type] || r.space_type}
      </TableCell>
      <TableCell className="hidden lg:table-cell text-sm text-muted-foreground">
        {formatDateTime(r.start_datetime)}
      </TableCell>
      <TableCell>
        <StatusBadge status={r.status} />
      </TableCell>
      <TableCell className="text-right">
        <div className="flex items-center justify-end gap-1">
          <Button variant="ghost" size="icon" className="h-8 w-8" onClick={onView}>
            <Eye className="h-4 w-4" />
          </Button>
          {r.status === "pending" && (
            <>
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8 text-emerald-600 hover:text-emerald-700 hover:bg-emerald-500/10"
                onClick={() => approve(r.id)}
              >
                <CheckCircle className="h-4 w-4" />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8 text-red-600 hover:text-red-700 hover:bg-red-500/10"
                onClick={() => reject(r.id)}
              >
                <XCircle className="h-4 w-4" />
              </Button>
            </>
          )}
        </div>
      </TableCell>
    </motion.tr>
  );
}
