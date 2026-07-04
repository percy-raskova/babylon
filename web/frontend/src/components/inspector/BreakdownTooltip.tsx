/**
 * BreakdownTooltip — click-to-open recursive contributor drill-down.
 *
 * Wraps children as a click trigger. Shows a Radix Popover with
 * a recursive BreakdownTree. Max depth capped at 4.
 */

import * as Popover from "@radix-ui/react-popover";
import type { ReactNode } from "react";
import type { ScriptValue, Scope, Contributor } from "@/lib/selectors/types";

const MAX_DEPTH = 4;

interface BreakdownTooltipProps {
  /** The selector to evaluate. */
  selector: ScriptValue;
  /** The scope to evaluate in. */
  scope: Scope | null;
  /** Optional value format function (defaults to 2 decimal places). */
  format?: (value: number) => string;
  /** Trigger element. */
  children: ReactNode;
}

function defaultFormat(value: number): string {
  return Number.isInteger(value) ? value.toLocaleString() : value.toFixed(2);
}

/** Humanize a SourceRef for display. */
function sourceLabel(kind: string, path: string): string {
  switch (kind) {
    case "snapshot_field":
      return `📊 ${path}`;
    case "gamedefines":
      return `⚙️ ${path}`;
    case "derived":
      return `🔗 ${path}`;
    default:
      return path;
  }
}

export function BreakdownTooltip({
  selector,
  scope,
  format = defaultFormat,
  children,
}: BreakdownTooltipProps) {
  if (!scope) {
    return <>{children}</>;
  }

  const breakdown = selector.breakdown(scope);

  return (
    <Popover.Root>
      <Popover.Trigger asChild>
        <button
          type="button"
          className="cursor-pointer underline decoration-dotted underline-offset-2 hover:decoration-solid"
          aria-label={`Breakdown for ${selector.label}`}
        >
          {children}
        </button>
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Content
          className="z-50 w-80 rounded-lg border border-wet-concrete bg-dark-metal p-4 text-sm text-bone shadow-lg"
          sideOffset={5}
          align="start"
        >
          <div className="mb-2 flex items-center justify-between">
            <span className="font-semibold text-gold">{selector.label}</span>
            <span className="text-silver">{format(breakdown.total)}</span>
          </div>
          {selector.description && (
            <p className="mb-3 text-xs text-silver">{selector.description}</p>
          )}
          {breakdown.contributors.length > 0 ? (
            <BreakdownTree contributors={breakdown.contributors} format={format} depth={0} />
          ) : (
            <p className="text-xs text-silver">No contributors</p>
          )}
          <Popover.Arrow className="fill-wet-concrete" />
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  );
}

// -----------------------------------------------------------------------
// Recursive tree
// -----------------------------------------------------------------------

function BreakdownTree({
  contributors,
  format,
  depth,
}: {
  contributors: Contributor[];
  format: (v: number) => string;
  depth: number;
}) {
  if (depth >= MAX_DEPTH) return null;

  return (
    <ul className="space-y-1" style={{ paddingLeft: depth > 0 ? "0.75rem" : 0 }}>
      {contributors.map((c, i) => (
        <li key={`${c.label}-${i}`}>
          <div className="flex items-center justify-between gap-2">
            <span className={depth === 0 ? "text-bone" : "text-silver"}>{c.label}</span>
            <div className="flex items-center gap-2 text-right">
              <span className={c.value < 0 ? "text-crimson" : "text-bone"}>{format(c.value)}</span>
              <span className="text-xs text-silver">({(c.share * 100).toFixed(0)}%)</span>
            </div>
          </div>
          <div className="text-xs text-ash">{sourceLabel(c.source.kind, c.source.path)}</div>
          {c.children.length > 0 && (
            <BreakdownTree contributors={c.children} format={format} depth={depth + 1} />
          )}
        </li>
      ))}
    </ul>
  );
}
