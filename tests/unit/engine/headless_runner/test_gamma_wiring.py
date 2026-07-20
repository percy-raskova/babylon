"""Unit tests for gamma calculator wiring in the headless runner.

Spec: E101 — wire gamma calculator into headless runner so
TickDynamicsSystem actually computes gamma instead of no-opping.

The headless runner's ServiceContainer.create() call previously passed
only ``defines=``, leaving ``gamma_calculator`` (and ``melt_calculator``)
at their default ``None``. TickDynamicsSystem guards on
``melt_calculator is not None`` (early-return at tick/system/__init__.py:136)
and then reads ``gamma_calculator.compute(year)`` at line 387. With both
``None`` the entire system no-ops — gamma stays at the hardcoded 0.33 default.

These tests cover two levels:
  1. The ``_build_economics_overrides`` helper (constructs calculators).
  2. The actual call site in ``run()`` — verifies the overrides are
     unpacked into ``ServiceContainer.create(**overrides)``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

SQLITE_REF = Path("data/sqlite/marxist-data-3NF.sqlite")


def test_build_economics_overrides_wires_gamma_calculator() -> None:
    """Gamma calculator is wired (parameterless MVP sources)."""
    from babylon.engine.headless_runner.runner import _build_economics_overrides

    overrides, leontief_session = _build_economics_overrides()
    assert "gamma_calculator" in overrides, "gamma_calculator key missing from overrides"
    assert overrides["gamma_calculator"] is not None, "gamma_calculator is None"
    assert leontief_session is None, "no session_factory provided; leontief_session must be None"


def test_build_economics_overrides_wires_melt_calculator_with_session() -> None:
    """Melt calculator (gate for TickDynamicsSystem) is wired when session_factory provided."""
    pytest.importorskip("sqlalchemy")
    if not SQLITE_REF.exists():
        pytest.skip(f"SQLite reference DB missing at {SQLITE_REF}")

    from babylon.engine.headless_runner.runner import _build_economics_overrides
    from babylon.reference.database import get_normalized_session_factory

    session_factory = get_normalized_session_factory()
    overrides, leontief_session = _build_economics_overrides(session_factory=session_factory)
    assert overrides.get("melt_calculator") is not None, "melt_calculator is None"
    assert overrides.get("gamma_calculator") is not None, "gamma_calculator is None"
    # event_bus/defines were not provided, so the Leontief pipeline stays unwired.
    assert overrides.get("production_chain_calculator") is None
    assert leontief_session is None


@pytest.mark.requires_reference_db
def test_build_economics_overrides_wires_leontief_pipeline_with_event_bus_and_defines() -> None:
    """Program 17 / Item 1a: Leontief overrides + session are wired when
    event_bus and defines are also provided alongside session_factory.

    ``requires_reference_db``: constructing the Leontief pipeline loads the BEA
    industry dimension (``dim_bea_industry``), a table the file-exists guard
    below cannot detect (the DB-free dev CI tier ships a stub SQLite that has
    the file but not the table). Deselected on ``test:unit-ci``; runs locally
    and in main/nightly against the ci-data-v1 subset.
    """
    pytest.importorskip("sqlalchemy")
    if not SQLITE_REF.exists():
        pytest.skip(f"SQLite reference DB missing at {SQLITE_REF}")

    from babylon.config.defines import GameDefines
    from babylon.engine.headless_runner.runner import _build_economics_overrides
    from babylon.kernel.event_bus import EventBus
    from babylon.reference.database import get_normalized_session_factory

    session_factory = get_normalized_session_factory()
    event_bus = EventBus()
    defines = GameDefines.load_default()

    overrides, leontief_session = _build_economics_overrides(
        session_factory=session_factory,
        event_bus=event_bus,
        defines=defines,
    )
    try:
        assert overrides.get("melt_calculator") is not None
        assert overrides.get("periphery_labor_source") is not None
        assert overrides.get("final_demand_source") is not None
        assert overrides.get("industry_county_allocator") is not None
        assert overrides.get("production_chain_calculator") is not None
        assert overrides.get("bea_industries")
        assert leontief_session is not None
    finally:
        if leontief_session is not None:
            leontief_session.close()


@pytest.mark.requires_reference_db
def test_run_passes_gamma_calculator_to_service_container(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """RED->GREEN: run() must pass gamma_calculator AND tensor_registry to
    ServiceContainer.create.

    Before E101 wiring: ``ServiceContainer.create(defines=defines)`` is
    called with no ``gamma_calculator`` kwarg -> assertion fails (RED).
    After wiring: ``_build_economics_overrides()`` is called and its
    return dict is unpacked into ``ServiceContainer.create(**overrides)``,
    so ``gamma_calculator`` is present and non-None (GREEN).

    U1 (vol3-money-scissors) additionally threads ``scope_fips=config.scope_fips``
    into that same call, so ``tensor_registry`` (and the Vol III financial
    calculators) must ALSO be present in the captured kwargs.

    The Postgres / hydration / bridge layer is stubbed so we reach the
    ``ServiceContainer.create`` call site without a live database. A
    sentinel exception stops execution immediately after the call so
    the captured kwargs can be inspected.
    """
    from babylon.engine.headless_runner import runner as runner_mod
    from babylon.engine.headless_runner.models import SimulationRunConfig

    if not SQLITE_REF.exists():
        pytest.skip(f"SQLite reference DB missing at {SQLITE_REF}")

    captured: dict[str, Any] = {}

    class _StopAfterCreate(Exception):
        """Sentinel: stop run() immediately after ServiceContainer.create."""

    # --- Stub Postgres / hydration layer to reach ServiceContainer.create ---

    monkeypatch.setattr(runner_mod, "_install_sigint_handler", lambda: None)
    monkeypatch.setattr(runner_mod, "_open_postgres_pool", lambda: None)
    monkeypatch.setattr(runner_mod, "_apply_migrations", lambda _pool: None)

    # PostgresRuntime is imported lazily inside run()
    import babylon.persistence

    monkeypatch.setattr(babylon.persistence, "PostgresRuntime", lambda **_kwargs: None)

    # initialize_session is imported lazily inside run()
    import babylon.persistence.postgres_initialization as pg_init

    class _FakeReport:
        hex_count = 100
        national_phi_reference = 0.0

    monkeypatch.setattr(pg_init, "initialize_session", lambda **_kw: _FakeReport())

    # ConservationAuditor is imported lazily inside run()
    import babylon.persistence.conservation_audit as ca

    class _FakeAuditor:
        audit_log_buffer: list[Any] = []

        def register_invariant(self, name: str, evaluator: Any) -> None:
            pass

    monkeypatch.setattr(ca, "ConservationAuditor", lambda **_kw: _FakeAuditor())

    # WorldStateBridge + friends are top-level imports in runner
    class _FakeWorld:
        def to_graph(self) -> Any:
            return None

    class _FakeBridge:
        # Gate A (runner.py) compares this against report.hex_count (100 here).
        hex_template_size = 100

        def hydrate_initial(self, **kw: Any) -> Any:
            return _FakeWorld()

    monkeypatch.setattr(runner_mod, "WorldStateBridge", lambda **_kw: _FakeBridge())
    monkeypatch.setattr(runner_mod, "BoundaryFlowRegister", lambda: object())
    monkeypatch.setattr(runner_mod, "EventBus", lambda: object())
    monkeypatch.setattr(runner_mod, "EventCapture", lambda: object())

    # ServiceContainer.create — capture kwargs, raise sentinel
    class _FakeServiceContainer:
        @staticmethod
        def create(*_args: Any, **kwargs: Any) -> Any:
            captured.update(kwargs)
            raise _StopAfterCreate

    monkeypatch.setattr(runner_mod, "ServiceContainer", _FakeServiceContainer)

    config = SimulationRunConfig(
        ticks=1,
        scope_fips=frozenset({"26163", "26125", "26099"}),
        sqlite_reference_path=SQLITE_REF,
        output_dir=tmp_path / "out",
    )

    with pytest.raises(_StopAfterCreate):
        runner_mod.run(config)

    assert captured.get("gamma_calculator") is not None, (
        "run() did not pass gamma_calculator to ServiceContainer.create; "
        f"captured kwargs: {sorted(captured.keys())}"
    )
    assert captured.get("melt_calculator") is not None, (
        "run() did not pass melt_calculator to ServiceContainer.create; "
        f"captured kwargs: {sorted(captured.keys())}"
    )
    assert captured.get("tensor_registry") is not None, (
        "run() did not pass tensor_registry to ServiceContainer.create; "
        f"captured kwargs: {sorted(captured.keys())}"
    )
    assert captured.get("distribution_calculator") is not None, (
        "run() did not pass distribution_calculator to ServiceContainer.create; "
        f"captured kwargs: {sorted(captured.keys())}"
    )


@pytest.mark.requires_reference_db
def test_build_economics_overrides_wires_tensor_registry_and_financial_services() -> None:
    """U1 (vol3-money-scissors): tensor_registry + Vol III financial
    calculators are wired when scope_fips is provided alongside
    session_factory.

    Without this, `_get_county_surplus`/`_get_county_profit_rate`
    (domain/economics/tick/system/__init__.py:1547,1599) read
    `getattr(services, "tensor_registry", None)` as permanently None, so
    `total_surplus` never exceeds 0 and `surplus_distribution` never
    computes — even though `distribution_calculator` et al. are wired.
    """
    pytest.importorskip("sqlalchemy")
    if not SQLITE_REF.exists():
        pytest.skip(f"SQLite reference DB missing at {SQLITE_REF}")

    from babylon.domain.economics.factory import load_fred_series_from_db
    from babylon.engine.headless_runner.runner import _build_economics_overrides
    from babylon.reference.database import get_normalized_session_factory

    session_factory = get_normalized_session_factory()
    overrides, leontief_session = _build_economics_overrides(
        session_factory=session_factory,
        scope_fips=frozenset({"26163"}),
    )
    try:
        assert overrides.get("tensor_registry") is not None
        registry = overrides["tensor_registry"]
        assert "26163" in registry.all_fips()
        # `all_fips()` only proves hydrate_counties() was CALLED for this
        # FIPS — TensorRegistry.hydrate_counties() catches per-county-year
        # failures and writes a (falsy) NoDataSentinel into the same cache
        # dict all_fips() iterates, so key presence survives even total
        # hydration failure. Prove real tensor content landed instead.
        hydrated_years = registry.available_years("26163")
        assert len(hydrated_years) == 15, (
            "expected all 15 hydration years (2010-2024) to have been "
            f"attempted for 26163, got {sorted(hydrated_years)}"
        )
        tensor_2020 = registry.get("26163", 2020)
        assert tensor_2020, (
            "26163/2020 hydrated to a falsy NoDataSentinel "
            f"(reason={getattr(tensor_2020, 'reason', None)!r}) — registry "
            "key presence does not imply real tensor data"
        )

        # Same class of gap on the financial-calculator side:
        # create_financial_services() always returns non-None calculator
        # objects even when fred_series_cache is empty (e.g. the reference
        # DB is missing fact_fred_national/dim_fred_series) — the
        # calculators just resolve to NoDataSentinel forever. Prove the
        # FRED cache actually has data and that it reaches a calculator.
        fred_cache = load_fred_series_from_db(session_factory)
        assert {"FEDFUNDS", "GFDEBTN"} <= set(fred_cache), (
            f"expected FEDFUNDS and GFDEBTN in the FRED cache, got {sorted(fred_cache)}"
        )
        assert fred_cache["FEDFUNDS"].get(2020) is not None, (
            "FEDFUNDS/2020 missing from the FRED cache — financial "
            "calculators would be wired to an empty series"
        )

        assert overrides.get("distribution_calculator") is not None
        assert overrides.get("interest_calculator") is not None
        assert overrides.get("fictitious_capital_calculator") is not None

        interest_state_2020 = overrides["interest_calculator"].compute_interest_rate_state(2020)
        assert interest_state_2020, (
            "interest_calculator.compute_interest_rate_state(2020) returned a "
            f"falsy NoDataSentinel (reason={getattr(interest_state_2020, 'reason', None)!r}) "
            "— a non-None calculator object does not imply real FRED data reached it"
        )
        assert interest_state_2020.base_rate is not None
    finally:
        if leontief_session is not None:
            leontief_session.close()


@pytest.mark.requires_reference_db
def test_build_economics_overrides_threads_defines_into_housing_calculator() -> None:
    """Honesty sweep (U2.4): ``_build_economics_overrides``'s
    ``create_financial_services(fred_series_cache=fred_cache)`` call
    (runner.py, inside the ``scope_fips`` branch) previously dropped the
    ``defines`` parameter already passed into this very function, so
    ``housing_calculator``'s interest rate silently reverted to a second,
    independent ``GameDefines.load_default()`` call inside the factory
    while every other ``capital_vol3`` coefficient honored the caller's
    ``--defines`` overlay.
    """
    pytest.importorskip("sqlalchemy")
    if not SQLITE_REF.exists():
        pytest.skip(f"SQLite reference DB missing at {SQLITE_REF}")

    from babylon.config.defines import CapitalVolumeIIIDefines, GameDefines
    from babylon.engine.headless_runner.runner import _build_economics_overrides
    from babylon.reference.database import get_normalized_session_factory

    session_factory = get_normalized_session_factory()
    custom_defines = GameDefines(
        capital_vol3=CapitalVolumeIIIDefines(housing_capitalization_rate_default=0.12)
    )

    overrides, leontief_session = _build_economics_overrides(
        session_factory=session_factory,
        defines=custom_defines,
        scope_fips=frozenset({"26163"}),
    )
    try:
        housing_calc = overrides.get("housing_calculator")
        assert housing_calc is not None
        assert housing_calc._interest_rate == 0.12
    finally:
        if leontief_session is not None:
            leontief_session.close()
