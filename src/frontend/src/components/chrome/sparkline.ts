/**
 * Shared sparkline geometry for the chrome widgets' history strips
 * (Playability Spine Task 21, spec-116 4d.5).
 *
 * Maps a parallel-indexed nullable series (the `TimeseriesPayload` arrays)
 * onto an SVG polyline `points` string. Null/undefined entries are SKIPPED,
 * never interpolated to a fabricated baseline (Constitution III.11) — the
 * series is a year-boundary step function with a null head, so the line
 * simply starts at the first real point.
 */

export interface SparklinePoint {
  x: number;
  y: number;
}

/** Extract the plottable (tick-index, value) pairs from a nullable series. */
export function sparklineSeries(values: readonly (number | null | undefined)[]): SparklinePoint[] {
  const points: SparklinePoint[] = [];
  values.forEach((value, index) => {
    if (typeof value === "number" && Number.isFinite(value)) {
      points.push({ x: index, y: value });
    }
  });
  return points;
}

/**
 * SVG polyline `points` for a nullable series scaled into a width x height
 * box (1px padding). Returns `null` when fewer than two real points exist —
 * a single point is not a trend and renders nothing rather than a dot of
 * fabricated significance.
 */
export function sparklinePoints(
  values: readonly (number | null | undefined)[],
  width: number,
  height: number,
): string | null {
  const series = sparklineSeries(values);
  const first = series[0];
  const last = series[series.length - 1];
  // The `!first || !last` arm is unreachable once `series.length >= 2`
  // (both indices exist) — it's what lets strict `noUncheckedIndexedAccess`
  // narrow them below without a non-null assertion (forbidden on
  // production code by this project's eslint config).
  if (series.length < 2 || !first || !last) return null;
  const xMin = first.x;
  const xMax = last.x;
  const ys = series.map((p) => p.y);
  const yMin = Math.min(...ys);
  const yMax = Math.max(...ys);
  const xSpan = xMax - xMin || 1;
  const ySpan = yMax - yMin || 1;
  const pad = 1;
  return series
    .map((p) => {
      const x = pad + ((p.x - xMin) / xSpan) * (width - 2 * pad);
      const y = height - pad - ((p.y - yMin) / ySpan) * (height - 2 * pad);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
}
