"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import {
  CreditCard,
  Smartphone,
  Building2,
  Wallet,
  CheckCircle2,
  AlertCircle,
  Clock,
  Car,
  CalendarDays,
  MapPin,
  ShieldCheck,
  Loader2,
  ArrowLeft,
  RefreshCw,
} from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ── Types ────────────────────────────────────────────────────────────────────

interface PaymentData {
  id: number;
  reservation_id: number;
  payment_token: string;
  status: "pending" | "paid" | "failed" | "expired";
  amount_inr: number;
  payment_method: string | null;
  transaction_id: string | null;
  paid_at: string | null;
  expires_at: string | null;
  user_name: string | null;
  user_email: string | null;
  vehicle_number: string | null;
  space_type: string | null;
  start_datetime: string | null;
  end_datetime: string | null;
  is_expired: boolean;
  is_payable: boolean;
}

type PaymentMethod = "upi" | "card" | "netbanking" | "wallet";

// ── Helpers ──────────────────────────────────────────────────────────────────

const SPACE_LABELS: Record<string, string> = {
  standard: "Standard Parking",
  large: "Large Vehicle",
  ev: "EV Charging",
  vip: "VIP Premium",
  disabled: "Disabled / Accessible",
  bike: "Bike / 2-Wheeler",
};

const WALLET_PROVIDERS = ["Paytm", "PhonePe", "Amazon Pay", "Airtel Money", "Mobikwik"];

function formatINR(amount: number) {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(amount);
}

function formatDate(dt: string | null) {
  if (!dt) return "—";
  // Handle both ISO and "YYYY-MM-DD HH:MM" formats
  const d = new Date(dt.replace(" ", "T"));
  return isNaN(d.getTime())
    ? dt
    : d.toLocaleString("en-IN", {
        day: "2-digit",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        hour12: true,
      });
}

// ── Sub-components ───────────────────────────────────────────────────────────

function BookingSummary({ data }: { data: PaymentData }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur-sm p-6 space-y-4">
      <h2 className="text-lg font-semibold text-white flex items-center gap-2">
        <Car className="h-5 w-5 text-blue-400" />
        Booking Summary
      </h2>

      <div className="space-y-3 text-sm">
        {data.user_name && (
          <Row label="Name" value={data.user_name} />
        )}
        {data.vehicle_number && (
          <Row label="Vehicle" value={data.vehicle_number} />
        )}
        {data.space_type && (
          <Row
            label="Parking Type"
            value={SPACE_LABELS[data.space_type] || data.space_type}
          />
        )}
        {data.start_datetime && (
          <Row
            label="From"
            value={formatDate(data.start_datetime)}
            icon={<CalendarDays className="h-4 w-4 text-blue-400" />}
          />
        )}
        {data.end_datetime && (
          <Row
            label="To"
            value={formatDate(data.end_datetime)}
            icon={<CalendarDays className="h-4 w-4 text-blue-400" />}
          />
        )}
        {data.expires_at && (
          <Row
            label="Pay Before"
            value={formatDate(data.expires_at)}
            icon={<Clock className="h-4 w-4 text-amber-400" />}
          />
        )}
      </div>

      <div className="border-t border-white/10 pt-4 flex justify-between items-center">
        <span className="text-gray-400 text-sm">Total Amount</span>
        <span className="text-2xl font-bold text-green-400">
          {formatINR(data.amount_inr)}
        </span>
      </div>

      <div className="flex items-center gap-2 text-xs text-gray-500">
        <ShieldCheck className="h-3.5 w-3.5 text-green-500" />
        <span>256-bit SSL encrypted · Secure payment</span>
      </div>
    </div>
  );
}

function Row({
  label,
  value,
  icon,
}: {
  label: string;
  value: string;
  icon?: React.ReactNode;
}) {
  return (
    <div className="flex justify-between items-center gap-4">
      <span className="text-gray-400 shrink-0">{label}</span>
      <span className="text-white text-right flex items-center gap-1.5">
        {icon}
        {value}
      </span>
    </div>
  );
}

