# Implementation Brief — feat/frontend-live-verbs (P0 #4 + 5th P0 + 3 Vitest failures)

Scouted at `chore/test-infra-rearm` = dev @ 9101dddf. All paths absolute. All line numbers verified 2026-07-08.

## 0. Problem statement (verified)

1. **P0 #4 — wrong payload shape**: `VerbPage.handleSubmit` (`/home/user/projects/game/babylon/web/frontend/src/components/pages/VerbPage.tsx:221-234`) submits:
   ```ts
   await submitAction(gameId, {
     verb: verb!.verb,
     org_id: activeOrgFallback,
     target_id: selected.id,
     ...paramVals,        // flat V2 mock params: {method:"Study Circle", intensity:3, ...}
   });
   ```
   Every live verb endpoint validates a different shape (see contract table §2) — **all 9 verbs 400** (`Validation failed` / `ACTION_INVALID_PARAMS`).
2. **5th P0 — fixture targets**: `VerbPage.tsx:215` `const targets = resolveTargets(verb.target_type);` — `resolveTargets` (`src/lib/verb-config.ts:36-155`) reads `ORGS, TERRITORIES, COMMUNITIES, EDGES` imported from **the fixture file** `src/fixtures/v2-mock-data.ts` (import at `verb-config.ts:9-17`). Selected target IDs are mock IDs the engine has never heard of.
3. **Dead live plumbing already exists** (built, never wired):
   - `gameStore.fetchVerbTargets` — `src/stores/gameStore.ts:205-223` (declared line 94; cache `verbTargets` line 86/109; `invalidateVerbTargets` lines 225-227, called from `resolveTick` line 185). **Zero production callers** — only `src/stores/gameStore.test.ts:65,86` exercise it.
   - `src/lib/verbs/` — a complete per-verb registry, imported **only** by its own test (`src/lib/verbs/__tests__/verbs.test.ts:6`). Inventory in §3.
4. **3 deterministic Vitest failures** — all in `src/components/pages/__tests__/tick-resolution-page.test.tsx`; root cause diagnosed in §5 (test-harness race, NOT missing UI behavior — the spec-092 severity classifier logic is already implemented in `TickResolutionPage.tsx:40-86`).

---

## 1. Verified seams (quotes)

### 1a. `gameStore.ts` — dead action + typing gap
`/home/user/projects/game/babylon/web/frontend/src/stores/gameStore.ts`
```ts
 86:  verbTargets: Record<string, unknown>;                      // <-- typing gap
 94:  fetchVerbTargets: (gameId: string, verb: PlayerVerb, orgId: string) => Promise<void>;

205:  fetchVerbTargets: async (gameId, verb, orgId) => {
206:    const cacheKey = `${verb}:${orgId}`;
208:    const res = await apiGet<Record<string, unknown>>(
209:      `/api/games/${gameId}/actions/${verb}/targets/?org_id=${orgId}`,
211:    if (res.status === "ok") {                                // <-- breaks on mobilize, see §2 note
215:      const payload = res.data ?? res;
216:      set((s) => ({
217:        verbTargets: { ...s.verbTargets, [cacheKey]: payload },
```
**Bug found while scouting**: `MobilizeAvailableSerializer` (`web/game/serializers.py:842-848`) has **no `status` field** (fields: `entity_id, name, available_sl, available_cl, mobilize_cost_cl, targets`). The API client (`src/api/client.ts:31-81`) passes the body through untouched for HTTP 200, so `res.status` is `undefined` for mobilize and the store drops the response into the error branch. Fix: `if (res.status !== "error")`.

