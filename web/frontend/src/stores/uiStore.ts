/**
 * UI state store — manages selection, panel visibility, pending actions,
 * lens navigation, breadcrumbs, and notifications.
 */

import { create } from "zustand";
import type {
  PlayerVerb,
  LensId,
  BreadcrumbEntry,
  ClassifiedEvent,
  EventSeverity,
  NotificationGroup,
  IndicatorId,
} from "@/types/game";

export type BottomTab = "timeseries" | "events" | "graph" | "notifications";

/** Maximum events kept in the notification buffer. */
const MAX_EVENT_BUFFER = 500;

/** Maximum breadcrumb depth. */
const MAX_BREADCRUMB_DEPTH = 3;

/** Default pinned indicators (political lens emphasis). */
const DEFAULT_PINNED: IndicatorId[] = [
  "avg_consciousness",
  "avg_heat",
  "avg_organization",
  "imperial_rent",
];

/**
 * Group events of a given severity into NotificationGroups.
 * Events with >2 of the same type are collapsed into a single summary group.
 */
function groupEventsBySeverity(
  events: ClassifiedEvent[],
  severity: EventSeverity,
): NotificationGroup[] {
  const groups: NotificationGroup[] = [];
  const byType = groupByType(events);

  for (const [eventType, typeEvents] of byType) {
    if (typeEvents.length <= 2) {
      for (const evt of typeEvents) {
        groups.push({
          severity,
          eventType,
          count: 1,
          events: [evt],
          summary: `${eventType} event`,
          representativeEvent: evt,
        });
      }
    } else {
      const representative = typeEvents[0];
      if (representative) {
        const label = eventType.toLowerCase().replace(/_/g, " ");
        groups.push({
          severity,
          eventType,
          count: typeEvents.length,
          events: typeEvents,
          summary: `${typeEvents.length} ${label} events`,
          representativeEvent: representative,
        });
      }
    }
  }
  return groups;
}

/**
 * Compute notification groups from classified events for a single tick.
 * Per research.md R-006: group when >2 of same type, max 5 visible cards.
 * Critical events are always shown individually (never grouped).
 */
function computeNotificationGroups(events: ClassifiedEvent[]): NotificationGroup[] {
  const critical = events.filter((e) => e.severity === "critical");
  const important = events.filter((e) => e.severity === "important");
  const informational = events.filter((e) => e.severity === "informational");

  // Critical events: always individual (no grouping)
  const criticalGroups: NotificationGroup[] = critical.map((evt) => ({
    severity: "critical" as const,
    eventType: evt.event.type,
    count: 1,
    events: [evt],
    summary: `${evt.event.type} event`,
    representativeEvent: evt,
  }));

  const importantGroups = groupEventsBySeverity(important, "important");
  const infoGroups = groupEventsBySeverity(informational, "informational");

  // Cap total visible cards at 5
  return [...criticalGroups, ...importantGroups, ...infoGroups].slice(0, 5);
}

function groupByType(events: ClassifiedEvent[]): Map<string, ClassifiedEvent[]> {
  const map = new Map<string, ClassifiedEvent[]>();
  for (const evt of events) {
    const key = evt.event.type;
    const existing = map.get(key);
    if (existing) {
      existing.push(evt);
    } else {
      map.set(key, [evt]);
    }
  }
  return map;
}

interface UIState {
  /** Currently selected node (entity/org/institution) ID. */
  selectedNodeId: string | null;
  /** Currently selected hex (territory) ID. */
  selectedHexId: string | null;
  /** Currently hovered node ID (for cross-view highlight). */
  hoveredNodeId: string | null;

  /** Right panel collapsed state. */
  rightPanelOpen: boolean;
  /** Bottom panel collapsed state. */
  bottomPanelOpen: boolean;
  /** Active bottom tab. */
  bottomTab: BottomTab;

  /** Action composition — pending turn before submission. */
  pendingVerb: PlayerVerb | null;
  pendingOrgId: string | null;
  pendingTargetId: string | null;
  pendingParams: Record<string, unknown>;

  /** Active analytical lens. */
  activeLens: LensId;

  /** Drill-down navigation stack. */
  breadcrumbs: BreadcrumbEntry[];

  /** Accumulated classified events (bounded buffer). */
  notifications: ClassifiedEvent[];
  /** Count of unread events. */
  unreadCount: number;
  /** Computed notification groups for the most recent tick. */
  notificationGroupsForTick: NotificationGroup[];

  /** Right panel width in pixels. */
  rightPanelWidth: number;
  /** Bottom panel height in pixels. */
  bottomPanelHeight: number;

  /** Which indicators are pinned in the top bar. */
  pinnedIndicators: IndicatorId[];

  /** Cross-renderer: org IDs selected in graph → highlight on map. */
  selectedOrgIds: string[];
  /** Cross-renderer: territory IDs selected on map → filter graph. */
  selectedTerritoryIds: string[];
  /** Whether the graph panel (left side) is visible. */
  graphPanelOpen: boolean;
  /** Width of the graph panel in pixels. */
  graphPanelWidth: number;

  // Actions — existing
  setSelectedNode: (id: string | null) => void;
  setSelectedHex: (id: string | null) => void;
  setHoveredNode: (id: string | null) => void;
  toggleRightPanel: () => void;
  toggleBottomPanel: () => void;
  setBottomTab: (tab: BottomTab) => void;
  setPendingAction: (verb: PlayerVerb, orgId: string) => void;
  setPendingTarget: (targetId: string | null) => void;
  clearPendingAction: () => void;

