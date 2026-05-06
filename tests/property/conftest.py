"""Hypothesis configuration and shared fixtures for property-based tests.

Spec 040: ``dev`` / ``ci`` / ``nightly`` profiles balance speed vs coverage
per environment.

Spec 053: ``default`` / ``slow`` profiles for conservation-invariant tests.
``default`` runs in the unit-test gate (~100 examples, derandomized for
deterministic CI replay, satisfies SC-001 baseline and FR-014). ``slow`` runs
out-of-band for exhaustive exploration (500 examples, non-derandomized so the
example database grows). Load via ``HYPOTHESIS_PROFILE=slow`` env var.

Spec 053 T014b: ``service_container_fixture`` and ``tick_context_fixture``
provide minimal harness for full-pipeline tests that invoke
``SimulationEngine.run_tick(graph, services, context)``.
"""

import os

import pytest
from hypothesis import HealthCheck, Verbosity, settings

from babylon.engine.context import TickContext
from babylon.engine.services import ServiceContainer

settings.register_profile(
    "dev",
    max_examples=20,
    deadline=1000,
    verbosity=Verbosity.normal,
)

settings.register_profile(
    "ci",
    max_examples=500,
    deadline=5000,
    suppress_health_check=[HealthCheck.too_slow],
)

settings.register_profile(
    "nightly",
    max_examples=5000,
    deadline=None,
)

settings.register_profile(
    "default",
    max_examples=100,
    derandomize=True,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)

settings.register_profile(
    "slow",
    max_examples=500,
    derandomize=False,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)

settings.load_profile(os.environ.get("HYPOTHESIS_PROFILE", "default"))


@pytest.fixture
def service_container_fixture() -> ServiceContainer:
    """Minimal ``ServiceContainer`` sufficient for a single ``run_tick`` call.

    Spec 053 T014b: Uses ``ServiceContainer.create()`` with all defaults
    (in-memory SQLite database, default GameDefines, default formula
    registry, fresh EventBus, in-memory metrics collector). Tests that need
    specific calculator services (Feature 011-024) should construct their
    own container; this fixture targets the conservation-invariant tests
    which only require the core six.
    """
    return ServiceContainer.create()


@pytest.fixture
def tick_context_fixture() -> TickContext:
    """Minimal ``TickContext(tick=0)`` for property tests.

    Spec 053 T014b: Single-tick tests pass this directly. Multi-tick tests
    construct a fresh context per tick or mutate ``context.tick``.
    """
    return TickContext(tick=0)
