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
  /**
   * Key to use for the target in the submit payload.
   * Defaults to "target_id" if not specified.
   */
  targetPayloadKey?: string;
  /** Optional selector for predicted effect tooltip (Phase 5 renders this). */
  predictedEffect?: ScriptValue;
}