  // Actions — Feature 042
  setActiveLens: (lens: LensId) => void;
  pushBreadcrumb: (entry: BreadcrumbEntry) => void;
  popBreadcrumbTo: (index: number) => void;
  clearBreadcrumbs: () => void;
  addEvents: (events: ClassifiedEvent[]) => void;
  markEventRead: (id: string) => void;
  markAllEventsRead: () => void;
  setRightPanelWidth: (width: number) => void;
  setBottomPanelHeight: (height: number) => void;
  setPinnedIndicators: (ids: IndicatorId[]) => void;
  resetPreferences: () => void;

  // Actions — Cross-renderer coordination
  setSelectedOrgIds: (ids: string[]) => void;
  setSelectedTerritoryIds: (ids: string[]) => void;
  clearCrossSelection: () => void;
  toggleGraphPanel: () => void;
  setGraphPanelWidth: (width: number) => void;
}

export const useUIStore = create<UIState>((set) => ({
  selectedNodeId: null,
  selectedHexId: null,
  hoveredNodeId: null,
  rightPanelOpen: true,
  bottomPanelOpen: true,
  bottomTab: "timeseries",
  pendingVerb: null,
  pendingOrgId: null,
  pendingTargetId: null,
  pendingParams: {},

  // Feature 042 defaults
  activeLens: "political",
  breadcrumbs: [],
  notifications: [],
  unreadCount: 0,
  notificationGroupsForTick: [],
  rightPanelWidth: 360,
  bottomPanelHeight: 260,
  pinnedIndicators: [...DEFAULT_PINNED],
  selectedOrgIds: [],
  selectedTerritoryIds: [],
  graphPanelOpen: true,
  graphPanelWidth: 340,

  // Existing actions
  setSelectedNode: (id) => set({ selectedNodeId: id }),
  setSelectedHex: (id) => set({ selectedHexId: id }),
  setHoveredNode: (id) => set({ hoveredNodeId: id }),
  toggleRightPanel: () => set((s) => ({ rightPanelOpen: !s.rightPanelOpen })),
  toggleBottomPanel: () => set((s) => ({ bottomPanelOpen: !s.bottomPanelOpen })),
  setBottomTab: (tab) => set({ bottomTab: tab }),
  setPendingAction: (verb, orgId) =>
    set({ pendingVerb: verb, pendingOrgId: orgId, pendingTargetId: null, pendingParams: {} }),
  setPendingTarget: (targetId) => set({ pendingTargetId: targetId }),
  clearPendingAction: () =>
    set({ pendingVerb: null, pendingOrgId: null, pendingTargetId: null, pendingParams: {} }),

  // Feature 042 actions
  setActiveLens: (lens) => set({ activeLens: lens }),

  pushBreadcrumb: (entry) =>
    set((s) => {
      const next = [...s.breadcrumbs, entry];
      return { breadcrumbs: next.slice(-MAX_BREADCRUMB_DEPTH) };
    }),

  popBreadcrumbTo: (index) =>
    set((s) => ({
      breadcrumbs: s.breadcrumbs.slice(0, index + 1),
    })),

  clearBreadcrumbs: () => set({ breadcrumbs: [] }),

  addEvents: (events) =>
    set((s) => {
      const merged = [...s.notifications, ...events];
      // Bounded ring buffer: keep most recent MAX_EVENT_BUFFER
      const trimmed = merged.length > MAX_EVENT_BUFFER ? merged.slice(-MAX_EVENT_BUFFER) : merged;
      const newUnread = s.unreadCount + events.filter((e) => !e.read).length;
      return {
        notifications: trimmed,
        unreadCount: newUnread,
        notificationGroupsForTick: computeNotificationGroups(events),
      };
    }),

  markEventRead: (id) =>
    set((s) => {
      let decremented = false;
      const updated = s.notifications.map((e) => {
        if (e.id === id && !e.read) {
          decremented = true;
          return { ...e, read: true };
        }
        return e;
      });
      return {
        notifications: updated,
        unreadCount: decremented ? Math.max(0, s.unreadCount - 1) : s.unreadCount,
      };
    }),

  markAllEventsRead: () =>
    set((s) => ({
      notifications: s.notifications.map((e) => ({ ...e, read: true })),
      unreadCount: 0,
    })),

  setRightPanelWidth: (width) => set({ rightPanelWidth: Math.max(280, Math.min(600, width)) }),

  setBottomPanelHeight: (height) =>
    set({ bottomPanelHeight: Math.max(180, Math.min(400, height)) }),

  setPinnedIndicators: (ids) => set({ pinnedIndicators: ids }),

  resetPreferences: () =>
    set({
      rightPanelWidth: 360,
      rightPanelOpen: true,
      bottomPanelHeight: 260,
      bottomPanelOpen: true,
      bottomTab: "timeseries",
      activeLens: "political",
      pinnedIndicators: [...DEFAULT_PINNED],
      graphPanelOpen: true,
      graphPanelWidth: 340,
    }),

  // Cross-renderer coordination
  setSelectedOrgIds: (ids) => set({ selectedOrgIds: ids }),
  setSelectedTerritoryIds: (ids) => set({ selectedTerritoryIds: ids }),
  clearCrossSelection: () => set({ selectedOrgIds: [], selectedTerritoryIds: [] }),
  toggleGraphPanel: () => set((s) => ({ graphPanelOpen: !s.graphPanelOpen })),
  setGraphPanelWidth: (width) => set({ graphPanelWidth: Math.max(240, Math.min(500, width)) }),
}));
