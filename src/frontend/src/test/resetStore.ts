/**
 * Reset the cockpit zustand store to its pristine initial state between
 * tests (spec-110 B3). `useStore` is a module-level singleton, so without
 * this, state (auth, snapshot, panel data, time status, ...) would leak
 * across test cases.
 *
 * Captures the state graph once at import time — every slice action
 * updates its subtree by spreading into a *new* object
 * (`{...s.session, field: x}`), never mutating in place, so the captured
 * `initialState` reference graph stays untouched no matter what tests do
 * to the live store. `setState(initialState, true)` (the `replace` flag)
 * then restores it exactly, action references included.
 */

import { useStore } from "@/store";

const initialState = useStore.getState();

export function resetStore(): void {
  useStore.setState(initialState, true);
}
