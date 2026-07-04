/**
 * Client-side CSV export for a fetched series (no extra round trip).
 *
 * The server's `series.csv/` endpoint is the contract of record; this mirror
 * lets the browser export the already-loaded points offline.
 */

import { SERIES_METRICS, type ValueAggregatePoint } from "./types";

const COLUMNS = ["tick", ...SERIES_METRICS] as const;

/** Serialise series points to CSV text (header row + one row per tick). */
export function seriesToCsv(points: ValueAggregatePoint[]): string {
  const header = COLUMNS.join(",");
  const rows = points.map((p) => COLUMNS.map((col) => p[col]).join(","));
  return [header, ...rows].join("\n");
}

/** Trigger a browser download of `csvText` as `filename`. */
export function downloadCsv(filename: string, csvText: string): void {
  const blob = new Blob([csvText], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}
