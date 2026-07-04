/**
 * OrgsPage — player action surface with org roster + 3×3 verb grid.
 *
 * Spec 061 US4 (T072-T074): wired to real engine snapshot. Player-tab
 * filters by ``org.player_controlled``; org detail reads cohesion /
 * OODA phase / vanguard pools from the live snapshot.
 *
 * Layout: left player roster (300px), right org detail + verb grid.
 * Only player-controlled orgs appear here. Enemy orgs are accessed via Intel.
 */

import { useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router";
import { BblBadge, BblData, BblLabel, BblPanel, Gauge, Stat } from "@/components/bbl";
import { PageHeader } from "@/components/layout/PageHeader";
import { useGameState } from "@/hooks/useGameState";
import { useGameStore } from "@/stores/gameStore";
import type { OrgState } from "@/types/game";

/** Spec 061 US4: static color palette for class characters (UI tokens, not data). */
const CLASS_COLORS: Record<string, string> = {
  proletarian: "#40c040",
  bourgeois: "#a070d0",
  petty_bourgeois: "#e0a030",
  lumpen: "#787878",
};

interface OrgRowProps {
  org: OrgState;
  isActive: boolean;
  onSelect: (id: string) => void;
}

function OrgRosterRow({ org: o, isActive, onSelect }: OrgRowProps) {
  const classColor = CLASS_COLORS[o.class_character] ?? "#787878";
  return (
    <button
      onClick={() => onSelect(o.id)}
      className={`rounded-md border p-3 text-left transition-colors ${
        isActive ? "border-gold bg-gold/10" : "border-soot bg-void hover:border-wet-concrete"
      }`}
    >
      <div className="flex items-center gap-2">
        <span className="text-sm font-semibold text-bone">{o.short_name ?? o.name}</span>
        <BblBadge color={classColor}>{o.class_character}</BblBadge>
      </div>
      <div className="mt-1 text-[10px] text-ash">{o.name}</div>
      {o.vanguard && (
        <div className="mt-2 flex gap-3 font-mono text-[9px]">
          <span className="text-royal-blue">{Math.round(o.vanguard.cadre_labor)} CL</span>
          <span className="text-data-green">{Math.round(o.vanguard.sympathizer_labor)} SL</span>
          <span className="text-gold">${Math.round(o.vanguard.budget)}</span>
        </div>
      )}
    </button>
  );
}

/** Spec 061 US5: verb glyph catalog. The full verb taxonomy is wired by US5
 *  (T081 removes unsupported verbs from this list); for now we ship the
 *  canonical 9-verb grid the v1 page used. */
const VERBS: { verb: string; glyph: string; label: string }[] = [
  { verb: "educate", glyph: "📖", label: "Educate" },
  { verb: "reproduce", glyph: "🌱", label: "Recruit" },
  { verb: "mobilize", glyph: "✊", label: "Mobilize" },
  { verb: "campaign", glyph: "📣", label: "Campaign" },
  { verb: "aid", glyph: "🤝", label: "Aid" },
  { verb: "attack", glyph: "💥", label: "Attack" },
];

function subtitleFor(loading: boolean, error: string | null): string {
  if (loading) return "Loading…";
  if (error) return `Error: ${error}`;
  return "Player action surface — select your org, choose a verb";
}

function OrgDetailPanel({ org, oodaPhase }: { org: OrgState; oodaPhase: string }) {
  const vanguard = org.vanguard ?? null;
  return (
    <BblPanel
      title={org.short_name ?? org.name}
      accent="#c8a860"
      right={<BblBadge color="#80b0e0">{oodaPhase}</BblBadge>}
    >
      <div className="flex flex-col gap-4">
        <div className="flex gap-6">
          <Stat label="Cohesion" value={`${(org.cohesion * 100).toFixed(0)}%`} color="#c8a860" />
          <Stat
            label="Legitimacy"
            value={`${((org.legitimacy ?? 0) * 100).toFixed(0)}%`}
            color="#40c040"
          />
          <Stat
            label="Opacity"
            value={`${((org.opacity ?? 0) * 100).toFixed(0)}%`}
            color="#a070d0"
          />
          <Stat label="Heat" value={`${(org.heat * 100).toFixed(0)}%`} color="#e04040" />
        </div>
        {vanguard && (
          <div className="flex gap-4">
            <Gauge
              label="CL"
              value={vanguard.cadre_labor}
              max={vanguard.max_cadre_labor}
              color="#80b0e0"
            />
            <Gauge
              label="SL"
              value={vanguard.sympathizer_labor}
              max={vanguard.max_sympathizer_labor}
              color="#40c040"
            />
            <div className="flex flex-col gap-1">
              <div className="flex items-baseline gap-1">
                <BblLabel>REP</BblLabel>
                <BblData size={10}>{(vanguard.reputation * 100).toFixed(0)}%</BblData>
              </div>
              <div className="flex items-baseline gap-1">
                <BblLabel>Budget</BblLabel>
                <BblData size={10} color="#c8a860">
                  ${Math.round(vanguard.budget)}
                </BblData>
              </div>
            </div>
          </div>
        )}
      </div>
    </BblPanel>
  );
}

function VerbGrid({ gameId }: { gameId: string | undefined }) {
  const navigate = useNavigate();
  return (
    <BblPanel title="Actions" right={<BblLabel>{VERBS.length} verbs</BblLabel>}>
      <div className="grid grid-cols-3 gap-2">
        {VERBS.map((verb) => (
          <button
            key={verb.verb}
            onClick={() => navigate(`/games/${gameId}/actions/${verb.verb}`)}
            className="flex flex-col items-center gap-1 rounded-md border border-soot bg-void p-3 text-ash transition-all hover:border-gold hover:text-gold"
          >
            <span className="text-lg">{verb.glyph}</span>
            <span className="text-[9px] font-semibold uppercase tracking-wider">{verb.label}</span>
          </button>
        ))}
      </div>
    </BblPanel>
  );
}

function CommunitiesPanel({ memberships }: { memberships: string[] }) {
  return (
    <BblPanel title="Communities" right={<BblBadge color="#787878">{memberships.length}</BblBadge>}>
      <div className="flex flex-col gap-2">
        {memberships.length === 0 && (
          <div className="rounded border border-dashed border-chassis p-2 text-center text-[10px] text-ash">
            Community memberships not yet wired (spec 061 US6).
          </div>
        )}
        {memberships.map((hid) => (
          <div key={hid} className="rounded border border-soot bg-void p-2">
            <div className="text-[11px] font-semibold text-bone">{hid}</div>
          </div>
        ))}
      </div>
    </BblPanel>
  );
}

export function OrgsPage() {
  const navigate = useNavigate();
  const { id: gameId } = useParams<{ id: string }>();
  const { snapshot, loading, error, resolveTick } = useGameState(gameId ?? null);
  const [resolving, setResolving] = useState(false);

  const playerOrgs: OrgState[] = useMemo(
    () => (snapshot?.organizations ?? []).filter((o) => Boolean(o.player_controlled)),
    [snapshot],
  );
  const [activeOrgId, setActiveOrgId] = useState<string>("");
  const currentActive =
    activeOrgId && playerOrgs.some((o) => o.id === activeOrgId) ? activeOrgId : playerOrgs[0]?.id;
  const org = playerOrgs.find((o) => o.id === currentActive) ?? playerOrgs[0];
  const oodaPhase = org?.ooda?.phase ?? "observe";
  const subtitle = subtitleFor(loading, error);

  // Spec 092: End Turn resolves the tick, then hands off to the Tick
  // Resolution screen for the animated summary of what just happened.
  //
  // Spec-092 review fix (Defect C): `resolveTick()` never throws — on
  // failure it sets `error` in the gameStore and resolves to `null`
  // (see `gameStore.ts`'s `resolveTick`). Navigating unconditionally
  // therefore sent the player to the resolution screen even when the
  // tick never actually resolved. Read the store's fresh `error` state
  // right after the await (imperative `getState()`, not the reactive
  // hook selector, since this closure isn't itself re-rendered) and only
  // navigate when it's still clear; the existing `error` subtitle
  // (`subtitleFor` below) already surfaces the failure to the player.
  const handleEndTurn = async () => {
    setResolving(true);
    try {
      await resolveTick();
      if (!useGameStore.getState().error) {
        navigate(`/games/${gameId}/resolution`);
      }
    } finally {
      setResolving(false);
    }
  };

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <PageHeader
        title="Organizations"
        subtitle={subtitle}
        breadcrumbs={["Operation", "Organizations"]}
        right={
          <div className="flex items-center gap-2">
            <BblBadge color="#40c040">{playerOrgs.length} allied orgs</BblBadge>
            <button
              onClick={() => void handleEndTurn()}
              disabled={resolving}
              className="rounded-md bg-gold px-3 py-1.5 text-[11px] font-bold uppercase tracking-[0.15em] text-void transition-all hover:brightness-110 disabled:opacity-50"
            >
              {resolving ? "Resolving…" : "End Turn ▸"}
            </button>
          </div>
        }
      />

      <div className="grid min-h-0 flex-1 grid-cols-[280px_1fr] gap-3 p-3">
        <BblPanel title="Your Orgs" right={<BblLabel>select</BblLabel>}>
          <div className="flex flex-col gap-2">
            {playerOrgs.length === 0 && (
              <div className="rounded border border-dashed border-chassis p-3 text-center text-[10px] text-ash">
                No player orgs in this session.
              </div>
            )}
            {playerOrgs.map((o) => (
              <OrgRosterRow
                key={o.id}
                org={o}
                isActive={o.id === currentActive}
                onSelect={setActiveOrgId}
              />
            ))}
            <div className="mt-2 rounded border border-dashed border-chassis p-2 text-center text-[10px] text-ash">
              Enemy orgs visible in <span className="text-gold">Intel</span> →
            </div>
          </div>
        </BblPanel>

        <div className="flex min-h-0 flex-col gap-3">
          {org && <OrgDetailPanel org={org} oodaPhase={oodaPhase} />}
          <div className="grid min-h-0 flex-1 grid-cols-[1fr_1fr] gap-3">
            <VerbGrid gameId={gameId} />
            <CommunitiesPanel memberships={org?.hyperedge_memberships ?? []} />
          </div>
        </div>
      </div>
    </div>
  );
}