// ── UPI Form ─────────────────────────────────────────────────────────────────

function UpiForm({ onSubmit }: { onSubmit: (d: object) => void }) {
  const [upiId, setUpiId] = useState("");
  const [error, setError] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!upiId.includes("@")) {
      setError("Enter a valid UPI ID (e.g. name@upi)");
      return;
    }
    setError("");
    onSubmit({ payment_method: "upi", upi_id: upiId });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label className="block text-sm text-gray-400 mb-1">UPI ID</label>
        <input
          type="text"
          value={upiId}
          onChange={(e) => setUpiId(e.target.value)}
          placeholder="yourname@upi"
          className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-white
                     placeholder:text-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        {error && <p className="text-red-400 text-xs mt-1">{error}</p>}
      </div>
      <p className="text-xs text-gray-500">
        Supports all UPI apps: GPay, PhonePe, Paytm, BHIM, Amazon Pay, etc.
      </p>
      <PayButton label="Pay via UPI" />
    </form>
  );
}

// ── Card Form ─────────────────────────────────────────────────────────────────

function CardForm({ onSubmit }: { onSubmit: (d: object) => void }) {
  const [cardNumber, setCardNumber] = useState("");
  const [expiry, setExpiry] = useState("");
  const [cvv, setCvv] = useState("");
  const [holder, setHolder] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});

  const formatCardNumber = (v: string) =>
    v
      .replace(/\D/g, "")
      .substring(0, 16)
      .replace(/(.{4})/g, "$1 ")
      .trim();

  const formatExpiry = (v: string) => {
    const digits = v.replace(/\D/g, "").substring(0, 4);
    if (digits.length >= 3) return `${digits.slice(0, 2)}/${digits.slice(2)}`;
    return digits;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const errs: Record<string, string> = {};
    const digits = cardNumber.replace(/\s/g, "");
    if (digits.length < 16) errs.cardNumber = "Enter a 16-digit card number";
    if (!expiry.match(/^\d{2}\/\d{2}$/)) errs.expiry = "Use MM/YY format";
    if (cvv.length < 3) errs.cvv = "Enter 3-digit CVV";
    if (!holder.trim()) errs.holder = "Enter card holder name";
    setErrors(errs);
    if (Object.keys(errs).length) return;
    onSubmit({
      payment_method: "card",
      card_last4: digits.slice(-4),
      card_holder: holder,
    });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <Field
        label="Card Number"
        value={cardNumber}
        onChange={(v) => setCardNumber(formatCardNumber(v))}
        placeholder="1234 5678 9012 3456"
        error={errors.cardNumber}
        maxLength={19}
      />
      <Field
        label="Card Holder Name"
        value={holder}
        onChange={setHolder}
        placeholder="John Smith"
        error={errors.holder}
      />
      <div className="grid grid-cols-2 gap-4">
        <Field
          label="Expiry (MM/YY)"
          value={expiry}
          onChange={(v) => setExpiry(formatExpiry(v))}
          placeholder="MM/YY"
          error={errors.expiry}
          maxLength={5}
        />
        <Field
          label="CVV"
          value={cvv}
          onChange={(v) => setCvv(v.replace(/\D/g, "").substring(0, 4))}
          placeholder="123"
          error={errors.cvv}
          maxLength={4}
          type="password"
        />
      </div>
      <p className="text-xs text-gray-500">Visa · Mastercard · RuPay · Amex accepted</p>
      <PayButton label="Pay with Card" />
    </form>
  );
}

// ── Net Banking Form ─────────────────────────────────────────────────────────

const BANKS = [
  "State Bank of India",
  "HDFC Bank",
  "ICICI Bank",
  "Axis Bank",
  "Kotak Mahindra Bank",
  "Punjab National Bank",
  "Bank of Baroda",
  "Canara Bank",
  "Yes Bank",
  "IDFC First Bank",
];

