/**
 * Typed client for the read-only Observatory endpoints (`/api/observatory/*`).
 *
 * Reuses the shared API client (CSRF + credentials + standard envelope). Each
 * function unwraps the `{status, data}` envelope; on any non-ok response the
 * caller receives `null` / `[]` so the UI can render an unavailable state
 * rather than throw (the backend 404s the whole surface when the feature flag
 * is off, and 403s when unauthenticated).
 */

import { get } from "@/api/client";
import type {
  CommitRecord,
  ObservatorySession,
  ObservatoryStatus,
  Scope,
  Series,
  TickRange,
} from "./types";

const BASE = "/api/observatory";

/** Probe the feature flag. Returns the status, or `null` when unavailable. */
export async function fetchStatus(): Promise<ObservatoryStatus | null> {
  const res = await get<ObservatoryStatus>(`${BASE}/status/`);
  return res.status === "ok" ? res.data : null;
}

/** List sessions with at least one committed tick, for the given source. */
export async function fetchSessions(
  source: "live" | "archive" = "live",
): Promise<ObservatorySession[]> {
  const q = source === "archive" ? "?source=archive" : "";
  const res = await get<ObservatorySession[]>(`${BASE}/sessions/${q}`);
  return res.status === "ok" ? res.data : [];
}

/** Committed tick range for a session, or `null` when none / unavailable. */
export async function fetchTickRange(sessionId: string): Promise<TickRange | null> {
  const res = await get<TickRange>(`${BASE}/sessions/${sessionId}/ticks/`);
  return res.status === "ok" ? res.data : null;
}

/** Fetch a value-aggregate series for a scope. */
export async function fetchSeries(
  sessionId: string,
  scope: Scope,
  scopeId: string,
  opts: { fromTick?: number; toTick?: number; source?: "live" | "archive" } = {},
): Promise<Series | null> {
  const params = new URLSearchParams({ scope });
  if (scope !== "national") {
    params.set("scope_id", scopeId);
  }
  if (opts.fromTick !== undefined) {
    params.set("from_tick", String(opts.fromTick));
  }
  if (opts.toTick !== undefined) {
    params.set("to_tick", String(opts.toTick));
  }
  if (opts.source === "archive") {
    params.set("source", "archive");
  }
  const res = await get<Series>(`${BASE}/sessions/${sessionId}/series/?${params.toString()}`);
  return res.status === "ok" ? res.data : null;
}

/** Fetch the per-tick commit hash chain summary. */
export async function fetchCommits(sessionId: string): Promise<CommitRecord[]> {
  const res = await get<CommitRecord[]>(`${BASE}/sessions/${sessionId}/commits/`);
  return res.status === "ok" ? res.data : [];
}

/** Direct-download URL for the server-rendered CSV of a series. */
export function seriesCsvUrl(sessionId: string, scope: Scope, scopeId: string): string {
  const params = new URLSearchParams({ scope });
  if (scope !== "national") {
    params.set("scope_id", scopeId);
  }
  return `${BASE}/sessions/${sessionId}/series.csv/?${params.toString()}`;
}
