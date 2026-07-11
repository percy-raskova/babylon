/**
 * TakeoverOverlay — the full-screen overlay host for the Wire, Chronicle,
 * and Dialectic takeovers (spec-110 B5, program 12 owner ruling 2: "Wire,
 * Chronicle/EndState, Dialectic stay full-screen takeovers").
 *
 * Renders OVER the persistent shell — the map stays mounted underneath
 * (`AppShell` never unmounts it); this is an absolutely-positioned overlay,
 * not a route change. `ui.takeover.active` drives which family renders;
 * `null` renders nothing. Escape closes; so does the floating close button.
 * Each family owns its own fetch (via its adapted hook mounting/unmounting
 * its panel), so only the open takeover's panel is tick-fanned-out.
 *
 * SKIN (Design Bible §9b "THE INSTALLER"): takeovers are literally menus —
 * the map is absent underneath them — so the OUTER frame gets the full
 * Guix dead-field + plate treatment: the backdrop moves to the ksbc field
 * tone, and a plate (hard zero-blur offset shadow, square corners, crimson
 * title tab breaking the top border) wraps whichever family is active.
 * This is framing only — Wire/Chronicle/Dialectic's OWN internal
 * content/CSS identity (WireWindow, chronicle.css, dialectic.css) is
 * ratified canon and untouched; their own scanline/vignette textures stay
 * exactly where they were, confined inside the plate per the juice-pass
 * performance budget.
 *
 * Colors reference the `--ksbc-*` role tokens from `index.css` (Lane
 * SKIN-CHROME) — single source of truth for the palette.
 */

import { useEffect } from "react";
import { useStore } from "@/store";
import { WireTakeover } from "./wire/WireTakeover";
import { ChronicleTakeover } from "./chronicle/ChronicleTakeover";
import { DialecticTakeover } from "./dialectic/DialecticTakeover";
import type { TakeoverKind } from "@/store/slices/uiSlice";

interface Props {
  gameId: string;
}

const FIELD = "var(--ksbc-field)";
const CRIMSON = "var(--ksbc-accent-crimson)";
const SHADOW = "var(--ksbc-key-shadow)";

/** Title-tab labels — deliberately distinct from each family's own internal
 * title text (e.g. WireWindow already renders "THE WIRE") so this frame
 * never collides with a family's own DOM text in tests or the accessibility
 * tree. */
const TAKEOVER_LABEL: Record<TakeoverKind, string> = {
  wire: "Wire Dispatch",
  chronicle: "Chronicle",
  dialectic: "Dialectic",
};

export function TakeoverOverlay({ gameId }: Props): React.JSX.Element | null {
  const active = useStore((s) => s.ui.takeover.active);
  const closeTakeover = useStore((s) => s.ui.closeTakeover);

  useEffect(() => {
    if (!active) return;
    function onKeyDown(event: KeyboardEvent): void {
      if (event.key === "Escape") closeTakeover();
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [active, closeTakeover]);

  if (!active) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6"
      style={{ background: FIELD }}
      data-testid="takeover-overlay"
      data-takeover={active}
      role="dialog"
      aria-modal="true"
      aria-label={`${active} takeover`}
    >
      <div
        className="relative flex h-full w-full flex-col border-2"
        style={{ background: FIELD, borderColor: CRIMSON, boxShadow: `10px 10px 0 0 ${SHADOW}` }}
      >
        <span
          className="absolute -top-[11px] left-6 z-10 px-2 text-[11px] font-bold uppercase tracking-[0.3em]"
          style={{ background: FIELD, color: CRIMSON }}
        >
          ┤ {TAKEOVER_LABEL[active]} ├
        </span>

        <button
          onClick={closeTakeover}
          aria-label="Close takeover"
          data-testid="takeover-close"
          className="absolute right-3 top-3 z-10 flex h-7 w-7 items-center justify-center border text-[13px] transition-transform active:translate-x-[1px] active:translate-y-[1px]"
          style={{ background: FIELD, borderColor: CRIMSON, color: CRIMSON }}
        >
          ✕
        </button>
        <div className="h-full w-full min-h-0 flex-1 overflow-hidden">
          {active === "wire" && <WireTakeover gameId={gameId} />}
          {active === "chronicle" && <ChronicleTakeover gameId={gameId} />}
          {active === "dialectic" && <DialecticTakeover gameId={gameId} />}
        </div>
      </div>
    </div>
  );
}
