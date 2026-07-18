/**
 * Lobby & Scenario Briefing e2e (spec-116 FR-116-3) — the first-session
 * flow: create with a curated difficulty preset, land on the briefing
 * (codename, five patterns, win condition, fixed-horizon copy), Begin
 * Operation into the cockpit, then manage the operation from the lobby
 * (archive -> abandoned, arm-and-confirm delete -> row gone).
 *
 * Serial like real-loop.spec.ts: later tests reuse the session the first
 * test created. Creates its OWN session (never shared across spec files —
 * game_turn UNIQUE(session_id, tick, org)). Runs on the
 * "chromium-authenticated" project (registered in AUTHENTICATED_SPECS).
 */
import { expect, test } from "./fixtures";

/** Session id created by the first test. */
let gameId = "";

test.describe("lobby & briefing (spec-116 FR-116-3)", () => {
  test.describe.configure({ mode: "serial" });

  test("creating an operation lands on the Scenario Briefing", async ({ page }) => {
    await page.goto("/lobby");
    await page.getByTestId("scenario-option-wayne_county").click();
    await page.getByTestId("difficulty-option-cadre").click();

    const [createResp] = await Promise.all([
      page.waitForResponse(
        (r) => r.url().includes("/api/games/") && r.request().method() === "POST",
        { timeout: 60000 },
      ),
      page.getByRole("button", { name: /new game/i }).click(),
    ]);
    expect(createResp.status()).toBe(201);
    const body = (await createResp.json()) as { data?: { session_id?: string } };
    gameId = body.data?.session_id ?? "";
    expect(gameId, "create response must carry data.session_id").toBeTruthy();

    await expect(page).toHaveURL(new RegExp(`/game/${gameId}/briefing`), { timeout: 15000 });

    // Codename is server-derived from the session UUID: two uppercase words.
    await expect(page.getByTestId("briefing-codename")).toHaveText(/^OPERATION [A-Z]+ [A-Z]+$/, {
      timeout: 15000,
    });
    // Five real patterns from get_journal_objectives, win condition named.
    await expect(page.locator('[data-testid^="briefing-pattern-"]')).toHaveCount(5, {
      timeout: 15000,
    });
    await expect(page.getByTestId("briefing-win-badge")).toBeVisible();
    // Fixed-horizon framing (owner ruling): a century, not a termination condition.
    await expect(page.getByTestId("briefing-horizon")).toContainText("100 years");

    await page.getByTestId("briefing-begin").click();
    await expect(page).toHaveURL(new RegExp(`/game/${gameId}$`), { timeout: 15000 });
    await expect(page.getByTestId("tick-value")).toHaveText("0", { timeout: 15000 });
  });

  test("the lobby row carries codename metadata; archive then delete retire it", async ({
    page,
  }) => {
    expect(gameId, "created-session test ran first").toBeTruthy();
    await page.goto("/lobby");

    const row = page.getByTestId(`game-option-${gameId}`);
    await expect(row).toBeVisible({ timeout: 10000 });
    await expect(row).toContainText(/Tick \d+/);
    await expect(row).toContainText("ACTIVE");

    // Archive: reversible soft delete — the row re-lists as ABANDONED.
    await page.getByTestId(`game-archive-${gameId}`).click();
    await expect(row).toContainText("ABANDONED", { timeout: 10000 });

    // Delete: arm-then-confirm, then the row is gone for good.
    await page.getByTestId(`game-delete-${gameId}`).click();
    await page.getByTestId(`game-delete-${gameId}`).click();
    await expect(row).toHaveCount(0, { timeout: 10000 });
  });
});
