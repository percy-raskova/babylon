# Implementation Brief — feat/verb-dispatch-engine (Design A, 6th P0)

**Repo**: /home/user/projects/game/babylon (verified at chore/test-infra-rearm, HEAD 9101dddf)
**Goal**: Player verbs currently resolve to blind `ActionResult(success=True)` — no engine effect. Wire a `VERB_RESOLVERS: dict[ActionType, VerbResolver]` registry so all 9 canonical verbs produce real graph effects, flow real results back to the bridge, and are contract-tested. Baseline-neutral: NPC path untouched; headless runs have no player actions.

**Ordering dependency**: `project/REMEDIATION_PLAN.md:53-55` says Design B (from_graph safety, Phase 2.1) lands FIRST because resolver graph-writes must satisfy the round-trip contract (§8 below). If B hasn't landed when you start, you must handle the `infrastructure` landmine (§8.3) yourself in the same commit.

---

## 1. Verified seam map (all quotes are current code)

### 1.1 The no-op seam — `src/babylon/engine/systems/ooda.py`

`_compat_graph` narrowing at **line 69**:
```python
        # Amendment L transition: subsystem helpers (layer0/layer3/effects)
        # still speak the nx-compat payload surface; narrow once here.
        graph = self._compat_graph(graph)
```
(`_compat_graph` is defined at `src/babylon/engine/systems/base.py:82-100`; returns `BabylonGraph`, raises `TypeError` otherwise.)

Blind player-action wrap in `_resolve_for_organization`, **lines 208-221**:
```python
        # Check for player-provided actions
        org_player_actions = player_actions.get(score.org_id)
        if org_player_actions:
            # Player actions are pre-validated Action dicts
            for action_data in org_player_actions:
                results.append(
                    ActionResult(
                        action=action_data
                        if not isinstance(action_data, dict)
                        else _action_from_dict(action_data, score.org_id),
                        success=True,
                        events_generated=[EventType.ORGANIZATIONAL_ACTION.value],
                    )
                )
```
NPC actions are ALSO blind-wrapped (lines 233-240, same `success=True` pattern) — `babylon.ooda.action_effects.resolve_action` is never called from the engine at all. **Keep the NPC path as-is** (plan: routing NPCs through resolvers is a defines-gated follow-up; this preserves baseline byte-identity).

`TurnResolution` built and DISCARDED, **lines 146-153**:
```python
        # Store turn resolution on context for downstream systems
        _resolution = TurnResolution(
            tick=tick,
            layer0_results=layer0_results,
            initiative_order=initiative_order,
            action_phase_results=action_phase_results,
            layer3_effects=layer3_effects,
        )
```
The comment lies — `_resolution` is never written to `context`. Nothing downstream can read it.

Player actions read from context, **lines 118-124**:
```python
        # Get player actions from context
        player_actions: dict[str, Any] = {}
        if isinstance(context, dict):
            player_actions = context.get("persistent_data", {}).get("player_actions", {})
        else:
            pd = getattr(context, "persistent_data", {})
            player_actions = pd.get("player_actions", {}) if isinstance(pd, dict) else {}
```

`_action_from_dict`, **lines 276-281** — note it DROPS `params`:
```python
    return Action(
        org_id=data.get("org_id", org_id),
        action_type=data["action_type"],
        target_id=data["target_id"],
        action_point_cost=data.get("action_point_cost", 1),
    )
```

Loop dispatch site in `step()`, **lines 130-140** — `_resolve_for_organization(score=, org_data_lookup=, player_actions=, defines=)`. The spec-056 spy (`tests/property/harness/org_action_spy.py`) patches this method and forwards `*args/**kwargs`, recovering `score` via `kwargs.get("score")` or `args[0]` — so you may ADD keyword params but `score` must stay first and the method must keep its name.

### 1.2 The bridge — `web/game/engine_bridge.py` (3691 lines)

Verb map, **lines 96-103** (6 verbs today):
```python
VERB_TO_ACTION_TYPE: dict[str, ActionType] = {
    "educate": ActionType.EDUCATE,
    "reproduce": ActionType.RECRUIT,
    "attack": ActionType.ATTACK_INFRASTRUCTURE,
    "mobilize": ActionType.PROTEST,
    "campaign": ActionType.PROPAGANDIZE,
    "aid": ActionType.PROVIDE_SERVICE,
}
```

Unsupported verbs, **lines 105-109**:
```python
# Spec 061 US5 (T081, FR-025): verbs that have stale wiring but no
# real engine handler. Listed for documentation; not exposed to the API.
UNSUPPORTED_VERBS: frozenset[str] = frozenset({"investigate", "move", "negotiate"})

CANONICAL_VERBS: frozenset[str] = frozenset(VERB_TO_ACTION_TYPE.keys())
```

Player-action injection in `resolve_tick`, **lines 1929-1951**:
```python
        # T014: Read pending player actions and format for engine injection
        pending = self.get_pending_actions(session_id, state.tick)
        if persistent_context is None:
            persistent_context = {}

        if pending:
            player_actions: dict[str, list[dict[str, Any]]] = {}
            for action in pending:
                org_id = action["org_id"]
                verb = action.get("verb", "")
                action_type_enum = VERB_TO_ACTION_TYPE.get(verb)
                action_type_val = action_type_enum.value if action_type_enum else verb

                player_actions.setdefault(org_id, []).append(
                    {
                        "action_type": action_type_val,
                        "target_id": action.get("target_id", org_id),
                        "org_id": org_id,
                        "action_point_cost": 1,
                        "params": action.get("params_json", {}),
                    }
                )
            persistent_context["player_actions"] = player_actions
```
Note line 1940: unmapped verbs fall through as raw strings (`action_type_val = ... else verb`) — a submitted "move" today would reach `_action_from_dict` and blow up Pydantic validation of `Action.action_type` at OODA time.