function NetBankingForm({ onSubmit }: { onSubmit: (d: object) => void }) {
  const [bank, setBank] = useState("");
  const [error, setError] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!bank) {
      setError("Please select a bank");
      return;
    }
    setError("");
    onSubmit({ payment_method: "netbanking", bank });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label className="block text-sm text-gray-400 mb-1">Select Your Bank</label>
        <select
          value={bank}
          onChange={(e) => setBank(e.target.value)}
          className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-white
                     focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="" className="bg-gray-900">
            — Choose bank —
          </option>
          {BANKS.map((b) => (
            <option key={b} value={b} className="bg-gray-900">
              {b}
            </option>
          ))}
        </select>
        {error && <p className="text-red-400 text-xs mt-1">{error}</p>}
      </div>
      <p className="text-xs text-gray-500">
        You will be redirected to your bank&apos;s secure portal.
      </p>
      <PayButton label="Proceed to Net Banking" />
    </form>
  );
}

// ── Wallet Form ───────────────────────────────────────────────────────────────

function WalletForm({ onSubmit }: { onSubmit: (d: object) => void }) {
  const [wallet, setWallet] = useState("");
  const [error, setError] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!wallet) {
      setError("Please select a wallet");
      return;
    }
    setError("");
    onSubmit({ payment_method: "wallet", wallet_provider: wallet });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-2 gap-3">
        {WALLET_PROVIDERS.map((w) => (
          <button
            key={w}
            type="button"
            onClick={() => setWallet(w)}
            className={`px-4 py-3 rounded-lg border text-sm font-medium transition-all ${
              wallet === w
                ? "border-blue-500 bg-blue-500/20 text-blue-300"
                : "border-white/10 bg-white/5 text-gray-400 hover:border-white/30"
            }`}
          >
            {w}
          </button>
        ))}
      </div>
      {error && <p className="text-red-400 text-xs">{error}</p>}
      <p className="text-xs text-gray-500">Balance will be deducted from your wallet.</p>
      <PayButton label="Pay with Wallet" />
    </form>
  );
}

// ── Shared Field ──────────────────────────────────────────────────────────────

function Field({
  label,
  value,
  onChange,
  placeholder,
  error,
  maxLength,
  type = "text",
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  error?: string;
  maxLength?: number;
  type?: string;
}) {
  return (
    <div>
      <label className="block text-sm text-gray-400 mb-1">{label}</label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        maxLength={maxLength}
        className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-white
                   placeholder:text-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500"
      />
      {error && <p className="text-red-400 text-xs mt-1">{error}</p>}
    </div>
  );
}

// ── Pay Button ────────────────────────────────────────────────────────────────

function PayButton({ label }: { label: string }) {
  return (
    <button
      type="submit"
      className="w-full bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-400
                 hover:to-emerald-500 text-white font-semibold py-4 rounded-xl transition-all
                 shadow-lg shadow-green-900/40 text-base tracking-wide"
    >
      🔒 {label}
    </button>
  );
}

// ── Success State ─────────────────────────────────────────────────────────────

function PaymentSuccess({ data }: { data: PaymentData }) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      className="text-center space-y-6"
    >
      <motion.div
        initial={{ scale: 0 }}
        animate={{ scale: 1 }}
        transition={{ type: "spring", delay: 0.2 }}
        className="mx-auto w-24 h-24 rounded-full bg-green-500/20 flex items-center justify-center"
      >
        <CheckCircle2 className="h-12 w-12 text-green-400" />
      </motion.div>

      <div>
        <h2 className="text-2xl font-bold text-white">Payment Successful!</h2>
        <p className="text-gray-400 mt-2">
          Your parking slot has been confirmed.
        </p>
      </div>

      <div className="rounded-xl border border-white/10 bg-white/5 p-5 text-left space-y-3 text-sm">
        <DetailRow label="Booking Ref" value={`#${data.reservation_id}`} />
        <DetailRow label="Amount Paid" value={formatINR(data.amount_inr)} highlight />
        <DetailRow
          label="Payment Method"
          value={(data.payment_method || "").toUpperCase()}
        />
        <DetailRow label="Transaction ID" value={data.transaction_id || "—"} mono />
        <DetailRow label="Paid At" value={formatDate(data.paid_at)} />
      </div>

      <div className="rounded-xl border border-green-500/30 bg-green-500/10 p-4 text-sm text-green-300">
        A payment confirmation has been sent to the admin. Please keep your
        Transaction ID for reference when you arrive at the parking facility.
      </div>
    </motion.div>
  );
}

