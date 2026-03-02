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

export function ActionPanel({
  actions,
  onSubmit,
  onResolve,
  resolving,
}: ActionPanelProps) {
  const [submitting, setSubmitting] = useState<string | null>(null);

  const grouped = useMemo(() => {
    const groups: Record<string, AvailableAction[]> = {};
    for (const action of actions) {
      const key = action.org_id;
      if (!groups[key]) {
        groups[key] = [];
      }
      groups[key]!.push(action);
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
    <div style={styles.container}>
      <div style={styles.header}>
        <h3 style={styles.title}>Actions</h3>
        <button
          onClick={onResolve}
          disabled={resolving}
          style={styles.resolveButton}
        >
          {resolving ? "Resolving..." : "Resolve Tick"}
        </button>
      </div>

      {actions.length === 0 ? (
        <p style={styles.empty}>No actions available this tick</p>
      ) : (
        <div style={styles.groups}>
          {Object.entries(grouped).map(([orgId, orgActions]) => (
            <div key={orgId} style={styles.group}>
              <div style={styles.orgHeader}>{orgId}</div>
              {orgActions.map((action, i) => {
                const key = `${action.org_id}-${action.verb}`;
                return (
                  <button
                    key={`${key}-${i}`}
                    onClick={() => handleSubmit(action)}
                    disabled={submitting === key}
                    style={styles.actionRow}
                  >
                    <span style={styles.verb}>{action.verb}</span>
                    {action.action_type && (
                      <span style={styles.actionType}>
                        {action.action_type}
                      </span>
                    )}
                    {action.cost !== undefined && (
                      <span style={styles.cost}>
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

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: "flex",
    flexDirection: "column" as const,
    height: "100%",
  },
  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: "12px",
    flexShrink: 0,
  },
  title: {
    fontSize: "14px",
    fontWeight: 600,
    color: "#c8a860",
    textTransform: "uppercase" as const,
    letterSpacing: "1px",
    margin: 0,
  },
  resolveButton: {
    background: "#c8a860",
    color: "#0a0a0f",
    border: "none",
    borderRadius: "6px",
    padding: "6px 16px",
    fontSize: "12px",
    fontWeight: 600,
    cursor: "pointer",
    textTransform: "uppercase" as const,
    letterSpacing: "0.5px",
  },
  empty: {
    color: "#666",
    fontSize: "14px",
    textAlign: "center" as const,
    padding: "24px",
  },
  groups: {
    display: "flex",
    flexDirection: "column" as const,
    gap: "12px",
    overflow: "auto",
    flex: 1,
  },
  group: {
    display: "flex",
    flexDirection: "column" as const,
    gap: "4px",
  },
  orgHeader: {
    fontSize: "13px",
    fontWeight: 600,
    color: "#80b0e0",
    padding: "4px 0",
  },
  actionRow: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    background: "#0e0e18",
    border: "1px solid #2a2a3a",
    borderRadius: "4px",
    padding: "8px 12px",
    cursor: "pointer",
    color: "#e0e0e0",
    fontSize: "13px",
    width: "100%",
    textAlign: "left" as const,
  },
  verb: {
    color: "#c8a860",
    fontWeight: 500,
    textTransform: "uppercase" as const,
    letterSpacing: "0.5px",
    fontSize: "12px",
  },
  actionType: {
    color: "#888",
    fontSize: "12px",
  },
  cost: {
    color: "#e06060",
    fontSize: "12px",
    fontFamily: "monospace",
  },
};
