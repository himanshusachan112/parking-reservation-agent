import api from "@/lib/api";
import type {
  AdminActionRequest,
  Reservation,
  StatusResponse,
} from "@/types";

export const adminService = {
  getPendingReservations: async (): Promise<Reservation[]> => {
    const { data } = await api.get<Reservation[]>("/api/reservations", {
      params: { status: "pending" },
    });
    return data;
  },

  getAllReservations: async (): Promise<Reservation[]> => {
    const { data } = await api.get<Reservation[]>("/api/reservations");
    return data;
  },

  approve: async (id: number, notes?: string): Promise<StatusResponse> => {
    const payload: AdminActionRequest = notes ? { admin_notes: notes } : {};
    const { data } = await api.post<StatusResponse>(
      `/admin/approve/${id}`,
      payload
    );
    return data;
  },

  reject: async (id: number, notes?: string): Promise<StatusResponse> => {
    const payload: AdminActionRequest = notes ? { admin_notes: notes } : {};
    const { data } = await api.post<StatusResponse>(
      `/admin/reject/${id}`,
      payload
    );
    return data;
  },
};
