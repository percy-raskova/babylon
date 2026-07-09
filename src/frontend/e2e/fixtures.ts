/**
 * Playwright storageState auth fixture stub (spec-110 B1).
 *
 * B2 will populate `storageState` by driving the real login flow (or
 * loading a cached auth state file) once the cockpit talks to the Django
 * bridge. For now this just re-exports the base `test`/`expect` so specs
 * have a stable import to grow into.
 */

import { test as base, expect } from "@playwright/test";

export const test = base;
export { expect };
