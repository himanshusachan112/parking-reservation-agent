"use client";

import { useEffect, useState, useCallback } from "react";
import { motion } from "framer-motion";
import {
  Plus,
  Minus,
  RefreshCw,
  Car,
  Edit3,
  Check,
  X,
  AlertCircle,
} from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import api from "@/lib/api";

interface ParkingTypeAdmin {
  id: number;
  slug: string;
  name: string;
  description: string;
  hourly_price: number;
  daily_price: number;
  monthly_price: number;
  features: string[];
  is_active: boolean;
  total_slots: number;
  available_slots: number;
  occupied_slots: number;
  maintenance_slots: number;
  availability_status: string;
  availability_percentage: number;
}

interface DashboardStats {
  slot_stats: Array<{
    slug: string;
    name: string;
    total: number;
    available: number;
    occupied: number;
    reserved_pending: number;
    hourly_price: number;
  }>;
  totals: {
    total_slots: number;
    available_slots: number;
    occupied_slots: number;
    pending_slots: number;
  };
  reservations: {
    pending: number;
    approved: number;
    rejected: number;
    total: number;
  };
}

function statusColor(status: string) {
  switch (status?.toLowerCase()) {
    case "available":
      return "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/20";
    case "limited":
      return "bg-yellow-500/10 text-yellow-700 dark:text-yellow-400 border-yellow-500/20";
    case "full":
      return "bg-red-500/10 text-red-700 dark:text-red-400 border-red-500/20";
    default:
      return "bg-slate-500/10 text-slate-600 border-slate-500/20";
  }
}

interface PriceEditState {
  hourly: string;
  daily: string;
  monthly: string;
}

