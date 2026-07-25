"""Unit tests for the headless-runner Vol I / Vol II parity fix (U5).

Program: ai/_inbox/vol1-value-production-program-prompt.md §2c/§10.3, U5.
SHARED unit with Vol II (ai/_inbox/vol2-circulation-engine-program-prompt.md
§2d/U5) — assigned to the Vol I lane by ADR103's §10.2 deviation note
("runner-parity stays assigned to Vol I").

Before this unit, ``_build_economics_overrides`` wired gamma/melt/Leontief/
financial services (and, for Vol III, ``tensor_registry``) but never called
``create_vol1_services`` or ``create_circulation_services`` — the canonical
headless run computed LESS Vol I/Vol II economics than a web session, which
already wires both (``web/game/engine_bridge.py:8002-8051``). This test file
proves both families are now wired identically to the web bridge:

- ``reserve_army_data_source`` / ``productivity_data_source`` /
  ``dispossession_data_source`` / ``transition_engine`` (Vol I)
- ``turnover_profile_source`` / ``inventory_data_source`` /
  ``depreciation_data_source`` (Vol II)
"""

from __future__ import annotations

from pathlib import Path

import pytest

SQLITE_REF = Path("data/sqlite/marxist-data-3NF.sqlite")


@pytest.mark.requires_reference_db
def test_build_economics_overrides_wires_vol1_services_with_scope_fips() -> None:
    """Vol I production services are wired when scope_fips is provided.

    Mirrors ``web/game/engine_bridge.py``'s ``create_vol1_services`` call
    (Spec-116 Task 21b) inside ``_build_economics_overrides``'s existing
    ``scope_fips`` branch — no new gating condition, same condition that
    already wires ``tensor_registry``/Vol III financial services.
    """
    pytest.importorskip("sqlalchemy")
    if not SQLITE_REF.exists():
        pytest.skip(f"SQLite reference DB missing at {SQLITE_REF}")

    from babylon.engine.headless_runner.runner import _build_economics_overrides
    from babylon.reference.database import get_normalized_session_factory

    session_factory = get_normalized_session_factory()
    overrides, leontief_session = _build_economics_overrides(
        session_factory=session_factory,
        scope_fips=frozenset({"26163"}),
    )
    try:
        assert overrides.get("reserve_army_data_source") is not None, (
            "reserve_army_data_source missing — create_vol1_services not wired"
        )
        assert overrides.get("productivity_data_source") is not None
        assert overrides.get("dispossession_data_source") is not None
        assert overrides.get("transition_engine") is not None, (
            "transition_engine missing — the _simulate_transitions "
            "'services.transition_engine is None' gate stays unsatisfied"
        )

        decomposition = overrides["reserve_army_data_source"].get_unemployment_decomposition(
            "26163", 2020
        )
        assert decomposition is not None, (
            "reserve_army_data_source produced no decomposition for 2020 — "
            "FRED UNRATE series is empty in this reference DB"
        )
    finally:
        if leontief_session is not None:
            leontief_session.close()


@pytest.mark.requires_reference_db
def test_build_economics_overrides_wires_circulation_services_with_scope_fips() -> None:
    """Vol II circulation services are wired when scope_fips is provided.

    Mirrors ``web/game/engine_bridge.py``'s ``create_circulation_services``
    call (Spec-116 Task 20b) inside the same ``scope_fips`` branch.
    """
    pytest.importorskip("sqlalchemy")
    if not SQLITE_REF.exists():
        pytest.skip(f"SQLite reference DB missing at {SQLITE_REF}")

    from babylon.engine.headless_runner.runner import _build_economics_overrides
    from babylon.reference.database import get_normalized_session_factory

    session_factory = get_normalized_session_factory()
    overrides, leontief_session = _build_economics_overrides(
        session_factory=session_factory,
        scope_fips=frozenset({"26163"}),
    )
    try:
        assert overrides.get("turnover_profile_source") is not None, (
            "turnover_profile_source missing — create_circulation_services not wired"
        )
        assert overrides.get("inventory_data_source") is not None
        assert overrides.get("depreciation_data_source") is not None
    finally:
        if leontief_session is not None:
            leontief_session.close()


@pytest.mark.requires_reference_db
def test_run_passes_vol1_and_circulation_services_to_service_container(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """RED->GREEN: run() must pass Vol I + Vol II services to ServiceContainer.

    Before U5: ``ServiceContainer.create(**overrides)`` never received
    ``reserve_army_data_source``/``transition_engine``/
    ``turnover_profile_source`` — the canonical run silently computed less
    economics than a web session (the parity gap this unit closes).

    Stubs the Postgres/hydration/bridge layer exactly like
    ``test_gamma_wiring.py::test_run_passes_gamma_calculator_to_service_container``
    to reach the ``ServiceContainer.create`` call site without a live database.
    """
    from babylon.engine.headless_runner import runner as runner_mod
    from babylon.engine.headless_runner.models import SimulationRunConfig

    if not SQLITE_REF.exists():
        pytest.skip(f"SQLite reference DB missing at {SQLITE_REF}")

    captured: dict[str, object] = {}

    class _StopAfterCreate(Exception):
        """Sentinel: stop run() immediately after ServiceContainer.create."""

    monkeypatch.setattr(runner_mod, "_install_sigint_handler", lambda: None)
    monkeypatch.setattr(runner_mod, "_open_postgres_pool", lambda: None)
    monkeypatch.setattr(runner_mod, "_apply_migrations", lambda _pool: None)

    import babylon.persistence

    monkeypatch.setattr(babylon.persistence, "PostgresRuntime", lambda **_kwargs: None)

    import babylon.persistence.postgres_initialization as pg_init

    class _FakeReport:
        hex_count = 100
        national_phi_reference = 0.0

    monkeypatch.setattr(pg_init, "initialize_session", lambda **_kw: _FakeReport())

    import babylon.persistence.conservation_audit as ca

    class _FakeAuditor:
        audit_log_buffer: list[object] = []

        def register_invariant(self, name: str, evaluator: object) -> None:
            pass

    monkeypatch.setattr(ca, "ConservationAuditor", lambda **_kw: _FakeAuditor())

    class _FakeWorld:
        def to_graph(self) -> object:
            return None

    class _FakeBridge:
        hex_template_size = 100

        def hydrate_initial(self, **kw: object) -> object:
            return _FakeWorld()

    monkeypatch.setattr(runner_mod, "WorldStateBridge", lambda **_kw: _FakeBridge())
    monkeypatch.setattr(runner_mod, "BoundaryFlowRegister", lambda: object())
    monkeypatch.setattr(runner_mod, "EventBus", lambda: object())
    monkeypatch.setattr(runner_mod, "EventCapture", lambda: object())

    class _FakeServiceContainer:
        @staticmethod
        def create(*_args: object, **kwargs: object) -> object:
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

    assert captured.get("reserve_army_data_source") is not None, (
        "run() did not pass reserve_army_data_source to ServiceContainer.create; "
        f"captured kwargs: {sorted(captured.keys())}"
    )
    assert captured.get("transition_engine") is not None, (
        "run() did not pass transition_engine to ServiceContainer.create; "
        f"captured kwargs: {sorted(captured.keys())}"
    )
    assert captured.get("turnover_profile_source") is not None, (
        "run() did not pass turnover_profile_source to ServiceContainer.create; "
        f"captured kwargs: {sorted(captured.keys())}"
    )
