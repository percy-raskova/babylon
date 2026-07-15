/**
 * Bundle-honesty guard for the narration MSW mock (seam Sensor 3).
 *
 * The narration mock is dev/test infra, not game-render — it must be
 * impossible for it to leak a fabricated narration payload into a real
 * session. Two independent assertions pin that:
 *
 * 1. **Runtime env-gate:** `startNarrationMockWorker()` must never even
 *    *construct* an `msw/browser` worker unless `VITE_MOCK_NARRATION === "1"`.
 *    We spy on the `msw/browser` boundary to prove the gate short-circuits
 *    before `setupWorker`. (Distinct from `browser.test.ts`, which only
 *    checks the promise resolves — that alone cannot tell a no-op apart from
 *    a worker that started.)
 * 2. **Static bundle:** the production entry (`main.tsx`) must not statically
 *    import `msw/browser`, so the mock (and its fixtures) is only ever
 *    reachable via the dev-gated dynamic import documented in `browser.ts`.
 */

import { describe, it, expect, afterEach, vi } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

// vi.hoisted: the spies must exist before the hoisted vi.mock factory runs.
const { setupWorkerSpy, startSpy } = vi.hoisted(() => {
  const startSpy = vi.fn(async () => {});
  const setupWorkerSpy = vi.fn(() => ({ start: startSpy }));
  return { setupWorkerSpy, startSpy };
});

vi.mock("msw/browser", () => ({ setupWorker: setupWorkerSpy }));

describe("narration MSW bundle honesty (seam Sensor 3)", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.resetModules();
    setupWorkerSpy.mockClear();
    startSpy.mockClear();
  });

  it("never constructs an msw/browser worker when VITE_MOCK_NARRATION !== '1'", async () => {
    vi.stubEnv("VITE_MOCK_NARRATION", "");
    vi.resetModules();
    const { startNarrationMockWorker } = await import("./browser");

    await startNarrationMockWorker();

    expect(setupWorkerSpy).not.toHaveBeenCalled();
    expect(startSpy).not.toHaveBeenCalled();
  });

  it("constructs and starts the worker only when the env-gate opens", async () => {
    vi.stubEnv("VITE_MOCK_NARRATION", "1");
    vi.resetModules();
    const { startNarrationMockWorker } = await import("./browser");

    await startNarrationMockWorker();

    expect(setupWorkerSpy).toHaveBeenCalledTimes(1);
    expect(startSpy).toHaveBeenCalledTimes(1);
  });

  it("keeps msw/browser out of the production entry (main.tsx)", () => {
    // Vitest runs with cwd = the frontend package root (src/frontend).
    const mainPath = resolve(process.cwd(), "src/main.tsx");
    const source = readFileSync(mainPath, "utf8");

    expect(source).not.toMatch(/msw\/browser/);
  });
});
