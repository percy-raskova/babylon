/**
 * domainMemo.ts — per-lens, per-session ramp-domain memoization
 * (DESIGN_BIBLE.md §3.2/§6: "Ramp DOMAIN fixed per session/lens — silent
 * rescaling between ticks is banned; domain changes fire a legend flash").
 *
 * A ramp lens's [min, max] normalization domain is computed fresh from
 * whatever data is on screen (`computeFillDomain` in `DeckGLMap.tsx`). Used
 * naively, that domain silently rescales every tick as the data's real
 * range drifts — the SAME raw value would paint a different color on tick
 * 10 vs. tick 50, which is exactly the "dequantified animation" Tufte
 * integrity violation the bible bans. `createDomainMemo()` instead captures
 * the FIRST domain observed for a lens (keyed by `lensKey`) and keeps
 * returning that fixed domain; a later render with wider data ONLY reports
 * `changed: true` (for the caller to fire a legend flash) without silently
 * adopting the wider range — a real rescale stays a deliberate,
 * caller-decided event.
 */

export interface FillDomain {
  min: number;
  max: number;
}

export interface DomainMemo {
  /**
   * Resolve the domain to actually use for `key` given `natural` (the
   * domain a fresh scan of the current data would produce). First call for
   * a given `key` adopts `natural` outright. Every later call for the same
   * `key` returns the ORIGINAL cached domain, reporting `changed: true`
   * exactly when `natural` would have required a wider domain than the
   * cached one (a real rescale event the caller may choose to act on —
   * this memo never adopts it automatically).
   */
  resolve(key: string, natural: FillDomain): { domain: FillDomain; changed: boolean };
  /** Test/lens-registry-reset hook — clears every cached domain. */
  reset(): void;
}

function widens(natural: FillDomain, cached: FillDomain): boolean {
  return natural.min < cached.min || natural.max > cached.max;
}

/** One memo instance per map surface (e.g. one per `DeckGLMap` mount) — never a module singleton. */
export function createDomainMemo(): DomainMemo {
  const cache = new Map<string, FillDomain>();
  return {
    resolve(key, natural) {
      const cached = cache.get(key);
      if (!cached) {
        cache.set(key, natural);
        return { domain: natural, changed: false };
      }
      return { domain: cached, changed: widens(natural, cached) };
    },
    reset() {
      cache.clear();
    },
  };
}
