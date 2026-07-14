/**
 * useActionPreview — live `/actions/preview/` fetch for the composed verb
 * (Program 17 Wave 1 item W1.2), alongside `useVerbTargets`.
 *
 * Fires once `gameId`/`orgId`/`verb` are set and the verb is composable — a
 * target is selected, or the verb's own `targetRequired` config says none is
 * needed (the same gate `VerbForm`/`useVerbTargets` use). Selection-driven,
 * not a text field, so there is deliberately no debounce: every composable
 * dependency change fires its own preview fetch immediately.
 *
 * Unlike `useVerbTargets` (which relies on `VerbForm`'s per-org+verb remount
 * to reset its `loading` flag via a lazy `useState` initializer), `targetId`
 * changes WITHOUT a remount here — so "loading" is instead DERIVED at render
 * time by comparing the current composable key against the key of the last
 * *settled* fetch (`settled`). The effect's only job is the fetch itself and
 * setting `settled` from its `.then()` callback — no synchronous setState in
 * the effect body (react-hooks/set-state-in-effect), and no stale chip ever
 * lingers across a target switch (a key mismatch alone forces `loading`).
 *
 * NOTE: only org_id/verb/target_id are sent (see `fetchActionPreview`) — the
 * backend's preview_action serializer accepts no params payload yet, so
 * mode-sensitive preview (e.g. attack's targeted vs mass mode, reproduce's
 * cadre_training vs mass_recruitment) is unplumbed backend-side.
 */

import { useEffect, useState } from "react";
import { fetchActionPreview } from "@/lib/verbs/fetchActionPreview";
import type { VerbConfig } from "@/lib/verbs";
import type { ActionPreviewResult, PlayerVerb } from "@/types/game";

export interface UseActionPreviewResult {
  /** The live preview, or null while loading / on error / when not yet composable. */
  preview: ActionPreviewResult | null;
  /** True while a preview fetch is in flight. */
  loading: boolean;
}

const IDLE: UseActionPreviewResult = { preview: null, loading: false };

interface Settled {
  /** The composable key this result was fetched for. */
  key: string;
  result: UseActionPreviewResult;
}

export function useActionPreview(
  gameId: string,
  orgId: string,
  verb: PlayerVerb,
  config: VerbConfig,
  targetId: string | null,
): UseActionPreviewResult {
  const targetRequired = config.targetRequired ?? true;
  const composable = Boolean(gameId && orgId && verb && (targetId || !targetRequired));
  const key = composable ? `${gameId}:${orgId}:${verb}:${targetId ?? ""}` : null;

  const [settled, setSettled] = useState<Settled | null>(null);

  useEffect(() => {
    if (!key) return;
    let cancelled = false;
    // fetchActionPreview never throws (it normalizes network/API errors into
    // its result object), so no unhandled-rejection guard is needed here.
    fetchActionPreview(gameId, orgId, verb, targetId).then((res) => {
      if (cancelled) return;
      setSettled({ key, result: { preview: res.ok ? res.data : null, loading: false } });
    });
    return () => {
      cancelled = true;
    };
  }, [key, gameId, orgId, verb, targetId]);

  if (!composable) return IDLE;
  if (settled?.key === key) return settled.result;
  return { preview: null, loading: true };
}
