import { z } from "zod";

const ONE_HOUR_MS = 60 * 60 * 1000;
const THIRTY_DAYS_MS = 30 * 24 * ONE_HOUR_MS;

export const reservationSchema = z
  .object({
    first_name: z
      .string()
      .min(2, "First name must be at least 2 characters")
      .max(50, "First name must be under 50 characters")
      .regex(
        /^[a-zA-Z\s'-]+$/,
        "First name can only contain letters, spaces, hyphens, and apostrophes"
      ),
    last_name: z
      .string()
      .min(2, "Last name must be at least 2 characters")
      .max(50, "Last name must be under 50 characters")
      .regex(
        /^[a-zA-Z\s'-]+$/,
        "Last name can only contain letters, spaces, hyphens, and apostrophes"
      ),
    email: z.string().email("Please enter a valid email address"),
    car_number: z
      .string()
      .min(2, "Vehicle number must be at least 2 characters")
      .max(20, "Vehicle number must be under 20 characters")
      .regex(
        /^[a-zA-Z0-9\s-]+$/,
        "Vehicle number can only contain letters, numbers, spaces, and hyphens"
      ),
    // Accept any non-empty string — the backend validates the slug against the DB
    space_type: z.string().min(1, "Please select a parking type"),
    start_datetime: z.string().min(1, "Start time is required"),
    end_datetime: z.string().min(1, "End time is required"),
  })
  .superRefine((data, ctx) => {
    if (!data.start_datetime || !data.end_datetime) return;
    const start = new Date(data.start_datetime).getTime();
    const end = new Date(data.end_datetime).getTime();
    if (isNaN(start) || isNaN(end)) return;

    if (end <= start) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "End time must be after start time",
        path: ["end_datetime"],
      });
    } else if (end - start < ONE_HOUR_MS) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "Minimum booking duration is 1 hour",
        path: ["end_datetime"],
      });
    } else if (end - start > THIRTY_DAYS_MS) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "Maximum booking duration is 30 days",
        path: ["end_datetime"],
      });
    }
  });

export type ReservationFormData = z.infer<typeof reservationSchema>;

export const adminNotesSchema = z.object({
  admin_notes: z.string().max(500, "Notes must be under 500 characters").optional(),
});

export type AdminNotesFormData = z.infer<typeof adminNotesSchema>;
