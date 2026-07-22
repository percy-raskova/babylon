"""System-level tests for Vol I U4 — the working day wired into consciousness.

``DefaultWorkingDayClassifier`` (``domain/economics/working_day/classifier.py``)
was fully built (Feature 021 US3) but had zero callers outside its own
package: ``ConsciousnessSystem``'s ``exploitation_visibility`` was computed
purely from ``wage_change``/``imperial_rent``, never from the Ch. 10
working-day regime (absolute vs. relative surplus-value extraction).

This module pins the wiring: ``ConsciousnessSystem`` must resolve
``services.productivity_data_source`` (via
``domain.economics.working_day.resolve_working_day_visibility_modifier``)
ONCE per tick and pass the result into
``compute_exploitation_visibility``'s ``working_day_modifier`` keyword, so
the working-day regime multiplicatively shapes how visible exploitation is
-- ABSOLUTE_DOMINANT (long hours) stays fully visible; RELATIVE_DOMINANT
(productivity/intensity gains) is dampened toward invisibility.
"""

from __future__ import annotations

import pytest

from babylon.config.defines import GameDefines, WorkingDayDefines
from babylon.domain.economics.working_day.types import WorkingDayState
from babylon.engine.context import TickContext
from babylon.engine.services import ServiceContainer
from babylon.engine.systems.ideology import ConsciousnessSystem
from babylon.models.enums import EdgeType
from babylon.topology.graph import BabylonGraph

_WORKER_ID = "worker_working_day_1"
_EMPLOYER_ID = "employer_working_day_1"

_ABSOLUTE_STATE = WorkingDayState(
    fips_code="26163",
    naics_sector="48",
    year=2019,
    avg_weekly_hours=50.0,
    labor_intensity_index=0.9,
)
_RELATIVE_STATE = WorkingDayState(
    fips_code="26163",
    naics_sector="51",
    year=2019,
    avg_weekly_hours=37.0,
    labor_intensity_index=2.0,
)


class _FixedProductivitySource:
    """Test double returning a fixed ``WorkingDayState`` regardless of args."""

    def __init__(self, state: WorkingDayState | None) -> None:
        self._state = state

    def get_working_day_state(
        self, fips_code: str, naics_sector: str, year: int
    ) -> WorkingDayState | None:
        return self._state


def _fresh_ideology() -> dict[str, float]:
    return {"class_consciousness": 0.0, "national_identity": 0.5, "agitation": 0.0}


def _graph_with_wage_cut() -> BabylonGraph:
    """A worker whose wages just fell (wage_change < 0) and whose wealth is
    flat (wealth_change == 0) -- isolates ``exploitation_rate`` as the sole
    nonzero visibility input, so the imperial-rent-only baseline visibility
    sits near 1.0 and any working-day dampening is cleanly observable."""
    graph = BabylonGraph()
    graph.add_node(_WORKER_ID, wealth=100.0, ideology=_fresh_ideology(), _node_type="social_class")
    graph.add_node(
        _EMPLOYER_ID, wealth=100.0, ideology=_fresh_ideology(), _node_type="social_class"
    )
    graph.add_edge(
        _EMPLOYER_ID,
        _WORKER_ID,
        edge_type=EdgeType.WAGES,
        value_flow=50.0,
    )
    return graph


def _context_with_prior_wage(prior_wage: float) -> TickContext:
    return TickContext(
        tick=1,
        persistent_data={
            "previous_wages": {_WORKER_ID: prior_wage},
            "previous_wealth": {_WORKER_ID: 100.0},
        },
    )


