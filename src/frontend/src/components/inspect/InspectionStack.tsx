/**
 * InspectionStack — the recursive drill-down surface (architecture.md
 * §1.1/§2.1, DESIGN_BIBLE.md §4). Mounts in `AppShell`'s marked chrome
 * slot, anchored left-of-tray. Renders nothing when the stack is empty
 * (map never occluded when there's nothing to inspect).
 *
 * Layout: a compact breadcrumb trail (`>`-separated, current node bold +
 * non-clickable, earlier nodes clickable → `popTo(i)` — clicking index 0
 * is DESIGN_BIBLE.md §4's "one-click return to root") above the current
 * (top) frame's full `InspectionCard`. Earlier frames stay resolved in
 * the store (so popping back is instant, no refetch) but only the top
 * frame renders in full — the breadcrumb IS their visible representation,
 * matching Vic3/CK3's one-detailed-card-plus-trail idiom rather than N
 * simultaneously-expanded stacked cards.
 *
 * Escape pops the top frame (`inspect.pop()`, which itself no-ops when
 * that frame is pinned — DESIGN_BIBLE.md §4's "pin keeps a frame open").
 * Backdrop-click-to-dismiss is NOT implemented here: this lane owns no
 * map-click surface to distinguish "click empty map" from "click a new
 * territory" (the latter already replaces the stack via
 * `mapSlice.setSelection`), so a naive outside-click handler would race
 * against that fan-out. Escape is the one Dismiss affordance for now.
 */

import { useEffect } from "react";
import { useStore } from "@/store";
import { FloatingPanel } from "@/components/chrome/FloatingPanel";
import { InspectionCard } from "./InspectionCard";
import { MAX_INSPECTION_DEPTH } from "@/store/slices/inspectSlice";
import { refKey } from "@/lib/inspect/resolvers";

interface InspectionStackProps {
  gameId: string;
}

export function InspectionStack(_props: InspectionStackProps): React.JSX.Element | null {
  const stack = useStore((s) => s.inspect.stack);
  const push = useStore((s) => s.inspect.push);
  const pop = useStore((s) => s.inspect.pop);
  const popTo = useStore((s) => s.inspect.popTo);
  const clear = useStore((s) => s.inspect.clear);
  const togglePin = useStore((s) => s.inspect.togglePin);

  useEffect(() => {
    if (stack.length === 0) return;
    function onKeyDown(e: KeyboardEvent): void {
      if (e.key === "Escape") pop();
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [stack.length, pop]);

  if (stack.length === 0) return null;
  const current = stack[stack.length - 1];
  if (!current) return null;

  const atDepthLimit = stack.length >= MAX_INSPECTION_DEPTH;

  return (
    <div
      className="pointer-events-none absolute bottom-2 right-[300px] top-14 flex w-[340px] flex-col"
      data-testid="inspection-stack-region"
    >
      <FloatingPanel anchor="free" width={340} testId="inspection-stack">
        <div className="flex flex-col gap-2 p-2">
          <div
            className="flex items-start justify-between gap-2 border-b border-rebar pb-1.5"
            data-testid="inspection-breadcrumb"
          >
            <div className="flex flex-wrap items-baseline gap-1 text-[10px]">
              {stack.map((frame, i) => {
                const isLast = i === stack.length - 1;
                const label = frame.data?.title ?? frame.ref.label ?? frame.ref.id;
                return (
                  <span key={refKey(frame.ref) + String(i)} className="flex items-baseline gap-1">
                    {i > 0 && (
                      <span className="text-shroud" aria-hidden="true">
                        &rsaquo;
                      </span>
                    )}
                    {isLast ? (
                      <span className="font-semibold text-spire">{label}</span>
                    ) : (
                      <button
                        type="button"
                        onClick={() => popTo(i)}
                        data-testid={`inspection-breadcrumb-${i}`}
                        className="text-fog underline decoration-dotted underline-offset-2 hover:text-spire"
                      >
                        {label}
                      </button>
                    )}
                  </span>
                );
              })}
            </div>
            <button
              type="button"
              onClick={clear}
              data-testid="inspection-close-all"
              aria-label="Close inspection stack"
              className="shrink-0 rounded border border-rebar px-1.5 text-[10px] text-fog hover:border-spire hover:text-spire"
            >
              &times;
            </button>
          </div>

          <InspectionCard
            frame={current}
            canDrill={!atDepthLimit}
            onDrill={push}
            onTogglePin={() => togglePin(stack.length - 1)}
          />
        </div>
      </FloatingPanel>
    </div>
  );
}