function DetailRow({
  label,
  value,
  highlight,
  mono,
}: {
  label: string;
  value: string;
  highlight?: boolean;
  mono?: boolean;
}) {
  return (
    <div className="flex justify-between items-center">
      <span className="text-gray-400">{label}</span>
      <span
        className={`text-right ${
          highlight ? "text-green-400 font-bold text-base" : "text-white"
        } ${mono ? "font-mono text-xs" : ""}`}
      >
        {value}
      </span>
    </div>
  );
}

// ── Main Component ────────────────────────────────────────────────────────────

const METHOD_TABS: {
  id: PaymentMethod;
  label: string;
  icon: React.ReactNode;
}[] = [
  { id: "upi", label: "UPI", icon: <Smartphone className="h-4 w-4" /> },
  { id: "card", label: "Card", icon: <CreditCard className="h-4 w-4" /> },
  { id: "netbanking", label: "Net Banking", icon: <Building2 className="h-4 w-4" /> },
  { id: "wallet", label: "Wallet", icon: <Wallet className="h-4 w-4" /> },
];

export function PaymentPage({ token }: { token: string }) {
  const router = useRouter();
  const [payment, setPayment] = useState<PaymentData | null>(null);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeMethod, setActiveMethod] = useState<PaymentMethod>("upi");

  const fetchPayment = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/api/payment/${token}`);
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.detail || `HTTP ${res.status}`);
      }
      const data: PaymentData = await res.json();
      setPayment(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load payment details.");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    fetchPayment();
  }, [fetchPayment]);

  const handlePayment = async (formData: object) => {
    setProcessing(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/api/payment/${token}/process`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(formData),
      });
      const data = await res.json();
      if (!res.ok) {
        if (res.status === 409) {
          // Already paid — refresh to show success state
          await fetchPayment();
          return;
        }
        throw new Error(data.detail || `Payment failed (${res.status})`);
      }
      setPayment(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Payment processing failed.");
    } finally {
      setProcessing(false);
    }
  };

  // ── Loading ──────────────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <div className="text-center space-y-4">
          <Loader2 className="h-10 w-10 animate-spin text-blue-400 mx-auto" />
          <p className="text-gray-400">Loading payment details…</p>
        </div>
      </div>
    );
  }

  // ── Not found ────────────────────────────────────────────────────────
  if (!payment && error) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center px-4">
        <div className="text-center space-y-4 max-w-md">
          <AlertCircle className="h-12 w-12 text-red-400 mx-auto" />
          <h2 className="text-xl font-semibold text-white">Payment Link Not Found</h2>
          <p className="text-gray-400">{error}</p>
          <button
            onClick={() => router.push("/")}
            className="inline-flex items-center gap-2 text-blue-400 hover:text-blue-300 text-sm"
          >
            <ArrowLeft className="h-4 w-4" /> Back to Home
          </button>
        </div>
      </div>
    );
  }

  if (!payment) return null;

  // ── Already paid ──────────────────────────────────────────────────────
  if (payment.status === "paid") {
    return (
      <div className="max-w-lg mx-auto px-4 py-12">
        <PaymentSuccess data={payment} />
      </div>
    );
  }

  // ── Expired ───────────────────────────────────────────────────────────
  if (payment.status === "expired" || payment.is_expired) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center px-4">
        <div className="text-center space-y-4 max-w-md">
          <Clock className="h-12 w-12 text-amber-400 mx-auto" />
          <h2 className="text-xl font-semibold text-white">Payment Link Expired</h2>
          <p className="text-gray-400">
            This payment link has expired. Please contact ParkSmart support to
            renew your payment link.
          </p>
          <button
            onClick={() => router.push("/")}
            className="inline-flex items-center gap-2 text-blue-400 hover:text-blue-300 text-sm"
          >
            <ArrowLeft className="h-4 w-4" /> Back to Home
          </button>
        </div>
      </div>
    );
  }

  // ── Payment form ──────────────────────────────────────────────────────
  return (
    <div className="max-w-4xl mx-auto px-4 py-10">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-8 text-center"
      >
        <h1 className="text-3xl font-bold text-white">Complete Your Payment</h1>
        <p className="text-gray-400 mt-2">
          Reservation #{payment.reservation_id} · Secure checkout
        </p>
      </motion.div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-8">
        {/* Left: Booking Summary */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.1 }}
          className="lg:col-span-2"
        >
          <BookingSummary data={payment} />
        </motion.div>

        {/* Right: Payment Methods */}
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.2 }}
          className="lg:col-span-3"
        >
          <div className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur-sm p-6">
            <h2 className="text-lg font-semibold text-white mb-5">
              Choose Payment Method
            </h2>

            {/* Tabs */}
            <div className="flex gap-2 mb-6 flex-wrap">
              {METHOD_TABS.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveMethod(tab.id)}
                  className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium
                    transition-all ${
                      activeMethod === tab.id
                        ? "bg-blue-600 text-white shadow-lg shadow-blue-900/40"
                        : "bg-white/5 text-gray-400 hover:bg-white/10 hover:text-white border border-white/10"
                    }`}
                >
                  {tab.icon}
                  {tab.label}
                </button>
              ))}
            </div>

            {/* Error Banner */}
            {error && (
              <motion.div
                initial={{ opacity: 0, y: -8 }}
                animate={{ opacity: 1, y: 0 }}
                className="mb-4 flex items-start gap-3 p-3 rounded-lg bg-red-500/10
                           border border-red-500/30 text-red-300 text-sm"
              >
                <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
                <span>{error}</span>
                <button
                  onClick={() => setError(null)}
                  className="ml-auto text-red-400 hover:text-red-300"
                >
                  ×
                </button>
              </motion.div>
            )}

            {/* Processing overlay */}
            {processing ? (
              <div className="text-center py-12 space-y-4">
                <Loader2 className="h-10 w-10 animate-spin text-green-400 mx-auto" />
                <p className="text-gray-300 font-medium">Processing your payment…</p>
                <p className="text-gray-500 text-sm">Please do not close this page.</p>
              </div>
            ) : (
              <AnimatePresence mode="wait">
                <motion.div
                  key={activeMethod}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -8 }}
                  transition={{ duration: 0.15 }}
                >
                  {activeMethod === "upi" && <UpiForm onSubmit={handlePayment} />}
                  {activeMethod === "card" && <CardForm onSubmit={handlePayment} />}
                  {activeMethod === "netbanking" && (
                    <NetBankingForm onSubmit={handlePayment} />
                  )}
                  {activeMethod === "wallet" && <WalletForm onSubmit={handlePayment} />}
                </motion.div>
              </AnimatePresence>
            )}

            {/* Refresh status */}
            {!processing && (
              <button
                onClick={fetchPayment}
                className="mt-4 flex items-center gap-1.5 text-xs text-gray-600
                           hover:text-gray-400 transition-colors"
              >
                <RefreshCw className="h-3 w-3" />
                Refresh payment status
              </button>
            )}
          </div>
        </motion.div>
      </div>
    </div>
  );
}
