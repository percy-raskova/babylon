/**
 * Verb configuration public API.
 */

export type { VerbConfig, VerbTarget, ParamField, VerbSubmitBody } from "./types";
export { VERB_REGISTRY, VERB_NAMES } from "./registry";
export { fetchVerbTargets } from "./fetchVerbTargets";
export type { VerbTargetsResult } from "./fetchVerbTargets";
