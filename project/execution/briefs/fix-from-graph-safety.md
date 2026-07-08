# Implementation Brief — `fix/from-graph-safety` (Design B: `WorldState.from_graph` crash minefield)

Verified 2026-07-08 against `dev` @ `3f9d1d69` (the stated base `chore/test-infra-rearm` @ `9101dddf` has since merged to dev; `git diff --stat 9101dddf..HEAD` over every seam file below is **empty** — all anchors are current). All line numbers are pre-edit anchors.

## 0. Verified seams (quotes from current code)

### 0.1 Exclusion frozensets — `src/babylon/models/world_state.py:54-101` (claim ✓)

Four module-level `Final[frozenset[str]]` constants:

```python
SOCIAL_CLASS_COMPUTED_FIELDS  # :54-71 = {"consumption_needs", "w_paid", "v_produced",
                              #           "contradiction_fields", "field_derivatives"}
TERRITORY_EXCLUDED_FIELDS     # :73-87 = {"p_acquiescence", "p_revolution", "dpd_state",
                              #  "dependency_ratio", "legitimation_index", "legitimation_crisis",
                              #  "legitimation_state", "mobility_params", "adjusted_p_to_d_prime",
                              #  "transmitted_ideology", "differential_p_to_d_prime"}
INSTITUTION_EXCLUDED_FIELDS   # :89-94 = {"hegemonic_fraction", "reproduction_capacity"}
ORGANIZATION_EXCLUDED_FIELDS  # :96-101 = {"effective_capacity", "composition_cache"}
```

Consumed at runtime by three property tests (single-source-of-truth contract, spec-055 FR-010):
`tests/property/invariants/test_round_trip_identity.py:25-26,44-45,54-55`, `test_consequence_after_actions.py:36-37,56-57`, `test_material_base_ordering.py:32-33,52-53`. Additions to the sets propagate to those tests automatically (unknown keys in `model_dump(exclude=...)` are ignored by pydantic — safe).

### 0.2 `from_graph` node-type dispatch — `world_state.py:484-505` (claim ✓, NO sovereign branch)

```python
        for node_id, data in G.nodes(data=True):
            node_type = data.get("_node_type", "social_class")
            # Create a copy without _node_type for model construction
            node_data = {k: v for k, v in data.items() if k not in ("_node_type", "type")}

            if node_type == "territory":
                territories[node_id] = _reconstruct_territory(node_data)
            elif node_type == "organization":
                organizations[node_id] = _reconstruct_organization(node_data)
            elif node_type == "key_figure":
                key_figures_dict[node_id] = KeyFigure(**node_data)
            elif node_type == "institution":
                institutions_dict[node_id] = _reconstruct_institution(node_data)
            elif node_type == "industry":
                industries_dict[node_id] = IndustryHyperedge(**node_data)
            else:
                # Reconstruct SocialClass (default for backward compatibility)
                entity_data = {
                    k: v for k, v in node_data.items() if k not in SOCIAL_CLASS_COMPUTED_FIELDS
                }
                entities[node_id] = SocialClass(**entity_data)
```

Any unknown `_node_type` (`"sovereign"`, `"faction"`, `"balkanization_faction"`, `"community"`) falls into the `else` and is force-fed to `SocialClass`, which has `model_config = ConfigDict(extra="forbid", ...)` (`src/babylon/models/entities/social_class.py:201-202`) → `ValidationError` crash. `web/game/engine_bridge.py:605-614` (`_build_balkanization_block` docstring) already documents this exact gap and works around it by reading the raw graph.

### 0.3 WorldState lacks `sovereigns`; Sovereign model (claims ✓)

- `WorldState` fields (`world_state.py:220-306`): tick, entities, territories, relationships, event_log, events, economy, state_finances, contradiction_frames, opposition_states, organizations, key_figures, institutions, **institution_relations (:297-300)**, industries. **No `sovereigns`.** `from_graph`'s return (:530-544) passes neither `sovereigns` nor `institution_relations` → institution_relations silently resets to `[]` on every round-trip.
- `src/babylon/models/entities/sovereign.py`: `class Sovereign` spans **:35-114** (file is 115 lines). Module-level circular import at **:30**:
  ```python
  from babylon.formulas.balkanization import calculate_metabolic_impact
  ```
  `metabolic_impact` is a `@computed_field` property at **:77-88** returning `calculate_metabolic_impact(self.extraction_policy)`. Being a computed field, it IS included in `model_dump()` — the new reconstruction path must exclude it.
