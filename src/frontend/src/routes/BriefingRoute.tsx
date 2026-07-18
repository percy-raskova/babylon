/**
 * Scenario Briefing — the post-create interstitial (spec-116 FR-116-3).
 *
 * Landed on from the lobby's create flow at `/game/:id/briefing`, BEFORE the
 * cockpit mounts: who you are (the Cadre Council), the stakes, and the five
 * terminal PATTERNS in plain language with the win condition named. Pattern
 * titles/descriptions/progress come verbatim from
 * `GET /api/games/:id/objectives/` (`get_journal_objectives`) — real data,
 * presented as stakes (tick-0 readings are honestly near zero).
 *
 * FIXED-HORIZON FRAMING (owner ruling 2026-07-17): the campaign runs 100
 * in-game years (5,200 weekly ticks). The five outcomes are patterns the
 * world settles into — never terminators — so the copy frames them as
 * "where the century can land", not win/lose conditions that end the game.
 *
 * Deliberately NOT GameRoute: no useHeartbeat/polling/autopause machinery
 * may start until the player clicks Begin Operation (recon gotcha).
 *
 * SKIN: Design Bible §9b "THE INSTALLER" — same plate treatment as
 * LobbyRoute; all colors via the `--ksbc-*` role tokens, no literal hex.
 */

import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router";
import { get as apiGet } from "@/api/client";
import { endpoints } from "@/api/endpoints";
import { useStore } from "@/store";
import type { GameDetailData } from "@/types/game";
import type { ObjectivesTracker } from "@/types/dialectic";

const FIELD = "var(--ksbc-field)";
const CRIMSON = "var(--ksbc-accent-crimson)";
const GOLD = "var(--ksbc-accent-gold)";
const INK = "var(--ksbc-ink)";
const MUTED = "var(--ksbc-muted-1)";
const MUTED_LIGHT = "var(--ksbc-muted-2)";
const SHADOW = "var(--ksbc-key-shadow)";

/** The named win condition among the five recognized patterns. */
const WIN_OBJECTIVE_ID = "revolution";

/** Crimson tab label sitting on a plate's top border (LobbyRoute's plate idiom). */
function PlateLabel({ children }: { children: string }): React.JSX.Element {
  return (
    <span
      className="absolute -top-[11px] left-6 px-2 text-[11px] font-bold uppercase tracking-[0.3em]"
      style={{ background: FIELD, color: CRIMSON }}
    >
      ┤ {children} ├
    </span>
  );
}

