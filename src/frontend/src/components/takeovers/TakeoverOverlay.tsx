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
 */

import { useEffect } from "react";
import { useStore } from "@/store";
import { WireTakeover } from "./wire/WireTakeover";
import { ChronicleTakeover } from "./chronicle/ChronicleTakeover";
import { DialecticTakeover } from "./dialectic/DialecticTakeover";

interface Props {
  gameId: string;
}

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
      className="fixed inset-0 z-50 bg-void"
      data-testid="takeover-overlay"
      data-takeover={active}
      role="dialog"
      aria-modal="true"
      aria-label={`${active} takeover`}
    >
      <button
        onClick={closeTakeover}
        aria-label="Close takeover"
        data-testid="takeover-close"
        className="absolute right-3 top-3 z-10 flex h-7 w-7 items-center justify-center rounded border border-rebar bg-concrete text-[13px] text-fog hover:border-laser hover:text-laser"
      >
        ✕
      </button>
      <div className="h-full w-full">
        {active === "wire" && <WireTakeover gameId={gameId} />}
        {active === "chronicle" && <ChronicleTakeover gameId={gameId} />}
        {active === "dialectic" && <DialecticTakeover gameId={gameId} />}
      </div>
    </div>
  );
}
