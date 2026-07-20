/**
 * First-session trunk e2e (spec-116 Task 25 — acceptance gate 6: "a fresh
 * player reaches their first submitted action unaided"). This is the
 * spine's own acceptance evidence, not a focused unit gate — it walks
 * EVERY surface the parent design's six gates touch, end-to-end, against
 * the live stack, in the order a real first session hits them:
 *
 *   lobby codenames -> create (scenario + curated difficulty) -> Scenario
 *   Briefing (cadre-council framing, five patterns, win condition named,
 *   fixed-horizon copy) -> Begin -> cockpit at tick 0 -> verb grid honestly
 *   all-enabled at tick 0 (checked live, not assumed — see the verb-grid
 *   leg's own comment; the disabled-with-reason machinery itself is real
 *   and unchanged, it just has nothing to fire on in wayne_county yet) ->
 *   eligible verb (Campaign) -> preview
 *   (probability + cost) visible BEFORE submit -> submit succeeds ->
 *   resolve two ticks (a FORCED first crisis hard-asserted live, dedup
 *   exercised live) -> endgame_progress axes rendered honestly in the
 *   objectives tray.
 *
 * G7-crisis (spec §7 lines 267-268's "... -> first crisis -> epilogue"):
 * `endgame_reached` is the ONLY event the frontend classifies "critical"
 * (spec-116 FR-116-2's salience re-tier — crimson reserved for the endgame
 * alone) and hence the only autopause trigger, and it fires exclusively at
 * the fixed ~5200-tick century horizon (EndgameDetector recognizes the five
 * patterns but never adjudicates — owner ruling 2026-07-17). No
 * scenario/seed reaches it inside this spec's 2-tick window, so the crisis
 * leg below forces it through a real, test-only server hook
 * (`forceEndgameOnNextResolve` — see its docstring in `fixtures.ts`) that
 * reuses the exact same `EndgameEvent` construction a genuine horizon
 * termination already uses; that leg asserts nothing about the epilogue's
 * own content, only that the incidental chronicle takeover it opens can be
 * cleared. The epilogue leg (last, below) is the real horizon->UNRESOLVED
 * path instead: a SEPARATE, rigged-horizon session (`campaign_horizon_years:
 * 1, weeks_per_year: 1` — `horizon_tick` = 1, so the very first resolve
 * crosses it for real, no forced hook) reaches the genuine `EndStateScreen`
 * epilogue and pins its content + terminal-state honesty.
 *
 * G7-epilogue investigation finding (real defect, FIXED alongside this
 * leg): reaching this leg without the fix left `get_endgame_state` — and
 * therefore every `tick_event`-sourced read (journal, alerts, endgame) —
 * permanently null. Root cause: `EngineBridge.resolve_tick`'s OWN
 * `_persist_tick_events_safe` call correctly wrote the tick's real events
 * (confirmed live via a delete-audit trigger on the dev DB), but a LATER
 * call in the same `resolve_tick`, `_persist_snapshots_safe` ->
 * `PostgresRuntime.persist_full_tick`, forwarded no `events=` argument at
 * all (it only carries the six read-model snapshot tables); `persist_full_
 * tick` unconditionally passed that `None` through as `events or []` to
 * `persist_tick_events`, whose default `replace=True` DELETEs the tick's
 * existing rows before inserting — with an empty list, deleting and
 * inserting nothing wiped the real events moments after they were
 * written, on EVERY tick of EVERY session. Fixed in
 * `src/babylon/persistence/postgres_runtime/_legacy.py` (`persist_full_
 * tick` now only touches `tick_event` when its caller passes `events`
 * explicitly — `None` is honored as "nothing to say", `[]` still clears);
 * regression-pinned in `tests/unit/persistence/test_postgres_runtime.py`
 * (`TestPersistFullTickEventsHandling`).
 *
 * FOLLOW-PATTERN: `real-loop.spec.ts` (shared-session serial suite shape)
 * + `lobby-briefing.spec.ts` (the real create->briefing->begin flow) +
 * `verb-submit.spec.ts` (the real VerbGrid/TargetPicker/preview contracts).
 * Every testid/selector below is read off the actual component source
 * (`BriefingRoute.tsx`, `VerbGrid.tsx`, `VerbForm.tsx`, `TargetPicker.tsx`,
 * `EventsFeed.tsx`, `ObjectivesTracker.tsx`), not invented — this spec
 * intentionally does NOT assert a `scenario-briefing` testid (the task
 * brief's illustrative pseudocode used that name, but no such testid
 * exists anywhere in the frontend; `BriefingRoute` exposes
 * `briefing-codename`/`briefing-pattern-*`/`briefing-win-badge`/
 * `briefing-horizon`/`briefing-begin` instead — those are the real
 * contract this test pins).
 *
 * Runs on "chromium-authenticated" (registered in AUTHENTICATED_SPECS,
 * storageState from auth.setup.ts) against its OWN fresh wayne_county/
 * cadre session — never shared across spec files (game_turn enforces one
 * queued action per (session, tick, org)).
 *
 * Honest-null notes carried from verb-submit.spec.ts: Campaign is
 * snapshot-sourced (its targets are territories/hyperedges, not a live
 * endpoint response), so its TargetPicker rows never carry expected-delta
 * chips (`TargetDeltaChip` is honest-null for undefined/zero deltas) — this
 * spec does not assert delta chips are visible for that reason, matching
 * the literal acceptance-gate code in the task brief (which asserts only
 * `preview-probability` + `verb-cost`, not target-delta chips).
 */
