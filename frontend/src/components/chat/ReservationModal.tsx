"use client";

import { useForm } from "react-hook-form";
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { reservationSchema, type ReservationFormData } from "@/lib/validations";
import { reservationService } from "@/services/reservationService";
import { useUIStore } from "@/store/uiStore";
import { maskEmail, spaceTypeLabels } from "@/lib/helpers";
import { useState } from "react";

export function ReservationModal() {
  const open = useUIStore((s) => s.reservationModalOpen);
  const setOpen = useUIStore((s) => s.setReservationModalOpen);
  const [submitting, setSubmitting] = useState(false);

  const {
    register,
    handleSubmit,
    setValue,
    reset,
    formState: { errors },
  } = useForm<ReservationFormData>({
    resolver: zodResolver(reservationSchema),
    defaultValues: {
      space_type: "standard",
    },
  });

  const onSubmit = async (data: ReservationFormData) => {
    setSubmitting(true);
    try {
      const res = await reservationService.create({
        ...data,
        email: data.email,
      });
      toast.success("Reservation submitted!", {
        description: `Booking #${res.id} is pending admin approval. Email: ${maskEmail(data.email)}`,
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
      <DialogContent className="sm:max-w-lg max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Car className="h-5 w-5" />
            Book a Parking Space
          </DialogTitle>
          <DialogDescription>
            Fill out the form below. Your reservation will be sent for admin
            approval.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 mt-2">
          {/* Name row */}
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="first_name" className="flex items-center gap-1.5">
                <User className="h-3.5 w-3.5" /> First Name
              </Label>
              <Input
                id="first_name"
                placeholder="John"
                {...register("first_name")}
              />
              {errors.first_name && (
                <p className="text-xs text-destructive">
                  {errors.first_name.message}
                </p>
              )}
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="last_name">Last Name</Label>
              <Input
                id="last_name"
                placeholder="Smith"
                {...register("last_name")}
              />
              {errors.last_name && (
                <p className="text-xs text-destructive">
                  {errors.last_name.message}
                </p>
              )}
            </div>
          </div>

          {/* Email */}
          <div className="space-y-1.5">
            <Label htmlFor="email" className="flex items-center gap-1.5">
              <Mail className="h-3.5 w-3.5" /> Email
            </Label>
            <Input
              id="email"
              type="email"
              placeholder="john@example.com"
              {...register("email")}
            />
            {errors.email && (
              <p className="text-xs text-destructive">
                {errors.email.message}
              </p>
            )}
          </div>

          {/* Vehicle Number */}
          <div className="space-y-1.5">
            <Label htmlFor="car_number" className="flex items-center gap-1.5">
              <Car className="h-3.5 w-3.5" /> Vehicle Number
            </Label>
            <Input
              id="car_number"
              placeholder="ABC-1234"
              {...register("car_number")}
            />
            {errors.car_number && (
              <p className="text-xs text-destructive">
                {errors.car_number.message}
              </p>
            )}
          </div>

          {/* Space Type */}
          <div className="space-y-1.5">
            <Label>Vehicle Type</Label>
            <Select
              defaultValue="standard"
              onValueChange={(val) =>
                setValue("space_type", val as ReservationFormData["space_type"], {
                  shouldValidate: true,
                })
              }
            >
              <SelectTrigger>
                <SelectValue placeholder="Select type" />
              </SelectTrigger>
              <SelectContent>
                {Object.entries(spaceTypeLabels).map(([value, label]) => (
                  <SelectItem key={value} value={value}>
                    {label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {errors.space_type && (
              <p className="text-xs text-destructive">
                {errors.space_type.message}
              </p>
            )}
          </div>

          {/* Datetime row */}
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label
                htmlFor="start_datetime"
                className="flex items-center gap-1.5"
              >
                <CalendarDays className="h-3.5 w-3.5" /> Start Time
              </Label>
              <Input
                id="start_datetime"
                type="datetime-local"
                {...register("start_datetime")}
              />
              {errors.start_datetime && (
                <p className="text-xs text-destructive">
                  {errors.start_datetime.message}
                </p>
              )}
            </div>
            <div className="space-y-1.5">
              <Label
                htmlFor="end_datetime"
                className="flex items-center gap-1.5"
              >
                <CalendarDays className="h-3.5 w-3.5" /> End Time
              </Label>
              <Input
                id="end_datetime"
                type="datetime-local"
                {...register("end_datetime")}
              />
              {errors.end_datetime && (
                <p className="text-xs text-destructive">
                  {errors.end_datetime.message}
                </p>
              )}
            </div>
          </div>

          {/* Submit */}
          <div className="flex justify-end gap-2 pt-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => setOpen(false)}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={submitting}>
              {submitting ? "Submitting…" : "Submit Reservation"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
