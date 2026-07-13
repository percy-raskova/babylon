# Seam Wiring Punch-List

**Generated from the Seam Observatory sentinels — a living artifact, not a hand-written list.**
Regenerate anytime with:

```bash
poetry run python tools/sentinel_check.py seam --check   # or: mise run check:seams
```

Every row below is a line the sentinels emit on the real tree (80 advisory findings at time of
writing, `feature/17-living-engine`). It is the map for the UI/UX wiring pass: the sentinels were
built to prove that **every quantity the engine computes is routed somewhere into the interface and
actually used** — or is flagged here as unrouted. Nothing computed falls on the floor unaccounted for.

Each row is one decision: **expose** it (register + serialize + type + render), **wire** it (the
serializer exists but the contract/consumer is missing), or **delete** it (dead/relabelled — remove
the promise). None of these gate the build; they are the honest backlog the "proper UI" gets built on.

The findings sort into three data-flow gaps, plus two adjacent vocabularies.

---

## Gap 1 — Computed → not emitted (the "created but not routed" leak)

The engine stamps these onto the graph every tick; **no serializer sends them to the UI**. This is the
richest untapped surface — real economic signal (crisis phase, financialisation, debt, unemployment,
the falling rate of profit's inputs) computed and thrown away before the player can see it.

**26 unregistered `tick_*` attrs** (source: `check_tick_coverage`, from
`src/babylon/domain/economics/tick/graph_bridge.py`):

`tick_accumulated_debt`, `tick_bifurcation_score`, `tick_capital_stock`, `tick_claims_exceed_surplus`,
`tick_class_distribution`, `tick_commodity_overhang`, `tick_crisis_duration`, `tick_crisis_phase`,
`tick_financial_crisis_signals`, `tick_financialization_share`, `tick_ground_rent`,
`tick_housing_fictitious_fraction`, `tick_interest_burden`, `tick_inventory_diagnosis`,
`tick_liquidity_ratio`, `tick_median_wage`, `tick_profit_of_enterprise`, `tick_realization_crisis`,
`tick_rentier_share`, `tick_replacement_cycle`, `tick_reproduction_crisis`, `tick_supply_chain_depth`,
`tick_throughput_position`, `tick_turnover_crisis`, `tick_unemployment_rate`, `tick_wage_compression`.

**Decision per attr:** expose (register as an observable + emit through a serializer + surface in a
panel/inspector), or delete (retire the computation if it truly has no player-facing role).

---

## Gap 2 — Emitted / reachable → not consumed (unrouted or untyped seams)

The backend produces (or claims to produce) these, but no typed UI contract consumes them.

### 2a — Potential broken endpoints (INVESTIGATE FIRST)

Views call these serializers, but **no definition exists anywhere in `web/game`** (checked the real
bridge *and* the stub). Either an inherited/mixin method the static scan can't see, or a genuine
runtime 500 on the endpoint. High priority — a dark endpoint reads as "no data" to the player.

| Endpoint | Serializer called | Status |
|---|---|---|
| `games/*/orgs/network` | `get_org_network` | **undefined in web/game** — investigate/fix |
| `games/*/hypergraph/communities` | `get_hypergraph_communities` | **undefined in web/game** — investigate/fix |
| `games/*/explain` | `get_explain` | stub-only (`stub_bridge.py`); real view uses `explain_metric()` directly — confirm the fallback is dead code and drop it |

### 2b — Serializers with no typed contract (`Untyped` in the manifest — wire a response type)

Each has a working `bridge.get_*` serializer but `endpoints.ts` declares its response `Untyped`.
Give each a real TS interface (derived from the serializer's emitted keys), then a consumer:

- **Dashboards:** `games/*/edges` (`get_edges_dashboard`), `games/*/organizations`
  (`get_organizations_dashboard`), `games/*/state-apparatus` (`get_state_apparatus_dashboard`),
  `games/*/exposure` (`get_county_import_exposure`), `games/*/trade-panel` (`get_trade_panel`).
- **Inspectors:** `games/*/node/*`, `games/*/org/*`, `games/*/community/*`, `games/*/edge/*`,
  `games/*/hex/*` (adapter-decoded to `RawEntity` client-side today — a typed inspector contract would
  let the sweep field-check them), plus histories `games/*/org/*/history`, `games/*/territory/*/history`.
- **Action targets:** `games/*/actions/{educate,aid,attack,mobilize,move,investigate,reproduce,negotiate}/targets`
  and `games/*/actions/available` (`get_*_targets` / `get_available_actions`).

### 2c — Structurally opaque returns (blind spots — not field-checkable as-is)

Honest limits of static extraction; not necessarily wrong, just unverifiable at the seam:

- `games/*/state` (`get_snapshot`) and `games/*/wire` (`get_wire_feed`) — **delegated** returns
  (assembled via a helper, not a literal dict). A typed interface on the manifest side would still let
  the consumer be checked even if the emitter can't.
- `games/*/map` (`get_map_snapshot`) — external `FeatureCollection` (geojson); per-feature props are
  covered by the Sensor-3 admin-emission check (Gap 3).

---

## Gap 3 — Declared → not emitted (the UI promises it, the backend never sends it → silent blank)

A component reading these gets `undefined`. Either emit the field from the serializer, or drop it from
the interface.

**`EconomyDashboardPayload` (`games/*/economy`, serializer `get_economy`) — 8 phantoms:**
`current_super_wage_rate`, `imperial_rent_pool`, `occ`, `profit_rate`, `tick`, `tribute_flow_total`,
`wage_flow_total`, `wealth_by_class_role`.
*(Note: several of these — `profit_rate`, `occ`, `imperial_rent_pool` — are exactly the Program-17 Φ
metrics computed per-tick in Gap 1. The economy dashboard promises them; the serializer never wires
them through. This is the single highest-value fix: the data exists, the contract exists, only the
serializer emission is missing.)*

**`AdminFeatureProperties` (map features, emitter `_aggregate_hex_features`) — 4 phantoms**
(source: Sensor-3 `check_admin_feature_emission`): `biocapacity`, `consciousness`, `rent`, `wealth`.

---

## Adjacent — narration & event vocabularies (product-scoped, kept advisory)

Not strictly seam-serialization, but the same "computed content never reaches the player" family.

- **6 crafted-but-unreachable narrator templates** (`check_narrator_vocabulary`): `ecological_collapse`,
  `eviction_pipeline`, `fascist_consolidation`, `heat_change`, `revolutionary_victory`,
  `solidarity_formed`. Fix = build outcome-aware narration (a feature) or delete the crafted content —
  an owner product decision.
- **45 of 79 `EventType`s drop to `None`** at the bus→pydantic boundary (`check_event_coverage`) and
  never reach the wire. Many are intentionally non-narrative (calibration/internal); owner triages
  which deserve conversion.

---

## How this stays honest

This file is a **snapshot**; the sentinels are the source of truth. When you wire an item, the next
`mise run check:seams` run drops it from the findings automatically — coverage is a pure function of
the current routes + `endpoints.ts` manifest + serializers, with no hand-maintained mapping table. As
the UI/UX pass wires the punch-list down, regenerate this file to watch it shrink.
