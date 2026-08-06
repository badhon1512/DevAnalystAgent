"use client";

import { useCallback, useEffect, useState } from "react";

import { fetchPageViewStats } from "../lib/api";
import type { PageViewStats } from "../lib/types";

const WINDOWS = [7, 30, 90];

function formatDateTime(value: string) {
  return new Date(value).toLocaleString();
}

function location(country: string | null, city: string | null) {
  if (city && country) return `${city}, ${country}`;
  return country || city || "Unknown";
}

export default function TrafficPanel({ token }: { token: string }) {
  const [stats, setStats] = useState<PageViewStats | null>(null);
  const [days, setDays] = useState(30);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError("");
    try {
      setStats(await fetchPageViewStats(token, days));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load traffic.");
    } finally {
      setLoading(false);
    }
  }, [token, days]);

  useEffect(() => {
    void load();
  }, [load]);

  const peak = Math.max(1, ...(stats?.daily.map((d) => d.views) || [1]));

  return (
    <section className="adminGrid" style={{ marginTop: 24 }}>
      <div className="adminConversationList">
        <div className="adminPanelTitle trafficPanelHeader">
          <span>Site traffic</span>
          <span className="trafficWindowButtons">
            {WINDOWS.map((value) => (
              <button
                key={value}
                type="button"
                className="adminGhostButton"
                onClick={() => setDays(value)}
                aria-pressed={days === value}
                style={{ opacity: days === value ? 1 : 0.55 }}
              >
                {value}d
              </button>
            ))}
          </span>
        </div>

        {error ? <div className="adminError">{error}</div> : null}
        {loading && !stats ? <p>Loading traffic…</p> : null}

        {stats ? (
          <>
            <section className="adminStats">
              <div>
                <span>{stats.total_views}</span>
                <p>Views ({stats.window_days}d)</p>
              </div>
              <div>
                <span>{stats.unique_visitors}</span>
                <p>Unique visitors</p>
              </div>
              <div>
                <span>{stats.views_today}</span>
                <p>Today</p>
              </div>
            </section>

            <div className="adminPanelTitle">Views per day</div>
            <div className="trafficChart">
              {stats.daily.map((day) => (
                <div
                  key={day.date}
                  className="trafficChartBar"
                  title={`${day.date}: ${day.views} views, ${day.visitors} visitors`}
                  style={{ height: `${Math.round((day.views / peak) * 100)}%` }}
                />
              ))}
              {stats.daily.length === 0 ? <p>No views recorded yet.</p> : null}
            </div>

            <div className="adminPanelTitle">Top countries</div>
            {stats.top_countries.map((row) => (
              <div key={row.label} className="trafficRow">
                <span>{row.label}</span>
                <strong>{row.views}</strong>
              </div>
            ))}

            <div className="adminPanelTitle">Top referrers</div>
            {stats.top_referrers.map((row) => (
              <div key={row.label} className="trafficRow">
                <span>{row.label}</span>
                <strong>{row.views}</strong>
              </div>
            ))}

            <div className="adminPanelTitle">Recent visits</div>
            {stats.recent.map((view, index) => (
              <article key={`${view.viewed_at}-${index}`} className="adminConversationItem">
                <small className="trafficRecentRow">
                  {formatDateTime(view.viewed_at)} · {view.path} ·{" "}
                  {location(view.country, view.city)}
                </small>
              </article>
            ))}
            {stats.recent.length === 0 ? <p>No visits in this window.</p> : null}
          </>
        ) : null}
      </div>
    </section>
  );
}
