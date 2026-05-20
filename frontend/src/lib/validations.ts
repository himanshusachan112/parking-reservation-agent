import { z } from "zod";

export const reservationSchema = z.object({
  first_name: z
    .string()
    .min(2, "First name must be at least 2 characters")
    .max(50, "First name must be under 50 characters")
    .regex(/^[a-zA-Z\s'-]+$/, "First name can only contain letters, spaces, hyphens, and apostrophes"),
  last_name: z
    .string()
    .min(2, "Last name must be at least 2 characters")
    .max(50, "Last name must be under 50 characters")
    .regex(/^[a-zA-Z\s'-]+$/, "Last name can only contain letters, spaces, hyphens, and apostrophes"),
  email: z
    .string()
    .email("Please enter a valid email address"),
  car_number: z
    .string()
    .min(2, "Vehicle number must be at least 2 characters")
    .max(20, "Vehicle number must be under 20 characters")
    .regex(/^[a-zA-Z0-9\s-]+$/, "Vehicle number can only contain letters, numbers, spaces, and hyphens"),
  space_type: z.enum(["standard", "large", "ev", "vip"], {
    message: "Please select a vehicle type",
  }),
  start_datetime: z
    .string()
    .min(1, "Start time is required"),
  end_datetime: z
    .string()
    .min(1, "End time is required"),
}).refine(
  (data) => {
    if (!data.start_datetime || !data.end_datetime) return true;
    return new Date(data.end_datetime) > new Date(data.start_datetime);
  },
  {
    message: "End time must be after start time",
    path: ["end_datetime"],
  }
);

export type ReservationFormData = z.infer<typeof reservationSchema>;

export const adminNotesSchema = z.object({
  admin_notes: z.string().max(500, "Notes must be under 500 characters").optional(),
});

export type AdminNotesFormData = z.infer<typeof adminNotesSchema>;