@pytest.mark.unit
class TestWorkingDayVisibilityWiring:
    """The headline property: the working-day regime must multiplicatively
    shape ``material_conditions.exploitation_visibility``."""

    def test_unwired_productivity_source_leaves_visibility_unchanged(self) -> None:
        """Default ``ServiceContainer.create()`` (no ``productivity_data_source``)
        must reproduce the EXACT pre-U4 visibility -- backward compatible."""
        graph = _graph_with_wage_cut()
        services = ServiceContainer.create()
        system = ConsciousnessSystem()

        system.step(graph, services, _context_with_prior_wage(100.0))

        mc = graph.nodes[_WORKER_ID]["material_conditions"]
        # exploitation_rate=50.0, imperial_rent=0.0 -> raw_visibility ~= 1.0
        assert mc["exploitation_visibility"] == pytest.approx(1.0, abs=1e-6)

    def test_relative_dominant_working_day_dampens_visibility(self) -> None:
        """RELATIVE_DOMINANT (productivity-gain exploitation) must dampen
        visibility well below the unwired baseline -- naturalized, largely
        invisible exploitation (Ch. 10/12)."""
        graph = _graph_with_wage_cut()
        source = _FixedProductivitySource(state=_RELATIVE_STATE)
        services = ServiceContainer.create(productivity_data_source=source)
        system = ConsciousnessSystem()

        system.step(graph, services, _context_with_prior_wage(100.0))

        mc = graph.nodes[_WORKER_ID]["material_conditions"]
        expected = 1.0 * WorkingDayDefines().relative_visibility
        assert mc["exploitation_visibility"] == pytest.approx(expected, abs=1e-3)

    def test_absolute_dominant_working_day_leaves_visibility_at_baseline(self) -> None:
        """ABSOLUTE_DOMINANT (long-hours exploitation) is directly
        experienced -- the default 1.0 modifier leaves visibility
        unchanged from the imperial-rent-only baseline."""
        graph = _graph_with_wage_cut()
        source = _FixedProductivitySource(state=_ABSOLUTE_STATE)
        services = ServiceContainer.create(productivity_data_source=source)
        system = ConsciousnessSystem()

        system.step(graph, services, _context_with_prior_wage(100.0))

        mc = graph.nodes[_WORKER_ID]["material_conditions"]
        assert mc["exploitation_visibility"] == pytest.approx(1.0, abs=1e-3)

    def test_relative_dominant_less_visible_than_absolute_dominant(self) -> None:
        """Direct comparison: the SAME wage-cut fixture, differing only by
        working-day regime, must show ABSOLUTE > RELATIVE visibility."""
        services_relative = ServiceContainer.create(
            productivity_data_source=_FixedProductivitySource(state=_RELATIVE_STATE)
        )
        services_absolute = ServiceContainer.create(
            productivity_data_source=_FixedProductivitySource(state=_ABSOLUTE_STATE)
        )

        graph_relative = _graph_with_wage_cut()
        ConsciousnessSystem().step(
            graph_relative, services_relative, _context_with_prior_wage(100.0)
        )
        relative_visibility = graph_relative.nodes[_WORKER_ID]["material_conditions"][
            "exploitation_visibility"
        ]

        graph_absolute = _graph_with_wage_cut()
        ConsciousnessSystem().step(
            graph_absolute, services_absolute, _context_with_prior_wage(100.0)
        )
        absolute_visibility = graph_absolute.nodes[_WORKER_ID]["material_conditions"][
            "exploitation_visibility"
        ]

        assert relative_visibility < absolute_visibility

    def test_source_returning_no_data_leaves_visibility_unchanged(self) -> None:
        """The data source may have no data for this tick's derived year --
        an honest ``None``, same multiplicative identity as unwired."""
        graph = _graph_with_wage_cut()
        source = _FixedProductivitySource(state=None)
        services = ServiceContainer.create(productivity_data_source=source)
        system = ConsciousnessSystem()

        system.step(graph, services, _context_with_prior_wage(100.0))

        mc = graph.nodes[_WORKER_ID]["material_conditions"]
        assert mc["exploitation_visibility"] == pytest.approx(1.0, abs=1e-6)

    def test_custom_working_day_defines_are_respected(self) -> None:
        """A run-scoped ``GameDefines.working_day`` override must be
        threaded through (task #42-A-style regression guard: without an
        explicit defines pass-through the resolver would silently fall
        back to schema defaults)."""
        custom_defines = GameDefines(working_day=WorkingDayDefines(relative_visibility=0.05))
        graph = _graph_with_wage_cut()
        source = _FixedProductivitySource(state=_RELATIVE_STATE)
        services = ServiceContainer.create(defines=custom_defines, productivity_data_source=source)
        system = ConsciousnessSystem()

        system.step(graph, services, _context_with_prior_wage(100.0))

        mc = graph.nodes[_WORKER_ID]["material_conditions"]
        assert mc["exploitation_visibility"] == pytest.approx(0.05, abs=1e-3)

    def test_deterministic(self) -> None:
        """Identical inputs must produce an identical result every time
        (Constitution III.7)."""
        services_a = ServiceContainer.create(
            productivity_data_source=_FixedProductivitySource(state=_RELATIVE_STATE)
        )
        services_b = ServiceContainer.create(
            productivity_data_source=_FixedProductivitySource(state=_RELATIVE_STATE)
        )

        graph_a = _graph_with_wage_cut()
        ConsciousnessSystem().step(graph_a, services_a, _context_with_prior_wage(100.0))

        graph_b = _graph_with_wage_cut()
        ConsciousnessSystem().step(graph_b, services_b, _context_with_prior_wage(100.0))

        assert (
            graph_a.nodes[_WORKER_ID]["material_conditions"]["exploitation_visibility"]
            == graph_b.nodes[_WORKER_ID]["material_conditions"]["exploitation_visibility"]
        )

    def test_compute_exploitation_visibility_called_with_working_day_modifier(self) -> None:
        """Direct call-contract pin: ``ideology.py`` must call
        ``compute_exploitation_visibility`` with ``working_day_modifier=``
        the resolved value, not silently drop it."""
        from unittest.mock import patch

        from babylon.formulas.consciousness_routing import (
            compute_exploitation_visibility as _real_compute_exploitation_visibility,
        )

        graph = _graph_with_wage_cut()
        source = _FixedProductivitySource(state=_RELATIVE_STATE)
        services = ServiceContainer.create(productivity_data_source=source)
        system = ConsciousnessSystem()

        with patch(
            "babylon.engine.systems.ideology.compute_exploitation_visibility",
            wraps=_real_compute_exploitation_visibility,
        ) as spy:
            system.step(graph, services, _context_with_prior_wage(100.0))

        calls_with_modifier = [
            call
            for call in spy.call_args_list
            if call.kwargs.get("working_day_modifier")
            == pytest.approx(WorkingDayDefines().relative_visibility)
        ]
        assert calls_with_modifier, (
            "compute_exploitation_visibility must be called with "
            "working_day_modifier=<resolved classifier output>; actual "
            f"calls: {spy.call_args_list}"
        )
