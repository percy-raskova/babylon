"""Resolve Ch. 10/12/15 working-day readings from real data.

Feature: 021-capital-volume-i / vol1-value-production program U4 + U6.

Bridges ``services.productivity_data_source`` (the FRED OPHNFB + HOANBS
adapter wired by ``domain.economics.factory.create_vol1_services`` --
its FIRST production reader) to
:class:`~babylon.domain.economics.working_day.classifier
.DefaultWorkingDayClassifier`. Two consumers share the one raw fetch
(:func:`resolve_working_day_state`):

- :func:`resolve_working_day_visibility_modifier` (U4) feeds
  :func:`~babylon.formulas.consciousness_routing.compute_exploitation_visibility`
  inside ``ConsciousnessSystem`` (``engine/systems/ideology.py``);
- :func:`resolve_absolute_relative_surplus_ratio` (U6) feeds the
  ``absolute_relative_surplus`` opposition's
  ``GraphInputs.surplus_strategy_ratio`` (Chs. 10, 12, 15 -- the working
  day's length vs. labor's intensity as the two surplus-value strategies).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from babylon.domain.economics.working_day.classifier import DefaultWorkingDayClassifier

if TYPE_CHECKING:
    from babylon.domain.economics.working_day.data_sources import ProductivityDataSource
    from babylon.domain.economics.working_day.types import WorkingDayState
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


def resolve_working_day_state(
    graph: GraphProtocol,
    services: ServicesProtocol,
    tick: int,
) -> WorkingDayState | None:
    """Fetch this tick's raw Ch. 10 working-day state, if wired.

    The single fetch both :func:`resolve_working_day_visibility_modifier`
    (U4) and :func:`resolve_absolute_relative_surplus_ratio` (U6) build on --
    one FRED read per tick, not one per consumer. Computed ONCE per tick
    (not per ``social_class`` node): the wired FRED adapter is national-level
    and uniform regardless of the fips_code/naics_sector arguments passed to
    it, and no per-node county/sector identity exists on ``social_class``
    graph nodes to honestly vary the call by -- computing per-node would
    either repeat the identical lookup or fabricate geography that isn't
    there.

    Args:
        graph: The world graph, read for the ``base_year`` attribute
            (defaults to 2022 when absent).
        services: ServicesProtocol with optional ``productivity_data_source``
            and ``defines.timescale``.
        tick: Current simulation tick number.

    Returns:
        The ``WorkingDayState`` (hours + intensity) for this tick's derived
        year when ``productivity_data_source`` is wired and has data;
        ``None`` when the source is unwired or returns no data for that
        year -- an explicit "no data", never a fabricated default.
    """
    source: ProductivityDataSource | None = services.productivity_data_source
    if source is None:
        return None

    weeks_per_year = services.defines.timescale.weeks_per_year
    base_year = graph.get_graph_attr("base_year", _DEFAULT_BASE_YEAR)
    year = base_year + tick // weeks_per_year

    return source.get_working_day_state(
        _NATIONAL_FIPS_PLACEHOLDER, _NATIONAL_NAICS_PLACEHOLDER, year
    )


def resolve_working_day_visibility_modifier(
    graph: GraphProtocol,
    services: ServicesProtocol,
    tick: int,
) -> float | None:
    """Resolve this tick's Ch. 10 working-day consciousness visibility modifier.

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
    working_day_state = resolve_working_day_state(graph, services, tick)
    if working_day_state is None:
        return None

    classifier = DefaultWorkingDayClassifier(services.defines.working_day)
    return classifier.compute_visibility_modifier(working_day_state)


def resolve_absolute_relative_surplus_ratio(
    graph: GraphProtocol,
    services: ServicesProtocol,
    tick: int,
) -> float | None:
    """Resolve this tick's Ch. 10/12/15 absolute⇄relative surplus-value ratio.

    Feature: vol1-value-production program U6 -- the ``absolute_relative_surplus``
    opposition's ``GraphInputs.surplus_strategy_ratio``.

    Capital has two levers for extracting more surplus value from the same
    labor-power: lengthening the working day (absolute surplus value, Ch. 10)
    or cheapening labor-power's reproduction via rising productivity/
    intensity (relative surplus value, Chs. 12, 15). Both raw ingredients
    come from the SAME ``WorkingDayState`` :func:`resolve_working_day_state`
    already fetches for U4 -- no new data source, no new ingestion.

    Reuses ``WorkingDayDefines.relative_hours_threshold`` (already the
    classifier's own boundary between "short enough to be relative-dominant"
    and "long enough to start counting as absolute") as the hours reference,
    so no new coefficient is authored: ``labor_intensity_index`` already
    carries its own natural parity point (1.0 = baseline, by the field's own
    docstring), and ``relative_hours_threshold / avg_weekly_hours`` carries
    the SAME parity convention for hours (1.0 exactly at the threshold).
    Their product is one ratio with a natural zero point at 1.0 -- both
    axes simultaneously at parity -- fed to the shared ``_ratio_reading``
    family (``dialectics.instances.catalog``), the same "product of two
    reference-scaled components" shape ``credit_fragility`` (``default_rate
    * spread``) already uses.

    Args:
        graph: The world graph, read for the ``base_year`` attribute.
        services: ServicesProtocol with optional ``productivity_data_source``
            and ``defines.timescale``/``defines.working_day``.
        tick: Current simulation tick number.

    Returns:
        ``labor_intensity_index * relative_hours_threshold / avg_weekly_hours``,
        or ``None`` when the source is unwired, returns no data for this
        tick's year, or reports non-positive hours (a degenerate reading a
        ratio cannot honestly answer) -- absence, never a fabricated ratio
        (Constitution III.11).
    """
    working_day_state = resolve_working_day_state(graph, services, tick)
    if working_day_state is None:
        return None
    if working_day_state.avg_weekly_hours <= 0.0:
        return None

    relative_hours_threshold = float(services.defines.working_day.relative_hours_threshold)
    hours_ratio = relative_hours_threshold / working_day_state.avg_weekly_hours
    return float(working_day_state.labor_intensity_index * hours_ratio)
