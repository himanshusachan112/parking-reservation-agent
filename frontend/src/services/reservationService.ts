import api from "@/lib/api";
import type {
  Reservation,
  ReservationRequest,
  ReservationStatus,
} from "@/types";

export const reservationService = {
  create: async (data: ReservationRequest): Promise<Reservation> => {
    const { data: res } = await api.post<Reservation>("/api/reservations", data);
    return res;
  },

  list: async (status?: ReservationStatus): Promise<Reservation[]> => {
    const params = status ? { status } : {};
    const { data } = await api.get<Reservation[]>("/api/reservations", { params });
    return data;
  },

  getById: async (id: number): Promise<Reservation> => {
    const { data } = await api.get<Reservation>(`/api/reservations/${id}`);
    return data;
  },
};
