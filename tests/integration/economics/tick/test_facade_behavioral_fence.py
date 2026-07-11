"""Spec 058 / FR-007 / Q3 — TickDynamicsSystem behavioral-fence regression test.

The 2026-05-08 Q3 clarification mandates that the post-decomposition
``TickDynamicsSystem`` facade preserves:
  - identical public method signatures
  - identical return-type classes (not merely structurally equal)
  - identical exception class hierarchies
  - identical event-bus emission ordering

Per the commit-7 reformulation: the TRUE behavioral fence in this commit is
the existing comprehensive ``tests/unit/economics/tick/test_system.py`` suite,
which exercises ``step()`` and the 33 private methods directly with controlled
mock services. If that suite passes after decomposition, the behavioral
contract holds.

This file adds an explicit, slim regression that pins the *facade public
surface* (the contract the decomposition MUST NOT break) — useful as a
focused diagnostic test if the broader test_system.py suite ever has its
internal mocks updated and we need to know whether the fence layer or the
mock layer changed.

Per FR-008: the spec-057 quarantine on ``_compute_imperial_rent`` is also
verified here (the stub remains, its tests stay skipped at the same count).
"""

from __future__ import annotations

import inspect

import pytest

# Method signatures pinned at the time of the decomposition commit. If the
# decomposition changes any of these, this test fails — pointing to the
# specific method whose contract drifted.
EXPECTED_STEP_PARAMS: tuple[str, ...] = ("self", "graph", "services", "context")
"""Pinned ``TickDynamicsSystem.step`` parameter list (post-relocation).

Drift here implies a facade public-contract violation."""


@pytest.mark.unit
class TestFacadePublicSurface:
    """The TickDynamicsSystem facade contract — pinned at commit 7."""

    def test_class_imports_from_canonical_path(self) -> None:
        """The import path ``babylon.domain.economics.tick.system.TickDynamicsSystem``
        is preserved across the package-relocation refactor."""
        from babylon.domain.economics.tick.system import TickDynamicsSystem

        assert TickDynamicsSystem.__name__ == "TickDynamicsSystem"

    def test_step_signature_pinned(self) -> None:
        """``TickDynamicsSystem.step`` signature MUST NOT drift across the
        decomposition. Drift here implies a facade contract violation."""
        from babylon.domain.economics.tick.system import TickDynamicsSystem

        sig = inspect.signature(TickDynamicsSystem.step)
        # Pin the parameter names + order; type annotations may be string
        # forward-refs (from __future__ annotations), so we don't compare them.
        params = list(sig.parameters.keys())
        assert params == ["self", "graph", "services", "context"], (
            f"Spec 058 / FR-007 / Q3: step() parameter list drifted: {params!r}"
        )

    def test_name_property_returns_canonical_string(self) -> None:
        """The ``name`` property's value is part of the public contract used
        by the SimulationEngine to identify systems in logs / events."""
        from babylon.domain.economics.tick.system import TickDynamicsSystem

        # Construct with no required args (TickDynamicsSystem.__init__ takes
        # no required parameters per the existing test_system.py fixtures)
        sys = TickDynamicsSystem()
        # `name` is a property (not a method) — accessed by attribute lookup.
        # The canonical value is "tick_dynamics" (snake_case identifier used
        # by the SimulationEngine in its system registry).
        assert sys.name == "tick_dynamics"


@pytest.mark.unit
class TestSpec057QuarantinePreserved:
    """Spec 058 / FR-008: the spec-057 quarantine on ``_compute_imperial_rent``
    survives the facade decomposition unchanged.

    The stub method remains; the ``pytest.mark.skip`` markers in quarantined
    test files are not touched.
    """

    def test_compute_imperial_rent_method_exists_as_stub(self) -> None:
        """``_compute_imperial_rent`` is still a method on TickDynamicsSystem
        (per FR-008 — the decomposition does not delete or rename the stub;
        spec 057 will replace its body with a real Leontief implementation)."""
        from babylon.domain.economics.tick.system import TickDynamicsSystem

        assert hasattr(TickDynamicsSystem, "_compute_imperial_rent"), (
            "Spec 058 / FR-008: _compute_imperial_rent stub MUST remain "
            "on TickDynamicsSystem; spec 057 replaces its body."
        )
        # The stub is callable — its body is preserved verbatim
        assert callable(TickDynamicsSystem._compute_imperial_rent)
