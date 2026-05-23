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
      } catch (err: unknown) {
        if (cancelled) return;
        // 503 = explicitly "not ready yet" — extract message from response body
        const status = (err as { status?: number })?.status;
        const detail = (err as { detail?: { message?: string } })?.detail;
        if (status === 503) {
          setMessage(detail?.message || "AI pipeline is loading…");
        } else {
          // Network error or backend down — keep polling
          setMessage("Connecting to backend…");
        }
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
