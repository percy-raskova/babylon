/**
 * VerbPage — parameterized action composer for all 9 verbs.
 * URL: /games/:id/actions/:verb
 *
 * Targets come from the live per-verb GET endpoints via
 * gameStore.fetchVerbTargets (or the snapshot for campaign, whose
 * targets route 405s), parsed by the VERB_REGISTRY configs; submissions
 * are built by each config's buildPayload so the POST body matches the
 * backend serializer contract exactly (P0 #4 + 5th P0).
 */

import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router";
import { BblBadge, BblData, BblLabel, BblPanel, BblTooltip } from "@/components/bbl";
import { PageHeader } from "@/components/layout/PageHeader";
import { useGameState } from "@/hooks/useGameState";
import { DISABLED_VERBS, SUPPORTED_VERBS } from "@/lib/verb-config";
import { VERB_REGISTRY } from "@/lib/verbs";
import type { ParamField, VerbConfig, VerbTarget } from "@/lib/verbs";
import { useGameStore } from "@/stores/gameStore";
import type { GameSnapshot } from "@/types/game";
import type { V2Verb } from "@/types/v2-types";

/** Neutral chip color — live VerbTargets carry no class-color telemetry. */
const TARGET_CHIP_COLOR = "#787878";

interface ActorPanelProps {
  playerOrgs: {
    id: string;
    name: string;
    short_name?: string;
    cohesion: number;
    ooda?: { phase?: string };
  }[];
  activeOrgId: string;
  onSelect: (id: string) => void;
}

function ActorPanel({ playerOrgs, activeOrgId, onSelect }: ActorPanelProps) {
  return (
    <div className="flex flex-col gap-2">
      {playerOrgs.length === 0 && (
        <div className="rounded border border-dashed border-chassis p-3 text-center text-[10px] text-ash">
          No player orgs in this session.
        </div>
      )}
      {playerOrgs.map((o) => (
        <button
          key={o.id}
          onClick={() => onSelect(o.id)}
          className={`rounded-md border p-2.5 text-left text-bone ${
            o.id === activeOrgId ? "border-gold bg-gold/10" : "border-soot bg-void"
          }`}
        >
          <div className="text-[12px] font-semibold">{o.short_name ?? o.name}</div>
          <div className="mt-0.5 text-[9px] text-ash">
            {o.ooda?.phase ?? "observe"} · COH {(o.cohesion * 100).toFixed(0)}%
          </div>
        </button>
      ))}
    </div>
  );
}

function VerbPicker({ currentVerb, gameId }: { currentVerb: string; gameId: string | undefined }) {
  const navigate = useNavigate();
  return (
    <div className="mt-3">
      <BblLabel>Other Verbs</BblLabel>
      <div className="mt-1.5 grid grid-cols-3 gap-1">
        {SUPPORTED_VERBS.map((v) => (
          <BblTooltip key={v.verb} text={`${v.label} → ${v.target_type.replace(/_/g, " ")}`}>
            <button
              onClick={() => navigate(`/games/${gameId}/actions/${v.verb}`)}
              className={`flex aspect-square items-center justify-center rounded text-sm ${
                v.verb === currentVerb
                  ? "border border-gold bg-gold/15 text-gold"
                  : "border border-soot text-ash hover:text-bone"
              }`}
            >
              {v.glyph}
            </button>
          </BblTooltip>
        ))}
      </div>
    </div>
  );
}

interface TargetListProps {
  targets: VerbTarget[];
  groups: string[];
  verbTargetType: string;
  filter: string;
  selectedId: string;
  emptyMessage: string;
  onFilter: (filter: string) => void;
  onSelect: (id: string) => void;
}

