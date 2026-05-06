"""Hypothesis configuration for property-based tests.

Spec 040: ``dev`` / ``ci`` / ``nightly`` profiles balance speed vs coverage
per environment.

Spec 053: ``default`` / ``slow`` profiles for conservation-invariant tests.
``default`` runs in the unit-test gate (~100 examples, derandomized for
deterministic CI replay, satisfies SC-001 baseline and FR-014). ``slow`` runs
out-of-band for exhaustive exploration (500 examples, non-derandomized so the
example database grows). Load via ``HYPOTHESIS_PROFILE=slow`` env var.
"""

import os

from hypothesis import HealthCheck, Verbosity, settings

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
