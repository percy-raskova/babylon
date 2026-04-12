"""Hypothesis configuration for property-based tests.

Spec 040: Profiles balance speed vs coverage per environment.
"""

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
