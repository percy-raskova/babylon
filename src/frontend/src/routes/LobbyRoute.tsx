/**
 * Lobby route — real `/api/games/` + `/api/scenarios/` list, minimal
 * create-game form. Mirrors the legacy `GameList`'s data flow through the
 * session slice instead of a local `useEffect` fetch.
 *
 * SKIN: Design Bible §9b "THE INSTALLER" — a menu screen (map absent),
 * full Guix-installer treatment: flat dead field, one centered plate per
 * logical group, hard offset shadow, crimson title tabs, and the
 * scenario/session lists render as GOLD INVERSE-VIDEO selection bars with
 * arrow-key + Enter navigation (falls back to click, which always works).
 *
 * Colors reference the `--ksbc-*` role tokens from `index.css` (Lane
 * SKIN-CHROME) — single source of truth for the palette; this file
 * holds no literal hex.
 */

import { useEffect, useState, type KeyboardEvent } from "react";
import { useNavigate } from "react-router";
import { useStore } from "@/store";
import { DIFFICULTY_PRESETS, rollRngSeed } from "@/lib/difficulty";

const FIELD = "var(--ksbc-field)";
const CRIMSON = "var(--ksbc-accent-crimson)";
const GOLD = "var(--ksbc-accent-gold)";
const INK = "var(--ksbc-ink)";
const MUTED = "var(--ksbc-muted-1)";
const MUTED_LIGHT = "var(--ksbc-muted-2)";
const SHADOW = "var(--ksbc-key-shadow)";

/** One row in a Guix-style listbox. */
interface SelectionItem {
  key: string;
  label: string;
  sublabel?: string;
  /** Right-aligned extra content (per-row actions); its buttons must stopPropagation. */
  trailing?: React.JSX.Element;
  /** Render at reduced opacity (archived operations). */
  dimmed?: boolean;
}

/**
 * Full-width gold-inverse-video selection listbox (Design Bible §9b).
 * `activeKey` drives the highlighted row; ArrowUp/ArrowDown move it,
 * Enter activates it; clicking a row both selects and activates it
 * (matches the pre-reskin `<select>`/button click semantics exactly).
 */
function SelectionList({
  items,
  activeKey,
  onSelect,
  onActivate,
  testIdPrefix,
  emptyText,
}: {
  items: SelectionItem[];
  activeKey: string;
  onSelect: (key: string) => void;
  onActivate: (key: string) => void;
  testIdPrefix: string;
  emptyText: string;
}): React.JSX.Element {
  function handleKeyDown(e: KeyboardEvent<HTMLDivElement>): void {
    if (items.length === 0) return;
    const idx = items.findIndex((i) => i.key === activeKey);
    if (e.key === "ArrowDown") {
      e.preventDefault();
      const next = items[(idx + 1) % items.length];
      if (next) onSelect(next.key);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      const prev = items[(idx - 1 + items.length) % items.length];
      if (prev) onSelect(prev.key);
    } else if (e.key === "Enter" && activeKey) {
      e.preventDefault();
      onActivate(activeKey);
    }
  }

  if (items.length === 0) {
    return (
      <p className="px-3 py-6 text-center text-[12px]" style={{ color: MUTED_LIGHT }}>
        {emptyText}
      </p>
    );
  }

  return (
    <div
      role="listbox"
      tabIndex={0}
      onKeyDown={handleKeyDown}
      className="flex flex-col outline-none"
      style={{ border: `3px double ${CRIMSON}` }}
    >
      {items.map((item) => {
        const active = item.key === activeKey;
        return (
          <div
            key={item.key}
            role="option"
            aria-selected={active}
            data-testid={`${testIdPrefix}-${item.key}`}
            onClick={() => {
              onSelect(item.key);
              onActivate(item.key);
            }}
            className="flex w-full cursor-pointer items-center justify-between px-3 py-2 text-[13px]"
            style={{
              background: active ? GOLD : FIELD,
              color: active ? SHADOW : INK,
              opacity: item.dimmed ? 0.55 : 1,
            }}
          >
            <span className="font-semibold">{item.label}</span>
            <span className="flex items-center gap-3">
              {item.sublabel && (
                <span className="font-mono text-[11px]" style={{ opacity: active ? 0.85 : 0.7 }}>
                  {item.sublabel}
                </span>
              )}
              {item.trailing}
            </span>
          </div>
        );
      })}
    </div>
  );
}

