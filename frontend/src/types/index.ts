// ════════════════════════════════════════
// Chat Types
// ════════════════════════════════════════

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  isStreaming?: boolean;
  reservationId?: number | null;
  isBookingFlow?: boolean;
}

export interface ChatSession {
  id: string;
  title: string;
  lastMessage: string;
  timestamp: Date;
  messages: ChatMessage[];
}

export interface ChatRequest {
  message: string;
}

export interface ChatResponse {
  response: string;
  is_booking_flow: boolean;
  reservation_id: number | null;
}

// ════════════════════════════════════════
// Reservation Types
// ════════════════════════════════════════

export interface Reservation {
  id: number;
  first_name: string;
  last_name: string;
  email: string | null;
  car_number: string;
  space_type: SpaceType;
  start_datetime: string;
  end_datetime: string;
  status: ReservationStatus;
  admin_notes: string | null;
  created_at: string | null;
  updated_at: string | null;
  approved_at: string | null;
}

export type ReservationStatus = "pending" | "approved" | "rejected";
export type SpaceType = "standard" | "large" | "ev" | "vip";

export interface ReservationRequest {
  first_name: string;
  last_name: string;
  email?: string;
  car_number: string;
  space_type: SpaceType;
  start_datetime: string;
  end_datetime: string;
}

export interface AdminActionRequest {
  admin_notes?: string;
}

export interface StatusResponse {
  success: boolean;
  message: string;
}

// ════════════════════════════════════════
// Admin Types
// ════════════════════════════════════════

export interface AdminStats {
  total: number;
  pending: number;
  approved: number;
  rejected: number;
}

export interface ActivityItem {
  id: number;
  action: string;
  reservation: Reservation;
  timestamp: string;
}

// ════════════════════════════════════════
// UI Types
// ════════════════════════════════════════

export interface ApiError {
  detail: string;
  status: number;
}
