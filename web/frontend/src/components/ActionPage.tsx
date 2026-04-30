/* eslint-disable @typescript-eslint/no-unsafe-member-access, @typescript-eslint/no-unsafe-assignment, @typescript-eslint/no-unsafe-call */
import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router";
import { get, post } from "@/api/client";
import { TopBar } from "@/components/layout/TopBar";
import { useGameState } from "@/hooks/useGameState";
import type { OrgState } from "@/types/game";

export function ActionPage({ username, onLogout }: { username: string; onLogout: () => void }) {
  const { id: gameId = "", verb = "educate" } = useParams<{ id: string; verb: string }>();
  const navigate = useNavigate();

  const { snapshot, resolveTick, loading: resolving } = useGameState(gameId);

  const [orgs, setOrgs] = useState<OrgState[]>([]);
  const [selectedOrgId, setSelectedOrgId] = useState<string>("");
  const [targetData, setTargetData] = useState<Record<string, unknown> | null>(null);
  const [loadingOrgs, setLoadingOrgs] = useState(true);
  const [loadingTargets, setLoadingTargets] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form state
  const [selectedTargetId, setSelectedTargetId] = useState<string>("");
  const [params, setParams] = useState<Record<string, unknown>>({});

  useEffect(() => {
    async function fetchOrgs() {
      try {
        const res = await get<{ organizations: OrgState[] }>(
          `/api/games/${gameId}/organizations/?player_only=true`,
        );
        if (res.status === "ok") {
          setOrgs(res.data.organizations);
          if (res.data.organizations.length > 0) {
            setSelectedOrgId(res.data.organizations[0]?.id ?? "");
          }
        }
      } catch {
        setError("Error fetching organizations");
      } finally {
        setLoadingOrgs(false);
      }
    }
    void fetchOrgs();
  }, [gameId]);

  useEffect(() => {
    if (!selectedOrgId) return;
    // eslint-disable-next-line complexity -- branching per verb type
    async function fetchTargets() {
      setLoadingTargets(true);
      setError(null);
      setTargetData(null);
      setSelectedTargetId("");
      try {
        const res = await get<Record<string, unknown>>(
          `/api/games/${gameId}/actions/${verb}/targets/?org_id=${selectedOrgId}`,
        );
        if (res.status === "ok" || (res.data as Record<string, unknown>).targets) {
          setTargetData(res.data);
          // Set default target if possible
          const raw = res.data as Record<string, unknown>;
          const targets = raw.targets as Record<string, string>[] | undefined;
          const popTargets = raw.population_targets as Record<string, string>[] | undefined;
          if (verb === "educate" && Array.isArray(targets) && targets.length > 0)
            setSelectedTargetId(targets[0]?.community_id ?? "");
          else if (verb === "aid" && Array.isArray(popTargets) && popTargets.length > 0)
            setSelectedTargetId(popTargets[0]?.community_id ?? "");
          else if (Array.isArray(targets) && targets.length > 0)
            setSelectedTargetId(targets[0]?.target_id || targets[0]?.id || "");
        } else {
          setError("Failed to fetch targets");
        }
      } catch {
        setError("Error fetching targets");
      } finally {
        setLoadingTargets(false);
      }
    }
    void fetchTargets();
  }, [gameId, selectedOrgId, verb]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedOrgId) return;

    // Fallback ID handling if verb has different names
    let payloadTargetId = selectedTargetId;
    const tdTargets = (targetData as Record<string, unknown> | null)?.targets as
      | Record<string, string>[]
      | undefined;
    if (
      verb === "educate" &&
      !payloadTargetId &&
      Array.isArray(tdTargets) &&
      tdTargets.length > 0
    ) {
      payloadTargetId = tdTargets[0]?.community_id ?? "";
    }

    const payload = {
      org_id: selectedOrgId,
      target_community_id: verb === "educate" ? payloadTargetId : undefined,
      target_id: verb !== "educate" ? payloadTargetId : undefined,
      params,
    };

    setSubmitting(true);
    setError(null);
    try {
      const res = await post<{ status: string; message?: string }>(
        `/api/games/${gameId}/actions/${verb}/`,
        payload,
      );
      if (res.status === "ok") {
        navigate(`/games/${gameId}`);
      } else {
        setError(res.message || "Failed to submit action");
      }
    } catch {
      setError("Error submitting action");
    } finally {
      setSubmitting(false);
    }
  }

  interface FormProps {
    verb: string;
    targetData: Record<string, unknown>;
    selectedTargetId: string;
    setSelectedTargetId: (id: string) => void;
    params: Record<string, unknown>;
    setParams: (p: Record<string, unknown>) => void;
  }

  function EducateForm({ targetData, selectedTargetId, setSelectedTargetId }: FormProps) {
    return (
      <div>
        <label
          htmlFor="target-select"
          className="mb-2 block text-sm font-semibold tracking-wider text-ash uppercase"
        >
          Select Target Territory (Community)
        </label>
        <select
          id="target-select"
          value={selectedTargetId}
          onChange={(e) => setSelectedTargetId(e.target.value)}
          className="w-full rounded border border-wet-concrete bg-void p-2 text-bone"
        >
          {((targetData.targets as Record<string, string>[]) || []).map((t) => (
            <option key={t.community_id} value={t.community_id}>
              {t.territory_name} ({t.category} - Credibility: {t.credibility})
            </option>
          ))}
        </select>
      </div>
    );
  }

  function AidForm({
    targetData,
    selectedTargetId,
    setSelectedTargetId,
    params,
    setParams,
  }: FormProps) {
    return (
      <>
        <div>
          <label
            htmlFor="target-select"
            className="mb-2 block text-sm font-semibold tracking-wider text-ash uppercase"
          >
            Select Target
          </label>
          <select
            id="target-select"
            value={selectedTargetId}
            onChange={(e) => setSelectedTargetId(e.target.value)}
            className="w-full rounded border border-wet-concrete bg-void p-2 text-bone"
          >
            <optgroup label="Communities">
              {((targetData.population_targets as Record<string, string>[]) || []).map((t) => (
                <option key={t.community_id} value={t.community_id}>
                  {t.community_name}
                </option>
              ))}
            </optgroup>
            <optgroup label="Organizations">
              {((targetData.org_targets as Record<string, string>[]) || []).map((t) => (
                <option key={t.org_id} value={t.org_id}>
                  {t.org_name}
                </option>
              ))}
            </optgroup>
          </select>
        </div>
        <div className="mt-4">
          <label
            htmlFor="amount"
            className="mb-2 block text-sm font-semibold tracking-wider text-ash uppercase"
          >
            Transfer Amount
          </label>
          <input
            id="amount"
            type="number"
            min="0"
            value={(params.transfer_amount as number) || 0}
            onChange={(e) => setParams({ ...params, transfer_amount: parseFloat(e.target.value) })}
            className="w-full rounded border border-wet-concrete bg-void p-2 text-bone"
          />
        </div>
      </>
    );
  }

  function AttackForm({
    targetData,
    selectedTargetId,
    setSelectedTargetId,
    params,
    setParams,
  }: FormProps) {
    return (
      <>
        <div>
          <label
            htmlFor="target-select"
            className="mb-2 block text-sm font-semibold tracking-wider text-ash uppercase"
          >
            Select Target
          </label>
          <select
            id="target-select"
            value={selectedTargetId}
            onChange={(e) => setSelectedTargetId(e.target.value)}
            className="w-full rounded border border-wet-concrete bg-void p-2 text-bone"
          >
            <optgroup label="Organizations">
              {(
                ((targetData as Record<string, Record<string, unknown>>).targets
                  ?.organizations as Record<string, string>[]) || []
              ).map((t) => (
                <option key={t.target_id} value={t.target_id}>
                  {t.name}
                </option>
              ))}
            </optgroup>
            <optgroup label="Institutions">
              {(
                ((targetData as Record<string, Record<string, unknown>>).targets
                  ?.institutions as Record<string, string>[]) || []
              ).map((t) => (
                <option key={t.target_id} value={t.target_id}>
                  {t.name}
                </option>
              ))}
            </optgroup>
          </select>
        </div>
        <div className="mt-4">
          <label
            htmlFor="mode"
            className="mb-2 block text-sm font-semibold tracking-wider text-ash uppercase"
          >
            Attack Mode
          </label>
          <select
            id="mode"
            value={(params.mode as string) || "targeted"}
            onChange={(e) => setParams({ ...params, mode: e.target.value })}
            className="w-full rounded border border-wet-concrete bg-void p-2 text-bone"
          >
            <option value="targeted">Targeted Sabotage</option>
            <option value="mass">Mass Action</option>
          </select>
        </div>
      </>
    );
  }

  function MobilizeForm({
    targetData,
    selectedTargetId,
    setSelectedTargetId,
    params,
    setParams,
  }: FormProps) {
    return (
      <>
        <div>
          <label
            htmlFor="target-select"
            className="mb-2 block text-sm font-semibold tracking-wider text-ash uppercase"
          >
            Select Target
          </label>
          <select
            id="target-select"
            value={selectedTargetId}
            onChange={(e) => setSelectedTargetId(e.target.value)}
            className="w-full rounded border border-wet-concrete bg-void p-2 text-bone"
          >
            {((targetData.targets as Record<string, string>[]) || []).map((t) => (
              <option key={t.id} value={t.id}>
                {t.name}
              </option>
            ))}
          </select>
        </div>
        <div className="mt-4">
          <label
            htmlFor="sl"
            className="mb-2 block text-sm font-semibold tracking-wider text-ash uppercase"
          >
            Sympathizer Labor Committed
          </label>
          <input
            id="sl"
            type="number"
            min="0"
            value={(params.sl_committed as number) || 0}
            onChange={(e) => setParams({ ...params, sl_committed: parseFloat(e.target.value) })}
            className="w-full rounded border border-wet-concrete bg-void p-2 text-bone"
          />
        </div>
      </>
    );
  }

  function GenericForm({ verb, targetData, selectedTargetId, setSelectedTargetId }: FormProps) {
    return (
      <div>
        <p className="text-silver">
          Specific form for {verb} not yet fully implemented. Using generic selector.
        </p>
        <label
          htmlFor="target-select"
          className="mt-4 mb-2 block text-sm font-semibold tracking-wider text-ash uppercase"
        >
          Select Target
        </label>
        <select
          id="target-select"
          value={selectedTargetId}
          onChange={(e) => setSelectedTargetId(e.target.value)}
          className="w-full rounded border border-wet-concrete bg-void p-2 text-bone"
        >
          {((targetData.targets as Record<string, string>[]) || []).map((t) => (
            <option
              key={t.id || t.target_id || t.community_id}
              value={t.id || t.target_id || t.community_id}
            >
              {t.name || t.territory_name || t.id || t.target_id || t.community_id}
            </option>
          ))}
        </select>
      </div>
    );
  }

  function renderVerbForm() {
    if (loadingTargets) return <p className="text-sm text-silver">Loading targets...</p>;
    if (!targetData) return null;

    const props = { targetData, selectedTargetId, setSelectedTargetId, params, setParams, verb };

    switch (verb) {
      case "educate":
        return <EducateForm {...props} />;
      case "aid":
        return <AidForm {...props} />;
      case "attack":
        return <AttackForm {...props} />;
      case "mobilize":
        return <MobilizeForm {...props} />;
      default:
        return <GenericForm {...props} />;
    }
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
          <h2 className="text-xl font-bold tracking-wider text-gold uppercase">Action: {verb}</h2>
          <button
            onClick={() => navigate(`/games/${gameId}`)}
            className="rounded border border-wet-concrete px-4 py-2 text-sm text-silver hover:border-gold"
          >
            ← Back to Briefing
          </button>
        </div>

        <div className="mx-auto mt-8 w-full max-w-xl rounded-lg border border-wet-concrete bg-dark-metal p-6">
          {error && <p className="mb-4 text-crimson">{error}</p>}

          <form onSubmit={handleSubmit} className="flex flex-col gap-6">
            <div>
              <label
                htmlFor="org-select"
                className="mb-2 block text-sm font-semibold tracking-wider text-ash uppercase"
              >
                Select Organization
              </label>
              {loadingOrgs ? (
                <p className="text-sm text-silver">Loading...</p>
              ) : (
                <select
                  id="org-select"
                  value={selectedOrgId}
                  onChange={(e) => setSelectedOrgId(e.target.value)}
                  className="w-full rounded border border-wet-concrete bg-void p-2 text-bone"
                  disabled={submitting}
                >
                  {orgs.map((org) => (
                    <option key={org.id} value={org.id}>
                      {org.name}
                    </option>
                  ))}
                </select>
              )}
            </div>

            {renderVerbForm()}

            <button
              type="submit"
              disabled={submitting || !selectedOrgId || (!selectedTargetId && verb !== "reproduce")}
              className="mt-4 rounded bg-gold py-2 font-bold text-void hover:bg-yellow-600 disabled:opacity-50"
            >
              {submitting ? "Submitting..." : "Submit Action"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
