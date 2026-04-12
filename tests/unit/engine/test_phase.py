"""RED phase: Tests for Phase-typed state (Spec 040 Discipline 4).

The Phase enum and typed aliases enforce system ordering at the type level.
Systems declare which phase they operate in, and the engine validates
that systems only run during their declared phase.
"""

from __future__ import annotations

from babylon.engine.phase import Phase, PhaseTransition, advance_phase


class TestPhaseEnum:
    """Verify Phase ordering and transitions."""

    def test_phase_ordering(self) -> None:
        """Phases are ordered: PRODUCTION < DISTRIBUTION < CONSCIOUSNESS < STRUGGLE."""
        assert Phase.PRODUCTION.value < Phase.DISTRIBUTION.value
        assert Phase.DISTRIBUTION.value < Phase.CONSCIOUSNESS.value
        assert Phase.CONSCIOUSNESS.value < Phase.STRUGGLE.value

    def test_all_phases_exist(self) -> None:
        """All required phases are defined."""
        assert hasattr(Phase, "PRODUCTION")
        assert hasattr(Phase, "DISTRIBUTION")
        assert hasattr(Phase, "CONSCIOUSNESS")
        assert hasattr(Phase, "STRUGGLE")

    def test_phase_count(self) -> None:
        """Exactly 4 phases defined."""
        assert len(Phase) == 4


class TestPhaseTransition:
    """Verify PhaseTransition tracks phase advancement."""

    def test_create_transition(self) -> None:
        """PhaseTransition records from and to phases."""
        transition = PhaseTransition(from_phase=Phase.PRODUCTION, to_phase=Phase.DISTRIBUTION)
        assert transition.from_phase == Phase.PRODUCTION
        assert transition.to_phase == Phase.DISTRIBUTION

    def test_transition_is_forward(self) -> None:
        """Forward transitions have to_phase > from_phase."""
        transition = PhaseTransition(from_phase=Phase.PRODUCTION, to_phase=Phase.DISTRIBUTION)
        assert transition.to_phase.value > transition.from_phase.value


class TestAdvancePhase:
    """Verify phase advancement function."""

    def test_advance_from_production(self) -> None:
        """PRODUCTION advances to DISTRIBUTION."""
        assert advance_phase(Phase.PRODUCTION) == Phase.DISTRIBUTION

    def test_advance_from_distribution(self) -> None:
        """DISTRIBUTION advances to CONSCIOUSNESS."""
        assert advance_phase(Phase.DISTRIBUTION) == Phase.CONSCIOUSNESS

    def test_advance_from_consciousness(self) -> None:
        """CONSCIOUSNESS advances to STRUGGLE."""
        assert advance_phase(Phase.CONSCIOUSNESS) == Phase.STRUGGLE

    def test_advance_from_struggle_wraps(self) -> None:
        """STRUGGLE wraps back to PRODUCTION for next tick."""
        assert advance_phase(Phase.STRUGGLE) == Phase.PRODUCTION
