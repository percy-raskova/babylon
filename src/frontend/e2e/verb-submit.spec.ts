/**
 * Verb submit — one verb end-to-end including the target picker
 * (spec-110 B6, cockpit equivalent of web/frontend/e2e/verb-submit.spec.ts).
 * real-loop.spec.ts also drives campaign once as part of the full loop;
 * this spec is the focused ActionComposer/VerbGrid/TargetPicker gate:
 * the flat 9-verb grid (Article V — all 9 verbs have real engine
 * resolvers, see `babylon.engine.actions.VERB_RESOLVERS`, but at tick 0
 * EDUCATE and MOBILIZE render disabled-with-reason per spec-116 FR-4.8 —
 * a structural dead-end honestly surfaced, not a missing handler), the
 * live snapshot-sourced target picker, and a full submit→201→pending-list
 * round trip.
 *
 * Runs on the "chromium-authenticated" project (storageState from
 * auth.setup.ts) against its own fresh wayne_county session.
 *
 * HISTORY (spec-110 B6, found 2026-07-09, RESOLVED d5f270b2): this suite
 * was once whole-suite `fixme` because Django's CSRF/CORS allowlist 403'd
 * every login origin but 5173 — see auth.setup.ts's docstring for the fix.
 * No `fixme` remains; the suite runs for real against the live stack.
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

  test("VerbGrid tick-0 eligibility: EDUCATE and MOBILIZE disabled with visible reason, no dead-end clicks (spec-116 FR-4.8)", async ({
    page,
  }) => {
    expect(gameId, "session-creation test ran first").toBeTruthy();
    await page.goto(`/game/${gameId}`);
    await expect(page.getByTestId("action-composer")).toBeVisible({ timeout: 15000 });
    const verbGrid = page.getByTestId("verb-grid");
    await expect(verbGrid).toBeVisible();

    // Tick-0 wayne_county: no social_class node carries the org's
    // territories (structural — SocialClass has no territory_ids field)
    // and the only co-located org is the state apparatus, so EDUCATE and
    // MOBILIZE are disabled-with-reason instead of dead-ending into
    // "No eligible targets."
    const educate = verbGrid.getByRole("button", { name: /educate/i });
    await expect(educate).toBeDisabled({ timeout: 15000 });
    await expect(educate).toHaveAttribute(
      "title",
      /no eligible targets yet: No organized community/,
    );
    await expect(verbGrid.getByRole("button", { name: /mobilize/i })).toBeDisabled();

    // Reason + remedy are VISIBLE, not tooltip-only.
    const reasons = page.getByTestId("verb-ineligible-reasons");
    await expect(reasons).toContainText("No organized community in your territories yet.");
    await expect(reasons).toContainText("political education unlocks");

    // Article V: the other seven verbs stay enabled; nothing is hidden.
    for (const verb of [
      "Aid",
      "Attack",
      "Campaign",
      "Move",
      "Investigate",
      "Reproduce",
      "Negotiate",
    ]) {
      await expect(verbGrid.getByRole("button", { name: new RegExp(verb, "i") })).toBeEnabled();
    }
    await expect(verbGrid.getByRole("button")).toHaveCount(9);
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

    // Spine acceptance gate #5 (spec-116): preview visible BEFORE every
    // submit. Campaign deltas can be zero (DeltaChip is honest-null), so the
    // guaranteed pre-submit surfaces are the probability line and the cost
    // line (campaign has no live cost envelope — GET 405s — so the line
    // carries the preview's AP cost).
    await expect(page.getByTestId("preview-probability")).toBeVisible({ timeout: 10000 });
    await expect(page.getByTestId("verb-cost")).toBeVisible();
    await expect(page.getByTestId("verb-cost")).toContainText("AP");

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
