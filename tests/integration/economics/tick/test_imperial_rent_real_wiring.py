"""Real-data integration test for Program 17 / Item 1a — wiring the full
per-county Imperial Rent Phi pipeline.

Unlike ``test_imperial_rent_pipeline.py`` (mock-everything, verifies the
orchestration logic in isolation), this test drives
:func:`babylon.domain.economics.factory.create_leontief_rent_services`
against the REAL reference SQLite (``data/sqlite/marxist-data-3NF.sqlite``)
and the real Detroit tri-county territory graph, proving the wire is
genuinely LIVE end-to-end: real BEA I-O coefficients, real Hickel ERDI
periphery wages, real BEA final demand, real QCEW county employment shares
all feed into ``TickDynamicsSystem``'s per-county ``tick_phi_hour``.

The load-bearing assertion is that phi_hour VARIES across the 3 counties
(Wayne/Oakland/Macomb) — this rules out the failure mode where the pipeline
runs without raising but silently degrades to an identical value for every
county (e.g. a broadcast/constant that looks "wired" but isn't actually
county-resolution).

KNOWN-RED (Program 17 / Item 1a, verified 2026-07-12, code-correct):
this test currently FAILS at assertion 2 — every county's phi_hour is
exactly 0.0 — for a data-availability reason, not a wiring bug. Root cause,
verified directly against ``data/sqlite/marxist-data-3NF.sqlite``:
``fact_bea_io_coefficient`` has 131,239 rows split only between
``table_type='USE'`` (57,876) and ``'TOTAL_REQ'`` (73,363) — ZERO rows with
``table_type='IMPORT_USE'``, for any year. ``DBImportShareSource`` therefore
always computes ``m_j = 0.0`` for every industry (correctly, given the
data), which zeroes the import-content matrix ``M = A_m @ L_d``, which
zeroes ``phi_vector``, which zeroes every county's allocated ``phi_hour`` —
deterministically, regardless of how correctly the rest of the pipeline is
wired. A loader for this exact data exists (``tools/ingest_bea_imports.py``,
writes ``table_type='IMPORT_USE'``) and its source archive IS present in
the trove (``/media/user/data/babylon-data/bea/MAKE-USE-IMPORTS (BEFORE
REDEFINITIONS).zip``) — it was simply never run against the canonical
reference DB. Running a data-ingestion tool against the shared 6GB
reference DB is out of scope for "wire the pipeline" (Item 1a) and needs
its own reviewed remediation step (mirrors the existing spec-086/097/098
reference-DB remediation program) — see
``tests/integration/economics/`` for the ~34 other data-availability
failures already tolerated in this codebase for the same reason. This test
is expected to start passing, with NO further code changes, the day
IMPORT_USE data is loaded.
"""

from __future__ import annotations

import pytest

from babylon.config.defines import GameDefines
from babylon.domain.economics.factory import create_leontief_rent_services
from babylon.domain.economics.gamma.adapters import MVPUnpaidCareHoursSource, QCEWCareAdapter
from babylon.domain.economics.gamma.gamma_iii import DefaultGammaIIICalculator
from babylon.domain.economics.melt import DefaultMELTCalculator
from babylon.domain.economics.melt.adapters import (
    SQLiteBEANationalGDPSource,
    SQLiteQCEWNationalEmploymentSource,
)
from babylon.domain.economics.tick.system import TickDynamicsSystem
from babylon.engine.context import TickContext
from babylon.engine.services import ServiceContainer
from babylon.kernel.event_bus import EventBus
from babylon.reference.database import get_normalized_session_factory
from tests.unit.economics.tick.conftest import build_territory_graph

pytestmark = [pytest.mark.integration, pytest.mark.requires_reference_db]

# Detroit tri-county (src/babylon/engine/headless_runner/scopes.py:123)
WAYNE_FIPS = "26163"
OAKLAND_FIPS = "26125"
MACOMB_FIPS = "26099"
_TRI_COUNTY_FIPS = [WAYNE_FIPS, OAKLAND_FIPS, MACOMB_FIPS]

# tick=260, base_year default 2010 -> year 2010 + 260 // 52 = 2015
_TICK = 260


@pytest.mark.integration
def test_tick_dynamics_computes_real_varying_phi_hour_across_counties() -> None:
    """TickDynamicsSystem, driven by the real Leontief-rent wire, must
    produce a non-zero, non-constant tick_phi_hour across Wayne/Oakland/
    Macomb — proving the pipeline is genuinely live, not a no-op or a
    uniform broadcast."""
    session_factory = get_normalized_session_factory()
    event_bus = EventBus()
    defines = GameDefines.load_default()

    overrides, leontief_session = create_leontief_rent_services(session_factory, event_bus, defines)
    try:
        services = ServiceContainer.create(
            defines=defines,
            melt_calculator=DefaultMELTCalculator(
                SQLiteBEANationalGDPSource(session_factory),
                SQLiteQCEWNationalEmploymentSource(session_factory),
            ),
            gamma_calculator=DefaultGammaIIICalculator(
                MVPUnpaidCareHoursSource(), QCEWCareAdapter()
            ),
            **overrides,
        )
        services.event_bus = event_bus

        graph = build_territory_graph(_TRI_COUNTY_FIPS)
        system = TickDynamicsSystem()
        system.step(graph, services, TickContext(tick=_TICK))

        phi_values = {fips: graph.nodes[fips].get("tick_phi_hour") for fips in _TRI_COUNTY_FIPS}

        # 1. All 3 counties received a value.
        assert all(v is not None for v in phi_values.values()), phi_values

        # 2. Not the permanent stub-zero.
        assert any(v != 0.0 for v in phi_values.values()), phi_values

        # 3. Crown assertion: genuinely varies across counties (rules out a
        # uniform-broadcast degenerate wiring).
        assert len(set(phi_values.values())) > 1, phi_values
    finally:
        leontief_session.close()
