"use client";

import { useState, useEffect, useRef } from "react";
import { chatService } from "@/services/chatService";

/**
 * Polls /api/ready until the backend AI pipeline is fully loaded.
 * Returns `ready=true` once warm, plus a status message for display.
 */
export function useBackendReady() {
  const [ready, setReady] = useState(false);
  const [message, setMessage] = useState("AI pipeline is loading…");
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    let cancelled = false;

    const check = async () => {
      try {
        const result = await chatService.checkReady();
        if (cancelled) return;
        if (result.ready) {
          setReady(true);
          setMessage("All systems operational");
          if (intervalRef.current) clearInterval(intervalRef.current);
        } else {
          setMessage(result.message || "AI pipeline is loading…");
        }
      } catch {
        // Backend might not be reachable yet — keep polling
        if (!cancelled) setMessage("Connecting to backend…");
      }
    };

    // Check immediately, then every 3 seconds
    check();
    intervalRef.current = setInterval(check, 3000);

    return () => {
      cancelled = true;
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, []);

  return { ready, message };
}