### 1b. `src/lib/verbs/` — dead registry (13 files, 452 LOC)
| File | Export | Key facts |
|---|---|---|
| `types.ts` (54 ln) | `VerbTarget {id,label,group?}`, `ParamField {key,label,type:"number"\|"select"\|"text",defaultValue,options?,min?,max?}`, `VerbConfig {verb,label,description,parseTargets(raw),paramFields,targetPayloadKey?,predictedEffect?}` | No `buildPayload` yet — must be added |
| `registry.ts` (29 ln) | `VERB_REGISTRY: Record<string,VerbConfig>` (all 9), `VERB_NAMES` | |
| `index.ts` (6 ln) | re-exports types + registry | |
| `educate.ts` | `educateConfig` — `targetPayloadKey: "target_community_id"` (line 15); parses `raw.targets[].community_id/territory_name/category/credibility`; `paramFields: []` | Matches live GET + POST contract |
| `aid.ts` | `aidConfig` — parses `raw.population_targets` + `raw.org_targets`; paramField `transfer_amount` (number) | Matches; **payload must nest** `params.transfer_amount` |
| `attack.ts` | `attackConfig` — parses `raw.targets.organizations/.institutions` (`target_id`,`name`); paramField `mode` select `targeted|mass` | Backend also returns `targets.edges` (serializers.py:750-753) — not parsed (add) |
| `mobilize.ts` | `mobilizeConfig` — parses flat `raw.targets[].id/name`; paramField `sl_committed` | Matches `MobilizeTargetSerializer` (id,name @831-833) |
| `campaign.ts` | `campaignConfig` — generic parse; `paramFields: []` | **Wrong**: needs `campaign_type` select + FLAT payload + snapshot-sourced targets (no GET endpoint, §2) |
| `move.ts`/`investigate.ts`/`negotiate.ts` | generic parse; `paramFields: []` | investigate parse is wrong (backend returns `targets.{territory_scans,targeted_scans,counter_intelligence}`, serializers.py:964-967); all 3 verbs are UI-disabled anyway |
| `reproduce.ts` (9 ln) | `parseTargets: () => []`; `paramFields: []` | Backend GET returns self-target list (`ReproduceTargetSerializer` target_id/name/type @885-890); submit `target_id` optional |
| `__tests__/verbs.test.ts` (131 ln) | registry completeness + parseTargets for educate/aid/attack/mobilize/reproduce + paramFields | Passing; extend, don't rewrite |

### 1c. VerbPage fixture pipeline
`src/components/pages/VerbPage.tsx:11` `import { DISABLED_VERBS, SUPPORTED_VERBS, getVerbParams, resolveTargets } from "@/lib/verb-config";` → `verb-config.ts:9-17` imports `ORGS, TERRITORIES, COMMUNITIES, EDGES, VERBS, CLASS_COLORS, EDGE_COLORS` **from `@/fixtures/v2-mock-data`** (the fixture file; its own header at v2-mock-data.ts:6 admits it feeds "the verb-target catalog in lib/verb-config.ts"). `verb-config.ts:26` `DISABLED_VERBS = new Set(["investigate","move","negotiate"])` (spec 061 FR-025) — **keep**. `getVerbParams` (`verb-config.ts:160-303`) is the mock V2 param schema ("Study Circle", sliders in CL/SL units) — display labels never translated to backend enums; replaced by `ParamField`s.

### 1d. Verb metadata that must survive
`src/fixtures/v2-mock-data.ts:370-443` `export const VERBS: V2Verb[]` — 9 entries `{verb,label,glyph,target_type,cost_label,desc}`. This is static Article-V metadata living in a fixture file; move it into `src/lib/verb-config.ts` so lib no longer imports fixtures (keep `export { VERBS }` shape; `v2-types.ts:100-126` has `V2Verb`, `V2VerbKey`, `V2TargetType`).

---

## 2. Backend contract — verb → required POST body (all verified against live URL routing)

URL routing `web/game/urls.py:112-196`: every verb has `games/<id>/actions/<verb>/` (POST submit) and `games/<id>/actions/<verb>/targets/` (GET) — **except campaign's "targets" route points at the submit view**. 8 of 9 verbs are standalone `APIView`s in `web/game/api.py` (Educate@1229, Aid@1294, Attack@1359, Mobilize@1424, Move@1496, Investigate@1561, Reproduce@1626, Negotiate@1691). Only **campaign** uses `BaseVerbActionView` (api.py:1118, subclass `CampaignActionView` api.py:1489-1493) — which defines **only `post`** (verified: single `def post` in 1118-1226) → **`GET /actions/campaign/targets/` = 405**, and `engine_bridge.py` has no `get_campaign_targets` (only 8 `get_*_targets`, lines 2247-2839).

DRF note: a nested `Serializer()` field without `required=False` is **required** — so `params` is mandatory everywhere below except educate.

