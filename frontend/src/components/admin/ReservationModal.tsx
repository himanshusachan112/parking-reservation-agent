"use client";

import { useState } from "react";
import { CheckCircle, XCircle, Car, Mail, Calendar, User, StickyNote } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { useAdminStore } from "@/store/adminStore";
import { formatDateTime, maskEmail, spaceTypeLabels } from "@/lib/helpers";

export function ReservationModal() {
  const reservation = useAdminStore((s) => s.selectedReservation);
  const setSelected = useAdminStore((s) => s.setSelectedReservation);
  const approve = useAdminStore((s) => s.approveReservation);
  const reject = useAdminStore((s) => s.rejectReservation);
  const isLoading = useAdminStore((s) => s.isLoading);
  const [notes, setNotes] = useState("");

  if (!reservation) return null;

  const r = reservation;

  const handleAction = async (action: "approve" | "reject") => {
    if (action === "approve") {
      await approve(r.id, notes || undefined);
    } else {
      await reject(r.id, notes || undefined);
    }
    setNotes("");
  };

  return (
    <Dialog open={!!reservation} onOpenChange={() => setSelected(null)}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            Reservation #{r.id}
            <StatusBadge status={r.status} />
          </DialogTitle>
          <DialogDescription>
            Submitted {formatDateTime(r.created_at)}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 mt-2">
          {/* Details grid */}
          <div className="grid grid-cols-2 gap-4">
            <DetailItem
              icon={User}
              label="Name"
              value={`${r.first_name} ${r.last_name}`}
            />
            <DetailItem
              icon={Mail}
              label="Email"
              value={r.email ? maskEmail(r.email) : "—"}
            />
            <DetailItem icon={Car} label="Vehicle" value={r.car_number} />
            <DetailItem
              icon={Car}
              label="Type"
              value={spaceTypeLabels[r.space_type] || r.space_type}
            />
            <DetailItem
              icon={Calendar}
              label="Start"
              value={formatDateTime(r.start_datetime)}
            />
            <DetailItem
              icon={Calendar}
              label="End"
              value={formatDateTime(r.end_datetime)}
            />
          </div>

          {r.admin_notes && (
            <div className="rounded-lg bg-muted p-3">
              <p className="text-xs font-medium text-muted-foreground mb-1">
                Admin Notes
              </p>
              <p className="text-sm">{r.admin_notes}</p>
            </div>
          )}

          {r.status === "pending" && (
            <>
              <Separator />
              <div className="space-y-2">
                <Label
                  htmlFor="admin-notes"
                  className="flex items-center gap-1.5"
                >
                  <StickyNote className="h-3.5 w-3.5" />
                  Admin Notes (optional)
                </Label>
                <Textarea
                  id="admin-notes"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Reason for approval/rejection..."
                  rows={2}
                />
              </div>
              <div className="flex justify-end gap-2">
                <Button
                  variant="outline"
                  className="text-red-600 border-red-200 hover:bg-red-50 dark:border-red-900 dark:hover:bg-red-950"
                  disabled={isLoading}
                  onClick={() => handleAction("reject")}
                >
                  <XCircle className="h-4 w-4 mr-1.5" />
                  Reject
                </Button>
                <Button
                  className="bg-emerald-600 hover:bg-emerald-700 text-white"
                  disabled={isLoading}
                  onClick={() => handleAction("approve")}
                >
                  <CheckCircle className="h-4 w-4 mr-1.5" />
                  Approve
                </Button>
              </div>
            </>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}

function DetailItem({
  icon: Icon,
  label,
  value,
}: {
  icon: React.ElementType;
  label: string;
  value: string;
}) {
  return (
    <div className="space-y-0.5">
      <p className="text-xs text-muted-foreground flex items-center gap-1">
        <Icon className="h-3 w-3" />
        {label}
      </p>
      <p className="text-sm font-medium">{value}</p>
    </div>
  );
}
