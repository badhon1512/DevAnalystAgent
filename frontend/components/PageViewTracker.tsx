"use client";

import { useEffect } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";
const SESSION_KEY = "productai-view-session";

/**
 * Records a single view per session per path.
 *
 * Fires after paint and swallows every error: analytics must never surface a
 * failure on the page it is measuring.
 */
export default function PageViewTracker({ path }: { path: string }) {
  useEffect(() => {
    const seenKey = `${SESSION_KEY}:${path}`;
    let sessionId = "";

    try {
      // One view per path per session, so a refresh is not counted twice.
      if (sessionStorage.getItem(seenKey)) return;

      sessionId = sessionStorage.getItem(SESSION_KEY) || "";
      if (!sessionId) {
        sessionId = crypto.randomUUID();
        sessionStorage.setItem(SESSION_KEY, sessionId);
      }
    } catch {
      // Private browsing can block sessionStorage; still record the view.
    }

    const markCounted = () => {
      try {
        sessionStorage.setItem(seenKey, "1");
      } catch {
        // Nothing to do; an uncounted retry is better than a lost view.
      }
    };

    // Marked only after the server confirms, so a failed request (backend down,
    // for instance) is retried on the next load rather than silently suppressed.
    void fetch(`${API_BASE}/page-views`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        path,
        referrer: document.referrer || null,
        session_id: sessionId || null,
      }),
      keepalive: true,
    })
      .then((res) => {
        if (res.ok) markCounted();
      })
      .catch(() => undefined);
  }, [path]);

  return null;
}