function TargetListPanel({
  targets,
  groups,
  verbTargetType,
  filter,
  selectedId,
  emptyMessage,
  onFilter,
  onSelect,
}: TargetListProps) {
  const filtered = filter === "all" ? targets : targets.filter((t) => t.group === filter);
  return (
    <BblPanel
      title={`Eligible Targets (${filtered.length})`}
      right={
        groups.length > 1 ? (
          <div className="flex gap-1">
            <ChipBtn active={filter === "all"} onClick={() => onFilter("all")}>
              all
            </ChipBtn>
            {groups.map((g) => (
              <ChipBtn key={g} active={filter === g} onClick={() => onFilter(g)}>
                {g}
              </ChipBtn>
            ))}
          </div>
        ) : (
          <BblBadge color={TARGET_CHIP_COLOR}>{verbTargetType.replace(/_/g, " ")}</BblBadge>
        )
      }
    >
      <div className="flex flex-col gap-1.5">
        {filtered.map((t) => (
          <TRow
            key={t.id}
            t={t}
            fallbackGroup={verbTargetType.replace(/_/g, " ")}
            sel={t.id === selectedId}
            onClick={() => onSelect(t.id)}
          />
        ))}
        {filtered.length === 0 && (
          <div className="py-6 text-center text-[11px] text-ash">{emptyMessage}</div>
        )}
      </div>
    </BblPanel>
  );
}

interface ComposePanelProps {
  verbLabel: string;
  selected: VerbTarget | undefined;
  params: ParamField[];
  paramVals: Record<string, unknown>;
  onParamChange: (key: string, value: unknown) => void;
  submitting: boolean;
  canSubmit: boolean;
  onSubmit: () => void;
}

function ComposePanel({
  verbLabel,
  selected,
  params,
  paramVals,
  onParamChange,
  submitting,
  canSubmit,
  onSubmit,
}: ComposePanelProps) {
  return (
    <BblPanel title="Compose Action" accent="#c8a860">
      <div className="flex h-full flex-col gap-3">
        <div className="rounded border border-soot bg-void p-2.5">
          <div className="flex items-baseline justify-between">
            <BblLabel>Selected target</BblLabel>
            {selected?.group && <BblBadge color={TARGET_CHIP_COLOR}>{selected.group}</BblBadge>}
          </div>
          <div className="mt-1 text-[13px] font-semibold text-bone">{selected?.label ?? "—"}</div>
        </div>
        {params.map((p) => (
          <ParamControl key={p.key} param={p} value={paramVals[p.key]} onChange={onParamChange} />
        ))}
        <div className="flex-1" />
        <button
          onClick={onSubmit}
          disabled={submitting || !canSubmit}
          className="shrink-0 rounded-md bg-gold px-4 py-3 text-[11px] font-bold uppercase tracking-[0.2em] text-void hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {submitting ? "Submitting…" : `Queue ${verbLabel} ▸`}
        </button>
      </div>
    </BblPanel>
  );
}

/** Initial param values from a verb config's ParamField defaults. */
function defaultParamVals(fields: ParamField[]): Record<string, unknown> {
  return Object.fromEntries(fields.map((p) => [p.key, p.defaultValue]));
}

/**
 * Live eligible targets for a verb (5th P0 fix).
 *
 * Endpoint-sourced verbs fetch via gameStore.fetchVerbTargets, cached by
 * `verb:org`. Cache hits skip the GET; resolveTick() invalidates the
 * cache each tick, which re-triggers the fetch. Snapshot-sourced verbs
 * (campaign — its targets route 405s) read territories + hyperedges from
 * the snapshot instead.
 */
