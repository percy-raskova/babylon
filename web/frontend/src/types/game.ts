/** TypeScript interfaces matching the Django API response schema. */

/** Standard API response envelope. */
export interface ApiResponse<T> {
  status: "ok" | "error";
  data: T;
  tick?: number;
  session_id?: string;
  message?: string;
}

/** Game session summary (from GET /api/games/). */
export interface GameSummary {
  id: string;
  scenario: string;
  current_tick: number;
  status: GameStatus;
  created_at: string;
}

export type GameStatus = "active" | "paused" | "completed" | "abandoned";

/** Full game state snapshot (from GET /api/games/{id}/state/). */
export interface GameSnapshot {
  tick: number;
  session_id: string;
  nodes: Record<string, NodeState>;
  edges: EdgeState[];
  organizations: Record<string, OrgState>;
  events: GameEvent[];
}

export interface NodeState {
  id: string;
  node_type: string;
  [key: string]: unknown;
}

export interface EdgeState {
  source: string;
  target: string;
  edge_type: string;
  weight: number;
}

export interface OrgState {
  id: string;
  name: string;
  org_type: string;
  resources: number;
  [key: string]: unknown;
}

export interface GameEvent {
  type: string;
  tick: number;
  data: Record<string, unknown>;
}

/** Available action for an organization. */
export interface AvailableAction {
  org_id: string;
  verb: string;
  action_type?: string;
  targets?: string[];
  cost?: number;
}

/** Pending player action. */
export interface PendingAction {
  id: number;
  org_id: string;
  verb: string;
  action_type?: string;
  target_id?: string;
  tick: number;
}

/** Action result from tick resolution. */
export interface ActionResultData {
  org_id: string;
  action_type: string;
  target_id?: string;
  initiative_score: number;
  action_cost: number;
  success: boolean;
  consciousness_delta?: number;
  heat_delta?: number;
  details?: Record<string, unknown>;
}

/** Parameters for submitting an action. */
export interface SubmitActionParams {
  org_id: string;
  verb: string;
  action_type?: string;
  target_id?: string;
  target_community?: string;
  params_json?: Record<string, unknown>;
}

/** Parameters for creating a new game. */
export interface CreateGameParams {
  scenario: string;
  config?: Record<string, unknown>;
  defines?: Record<string, unknown>;
  rng_seed?: number;
}

/** Auth state from /accounts/whoami/. */
export interface AuthState {
  is_authenticated: boolean;
  id?: number;
  username?: string;
}