- Circular import **reproduced live**: `poetry run python -c "import babylon.formulas.balkanization"` fails with `ImportError: cannot import name 'calculate_metabolic_impact' from partially initialized module` — chain: `formulas.balkanization` → `babylon.models.enums` (balkanization.py:17) → `babylon.models` `__init__` → `entities/__init__.py:77` (`from babylon.models.entities.sovereign import Sovereign`) → `sovereign.py:30` back into the half-initialized formulas module. This is the exact `mise run test:doctest` breaker recorded in memory. `Sovereign` model config is `ConfigDict(frozen=True)` only (extra defaults to ignore). Required fields with no defaults: `id` (pattern `^SOV_[A-Z][A-Z0-9_]*$`), `name`, `sovereignty_type`, `color_hex`, `extraction_policy`, `founded_tick`.

### 0.4 `to_graph` never emits sovereigns; writers omit `id`/`name` (claims ✓)

- `to_graph` (`world_state.py:312-413`) adds social_class (:372-373), territory (:376-377), organization + PRESENCE (:380-385), key_figure (:388-389), institution + PRESENCE/HOUSES (:392-401), industry (:404-405), relationship edges (:408-411). **No sovereign emission, no institution_relations metadata.**
- `src/babylon/engine/systems/collapse_transition.py:149-159` (collapse successor):
  ```python
              wrapped.add_node(
                  new_sov_id,
                  "sovereign",
                  name=f"Successor of {sovereign_id}",
                  sovereignty_type="provisional",
                  legitimacy=0.5,
                  color_hex="#7f7f7f",
                  ruling_faction_id=faction_id,
                  extraction_policy=_extraction_policy_for_faction(wrapped, faction_id),
                  founded_tick=tick,
              )
  ```
  and **:220-230** (secession breakaway, `sovereignty_type="secessionist"`, `color_hex="#ff7f00"`, `name=f"Breakaway from {parent_id}"`). Both payloads **lack `id`**. (`_extraction_policy_for_faction` at :300-320 returns a plain `str` like `"continue"` — pydantic coerces to the `ExtractionPolicy` StrEnum fine. Generated ids `SOV_AUTO_T{tick}_F..._{n}` / `SOV_BREAK_T{tick}_F...` at :145-147/:218-219 satisfy the `^SOV_` pattern.)
- `src/babylon/engine/systems/decomposition.py:240-251` (`_create_target_entity`):
  ```python
          graph.add_node(
              new_id,
              "social_class",
              role=role.value,
              active=False,
              population=0,
              wealth=0.0,
              county_fips=la_data.get("county_fips"),
              subsistence_threshold=la_data.get("subsistence_threshold", 0.0),
              s_bio=la_data.get("s_bio", 0.01),
              s_class=la_data.get("s_class", 0.0),
          )
  ```
  Payload lacks **`id` AND `name`** — both required on `SocialClass` (`social_class.py:286-295`: `id` pattern `^C[0-9]{3,}$`, `name` min_length=1). `_derive_entity_id` (decomposition.py:35-49) produces pattern-valid `C\d{3}` ids, so injecting `id` works; `name` must be added at the writer.

### 0.5 `threat_score` (claim ✓ — and it is a CRASH, not a drop)

Written by `CommunitySystem._compute_threat_scores` — `src/babylon/engine/systems/community.py:580` (`graph.update_node(node_id, threat_score=0.0)`) and **:598** (`graph.update_node(node_id, threat_score=score)`), keyed by agent (social_class) node ids. `threat_score` is **not** a `SocialClass` field (verified: no match in social_class.py) and **not** in `SOCIAL_CLASS_COMPUTED_FIELDS`; with `extra="forbid"` the next `from_graph` raises `ValidationError`. Latent today only because `agent_memberships` is empty in default runs. Note `community_cost_modifier` (written at community.py:611) IS a SocialClass field (:419) — no action needed.