function useVerbTargets(
  gameId: string | undefined,
  verb: V2Verb,
  config: VerbConfig,
  orgId: string,
  snapshot: GameSnapshot | null,
): VerbTarget[] {
  const fetchVerbTargets = useGameStore((s) => s.fetchVerbTargets);
  const verbTargets = useGameStore((s) => s.verbTargets);
  const cacheKey = `${verb.verb}:${orgId}`;

  useEffect(() => {
    if (!gameId || !orgId) return;
    if ((config.targetsSource ?? "endpoint") !== "endpoint") return;
    if (verbTargets[cacheKey]) return;
    void fetchVerbTargets(gameId, verb.verb, orgId);
  }, [gameId, verb, config, orgId, cacheKey, verbTargets, fetchVerbTargets]);

  return useMemo(() => {
    if (config.targetsSource === "snapshot") {
      return [
        ...(snapshot?.territories ?? []).map((t) => ({
          id: t.id,
          label: t.name,
          group: "Territories",
        })),
        ...(snapshot?.hyperedges ?? []).map((h) => ({
          id: h.id,
          label: h.label,
          group: "Communities",
        })),
      ];
    }
    const raw = verbTargets[cacheKey];
    return raw ? config.parseTargets(raw) : [];
  }, [config, snapshot, verbTargets, cacheKey]);
}

export function VerbPage() {
  const { id: gameId, verb: verbKey } = useParams<{ id: string; verb: string }>();
  const verb = SUPPORTED_VERBS.find((v) => v.verb === verbKey);
  const config = verb ? VERB_REGISTRY[verb.verb] : undefined;

  // Spec 061 T081/FR-025: unknown OR disabled verb → reject at the UI boundary.
  if (!verb || !config) {
    const disabled = verbKey && DISABLED_VERBS.has(verbKey);
    return (
      <div className="flex h-full items-center justify-center text-sm text-crimson">
        {disabled
          ? `Verb '${verbKey}' is not yet supported (spec 061 FR-025). A follow-up spec will add the real handler.`
          : `Unknown verb: ${verbKey}`}
      </div>
    );
  }

  // key remounts the composer per verb, resetting filter/selection/params.
  return <VerbComposer key={verb.verb} gameId={gameId} verb={verb} config={config} />;
}

interface VerbComposerProps {
  gameId: string | undefined;
  verb: V2Verb;
  config: VerbConfig;
}

