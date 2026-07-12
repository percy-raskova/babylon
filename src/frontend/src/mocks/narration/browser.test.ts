/**
 * Tests for the narration dev-mode MSW browser worker gate.
 *
 * Only the `VITE_MOCK_NARRATION` env-gate is exercised here — actually
 * starting a `msw/browser` worker requires a real `navigator.serviceWorker`
 * (unavailable under jsdom/Vitest), so the "enabled" path is left to
 * manual dev verification (documented in `browser.ts`'s module docstring).
 */

import { describe, it, expect, afterEach, vi } from "vitest";

describe("startNarrationMockWorker", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.resetModules();
  });

  it("is a no-op (never touches msw/browser) when VITE_MOCK_NARRATION is unset", async () => {
    vi.stubEnv("VITE_MOCK_NARRATION", "");
    vi.resetModules();
    const { startNarrationMockWorker } = await import("./browser");

    await expect(startNarrationMockWorker()).resolves.toBeUndefined();
  });

  it('is a no-op when VITE_MOCK_NARRATION is set to something other than "1"', async () => {
    vi.stubEnv("VITE_MOCK_NARRATION", "0");
    vi.resetModules();
    const { startNarrationMockWorker } = await import("./browser");

    await expect(startNarrationMockWorker()).resolves.toBeUndefined();
  });
});