Additional minefield entries found during verification (same fix pattern):
- `src/babylon/engine/systems/metabolism.py:86` — `graph.update_node(territory_id, habitability=new_hab)`, gated on SovereigntySystem's `balkanization.metabolic_impact_by_territory` persistent data (i.e. armed the moment sovereigns exist). `Territory` has `extra="forbid"` (territory.py:51) and **no `habitability` field** → crash.
- `src/babylon/engine/systems/dispossession_events.py:114` — `protocol.update_node(node_id, dispossession_intensity=intensity)` on territory nodes; not a Territory field → crash. Currently dead because :61 queries `node_type="Territory"` (capital-T case bug — Phase 2.2 will arm it). Also :97 writes `wealth` onto territory nodes (no Territory `wealth` field) — only fires when `wealth` already exists on the node; **flag to the Phase 2.2 owner, do not paper over with an exclusion**.

### 0.6 `_validate_event` — `world_state.py:104-129` (claim ✓, mechanism confirmed)

```python
    if "kind" not in data and "event_type" in data:
        et = data["event_type"]
        # Mutate in place: event_type values map 1:1 to kind values
        data = {**data, "kind": et if isinstance(et, str) else et.value}
    if "kind" in data:
        return TickEventAdapter.validate_python(data)
```

`TickEvent` (`src/babylon/models/events/_legacy.py:1180-1201`) is a discriminated union over exactly **19** leaf variants; `EVENT_CLASS_MAP` (:1124-1145) keys are the same 19 `EventType.X.value` strings, and each equals its class's `kind` literal (spot-verified incl. the three `calibration_warning.*` values). `EventType` (`src/babylon/models/enums/events.py:30`) now has **87 members** (regex count of `^    NAME = "` — the "79" in CLAUDE.md and the task's "60/79" are stale; the real number is **68 of 87** non-union types). For any of those 68, the code above injects `kind` then hands it to the adapter → pydantic `union_tag_invalid` `ValidationError` → replay crash. The existing bare fallback (:118-129) is unreachable for any dict carrying `event_type`.