| verb | serializer (web/game/serializers.py) | required body | optional | enum values |
|---|---|---|---|---|
| **educate** | `EducateSubmitSerializer` :512-515 | `org_id`, **`target_community_id`** | `params` (DictField, default `{}`) | — |
| **aid** | `AidSubmitSerializer` :538-541 | `org_id`, `target_id`, `params:{transfer_amount: float}` (:534-535) | — | — |
| **attack** | `AttackSubmitSerializer` :84-89 | `org_id`, `params:{mode}` (:79-81) | `target_id` (null ok), `params.specific_target` | mode: `targeted`\|`mass` |
| **mobilize** | `MobilizeSubmitSerializer` :772-777 | `org_id`, `target_id`, `params:{sl_committed: float}` (:768-769) | — | — |
| **campaign** | `CampaignActionSerializer` :95-100 (extends `BaseActionSerializer` :43-51) | `org_id`, `target_id`, **`campaign_type`** — **FLAT, no params nesting** | — | `ELECTORAL`\|`LEGISLATIVE`\|`PUBLIC_PRESSURE` |
| **move** | `MoveSubmitSerializer` :1048-1051 | `org_id`, `target_id`, `params:{mode}` (:1044-1045) | — | mode: `expand`\|`relocate` |
| **investigate** | `InvestigateSubmitSerializer` :991-994 | `org_id`, `params:{scan_type}` (:985-988) | `target_id` (null ok) | scan_type: `territory_scan`\|`targeted_scan`\|`counter_intelligence` |
| **reproduce** | `ReproduceSubmitSerializer` :908-911 | `org_id`, `params:{mode}` (:902-905) | `target_id` (null ok), `params.cl_committed`, `params.sl_committed` (floats, null ok) | mode: `cadre_training`\|`mass_recruitment` |
| **negotiate** | `NegotiateSubmitSerializer` :1119-1122 | `org_id`, `target_id`, `params:{proposal}` (:1107-1116) | — | proposal: `coordination_pact`\|`resource_sharing`\|`ceasefire`\|`demand_policy_change`\|`reconciliation` |

Campaign is also the only verb whose extra field travels flat because `BaseVerbActionView.post` (api.py:1158-1161) strips `_COMMON_FIELDS = {"org_id","target_id"}` (api.py:1115) and forwards the remainder as `params_json` itself; and the only one that (a) scopes the session to `request.user` (`_get_session_or_none` api.py:1096-1106) and (b) requires `session.status == "active"` (api.py:1139-1143).

Targets-GET responses are **flat** (no `{status,data}` envelope): views return `Response(serializer.data)` directly; e.g. `EducateAvailableSerializer` :502-509 (`status,tick,verb,acting_org,cost,targets[],unavailable_communities[]`), `EducateTargetSerializer` :441-452 (`community_id, community_type, category, territory_name, territory_id, credibility, ...`). This is why `fetchVerbTargets` stores `res.data ?? res` (gameStore.ts:212-215). MSW mock `src/mocks/educate_targets.json` mirrors the flat shape.

---

## 3. Implementation steps

Work under `web/frontend/` unless noted. Order = TDD: steps marked **[RED]** write failing tests first.

