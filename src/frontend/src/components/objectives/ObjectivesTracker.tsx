/**
 * ObjectivesTracker - Vic3-style objectives tracker.
 * Spec 095 FR-095-10: ports the objectives tracker design.
 *
 * Lists active/completed/failed objectives with progress bars and status
 * badges. Objectives map to the 5 endgame conditions. Fed by useObjectives
 * hook polling GET /api/games/:id/objectives/.
 *
 * Constitution III: pure read.
 */

import { useObjectives } from "@/hooks/useObjectives";
import type { Objective, ObjectiveStatus } from "@/types/dialectic";
import "@/components/objectives/objectives.css";

interface Props {
  gameId: string;
}

/** Map an objective's category to its accent color. */
function categoryColor(category: string): string {
  switch (category) {
    case "revolution":
      return "var(--babylon-rupture)";
    case "collapse":
      return "var(--babylon-heat)";
    case "fascist":
      return "var(--babylon-laser)";
    case "red_ogv":
      return "var(--babylon-rent)";
    case "fragmented":
      return "var(--babylon-thermal)";
    default:
      return "var(--babylon-cadre)";
  }
}

function badgeClass(status: ObjectiveStatus): string {
  switch (status) {
    case "complete":
      return "objective-badge--complete";
    case "failed":
      return "objective-badge--failed";
    default:
      return "objective-badge--active";
  }
}

function cardClass(status: ObjectiveStatus): string {
  switch (status) {
    case "complete":
      return "objective-card--complete";
    case "failed":
      return "objective-card--failed";
    default:
      return "";
  }
}

function ObjectiveRow({ obj }: { obj: Objective }) {
  const color = categoryColor(obj.category);
  const pct = `${Math.min(100, Math.max(0, obj.progress * 100)).toFixed(0)}%`;

  return (
    <div className={`objective-card ${cardClass(obj.status)}`}>
      <div className="objective-card-top">
        <div>
          <div className="objective-title">{obj.title}</div>
          <div className="objective-description">{obj.description}</div>
        </div>
        <span className={`objective-badge ${badgeClass(obj.status)}`}>{obj.status}</span>
      </div>
      <div className="objective-progress-row">
        <span className="objective-progress-label">Progress</span>
        <div className="objective-progress-track">
          <div className="objective-progress-fill" style={{ width: pct, background: color }} />
        </div>
        <span className="objective-progress-value" style={{ color }}>
          {obj.progress.toFixed(2)}
        </span>
      </div>
      <div className="objective-category">▸ {obj.category}</div>
    </div>
  );
}

export function ObjectivesTracker({ gameId }: Props) {
  const { data: tracker, loading, error } = useObjectives(gameId);

  return (
    <div className="objectives-tracker">
      <div className="objectives-header">
        <span className="objectives-title">▸ Objectives</span>
        <span className="objectives-count">{tracker.objectives.length} tracked</span>
      </div>

      {loading && tracker.objectives.length === 0 && (
        <div className="objectives-empty">Loading objectives…</div>
      )}
      {error && <div className="objectives-empty">Error: {error}</div>}

      {tracker.objectives.length === 0 && !loading && !error && (
        <div className="objectives-empty">No objectives declared this session.</div>
      )}

      <div className="objectives-grid">
        {tracker.objectives.map((obj) => (
          <ObjectiveRow key={obj.id} obj={obj} />
        ))}
      </div>
    </div>
  );
}