export function BriefingRoute(): React.JSX.Element {
  const { id: gameId } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const scenarios = useStore((s) => s.session.scenarios);
  const fetchScenarios = useStore((s) => s.session.fetchScenarios);

  const [detail, setDetail] = useState<GameDetailData | null>(null);
  const [objectives, setObjectives] = useState<ObjectivesTracker | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!gameId) return;
    if (scenarios.length === 0) void fetchScenarios();
    void (async () => {
      const [detailRes, objectivesRes] = await Promise.all([
        apiGet<GameDetailData>(endpoints.gameDetail.path({ id: gameId })),
        apiGet<ObjectivesTracker>(endpoints.objectives.path({ id: gameId })),
      ]);
      if (detailRes.status === "ok") setDetail(detailRes.data);
      else setError(detailRes.message ?? "Failed to load operation");
      if (objectivesRes.status === "ok") setObjectives(objectivesRes.data);
      else setError(objectivesRes.message ?? "Failed to load patterns");
    })();
  }, [gameId, scenarios.length, fetchScenarios]);

  if (!gameId) {
    return <div className="flex h-screen items-center justify-center text-laser">No game id.</div>;
  }

  const scenario = scenarios.find((s) => s.key === detail?.scenario);

  return (
    <div className="flex min-h-screen flex-col font-mono" style={{ background: FIELD }}>
      <div className="mx-auto flex w-full max-w-2xl flex-col gap-8 px-6 py-10">
        {/* Operation plate */}
        <section className="relative border-2 p-6" style={{ borderColor: CRIMSON }}>
          <PlateLabel>Scenario Briefing</PlateLabel>
          <h1
            data-testid="briefing-codename"
            className="mt-2 text-lg font-bold tracking-[3px]"
            style={{ color: GOLD }}
          >
            {detail ? `OPERATION ${detail.codename}` : "OPERATION —"}
          </h1>
          <p className="mt-1 text-[12px] font-bold" style={{ color: INK }}>
            {scenario?.name ?? detail?.scenario ?? ""}
          </p>
          <p className="mt-2 text-[12px] leading-relaxed" style={{ color: MUTED_LIGHT }}>
            {scenario?.description ?? ""}
          </p>
        </section>

        {/* Who you are */}
        <section className="relative border-2 p-6" style={{ borderColor: CRIMSON }}>
          <PlateLabel>Who You Are</PlateLabel>
          <p className="mt-2 text-[12px] leading-relaxed" style={{ color: INK }}>
            You are the Cadre Council — the collective leadership of the organization. You direct
            cadre, funds, and lines of struggle; the world answers with its own motion. The engine
            adjudicates the material consequences; nothing is scripted.
          </p>
        </section>

        {/* The stakes — fixed horizon */}
        <section className="relative border-2 p-6" style={{ borderColor: CRIMSON }}>
          <PlateLabel>The Stakes</PlateLabel>
          <p
            data-testid="briefing-horizon"
            className="mt-2 text-[12px] leading-relaxed"
            style={{ color: INK }}
          >
            The campaign runs 100 years — 5,200 weekly turns. Nothing ends early: as material
            conditions move, the world settles toward one of five recognized patterns. The campaign
            closes at the horizon, or when you choose to accept a pattern once it has locked in.
          </p>
        </section>

        {/* Five patterns, real data */}
        <section className="relative border-2 p-6" style={{ borderColor: CRIMSON }}>
          <PlateLabel>Five Ways the Century Can Land</PlateLabel>
          <div className="mt-2 flex flex-col gap-3">
            {(objectives?.objectives ?? []).map((obj) => (
              <div
                key={obj.id}
                data-testid={`briefing-pattern-${obj.id}`}
                className="border p-3"
                style={{ borderColor: obj.id === WIN_OBJECTIVE_ID ? GOLD : MUTED }}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="text-[12px] font-bold" style={{ color: INK }}>
                    {obj.title}
                  </span>
                  {obj.id === WIN_OBJECTIVE_ID && (
                    <span
                      data-testid="briefing-win-badge"
                      className="px-1.5 text-[10px] font-bold uppercase tracking-[0.15em]"
                      style={{ background: GOLD, color: SHADOW }}
                    >
                      the win condition
                    </span>
                  )}
                </div>
                <p className="mt-1 text-[11px] leading-relaxed" style={{ color: MUTED_LIGHT }}>
                  {obj.description}
                </p>
                <p className="mt-1 font-mono text-[10px]" style={{ color: MUTED_LIGHT }}>
                  current reading: {obj.progress.toFixed(2)}
                </p>
              </div>
            ))}
            {objectives !== null && objectives.objectives.length === 0 && (
              <p className="text-[12px]" style={{ color: MUTED_LIGHT }}>
                No patterns declared this session.
              </p>
            )}
          </div>
        </section>

        {error && (
          <p role="alert" className="m-0 text-[12px]" style={{ color: CRIMSON }}>
            {error}
          </p>
        )}

        <button
          data-testid="briefing-begin"
          onClick={() => navigate(`/game/${gameId}`)}
          className="self-start border-2 px-4 py-2 text-[11px] font-bold uppercase tracking-[0.2em] transition-transform active:translate-x-[2px] active:translate-y-[2px]"
          style={{
            background: CRIMSON,
            color: INK,
            borderColor: SHADOW,
            boxShadow: `3px 3px 0 0 ${SHADOW}`,
          }}
        >
          Begin Operation
        </button>
      </div>
    </div>
  );
}
