/**
 * Verb submit — one verb end-to-end including the target picker
 * (spec-110 B6, cockpit equivalent of web/frontend/e2e/verb-submit.spec.ts).
 * real-loop.spec.ts also drives campaign once as part of the full loop;
 * this spec is the focused ActionComposer/VerbGrid/TargetPicker gate:
 * the flat 9-verb grid (Article V — 3 disabled-but-visible verbs per
 * FR-025), the live snapshot-sourced target picker, and a full
 * submit→201→pending-list round trip.
 *
 * Runs on the "chromium-authenticated" project (storageState from
 * auth.setup.ts) against its own fresh wayne_county session.
 *
 * KNOWN DEFECT (spec-110 B6, found 2026-07-09): every test here needs the
 * "chromium-authenticated" project's storageState, which the "setup"
 * project can never produce — see auth.setup.ts's docstring (Django's
 * CSRF_TRUSTED_ORIGINS/CORS_ALLOWED_ORIGINS 403s any login origin but
 * 5173, including the cockpit's own 5174). Whole suite `fixme` until
 * that `web/` settings allowlist is fixed.
 */
import { expect, test, createWayneCountyGame } from "./fixtures";

let gameId = "";

test.describe("Verb submit — live engine (cockpit, spec-110 B6)", () => {
  test.describe.configure({ mode: "serial" });

  test("provisions a fresh wayne_county session", async ({ page }) => {
    await page.goto("/lobby");
    gameId = await createWayneCountyGame(page);
    expect(gameId, "session creation must return a session_id").toBeTruthy();
  });

  test("ActionComposer renders the 9-verb grid; FR-025 verbs are disabled, not hidden", async ({
    page,
  }) => {
    expect(gameId, "session-creation test ran first").toBeTruthy();
    await page.goto(`/game/${gameId}`);
    await expect(page.getByTestId("action-composer")).toBeVisible({ timeout: 15000 });
    const verbGrid = page.getByTestId("verb-grid");
    await expect(verbGrid).toBeVisible();

    for (const verb of ["Investigate", "Move", "Negotiate"]) {
      await expect(verbGrid.getByRole("button", { name: new RegExp(verb, "i") })).toBeDisabled();
    }
    for (const verb of ["Educate", "Aid", "Attack", "Mobilize", "Campaign", "Reproduce"]) {
      await expect(verbGrid.getByRole("button", { name: new RegExp(verb, "i") })).toBeEnabled();
    }
  });

  test("selecting Campaign renders the live snapshot-sourced target picker", async ({ page }) => {
    expect(gameId, "session-creation test ran first").toBeTruthy();
    await page.goto(`/game/${gameId}`);
    await page
      .getByTestId("verb-grid")
      .getByRole("button", { name: /campaign/i })
      .click();

    const targetPicker = page.getByTestId("target-picker");
    await expect(targetPicker).toBeVisible({ timeout: 10000 });
    await expect(targetPicker.getByRole("button").first()).toBeVisible();
  });

  test("campaign submits through the UI and lands in the pending list", async ({ page }) => {
    expect(gameId, "session-creation test ran first").toBeTruthy();
    await page.goto(`/game/${gameId}`);
    await page
      .getByTestId("verb-grid")
      .getByRole("button", { name: /campaign/i })
      .click();
    await page.getByTestId("target-picker").getByRole("button").first().click();

    const submitButton = page.getByRole("button", { name: /submit campaign/i });
    await expect(submitButton).toBeEnabled({ timeout: 10000 });
    const [submitResp] = await Promise.all([
      page.waitForResponse(
        (r) =>
          r.url().includes(`/api/games/${gameId}/actions/campaign/`) &&
          r.request().method() === "POST",
        { timeout: 20000 },
      ),
      submitButton.click(),
    ]);
    expect(submitResp.status()).toBe(201);
    await expect(page.getByTestId("pending-actions")).toContainText(/campaign/i, {
      timeout: 10000,
    });
  });
});
