/**
 * Organization dashboard component.
 *
 * Displays organization state: resources, type, class character,
 * and key metrics for each org in the game.
 */

import { useMemo, useState } from "react";
import type { GameSnapshot, OrgState } from "@/types/game";

interface OrgDashboardProps {
  snapshot: GameSnapshot;
  onSelectOrg?: (orgId: string) => void;
}

export function OrgDashboard({ snapshot, onSelectOrg }: OrgDashboardProps) {
  const [selectedOrg, setSelectedOrg] = useState<string | null>(null);

  const orgs = useMemo(() => {
    return Object.entries(snapshot.organizations ?? {});
  }, [snapshot.organizations]);

  function handleSelect(orgId: string) {
    setSelectedOrg(orgId === selectedOrg ? null : orgId);
    onSelectOrg?.(orgId);
  }

  return (
    <div style={styles.container}>
      <h3 style={styles.title}>Organizations</h3>

      {orgs.length === 0 ? (
        <p style={styles.empty}>No organizations in this game</p>
      ) : (
        <div style={styles.list}>
          {orgs.map(([id, org]) => (
            <button
              key={id}
              onClick={() => handleSelect(id)}
              style={{
                ...styles.orgCard,
                ...(selectedOrg === id ? styles.orgSelected : {}),
              }}
            >
              <div style={styles.orgHeader}>
                <span style={styles.orgName}>{org.name}</span>
                <span style={styles.orgType}>{org.org_type}</span>
              </div>
              <div style={styles.orgStats}>
                <OrgStat label="Resources" value={org.resources} />
                {org["class_character"] !== undefined && (
                  <OrgStat
                    label="Class"
                    value={String(org["class_character"])}
                  />
                )}
                {org["capacity"] !== undefined && (
                  <OrgStat
                    label="Capacity"
                    value={Number(org["capacity"])}
                  />
                )}
              </div>
              {selectedOrg === id && (
                <pre style={styles.detail}>
                  {JSON.stringify(org, null, 2)}
                </pre>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function OrgStat({
  label,
  value,
}: {
  label: string;
  value: number | string;
}) {
  const display =
    typeof value === "number" ? value.toFixed(1) : value;
  return (
    <div style={statStyles.container}>
      <span style={statStyles.label}>{label}</span>
      <span style={statStyles.value}>{display}</span>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: "flex",
    flexDirection: "column" as const,
    height: "100%",
  },
  title: {
    fontSize: "14px",
    fontWeight: 600,
    color: "#c8a860",
    textTransform: "uppercase" as const,
    letterSpacing: "1px",
    marginBottom: "12px",
    flexShrink: 0,
  },
  empty: {
    color: "#666",
    fontSize: "14px",
    textAlign: "center" as const,
  },
  list: {
    display: "flex",
    flexDirection: "column" as const,
    gap: "8px",
    overflow: "auto",
    flex: 1,
  },
  orgCard: {
    background: "#0e0e18",
    border: "1px solid #2a2a3a",
    borderRadius: "6px",
    padding: "10px 14px",
    cursor: "pointer",
    textAlign: "left" as const,
    color: "#e0e0e0",
    width: "100%",
    fontSize: "13px",
  },
  orgSelected: {
    borderColor: "#c8a860",
  },
  orgHeader: {
    display: "flex",
    justifyContent: "space-between",
    marginBottom: "6px",
  },
  orgName: {
    fontWeight: 600,
    color: "#80b0e0",
  },
  orgType: {
    fontSize: "11px",
    color: "#666",
    textTransform: "uppercase" as const,
    letterSpacing: "0.5px",
  },
  orgStats: {
    display: "flex",
    gap: "16px",
  },
  detail: {
    marginTop: "8px",
    padding: "8px",
    background: "#0a0a14",
    borderRadius: "4px",
    fontSize: "11px",
    color: "#888",
    whiteSpace: "pre-wrap" as const,
    wordBreak: "break-all" as const,
  },
};

const statStyles: Record<string, React.CSSProperties> = {
  container: {
    display: "flex",
    flexDirection: "column" as const,
    gap: "2px",
  },
  label: {
    fontSize: "10px",
    color: "#666",
    textTransform: "uppercase" as const,
    letterSpacing: "0.5px",
  },
  value: {
    fontSize: "14px",
    fontWeight: 600,
    color: "#e0e0e0",
    fontFamily: "monospace",
  },
};
