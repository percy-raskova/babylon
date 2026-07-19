/**
 * VeilLock — the Veil of Money's locked-instrument placeholder (spec-117
 * §5d, D7). "Visible-but-veiled with a path", never a bare hidden section
 * ("Your cadre cannot yet see through the money-form"). The CTA names the
 * REAL next doctrine node (`veil.next_unlock_label`, sourced server-side
 * from the loaded tree, never a fabricated label) and links into the
 * routed Doctrine page (`/game/:id/doctrine`).
 *
 * Extracted from `CircuitPage.tsx` (T2-8/T2-9) to a shared component (G4)
 * so `EconomyDashboard.tsx` can render the identical lock for its own
 * gated stat chips rather than reimplementing the copy/markup — the two
 * screens' veiled sections share one presentation, not two independently
 * authored ones that could drift.
 */

interface VeilLockProps {
  label: string;
  onStudy: () => void;
  /** Disambiguates this lock's testids from a screen's OTHER veiled
   *  section(s) — more than one may render simultaneously at a given tier. */
  section: "exploitation" | "scissors" | "fundamental-theorem" | "economy";
}

export function VeilLock({ label, onStudy, section }: VeilLockProps): React.JSX.Element {
  return (
    <div
      className="border-2 border-dashed border-ksbc-muted-1 p-3 text-[11px] italic text-shroud"
      data-testid="veil-locked"
    >
      Your cadre cannot yet see through the money-form.{" "}
      <button
        type="button"
        onClick={onStudy}
        data-testid={`veil-study-link-${section}`}
        className="not-italic text-accent-crimson underline hover:text-rupture"
      >
        Study: {label}
      </button>
    </div>
  );
}