Note: `simulation_engine.step()` (:728-736) only stores union-type events (its `_convert_bus_event_to_pydantic` returns `None` for the rest at :603-606 — that's the silent-drop sibling of this crash), so the crash arms whenever a caller places a bare `SimulationEvent` (public field type `list[SimulationEvent]`) into `WorldState.events` and round-trips.

### 0.7 Edge merge — `src/babylon/engine/graph.py` (claims ✓)

- `:79` — `rx.PyDiGraph(multigraph=False)` core; `:83` — `self._edge_payload: dict[tuple[str, str], EdgePayload] = {}` (keyed by pair only, no edge_type).
- `add_edge` merge at **:240-243**:
  ```python
          payload = self._normalize_edge_payload(edge_type, weight, attributes)
          key = self._stored_edge_key(source, target)
          if key is not None:
              self._edge_payload[key].update(payload)
              return
  ```
  Two Relationships on one `(source, target)` pair with different `edge_type`s collapse to one edge, last-writer-wins on `edge_type`. `Relationship` (`src/babylon/models/entities/relationship.py:76-119`) carries `source_id`, `target_id`, `edge_type` (+ value_flow, tension, description, subsidy_cap, solidarity_strength) — sufficient to detect the collision in a `to_graph` pre-scan. The Hypothesis strategy (`tests/property/strategies/worldstate.py:74-98`) already dedupes by `(source, target)` and its comment (:74-79) codifies the collapse as "not a bug" — update that comment when you invert the contract.

### 0.8 C.1 gate — DRIFT: `src/babylon/engine/system_registry.py` does NOT exist

`all_systems()` lives at **`tests/property/harness/system_registry.py:38`** (pkgutil auto-discovery over `babylon.engine.systems`, `_MIN_EXPECTED_SYSTEMS = 21` at :28, `lru_cache`d, exported via `tests/property/harness/__init__.py`). The spec-054 harness (`tests/property/harness/bound_harness.py:89-101`) already demonstrates the run-one-system-then-`from_graph` pattern:
```python
        graph = pre.to_graph()
        runner(graph, services, ctx)
        post = WorldState.from_graph(graph, tick=pre.tick + 1)
```
It passes today only because `worldstate_strategy()` never seeds sovereigns/communities, so the crashing systems no-op.

---

## 1. Ordered implementation (one conventional commit per step; TDD red-first inside each)

Branch from `dev`: `git checkout -b fix/from-graph-safety`.

### Step 1 — `fix(models): break sovereign→balkanization circular import`

**RED**: new `tests/unit/formulas/test_balkanization_import.py` (dir exists):
```python
"""Regression: babylon.formulas.balkanization must be importable FIRST.

The module-level Sovereign import of calculate_metabolic_impact created a
models <-> formulas cycle that broke any process whose first babylon import
was formulas.balkanization (e.g. pytest --doctest-modules).
"""

from __future__ import annotations

import subprocess
import sys

import pytest


@pytest.mark.unit
def test_balkanization_imports_standalone() -> None:
    proc = subprocess.run(
        [sys.executable, "-c", "import babylon.formulas.balkanization"],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
```
Fails today (reproduced live).

**GREEN**: in `src/babylon/models/entities/sovereign.py` delete line 30 (`from babylon.formulas.balkanization import calculate_metabolic_impact`) and make the import runtime-local inside the property (:77-88), matching the `world_state.py:342-344` precedent:
```python
    @computed_field  # type: ignore[prop-decorator]
    @property
    def metabolic_impact(self) -> float:
        """... (docstring unchanged) ..."""
        # Runtime-local import: models MUST NOT import formulas at module
        # level — formulas.balkanization imports babylon.models.enums back,
        # so a module-level import here deadlocks any process whose first
        # babylon import is formulas.balkanization (doctest, tooling).
        from babylon.formulas.balkanization import calculate_metabolic_impact

        return calculate_metabolic_impact(self.extraction_policy)
```
Verify: the new test passes; `mise run test:q -- tests/unit/balkanization tests/unit/models/test_enums.py` stays green; re-run `mise run test:doctest` and note the delta (other doctest failures may remain — do not chase them here).

### Step 2 — `feat(models): WorldState.sovereigns field + sovereign round-trip`

**RED** (add to `tests/unit/models/test_graph_roundtrip.py`, mirroring the class style there):
1. `WorldState(sovereigns={...})` accepts a `Sovereign`; `to_graph()` produces a node with `_node_type == "sovereign"`; `from_graph` returns an equal `sovereigns` dict (compare `model_dump()`).
2. A graph node written the way `CollapseTransitionSystem` writes it (no `id` attr — use `G.add_node("SOV_TEST", _node_type="sovereign", name="X", sovereignty_type="provisional", legitimacy=0.5, color_hex="#7f7f7f", ruling_faction_id=None, extraction_policy="continue", founded_tick=0)`) reconstructs with `id == "SOV_TEST"` instead of crashing. (Today: `ValidationError` from `SocialClass(extra="forbid")`.)

**GREEN** edits in `src/babylon/models/world_state.py`:
- Import (after :35 block): `from babylon.models.entities.sovereign import Sovereign` (safe post-Step-1; no cycle — sovereign no longer imports formulas at module scope).
- New frozenset after `ORGANIZATION_EXCLUDED_FIELDS` (:96-101):
```python
SOVEREIGN_COMPUTED_FIELDS: Final[frozenset[str]] = frozenset(
    {
        # @computed_field — included in model_dump() by to_graph, not a
        # constructor argument (mirrors SocialClass.consumption_needs).
        "metabolic_impact",
    }
)
```
- Reconstruction helper after `_reconstruct_organization` (:165-192):
```python
def _reconstruct_sovereign(node_id: str, node_data: dict[str, Any]) -> Sovereign:
    """Reconstruct a Sovereign from graph node data (spec-070).

    Runtime writers (CollapseTransitionSystem) historically omitted ``id``
    from the node payload — the node id IS the sovereign id, so inject it
    when absent. Computed fields are excluded per SOVEREIGN_COMPUTED_FIELDS.
    """
    sov_data = {k: v for k, v in node_data.items() if k not in SOVEREIGN_COMPUTED_FIELDS}
    sov_data.setdefault("id", node_id)
    return Sovereign(**sov_data)
```
- Field after `industries` (:303-306):
```python
    # Sovereign authorities (spec-070 Balkanization)
    sovereigns: dict[str, Sovereign] = Field(
        default_factory=dict,
        description="Map of sovereign ID to Sovereign (spec-070 Balkanization)",
    )
```
- `to_graph` emission after the industry loop (:404-405):
```python
        # Add sovereign nodes with _node_type marker (spec-070)
        for sov_id, sov in self.sovereigns.items():
            G.add_node(sov_id, _node_type="sovereign", **sov.model_dump())
```
- `from_graph`: declare `sovereigns_dict: dict[str, Sovereign] = {}` alongside :477-482; insert dispatch branch after the `industry` elif (:497-498):
```python
            elif node_type == "sovereign":
                sovereigns_dict[node_id] = _reconstruct_sovereign(node_id, node_data)
```
and add `sovereigns=sovereigns_dict,` to the `cls(...)` return (:530-544).

Known residual (document in the commit body, do not fix here): CLAIMS edge attrs (`control_level`, `legal_status`, `fiscal_status`, `recognition_level`, `claimed_since_tick` — collapse_transition.py:160-170) are still flattened by the `from_graph` Relationship reconstruction (:509-528), which copies only the 5 known fields. `EdgeType.CLAIMS = "claims"` exists (`src/babylon/models/enums/topology.py:59`) so the edge itself survives without crashing. Rich-edge round-trip is the pre-existing "non-core Relationship attrs" gap (holistic-review item), out of Design B scope. Bridged-runner ticks are unaffected (graph persists across ticks; runner.py:378).

### Step 3 — `fix(engine): runtime node writers emit model-complete payloads`

**RED**: extend `tests/unit/balkanization/test_collapse_transition_system.py` (or a new focused test) — after driving a collapse (existing fixtures at :48-161 show the seeding pattern: `adapter.add_node("SOV_USA_FED", "sovereign", legitimacy=0.0)` + faction + claims), assert `WorldState.from_graph(graph, tick=1)` succeeds and the successor sovereign appears in `.sovereigns` with a `^SOV_AUTO_` id. For decomposition: drive `DecompositionSystem._create_target_entity` (or the full `_execute_decomposition` path) and assert `from_graph` reconstructs the new entity with `id == node_id` and a non-empty `name`. Both red before the writer edits (collapse case turns green already via Step 2's `setdefault`; keep it as the integration pin — decomposition stays red until this step).

**GREEN**:
- `collapse_transition.py:149-159` and :220-230 — add `id=new_sov_id,` as the first kwarg after the node-type positional (self-describing payload, consistent with `model_dump()`-sourced nodes):
```python
            wrapped.add_node(
                new_sov_id,
                "sovereign",
                id=new_sov_id,
                name=f"Successor of {sovereign_id}",
                ...
```
- `decomposition.py:240-251` — add `id=new_id,` and a deterministic `name` (no `hash()` — Constitution III.7):
```python
        graph.add_node(
            new_id,
            "social_class",
            id=new_id,
            name=f"{role.value} (decomposed from {la_id})",
            role=role.value,
            ...
```
Determinism note for Phase 2.R: these payload additions change node attribute sets, hence tick hashes, ONLY on runs where collapse/decomposition actually fire (both dormant in the canonical baseline). Confirm with `mise run qa:regression` — expected no-diff; if it diffs, coordinate baseline regen with Phase 2.R instead of regenerating ad hoc.

### Step 4 — `fix(models): exclude transient system-written node attrs in from_graph`

**RED** (pattern: copy `test_from_graph_drops_wage_accounting_attrs` at `tests/unit/models/test_graph_roundtrip.py:460`):
1. Set `threat_score=0.7` on a social_class node post-`to_graph`; `from_graph` must succeed and the entity must not carry it. (Today: `ValidationError`.)
2. Set `habitability=0.4` and `dispossession_intensity=0.2` on a territory node; `from_graph` must succeed. (Today: `ValidationError` — Territory `extra="forbid"`, territory.py:51.)

**GREEN** in `world_state.py`:
- Append to `SOCIAL_CLASS_COMPUTED_FIELDS` (:54-71):
```python
        # CommunitySystem per-tick threat assessment (community.py
        # _compute_threat_scores) — transient graph-only attr, not a
        # SocialClass model field.
        "threat_score",
```
- Append to `TERRITORY_EXCLUDED_FIELDS` (:73-87):
```python
        # Spec-070 FR-043: MetabolismSystem writes sovereign-driven
        # habitability onto territory nodes; web derives display
        # habitability from biocapacity — not a Territory model field.
        "habitability",
        # DispossessionEventSystem per-tick intensity (armed once the
        # Phase-2.2 node_type case fix lands) — not a Territory field.
        "dispossession_intensity",
```
The three spec-055 property tests consume these sets at runtime and adapt automatically. Leave `dispossession_events.py:97`'s territory-`wealth` write alone — hand that hazard to Phase 2.2 (it silently no-ops today and an exclusion would eat the transfer).

### Step 5 — `fix(models): round-trip institution_relations via graph metadata`

**RED** (in `test_graph_roundtrip.py`): a `WorldState` with one `InstitutionOrgRelation` (model at `src/babylon/models/entities/institution.py:218+`; only `institution_id`/`organization_id` required) must survive `to_graph`→`from_graph` (compare `model_dump()`). Today `restored.institution_relations == []`.

**GREEN** — exact `state_finances` precedent (to_graph :351-354, from_graph :445-448):
- `to_graph`, after the events metadata block (:367-369):
```python
        # Store institution-org housing relations in graph metadata (Feature
        # 040). Relations are richer than the HOUSES edges to_graph derives
        # from housed_org_ids, so round-trip them via G.graph like
        # state_finances (Spec 055 lossless round-trip).
        G.graph["institution_relations"] = [r.model_dump() for r in self.institution_relations]
```
- `from_graph`, after the contradiction_frames block (:450-454):
```python
        # Reconstruct institution-org relations from graph metadata (Feature 040)
        ir_data = G.graph.get("institution_relations", [])
        institution_relations = [InstitutionOrgRelation(**data) for data in ir_data]
```
and add `institution_relations=institution_relations,` to the return. (`InstitutionOrgRelation` is already imported at :27-30.)

### Step 6 — `fix(models): bare-SimulationEvent fallback for non-union event replay`

**RED** (in `test_graph_roundtrip.py`, next to `test_events_survive_round_trip` :32):
```python
    NON_UNION_TYPES = sorted(set(EventType) - set(EVENT_CLASS_MAP), key=str)

    @pytest.mark.parametrize("event_type", NON_UNION_TYPES)
    def test_non_union_event_types_survive_round_trip(self, event_type: EventType) -> None:
        state = WorldState(tick=0, events=[SimulationEvent(event_type=event_type, tick=0)])
        restored = WorldState.from_graph(state.to_graph(), tick=0)
        assert len(restored.events) == 1
        assert restored.events[0].event_type is event_type
```
68 parametrized cases, all `ValidationError` (union_tag_invalid) today. Sanity-pin the count: `assert len(NON_UNION_TYPES) == len(EventType) - 19`.

**GREEN** — surgical edit to `_validate_event` (:112-129): gate the adapter on union membership; the existing fallback becomes reachable:
```python
    if "kind" not in data and "event_type" in data:
        et = data["event_type"]
        # Mutate in place: event_type values map 1:1 to kind values
        data = {**data, "kind": et if isinstance(et, str) else et.value}
    if "kind" in data and data["kind"] in EVENT_CLASS_MAP:
        # Only the 19 TickEvent leaf kinds are dispatchable; feeding any
        # other EventType (68 of 87) to the discriminated adapter raises
        # union_tag_invalid instead of replaying the event.
        return TickEventAdapter.validate_python(data)
    # Fallback: bare SimulationEvent (kind outside the union, or no
    # discriminator at all) — preserve replay instead of crashing.
```
(Keep :120-129 unchanged; `SimulationEvent` ignores the extra `kind` key — its config is `ConfigDict(frozen=True)` only, `_legacy.py:89`.) `EVENT_CLASS_MAP` keys were verified identical to the 19 `kind` literals, including the dotted `calibration_warning.*` trio (enums/events.py:138-142).

### Step 7 — `fix(models): to_graph pre-scan raises on same-pair edge_type collision`

**RED**:
```python
    def test_to_graph_raises_on_same_pair_edge_type_collision(self) -> None:
        state = _state_with_two_entities()  # C000, C001
        state = state.model_copy(update={"relationships": [
            Relationship(source_id="C000", target_id="C001", edge_type=EdgeType.EXPLOITATION),
            Relationship(source_id="C000", target_id="C001", edge_type=EdgeType.SOLIDARITY),
        ]})
        with pytest.raises(ValueError, match="edge collision"):
            state.to_graph()
```
Today: no raise; the second edge's attrs silently overwrite the first (graph.py:240-243).

**GREEN** — in `to_graph` immediately before the relationships loop (:407-411):
```python
        # BabylonGraph stores ONE edge per (source, target) pair (rustworkx
        # core is multigraph=False; add_edge merges payloads — see
        # engine/graph.py add_edge). Two Relationships on the same pair with
        # different edge_types would collapse last-writer-wins. Fail loud
        # rather than silently corrupt the round-trip (Design B).
        seen_edge_types: dict[tuple[str, str], EdgeType] = {}
        for rel in self.relationships:
            prior = seen_edge_types.get(rel.edge_tuple)
            if prior is not None and prior is not rel.edge_type:
                raise ValueError(
                    f"Relationship edge collision on {rel.edge_tuple}: "
                    f"{prior.value!r} vs {rel.edge_type.value!r} — BabylonGraph "
                    "stores one edge per (source, target) pair"
                )
            seen_edge_types[rel.edge_tuple] = rel.edge_type
```
Also update the now-inverted comment at `tests/property/strategies/worldstate.py:74-79` ("This is the real graph semantics, not a bug" → note that to_graph now raises on differing-type collisions; the strategy's pair-dedupe already satisfies the contract). Residuals to document, not fix: (a) same-pair SAME-type duplicates still merge silently (multiset contract unchanged); (b) synthetic PRESENCE/HOUSES edges (:383-401) can still merge into an explicit Relationship on the same pair — the pre-scan sees only `self.relationships`.

### Step 8 — `test(engine): C.1 per-system round-trip gate`

New file `tests/unit/engine/test_system_roundtrip.py` (does not exist; verified). Reuse the discovery registry and the bound-harness invocation pattern — do NOT re-implement discovery:

```python
"""C.1 gate: every engine System's graph mutations must survive
WorldState.from_graph on a minefield-seeded state.

Uses the spec-054 auto-discovery registry (tests/property/harness/
system_registry.py) so newly added Systems are covered automatically,
and the bound-harness invocation pattern (bound_harness.py:89-101).
"""

from __future__ import annotations

import pytest

from babylon.engine.context import TickContext
from babylon.engine.services import ServiceContainer
from babylon.models.entities.relationship import Relationship
from babylon.models.entities.sovereign import Sovereign
from babylon.models.enums import EdgeType, ExtractionPolicy, SocialRole, SovereigntyType
from babylon.models.world_state import WorldState
from tests.property.harness.system_registry import all_systems


def _minefield_state() -> WorldState:
    """Seed every node family from_graph must reconstruct, incl. a Sovereign."""
    ...  # 2 SocialClass (worker C000 / owner C001 via engine factories or direct),
    ...  # 1 Territory, EXPLOITATION + SOLIDARITY relationships (distinct pairs),
    ...  # 1 Sovereign(id="SOV_TEST", sovereignty_type=SovereigntyType.RECOGNIZED_STATE,
    ...  #             extraction_policy=ExtractionPolicy.CONTINUE, ruling_faction_id=None,
    ...  #             name="Test Sovereign", color_hex="#112233", founded_tick=0)


@pytest.mark.unit
@pytest.mark.parametrize("system_cls", all_systems(), ids=lambda c: c.__name__)
def test_single_system_step_round_trips(system_cls) -> None:
    state = _minefield_state()
    graph = state.to_graph()
    services = ServiceContainer.create()
    ctx = TickContext(tick=0)
    system_cls().step(graph, services, ctx)
    restored = WorldState.from_graph(graph, tick=1)  # must not raise
    assert restored.tick == 1
```
Plus one full-pipeline case (`from babylon.engine.simulation_engine import _DEFAULT_SYSTEMS, SimulationEngine`; `SimulationEngine(list(_DEFAULT_SYSTEMS)).run_tick(graph, services, ctx)` then `from_graph`), and one targeted collapse case: seed the sovereign with `legitimacy=0.0` plus a `balkanization_faction`-typed node and CLAIMS edges (copy the fixture shape from `tests/unit/balkanization/test_collapse_transition_system.py:48-161`), run `CollapseTransitionSystem` alone, assert `from_graph` succeeds and a `SOV_AUTO_*` successor lands in `.sovereigns`. `ServiceContainer.create()` takes all-optional args (`services.py:143-155`); the bound harness proves bare `create()` + `TickContext(tick=0)` suffices for every discovered system. Write this file's core cases FIRST (red against dev) — they are the integration proof for Steps 2-4; the per-system parametrization goes green as the steps land.

---

## 2. Existing coverage / skips

- **Direct coverage that must stay green**: `tests/unit/models/test_graph_roundtrip.py` (events + full-state round-trip; :460 is the drop-attr test pattern), `tests/unit/models/test_world_state_round_trip_spec066.py`, `tests/unit/models/test_world_state.py`, `tests/property/invariants/test_round_trip_identity.py` (INV-012; reads the frozensets at runtime), `test_consequence_after_actions.py`, `test_material_base_ordering.py`, `tests/unit/balkanization/*` (system behavior on raw graphs), `tests/unit/web/test_engine_bridge.py:850+` (reads `"faction"`/`"sovereign"` nodes raw — unaffected), `tests/unit/engine/test_event_conversion.py`.
- **Skipped tests to un-skip: NONE.** The only skips near these seams are runtime `pytest.skip(...)` guards on Postgres availability (`tests/integration/balkanization/test_postgres_persistence.py:42`, `test_audit_round_trip.py:63`) — they self-arm when Postgres is up; no marker removal applies.

## 3. Verification commands (run after each step; full set before merge)

```bash
# Step-scoped (fast, keeps --lf cache):
mise run test:q -- tests/unit/formulas/test_balkanization_import.py          # Step 1
mise run test:q -- tests/unit/models/test_graph_roundtrip.py                 # Steps 2,4,5,6,7
mise run test:q -- tests/unit/balkanization                                  # Steps 2,3
mise run test:q -- tests/unit/engine/test_system_roundtrip.py                # Step 8
mise run test:q -- tests/property/invariants/test_round_trip_identity.py tests/property/invariants/test_consequence_after_actions.py tests/property/invariants/test_material_base_ordering.py

# Circular import gone (Step 1 proof):
poetry run python -c "import babylon.formulas.balkanization"
mise run test:doctest        # was broken at HEAD by exactly this cycle; check the delta

# Quality gate (ruff line-length=100, mypy strict):
mise run check:quick
mise run test:unit

# Determinism guard (Step 3): expected NO diff on canonical baseline
mise run qa:regression
```

## 4. Out-of-scope hazards to hand off (do not fix on this branch)

1. `dispossession_events.py:61` `node_type="Territory"` case bug + its :97 territory-`wealth` write → Phase 2.2 owner (the `dispossession_intensity` exclusion in Step 4 pre-arms safety for that fix).
2. Node-type spelling split: engine systems query `"balkanization_faction"` (reactionary.py:215, faction_influence.py:164,200) while `web/game/engine_bridge.py` reads `"faction"` — faction nodes have NO production writer yet (tests/web only); a `factions` WorldState field is future spec-070 wiring, not Design B.
3. Rich CLAIMS/INFLUENCES edge attributes flattened by `from_graph` Relationship reconstruction (world_state.py:509-528) — pre-existing, affects only the facade path (bridged runner keeps the live graph).
4. `_convert_bus_event_to_pydantic` returning `None` for 68 event types (simulation_engine.py:603-606) — silent drop sibling of Step 6; a full typed-event surface is spec territory.
