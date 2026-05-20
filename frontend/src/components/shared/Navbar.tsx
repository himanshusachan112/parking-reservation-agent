"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Car, MessageSquare, LayoutDashboard, LogOut } from "lucide-react";
import { ThemeToggle } from "./ThemeToggle";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/store/authStore";

const navItems = [
  { href: "/chat", label: "Chat", icon: MessageSquare },
  { href: "/admin", label: "Admin", icon: LayoutDashboard },
];

export function Navbar() {
  const pathname = usePathname();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const logout = useAuthStore((s) => s.logout);
  const isAdmin = pathname.startsWith("/admin");

  return (
    <header className="sticky top-0 z-50 border-b bg-background/80 backdrop-blur-xl">
      <div className="flex h-14 items-center px-4 md:px-6">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2 mr-6">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
            <Car className="h-4 w-4 text-primary-foreground" />
          </div>
          <span className="font-semibold text-lg hidden sm:inline-block">
            ParkSmart
          </span>
        </Link>

        {/* Nav Links */}
        <nav className="flex items-center gap-1">
          {navItems.map((item) => {
            const isActive = pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-primary/10 text-primary"
                    : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                )}
              >
                <item.icon className="h-4 w-4" />
                <span className="hidden sm:inline">{item.label}</span>
              </Link>
            );
          })}
        </nav>

        {/* Right side */}
        <div className="ml-auto flex items-center gap-2">
          {isAdmin && isAuthenticated && (
            <button
              onClick={logout}
              className="flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium text-muted-foreground hover:bg-destructive/10 hover:text-destructive transition-colors"
            >
              <LogOut className="h-4 w-4" />
              <span className="hidden sm:inline">Logout</span>
            </button>
          )}
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}
