/**
 * NarrationBlock — the one reusable AI-narration slot (Program 16 Lane N).
 *
 * Props-driven, no store coupling — callers (wire cards, toasts, county
 * inspection cards, the future chronicle) pass a `beat` (or `null`) plus
 * the narrator's overall `state`, and this component renders either the
 * beat or one of three honest degradation states (Constitution III.11:
 * absent narration is labeled, never silently blank).
 *
 * Voice register (Design Bible §7): `"wire"` beats read as terse newspaper
 * declaratives (mono, tight tracking); `"analysis"` beats read as the
 * longer theory register (sans, relaxed leading). Neither register ever
 * renders ALL-CAPS — urgency comes from weight/size/color, not shouting.
 */

import type { NarrationBeat, NarrationRegister, NarrationState } from "@/types/narration";

export interface NarrationBlockProps {
  /** The beat to render, or `null` when nothing has been narrated for this slot. */
  beat: NarrationBeat | null;
  /** The narrator's overall availability — governs the empty-state copy when `beat` is `null`. */
  state: NarrationState;
  className?: string;
}

const HEADLINE_CLASS: Record<NarrationRegister, string> = {
  wire: "font-mono text-[11px] font-semibold tracking-wide text-bone",
  analysis: "font-sans text-[12px] font-medium text-bone",
};

const BODY_CLASS: Record<NarrationRegister, string> = {
  wire: "font-mono text-[11px] leading-snug text-ash",
  analysis: "font-sans text-[12px] leading-relaxed text-ash",
};

/** In-register copy for each honest empty state — never the admin voice
 * ("No world state loaded yet."-style); see `.design-sync/NOTES.md` and
 * Design Bible §7 "purge the admin voice". */
const EMPTY_COPY: Record<NarrationState, string> = {
  offline: "The narrator is silent — machine narration is disabled for this session.",
  pending: "Dispatch pending. The narrator hasn't filed yet.",
  ready: "Nothing filed here yet.",
};

export function NarrationBlock({
  beat,
  state,
  className = "",
}: NarrationBlockProps): React.JSX.Element {
  if (beat) {
    return (
      <div
        className={`flex flex-col gap-1 ${className}`}
        data-testid="narration-block"
        data-narration-state="beat"
        data-register={beat.register}
      >
        <p data-testid="narration-headline" className={HEADLINE_CLASS[beat.register]}>
          {beat.headline}
        </p>
        <p data-testid="narration-body" className={BODY_CLASS[beat.register]}>
          {beat.body}
        </p>
      </div>
    );
  }

  return (
    <div
      className={`flex flex-col gap-1 ${className}`}
      data-testid="narration-block"
      data-narration-state={state}
    >
      <p data-testid="narration-empty" className="font-sans text-[11px] italic text-shroud">
        {EMPTY_COPY[state]}
      </p>
    </div>
  );
}