export function LobbyRoute(): React.JSX.Element {
  const auth = useStore((s) => s.session.auth);
  const games = useStore((s) => s.session.games);
  const gamesLoading = useStore((s) => s.session.gamesLoading);
  const scenarios = useStore((s) => s.session.scenarios);
  const error = useStore((s) => s.session.error);
  const fetchGames = useStore((s) => s.session.fetchGames);
  const fetchScenarios = useStore((s) => s.session.fetchScenarios);
  const createGame = useStore((s) => s.session.createGame);
  const deleteGame = useStore((s) => s.session.deleteGame);
  const archiveGame = useStore((s) => s.session.archiveGame);
  const logout = useStore((s) => s.session.logout);
  const navigate = useNavigate();

  // "" means "no explicit user pick yet" — the effective selection falls
  // back to the first fetched scenario (computed below during render, not
  // synced via an effect: there is nothing to derive once fetched data
  // arrives that render can't compute directly).
  const [selectedScenario, setSelectedScenario] = useState("");
  const [creating, setCreating] = useState(false);
  const effectiveScenario = selectedScenario || (scenarios[0]?.key ?? "");

  // Curated difficulty (spec-116 FR-116-3): vetted preset keys only,
  // never raw defines. "cadre" = schema defaults.
  const [selectedDifficulty, setSelectedDifficulty] = useState("cadre");

  // Arm-to-confirm for the permanent delete: first click arms, second fires.
  const [pendingDeleteId, setPendingDeleteId] = useState("");

  // Human scenario names live in the catalog; rows fall back to the raw key.
  const scenarioNames = new Map(scenarios.map((s) => [s.key, s.name]));

  // Same "no explicit pick yet" pattern for the games listbox's keyboard
  // highlight — arrow keys move it, click/Enter navigate.
  const [focusedGameId, setFocusedGameId] = useState("");
  const effectiveGameId = focusedGameId || (games[0]?.id ?? "");

  useEffect(() => {
    fetchGames();
    fetchScenarios();
  }, [fetchGames, fetchScenarios]);

  async function handleCreate(): Promise<void> {
    if (!effectiveScenario) return;
    const preset = DIFFICULTY_PRESETS.find((p) => p.key === selectedDifficulty);
    setCreating(true);
    const id = await createGame({
      scenario: effectiveScenario,
      defines: preset?.defines ?? {},
      rng_seed: rollRngSeed(),
    });
    setCreating(false);
    if (id) navigate(`/game/${id}`);
  }

  function handleDeleteClick(id: string): void {
    if (pendingDeleteId === id) {
      setPendingDeleteId("");
      void deleteGame(id);
    } else {
      setPendingDeleteId(id);
    }
  }

  async function handleLogout(): Promise<void> {
    await logout();
    navigate("/login");
  }

  return (
    <div className="flex min-h-screen flex-col font-mono" style={{ background: FIELD }}>
      <header
        className="flex items-center justify-between border-b-2 px-6 py-3"
        style={{ borderColor: CRIMSON }}
      >
        <span className="text-sm font-bold tracking-[4px]" style={{ color: INK }}>
          BABYLON
        </span>
        <div className="flex items-center gap-4">
          <span className="text-sm" style={{ color: MUTED_LIGHT }}>
            {auth?.username}
          </span>
          <button
            onClick={() => void handleLogout()}
            className="border-2 px-3 py-1.5 text-[12px] font-bold uppercase tracking-[0.15em] transition-transform active:translate-x-[1px] active:translate-y-[1px]"
            style={{
              background: FIELD,
              color: INK,
              borderColor: MUTED,
              boxShadow: `2px 2px 0 0 ${SHADOW}`,
            }}
          >
            Logout
          </button>
        </div>
      </header>

      <div className="mx-auto flex w-full max-w-2xl flex-col gap-8 px-6 py-10">
        {/* New Operation plate */}
        <section className="relative border-2 p-6" style={{ borderColor: CRIMSON }}>
          <span
            className="absolute -top-[11px] left-6 px-2 text-[11px] font-bold uppercase tracking-[0.3em]"
            style={{ background: FIELD, color: CRIMSON }}
          >
            ┤ New Operation ├
          </span>
          <div className="mt-2 flex flex-col gap-4">
            <SelectionList
              items={scenarios.map((s) => ({ key: s.key, label: s.name }))}
              activeKey={effectiveScenario}
              onSelect={setSelectedScenario}
              onActivate={setSelectedScenario}
              testIdPrefix="scenario-option"
              emptyText="No scenarios available."
            />
            <div>
              <p
                className="mb-1 text-[10px] uppercase tracking-[0.2em]"
                style={{ color: MUTED_LIGHT }}
              >
                Difficulty
              </p>
              <SelectionList
                items={DIFFICULTY_PRESETS.map((p) => ({
                  key: p.key,
                  label: p.label,
                  sublabel: p.description,
                }))}
                activeKey={selectedDifficulty}
                onSelect={setSelectedDifficulty}
                onActivate={setSelectedDifficulty}
                testIdPrefix="difficulty-option"
                emptyText="No presets."
              />
            </div>
            <button
              onClick={() => void handleCreate()}
              disabled={creating || !effectiveScenario}
              className="self-start border-2 px-4 py-2 text-[11px] font-bold uppercase tracking-[0.2em] transition-transform active:translate-x-[2px] active:translate-y-[2px] disabled:opacity-50"
              style={{
                background: CRIMSON,
                color: INK,
                borderColor: SHADOW,
                boxShadow: `3px 3px 0 0 ${SHADOW}`,
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = GOLD;
                e.currentTarget.style.color = SHADOW;
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = CRIMSON;
                e.currentTarget.style.color = INK;
              }}
            >
              {creating ? "Creating…" : "+ New Game"}
            </button>
          </div>
        </section>

        {error && (
          <p role="alert" className="m-0 text-[12px]" style={{ color: CRIMSON }}>
            {error}
          </p>
        )}

        {/* Your Games plate */}
        <section className="relative border-2 p-6" style={{ borderColor: CRIMSON }}>
          <span
            className="absolute -top-[11px] left-6 px-2 text-[11px] font-bold uppercase tracking-[0.3em]"
            style={{ background: FIELD, color: CRIMSON }}
          >
            ┤ Your Games ({games.length}) ├
          </span>
          <div className="mt-2">
            {gamesLoading && (
              <p className="text-[12px]" style={{ color: MUTED_LIGHT }}>
                Reading operation logs…
              </p>
            )}
            {!gamesLoading && (
              <SelectionList
                items={games.map((g) => ({
                  key: g.id,
                  label: g.codename,
                  sublabel: `${scenarioNames.get(g.scenario) ?? g.scenario} · Tick ${g.current_tick} · ${g.status.toUpperCase()} · ${g.created_at.slice(0, 10)}`,
                  dimmed: g.status === "abandoned",
                  trailing: (
                    <span className="flex items-center gap-2">
                      {g.status !== "abandoned" && (
                        <button
                          data-testid={`game-archive-${g.id}`}
                          title="Archive operation (reversible)"
                          onClick={(e) => {
                            e.stopPropagation();
                            void archiveGame(g.id);
                          }}
                          className="border px-1.5 text-[10px] uppercase tracking-[0.1em]"
                          style={{
                            borderColor: MUTED,
                            color: MUTED_LIGHT,
                            background: "transparent",
                          }}
                        >
                          archive
                        </button>
                      )}
                      <button
                        data-testid={`game-delete-${g.id}`}
                        title="Delete operation (permanent)"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDeleteClick(g.id);
                        }}
                        className="border px-1.5 text-[10px] font-bold uppercase tracking-[0.1em]"
                        style={{
                          borderColor: CRIMSON,
                          color: pendingDeleteId === g.id ? SHADOW : CRIMSON,
                          background: pendingDeleteId === g.id ? CRIMSON : "transparent",
                        }}
                      >
                        {pendingDeleteId === g.id ? "confirm" : "×"}
                      </button>
                    </span>
                  ),
                }))}
                activeKey={effectiveGameId}
                onSelect={setFocusedGameId}
                onActivate={(id) => navigate(`/game/${id}`)}
                testIdPrefix="game-option"
                emptyText="No operations on record — start one above."
              />
            )}
          </div>
        </section>
      </div>

      <p
        className="mx-auto mb-6 mt-auto px-6 text-center text-[9px] uppercase tracking-[0.2em]"
        style={{ color: MUTED_LIGHT }}
      >
        ↑↓ — select · Enter — open · Click — open
      </p>
    </div>
  );
}
