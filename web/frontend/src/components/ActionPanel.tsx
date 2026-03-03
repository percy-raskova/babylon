/**
 * Action panel for submitting player actions.
 *
 * Shows available actions grouped by organization,
 * allows selection and submission.
 */

import { useCallback, useMemo, useState } from "react";
import type { AvailableAction, SubmitActionParams } from "@/types/game";

interface ActionPanelProps {
  actions: AvailableAction[];
  onSubmit: (params: SubmitActionParams) => Promise<void>;
  onResolve: () => Promise<void>;
  resolving: boolean;
}

export function ActionPanel({ actions, onSubmit, onResolve, resolving }: ActionPanelProps) {
  const [submitting, setSubmitting] = useState<string | null>(null);

  const grouped = useMemo(() => {
    const groups: Record<string, AvailableAction[]> = {};
    for (const action of actions) {
      const key = action.org_id;
      if (!(key in groups)) {
        groups[key] = [];
      }
      const group = groups[key];
      if (group) {
        group.push(action);
      }
    }
    return groups;
  }, [actions]);

  const handleSubmit = useCallback(
    async (action: AvailableAction) => {
      const key = `${action.org_id}-${action.verb}`;
      setSubmitting(key);
      await onSubmit({
        org_id: action.org_id,
        verb: action.verb,
        action_type: action.action_type,
      });
      setSubmitting(null);
    },
    [onSubmit],
  );

  return (
    <div className="flex h-full flex-col">
      <div className="mb-3 flex shrink-0 items-center justify-between">
        <h3 className="m-0 text-sm font-semibold uppercase tracking-wider text-gold">Actions</h3>
        <button
          onClick={onResolve}
          disabled={resolving}
          className="rounded-md bg-gold px-4 py-1.5 text-xs font-semibold uppercase tracking-wider text-void hover:brightness-110 disabled:opacity-50"
        >
          {resolving ? "Resolving..." : "Resolve Tick"}
        </button>
      </div>

      {actions.length === 0 ? (
        <p className="py-6 text-center text-sm text-ash">No actions available this tick</p>
      ) : (
        <div className="flex flex-1 flex-col gap-3 overflow-auto">
          {Object.entries(grouped).map(([orgId, orgActions]) => (
            <div key={orgId} className="flex flex-col gap-1">
              <div className="py-1 text-[13px] font-semibold text-royal-blue">{orgId}</div>
              {orgActions.map((action, i) => {
                const key = `${action.org_id}-${action.verb}`;
                return (
                  <button
                    key={`${key}-${i}`}
                    onClick={() => handleSubmit(action)}
                    disabled={submitting === key}
                    className="flex w-full items-center justify-between rounded border border-wet-concrete bg-void px-3 py-2 text-left text-[13px] text-bone hover:border-silver disabled:opacity-50"
                  >
                    <span className="text-xs font-medium uppercase tracking-wider text-gold">
                      {action.verb}
                    </span>
                    {action.action_type && (
                      <span className="text-xs text-ash">{action.action_type}</span>
                    )}
                    {action.cost !== undefined && (
                      <span className="font-mono text-xs text-phosphor-red">
                        {action.cost.toFixed(1)}
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
