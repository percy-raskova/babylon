/**
 * The Veil of Money — locked-instrument + study-link e2e (spec-117 §5d, D7;
 * spec §7 lines 264-265's contracted acceptance gate, "(e2e)" literal in the
 * text: a locked instrument for a below-threshold player, with a study-link
 * into the doctrine page). Drives a REAL tier-0 session to `/game/:id/circuit`
 * and asserts the veiled placeholders render (never the real numbers), then
 * follows the study CTA into the REAL routed Doctrine page.
 *
 * **Why this session is guaranteed tier 0**: `Organization.acquired_doctrine_ids`
 * defaults to `()` (`src/babylon/models/entities/organization.py`), and
 * `EngineBridge.create_game` persists the raw scenario-built `WorldState`
 * directly — it never runs an engine tick (see that method: it calls
 * `_build_initial_state_for_scenario` then `persist_tick` straight away, no
 * `run_tick`). `web/game/veil.py`'s module docstring notes `DoctrineSystem`
 * would auto-bootstrap the free `class_consciousness` root "once
 * theoretical_labor >= 0, which holds from the first tick it ever runs" —
 * i.e. tier could flip to 1 as early as the FIRST resolved tick. This spec
 * therefore never steps/resolves a tick: it reads the Circuit straight off
 * the freshly-created (never-resolved) tick-0 state, where
 * `acquired_doctrine_ids` is still empty and `compute_veil_tier` is
 * structurally 0 (`web/game/veil.py`, pinned unit-side by
 * `tests/unit/web/test_veil.py::test_empty_acquired_is_tier_zero`).
 *
 * FOLLOW-PATTERN: `verb-submit.spec.ts` (`createWayneCountyGame` + serial
 * describe, bypassing the lobby UI for a fresh, uncontended session — Track
 * 2/3 route testids are read off the actual component source
 * (`CircuitPage.tsx`, `DoctrinePage.tsx`, `DoctrineTakeover.tsx`), not
 * invented: `veil-locked` / `veil-study-link-exploitation` /
 * `veil-study-link-scissors` / `circuit-exploitation-chips` / `scissors-chart`
 * / `region-doctrine` / `doctrine-takeover`.
 *
 * Runs on "chromium-authenticated" (registered in AUTHENTICATED_SPECS,
 * storageState from auth.setup.ts) against its OWN fresh wayne_county
 * session — never shared across spec files (game_turn enforces one queued
 * action per (session, tick, org), and this spec never queues one anyway).
 */
import { expect, test, createWayneCountyGame } from "./fixtures";

/** Session id created by the "provisions a fresh session" test. */
let gameId = "";

test.describe("Veil of Money — locked instrument + study link (spec-117 D7, §7 e2e gate)", () => {
  test.describe.configure({ mode: "serial" });

  test("provisions a fresh wayne_county session (tier 0: no doctrines acquired)", async ({
    page,
  }) => {
    await page.goto("/lobby");
    gameId = await createWayneCountyGame(page);
    expect(gameId, "session creation must return a session_id").toBeTruthy();
  });

  test("the Circuit veils both the exploitation axis and the scissors, real numbers absent", async ({
    page,
  }) => {
    expect(gameId, "session-creation test ran first").toBeTruthy();
    await page.goto(`/game/${gameId}/circuit`);
    await expect(page.getByTestId("region-circuit")).toBeVisible({ timeout: 15000 });

    // Tier 0: CircuitPage renders ONE VeilLock per veiled section
    // (exploitation + scissors), each carrying the same "veil-locked"
    // testid — never a bare hidden section (spec-117 §5d: "Your cadre
    // cannot yet see through the money-form").
    await expect(page.getByTestId("veil-locked").first()).toBeVisible({ timeout: 15000 });
    await expect(page.getByTestId("veil-locked")).toHaveCount(2);
    await expect(page.getByTestId("veil-study-link-exploitation")).toBeVisible();
    await expect(page.getByTestId("veil-study-link-scissors")).toBeVisible();

    // The REAL numbers are absent for this tier-0 client: no scissors chart
    // (Program 23's ScissorsChart, tier >= 2 only) and no exploitation
    // value/rate chips (tier >= 1 only).
    await expect(page.getByTestId("scissors-chart")).toHaveCount(0);
    await expect(page.getByTestId("circuit-exploitation-chips")).toHaveCount(0);
  });

  test("the study CTA navigates to the REAL routed Doctrine page (not a stub)", async ({
    page,
  }) => {
    expect(gameId, "session-creation test ran first").toBeTruthy();
    await page.goto(`/game/${gameId}/circuit`);
    await expect(page.getByTestId("veil-study-link-exploitation")).toBeVisible({
      timeout: 15000,
    });

    await page.getByTestId("veil-study-link-exploitation").click();

    await expect(page).toHaveURL(new RegExp(`/game/${gameId}/doctrine$`), { timeout: 15000 });
    // Not just a URL match: the real routed Doctrine page chrome...
    await expect(page.getByTestId("region-doctrine")).toBeVisible({ timeout: 15000 });
    // ...and its live content — the Doctrine Tree canvas (DoctrineTakeover,
    // relocated onto this route by T3-5), fed by the real
    // `/doctrine-tree/` endpoint: theoretical-labor readout and the tier-0
    // row (naming the same `class_consciousness` node the study link named)
    // both render, proving real tree data loaded rather than an empty shell.
    await expect(page.getByTestId("doctrine-takeover")).toBeVisible({ timeout: 15000 });
    await expect(page.getByTestId("doctrine-theoretical-labor")).toBeVisible({ timeout: 10000 });
    await expect(page.getByTestId("doctrine-tier-0")).toBeVisible({ timeout: 10000 });
    await expect(page.getByTestId("doctrine-node-class_consciousness")).toBeVisible();
  });
});
