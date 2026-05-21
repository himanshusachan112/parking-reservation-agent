"use client";

import { useForm, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { toast } from "sonner";
import { CalendarDays, Car, Mail, User } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { reservationSchema, type ReservationFormData } from "@/lib/validations";
import { reservationService } from "@/services/reservationService";
import { useUIStore } from "@/store/uiStore";
import { maskEmail } from "@/lib/helpers";
import { useState, useRef } from "react";
import { ParkingTypeSelector } from "./ParkingTypeSelector";
import { BookingSummaryCard } from "./BookingSummaryCard";

// Min datetime = now + 1 hour (datetime-local format)
function minDatetime(): string {
  const d = new Date(Date.now() + 60 * 60 * 1000);
  return d.toISOString().slice(0, 16);
}

// Max datetime = now + 30 days
function maxDatetime(): string {
  const d = new Date(Date.now() + 30 * 24 * 60 * 60 * 1000);
  return d.toISOString().slice(0, 16);
}

export function ReservationModal() {
  const open = useUIStore((s) => s.reservationModalOpen);
  const setOpen = useUIStore((s) => s.setReservationModalOpen);
  const [submitting, setSubmitting] = useState(false);

  // Store the human-readable name for BookingSummaryCard
  const selectedNameRef = useRef<string>("");

  const {
    register,
    handleSubmit,
    setValue,
    control,
    reset,
    formState: { errors },
  } = useForm<ReservationFormData>({
    resolver: zodResolver(reservationSchema),
    defaultValues: { space_type: "standard" },
  });

  // Watch for live price calculation
  const watchedType = useWatch({ control, name: "space_type" });
  const watchedStart = useWatch({ control, name: "start_datetime" });
  const watchedEnd = useWatch({ control, name: "end_datetime" });

  const onSubmit = async (data: ReservationFormData) => {
    setSubmitting(true);
    try {
      const res = await reservationService.create({ ...data });
      toast.success("Reservation submitted!", {
        description: `Booking #${res.id} is pending admin approval. Confirmation sent to: ${maskEmail(data.email)}`,
      });
      reset();
      setOpen(false);
    } catch (err: unknown) {
      const msg =
        err && typeof err === "object" && "detail" in err
          ? (err as { detail: string }).detail
          : "Failed to submit reservation";
      toast.error("Submission failed", { description: msg });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="sm:max-w-2xl max-h-[92vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-lg">
            <div className="h-8 w-8 rounded-lg bg-primary/10 flex items-center justify-center">
              <Car className="h-4 w-4 text-primary" />
            </div>
            Book a Parking Space
          </DialogTitle>
          <DialogDescription>
            Select your parking type and dates. Your reservation will be sent
            for admin approval.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-5 mt-1">

          {/* ── Personal details ── */}
          <div className="space-y-3">
            <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Personal Details
            </p>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label htmlFor="first_name" className="flex items-center gap-1.5 text-xs">
                  <User className="h-3.5 w-3.5" /> First Name
                </Label>
                <Input
                  id="first_name"
                  placeholder="John"
                  className="h-9"
                  {...register("first_name")}
                />
                {errors.first_name && (
                  <p className="text-[11px] text-destructive">{errors.first_name.message}</p>
                )}
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="last_name" className="text-xs">Last Name</Label>
                <Input
                  id="last_name"
                  placeholder="Smith"
                  className="h-9"
                  {...register("last_name")}
                />
                {errors.last_name && (
                  <p className="text-[11px] text-destructive">{errors.last_name.message}</p>
                )}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label htmlFor="email" className="flex items-center gap-1.5 text-xs">
                  <Mail className="h-3.5 w-3.5" /> Email
                </Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="john@example.com"
                  className="h-9"
                  {...register("email")}
                />
                {errors.email && (
                  <p className="text-[11px] text-destructive">{errors.email.message}</p>
                )}
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="car_number" className="flex items-center gap-1.5 text-xs">
                  <Car className="h-3.5 w-3.5" /> Vehicle Number
                </Label>
                <Input
                  id="car_number"
                  placeholder="TS09AB1234"
                  className="h-9"
                  {...register("car_number")}
                />
                {errors.car_number && (
                  <p className="text-[11px] text-destructive">{errors.car_number.message}</p>
                )}
              </div>
            </div>
          </div>

          {/* ── Date & Time ── */}
          <div className="space-y-3">
            <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Booking Duration
            </p>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label htmlFor="start_datetime" className="flex items-center gap-1.5 text-xs">
                  <CalendarDays className="h-3.5 w-3.5" /> Start
                </Label>
                <Input
                  id="start_datetime"
                  type="datetime-local"
                  min={minDatetime()}
                  max={maxDatetime()}
                  className="h-9 text-xs"
                  {...register("start_datetime")}
                />
                {errors.start_datetime && (
                  <p className="text-[11px] text-destructive">{errors.start_datetime.message}</p>
                )}
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="end_datetime" className="flex items-center gap-1.5 text-xs">
                  <CalendarDays className="h-3.5 w-3.5" /> End
                </Label>
                <Input
                  id="end_datetime"
                  type="datetime-local"
                  min={watchedStart || minDatetime()}
                  max={maxDatetime()}
                  className="h-9 text-xs"
                  {...register("end_datetime")}
                />
                {errors.end_datetime && (
                  <p className="text-[11px] text-destructive">{errors.end_datetime.message}</p>
                )}
              </div>
            </div>
          </div>

          {/* ── Parking type selector ── */}
          <div className="space-y-3">
            <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Select Parking Type
            </p>
            <ParkingTypeSelector
              value={watchedType || "standard"}
              onChange={(slug, name) => {
                selectedNameRef.current = name;
                setValue("space_type", slug as ReservationFormData["space_type"], {
                  shouldValidate: true,
                });
              }}
              disabled={submitting}
            />
            {errors.space_type && (
              <p className="text-[11px] text-destructive">{errors.space_type.message}</p>
            )}
          </div>

          {/* ── Live price estimate ── */}
          <BookingSummaryCard
            spaceType={watchedType || ""}
            spaceName={selectedNameRef.current}
            startDatetime={watchedStart || ""}
            endDatetime={watchedEnd || ""}
          />

          {/* ── Submit ── */}
          <div className="flex justify-end gap-2 pt-1 border-t">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setOpen(false)}
            >
              Cancel
            </Button>
            <Button type="submit" size="sm" disabled={submitting}>
              {submitting ? "Submitting…" : "Submit Reservation"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}

