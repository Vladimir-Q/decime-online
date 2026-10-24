"use client";

import { useEffect, useState } from "react";

import { AppNav } from "@/components/AppNav";
import { fetchAdminDashboard } from "@/lib/auth";
import type { AdminDashboardResponse } from "@/types/admin-dashboard";

export default function AdminUsagePage() {
  const [days, setDays] = useState(30);
  const [data, setData] = useState<AdminDashboardResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      setLoading(true);
      setError(null);
      try {
        const dashboard = await fetchAdminDashboard(days);
        if (!cancelled) {
          setData(dashboard);
        }
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : "Failed to load dashboard");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [days]);

  return (
    <main className="page">
      <AppNav isAdmin />
      <section className="hero">
        <p className="eyebrow">Admin</p>
        <h1>Usage & quality</h1>
        <p className="lead">LLM token spend and user translation ratings.</p>
        <label className="field-label" htmlFor="usage-days">
          Window (days)
        </label>
        <select
          id="usage-days"
          className="select"
          value={days}
          onChange={(event) => setDays(Number(event.target.value))}
        >
          <option value={7}>7</option>
          <option value={30}>30</option>
          <option value={90}>90</option>
        </select>
      </section>

      {loading ? <p className="muted">Loading…</p> : null}
      {error ? <p className="error">{error}</p> : null}

      {data ? (
        <>
          <section className="card settings-section">
            <h2>Translation model usage</h2>
            <p>
              Calls: <strong>{data.usage.calls}</strong>
            </p>
            <p>
              Tokens: <strong>{data.usage.total_tokens}</strong> (prompt{" "}
              {data.usage.prompt_tokens} · completion {data.usage.completion_tokens})
            </p>
            <p>
              Known cost: <strong>${data.usage.estimated_cost_usd.toFixed(4)}</strong>
              {data.usage.pricing_version ? (
                <span className="muted"> · {data.usage.pricing_version}</span>
              ) : null}
            </p>
            {(data.usage.unknown_price_calls ?? 0) > 0 ? (
              <p>
                Unknown price: <strong>{data.usage.unknown_price_calls}</strong> calls are not
                included in the dollar total.
              </p>
            ) : null}
            {(data.usage.legacy_unverified_cost_usd ?? 0) > 0 ? (
              <p>
                Historical estimate (not recalculated):{" "}
                <strong>${data.usage.legacy_unverified_cost_usd?.toFixed(4)}</strong>
              </p>
            ) : null}
            <ul className="usage-ops">
              {Object.entries(data.usage.by_operation).map(([operation, stats]) => (
                <li key={operation}>
                  <strong>{operation}</strong>: {stats.calls} calls · {stats.total_tokens} tokens · $
                  {stats.estimated_cost_usd.toFixed(4)}
                </li>
              ))}
            </ul>
          </section>

          <section className="card settings-section">
            <h2>Translation ratings</h2>
            <p>
              Total: <strong>{data.ratings.total}</strong> · Average score:{" "}
              <strong>{data.ratings.average_score}</strong>
            </p>
            <p>
              Good (1): {data.ratings.counts.good} · Mixed (0): {data.ratings.counts.mixed} · Bad
              (−1): {data.ratings.counts.bad}
            </p>
            <ul className="usage-ops">
              {Object.entries(data.ratings.by_feature).map(([feature, stats]) => (
                <li key={feature}>
                  <strong>{feature}</strong>: {stats.total} · good {stats.good} · mixed {stats.mixed}{" "}
                  · bad {stats.bad}
                </li>
              ))}
            </ul>
          </section>
        </>
      ) : null}
    </main>
  );
}