Pre-step snapshot, **lines 1953-1961**, and the post-step diff fakery, **lines 1990-2018**:
```python
        # T016: Persist ActionResult records with computed deltas
        for action in pending:
            tid = action.get("target_id")
            pre = pre_step.get(tid or "", {})
            post_consciousness = 0.0
            post_heat = 0.0
            if tid and tid in new_graph.nodes:
                post_consciousness = float(new_graph.nodes[tid].get("class_consciousness", 0.0))
                post_heat = float(new_graph.nodes[tid].get("heat", 0.0))
            ...
            result_data = {
                ...
                "initiative_score": 0.0,
                "action_cost": 1.0,
                "success": True,
                "consciousness_delta": post_consciousness - pre.get("consciousness", 0.0),
                "heat_delta": post_heat - pre.get("heat", 0.0),
                "details": None,
            }
            _persist_action_result(self._persistence, result_data)
```
Double fakery: `success` is hardcoded `True`, and `class_consciousness` NEVER exists as a top-level node attr on social_class nodes (it lives nested in the `ideology` dict — see `src/babylon/engine/systems/ideology.py:46-61`), so `consciousness_delta` is always `0.0 - 0.0`.

Engine step call, **lines 1963-1970**: `new_state = step(state, sim_config, persistent_context=persistent_context, defines=game_defines)` — after this returns, `persistent_context` contains everything the engine synced back (§1.4), which is where `turn_resolution` will arrive.

Callers: `api.py:1003 resolve_tick` → `tick_resolver.py:resolve_game_tick(bridge, session_id)` with NO `persistent_context` → fresh dict per tick (fine: readback happens within the same `resolve_tick` call).

### 1.3 Preview endpoints (what they compute today)

