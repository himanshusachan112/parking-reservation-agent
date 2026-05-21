"use client";

import { useEffect, useState } from "react";
import { RefreshCw, Search, LayoutList, Settings2 } from "lucide-react";
import { motion } from "framer-motion";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { StatsCards } from "@/components/admin/StatsCards";
import { ReservationTable } from "@/components/admin/ReservationTable";
import { ReservationModal } from "@/components/admin/ReservationModal";
import { ActivityFeed } from "@/components/admin/ActivityFeed";
import { AdminLoginGate } from "@/components/admin/AdminLoginGate";
import { SlotManagement } from "@/components/admin/SlotManagement";
import { ErrorBoundary } from "@/components/shared/ErrorBoundary";
import { useAdminStore } from "@/store/adminStore";

type AdminTab = "reservations" | "slots";

export default function AdminPage() {
  const fetchReservations = useAdminStore((s) => s.fetchReservations);
  const isLoading = useAdminStore((s) => s.isLoading);
  const error = useAdminStore((s) => s.error);
  const clearError = useAdminStore((s) => s.clearError);
  const filterStatus = useAdminStore((s) => s.filterStatus);
  const setFilterStatus = useAdminStore((s) => s.setFilterStatus);
  const searchQuery = useAdminStore((s) => s.searchQuery);
  const setSearchQuery = useAdminStore((s) => s.setSearchQuery);
  const [activeTab, setActiveTab] = useState<AdminTab>("reservations");

  useEffect(() => {
    fetchReservations();
    // Auto-refresh reservations every 15 s so admin always sees latest pending bookings
    const interval = setInterval(() => fetchReservations(), 15_000);
    return () => clearInterval(interval);
  }, [fetchReservations]);

  useEffect(() => {
    if (error) {
      toast.error("Error", { description: error });
      clearError();
    }
  }, [error, clearError]);

  return (
    <AdminLoginGate>
    <ErrorBoundary>
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-7xl mx-auto px-4 md:px-6 py-6 space-y-6">
          {/* Header */}
          <motion.div
            initial={{ opacity: 0, y: -12 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4"
          >
            <div>
              <h1 className="text-2xl font-bold tracking-tight">
                Admin Dashboard
              </h1>
              <p className="text-sm text-muted-foreground mt-0.5">
                Manage parking reservations and slot inventory
              </p>
            </div>
            <div className="flex items-center gap-2 self-start">
              {/* Main tab switcher */}
              <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as AdminTab)}>
                <TabsList>
                  <TabsTrigger value="reservations" className="gap-1.5">
                    <LayoutList className="h-3.5 w-3.5" />
                    Reservations
                  </TabsTrigger>
                  <TabsTrigger value="slots" className="gap-1.5">
                    <Settings2 className="h-3.5 w-3.5" />
                    Slot Management
                  </TabsTrigger>
                </TabsList>
              </Tabs>
              {activeTab === "reservations" && (
                <Button
                  variant="outline"
                  size="sm"
                  className="gap-1.5"
                  onClick={() => fetchReservations()}
                  disabled={isLoading}
                >
                  <RefreshCw
                    className={`h-3.5 w-3.5 ${isLoading ? "animate-spin" : ""}`}
                  />
                  Refresh
                </Button>
              )}
            </div>
          </motion.div>

          {/* Stats (always visible) */}
          <StatsCards />

          {/* Tab content */}
          {activeTab === "reservations" ? (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Reservations table */}
              <div className="lg:col-span-2 space-y-4">
                {/* Filters */}
                <div className="flex flex-col sm:flex-row gap-3">
                  <div className="relative flex-1">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                    <Input
                      placeholder="Search by name, vehicle, or ID..."
                      className="pl-9"
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                    />
                  </div>
                  <Tabs
                    value={filterStatus}
                    onValueChange={setFilterStatus}
                  >
                    <TabsList>
                      <TabsTrigger value="all">All</TabsTrigger>
                      <TabsTrigger value="pending">Pending</TabsTrigger>
                      <TabsTrigger value="approved">Approved</TabsTrigger>
                      <TabsTrigger value="rejected">Rejected</TabsTrigger>
                    </TabsList>
                  </Tabs>
                </div>

                <ReservationTable />
              </div>

              {/* Activity feed */}
              <div>
                <ActivityFeed />
              </div>
            </div>
          ) : (
            <SlotManagement />
          )}
        </div>
      </div>

      <ReservationModal />
    </ErrorBoundary>
    </AdminLoginGate>
  );
}