export function SlotManagement() {
  const [types, setTypes] = useState<ParkingTypeAdmin[]>([]);
  const [dashboard, setDashboard] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [slotCounts, setSlotCounts] = useState<Record<string, number>>({});
  const [editingPrice, setEditingPrice] = useState<string | null>(null);
  const [priceForm, setPriceForm] = useState<PriceEditState>({ hourly: "", daily: "", monthly: "" });
  const [busySlug, setBusySlug] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const [typesRes, dashRes] = await Promise.all([
        api.get("/api/admin/parking-types"),
        api.get("/api/admin/dashboard"),
      ]);
      setTypes(typesRes.data.parking_types);
      setDashboard(dashRes.data);
    } catch (err) {
      console.error("Failed to load slot management data", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 10_000);
    // Immediate refresh when admin approves / rejects
    window.addEventListener("parksmart:slot-stats-refresh", fetchData);
    return () => {
      clearInterval(interval);
      window.removeEventListener("parksmart:slot-stats-refresh", fetchData);
    };
  }, [fetchData]);

  async function handleAddSlots(slug: string) {
    const count = slotCounts[slug] || 1;
    setBusySlug(slug);
    try {
      const res = await api.post(`/api/admin/parking-types/${slug}/slots/add`, { count });
      toast.success(`Added ${count} slot(s) to ${slug.toUpperCase()}`, {
        description: `New total: ${res.data.new_total} slots`,
      });
      await fetchData();
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      toast.error("Failed to add slots", { description: detail || "Unknown error" });
    } finally {
      setBusySlug(null);
    }
  }

  async function handleRemoveSlots(slug: string) {
    const count = slotCounts[slug] || 1;
    setBusySlug(slug);
    try {
      const res = await api.post(`/api/admin/parking-types/${slug}/slots/remove`, { count });
      toast.success(`Removed ${count} slot(s) from ${slug.toUpperCase()}`, {
        description: `New total: ${res.data.new_total} slots`,
      });
      await fetchData();
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      toast.error("Failed to remove slots", { description: detail || "Unknown error" });
    } finally {
      setBusySlug(null);
    }
  }

  async function handleToggleActive(slug: string, currentlyActive: boolean) {
    setBusySlug(slug);
    try {
      await api.put(`/api/admin/parking-types/${slug}`, { is_active: !currentlyActive });
      toast.success(`${currentlyActive ? "Deactivated" : "Activated"} ${slug.toUpperCase()}`);
      await fetchData();
    } catch {
      toast.error("Failed to update status");
    } finally {
      setBusySlug(null);
    }
  }

  function startEditPrice(pt: ParkingTypeAdmin) {
    setEditingPrice(pt.slug);
    setPriceForm({
      hourly: String(pt.hourly_price),
      daily: String(pt.daily_price),
      monthly: String(pt.monthly_price),
    });
  }

  async function savePrices(slug: string) {
    setBusySlug(slug);
    try {
      await api.put(`/api/admin/parking-types/${slug}`, {
        hourly_price: parseFloat(priceForm.hourly),
        daily_price: parseFloat(priceForm.daily),
        monthly_price: parseFloat(priceForm.monthly),
      });
      toast.success(`Prices updated for ${slug.toUpperCase()}`);
      setEditingPrice(null);
      await fetchData();
    } catch {
      toast.error("Failed to update prices");
    } finally {
      setBusySlug(null);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-48">
        <RefreshCw className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Live Dashboard Summary */}
      {dashboard && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            { label: "Total Slots", value: dashboard.totals.total_slots, color: "text-blue-600" },
            { label: "Available", value: dashboard.totals.available_slots, color: "text-emerald-600" },
            { label: "Occupied", value: dashboard.totals.occupied_slots, color: "text-orange-600" },
            { label: "Pending (reserved)", value: dashboard.totals.pending_slots ?? dashboard.reservations.pending, color: "text-yellow-600" },
          ].map((stat, i) => (
            <motion.div
              key={stat.label}
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.07 }}
            >
              <Card className="bg-card/50 backdrop-blur-sm border">
                <CardContent className="p-4">
                  <p className="text-xs text-muted-foreground uppercase tracking-wider mb-1">{stat.label}</p>
                  <p className={`text-2xl font-bold ${stat.color}`}>{stat.value}</p>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </div>
      )}

      {/* Per-type slot management */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Parking Type Inventory</h2>
        <Button variant="outline" size="sm" className="gap-1.5" onClick={fetchData}>
          <RefreshCw className="h-3.5 w-3.5" />
          Refresh
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {types.map((pt, i) => (
          <motion.div
            key={pt.slug}
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.06 }}
          >
            <Card className={`border ${!pt.is_active ? "opacity-60" : ""}`}>
              <CardHeader className="pb-2">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <div className="h-8 w-8 rounded-lg bg-primary/10 flex items-center justify-center">
                      <Car className="h-4 w-4 text-primary" />
                    </div>
                    <div>
                      <CardTitle className="text-base">{pt.name}</CardTitle>
                      <p className="text-xs text-muted-foreground">{pt.slug}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-1.5 flex-shrink-0">
                    <Badge
                      variant="outline"
                      className={`text-xs ${statusColor(pt.availability_status)}`}
                    >
                      {pt.availability_status}
                    </Badge>
                    {!pt.is_active && (
                      <Badge variant="outline" className="text-xs bg-slate-500/10 text-slate-500">
                        Inactive
                      </Badge>
                    )}
                  </div>
                </div>
              </CardHeader>

              <CardContent className="space-y-4">
                {/* Slot bar */}
                <div>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-muted-foreground">Slots</span>
                    <span className="font-medium">
                      {pt.available_slots} available / {pt.total_slots} total
                    </span>
                  </div>
                  <div className="h-2 rounded-full bg-muted overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all ${
                        pt.availability_percentage > 50
                          ? "bg-emerald-500"
                          : pt.availability_percentage > 0
                          ? "bg-yellow-500"
                          : "bg-red-500"
                      }`}
                      style={{ width: `${pt.availability_percentage}%` }}
                    />
                  </div>
                  <div className="flex gap-4 text-xs text-muted-foreground mt-1">
                    <span>{pt.occupied_slots} occupied</span>
                    <span>{pt.maintenance_slots} maintenance</span>
                  </div>
                </div>

                {/* Add / Remove slots */}
                <div className="flex items-center gap-2">
                  <Input
                    type="number"
                    min={1}
                    max={500}
                    placeholder="Count"
                    value={slotCounts[pt.slug] ?? ""}
                    onChange={(e) =>
                      setSlotCounts((prev) => ({
                        ...prev,
                        [pt.slug]: Math.max(1, parseInt(e.target.value) || 1),
                      }))
                    }
                    className="h-8 w-20 text-sm"
                  />
                  <Button
                    size="sm"
                    variant="outline"
                    className="h-8 gap-1 text-emerald-700 border-emerald-500/30 hover:bg-emerald-500/10"
                    onClick={() => handleAddSlots(pt.slug)}
                    disabled={busySlug === pt.slug}
                  >
                    <Plus className="h-3.5 w-3.5" />
                    Add
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    className="h-8 gap-1 text-red-700 border-red-500/30 hover:bg-red-500/10"
                    onClick={() => handleRemoveSlots(pt.slug)}
                    disabled={busySlug === pt.slug || pt.available_slots === 0}
                  >
                    <Minus className="h-3.5 w-3.5" />
                    Remove
                  </Button>
                </div>

                {/* Pricing */}
                {editingPrice === pt.slug ? (
                  <div className="space-y-2">
                    <div className="grid grid-cols-3 gap-2">
                      {(["hourly", "daily", "monthly"] as const).map((k) => (
                        <div key={k}>
                          <p className="text-xs text-muted-foreground mb-1 capitalize">{k} (₹)</p>
                          <Input
                            type="number"
                            min={0}
                            value={priceForm[k]}
                            onChange={(e) => setPriceForm((prev) => ({ ...prev, [k]: e.target.value }))}
                            className="h-8 text-sm"
                          />
                        </div>
                      ))}
                    </div>
                    <div className="flex gap-2">
                      <Button
                        size="sm"
                        className="h-8 gap-1 flex-1"
                        onClick={() => savePrices(pt.slug)}
                        disabled={busySlug === pt.slug}
                      >
                        <Check className="h-3.5 w-3.5" />
                        Save
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        className="h-8 gap-1"
                        onClick={() => setEditingPrice(null)}
                      >
                        <X className="h-3.5 w-3.5" />
                        Cancel
                      </Button>
                    </div>
                  </div>
                ) : (
                  <div className="flex items-center justify-between text-sm">
                    <div className="text-muted-foreground">
                      ₹{pt.hourly_price}/hr · ₹{pt.daily_price}/day
                    </div>
                    <div className="flex gap-1.5">
                      <Button
                        size="sm"
                        variant="ghost"
                        className="h-7 px-2 gap-1 text-xs"
                        onClick={() => startEditPrice(pt)}
                      >
                        <Edit3 className="h-3 w-3" />
                        Edit Prices
                      </Button>
                      <Button
                        size="sm"
                        variant={pt.is_active ? "destructive" : "outline"}
                        className="h-7 px-2 text-xs"
                        onClick={() => handleToggleActive(pt.slug, pt.is_active)}
                        disabled={busySlug === pt.slug}
                      >
                        {pt.is_active ? "Deactivate" : "Activate"}
                      </Button>
                    </div>
                  </div>
                )}

                {/* Warning if zero available but active */}
                {pt.is_active && pt.available_slots === 0 && pt.total_slots > 0 && (
                  <div className="flex items-center gap-2 text-xs text-red-600 bg-red-500/10 rounded px-2 py-1.5">
                    <AlertCircle className="h-3.5 w-3.5 flex-shrink-0" />
                    All slots occupied — consider adding more slots
                  </div>
                )}
                {pt.is_active && pt.total_slots === 0 && (
                  <div className="flex items-center gap-2 text-xs text-orange-600 bg-orange-500/10 rounded px-2 py-1.5">
                    <AlertCircle className="h-3.5 w-3.5 flex-shrink-0" />
                    No slots exist — add slots to accept bookings
                  </div>
                )}
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
