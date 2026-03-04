/**
 * usePersistentUI — syncs UI preferences to/from localStorage.
 *
 * Per research.md R-005: localStorage with namespaced key and version field
 * for safe migration of UI preferences.
 */

import { useEffect, useRef } from "react";
import { useUIStore } from "@/stores/uiStore";
import type { UIPreferences } from "@/types/game";

const STORAGE_KEY = "babylon:ui-preferences";
const SCHEMA_VERSION = 1;

/** Debounce delay in ms for persisting changes. */
const PERSIST_DEBOUNCE_MS = 500;

/**
 * Read saved preferences from localStorage.
 * Returns null if absent, corrupt, or wrong version.
 */
function loadPreferences(): UIPreferences | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as UIPreferences;
    if (parsed.version !== SCHEMA_VERSION) return null;
    return parsed;
  } catch {
    return null;
  }
}

/**
 * Write current UI preferences to localStorage.
 */
function savePreferences(prefs: UIPreferences): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs));
  } catch {
    // Silently fail if storage is full or unavailable
  }
}

/**
 * Extract UIPreferences from current uiStore state.
 */
function extractPreferences(): UIPreferences {
  const s = useUIStore.getState();
  return {
    version: SCHEMA_VERSION,
    rightPanelWidth: s.rightPanelWidth,
    rightPanelOpen: s.rightPanelOpen,
    bottomPanelHeight: s.bottomPanelHeight,
    bottomPanelOpen: s.bottomPanelOpen,
    bottomTab: s.bottomTab,
    activeLens: s.activeLens,
    pinnedIndicators: s.pinnedIndicators,
    graphEdgeFilter: null,
  };
}

/**
 * Hook that restores UI preferences on mount and persists changes
 * with a debounced write to localStorage.
 *
 * Call once at the app shell level (e.g., GameShell).
 */
export function usePersistentUI(): void {
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Restore on mount
  useEffect(() => {
    const saved = loadPreferences();
    if (saved) {
      useUIStore.setState({
        rightPanelWidth: saved.rightPanelWidth,
        rightPanelOpen: saved.rightPanelOpen,
        bottomPanelHeight: saved.bottomPanelHeight,
        bottomPanelOpen: saved.bottomPanelOpen,
        bottomTab: saved.bottomTab,
        activeLens: saved.activeLens,
        pinnedIndicators: saved.pinnedIndicators,
      });
    }
  }, []);

  // Subscribe to changes and persist with debounce
  useEffect(() => {
    const unsubscribe = useUIStore.subscribe(() => {
      if (timerRef.current) {
        clearTimeout(timerRef.current);
      }
      timerRef.current = setTimeout(() => {
        savePreferences(extractPreferences());
      }, PERSIST_DEBOUNCE_MS);
    });

    return () => {
      unsubscribe();
      if (timerRef.current) {
        clearTimeout(timerRef.current);
      }
    };
  }, []);
}
