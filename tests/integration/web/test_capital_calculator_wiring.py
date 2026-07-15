"""Program 17 item-25 Fix B: the web bridge wires a REAL per-county capital_calculator.

Owner-ruled (2026-07-12): source per-county capital stock K from the real
``CapitalStockCalculator(tensor_registry)`` tensor/BEA pipeline rather than a
coefficient or a flat default. With K=0 the derived rates degenerate —
``profit_rate = s/(0+v) == s/v = exploitation_rate`` and ``occ = 0/v = 0`` — two
identical lenses. A real K breaks that tie (``profit_rate < exploitation_rate``,
``occ > 0``).

This gate pins that ``_build_capital_calculator`` hydrates a TensorRegistry from
the reference DB and yields a calculator whose ``get_K`` returns a positive real
capital stock for a covered county-year. It is ``requires_reference_db`` (needs
the reference SQLite / its CI subset); it skips — loudly — if that subset lacks
Wayne QCEW (the same reference-DB reproducibility gap tracked for Φ), rather than
red on a thin CI artifact.
"""

from __future__ import annotations

import os

import pytest

from babylon.domain.economics.tensor import NoDataSentinel

pytestmark = [pytest.mark.integration, pytest.mark.requires_reference_db]

WAYNE_FIPS = "26163"


@pytest.fixture
def _django_setup() -> None:
    import django
    from django.conf import settings

    if not settings.configured:
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "babylon_web.settings.development")
        django.setup()


def test_build_capital_calculator_returns_real_K_for_wayne(_django_setup: None) -> None:
    """A hydrated capital_calculator returns a positive real K for Wayne 2010."""
    from game.engine_bridge import _build_capital_calculator

    calc = _build_capital_calculator((WAYNE_FIPS,))
    k = calc.get_K(WAYNE_FIPS, 2010)

    if isinstance(k, NoDataSentinel):
        pytest.skip(f"reference DB subset lacks Wayne QCEW capital data: {k.reason}")

    assert isinstance(k, float)
    assert k > 0.0, "capital stock K must be a positive labor-hours figure"


def test_bridge_overrides_include_capital_calculator_when_fips_given(_django_setup: None) -> None:
    """_bridge_economics_overrides wires capital_calculator only when it knows the FIPS."""
    from game.engine_bridge import _bridge_economics_overrides

    overrides, session = _bridge_economics_overrides((WAYNE_FIPS,))
    try:
        assert "capital_calculator" in overrides
        assert overrides["capital_calculator"] is not None
        # Fix C: employment_source is wired unconditionally (queried per fips-year,
        # no upfront hydration).
        assert overrides.get("employment_source") is not None
    finally:
        if session is not None:
            session.close()

    # With no FIPS there is nothing to hydrate, so the capital_calculator is absent
    # (the Leontief/MELT/gamma wiring is unaffected) — but employment_source, being
    # hydration-free, is still wired.
    overrides_bare, session_bare = _bridge_economics_overrides(())
    try:
        assert "capital_calculator" not in overrides_bare
        assert overrides_bare.get("employment_source") is not None
    finally:
        if session_bare is not None:
            session_bare.close()
