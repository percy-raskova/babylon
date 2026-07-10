/**
 * Barrel export for the Babylon design-system primitives ported for the
 * takeover surfaces (spec-110 B5). Only the subset `BlocFlowLines` needs —
 * the full `web/frontend/src/components/bbl/` set (BblPanel, BblBadge,
 * BblTooltip, Gauge, Stat) has no consumer in `src/frontend` yet, so it
 * stays unported until something needs it (DRY: port on demand, not
 * speculatively).
 *
 * Usage: import { BblLabel, BblData, Sparkline } from "@/components/bbl";
 */

export { BblLabel } from "./BblLabel";
export { BblData } from "./BblData";
export { Sparkline } from "./Sparkline";
