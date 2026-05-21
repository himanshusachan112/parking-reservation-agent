"use client";

/**
 * DemoBanner — shown only when NEXT_PUBLIC_APP_ENV=demo.
 *
 * LOCAL mode  → banner is hidden; zero layout impact.
 * DEMO mode   → yellow sticky bar at the very top of every page.
 *
 * WHY: Visitors arriving via a shared ngrok link need to know they are
 * looking at a live demo, not a production service.  The banner also
 * shows the API URL so the presenter can quickly verify the backend
 * connection during a live showcase.
 */

const IS_DEMO = process.env.NEXT_PUBLIC_APP_ENV === "demo";
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function DemoBanner() {
  if (!IS_DEMO) return null;

  return (
    <div className="w-full bg-amber-400 text-amber-950 text-xs font-semibold py-1.5 px-4 flex items-center justify-center gap-3 z-50">
      <span className="text-sm">🚀</span>
      <span>ParkSmart AI — Public Demo Environment</span>
      <span className="hidden sm:inline opacity-60">·</span>
      <span className="hidden sm:inline font-normal opacity-70">
        Backend: {API_URL}
      </span>
    </div>
  );
}
