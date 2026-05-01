/**
 * Barrel export — importing this module auto-registers all selectors.
 */

export type {
  ScriptValue,
  Scope,
  ScopeEntity,
  ScopeEntityKind,
  Breakdown,
  Contributor,
  SourceRef,
  SourceKind,
} from "./types";

export { SelectorRegistry, selectors } from "./registry";
export { GAMEDEFINES } from "./gamedefines";

// Side-effect imports: registration of all selectors
import "./primitives";
import "./derived";
