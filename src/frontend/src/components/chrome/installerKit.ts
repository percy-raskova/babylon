/**
 * installerKit — shared class-string primitives for the Installer dialog
 * anatomy (DESIGN_BIBLE.md §9b, spec-113 Lane SKIN-CHROME). Every chrome
 * button/frame/well in `components/chrome/**` and the map-controls
 * cluster composes these instead of hand-rolling the grammar per call
 * site, so "gold inverse-video for selected/active states... everywhere
 * the same grammar" (task brief §5) actually holds.
 *
 * Pure strings, no components — call sites stay plain `<button>`/`<div>`
 * elements so existing `getByRole`/`getByTestId` queries and `aria-*`
 * attributes are untouched (restyle only, per the task's TDD note: "for
 * pure restyles update existing tests deliberately, assert testids/roles,
 * not classes").
 */

/** Base "button-as-key" shape: square, chunky, hard offset shadow, mono. */
const KEY_BASE =
  "key-button font-mono uppercase tracking-widest transition-colors disabled:cursor-not-allowed";

/** Idle key: plate background, muted-grey border, crimson on hover. */
const KEY_IDLE =
  "border-ksbc-muted-1 bg-plate text-ink hover:border-accent-crimson hover:text-accent-crimson";

/** Selected/active key: gold inverse-video (black text on gold) — the ONE selection grammar. */
const KEY_SELECTED =
  "border-accent-gold bg-accent-gold text-selection-ink hover:text-selection-ink";

/**
 * Composes the shared button-as-key classes. `selected` drives the gold
 * inverse-video grammar (bible §9b: "Selection = inverse video... Focus/
 * hover the same grammar at lower weight"); `extra` appends call-site
 * sizing/spacing (padding/text-size vary per button density).
 */
export function keyButtonClass(selected: boolean, extra = ""): string {
  return `${KEY_BASE} ${selected ? KEY_SELECTED : KEY_IDLE} ${extra}`.trim();
}

/** A muted, non-selectable variant for disabled/no-data affordances (still square + mono). */
export function keyButtonMutedClass(extra = ""): string {
  return `${KEY_BASE} border-ksbc-muted-3 bg-plate text-ksbc-muted-2 ${extra}`.trim();
}

/**
 * Urgent key: crimson border + ink on plate (bible §9b: crimson = urgency
 * accent, never the gold selection grammar) — for recovery affordances
 * like autopause/error Resume.
 */
export function keyButtonUrgentClass(extra = ""): string {
  return `${KEY_BASE} border-accent-crimson bg-plate text-accent-crimson ${extra}`.trim();
}

/** Double-line crimson well wrapper for scrollable content regions (bible §9b "Inner wells"). */
export const INSTALLER_WELL = "installer-well";

/** Title-tab label: crimson, mono, uppercase, breaks the panel's top border (fieldset/legend idiom). */
export const TITLE_TAB =
  "-mt-[9px] ml-2 w-fit bg-plate px-1.5 font-mono text-[10px] uppercase tracking-widest text-accent-crimson";
