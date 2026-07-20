/**
 * Verb submit — one verb end-to-end including the target picker
 * (spec-110 B6, cockpit equivalent of web/frontend/e2e/verb-submit.spec.ts).
 * real-loop.spec.ts also drives campaign once as part of the full loop;
 * this spec is the focused ActionComposer/VerbGrid/TargetPicker gate: the
 * flat 9-verb grid (Article V — all 9 verbs have real engine resolvers,
 * see `babylon.engine.actions.VERB_RESOLVERS`, and all nine are ELIGIBLE
 * at tick 0 in wayne_county — see the eligibility test's own comment), the
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
 *
 * CORRECTED 2026-07-19 (G7-epilogue task, folded in): the eligibility test
 * used to assert EDUCATE and MOBILIZE disabled-with-reason at tick 0 — the
 * same stale defect-era assumption `first-session.spec.ts`'s leg 4 already
 * shed (see that file's own comment, citing commit 4fa5d45c). That
 * expectation encoded the retired `territory_ids`-on-social_class
 * fabricated-shape bug (`get_verb_eligibility`'s `has_social_class`
 * predicate read a field `SocialClass` never declares); the fix resolves
 * class -> territory via the real Occupant -> Territory TENANCY edge
 * instead, and wayne_county's map is 100% class-partitioned from scenario
 * construction, so a resident social_class already tenants the player's
 * territories from tick 0 by design. Re-verified live against this exact
 * spec's own session before amending: `GET .../actions/eligibility/` on a
 * fresh wayne_county session at tick 0 returns `eligible: true` for all
 * nine verbs, no `verb-ineligible-reasons` block. Amended to the honest,
 * currently-correct assertion (positive, not a fabricated disabled state)
 * rather than deleting the coverage.
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

  test("VerbGrid tick-0 eligibility: all nine verbs enabled, no dead ends, no fabricated disabled state (spec-116 FR-4.8)", async ({
    page,
  }) => {
    expect(gameId, "session-creation test ran first").toBeTruthy();
    await page.goto(`/game/${gameId}`);
    await expect(page.getByTestId("action-composer")).toBeVisible({ timeout: 15000 });
    const verbGrid = page.getByTestId("verb-grid");
    await expect(verbGrid).toBeVisible();

    // Tick-0 wayne_county: EDUCATE and MOBILIZE are ELIGIBLE, not disabled.
    // This leg used to assert the opposite ("no organized community in the
    // player's territories yet") — that expectation encoded the retired
    // `territory_ids`-on-social_class fabricated-shape bug. Commit
    // 4fa5d45c (Track 1 Task 8b) fixed `get_verb_eligibility`'s
    // `has_social_class` predicate (and `get_educate_targets`) to resolve
    // class -> territory via the real Occupant -> Territory TENANCY edge
    // (`_tenancy_members_by_territory` in `web/game/engine_bridge.py`), not
    // the nonexistent `territory_ids` field on social_class nodes.
    // wayne_county's map is 100% class-partitioned from scenario
    // construction (`_legacy_wayne.py`), so a resident social_class already
    // tenants the player's starting territories from tick 0 by design —
    // see `first-session.spec.ts`'s verb-grid leg for the same finding,
    // pinned there by `TestVerbEligibilityAgreesWithTargetsRealWayneCounty`.
    // All nine verbs render enabled and the disabled-with-reason machinery
    // (still real and unchanged) stays absent — the honest live state, not
    // a fabricated dead end in either direction.
    for (const verb of [
      "Educate",
      "Aid",
      "Attack",
      "Mobilize",
      "Campaign",
      "Move",
      "Investigate",
      "Reproduce",
      "Negotiate",
    ]) {
      await expect(
        verbGrid.getByRole("button", { name: new RegExp(verb, "i") }),
        `${verb} must be enabled at tick 0 (real live state)`,
      ).toBeEnabled({ timeout: 15000 });
    }
    await expect(verbGrid.getByRole("button")).toHaveCount(9);
    await expect(page.getByTestId("verb-ineligible-reasons")).toHaveCount(0);
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
