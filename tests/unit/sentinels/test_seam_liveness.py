"""Seam Sensor-2 (liveness) — the "would have screamed Φ blank at tick 1" sensor.

Sensor 1 (``test_seam_registry_check.py``) proves an observable is *wired* end to
end (computed → serialized → registered). Sensor 2 proves it is *alive*: that a
``MUST_BE_LIVE`` observable in
:data:`babylon.sentinels.seam.registry.SEAM_REGISTRY` actually resolves to a
non-null, non-default value on real tick state rather than defaulting to a blank
the whole way down the seam. This is Babylon's mechanical enforcement of
Constitution III.11 (Loud Failure) for the *silent blank* failure mode.

The liveness *logic* lives here, not in the layer-0.5 package, because it needs a
live ``WorldState`` and its ``to_graph`` bridge — above the sentinels' import
boundary. Only the declared registry (what MUST be live) is in the package.

Scope. Only ``LivenessClass.MUST_BE_LIVE`` MAP observables gate here. The
``DECLARED_CONDITIONAL`` Φ / derived-rate family (``profit_rate``,
``exploitation_rate``, ``occ``, ``imperial_rent``) is deliberately SKIPPED: those
depend on per-county IMPORT_USE + QCEW reference data the synthetic
``imperial_circuit`` scenario never loads, so they are checked nightly against
the Parquet reference DB, not on the fast-gate substrate. Wave 2 W2.4's
``throughput_position``/``agitation`` join that same DECLARED_CONDITIONAL,
skipped-here family (year-boundary + calculator wiring / legitimately-0.0-at-
tick-0, respectively) — only ``territory_type`` (MUST_BE_LIVE, a plain
``Territory`` model field) is new gated scope for this sensor.

Honesty (Amendment Q / III.12). Of the seven ``MUST_BE_LIVE`` map observables,
exactly one (``territory_type``) is VALUE-live on this fast-gate substrate — see
:func:`test_shared_tick_map_liveness_partition` and the module docstring's
"Reality" note below. That is not a loosened check; it is the true altitude
finding: most of the ``/map/`` surface is lit by the web ``EngineBridge`` against
the hex / Postgres projection, **not** by a bare-engine run of a synthetic
2-territory scenario whose ``to_graph()`` carries only ``Territory`` model
fields — ``territory_type`` is the one exception, itself a plain ``Territory``
field needing no bridge derivation. So this file asserts (a) the probe's
*discrimination* — proven on injected live / dark / absent fixtures — and (b)
the *exact honest partition* of the seven observables on ``shared_tick``, a
characterization contract that reds the moment that wiring changes. It does
**not** fake a green "all-live" gate the substrate cannot honestly produce.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

import pytest

from babylon.sentinels.dynamic import DynamicArtifact
from babylon.sentinels.seam.registry import SEAM_REGISTRY
from babylon.sentinels.seam.types import LivenessClass, SeamEntry, SeamScope

pytestmark = pytest.mark.unit

#: The seven MUST_BE_LIVE MAP wire keys this sensor is responsible for. Pinned as
#: a literal so a registry drift (a MUST_BE_LIVE row added/removed/reclassified)
#: reds :func:`test_must_be_live_scope_matches_registry` instead of silently
#: shrinking the sensor's remit. Wave 2 W2.4 adds ``territory_type`` (the real
#: ``Territory.territory_type`` enum — a required, defaulted model field, so it
#: is always present, never fabricated).
_EXPECTED_MUST_BE_LIVE: frozenset[str] = frozenset(
    {
        "heat",
        "population",
        "habitability",
        "org_presence",
        "dominant_class",
        "solidarity_index",
        "territory_type",
    }
)


class Liveness(StrEnum):
    """The verdict :func:`probe_liveness` returns for one observable.

    :cvar LIVE: present on at least one territory node with a non-default value.
    :cvar DARK_DEFAULT: present on the graph but default-valued everywhere
        (``0`` / ``0.0`` / ``""`` / ``False`` / ``None``) — the classic "computed
        but never populated, renders blank" failure.
    :cvar DARK_ABSENT: the payload attribute is on no territory node at all — the
        engine graph never carries it (e.g. a bridge-derived / hex-projected
        quantity, or a payload naming a renamed/never-written attr).
    """

    LIVE = "live"
    DARK_DEFAULT = "dark_default"
    DARK_ABSENT = "dark_absent"


def _is_default(value: Any) -> bool:
    """Return whether ``value`` is a blank-equivalent default (never a live datum).

    A ``MUST_BE_LIVE`` field holding one of these is indistinguishable, on the
    wire, from "never written" — so the probe treats it as dark.

    :param value: The serialized attribute value read off a territory node.
    :returns: ``True`` for ``None`` / numeric zero / empty string / ``False``.
    """
    if value is None:
        return True
    if isinstance(value, str):
        return value == ""
    # bool is a subclass of int; ``False`` and ``0``/``0.0`` are all dark.
    if isinstance(value, (int, float)):
        return value == 0
    return False


def territory_attr_dicts(graph: Any) -> list[dict[str, Any]]:
    """Extract the attribute dict of every ``territory`` node on a live graph.

    :param graph: A ``BabylonGraph`` (from ``WorldState.to_graph()``); only its
        ``nodes`` mapping is read, so this stays below the engine import weight.
    :returns: One attribute dict per territory node (empty list if none exist).
    """
    return [
        dict(graph.nodes[node_id])
        for node_id in graph.nodes
        if graph.nodes[node_id].get("_node_type") == "territory"
    ]


def probe_liveness(territory_attrs: list[dict[str, Any]], payload: str) -> Liveness:
    """Classify one observable's liveness across a set of territory attribute dicts.

    An observable is :attr:`Liveness.LIVE` if *any* territory node carries the
    payload attribute with a non-default value; :attr:`Liveness.DARK_ABSENT` if no
    node carries the attribute at all; :attr:`Liveness.DARK_DEFAULT` if it is
    present but default-valued on every node.

    :param territory_attrs: The per-territory attribute dicts
        (:func:`territory_attr_dicts`), or synthetic fixtures for the efficacy
        proofs.
    :param payload: The registry payload / graph attribute name to probe.
    :returns: The :class:`Liveness` verdict.
    """
    present_anywhere = False
    for attrs in territory_attrs:
        if payload not in attrs:
            continue
        present_anywhere = True
        if not _is_default(attrs[payload]):
            return Liveness.LIVE
    return Liveness.DARK_DEFAULT if present_anywhere else Liveness.DARK_ABSENT


def _must_be_live_map_entries(registry: tuple[SeamEntry, ...]) -> tuple[SeamEntry, ...]:
    """Return the MAP-scope, ``MUST_BE_LIVE`` rows this sensor gates.

    :param registry: The registry to filter (injectable so efficacy tests can
        supply a synthetic row).
    :returns: The subset of rows Sensor 2 asserts liveness for.
    """
    return tuple(
        e
        for e in registry
        if e.scope is SeamScope.MAP and e.liveness_class is LivenessClass.MUST_BE_LIVE
    )


def check_map_liveness(
    territory_attrs: list[dict[str, Any]],
    registry: tuple[SeamEntry, ...] = SEAM_REGISTRY,
) -> list[str]:
    """Report every ``MUST_BE_LIVE`` MAP observable that is not live on the graph.

    The sensor proper: for each gated row, probe the graph and record a loud,
    located violation naming the wire key, payload, and dark verdict when the
    observable fails to be :attr:`Liveness.LIVE`. An empty return means every
    gated observable was value-live.

    :param territory_attrs: Per-territory attribute dicts to probe against.
    :param registry: The registry to gate (injectable for the efficacy proofs).
    :returns: One violation string per dark ``MUST_BE_LIVE`` observable.
    """
    violations: list[str] = []
    for entry in _must_be_live_map_entries(registry):
        verdict = probe_liveness(territory_attrs, entry.payload)
        if verdict is not Liveness.LIVE:
            violations.append(
                f"{entry.key} (payload {entry.payload!r}) is {verdict.value} on the tick graph — "
                f"a MUST_BE_LIVE observable reading blank (owner_layer={entry.owner_layer!r})"
            )
    return violations


# --------------------------------------------------------------------------- #
# Scope guard — the sensor knows exactly what it is responsible for.
# --------------------------------------------------------------------------- #


def test_must_be_live_scope_matches_registry() -> None:
    """The gated set equals the six declared MUST_BE_LIVE MAP observables.

    Guards against a silently-shrinking remit: if a row is reclassified out of
    ``MUST_BE_LIVE`` (or a new one is added) the sensor's scope must be
    re-examined, not let drift. Also confirms the DECLARED_CONDITIONAL Φ /
    derived-rate family is *excluded* here (it is nightly, not fast-gate).
    """
    gated = {e.payload for e in _must_be_live_map_entries(SEAM_REGISTRY)}
    assert gated == set(_EXPECTED_MUST_BE_LIVE)

    conditional = {
        e.wire_keys[0]
        for e in SEAM_REGISTRY
        if e.scope is SeamScope.MAP and e.liveness_class is LivenessClass.DECLARED_CONDITIONAL
    }
    assert conditional == {
        "profit_rate",
        "exploitation_rate",
        "occ",
        "imperial_rent",
        # Wave 2 W2.4: throughput_position (year-boundary + calculator wiring)
        # and agitation (legitimately 0.0 at tick 0) join the DECLARED_CONDITIONAL
        # family alongside the derived-rate/Φ group above.
        "throughput_position",
        "agitation",
        # Audit Wave 4 straggler (task #76): centrality is non-null only for
        # a territory carrying a PRESENCE/HOUSES edge from an org/institution
        # in the (today sparse, wayne_county-only) org network.
        "centrality",
        # Wave 5 receptivity lens pair: honest-null for a tenant-less
        # territory or before EpistemicHorizonSystem has ever run this
        # session; mass_receptivity can also be legitimately exactly 0.0
        # (indistinguishable from Sensor 2's dark_default probe), which is
        # why it (and its categorical sibling vision_state, conditionally
        # PRESENT unlike territory_type) stay DECLARED_CONDITIONAL rather
        # than MUST_BE_LIVE — see registry.py's row-level reasoning.
        "mass_receptivity",
        "vision_state",
        # Wave 6 labor-market lens pair (tasks #87/#88): wage_pressure
        # (ReserveArmySystem) and dispossession_intensity (DispossessionEventSystem)
        # write NO attr at all for a territory with no reserve-army pressure / no
        # dispossession this tick — honest-null, so DECLARED_CONDITIONAL not
        # MUST_BE_LIVE (see registry.py:385/411 row-level reasoning).
        "wage_pressure",
        "dispossession_intensity",
    }
    assert gated.isdisjoint(conditional)


# --------------------------------------------------------------------------- #
# Efficacy — the probe discriminates live / default / absent, and the gate reds
# on a dark MUST_BE_LIVE observable. A green sensor that cannot red is worthless.
# --------------------------------------------------------------------------- #


def test_probe_reports_live_on_a_populated_value() -> None:
    """A territory carrying a non-default value probes :attr:`Liveness.LIVE`."""
    attrs = [{"_node_type": "territory", "heat": 0.0}, {"_node_type": "territory", "heat": 0.7}]
    assert probe_liveness(attrs, "heat") is Liveness.LIVE


def test_probe_flags_default_valued_attr_as_dark_default() -> None:
    """A present-but-zero attribute is DARK_DEFAULT — the "renders blank" case.

    This is the discrimination the whole sensor turns on: a field can be wired
    (Sensor 1 green) and present on the graph yet still be a blank on the wire.
    """
    attrs = [{"_node_type": "territory", "heat": 0.0}, {"_node_type": "territory", "heat": 0}]
    assert probe_liveness(attrs, "heat") is Liveness.DARK_DEFAULT


def test_probe_flags_never_written_attr_as_dark_absent() -> None:
    """A payload on no node at all is DARK_ABSENT — the renamed/never-written case."""
    attrs = [{"_node_type": "territory", "heat": 0.5}]
    assert probe_liveness(attrs, "__phi_never_written__") is Liveness.DARK_ABSENT


def test_gate_reds_on_a_fake_must_be_live_row_naming_a_dark_attr() -> None:
    """EFFICACY: the gate screams when a MUST_BE_LIVE row's payload is dark.

    The "would have screamed Φ blank at tick 1" proof. A synthetic MUST_BE_LIVE
    row whose payload names an attribute the engine never writes must produce a
    loud, located violation — over a graph where a *real* attribute (``heat``) IS
    present, so the red is attributable to the planted dark row, not the fixture.
    """
    live_graph = [{"_node_type": "territory", "heat": 0.9, "population": 5000}]
    planted = SeamEntry(
        payload="phi_hour_never_written",
        wire_keys=("imperial_rent_flow",),
        scope=SeamScope.MAP,
        owner_layer="test-injected-defect",
        liveness_class=LivenessClass.MUST_BE_LIVE,
        dtype="float",
    )

    violations = check_map_liveness(live_graph, registry=(planted,))

    assert len(violations) == 1, "sensor FAILED to scream on a dark MUST_BE_LIVE observable"
    assert "phi_hour_never_written" in violations[0]
    assert "dark_absent" in violations[0]


def test_gate_is_clean_when_every_gated_observable_is_live() -> None:
    """EFFICACY (positive): the gate goes GREEN when all gated payloads are live.

    Proves the sensor is not stuck-red — over a synthetic graph where every one of
    the seven MUST_BE_LIVE payloads carries a non-default value, the gate returns
    no violations. Without this, an always-red gate would be as useless as an
    always-green one.
    """
    live_node = {
        "_node_type": "territory",
        "heat": 0.4,
        "population": 1200,
        "habitability": 0.8,
        "org_presence": 0.3,
        "dominant_class": "periphery_proletariat",
        "solidarity_index": 0.6,
        "territory_type": "core",
    }
    assert check_map_liveness([live_node], registry=SEAM_REGISTRY) == []


# --------------------------------------------------------------------------- #
# Reality / invariant over the shared tick — the honest partition (Amendment Q).
# --------------------------------------------------------------------------- #


def test_shared_tick_has_territory_nodes(shared_tick: DynamicArtifact) -> None:
    """The substrate the partition is asserted over actually has territories.

    Guards :func:`test_shared_tick_map_liveness_partition` from being vacuous: a
    graph with no territory nodes would make every probe trivially DARK_ABSENT.
    """
    graph = shared_tick.final_state.to_graph()
    assert territory_attr_dicts(graph), "shared_tick graph has no territory nodes"


def test_shared_tick_map_liveness_partition(shared_tick: DynamicArtifact) -> None:
    """The honest liveness partition of the seven MUST_BE_LIVE observables.

    Reality on ``imperial_circuit`` (verified, not assumed):

    * ``heat`` and ``population`` are ``Territory`` model fields, so they survive
      ``to_graph()`` and are PRESENT — but this calm 2-territory scenario never
      drives either above its ``0`` default, so both probe :attr:`DARK_DEFAULT`.
    * ``habitability``, ``org_presence``, ``dominant_class`` and
      ``solidarity_index`` are NOT ``Territory`` model fields — they are
      bridge-derived / hex-projected at web-serialization time — so they are
      ABSENT from the engine ``to_graph()`` and probe :attr:`DARK_ABSENT`.
    * ``territory_type`` (Wave 2 W2.4) IS a ``Territory`` model field (unlike the
      four above) AND every territory carries a real, non-empty enum value
      (``TerritoryType.CORE``/``"core"`` on this scenario, never ``""``) — so
      unlike ``heat``/``population`` it genuinely probes :attr:`Liveness.LIVE`.

    Net: **1 of 7 is value-live** on this fast-gate substrate (``territory_type``
    — a real, always-populated engine field, not a "renders blank" case at all).
    The other 6 stay dark for the reasons above. That is the true altitude
    finding (most of the ``/map/`` surface is lit by the web ``EngineBridge``,
    not the bare engine — ``territory_type`` is the one exception, a plain
    model field that needs no bridge derivation), asserted here as an explicit
    characterization contract: if a future change starts lighting any of the
    other six on the engine graph — or ``territory_type`` stops being live — a
    verdict changes and this test reds, forcing a conscious registry / altitude
    review rather than a silent drift.
    """
    graph = shared_tick.final_state.to_graph()
    attrs = territory_attr_dicts(graph)

    verdicts = {
        entry.payload: probe_liveness(attrs, entry.payload)
        for entry in _must_be_live_map_entries(SEAM_REGISTRY)
    }

    present_but_default = {"heat", "population"}
    absent_from_graph = {
        "habitability",
        "org_presence",
        "dominant_class",
        "solidarity_index",
    }
    genuinely_live = {"territory_type"}

    for payload in present_but_default:
        assert verdicts[payload] is Liveness.DARK_DEFAULT, (
            f"{payload}: expected present-but-default on the engine graph, got "
            f"{verdicts[payload].value} — the map wiring may have changed altitude"
        )
    for payload in absent_from_graph:
        assert verdicts[payload] is Liveness.DARK_ABSENT, (
            f"{payload}: expected absent from the engine graph (bridge/hex-projected), got "
            f"{verdicts[payload].value} — it may now be engine-graph-resident; re-review"
        )
    for payload in genuinely_live:
        assert verdicts[payload] is Liveness.LIVE, (
            f"{payload}: expected genuinely live (a real, always-populated model field), got "
            f"{verdicts[payload].value} — re-review Territory.territory_type's default/wiring"
        )

    # The explicit, loud finding: exactly territory_type is value-live here.
    assert {p for p, v in verdicts.items() if v is Liveness.LIVE} == genuinely_live