### Step 1 — `buildPayload` on VerbConfig **[RED first: see Tests §4-T1]**
`src/lib/verbs/types.ts` — extend `VerbConfig` (after `paramFields`, before `targetPayloadKey`; keep RST-ish doc-comment style of the file):
```ts
  /** Whether a target selection is required before submit (default true). */
  targetRequired?: boolean;
  /** Where eligible targets come from: the live per-verb GET endpoint, or the
   *  snapshot (campaign has no targets endpoint — GET returns 405). */
  targetsSource?: "endpoint" | "snapshot";
  /** Build the POST body for /api/games/{id}/actions/{verb}/ (verb rides in the URL). */
  buildPayload: (orgId: string, targetId: string | null, params: Record<string, unknown>) => Record<string, unknown>;
```
Per-verb additions (each in its own file, matching surrounding style):
```ts
// educate.ts
buildPayload: (orgId, targetId, params) => ({
  org_id: orgId,
  target_community_id: targetId ?? "",
  params,
}),
// aid.ts
buildPayload: (orgId, targetId, params) => ({
  org_id: orgId,
  target_id: targetId ?? "",
  params: { transfer_amount: Number(params.transfer_amount ?? 0) },
}),
// attack.ts
buildPayload: (orgId, targetId, params) => ({
  org_id: orgId,
  target_id: targetId,
  params: { mode: String(params.mode ?? "targeted") },
}),
// mobilize.ts
buildPayload: (orgId, targetId, params) => ({
  org_id: orgId,
  target_id: targetId ?? "",
  params: { sl_committed: Number(params.sl_committed ?? 0) },
}),
// campaign.ts — FLAT (BaseVerbActionView contract)
targetsSource: "snapshot",
paramFields: [{
  key: "campaign_type", label: "Campaign Type", type: "select",
  defaultValue: "PUBLIC_PRESSURE",
  options: [
    { value: "ELECTORAL", label: "Electoral" },
    { value: "LEGISLATIVE", label: "Legislative" },
    { value: "PUBLIC_PRESSURE", label: "Public Pressure" },
  ],
}],
buildPayload: (orgId, targetId, params) => ({
  org_id: orgId,
  target_id: targetId ?? "",
  campaign_type: String(params.campaign_type ?? "PUBLIC_PRESSURE"),
}),
// reproduce.ts
targetRequired: false,
paramFields: [
  { key: "mode", label: "Mode", type: "select", defaultValue: "cadre_training",
    options: [
      { value: "cadre_training", label: "Cadre Training" },
      { value: "mass_recruitment", label: "Mass Recruitment" },
    ] },
  { key: "cl_committed", label: "Cadre Labor Committed", type: "number", defaultValue: 0, min: 0 },
  { key: "sl_committed", label: "Sympathizer Labor Committed", type: "number", defaultValue: 0, min: 0 },
],
buildPayload: (orgId, targetId, params) => ({
  org_id: orgId,
  ...(targetId ? { target_id: targetId } : {}),
  params: {
    mode: String(params.mode ?? "cadre_training"),
    cl_committed: Number(params.cl_committed ?? 0),
    sl_committed: Number(params.sl_committed ?? 0),
  },
}),
// move.ts / investigate.ts / negotiate.ts — same pattern:
//   move:        params:{ mode: "expand"|"relocate" }           + paramFields select
//   investigate: params:{ scan_type: "territory_scan"|... }     + paramFields select; target optional
//   negotiate:   params:{ proposal: "coordination_pact"|... }   + paramFields select
```
(These three stay UI-disabled via `DISABLED_VERBS`, but their builders + tests ship now so enabling them later is a one-line set change.)
Also fix `attack.ts` `parseTargets` to include the `edges` group (`AttackTargetEdgeModelSerializer` :726-733 — `target_id`, `edge_description`); fix `investigate.ts` to parse `raw.targets.territory_scans/.targeted_scans`; optionally have `reproduce.ts` parse the self-target list (`raw.targets[].target_id/name`).

