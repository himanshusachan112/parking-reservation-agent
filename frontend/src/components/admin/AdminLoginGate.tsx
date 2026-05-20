"use client";

import { useState, useEffect, type FormEvent } from "react";
import { Shield, Eye, EyeOff, LogIn, AlertCircle } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuthStore } from "@/store/authStore";

export function AdminLoginGate({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const isLoading = useAuthStore((s) => s.isLoading);
  const error = useAuthStore((s) => s.error);
  const login = useAuthStore((s) => s.login);
  const clearError = useAuthStore((s) => s.clearError);

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [hydrated, setHydrated] = useState(false);

  // Restore session on mount
  useEffect(() => {
    if (typeof window !== "undefined") {
      const saved = sessionStorage.getItem("parksmart_admin_auth");
      if (saved === "1") {
        useAuthStore.setState({ isAuthenticated: true });
      }
    }
    setHydrated(true);
  }, []);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password.trim()) return;
    await login(username.trim(), password);
  };

  // Avoid hydration mismatch
  if (!hydrated) return null;

  if (isAuthenticated) {
    return <>{children}</>;
  }

  return (
    <div className="flex-1 flex items-center justify-center p-4">
      <motion.div
        initial={{ opacity: 0, y: 20, scale: 0.97 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.4, ease: "easeOut" }}
        className="w-full max-w-md"
      >
        <div className="rounded-2xl border bg-card shadow-xl overflow-hidden">
          {/* Header */}
          <div className="bg-gradient-to-br from-primary/10 via-primary/5 to-transparent px-8 pt-8 pb-6 text-center">
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ delay: 0.15, type: "spring", stiffness: 200 }}
              className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10 ring-1 ring-primary/20"
            >
              <Shield className="h-8 w-8 text-primary" />
            </motion.div>
            <h2 className="text-xl font-bold tracking-tight">Admin Portal</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              Enter your credentials to access the dashboard
            </p>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="px-8 pb-8 pt-6 space-y-5">
            <AnimatePresence mode="wait">
              {error && (
                <motion.div
                  key="error"
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  className="flex items-center gap-2 rounded-lg bg-destructive/10 border border-destructive/20 px-4 py-3 text-sm text-destructive"
                >
                  <AlertCircle className="h-4 w-4 shrink-0" />
                  <span>{error}</span>
                </motion.div>
              )}
            </AnimatePresence>

            <div className="space-y-2">
              <Label htmlFor="username">Username</Label>
              <Input
                id="username"
                type="text"
                placeholder="Enter username"
                value={username}
                onChange={(e) => {
                  setUsername(e.target.value);
                  if (error) clearError();
                }}
                autoComplete="username"
                autoFocus
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <div className="relative">
                <Input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  placeholder="Enter password"
                  value={password}
                  onChange={(e) => {
                    setPassword(e.target.value);
                    if (error) clearError();
                  }}
                  autoComplete="current-password"
                  className="pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                  tabIndex={-1}
                >
                  {showPassword ? (
                    <EyeOff className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                </button>
              </div>
            </div>

            <Button
              type="submit"
              className="w-full gap-2"
              disabled={isLoading || !username.trim() || !password.trim()}
            >
              {isLoading ? (
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ repeat: Infinity, duration: 1, ease: "linear" }}
                  className="h-4 w-4 border-2 border-primary-foreground/30 border-t-primary-foreground rounded-full"
                />
              ) : (
                <LogIn className="h-4 w-4" />
              )}
              {isLoading ? "Authenticating..." : "Sign In"}
            </Button>

            <div className="rounded-lg bg-muted/50 border px-4 py-3">
              <p className="text-xs font-medium text-muted-foreground mb-1.5">
                Demo Credentials
              </p>
              <div className="flex gap-4 text-xs">
                <span className="text-foreground">
                  <span className="text-muted-foreground">User: </span>
                  <code className="font-mono bg-muted px-1.5 py-0.5 rounded">
                    admin
                  </code>
                </span>
                <span className="text-foreground">
                  <span className="text-muted-foreground">Pass: </span>
                  <code className="font-mono bg-muted px-1.5 py-0.5 rounded">
                    admin123
                  </code>
                </span>
              </div>
            </div>
          </form>
        </div>
      </motion.div>
    </div>
  );
}