import {
  expect,
  test,
  acknowledgeAutopauseIfPresent,
  forceEndgameOnNextResolve,
  createWayneCountyGame,
  csrfToken,
  BASE,
} from "./fixtures";

/** Session id created by the "creating an operation" test. */
let gameId = "";

test.describe("first session — fresh player trunk (spec-116 acceptance gate 6)", () => {
  test.describe.configure({ mode: "serial" });

  test("lobby shows generated operation codenames — no unnamed rows", async ({ page }) => {
    await page.goto("/lobby");
    await expect(page.getByText("New Operation")).toBeVisible({ timeout: 10000 });

    // Every listed operation row's label is the server-derived codename
    // (LobbyRoute.tsx: `label: g.codename`, two uppercase words) — never
    // blank/"undefined". Bounded by whatever the lobby actually lists
    // (statically capped so the loop is provably finite either way).
    const rows = page.locator('[data-testid^="game-option-"]');
    const rowCount = await rows.count();
    const MAX_ROWS = 200;
    for (let i = 0; i < Math.min(rowCount, MAX_ROWS); i++) {
      const label = (await rows.nth(i).locator("span").first().textContent())?.trim();
      expect(label, `lobby row ${i} must carry a real codename, not blank/undefined`).toBeTruthy();
      expect(label).not.toBe("undefined");
    }
  });

  test("creating an operation lands on the Scenario Briefing (cadre-council framing, five patterns, win condition, fixed horizon)", async ({
    page,
  }) => {
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

    // Codename + cadre-council framing.
    await expect(page.getByTestId("briefing-codename")).toHaveText(/^OPERATION [A-Z]+ [A-Z]+$/, {
      timeout: 15000,
    });
    await expect(page.getByText(/Cadre Council/)).toBeVisible();

    // Five real patterns (get_journal_objectives), win condition named.
    await expect(page.locator('[data-testid^="briefing-pattern-"]')).toHaveCount(5, {
      timeout: 15000,
    });
    await expect(page.getByTestId("briefing-win-badge")).toBeVisible();

    // Fixed-horizon framing (owner ruling): a century, not a termination condition.
    await expect(page.getByTestId("briefing-horizon")).toContainText("100 years");

    // "Begin" enters the cockpit at tick 0.
    await page.getByTestId("briefing-begin").click();
    await expect(page).toHaveURL(new RegExp(`/game/${gameId}$`), { timeout: 15000 });
    await expect(page.getByTestId("tick-value")).toHaveText("0", { timeout: 15000 });
  });

  test("verb grid: EDUCATE eligible from tick 0 (real TENANCY partition), all nine verbs enabled, no dead ends", async ({
    page,
  }) => {
    expect(gameId, "briefing test ran first").toBeTruthy();
    await page.goto(`/game/${gameId}`);
    await expect(page.getByTestId("action-composer")).toBeVisible({ timeout: 15000 });

    const verbGrid = page.getByTestId("verb-grid");
    await expect(verbGrid).toBeVisible();
    // Article V: flat 9-verb grid, nothing hidden.
    await expect(verbGrid.getByRole("button")).toHaveCount(9);

    // Tick-0 wayne_county: EDUCATE is ELIGIBLE, not disabled. This leg used
    // to assert the opposite ("no organized community in the player's
    // territories yet") — that expectation encoded the retired
    // `territory_ids`-on-social_class fabricated-shape bug. Evidence
    // (verified by a prior agent, cited rather than re-derived): commit
    // 4fa5d45c (Track 1 Task 8b) fixed `get_verb_eligibility`'s
    // `has_social_class` predicate (and `get_educate_targets`) to resolve
    // class -> territory via the real Occupant -> Territory TENANCY edge
    // (`_tenancy_members_by_territory` in `web/game/engine_bridge.py`), not
    // the nonexistent `territory_ids` field on social_class nodes — pinned
    // by its own regression test
    // `TestVerbEligibilityAgreesWithTargetsRealWayneCounty`. wayne_county's
    // map is 100% class-partitioned from scenario construction
    // (`_legacy_wayne.py`), so a resident social_class already tenants the
    // player's starting territories from tick 0 BY DESIGN. EDUCATE enabled
    // at tick 0 is the correct, current behavior.
    const educate = verbGrid.getByRole("button", { name: /educate/i });
    await expect(educate).toBeEnabled({ timeout: 15000 });

    // Disabled-with-reason contract (spec-116 FR-4.8) — checked live, not
    // assumed: every verb's eligibility predicate in `get_verb_eligibility`
    // (`web/game/engine_bridge.py`) was read, and the real
    // `GET .../actions/eligibility/?org_id=ORG001` payload was queried
    // against a fresh wayne_county session at tick 0 — all nine verbs come
    // back `eligible: true` (ORG001 starts with its own territories for
    // investigate/campaign/move; the seeded Detroit-periphery state
    // apparatus and QCEW businesses already share those territories for
    // aid/attack/mobilize/negotiate; reproduce always targets the org
    // itself). No verb is genuinely ineligible in wayne_county at tick 0
    // today, so this leg does not fabricate a disabled-verb assertion — it
    // pins the honest live state instead: every verb renders enabled
    // (including Campaign, the verb this trunk test submits below) and the
    // ineligible-reasons list stays absent, the same "never a fabricated
    // disabled state" contract VerbGrid.tsx's own honest-null comment
    // names, exercised from the other direction.
    for (const label of [
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
      await expect(verbGrid.getByRole("button", { name: new RegExp(label, "i") })).toBeEnabled();
    }
    await expect(page.getByTestId("verb-ineligible-reasons")).toHaveCount(0);
  });

  test("Campaign: target picker renders, preview visible before submit, submit succeeds", async ({
    page,
  }) => {
    expect(gameId, "briefing test ran first").toBeTruthy();
    await page.goto(`/game/${gameId}`);

    await page
      .getByTestId("verb-grid")
      .getByRole("button", { name: /campaign/i })
      .click();

    const targetPicker = page.getByTestId("target-picker");
    await expect(targetPicker).toBeVisible({ timeout: 10000 });
    await targetPicker.getByRole("button").first().click();

    // Acceptance gate 5 (spec-116): preview visible BEFORE every submit —
    // the probability line and cost line (Task 17's surfaces). Campaign's
    // per-target delta chips are honest-null at tick 0 (see file header),
    // so they are deliberately not asserted here.
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
    await expect(page.getByTestId("pending-actions")).toBeVisible({ timeout: 10000 });
  });

  test("resolving two ticks: a forced first crisis autopauses and is acknowledged live, no consecutive identical event cards, endgame_progress axes render honestly", async ({
    page,
  }) => {
    expect(gameId, "submit test ran first").toBeTruthy();
    await page.goto(`/game/${gameId}`);
    await expect(page.getByTestId("tick-value")).toHaveText("0", { timeout: 15000 });

    // Resolve tick 0 -> 1, forcing a real endgame_reached via the G7-crisis
    // test-only hook (see forceEndgameOnNextResolve's docstring) — the spec
    // §7 "first crisis" leg, deterministic and asserted, not tolerated.
    await forceEndgameOnNextResolve(page);
    const stepButton = page.getByRole("button", { name: "Step" });
    await expect(stepButton).toBeEnabled({ timeout: 10000 });
    await Promise.all([
      page.waitForResponse(
        (r) => r.url().includes(`/api/games/${gameId}/resolve/`) && r.request().method() === "POST",
        { timeout: 30000 },
      ),
      stepButton.click(),
    ]);
    await expect(page.getByTestId("tick-value")).toHaveText("1", { timeout: 15000 });

    // Acceptance gate 3, HARD-asserted: the forced critical event actually
    // autopauses the sim (not "if present" — it must be present).
    await expect(page.getByTestId("time-status")).toHaveText("AUTOPAUSED", { timeout: 15000 });
    await expect(page.getByTestId("critical-event-modal")).toBeVisible();

    // endgame_reached also flips panels.endgame.data.outcome null -> non-null
    // on this SAME tick (worldSlice.onTickAdvanced's
    // maybeOpenChronicleOnEndgame), auto-opening the chronicle takeover
    // (z-50) on top of the modal (chrome layer, z-20) — an unavoidable side
    // effect of the only event type the frontend currently classifies
    // "critical" (spec-116 FR-116-2). The epilogue leg is out of scope here
    // (a separate later task) — this only clears the incidental overlay so
    // the modal underneath is reachable again; nothing about the
    // takeover's own content is asserted.
    const takeover = page.getByTestId("takeover-overlay");
    if ((await takeover.count()) > 0) {
      await page.getByTestId("takeover-close").click();
    }

    await page.getByTestId("autopause-resume").click();
    await expect(page.getByTestId("time-status")).toHaveText("PAUSED", { timeout: 10000 });
    await expect(page.getByTestId("critical-event-modal")).toHaveCount(0);

    // Resolve tick 1 -> 2 (no forced crisis this time — the real engine's
    // own dynamics govern it, so the tolerant helper stays the right tool).
    await expect(stepButton).toBeEnabled({ timeout: 10000 });
    await Promise.all([
      page.waitForResponse(
        (r) => r.url().includes(`/api/games/${gameId}/resolve/`) && r.request().method() === "POST",
        { timeout: 30000 },
      ),
      stepButton.click(),
    ]);
    await expect(page.getByTestId("tick-value")).toHaveText("2", { timeout: 15000 });
    await acknowledgeAutopauseIfPresent(page);

    // EventTray/EventsFeed: never blank (honest empty copy or real cards).
    await expect(page.getByTestId("event-tray")).toBeVisible({ timeout: 15000 });
    const feed = page.getByTestId("events-feed");
    await expect(feed).toBeVisible({ timeout: 10000 });
    await expect(feed).not.toBeEmpty({ timeout: 5000 });

    // Acceptance gate 2, exercised live against the real dedup output: no two
    // CONSECUTIVE rendered cards share the same dedup KEY `${type}:${subject}`
    // (dedupeEvents collapses same-(type,subject) runs into one card + count —
    // see eventDedup.ts + EventsFeed.tsx's data-dedup-key). This is the ACTUAL
    // contract: two adjacent same-TYPE / different-SUBJECT cards (e.g.
    // dispossession in county 26163 then 26099) are CORRECT and expected — the
    // sibling unit test EventsFeed.test.tsx pins exactly that — so asserting on
    // type alone would false-fail on any real multi-territory feed. wayne_county's
    // 81 territories fire lifecycle/inheritance events once PER TERRITORY per
    // tick (a real, large card count — reports/pacing-calibration-2026-07-17.md
    // §5), so this reads every card's key in ONE batched call rather than an
    // N-await loop (which timed out against the real event volume). The slice is
    // a static upper bound on the iterated array (repo loop-bound rule); the
    // comparison is synchronous JS, not per-item network round trips.
    const dedupKeys = (
      await feed
        .locator("[data-dedup-key]")
        .evaluateAll((els) => els.map((el) => el.getAttribute("data-dedup-key") ?? ""))
    ).slice(0, 1000);
    expect(dedupKeys.length, "the live feed rendered real event cards").toBeGreaterThan(0);
    for (let i = 1; i < dedupKeys.length; i++) {
      expect(
        dedupKeys[i],
        "no two consecutive cards share a ${type}:${subject} dedup key (acceptance gate 2)",
      ).not.toBe(dedupKeys[i - 1]);
    }

    // Acceptance gate 6's last leg: endgame_progress axes render in the
    // objectives tray (always mounted in AppShell) as five real objective
    // cards fed by get_journal_objectives — never pinned at a fabricated
    // 1.00 two ticks in.
    await expect(page.getByTestId("objectives-tray")).toBeVisible({ timeout: 10000 });
    const progressValues = page.locator(".objective-progress-value");
    await expect(progressValues).toHaveCount(5, { timeout: 10000 });
    const values = await progressValues.allTextContents();
    for (const v of values) {
      expect(v, "no endgame_progress axis may be pinned at 1.00 two ticks in").not.toBe("1.00");
    }
  });

  test("epilogue: a real horizon termination renders the UNRESOLVED epilogue and the outcome is a genuine terminal state", async ({
    page,
  }) => {
    // Measured cost: one real /resolve/ call on this rigged session took
    // ~14-15s live; 90s leaves ample margin for that plus rendering/polling
    // (no other spec file in e2e/ sets test.setTimeout — the Playwright
    // default is 30s, too tight for a real engine step).
    test.setTimeout(90_000);

    // A SECOND, independent session via the API fixture (never through
    // lobby/briefing — leg 2 above drives the real create->briefing flow
    // and asserts `briefing-horizon` contains "100 years" on an UN-rigged
    // session; that assertion must keep passing, so this leg's rigged
    // defines override never touches it). `defines` is the officially
    // supported `CreateGameSerializer` field (`web/game/serializers.py`) ->
    // `GameDefines(**(defines or {}))` in `EngineBridge.create_game`
    // (`engine_bridge.py:2261-2299`), persisted per-session and re-read
    // every tick via `_fetch_session_game_defines`.
    //
    // `weeks_per_year` is NOT display-only — it feeds real sim dynamics
    // (checked before overriding it: `production.py`/`economic.py` divide
    // annual labor-power/wage-rate/extraction-efficiency by it every tick,
    // `phi_distribution.py` divides the annual Φ inflow by it). Overriding
    // it to 1 for this ONE rigged, deterministic, e2e-only session is the
    // documented trade the brief authorizes ("acceptable — fabricating the
    // epilogue payload is NOT"): `horizon_tick = campaign_horizon_years(1)
    // * weeks_per_year(1) = 1`, so the very first resolve crosses the
    // fixed-horizon gate for real (`engine_bridge.py:5535-5537`) — no
    // forced test hook, the same `EndgameEvent` construction a genuine
    // ~5200-tick campaign uses. Verified live (a single real resolve on
    // this exact override produced a normal ~250-event tick, no engine
    // errors) before relying on it here.
    const epilogueGameId = await createWayneCountyGame(page, {
      endgame: { campaign_horizon_years: 1 },
      timescale: { weeks_per_year: 1 },
    });
    expect(epilogueGameId, "the rigged-horizon session must be created").toBeTruthy();

    await page.goto(`/game/${epilogueGameId}`);
    await expect(page.getByTestId("tick-value")).toHaveText("0", { timeout: 15000 });

    const stepButton = page.getByRole("button", { name: "Step" });
    await expect(stepButton).toBeEnabled({ timeout: 10000 });
    await Promise.all([
      page.waitForResponse(
        (r) =>
          r.url().includes(`/api/games/${epilogueGameId}/resolve/`) &&
          r.request().method() === "POST",
        { timeout: 30000 },
      ),
      stepButton.click(),
    ]);
    await expect(page.getByTestId("tick-value")).toHaveText("1", { timeout: 15000 });

    // endgame_reached is real here (not the crisis leg's forced hook), so
    // the SAME "critical" autopause machinery fires — verified live: on
    // this exact rigged session, `time-status` reaches AUTOPAUSED, the
    // critical-event-modal mounts, and (per FR-116-4.2's null->non-null
    // outcome transition) the chronicle takeover auto-opens UNDERNEATH it
    // (z-50 over the modal's z-20) with the real EndStateScreen content —
    // this leg asserts that content directly rather than dismissing it.
    const endState = page.getByTestId("end-state");
    await expect(endState).toBeVisible({ timeout: 15000 });
    await expect(endState).toHaveAttribute("data-outcome", "unresolved");
    await expect(endState).toHaveClass(/end-state--unresolved/);

    // Exact copy from web/game/epilogues.py's "unresolved" entry — the
    // real horizon->UNRESOLVED epilogue, not a fabricated stand-in.
    await expect(page.getByRole("heading", { name: "THE STRUGGLE CONTINUES" })).toBeVisible();
    await expect(page.locator(".end-state-epilogue-body")).toHaveText(
      "One hundred years, and no verdict. The contradiction did not resolve; it deepened, " +
        "changed terrain, and outlived every administration that claimed to manage it. " +
        "History does not end because the observation window closes. The line holds where " +
        "you built it; the rest belongs to the next century, and to whoever organizes it.",
    );

    // Real terminal-state verification (checked live, not assumed): the
    // backend has no session-status gate that refuses a further
    // `/resolve/` once horizon_tick is crossed (`session.status` stays
    // "active"), so a direct API call still returns 200 and the tick
    // keeps advancing underneath. What IS genuinely terminal: (a) the UI's
    // own Step control is disabled the moment AUTOPAUSED lands (`Time
    // Controls.tsx`'s `disabled={!isPaused}` — the player cannot advance
    // further without an explicit Resume), and (b) the PERSISTED epilogue
    // itself never changes — `get_endgame_state`'s `_fetch_endgame_event_
    // row` reads the FIRST `ENDGAME_REACHED` row
    // (`ORDER BY tick ASC LIMIT 1`), so the outcome/headline/epilogue/tick
    // this leg already asserted above stay byte-identical no matter how
    // many further ticks resolve. Both are asserted directly rather than
    // fabricating a "resolve was refused" claim the app does not make.
    await expect(page.getByTestId("time-status")).toHaveText("AUTOPAUSED", { timeout: 10000 });
    await expect(stepButton).toBeDisabled();

    const endgameBefore = await (
      await page.request.get(`${BASE}/api/games/${epilogueGameId}/endgame/`)
    ).json();

    const furtherResolve = await page.request.post(`${BASE}/api/games/${epilogueGameId}/resolve/`, {
      data: {},
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": await csrfToken(page),
        Referer: `${BASE}/`,
      },
    });
    expect(
      furtherResolve.status(),
      "the backend has no game_over refusal gate — a further resolve succeeds",
    ).toBe(200);

    const endgameAfter = await (
      await page.request.get(`${BASE}/api/games/${epilogueGameId}/endgame/`)
    ).json();
    expect(
      endgameAfter.data,
      "the persisted epilogue is a genuine terminal state — immutable across further ticks",
    ).toEqual(endgameBefore.data);
  });
});
