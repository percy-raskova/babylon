"""Resolve the Ch. 10 working-day visibility modifier from real data.

Feature: 021-capital-volume-i / vol1-value-production program U4.

Bridges ``services.productivity_data_source`` (the FRED OPHNFB + HOANBS
adapter wired by ``domain.economics.factory.create_vol1_services`` --
its FIRST production reader) to
:class:`~babylon.domain.economics.working_day.classifier
.DefaultWorkingDayClassifier`, producing the visibility modifier that
:func:`~babylon.formulas.consciousness_routing.compute_exploitation_visibility`
consumes inside ``ConsciousnessSystem`` (``engine/systems/ideology.py``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from babylon.domain.economics.working_day.classifier import DefaultWorkingDayClassifier

if TYPE_CHECKING:
    from babylon.kernel.graph_protocol import GraphProtocol
    from babylon.kernel.services import ServicesProtocol

#: Placeholder county/sector codes passed to ``productivity_data_source``.
#: The wired FRED adapter (``factory.py``'s ``_FredProductivityAdapter``) is
#: itself national-level and uniform regardless of these arguments (program
#: prompt §2c's documented honesty gap); no per-class county/sector identity
#: exists on ``social_class`` graph nodes to honestly vary the call by, so
#: this is not a fabricated identity -- it matches the adapter's OWN
#: fallback branch for "no specific geography given" (``fips_code if
#: len(fips_code) == 5 else "00000"``).
_NATIONAL_FIPS_PLACEHOLDER = "00000"
_NATIONAL_NAICS_PLACEHOLDER = "00"

#: Default base year when the graph carries no ``base_year`` attribute.
#: Matches ``engine/systems/production.py``'s ``hydrated_base_year`` default
#: exactly -- both read the same graph attribute within one tick, so a
#: shared default keeps the two readings consistent when the attribute is
#: genuinely absent (abstract, non-hydrated scenarios).
_DEFAULT_BASE_YEAR = 2022


def resolve_working_day_visibility_modifier(
    graph: GraphProtocol,
    services: ServicesProtocol,
    tick: int,
) -> float | None:
    """Resolve this tick's Ch. 10 working-day consciousness visibility modifier.

    Computed ONCE per tick (not per ``social_class`` node): the wired FRED
    adapter is national-level and uniform regardless of the
    fips_code/naics_sector arguments passed to it, and no per-node
    county/sector identity exists on ``social_class`` graph nodes to
    honestly vary the call by -- computing per-node would either repeat the
    identical lookup or fabricate geography that isn't there.

    Args:
        graph: The world graph, read for the ``base_year`` attribute
            (defaults to 2022 when absent).
        services: ServicesProtocol with optional ``productivity_data_source``
            and ``defines.timescale``/``defines.working_day``.
        tick: Current simulation tick number.

    Returns:
        Visibility modifier in [0, 1] when ``productivity_data_source`` is
        wired and returns data for this tick's derived year; ``None`` when
        the source is unwired or returns no data for that year -- an
        explicit "no data", never a fabricated default (the caller applies
        its own absent-safe, multiplicative-identity handling from there).
    """
    source = services.productivity_data_source
    if source is None:
        return None

    weeks_per_year = services.defines.timescale.weeks_per_year
    base_year = graph.get_graph_attr("base_year", _DEFAULT_BASE_YEAR)
    year = base_year + tick // weeks_per_year

    working_day_state = source.get_working_day_state(
        _NATIONAL_FIPS_PLACEHOLDER, _NATIONAL_NAICS_PLACEHOLDER, year
    )
    if working_day_state is None:
        return None

    classifier = DefaultWorkingDayClassifier(services.defines.working_day)
    return classifier.compute_visibility_modifier(working_day_state)