- `POST /api/games/{id}/actions/preview/` (`urls.py:102-105`) → `api.actions_preview` (`api.py:853`, verb-validated against `CANONICAL_VERBS` at :873) → `EngineBridge.preview_action` (**engine_bridge.py:2904-3012**). It computes **hardcoded per-verb-category heuristics**, e.g. lines 2971-2990: `educate/campaign → estimated_consciousness_delta = 0.05 * org_cohesion`, `attack/mobilize → estimated_heat_delta = 0.08 * org_cohesion`, `investigate/negotiate/move → 0.0` — completely disconnected from `action_effects` math.
- Per-verb GET panels (verb views at `api.py:1230-1692`, routed via `urls.py`): `get_educate_targets:2247`, `get_aid_targets:2347`, `get_mobilize_targets:2443`, `get_attack_targets:2495`, `get_reproduce_targets:2621`, `get_investigate_targets:2696`, `get_move_targets:2785`, `get_negotiate_targets:2839`. Some return literal fixtures (e.g. negotiate's fake `"org-auto-union"` target at 2860-2882).
- **Scope note**: full preview==resolution repointing is in the plan text but large; minimum for this branch is `preview_action` for the consciousness verbs calling `compute_consciousness_delta` (pure, no mutation). Do the panels in a follow-up if time-boxed.

### 1.4 Engine context plumbing — `src/babylon/engine/simulation_engine.py`

TickContext creation + sync-back, **lines 710-726**:
```python
    # Create typed TickContext for this tick
    # persistent_data is initialized from caller's persistent_context if provided
    context = TickContext(
        tick=state.tick,
        persistent_data=dict(persistent_context) if persistent_context else {},
    )

    # Run all systems through the engine
    _DEFAULT_ENGINE.run_tick(G, services, context)

    # Feature 020: Persist tick_dynamics for WorldState round-trip survival
    _save_graph_context(G, persistent_context, state.tick)

    # Sync any changes from context.persistent_data back to caller's dict
    if persistent_context is not None:
        for key, value in context.persistent_data.items():
            persistent_context[key] = value
```
So: OODASystem writes `context.persistent_data["turn_resolution"]` → step() copies it into the bridge's `persistent_context` → bridge reads it after line 1970. `TickContext` (`src/babylon/engine/context.py:19-113`) is `ConfigDict(extra="allow")`, `persistent_data: dict[str, Any]` — free-form, no schema change needed.

### 1.5 Layer 3 consequence propagation — `src/babylon/ooda/layer3.py` (NOT engine/systems/)

`process_layer3`, **lines 22-54**:
```python
def process_layer3(
    action_results: list[ActionResult],
    graph: BabylonGraph,
    defines: OODADefines,
) -> dict[str, Any]:
    ...
    summary: dict[str, Any] = {}

    # Feature 034: consciousness and contestation are now derived quantities
    # computed from org landscape in CommunitySystem, not direct writes.
    summary["consciousness"] = 0
    summary["heat_updates"] = _propagate_heat(action_results, graph, defines)
    summary["edge_transitions"] = _propagate_edge_transitions(action_results, graph)
    summary["infrastructure_updates"] = _propagate_infrastructure(action_results, graph, defines)
    summary["contestation_updates"] = 0

    return summary
```
It already consumes `ActionResult`s: heat for REPRESS/SURVEIL (lines 57-100), TRANSACTIONAL→SOLIDARISTIC edge flips for ORGANIZE (103-137), and `infrastructure` ± for BUILD/ATTACK_INFRASTRUCTURE (140-182, write at line 176: `graph.nodes[target]["infrastructure"] = max(0.0, min(1.0, current + delta))`). **Crucially, `consciousness_delta` on ActionResults feeds NOTHING here** (Feature 034 moved CI to CommunitySystem's org-landscape derivation) — so a resolver's meaningful effects are its own direct graph writes + these three layer3 channels + persisted results for the UI.

### 1.6 The dormant effects machinery — `src/babylon/ooda/action_effects.py` (371 lines, zero engine callers)

Callers: only `src/babylon/ooda/__init__.py:17` (re-export) and tests (`tests/unit/ooda/test_action_effects.py`, `tests/unit/ooda/test_reactionary_ooda_verbs.py`). `resolve_action(action, org_attrs, graph, defines, org_defines, reactionary=None) -> ActionResult` (lines 106-163) dispatches:

| ActionType | Path | Effect |
|---|---|---|
| AGITATE | `_resolve_agitate` (226-239) | `direct_effects={"contestation_delta": ...}` (layer3 no longer applies it) |
| REPRESS, SURVEIL | `_resolve_repressive` (242-277) | backfire `ConsciousnessDelta` (REVOLUTIONARY tendency) + STATE_REPRESSION/STATE_SURVEILLANCE events |
| ASSIMILATE | `_resolve_assimilate` (280-304) | negative CI delta, LIBERAL tendency |
| POGROM / VIGILANTISM / LOCKOUT | `_resolve_fascist_verb` (166-223) | **the precedent for direct graph mutation**: `graph.update_node(target_id, repression_faced=...)`, wealth destruction, WAGES `value_flow` attenuation via `graph.update_edge(...)` |
| everything else | `compute_consciousness_delta` (33-103) | five-factor CI delta scaled by `defines.get_action_base(action_type.value)`; **base is 0.0 → `None` delta** for PROTEST, ATTACK_INFRASTRUCTURE, MAP_NETWORK, PROPOSE_ALLIANCE (only educate/agitate/provide_service/recruit/organize/propagandize/repress/surveil/assimilate have nonzero bases — `config/defines/ooda.py:449-469`; unknown keys return 0.0, so MOVE is safe there) |

### 1.7 Orphaned verb modules — `src/babylon/engine/actions/` (NO `__init__.py` — implicit namespace package)

| File | State |
|---|---|
| `aid.py` (55 ln) | Docstring + commented pseudo-code + `pass`. Signature `resolve_aid(action, graph, hypergraph, defines) -> Any` |
| `investigate.py` (47 ln) | Stub, `pass`. `resolve_investigate(action, graph, defines)` |
| `mobilize.py` (143 ln) | **Only real body.** `resolve_mobilize(action, graph, hypergraph, defines) -> dict` — solidarity-multiplied turnout, strike vs protest branch, George Floyd backfire. BUT: writes `graph.nodes[target]["agitation"]`, `["heat"]`, `["extraction_flow"]`, `graph.nodes[org]["consciousness"]` (three of four are NOT model fields, §8), returns a raw dict not `ActionResult`, and emits ad-hoc event strings (`"MOBILIZATION_BACKFIRE"`) that are not `EventType` members |
| `move.py` (43 ln) | Stub, `pass` |
| `negotiate.py` (44 ln) | Stub, `pass` |
| `reproduce.py` (53 ln) | Stub, `pass` |
| `educate.py`, `attack.py`, `campaign.py` | **Do not exist** (the canary try-imports them and gets ImportError) |

Zero production imports; only `tests/test_verb_simplex_canary.py` imports these.

### 1.8 ActionType — `src/babylon/models/enums/actions.py:32-88`

25 `StrEnum` members. Present: `RECRUIT, ORGANIZE, EDUCATE, AGITATE, PROPAGANDIZE, FUNDRAISE, PROVIDE_SERVICE, EMPLOY, REPRESS, PROTEST, STRIKE, EXPROPRIATE, SURVEIL, INFILTRATE, COUNTER_INTEL, MAP_NETWORK, PROPOSE_ALLIANCE, DENOUNCE, BUILD_INFRASTRUCTURE, ATTACK_INFRASTRUCTURE, ASSIMILATE, POGROM, LOCKOUT, VIGILANTISM, RED_BROWN_COUP`. **`MOVE` is missing** (and there is no INVESTIGATE/NEGOTIATE — they map to MAP_NETWORK/PROPOSE_ALLIANCE). Docstring at line 35 claims "25 action types" — update to 26.

### 1.9 Canary — `tests/test_verb_simplex_canary.py` (202 lines)

Imports each `resolve_*` in `try/except ImportError: resolve_x = None` (lines 6-49). Actual behavior TODAY:
- `test_educate_simplex_drift`, `test_campaign_simplex_routing`, `test_attack_simplex_routing`: `@pytest.mark.skip(reason="... ADR-037 ...")` decorators (lines 171-190) — skip.
- `test_aid_simplex_drift` (192-201): unconditional `pytest.skip("AID stub deferred (ADR-037 / spec 045)...")` in the body — skip.
- `test_investigate/reproduce/move/negotiate_does_not_mutate_simplex`: the guard is `if not resolve_investigate: pytest.skip(...)` — but the stubs EXIST as truthy function objects, so these four **run vacuously and pass** (a `pass`-body stub trivially "does not mutate the simplex").
- `test_mobilize_agitation_routing` (149-169): actually exercises the real `resolve_mobilize` body against a `create_wayne_county_scenario()` graph.

### 1.10 Supporting facts you will need

- `Action` / `ActionResult` / `TurnResolution` — `src/babylon/ooda/types.py:89-277`, all `ConfigDict(frozen=True)`. `Action` has NO `params` field (hence §1.1 drop).
- `OODADefines.get_base_cost` (`config/defines/ooda.py:405-448`) **raises KeyError for unknown types** — a `MOVE` member without `base_cost_move` breaks the sweep test (§9).
- Eligibility matrix `_ELIGIBILITY_MAP` (`src/babylon/ooda/action_eligibility.py:15-120`) is built per-(OrgType, ActionType); completeness is asserted by `tests/unit/ooda/test_eligibility.py:18-25` (`len == len(OrgType) * len(ActionType)`).
- `ACTION_COSTS` (`src/babylon/models/vanguard_resources.py:139-152`) already has all 9 verbs including move/investigate/negotiate — submission-side affordability already works; only the map + engine were missing.
- `submit_action` (`engine_bridge.py:2111-2196`) does NOT validate against CANONICAL_VERBS; `api.actions_preview`/`actions_submit` do (`api.py:873, 954`). Per-verb POST views exist for all verbs incl. MoveVerbView (`urls.py:128-180`).
- `EventType.ORGANIZATIONAL_ACTION = "organizational_action"` (`src/babylon/models/enums/events.py:116`); STATE_REPRESSION / STATE_SURVEILLANCE also exist.
- `GameDefines` composes `.ooda` (`OODADefines`), plus `OrganizationDefines`/`ReactionaryDefines` (exported from `babylon.config.defines`) — mirror how `resolve_action` takes them today.

---

## 2. Design: the registry

### 2.1 New file: `src/babylon/engine/actions/__init__.py`

This makes `engine/actions` a regular package (currently namespace-only) and is the single registry per the ratified plan (`project/REMEDIATION_PLAN.md:42-48`). Sketch (match project style — `from __future__ import annotations`, RST docstrings, strict types):

```python
"""Player-verb resolver registry (Design A — verb dispatch engine).

Maps engine :class:`ActionType` members to resolver callables. The
uniform signature is::

    resolve_<verb>(action, org_attrs, graph, services) -> ActionResult

Missing resolver => ``ActionResult(success=False, failure_reason=...)``
— loud, never silent success.

See Also:
    :func:`babylon.ooda.action_effects.resolve_action`: the effects
    machinery the consciousness-class resolvers compose.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

from babylon.engine.actions.aid import resolve_aid
from babylon.engine.actions.attack import resolve_attack
from babylon.engine.actions.campaign import resolve_campaign
from babylon.engine.actions.educate import resolve_educate
from babylon.engine.actions.investigate import resolve_investigate
from babylon.engine.actions.mobilize import resolve_mobilize
from babylon.engine.actions.move import resolve_move
from babylon.engine.actions.negotiate import resolve_negotiate
from babylon.engine.actions.reproduce import resolve_reproduce
from babylon.models.enums import ActionType
from babylon.ooda.types import Action, ActionResult

if TYPE_CHECKING:
    from babylon.engine.graph import BabylonGraph
    from babylon.engine.services import ServiceContainer


class VerbResolver(Protocol):
    """Structural type for a player-verb resolver."""

    def __call__(
        self,
        action: Action,
        org_attrs: dict[str, Any],
        graph: BabylonGraph,
        services: ServiceContainer,
    ) -> ActionResult: ...


VERB_RESOLVERS: dict[ActionType, VerbResolver] = {
    ActionType.EDUCATE: resolve_educate,
    ActionType.RECRUIT: resolve_reproduce,
    ActionType.ATTACK_INFRASTRUCTURE: resolve_attack,
    ActionType.PROTEST: resolve_mobilize,
    ActionType.PROPAGANDIZE: resolve_campaign,
    ActionType.PROVIDE_SERVICE: resolve_aid,
    ActionType.MAP_NETWORK: resolve_investigate,
    ActionType.MOVE: resolve_move,
    ActionType.PROPOSE_ALLIANCE: resolve_negotiate,
}


def resolve_player_action(
    action: Action,
    org_attrs: dict[str, Any],
    graph: BabylonGraph,
    services: ServiceContainer,
) -> ActionResult:
    """Dispatch one player action to its registered resolver."""
    resolver = VERB_RESOLVERS.get(action.action_type)
    if resolver is None:
        return ActionResult(
            action=action,
            success=False,
            failure_reason=(
                f"No resolver registered for action_type '{action.action_type.value}'"
            ),
        )
    return resolver(action=action, org_attrs=org_attrs, graph=graph, services=services)


__all__ = [
    "VERB_RESOLVERS",
    "VerbResolver",
    "resolve_player_action",
]
```

No import cycle: `engine/actions` imports `ooda.types` + `models.enums` (leafward); `ServiceContainer` is TYPE_CHECKING-only. `engine/systems/ooda.py` importing `engine/actions` is safe (do it lazily inside the method to be certain, matching the existing lazy-import style at ooda.py:157, 274).

### 2.2 The 9 resolvers — mapping and effect classes

Every write MUST honor §8. All resolvers return `ActionResult` (frozen) and reuse `EventType` values (no ad-hoc event strings).

| Verb | ActionType | Module | Implementation |
|---|---|---|---|
| educate | EDUCATE | `educate.py` **NEW** | Thin delegate: `action_effects.resolve_action(action, org_attrs, graph, services.defines.ooda, services.defines.organization)` → real ConsciousnessDelta (five-factor, contestation bonus). No direct graph writes. |
| campaign | PROPAGANDIZE | `campaign.py` **NEW** | Same delegate (action_base_propagandize path). |
| aid | PROVIDE_SERVICE | `aid.py` rewrite | Delegate for CI (tendency-split base) + material transfer: read `params["transfer_amount"]`, decrement org node `budget`, increment target `wealth` (both model fields) via `graph.update_node(...)`; record `direct_effects={"amount_transferred": ...}`. Insufficient budget → `success=False, failure_reason=...`. |
| reproduce | RECRUIT | `reproduce.py` rewrite | Mode branch from `params["mode"]` per the in-file pseudo-code, but write ONLY round-trip fields: cadre_training → `cadre_level` up / `cohesion` up; mass_recruitment → `cohesion` down + `budget` down; record pool math in `direct_effects`. |
| attack | ATTACK_INFRASTRUCTURE | `attack.py` **NEW** | Return `ActionResult` carrying the action so layer3 `_propagate_infrastructure` applies the infra delta (already wired, layer3.py:159-176 — see §8.3 landmine); resolver additionally raises acting-org `heat` (model field) and puts backfire/collateral in `direct_effects`. |
| mobilize | PROTEST | `mobilize.py` adapt | Port the existing 143-line body but: (a) return `ActionResult` (turnout, heat_generated, events in `direct_effects`/`events_generated`); (b) heat write is fine on Territory/Organization nodes (`heat` is a field of both); (c) agitation on a social_class target must go through copy-modify-writeback of the nested `ideology` dict (`ideology["agitation"] += ...`, then `graph.update_node(target, ideology=new_ideology)`) — top-level `agitation` does NOT round-trip; (d) drop `extraction_flow` and top-level org `consciousness` writes (not model fields — either route to `budget`/`cohesion` or record in `direct_effects` only); (e) replace `"MOBILIZATION_BACKFIRE"`-style strings with `EventType` values (EXCESSIVE_FORCE/UPRISING exist for the George Floyd dynamic — check `models/enums/events.py` for exact members before choosing). |
| investigate | MAP_NETWORK | `investigate.py` rewrite | **No graph writes.** Return `success=True` with `direct_effects={"revealed": {target_id: [attr names]}, "scan_type": params.get("scan_type", "territory_scan")}` — bridge/UI consumes it from persisted results. Optionally raise acting-org `heat` on a failed check (deterministic threshold, no RNG — Phase 2.3 owns randomness). |
| move | **MOVE (new enum member)** | `move.py` rewrite | Validate target territory exists (`graph.nodes.get(target)` `_node_type == "territory"`), then rewrite org `territory_ids` (list field on Organization — round-trips): `graph.update_node(org_id, territory_ids=[action.target_id])` (or append, per params `mode`). Invalid target → `success=False`. |
| negotiate | PROPOSE_ALLIANCE | `negotiate.py` rewrite | Edge state machine: if `graph.has_edge(org, target)` and edge_type is antagonistic-class, flip to `EdgeType.TRANSACTIONAL` (mirror layer3's ORGANIZE flip at layer3.py:127-132, and note only `edge_type/value_flow/tension/description/subsidy_cap/solidarity_strength` round-trip — §8.4); else create a TRANSACTIONAL edge. Success gate on leverage from `cohesion`/`cadre_level` (deterministic). |

Uniform per-module signature (matches registry Protocol):
```python
def resolve_educate(
    action: Action,
    org_attrs: dict[str, Any],
    graph: BabylonGraph,
    services: ServiceContainer,
) -> ActionResult:
```
(`ServiceContainer` import under TYPE_CHECKING in each module; runtime access is `services.defines.ooda`, `.organization`, `.reactionary`.)

---

## 3. Implementation steps (TDD order)

### Step 0 — RED: contract suite skeleton `tests/contract/verbs/`
Create `tests/contract/verbs/__init__.py` + three files (marker `@pytest.mark.contract` — registered in pyproject `markers`, and `strict_markers = true` is armed, so use only registered markers). **Direct imports, no try/except** — a missing resolver is a COLLECTION FAILURE, not a skip:

- `test_registry.py`:
  - `from babylon.engine.actions import VERB_RESOLVERS, resolve_player_action` (hard import).
  - all 9 ActionTypes above are keys; values are callable.
  - unregistered type (e.g. `ActionType.FUNDRAISE`) → `resolve_player_action(...)` returns `success=False` with non-None `failure_reason` (never raises, never silent-succeeds).
  - bridge parity: `from web.game.engine_bridge import VERB_TO_ACTION_TYPE` — `set(VERB_TO_ACTION_TYPE.values()) == set(VERB_RESOLVERS.keys())` and `len(VERB_TO_ACTION_TYPE) == 9` (this is the test that keeps map and registry from drifting apart; `tests/integration/test_unsupported_verbs.py` shows web-import style from repo root works).
- `test_effects.py`: per-verb effect-class assertions on a `create_wayne_county_scenario()` graph (reuse the canary's fixture pattern, lines 66-69), e.g. educate → `consciousness_delta is not None`; mobilize → target ideology.agitation increased AND heat increased; move → territory_ids changed; negotiate → edge_type flipped; investigate → zero graph mutation (snapshot node payloads before/after) but non-empty `direct_effects`; attack → ActionResult routes through `process_layer3` and infra channel fires; aid → wealth/budget conservation (org loss == target gain × efficiency).
- `test_roundtrip.py` (the graph-write contract, §8): for each verb — resolve, then `WorldState.from_graph(G, tick=1)` must not raise; then `.to_graph()` and assert the intended mutation survived, OR the written attr is a member of the matching exclusion frozenset imported from `babylon.models.world_state` (`SOCIAL_CLASS_COMPUTED_FIELDS`, `TERRITORY_EXCLUDED_FIELDS`, `ORGANIZATION_EXCLUDED_FIELDS` — module scope, lines 54-101, exported for exactly this purpose).

Run: `mise run test:q -- tests/contract/verbs/` → all red (ImportError on `babylon.engine.actions` registry).

### Step 1 — ActionType.MOVE + defines + eligibility (small, self-contained commit)
1. `src/babylon/models/enums/actions.py`: add `MOVE = "move"` after ASSIMILATE (line 83, before the spec-071 block); update the "25 action types" docstring (line 35) to 26 and add a `MOVE:` line in the Values block.
2. `src/babylon/config/defines/ooda.py`: add `base_cost_move: int = Field(default=1, ge=1, description="AP cost: MOVE")` next to the other base_cost fields (~line 294 area) and `"move": self.base_cost_move,` in the `get_base_cost` map (lines 417-443). `get_action_base` needs nothing (returns 0.0 default, line 469).
3. `src/babylon/ooda/action_eligibility.py`: add `ActionType.MOVE` to `_UNIVERSAL_ACTIONS` (lines 23-38) — completeness test sweeps all pairs.
4. Update pinned tests: `tests/unit/ooda/test_types.py:248-250` (`test_has_25_values` → 26; rename to `test_has_26_values`); `tests/unit/ooda/test_defines.py:106-110` and `tests/unit/ooda/test_eligibility.py:18-25` go green automatically once 2-3 are done.
Verify: `mise run test:q -- tests/unit/ooda/`.

### Step 2 — `Action.params` + `_action_from_dict` passthrough
`src/babylon/ooda/types.py` `Action` (89-134): add
```python
    params: dict[str, Any] = Field(
        default_factory=dict,
        description="Verb-specific parameters (bridge params_json passthrough)",
    )
```
`src/babylon/engine/systems/ooda.py:_action_from_dict` (276-281): add `params=data.get("params", {}),`. The bridge already injects `"params"` (engine_bridge.py:1948) — today it is silently dropped. Red-first: a unit test in `tests/unit/ooda/test_types.py` + a dispatch test asserting `params` reaches the resolver.

### Step 3 — resolvers + registry (Step 0 goes green file-by-file)
Write `educate.py`/`campaign.py`/`attack.py` (new), rewrite the 5 stubs, adapt `mobilize.py`, then the `__init__.py` registry (§2.1). Mypy strict applies (`pyproject [tool.mypy] strict = true`, excludes only tests/) — no `Any`-typed public signatures beyond `dict[str, Any]` payloads; RST docstrings mandatory.

### Step 4 — OODA dispatch + turn_resolution publication
`src/babylon/engine/systems/ooda.py`:
1. In `step()`, thread graph + services into the seam — change the call at 134-139 to add `graph=graph, services=services` (kwargs AFTER `score`; the spec-056 spy forwards `*args/**kwargs` and reads `kwargs["score"]`, so this is safe — but do NOT rename the method).
2. In `_resolve_for_organization`, replace the blind wrap (209-221):
```python
        # Check for player-provided actions
        org_player_actions = player_actions.get(score.org_id)
        if org_player_actions:
            from babylon.engine.actions import resolve_player_action

            for action_data in org_player_actions:
                action = (
                    action_data
                    if not isinstance(action_data, dict)
                    else _action_from_dict(action_data, score.org_id)
                )
                results.append(
                    resolve_player_action(
                        action=action,
                        org_attrs=org_data,
                        graph=graph,
                        services=services,
                    )
                )
```
   (NPC branch 222-240 stays byte-identical.)
3. Replace the discarded `_resolution` (146-153) with publication:
```python
        # Store turn resolution on context for the bridge + downstream systems
        resolution = TurnResolution(
            tick=tick,
            layer0_results=layer0_results,
            initiative_order=initiative_order,
            action_phase_results=action_phase_results,
            layer3_effects=layer3_effects,
        )
        if isinstance(context, dict):
            context.setdefault("persistent_data", {})["turn_resolution"] = resolution.model_dump(
                mode="json"
            )
        else:
            context.persistent_data["turn_resolution"] = resolution.model_dump(mode="json")
```
   `mode="json"` matters: `ActionResult.action.action_type` is a StrEnum and `ConsciousnessDelta` nests enums — the bridge persists JSON. `simulation_engine.py:723-726` then syncs it to the caller's dict for free.
Red-first tests in `tests/unit/ooda/test_ooda_system.py` (extend existing file; `_make_graph_with_orgs` fixture at lines 26-61): (a) step with `context={"tick": 0, "persistent_data": {"player_actions": {"rev_workers": [{"action_type": "educate", "target_id": "detroit", ...}]}}}` → resolver-real result (not blind: assert `results` reflect resolver semantics, e.g. unknown type gives success=False); (b) `"turn_resolution"` appears in `context["persistent_data"]` with `action_phase_results` non-empty; (c) TickContext variant too.

### Step 5 — bridge consumption + verb map
`web/game/engine_bridge.py`:
1. Extend `VERB_TO_ACTION_TYPE` (96-103) to 9 entries (`"investigate": ActionType.MAP_NETWORK, "move": ActionType.MOVE, "negotiate": ActionType.PROPOSE_ALLIANCE`); **delete** `UNSUPPORTED_VERBS` (105-107) and its stale comment (90-95 → rewrite to state all 9 verbs have engine resolvers); `CANONICAL_VERBS` derives automatically.
2. Rewrite the T016 block (1990-2018) to consume REAL results:
```python
        # T016: Persist REAL per-action results from the engine's TurnResolution
        resolution = persistent_context.get("turn_resolution", {}) or {}
        results_by_org: dict[str, list[dict[str, Any]]] = {}
        for r in resolution.get("action_phase_results", []):
            results_by_org.setdefault(r["action"]["org_id"], []).append(r)

        for action in pending:
            tid = action.get("target_id")
            pre = pre_step.get(tid or "", {})
            post_heat = 0.0
            if tid and tid in new_graph.nodes:
                post_heat = float(new_graph.nodes[tid].get("heat", 0.0))

            verb = action.get("verb", "")
            action_type_enum = VERB_TO_ACTION_TYPE.get(verb)
            action_type_val = action_type_enum.value if action_type_enum else verb

            org_results = results_by_org.get(action["org_id"], [])
            engine_result = org_results.pop(0) if org_results else None

            success = False
            failure_reason: str | None = "action not resolved by engine"
            ci_delta = 0.0
            direct_effects: dict[str, Any] = {}
            if engine_result is not None:
                success = bool(engine_result.get("success", False))
                failure_reason = engine_result.get("failure_reason")
                cd = engine_result.get("consciousness_delta")
                ci_delta = float(cd["collective_identity_delta"]) if cd else 0.0
                direct_effects = engine_result.get("direct_effects", {})

            result_data = {
                "session_id": session_id,
                "tick": new_state.tick,
                "org_id": action["org_id"],
                "action_type": action_type_val,
                "target_id": tid,
                "target_community": action.get("target_community"),
                "initiative_score": 0.0,
                "action_cost": 1.0,
                "success": success,
                "consciousness_delta": ci_delta,
                "heat_delta": post_heat - pre.get("heat", 0.0),
                "details": {
                    "direct_effects": direct_effects,
                    "failure_reason": failure_reason,
                },
            }
            _persist_action_result(self._persistence, result_data)
```
   Keep the pre-step snapshot (1953-1961) — heat now moves for real, so the diff becomes a measurement. (Drop the dead `class_consciousness` reads: they were always 0.0, see §1.2.) Check `_persist_action_result` (3628) accepts a dict `details` — it presumably JSON-serializes; verify and adapt (`json.dumps` if the column wants text).
3. `preview_action` (2904+): minimum change — for educate/campaign/aid, call `compute_consciousness_delta(org_data, target, action_type, graph, defines.ooda, defines.organization)` (pure, read-only) instead of the `0.05 * cohesion` literal at 2973; keep heuristics for the rest with a `# TODO(verb-preview parity)` note, or do full parity if time allows.
4. Delete/invert `tests/integration/test_unsupported_verbs.py` — its assertions (`"move" not in VERB_TO_ACTION_TYPE`, `UNSUPPORTED_VERBS` import) now fail by design. Replace with a 9-verb supported test or fold into `tests/contract/verbs/test_registry.py` (preferred; delete the file).

### Step 6 — canary replacement
`git rm tests/test_verb_simplex_canary.py`. Its replacement is `tests/contract/verbs/` (Step 0), which is strictly stronger: hard imports (collection failure on missing resolver — no more vacuous green), per-verb effect-class, and round-trip survival. Grep for stragglers: `rg -n "verb_simplex_canary" --` (only the .pyc cache references it).

### Step 7 — baseline byte-identity proof
Headless runs never populate `player_actions`, and the NPC path is untouched, so baselines must not move:
```
mise run qa:regression
```
plus `mise run sim:trace` diff if the PR checklist requires trace.csv identity. If regression shifts, you touched the NPC path or layer3 by accident — stop and bisect.

---

## 8. The graph-write contract (must-read before writing any resolver)

`WorldState.from_graph` (`src/babylon/models/world_state.py:416-544`) reconstructs frozen Pydantic models per `_node_type`. The exclusion frozensets are module-scope at **world_state.py:54-101** (`SOCIAL_CLASS_COMPUTED_FIELDS`, `TERRITORY_EXCLUDED_FIELDS`, `INSTITUTION_EXCLUDED_FIELDS`, `ORGANIZATION_EXCLUDED_FIELDS`) — importable by the contract tests.

1. **SocialClass** (`entities/social_class.py:201-205`): `extra="forbid"`. Writable round-trip fields include `wealth, organization, repression_faced, subsistence_threshold, effective_wealth, population, entitlement, volatility, fascist_alignment, ideology` (nested `IdeologicalProfile` dict holding `class_consciousness`/`national_identity`/`agitation` — mutate via copy-modify-writeback of the whole dict). Writing any other top-level attr → **ValidationError at from_graph** unless it's in `SOCIAL_CLASS_COMPUTED_FIELDS` (`{consumption_needs, w_paid, v_produced, contradiction_fields, field_derivatives}` — then it's legal but dropped per-tick).
2. **Territory** (`entities/territory.py:50-54`): `extra="forbid"`. Round-trip fields: `heat, rent_level, population, under_eviction, biocapacity, max_biocapacity, regeneration_rate, extraction_intensity, profile, ...` — NO `agitation`, NO `infrastructure`.
3. **⚠ LANDMINE — `infrastructure`**: layer3 `_propagate_infrastructure` (layer3.py:176) writes `graph.nodes[target]["infrastructure"]`, which is neither a Territory field nor in `TERRITORY_EXCLUDED_FIELDS`. The moment the attack verb routes ATTACK_INFRASTRUCTURE at a territory node, the very next `from_graph` raises. Design B owns the general fix; if it hasn't landed, add `"infrastructure"` to `TERRITORY_EXCLUDED_FIELDS` (transient, like the dpd fields) **in this branch's first commit**, with a comment citing layer3.py:176. (Same exposure exists today via NPC CIVIL_SOCIETY → BUILD_INFRASTRUCTURE, so this is also a live pre-existing bug — mention it in the PR.)
4. **Organization** (`entities/organization.py:138`): `ConfigDict(frozen=True)` only — pydantic default `extra="ignore"`, so unknown attrs **silently vanish** on round-trip (no crash, but your effect evaporates). Round-trip fields: `cohesion, cadre_level, budget, heat, territory_ids, consciousness_tendency, headquarters_id, legal_standing, ...`. `ORGANIZATION_EXCLUDED_FIELDS = {effective_capacity, composition_cache}`.
5. **Edges**: from_graph (world_state.py:509-528) keeps ONLY `edge_type, value_flow, tension, description, subsidy_cap, solidarity_strength`. Negotiate's edge flip round-trips; anything else on edges is dropped.
6. **Mutation API**: prefer `graph.update_node(id, **attrs)` / `graph.update_edge(...)` (the fascist-verb precedent, action_effects.py:197-215); the nx-compat `graph.nodes[id][k] = v` surface also works under `_compat_graph` (layer3 precedent).

---

## 9. Test inventory

**Existing tests covering the area (must stay green):**
- `tests/unit/ooda/test_ooda_system.py` — 7 tests, OODASystem orchestration (extend for dispatch)
- `tests/unit/ooda/test_action_effects.py`, `test_reactionary_ooda_verbs.py` — `resolve_action` machinery (untouched)
- `tests/unit/ooda/test_layer3.py`, `test_layer0.py`, `test_npc_stub.py`, `test_initiative.py`, `test_types.py`, `test_defines.py`, `test_eligibility.py`, `test_action_costs.py`, `test_constraints.py`, `test_cycle_time.py`
- `tests/integration/test_ooda_detroit.py` — integration arc
- `tests/property/invariants/test_consequence_after_actions.py`, `test_material_base_ordering.py` + `tests/property/harness/org_action_spy.py` — patch `_resolve_for_organization`; signature-append-only (§Step 4)
- `tests/unit/engine/test_system_order.py`, `tests/contract/engine/test_systembase_inheritance.py`
- `tests/unit/web/test_per_verb_views.py`, `test_per_verb_serializers.py` — per-verb API surface

**Tests to update (will go red on your changes, by design):**
- `tests/unit/ooda/test_types.py:248-250` (len(ActionType)==25 → 26)
- `tests/integration/test_unsupported_verbs.py` — delete (superseded by contract registry test)
- `tests/test_verb_simplex_canary.py` — delete (superseded by `tests/contract/verbs/`); note 4 of its 9 tests were passing vacuously against `pass` stubs

**New (red-first):** `tests/contract/verbs/{test_registry,test_effects,test_roundtrip}.py` (Step 0); dispatch + turn_resolution tests in `tests/unit/ooda/test_ooda_system.py` (Step 4); bridge consumption test `tests/unit/web/test_resolve_tick_consumes_results.py` (mock persistence, seeded turn_resolution dict) (Step 5).

---

## 10. Verification commands

```bash
# RED phase
mise run test:q -- tests/contract/verbs/                # all red before Step 3

# per-step scoped
mise run test:q -- tests/unit/ooda/
mise run test:q -- tests/contract/verbs/
mise run test:failed                                    # re-run last failures
poetry run pytest tests/unit/ooda/test_ooda_system.py tests/contract/verbs/ -q
poetry run pytest tests/integration/test_ooda_detroit.py -q
poetry run pytest tests/property/invariants/test_consequence_after_actions.py -q   # spy seam intact
poetry run pytest tests/unit/web/ -q                    # bridge/web unit surface

# quality gate
mise run check:quick                                    # ruff lint+format + mypy strict
mise run check                                          # + test:unit

# baseline neutrality (PR requirement)
mise run qa:regression

# commit each step (hook-safe)
mise run commit -- "feat(engine): add ActionType.MOVE + defines + eligibility (verb dispatch step 1)"
```

Known unrelated reds at dev HEAD (don't chase): `tests/unit/economics/throughput/...::test_frozen`, `tests/integration/economics/` data-availability failures, `test:doctest` circular-import break.

---

## 11. Commit plan (per CLAUDE.md commit-per-unit)
1. `feat(models): add ActionType.MOVE (26 members) + base_cost_move + eligibility rows` (+ pinned-test updates)
2. `feat(ooda): Action.params passthrough from bridge to resolvers`
3. `fix(models): mark 'infrastructure' as transient territory graph attr` (skip if Design B already covered it)
4. `feat(engine): verb resolver registry + 9 resolvers (tests/contract/verbs RED→GREEN)`
5. `feat(engine): OODA dispatch via VERB_RESOLVERS + turn_resolution into context.persistent_data`
6. `feat(web): bridge consumes real TurnResolution; 9-verb map; drop UNSUPPORTED_VERBS`
7. `test(contract): retire verb_simplex_canary + unsupported_verbs in favor of tests/contract/verbs/`
8. `chore(qa): baseline byte-identity proof (qa:regression clean)`
