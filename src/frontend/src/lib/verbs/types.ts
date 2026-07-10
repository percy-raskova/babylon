/**
 * Verb configuration types — drives the generic ActionPage form.
 */

import type { ScriptValue } from "@/lib/selectors/types";

/** A target option parsed from the API's verb-target endpoint response. */
export interface VerbTarget {
  /** Unique target identifier. */
  id: string;
  /** Human-readable label. */
  label: string;
  /** Optional group name for <optgroup> rendering. */
  group?: string;
}

/** A dynamic form field definition for verb-specific parameters. */
export interface ParamField {
  /** Field key in the params object. */
  key: string;
  /** Human-readable label. */
  label: string;
  /** Field type. */
  type: "number" | "select" | "text";
  /** Default value. */
  defaultValue: string | number;
  /** Options for select fields. */
  options?: { value: string; label: string }[];
  /** Minimum value for number fields. */
  min?: number;
  /** Maximum value for number fields. */
  max?: number;
}

/**
 * POST body for ``/api/games/{id}/actions/{verb}/`` (the verb rides in
 * the URL path, never in the body — Spec 040).
 */
export interface VerbSubmitBody {
  /** Acting organization id — required by every verb serializer. */
  org_id: string;
  /** Verb-specific fields: target key, params nesting, enum values. */
  [key: string]: unknown;
}

/** Complete configuration for one player verb. */
export interface VerbConfig {
  /** The verb identifier (matches PlayerVerb). */
  verb: string;
  /** Human-readable label. */
  label: string;
  /** Short description of what this verb does. */
  description: string;
  /** Parse the raw API target response into a flat list of VerbTarget. */
  parseTargets: (raw: Record<string, unknown>) => VerbTarget[];
  /** Additional form parameter fields beyond org and target. */
  paramFields: ParamField[];
  /** Whether a target selection is required before submit (default true). */
  targetRequired?: boolean;
  /** Where eligible targets come from: the live per-verb GET endpoint, or the
   *  snapshot (campaign has no targets endpoint — GET returns 405). */
  targetsSource?: "endpoint" | "snapshot";
  /** Build the POST body the verb's submit serializer requires. */
  buildPayload: (
    orgId: string,
    targetId: string | null,
    params: Record<string, unknown>,
  ) => VerbSubmitBody;
  /**
   * Key to use for the target in the submit payload.
   * Defaults to "target_id" if not specified.
   */
  targetPayloadKey?: string;
  /** Optional selector for predicted effect tooltip (Phase 5 renders this). */
  predictedEffect?: ScriptValue;
}
