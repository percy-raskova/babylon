/**
 * VerbPage — parameterized action composer for all 9 verbs.
 * URL: /games/:id/actions/:verb
 */

import { useState } from "react";
import { useParams, useNavigate } from "react-router";
import { PageHeader } from "@/components/layout/PageHeader";
import { BblPanel, BblBadge, BblLabel, BblData, BblTooltip } from "@/components/bbl";
import { ORGS, VERBS } from "@/fixtures/v2-mock-data";
import { resolveTargets, getVerbParams } from "@/lib/verb-config";
import type { V2VerbKey, V2ResolvedTarget, V2VerbParam } from "@/types/v2-types";

export function VerbPage() {
  const { id: gameId, verb: verbKey } = useParams<{ id: string; verb: string }>();
  const navigate = useNavigate();
  const verb = VERBS.find((v) => v.verb === verbKey);

  // Hooks must be called unconditionally — see react-hooks/rules-of-hooks.
  // Compute defaults defensively so `params` is empty when `verb` is missing.
  const playerOrgs = ORGS.filter((o) => o.player_controlled);
  const params = verb ? getVerbParams(verb.verb as V2VerbKey) : [];
  const [activeOrgId, setActiveOrgId] = useState(playerOrgs[0]?.id ?? "");
  const [filter, setFilter] = useState("all");
  const [selectedId, setSelectedId] = useState("");
  const [paramVals, setParamVals] = useState<Record<string, unknown>>(() =>
    Object.fromEntries(params.map((p) => [p.key, p.default ?? (p.options ? p.options[0] : 0)])),
  );

  if (!verb) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-crimson">
        Unknown verb: {verbKey}
      </div>
    );
  }

  const targets = resolveTargets(verb.target_type);
  const targetTypes = [...new Set(targets.map((t) => t.type))];
  const filtered = filter === "all" ? targets : targets.filter((t) => t.type === filter);
  const selected = targets.find((t) => t.id === selectedId) ?? filtered[0];
  const setParam = (key: string, value: unknown) => setParamVals((v) => ({ ...v, [key]: value }));

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
          <div className="flex flex-col gap-2">
            {playerOrgs.map((o) => (
              <button
                key={o.id}
                onClick={() => setActiveOrgId(o.id)}
                className={`rounded-md border p-2.5 text-left text-bone ${
                  o.id === activeOrgId ? "border-gold bg-gold/10" : "border-soot bg-void"
                }`}
              >
                <div className="text-[12px] font-semibold">{o.short}</div>
                <div className="mt-0.5 text-[9px] text-ash">
                  {o.ooda_phase} · COH {(o.cohesion * 100).toFixed(0)}%
                </div>
              </button>
            ))}
            <div className="mt-3">
              <BblLabel>Other Verbs</BblLabel>
              <div className="mt-1.5 grid grid-cols-3 gap-1">
                {VERBS.map((v) => (
                  <BblTooltip
                    key={v.verb}
                    text={`${v.label} → ${v.target_type.replace(/_/g, " ")}`}
                  >
                    <button
                      onClick={() => navigate(`/games/${gameId}/actions/${v.verb}`)}
                      className={`flex aspect-square items-center justify-center rounded text-sm ${
                        v.verb === verb.verb
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
          </div>
        </BblPanel>

        {/* 2. Target list */}
        <BblPanel
          title={`Eligible Targets (${filtered.length})`}
          right={
            targetTypes.length > 1 ? (
              <div className="flex gap-1">
                <ChipBtn active={filter === "all"} onClick={() => setFilter("all")}>
                  all
                </ChipBtn>
                {targetTypes.map((t) => (
                  <ChipBtn key={t} active={filter === t} onClick={() => setFilter(t)}>
                    {t}
                  </ChipBtn>
                ))}
              </div>
            ) : (
              <BblBadge color="#787878">{verb.target_type.replace(/_/g, " ")}</BblBadge>
            )
          }
        >
          <div className="flex flex-col gap-1.5">
            {filtered.map((t) => (
              <TRow
                key={t.id}
                t={t}
                sel={t.id === selected?.id}
                onClick={() => setSelectedId(t.id)}
              />
            ))}
            {!filtered.length && (
              <div className="py-6 text-center text-[11px] text-ash">No eligible targets.</div>
            )}
          </div>
        </BblPanel>

        {/* 3. Compose */}
        <BblPanel title="Compose Action" accent="#c8a860">
          <div className="flex h-full flex-col gap-3">
            <div className="rounded border border-soot bg-void p-2.5">
              <div className="flex items-baseline justify-between">
                <BblLabel>Selected target</BblLabel>
                {selected && <BblBadge color={selected.color}>{selected.type}</BblBadge>}
              </div>
              <div className="mt-1 text-[13px] font-semibold text-bone">
                {selected?.label ?? "—"}
              </div>
              <div className="mt-0.5 text-[10px] text-ash">{selected?.sub}</div>
            </div>
            {params.map((p) => (
              <ParamControl key={p.key} param={p} value={paramVals[p.key]} onChange={setParam} />
            ))}
            <div className="flex-1" />
            <button className="shrink-0 rounded-md bg-gold px-4 py-3 text-[11px] font-bold uppercase tracking-[0.2em] text-void hover:brightness-110">
              Queue {verb.label} ▸
            </button>
          </div>
        </BblPanel>
      </div>
    </div>
  );
}

interface ParamControlProps {
  param: V2VerbParam;
  value: unknown;
  onChange: (key: string, value: unknown) => void;
}

function ParamControl({ param, value, onChange }: ParamControlProps) {
  return (
    <div>
      <div className="mb-1 flex items-baseline justify-between">
        <BblLabel>{param.label}</BblLabel>
        {param.kind === "slider" && (
          <BblData color="#c8a860" size={11}>
            {String(value)} {param.unit}
          </BblData>
        )}
      </div>
      {param.kind === "radio" && (
        <div className="flex flex-wrap gap-1">
          {param.options?.map((opt) => (
            <RadioOption
              key={opt}
              opt={opt}
              active={value === opt}
              onSelect={() => onChange(param.key, opt)}
            />
          ))}
        </div>
      )}
      {param.kind === "slider" && (
        <input
          type="range"
          min={param.min}
          max={param.max}
          value={Number(value)}
          onChange={(e) => onChange(param.key, Number(e.target.value))}
          className="w-full accent-gold"
        />
      )}
      {param.kind === "toggle" && (
        <button
          onClick={() => onChange(param.key, !value)}
          className={`rounded border px-3 py-1.5 text-[10px] ${
            value ? "border-crimson bg-crimson/15 text-crimson" : "border-wet-concrete text-ash"
          }`}
        >
          {value ? "ENABLED" : "OFF"}
        </button>
      )}
    </div>
  );
}

function RadioOption({
  opt,
  active,
  onSelect,
}: {
  opt: string;
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
      {opt}
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

function TRow({ t, sel, onClick }: { t: V2ResolvedTarget; sel: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={`grid grid-cols-[4px_1fr_auto] items-center gap-3 rounded-md border p-2.5 text-left ${
        sel ? "border-gold bg-gold/8" : "border-soot bg-void"
      }`}
    >
      <div className="h-9 w-1 rounded-full" style={{ background: t.color }} />
      <div>
        <div className="flex items-center gap-1.5">
          <span className="text-[12px] font-semibold text-bone">{t.label}</span>
          <BblBadge color={t.color}>{t.type}</BblBadge>
        </div>
        <div className="mt-0.5 text-[10px] text-ash">{t.sub}</div>
      </div>
      <div className="flex flex-col items-end gap-0.5">
        {Object.entries(t.telemetry).map(([k, v]) => (
          <div key={k} className="flex gap-1 font-mono text-[9px]">
            <span className="text-chassis">{k}</span>
            <span style={{ color: t.color }}>{(v * 100).toFixed(0)}%</span>
          </div>
        ))}
      </div>
    </button>
  );
}
