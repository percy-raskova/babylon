/**
 * Selector type system — Paradox-pattern typed selectors with breakdown support.
 *
 * Pure data types. No React, no store imports, no API calls.
 *
 * ScriptValue<T> is the core abstraction: a named computation over a GameSnapshot
 * that produces both a value and a recursive breakdown of contributors.
 */

import type { GameSnapshot } from "@/types/game";

// ---------------------------------------------------------------------------
// Scope — what entity the selector is evaluating "about"
// ---------------------------------------------------------------------------

/** Entity types that can serve as a scope target. */
export type ScopeEntityKind = "hex" | "org" | "institution" | "hyperedge" | "global";

/** Reference to a specific entity in the snapshot. */
export interface ScopeEntity {
  kind: ScopeEntityKind;
  id: string;
}

/**
 * Evaluation scope — the snapshot plus an optional focus entity.
 *
 * When `this` is null, the selector evaluates globally (e.g., averaged across
 * all territories). When `this` is a specific entity, the selector scopes
 * to that entity.
 */
export interface Scope {
  snapshot: GameSnapshot;
  this: ScopeEntity | null;
}

// ---------------------------------------------------------------------------
// Source references — provenance tracing
// ---------------------------------------------------------------------------

/**
 * Where a value was read from. Every leaf contributor must declare its source.
 *
 * - `snapshot_field`: read directly from `snapshot.{path}`
 * - `gamedefines`: read from the static GameDefines constants
 * - `derived`: computed from other selectors (non-leaf)
 */
export type SourceKind = "snapshot_field" | "gamedefines" | "derived";

export interface SourceRef {
  kind: SourceKind;
  /** Human-readable path, e.g. "territories[downtown].heat" or "GAMEDEFINES.HEAT_CADRE_PENALTY" */
  path: string;
}

// ---------------------------------------------------------------------------
// Breakdown — recursive contributor tree
// ---------------------------------------------------------------------------

/**
 * A single contributor to a breakdown. May itself contain sub-contributors
 * (for derived selectors that compose primitives).
 */
export interface Contributor {
  label: string;
  value: number;
  /** Fraction of the parent's total value. */
  share: number;
  source: SourceRef;
  /** Sub-breakdown. Empty for leaf values. */
  children: Contributor[];
}

/**
 * Full breakdown of a computed value. The `total` field must always equal
 * the result of `evaluate()` (consistency invariant).
 */
export interface Breakdown {
  total: number;
  contributors: Contributor[];
}

// ---------------------------------------------------------------------------
// ScriptValue<T> — the core selector primitive
// ---------------------------------------------------------------------------

/**
 * A named, typed selector that can evaluate a value from a game snapshot
 * and produce a recursive breakdown for provenance tracing.
 *
 * The generic parameter T is the return type of `evaluate()`.
 * Most selectors return `number`, but the type system supports richer values.
 */
export interface ScriptValue<T = number> {
  /** Unique name, e.g. "hex.heat" or "org.effective_cadre". */
  name: string;
  /** Human-readable label for UI display. */
  label: string;
  /** Short description of what this selector computes. */
  description: string;
  /** What kind of entity this selector is "about". */
  scopeKind: ScopeEntityKind;
  /** Compute the value for the given scope. */
  evaluate: (scope: Scope) => T;
  /** Compute a provenance breakdown for the given scope. */
  breakdown: (scope: Scope) => Breakdown;
}
