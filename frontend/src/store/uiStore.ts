import { create } from "zustand";

interface UIStore {
  sidebarOpen: boolean;
  reservationModalOpen: boolean;
  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;
  setReservationModalOpen: (open: boolean) => void;
}

export const useUIStore = create<UIStore>((set) => ({
  sidebarOpen: false,
  reservationModalOpen: false,
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
  setReservationModalOpen: (open) => set({ reservationModalOpen: open }),
}));