function VerbComposer({ gameId, verb, config }: VerbComposerProps) {
  const { snapshot } = useGameState(gameId ?? null);
  const submitAction = useGameStore((s) => s.submitAction);
  const storeError = useGameStore((s) => s.error);

  // Spec 061 US5 (T082): actor list comes from the live snapshot, not fixtures.
  const playerOrgs = useMemo(
    () => (snapshot?.organizations ?? []).filter((o) => Boolean(o.player_controlled)),
    [snapshot],
  );
  const params: ParamField[] = config.paramFields;
  const [activeOrgId, setActiveOrgId] = useState("");
  const activeOrgFallback =
    activeOrgId && playerOrgs.some((o) => o.id === activeOrgId)
      ? activeOrgId
      : (playerOrgs[0]?.id ?? "");
  const [filter, setFilter] = useState("all");
  const [selectedId, setSelectedId] = useState("");
  const [paramVals, setParamVals] = useState<Record<string, unknown>>(() =>
    defaultParamVals(params),
  );
  const [submitting, setSubmitting] = useState(false);

  const targets = useVerbTargets(gameId, verb, config, activeOrgFallback, snapshot);

  const groups = [...new Set(targets.map((t) => t.group).filter((g): g is string => Boolean(g)))];
  const filtered = filter === "all" ? targets : targets.filter((t) => t.group === filter);
  const selected = targets.find((t) => t.id === selectedId) ?? filtered[0];
  const targetRequired = config.targetRequired ?? true;
  const setParam = (key: string, value: unknown) => setParamVals((v) => ({ ...v, [key]: value }));

  async function handleSubmit(): Promise<void> {
    if (!gameId || !activeOrgFallback) return;
    if (targetRequired && !selected) return;
    setSubmitting(true);
    try {
      await submitAction(gameId, {
        verb: verb.verb,
        ...config.buildPayload(activeOrgFallback, selected?.id ?? null, paramVals),
      });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <PageHeader
        title={`Action · ${verb.label}`}
        subtitle={verb.desc}
        breadcrumbs={["Operation", "Actions", verb.label]}
        right={
          <div className="flex items-center gap-2">
            <BblBadge color="#c8a860">target type · {verb.target_type.replace(/_/g, " ")}</BblBadge>
            <BblBadge color="#80b0e0">cost · {verb.cost_label}</BblBadge>
          </div>
        }
      />

      <div className="grid min-h-0 flex-1 grid-cols-[240px_1fr_320px] gap-3 p-3">
        {/* 1. Actor selection */}
        <BblPanel title="Acting Org" right={<BblLabel>required</BblLabel>}>
          <ActorPanel
            playerOrgs={playerOrgs}
            activeOrgId={activeOrgFallback}
            onSelect={setActiveOrgId}
          />
          <VerbPicker currentVerb={verb.verb} gameId={gameId} />
        </BblPanel>

        {/* 2. Target list */}
        <TargetListPanel
          targets={targets}
          groups={groups}
          verbTargetType={verb.target_type}
          filter={filter}
          selectedId={selected?.id ?? ""}
          emptyMessage={targets.length === 0 && storeError ? storeError : "No eligible targets."}
          onFilter={setFilter}
          onSelect={setSelectedId}
        />

        {/* 3. Compose */}
        <ComposePanel
          verbLabel={verb.label}
          selected={selected}
          params={params}
          paramVals={paramVals}
          onParamChange={setParam}
          submitting={submitting}
          canSubmit={Boolean(activeOrgFallback && (selected || !targetRequired))}
          onSubmit={() => void handleSubmit()}
        />
      </div>
    </div>
  );
}

interface ParamControlProps {
  param: ParamField;
  value: unknown;
  onChange: (key: string, value: unknown) => void;
}

function ParamControl({ param, value, onChange }: ParamControlProps) {
  return (
    <div>
      <div className="mb-1 flex items-baseline justify-between">
        <BblLabel>{param.label}</BblLabel>
        {param.type === "number" && (
          <BblData color="#c8a860" size={11}>
            {String(value)}
          </BblData>
        )}
      </div>
      {param.type === "select" && (
        <div className="flex flex-wrap gap-1">
          {param.options?.map((opt) => (
            // Display label, submit enum value — labels never enter payloads.
            <RadioOption
              key={opt.value}
              label={opt.label}
              active={value === opt.value}
              onSelect={() => onChange(param.key, opt.value)}
            />
          ))}
        </div>
      )}
      {param.type === "number" && (
        <input
          type="range"
          min={param.min}
          max={param.max}
          value={Number(value)}
          onChange={(e) => onChange(param.key, Number(e.target.value))}
          className="w-full accent-gold"
        />
      )}
      {param.type === "text" && (
        <input
          type="text"
          value={String(value ?? "")}
          onChange={(e) => onChange(param.key, e.target.value)}
          className="w-full rounded border border-wet-concrete bg-void px-2.5 py-1.5 text-[11px] text-bone"
        />
      )}
    </div>
  );
}

function RadioOption({
  label,
  active,
  onSelect,
}: {
  label: string;
  active: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      onClick={onSelect}
      className={`rounded border px-2.5 py-1.5 text-[10px] ${
        active ? "border-gold bg-gold/15 text-gold" : "border-wet-concrete text-ash"
      }`}
    >
      {label}
    </button>
  );
}

function ChipBtn({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={`rounded border px-2 py-0.5 text-[9px] uppercase tracking-[0.15em] ${
        active ? "border-gold bg-gold/15 text-gold" : "border-wet-concrete text-ash"
      }`}
    >
      {children}
    </button>
  );
}

function TRow({
  t,
  fallbackGroup,
  sel,
  onClick,
}: {
  t: VerbTarget;
  fallbackGroup: string;
  sel: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-1.5 rounded-md border p-2.5 text-left ${
        sel ? "border-gold bg-gold/8" : "border-soot bg-void"
      }`}
    >
      <span className="text-[12px] font-semibold text-bone">{t.label}</span>
      <BblBadge color={TARGET_CHIP_COLOR}>{t.group ?? fallbackGroup}</BblBadge>
    </button>
  );
}
