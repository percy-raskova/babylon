/**
 * ActionPage — config-driven action form using VerbShell.
 *
 * Phase 4: No per-verb switch statement. All form rendering
 * is driven by VERB_REGISTRY and VerbShell.
 */

import { useState, useEffect, useRef, useMemo } from "react";
import { useParams, useNavigate } from "react-router";
import { TopBar } from "@/components/layout/TopBar";
import { VerbShell } from "@/components/action/VerbShell";
import { useGameState } from "@/hooks/useGameState";
import { useGameStore } from "@/stores/gameStore";
import { VERB_REGISTRY } from "@/lib/verbs";
import type { PlayerVerb } from "@/types/game";

export function ActionPage({ username, onLogout }: { username: string; onLogout: () => void }) {
  const { id: gameId = "", verb = "educate" } = useParams<{ id: string; verb: string }>();
  const navigate = useNavigate();
  const { snapshot, resolveTick, loading: resolving } = useGameState(gameId);

  const config = VERB_REGISTRY[verb];

  // Store reads
  const playerOrgs = useGameStore((s) => s.playerOrgs);
  const playerOrgsLoaded = useGameStore((s) => s.playerOrgsLoaded);
  const fetchPlayerOrgs = useGameStore((s) => s.fetchPlayerOrgs);
  const verbTargets = useGameStore((s) => s.verbTargets);
  const fetchVerbTargets = useGameStore((s) => s.fetchVerbTargets);
  const submitAction = useGameStore((s) => s.submitAction);
  const storeError = useGameStore((s) => s.error);

  const [selectedOrgId, setSelectedOrgId] = useState("");
  const [selectedTargetId, setSelectedTargetId] = useState("");
  const [params, setParams] = useState<Record<string, unknown>>({});
  const [submitting, setSubmitting] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  const error = localError ?? storeError;
  const cacheKey = `${verb}:${selectedOrgId}`;
  const rawTargetData = verbTargets[cacheKey] as Record<string, unknown> | undefined;
  const loadingTargets = selectedOrgId !== "" && !rawTargetData;

  // Parse targets through verb config
  const parsedTargets = useMemo(
    () => (config && rawTargetData ? config.parseTargets(rawTargetData) : []),
    [config, rawTargetData],
  );

  // Fetch player orgs
  useEffect(() => {
    void fetchPlayerOrgs(gameId);
  }, [gameId, fetchPlayerOrgs]);

  // Auto-select first org
  useEffect(() => {
    if (playerOrgsLoaded && playerOrgs.length > 0 && !selectedOrgId) {
      setSelectedOrgId(playerOrgs[0]?.id ?? "");
    }
  }, [playerOrgsLoaded, playerOrgs, selectedOrgId]);

  // Auto-select tracking
  const autoSelectedRef = useRef("");

  // Fetch targets when org/verb changes
  useEffect(() => {
    if (!selectedOrgId) return;
    setSelectedTargetId("");
    autoSelectedRef.current = "";
    void fetchVerbTargets(gameId, verb as PlayerVerb, selectedOrgId);
  }, [gameId, selectedOrgId, verb, fetchVerbTargets]);

  // Auto-select first target
  useEffect(() => {
    if (parsedTargets.length === 0) return;
    if (autoSelectedRef.current === cacheKey) return;
    autoSelectedRef.current = cacheKey;
    setSelectedTargetId(parsedTargets[0]?.id ?? "");
  }, [parsedTargets, cacheKey]);

  // Initialize default param values from config
  useEffect(() => {
    if (!config) return;
    const defaults: Record<string, unknown> = {};
    for (const f of config.paramFields) {
      defaults[f.key] = f.defaultValue;
    }
    setParams(defaults);
  }, [config]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedOrgId || !config) return;

    setSubmitting(true);
    setLocalError(null);
    try {
      const targetKey = config.targetPayloadKey ?? "target_id";
      await submitAction(gameId, {
        org_id: selectedOrgId,
        verb: verb as PlayerVerb,
        target_id: selectedTargetId,
        ...(targetKey !== "target_id" ? { [targetKey]: selectedTargetId } : {}),
        params,
      });
      navigate(`/games/${gameId}`);
    } catch {
      setLocalError("Error submitting action");
    } finally {
      setSubmitting(false);
    }
  }

  if (!config) {
    return (
      <div className="flex h-screen items-center justify-center bg-void text-crimson">
        Unknown verb: {verb}
      </div>
    );
  }

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-void">
      {snapshot && (
        <TopBar
          snapshot={snapshot}
          gameId={gameId}
          username={username}
          resolving={resolving}
          onResolve={async () => {
            await resolveTick();
          }}
          onBack={() => navigate(`/games/${gameId}`)}
          onLogout={onLogout}
        />
      )}

      <div className="flex flex-1 flex-col overflow-hidden p-6">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-xl font-bold tracking-wider text-gold uppercase">
            Action: {config.label}
          </h2>
          <button
            onClick={() => navigate(`/games/${gameId}`)}
            className="rounded border border-wet-concrete px-4 py-2 text-sm text-silver hover:border-gold"
          >
            ← Back to Briefing
          </button>
        </div>

        <div className="mx-auto mt-8 w-full max-w-xl rounded-lg border border-wet-concrete bg-dark-metal p-6">
          <VerbShell
            config={config}
            orgs={playerOrgs}
            orgsLoaded={playerOrgsLoaded}
            selectedOrgId={selectedOrgId}
            onOrgChange={setSelectedOrgId}
            targets={parsedTargets}
            loadingTargets={loadingTargets}
            selectedTargetId={selectedTargetId}
            onTargetChange={setSelectedTargetId}
            params={params}
            onParamChange={(key, val) => setParams((p) => ({ ...p, [key]: val }))}
            submitting={submitting}
            onSubmit={handleSubmit}
            error={error}
          />
        </div>
      </div>
    </div>
  );
}
