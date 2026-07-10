/**
 * GameDefines constants — frontend subset of the Python GameDefines.
 *
 * These are the default values from babylon.config.defines.GameDefines,
 * frozen for frontend use. When a /api/gamedefines/ endpoint exists,
 * this should be hydrated from the API response instead.
 *
 * NOTE: Replace with API-hydrated values once a /api/gamedefines/ endpoint is available.
 */

export const GAMEDEFINES = Object.freeze({
  /** Heat penalty applied to cadre effectiveness (multiplicative). */
  HEAT_CADRE_PENALTY: 0.1,
  /** Base education cost in budget units. */
  EDUCATE_BASE_COST: 50.0,
  /** Base mobilize cost in cadre labor. */
  MOBILIZE_COST_CL: 0.2,
  /** Heat decay rate per tick. */
  HEAT_DECAY_RATE: 0.05,
  /** Consciousness routing shift per education tick. */
  EDUCATION_ROUTING_DELTA: 0.02,
  /** Attack cadre labor cost. */
  ATTACK_COST_CL: 2.0,
  /** Aid budget transfer minimum. */
  AID_TRANSFER_MIN: 10.0,
});

export type GameDefinesKey = keyof typeof GAMEDEFINES;
