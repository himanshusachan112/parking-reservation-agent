import { create } from "zustand";
import type { Reservation, AdminStats } from "@/types";
import { adminService } from "@/services/adminService";

interface AdminStore {
  // State
  reservations: Reservation[];
  isLoading: boolean;
  error: string | null;
  selectedReservation: Reservation | null;
  filterStatus: string;
  searchQuery: string;

  // Computed
  stats: () => AdminStats;
  filteredReservations: () => Reservation[];

  // Actions
  fetchReservations: () => Promise<void>;
  approveReservation: (id: number, notes?: string) => Promise<void>;
  rejectReservation: (id: number, notes?: string) => Promise<void>;
  setSelectedReservation: (r: Reservation | null) => void;
  setFilterStatus: (status: string) => void;
  setSearchQuery: (query: string) => void;
  clearError: () => void;
}

export const useAdminStore = create<AdminStore>((set, get) => ({
  reservations: [],
  isLoading: false,
  error: null,
  selectedReservation: null,
  filterStatus: "all",
  searchQuery: "",

  stats: () => {
    const { reservations } = get();
    return {
      total: reservations.length,
      pending: reservations.filter((r) => r.status === "pending").length,
      approved: reservations.filter((r) => r.status === "approved").length,
      rejected: reservations.filter((r) => r.status === "rejected").length,
    };
  },

  filteredReservations: () => {
    const { reservations, filterStatus, searchQuery } = get();
    let filtered = reservations;

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
  },

  fetchReservations: async () => {
    set({ isLoading: true, error: null });
    try {
      const data = await adminService.getAllReservations();
      set({ reservations: data, isLoading: false });
    } catch (err: unknown) {
      const errorMessage =
        err && typeof err === "object" && "detail" in err
          ? (err as { detail: string }).detail
          : "Failed to fetch reservations";
      set({ isLoading: false, error: errorMessage });
    }
  },

  approveReservation: async (id, notes) => {
    set({ isLoading: true, error: null });
    try {
      await adminService.approve(id, notes);
      await get().fetchReservations();
      set({ selectedReservation: null });
      // Immediately refresh slot stats in StatsCards / SlotManagement
      window.dispatchEvent(new CustomEvent("parksmart:slot-stats-refresh"));
    } catch (err: unknown) {
      const errorMessage =
        err && typeof err === "object" && "detail" in err
          ? (err as { detail: string }).detail
          : "Failed to approve reservation";
      set({ isLoading: false, error: errorMessage });
    }
  },

  rejectReservation: async (id, notes) => {
    set({ isLoading: true, error: null });
    try {
      await adminService.reject(id, notes);
      await get().fetchReservations();
      set({ selectedReservation: null });
      // Immediately refresh slot stats in StatsCards / SlotManagement
      window.dispatchEvent(new CustomEvent("parksmart:slot-stats-refresh"));
    } catch (err: unknown) {
      const errorMessage =
        err && typeof err === "object" && "detail" in err
          ? (err as { detail: string }).detail
          : "Failed to reject reservation";
      set({ isLoading: false, error: errorMessage });
    }
  },

  setSelectedReservation: (r) => set({ selectedReservation: r }),
  setFilterStatus: (status) => set({ filterStatus: status }),
  setSearchQuery: (query) => set({ searchQuery: query }),
  clearError: () => set({ error: null }),
}));
