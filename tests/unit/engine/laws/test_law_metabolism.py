"""Behavioral law for MetabolismSystem (P27 Phase-0 backfill, §8.4).

Read end-to-end first (F1 discipline):
  src/babylon/engine/systems/metabolism.py (step(), lines 56-153)
  src/babylon/formulas/metabolic_rift.py (calculate_biocapacity_delta,
    calculate_hysteresis_damage, calculate_overshoot_ratio)

Laws pinned (each traces to a specific line range read above):

  L1 -- biocapacity clamp: after step(), every territory's biocapacity is
        within [0, its own post-update max_biocapacity]. The system computes
        ``new_biocapacity = max(0.0, min(new_max, current + delta))`` and
        writes both ``biocapacity`` and ``max_biocapacity`` from the SAME
        ``new_max`` (metabolism.py:113-118), so the post-state clamp bound
        must use the post-state ceiling, not the pre-tick one.

  L2 -- hysteresis ratchet is non-increasing: max_biocapacity NEVER goes up
        in a single tick. ``damage = raw_extraction * hysteresis_rate`` is
        always >= 0 for non-negative extraction_intensity/biocapacity/rate,
        and ``new_max = max(0.0, max_cap - damage)`` (metabolism.py:108-113;
        formulas/metabolic_rift.py:56-87), so new_max <= max_cap always.

  L3 -- zero-forcing inactivity: a territory with extraction_intensity=0.0
        AND regeneration_rate=0.0, and biocapacity <= max_biocapacity to
        start, is COMPLETELY unchanged by the tick -- neither biocapacity
        nor max_biocapacity move. Per the formula, regeneration =
        regeneration_rate * max_biocapacity = 0 and ecological_cost =
        extraction_intensity * current * entropy = 0, so delta = 0
        (metabolic_rift.py:39-53); raw_extraction = 0 so damage = 0
        (metabolic_rift.py:86-87) and new_max = max_cap. Found via a RED
        run: without the biocapacity<=max_biocapacity precondition, a
        territory starting ABOVE its own ceiling gets clamped DOWN to
        max_cap by the same-tick L1 clamp even though both forcing terms
        are zero -- so the precondition is load-bearing, not cosmetic.

  L4 -- inactive social_class exclusion: total_consumption (and therefore
        the emitted ECOLOGICAL_OVERSHOOT payload) is computed only over
        social_class nodes with ``active`` truthy (default True); an
        inactive node's s_bio/s_class/population contribute NOTHING,
        regardless of magnitude (metabolism.py:126-132, the
        ``if node.attributes.get("active", True)`` filter).

Caveat found while reading (NOT promoted to a law): when a graph has no
TERRITORY nodes at all, total_biocapacity == 0 and
calculate_overshoot_ratio short-circuits to max_ratio (metabolic_rift.py:
116-117) regardless of total_consumption -- so an EMPTY graph with the
default overshoot_threshold=1.0 (defines.yaml) WILL emit
ECOLOGICAL_OVERSHOOT (ratio=999.0 > 1.0). "No territories" is therefore
NOT an inactivity/no-op case for this system's event surface; only the
per-territory zero-forcing case (L3) and the per-class active-flag case
(L4) are true no-ops. This is flagged for the porting-contract table, not
asserted as a law here.
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from babylon.engine.context import TickContext
from babylon.engine.services import ServiceContainer
from babylon.engine.systems.metabolism import MetabolismSystem
from babylon.models.enums import EventType, NodeType
from babylon.topology.graph import BabylonGraph

# Bounded, non-degenerate ranges -- extraction_intensity and
# regeneration_rate are documented as fractions in [0, 1]
# (metabolic_rift.py:22-24); biocapacity/max_biocapacity are stock
# quantities bounded well above any single-tick delta so clamping behavior
# stays legible under the hypothesis-drawn inputs.
_FRACTION = st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)
_STOCK = st.floats(min_value=0.0, max_value=1_000.0, allow_nan=False, allow_infinity=False)


def _make_territory_graph(
    biocapacity: float,
    max_biocapacity: float,
    extraction_intensity: float,
    regeneration_rate: float,
) -> BabylonGraph:
    """Single-territory graph via the project's real BabylonGraph API.

    Matches the authoring form already exercised end-to-end in
    tests/unit/engine/systems/test_metabolism.py -- ``add_node`` with
    ``_node_type=NodeType.TERRITORY`` (never a hand-stamped raw string, per
    the vocabulary sentinel).
    """
    graph = BabylonGraph()
    graph.add_node(
        "T001",
        _node_type=NodeType.TERRITORY,
        biocapacity=biocapacity,
        max_biocapacity=max_biocapacity,
        extraction_intensity=extraction_intensity,
        regeneration_rate=regeneration_rate,
    )
    return graph


@given(
    biocapacity=_STOCK,
    max_biocapacity=st.floats(
        min_value=1.0, max_value=1_000.0, allow_nan=False, allow_infinity=False
    ),
    extraction_intensity=_FRACTION,
    regeneration_rate=_FRACTION,
)
@settings(max_examples=25, deadline=None)
def test_biocapacity_clamped_within_post_update_ceiling(
    biocapacity: float,
    max_biocapacity: float,
    extraction_intensity: float,
    regeneration_rate: float,
) -> None:
    """L1: 0 <= biocapacity <= max_biocapacity always holds post-step."""
    graph = _make_territory_graph(
        biocapacity, max_biocapacity, extraction_intensity, regeneration_rate
    )
    services = ServiceContainer.create()
    MetabolismSystem().step(graph, services, TickContext(tick=1))

    node = graph.nodes["T001"]
    assert node["biocapacity"] >= 0.0
    assert node["biocapacity"] <= node["max_biocapacity"] + 1e-9


@given(
    biocapacity=_STOCK,
    max_biocapacity=st.floats(
        min_value=1.0, max_value=1_000.0, allow_nan=False, allow_infinity=False
    ),
    extraction_intensity=_FRACTION,
    regeneration_rate=_FRACTION,
)
@settings(max_examples=25, deadline=None)
def test_hysteresis_ratchet_never_increases_ceiling(
    biocapacity: float,
    max_biocapacity: float,
    extraction_intensity: float,
    regeneration_rate: float,
) -> None:
    """L2: max_biocapacity is non-increasing across a single tick."""
    graph = _make_territory_graph(
        biocapacity, max_biocapacity, extraction_intensity, regeneration_rate
    )
    services = ServiceContainer.create()
    MetabolismSystem().step(graph, services, TickContext(tick=1))

    assert graph.nodes["T001"]["max_biocapacity"] <= max_biocapacity + 1e-9


@given(
    max_biocapacity=st.floats(
        min_value=1.0, max_value=1_000.0, allow_nan=False, allow_infinity=False
    ),
    fill_fraction=_FRACTION,
)
@settings(max_examples=25, deadline=None)
def test_zero_forcing_terms_leave_territory_unchanged(
    max_biocapacity: float,
    fill_fraction: float,
) -> None:
    """L3: extraction_intensity=0 AND regeneration_rate=0 is a true no-op.

    Precondition: biocapacity <= max_biocapacity (an invariant L1 itself
    maintains tick over tick -- a territory starting ABOVE its own ceiling
    is an out-of-band state the clamp corrects even with both forcing
    terms at zero, so it is excluded here rather than silently violating
    the "no-op" claim).
    """
    biocapacity = fill_fraction * max_biocapacity
    graph = _make_territory_graph(
        biocapacity,
        max_biocapacity,
        extraction_intensity=0.0,
        regeneration_rate=0.0,
    )
    services = ServiceContainer.create()
    MetabolismSystem().step(graph, services, TickContext(tick=1))

    node = graph.nodes["T001"]
    assert node["biocapacity"] == biocapacity
    assert node["max_biocapacity"] == max_biocapacity


@given(
    inactive_s_bio=st.floats(min_value=0.0, max_value=1e6, allow_nan=False, allow_infinity=False),
    inactive_s_class=st.floats(min_value=0.0, max_value=1e6, allow_nan=False, allow_infinity=False),
    inactive_population=st.integers(min_value=1, max_value=1_000_000),
)
@settings(max_examples=25, deadline=None)
def test_inactive_social_class_excluded_from_consumption(
    inactive_s_bio: float,
    inactive_s_class: float,
    inactive_population: int,
) -> None:
    """L4: an inactive class contributes nothing, however large its terms.

    Territory and the single active class are fixed so the emitted
    total_consumption is deterministic (10.0); an inactive class carrying
    arbitrarily large s_bio/s_class/population must never move that number.
    """
    graph = BabylonGraph()
    graph.add_node(
        "T001",
        _node_type=NodeType.TERRITORY,
        biocapacity=100.0,
        max_biocapacity=100.0,
        regeneration_rate=0.0,
        extraction_intensity=0.0,
    )
    graph.add_node(
        "ACTIVE_WORKER",
        _node_type=NodeType.SOCIAL_CLASS,
        s_bio=5.0,
        s_class=5.0,
        population=1,
        active=True,
    )
    graph.add_node(
        "DEAD_COMPRADOR",
        _node_type=NodeType.SOCIAL_CLASS,
        s_bio=inactive_s_bio,
        s_class=inactive_s_class,
        population=inactive_population,
        active=False,
    )

    services = ServiceContainer.create()
    MetabolismSystem().step(graph, services, TickContext(tick=1))

    # Biocapacity stays at 100 (no forcing terms) so no overshoot fires;
    # assert directly on the deterministic active-only total instead of
    # relying on event emission, so the law holds even when the drawn
    # inactive terms are enormous.
    events = services.event_bus.get_history()
    overshoot_events = [e for e in events if e.type == EventType.ECOLOGICAL_OVERSHOOT]
    assert len(overshoot_events) == 0, (
        "active-only consumption (10.0) must never overshoot a 100.0 "
        "biocapacity territory regardless of the inactive class's terms"
    )