### Step 2 — Store fixes **[RED first: §4-T2]**
`src/stores/gameStore.ts`:
- Line 86: `verbTargets: Record<string, unknown>;` → `verbTargets: Record<string, Record<string, unknown>>;`
- Line 211: `if (res.status === "ok") {` → `if (res.status !== "error") {` (mobilize's flat body has no `status`; client only synthesizes `status:"error"` on failures — client.ts:48-73).
- Line 215: `const payload = res.data ?? res;` → `const payload = (res.data ?? res) as Record<string, unknown>;`
- `src/types/game.ts:373-379` — `SubmitActionParams.target_id: string` → `target_id?: string;` (educate submits `target_community_id`; reproduce may omit target). No other production writers: only `VerbPage.tsx:225` and tests build this type.

### Step 3 — Wire VerbPage (the core change)
`src/components/pages/VerbPage.tsx`. Preserve the hooks-before-early-return discipline noted at lines 184-185 (react-hooks/rules-of-hooks — this page was burned before).
1. Imports: drop `getVerbParams, resolveTargets` from the line-11 import (keep `DISABLED_VERBS, SUPPORTED_VERBS`); add `import { VERB_REGISTRY } from "@/lib/verbs"; import type { ParamField, VerbTarget } from "@/lib/verbs";`
2. Before the early return (all unconditional):
```ts
const config = verb ? VERB_REGISTRY[verb.verb] : undefined;
const fetchVerbTargets = useGameStore((s) => s.fetchVerbTargets);
const verbTargets = useGameStore((s) => s.verbTargets);
const cacheKey = verb ? `${verb.verb}:${activeOrgFallback}` : "";
useEffect(() => {
  if (!gameId || !verb || !activeOrgFallback) return;
  if ((config?.targetsSource ?? "endpoint") !== "endpoint") return;
  if (verbTargets[cacheKey]) return; // cache hit; resolveTick() invalidates per tick
  void fetchVerbTargets(gameId, verb.verb as PlayerVerb, activeOrgFallback);
}, [gameId, verb, activeOrgFallback, cacheKey, config, verbTargets, fetchVerbTargets]);
const targets: VerbTarget[] = useMemo(() => {
  if (!verb || !config) return [];
  if (config.targetsSource === "snapshot") {
    return [
      ...(snapshot?.territories ?? []).map((t) => ({ id: t.id, label: t.name, group: "Territories" })),
      ...(snapshot?.hyperedges ?? []).map((h) => ({ id: h.id, label: h.label, group: "Communities" })),
    ];
  }
  const raw = verbTargets[cacheKey];
  return raw ? config.parseTargets(raw) : [];
}, [verb, config, snapshot, verbTargets, cacheKey]);
```
3. Params: replace `getVerbParams(...)` (line 190) with `const params = config?.paramFields ?? [];` and re-key `paramVals` init (line 198-200) on `defaultValue`. Rewrite `ParamControl` (lines 294-339) to render `ParamField`: `select` → the existing radio-chip row using `opt.label` for display and `onChange(param.key, opt.value)` (**this is the label→enum translation — display labels never enter the payload**); `number` → keep the range input honoring `min`/`max`; `text` → styled `<input type="text">`. Delete `V2VerbParam` usage from this file.
4. Target list: `TargetListPanel`/`TRow` (lines 78-128, 383-409) currently render `V2ResolvedTarget` (color/telemetry/sub). Map `VerbTarget` → row display (`type` chip from `group ?? verb.target_type`, neutral `#787878` color, empty telemetry) or simplify TRow to id/label/group — either way remove the `V2ResolvedTarget` import.
5. Submit (lines 221-234):
```ts
async function handleSubmit(): Promise<void> {
  if (!gameId || !activeOrgFallback || !config) return;
  if ((config.targetRequired ?? true) && !selected) return;
  setSubmitting(true);
  try {
    await submitAction(gameId, {
      verb: verb!.verb as PlayerVerb,
      ...config.buildPayload(activeOrgFallback, selected?.id ?? null, paramVals),
    });
  } finally {
    setSubmitting(false);
  }
}
```
   and `canSubmit={Boolean(activeOrgFallback && (selected || !(config?.targetRequired ?? true)))}`.
6. Empty-target UX: when `targets.length === 0` and the fetch errored (`useGameStore((s) => s.error)`), surface the store error string instead of the bare "No eligible targets."

### Step 4 — Fixture decoupling
- Move the `VERBS` array (v2-mock-data.ts:370-443) into `src/lib/verb-config.ts` verbatim (typed `V2Verb[]`); delete `export { VERBS }` re-export at verb-config.ts:19 in favor of the local const; delete `resolveTargets` (:36-155) and `getVerbParams` (:160-303); delete the fixture import block (:9-17). Leave `VERBS` also exported from v2-mock-data only if something else imports it — verified: **nothing else does** (only verb-config.ts:14 and verb-config.test.ts via re-export), so remove it from v2-mock-data or leave as dead data per "don't delete pre-existing dead code" — recommended: remove from the import list only; do not touch the rest of v2-mock-data (other fixtures still feed seed helpers).
- `src/lib/__tests__/verb-config.test.ts` (126 ln): delete the `resolveTargets` describe blocks (:13-76) and `getVerbParams` assertions; keep/port the VERBS-completeness invariant (9 verbs, unique keys, every `target_type` valid).
- `src/components/pages/__tests__/pages-v2.test.tsx:156-165` assert fixture strings ("Dearborn Proletarian Workers" from COMMUNITIES, "Study Circle" from getVerbParams) — rewrite: seed store (`seedGameStore`), let MSW's educate-targets handler (`src/test/handlers.ts:327-329` → `src/mocks/educate_targets.json`, targets `comm-1` "Downtown Detroit…", `comm-2` "Dearborn Assembly…") drive the list; assert "Downtown Detroit" renders and the new param control labels.

### Step 5 — Fix the 3 Vitest failures (deterministic, one root cause)
Failing (verified by run, and they fail in file-isolation too):
```
src/components/pages/__tests__/tick-resolution-page.test.tsx
  × reveals the first severity step immediately, not the state-response step   (line 72)
  × shows 'no changes' state when the tick had no events and no alerts         (line 133)
  × buckets a real lowercase EventType by its own severity ... (spec 092 Defect B) (line 163)
```
**Diagnosis** (important — do NOT touch TickResolutionPage severity logic; it is already correct at `TickResolutionPage.tsx:40-86`): the error is jest-dom's `element could not be found in the document` from `.toBeInTheDocument()` — i.e. `findByText` **resolved** against the seeded render, then the node **detached**. `TickResolutionPage` calls `useGameState(gameId)` (`src/hooks/useGameState.ts:47-62`) which fires `fetchState("g1")` on mount; MSW's default handler (`src/test/handlers.ts:293-298`) answers with the module-level `mockState` (= `makeWayneCountySnapshot()`, handlers.ts:17), which **clobbers the seeded snapshot** (`gameStore.fetchState` sets `snapshot: snap` at gameStore.ts:133) and re-renders away the asserted line (~150 ms in). The 3 passing siblings survive only because they never assert on the pre-clobber node (they `await` it bare, or assert post-clobber content that exists under mockState + default alerts too).
**Fix** — pin the state endpoint to the seed, in `src/__tests__/helpers/seedSnapshot.ts:136-138`:
```ts
import { http, HttpResponse } from "msw";
import { server } from "@/test/server";
...
export function seedGameStore(snapshot: GameSnapshot = SEEDED_SNAPSHOT): void {
  useGameStore.setState({ snapshot, loading: false, error: null });
  // useGameState fires fetchState on mount; without this override the default
  // handler's mockState clobbers the seed mid-test (detached-node failures).
  server.use(
    http.get("/api/games/:id/state/", () => HttpResponse.json({ status: "ok", data: snapshot })),
  );
}
```
`server.resetHandlers()` runs in the global `afterEach` (`src/test/setup.ts:104`), so the override is per-test. Other `seedGameStore` users (`pages-v2`, `intel-v2`, `tick-resolution.test.tsx` integration, `TerritoryDetailView`, `OrgDetailView`) assert seeded content and only get *more* deterministic — but run the full suite; if `src/__tests__/integration/tick-resolution.test.tsx` depends on post-resolve `mockState.tick` advancing, give `seedGameStore` an opt-out flag (`seedGameStore(snap, { pinStateEndpoint: false })`) rather than reverting. No test-file edits needed for the 3 failures themselves.

---

## 4. Tests (TDD — write RED first)

No skipped tests exist to un-skip (`rg "\.skip\(|it\.todo" src` → none). Existing coverage: `lib/verbs/__tests__/verbs.test.ts` (registry+parseTargets, passing), `gameStore.test.ts:55-92` (fetchVerbTargets cache), `pages-v2.test.tsx:134-171` (VerbPage, fixture-coupled — rewrite per Step 4), `tick-resolution-page.test.tsx` (3 RED now, GREEN after Step 5).

**T1 [RED] `src/lib/verbs/__tests__/payloads.test.ts`** — table-driven, one case per verb, asserting the **exact** §2 body:
```ts
import { describe, it, expect } from "vitest";
import { VERB_REGISTRY } from "@/lib/verbs";

describe("buildPayload — serializer contracts", () => {
  it("educate: target under target_community_id, params dict", () => {
    expect(VERB_REGISTRY.educate!.buildPayload("org-1", "comm-1", {})).toEqual({
      org_id: "org-1", target_community_id: "comm-1", params: {},
    });
  });
  it("aid: nests transfer_amount under params", () => {
    expect(VERB_REGISTRY.aid!.buildPayload("org-1", "c-1", { transfer_amount: 50 })).toEqual({
      org_id: "org-1", target_id: "c-1", params: { transfer_amount: 50 },
    });
  });
  it("campaign: FLAT campaign_type, no params key", () => {
    const body = VERB_REGISTRY.campaign!.buildPayload("org-1", "terr-1", { campaign_type: "ELECTORAL" });
    expect(body).toEqual({ org_id: "org-1", target_id: "terr-1", campaign_type: "ELECTORAL" });
    expect(body).not.toHaveProperty("params");
  });
  // + attack (mode enum, default "targeted"), mobilize (sl_committed number),
  //   reproduce (mode + omitted target_id when null), move/investigate/negotiate enums
});
```
Also RED-assert enum hygiene: every `select` ParamField option `value` is a backend enum literal (no "Study Circle" style labels in values).

**T2 [RED] extend `src/stores/gameStore.test.ts`** — flat status-less response (mobilize regression):
```ts
it("caches flat responses that lack a status field (mobilize contract)", async () => {
  server.use(
    http.get("/api/games/:id/actions/:verb/targets/", () =>
      HttpResponse.json({ entity_id: "org-1", targets: [{ id: "t-9", name: "Rally" }] }),
    ),
  );
  await useGameStore.getState().fetchVerbTargets("game-001", "mobilize", "org-1");
  expect(useGameStore.getState().verbTargets["mobilize:org-1"]).toMatchObject({ targets: [{ id: "t-9" }] });
  expect(useGameStore.getState().error).toBeNull();
});
```

**T3 [RED] new `src/components/pages/__tests__/verb-page.test.tsx`** — component wiring (MSW capture pattern; follow tick-resolution-page.test.tsx harness style: `seedGameStore`, `MemoryRouter` at `/games/g1/actions/:verb`, real timers):
1. *educate end-to-end*: seed store (SEEDED_SNAPSHOT has player org `org-wclf`); default MSW educate-targets handler serves `src/mocks/educate_targets.json`; assert "Downtown Detroit" listed (live targets, not fixture COMMUNITIES); click it, click "Queue Educate"; capture the POST via `server.use(http.post("/api/games/:id/actions/educate/", async ({request}) => {captured = await request.json(); ...}))`; expect `{org_id: "org-wclf", target_community_id: "comm-1", params: {}}`.
2. *aid params nesting*: add a flat aid-targets handler (`population_targets`/`org_targets`); set the number field; expect `params.transfer_amount`.
3. *campaign*: assert **no** GET to `/actions/campaign/targets/` fires (register a handler that fails the test if hit), targets come from seeded snapshot territories (`Hamtramck`) + hyperedges (`Hamtramck Tenants Union`), and the POST body is flat with `campaign_type`.
4. *disabled verbs*: `/actions/move` renders the FR-025 rejection copy (already at VerbPage.tsx:204-213 — regression pin).
5. *fetch-once + invalidation*: second render with same `verb:org` key does not re-GET; after `resolveTick`, cache is empty (`invalidateVerbTargets` at gameStore.ts:185).

**T4** tick-resolution-page tests go GREEN with zero edits (they are the regression suite for Step 5).

## Verification commands
```bash
cd /home/user/projects/game/babylon/web/frontend
# RED phase (before implementing):
npx vitest run src/lib/verbs/__tests__/payloads.test.ts src/components/pages/__tests__/verb-page.test.tsx
# targeted GREEN:
npx vitest run src/lib/verbs src/stores/gameStore.test.ts \
  src/components/pages/__tests__/verb-page.test.tsx \
  src/components/pages/__tests__/tick-resolution-page.test.tsx \
  src/components/pages/__tests__/pages-v2.test.tsx src/lib/__tests__/verb-config.test.ts
# full gate (tsc --noEmit + eslint + prettier --check + vitest run):
npm run check          # or: mise run web:check   (from repo root)
```
NOTE: vitest 4.0.18 — `--reporter=basic` was removed; use `--reporter=dot` or default. Baseline before this branch: `3 failed | 478 passed (481), 66 files` — the only failures are the 3 tick-resolution ones; expected end state: 0 failed, +new tests.

## Out of scope (adjacent, do not touch)
- Engine-side verb dispatch (Phase 2.4 / 6th P0) — this branch only makes the client speak the serializer contract; `bridge.submit_action` acceptance is server territory.
- Backend campaign targets GET (405) — client works around via `targetsSource: "snapshot"`; flag for a backend follow-up (add `get` or a bridge `get_campaign_targets`).
- Backend session-scoping inconsistency: campaign (BaseVerbActionView api.py:1135-1143) checks user ownership + active status; the 8 APIView verbs use bare `get_object_or_404(GameSession, id=game_id)` with no player scoping (e.g. api.py:1233) — security/consistency note for the backend lane.
- `uiStore.pendingVerb/pendingParams` — unrelated legacy pending-action state; leave alone.
