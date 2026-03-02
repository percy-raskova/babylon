"""Tests for TernaryConsciousness model (Feature 034).

TDD red phase: tests written before implementation.
Covers model construction, simplex constraint, backward compatibility,
legacy migration, serialization roundtrip, and substrate floor.
"""

from __future__ import annotations

import math

import pytest
from pydantic import ValidationError

from babylon.models.enums import ConsciousnessTendency


@pytest.mark.unit
class TestTernaryConsciousnessConstruction:
    """Test native (r, l, f) construction path."""

    def test_create_with_defaults(self) -> None:
        """Default TernaryConsciousness has r=0.3, l=0.6, f=0.1."""
        from babylon.models.entities.consciousness import TernaryConsciousness

        tc = TernaryConsciousness()
        assert tc.r == pytest.approx(0.3, abs=1e-4)
        assert tc.l == pytest.approx(0.6, abs=1e-4)
        assert tc.f == pytest.approx(0.1, abs=1e-4)

    def test_create_with_custom_values(self) -> None:
        """Custom ternary coordinates accepted."""
        from babylon.models.entities.consciousness import TernaryConsciousness

        tc = TernaryConsciousness(r=0.5, l=0.3, f=0.2)
        assert tc.r == pytest.approx(0.5, abs=1e-4)
        assert tc.l == pytest.approx(0.3, abs=1e-4)
        assert tc.f == pytest.approx(0.2, abs=1e-4)

    def test_simplex_constraint_enforced(self) -> None:
        """r + l + f must equal 1.0 within tolerance."""
        from babylon.models.entities.consciousness import TernaryConsciousness

        with pytest.raises(ValidationError):
            TernaryConsciousness(r=0.5, l=0.5, f=0.5)

    def test_simplex_near_one_accepted(self) -> None:
        """Values summing to 1.0 within floating-point tolerance are accepted."""
        from babylon.models.entities.consciousness import TernaryConsciousness

        # Slightly off due to floating point — should be accepted
        tc = TernaryConsciousness(r=0.33333, l=0.33334, f=0.33333)
        assert tc.r + tc.l + tc.f == pytest.approx(1.0, abs=1e-4)

    def test_frozen_immutability(self) -> None:
        """TernaryConsciousness is frozen."""
        from babylon.models.entities.consciousness import TernaryConsciousness

        tc = TernaryConsciousness()
        with pytest.raises(ValidationError):
            tc.r = 0.9  # type: ignore[misc]

    def test_negative_component_rejected(self) -> None:
        """Negative components are invalid."""
        from babylon.models.entities.consciousness import TernaryConsciousness

        with pytest.raises(ValidationError):
            TernaryConsciousness(r=-0.1, l=0.6, f=0.5)

    def test_component_over_one_rejected(self) -> None:
        """Components over 1.0 are invalid."""
        from babylon.models.entities.consciousness import TernaryConsciousness

        with pytest.raises(ValidationError):
            TernaryConsciousness(r=1.5, l=0.0, f=0.0)

    def test_pure_revolutionary(self) -> None:
        """Pure revolutionary: r=1, l=0, f=0."""
        from babylon.models.entities.consciousness import TernaryConsciousness

        tc = TernaryConsciousness(r=1.0, l=0.0, f=0.0)
        assert tc.r == pytest.approx(1.0, abs=1e-4)
        assert tc.l == pytest.approx(0.0, abs=1e-4)
        assert tc.f == pytest.approx(0.0, abs=1e-4)

    def test_pure_liberal(self) -> None:
        """Pure liberal: r=0, l=1, f=0."""
        from babylon.models.entities.consciousness import TernaryConsciousness

        tc = TernaryConsciousness(r=0.0, l=1.0, f=0.0)
        assert tc.l == pytest.approx(1.0, abs=1e-4)

    def test_pure_fascist(self) -> None:
        """Pure fascist: r=0, l=0, f=1."""
        from babylon.models.entities.consciousness import TernaryConsciousness

        tc = TernaryConsciousness(r=0.0, l=0.0, f=1.0)
        assert tc.f == pytest.approx(1.0, abs=1e-4)


@pytest.mark.unit
class TestTernaryBackwardCompatProperties:
    """Test computed properties for backward compatibility."""

    def test_collective_identity_equals_r(self) -> None:
        """collective_identity property returns r component."""
        from babylon.models.entities.consciousness import TernaryConsciousness

        tc = TernaryConsciousness(r=0.5, l=0.3, f=0.2)
        assert tc.collective_identity == pytest.approx(0.5, abs=1e-4)

    def test_dominant_tendency_liberal(self) -> None:
        """argmax returns LIBERAL when l is largest."""
        from babylon.models.entities.consciousness import TernaryConsciousness

        tc = TernaryConsciousness(r=0.2, l=0.6, f=0.2)
        assert tc.dominant_tendency == ConsciousnessTendency.LIBERAL

    def test_dominant_tendency_revolutionary(self) -> None:
        """argmax returns REVOLUTIONARY when r is largest."""
        from babylon.models.entities.consciousness import TernaryConsciousness

        tc = TernaryConsciousness(r=0.6, l=0.3, f=0.1)
        assert tc.dominant_tendency == ConsciousnessTendency.REVOLUTIONARY

    def test_dominant_tendency_fascist(self) -> None:
        """argmax returns FASCIST when f is largest."""
        from babylon.models.entities.consciousness import TernaryConsciousness

        tc = TernaryConsciousness(r=0.1, l=0.2, f=0.7)
        assert tc.dominant_tendency == ConsciousnessTendency.FASCIST

    def test_dominant_tendency_tie_defaults_liberal(self) -> None:
        """When components are tied, default to liberal (structural advantage)."""
        from babylon.models.entities.consciousness import TernaryConsciousness

        # l and f tied at 0.4, r at 0.2
        tc = TernaryConsciousness(r=0.2, l=0.4, f=0.4)
        assert tc.dominant_tendency == ConsciousnessTendency.LIBERAL

    def test_contestation_pure_vertex_zero(self) -> None:
        """Pure single-vertex yields zero entropy (no contestation)."""
        from babylon.models.entities.consciousness import TernaryConsciousness

        tc = TernaryConsciousness(r=1.0, l=0.0, f=0.0)
        assert tc.ideological_contestation == pytest.approx(0.0, abs=1e-4)

    def test_contestation_uniform_maximum(self) -> None:
        """Uniform distribution yields maximum entropy (1.0 after normalization)."""
        from babylon.models.entities.consciousness import TernaryConsciousness

        tc = TernaryConsciousness(r=0.33333, l=0.33334, f=0.33333)
        assert tc.ideological_contestation == pytest.approx(1.0, abs=0.01)

    def test_contestation_moderate(self) -> None:
        """Non-uniform distribution yields intermediate entropy."""
        from babylon.models.entities.consciousness import TernaryConsciousness

        tc = TernaryConsciousness(r=0.5, l=0.3, f=0.2)
        # Shannon entropy: -sum(p*log(p)) / log(3)
        raw_entropy = -(0.5 * math.log(0.5) + 0.3 * math.log(0.3) + 0.2 * math.log(0.2))
        expected = raw_entropy / math.log(3)
        assert tc.ideological_contestation == pytest.approx(expected, abs=0.01)

    def test_assimilation_ratio_balanced(self) -> None:
        """assimilation_ratio = f / (l + f)."""
        from babylon.models.entities.consciousness import TernaryConsciousness

        tc = TernaryConsciousness(r=0.2, l=0.4, f=0.4)
        assert tc.assimilation_ratio == pytest.approx(0.5, abs=1e-4)

    def test_assimilation_ratio_all_liberal(self) -> None:
        """When f=0, assimilation_ratio is 0 (no fascist component)."""
        from babylon.models.entities.consciousness import TernaryConsciousness

        tc = TernaryConsciousness(r=0.3, l=0.7, f=0.0)
        assert tc.assimilation_ratio == pytest.approx(0.0, abs=1e-4)

    def test_assimilation_ratio_all_revolutionary(self) -> None:
        """When l+f near zero, assimilation_ratio defaults to 0.5."""
        from babylon.models.entities.consciousness import TernaryConsciousness

        tc = TernaryConsciousness(r=1.0, l=0.0, f=0.0)
        assert tc.assimilation_ratio == pytest.approx(0.5, abs=1e-4)


@pytest.mark.unit
class TestTernaryLegacyConstruction:
    """Test backward-compatible construction with old kwargs."""

    def test_legacy_liberal_kwargs(self) -> None:
        """Legacy kwargs (CI=0.5, tendency=LIBERAL, contestation=0.4) accepted."""
        from babylon.models.entities.consciousness import TernaryConsciousness

        tc = TernaryConsciousness(
            collective_identity=0.5,
            dominant_tendency=ConsciousnessTendency.LIBERAL,
            ideological_contestation=0.4,
        )
        assert tc.collective_identity == pytest.approx(0.5, abs=1e-4)
        assert tc.dominant_tendency == ConsciousnessTendency.LIBERAL
        assert tc.ideological_contestation == pytest.approx(0.4, abs=1e-4)

    def test_legacy_revolutionary_kwargs(self) -> None:
        """Legacy REVOLUTIONARY construction preserves tendency."""
        from babylon.models.entities.consciousness import TernaryConsciousness

        tc = TernaryConsciousness(
            collective_identity=0.6,
            dominant_tendency=ConsciousnessTendency.REVOLUTIONARY,
            ideological_contestation=0.3,
        )
        assert tc.collective_identity == pytest.approx(0.6, abs=1e-4)
        assert tc.dominant_tendency == ConsciousnessTendency.REVOLUTIONARY
        assert tc.ideological_contestation == pytest.approx(0.3, abs=1e-4)

    def test_legacy_fascist_kwargs(self) -> None:
        """Legacy FASCIST construction preserves tendency."""
        from babylon.models.entities.consciousness import TernaryConsciousness

        tc = TernaryConsciousness(
            collective_identity=0.3,
            dominant_tendency=ConsciousnessTendency.FASCIST,
            ideological_contestation=0.3,
        )
        assert tc.collective_identity == pytest.approx(0.3, abs=1e-4)
        assert tc.dominant_tendency == ConsciousnessTendency.FASCIST
        assert tc.ideological_contestation == pytest.approx(0.3, abs=1e-4)

    def test_legacy_default_construction(self) -> None:
        """Empty construction produces same defaults as old model."""
        from babylon.models.entities.consciousness import TernaryConsciousness

        tc = TernaryConsciousness()
        assert tc.collective_identity == pytest.approx(0.3, abs=1e-4)
        assert tc.dominant_tendency == ConsciousnessTendency.LIBERAL
        assert tc.ideological_contestation == pytest.approx(0.2, abs=1e-4)

    def test_legacy_simplex_holds(self) -> None:
        """Legacy construction always produces valid simplex point."""
        from babylon.models.entities.consciousness import TernaryConsciousness

        for ci in [0.1, 0.3, 0.5, 0.7, 0.9]:
            for tendency in ConsciousnessTendency:
                tc = TernaryConsciousness(
                    collective_identity=ci,
                    dominant_tendency=tendency,
                    ideological_contestation=0.3,
                )
                assert tc.r + tc.l + tc.f == pytest.approx(1.0, abs=1e-4), (
                    f"Simplex violated for ci={ci}, tendency={tendency}"
                )

    def test_legacy_r_equals_ci(self) -> None:
        """In legacy construction, r always equals collective_identity."""
        from babylon.models.entities.consciousness import TernaryConsciousness

        tc = TernaryConsciousness(
            collective_identity=0.7,
            dominant_tendency=ConsciousnessTendency.LIBERAL,
            ideological_contestation=0.2,
        )
        assert tc.r == pytest.approx(0.7, abs=1e-4)


@pytest.mark.unit
class TestTernarySerialization:
    """Test model_dump / model_validate roundtrip."""

    def test_native_roundtrip(self) -> None:
        """Native TernaryConsciousness survives model_dump→model_validate."""
        from babylon.models.entities.consciousness import TernaryConsciousness

        original = TernaryConsciousness(r=0.5, l=0.3, f=0.2)
        data = original.model_dump(mode="json")
        restored = TernaryConsciousness.model_validate(data)
        assert restored.r == pytest.approx(original.r, abs=1e-4)
        assert restored.l == pytest.approx(original.l, abs=1e-4)
        assert restored.f == pytest.approx(original.f, abs=1e-4)

    def test_legacy_roundtrip(self) -> None:
        """Legacy-constructed TernaryConsciousness survives roundtrip."""
        from babylon.models.entities.consciousness import TernaryConsciousness

        original = TernaryConsciousness(
            collective_identity=0.5,
            dominant_tendency=ConsciousnessTendency.LIBERAL,
            ideological_contestation=0.4,
        )
        data = original.model_dump(mode="json")
        restored = TernaryConsciousness.model_validate(data)
        assert restored.collective_identity == pytest.approx(0.5, abs=1e-4)
        assert restored.ideological_contestation == pytest.approx(0.4, abs=1e-4)

    def test_roundtrip_preserves_contestation_stored(self) -> None:
        """contestation_stored survives roundtrip for legacy objects."""
        from babylon.models.entities.consciousness import TernaryConsciousness

        original = TernaryConsciousness(
            collective_identity=0.2,
            dominant_tendency=ConsciousnessTendency.LIBERAL,
            ideological_contestation=0.5,
        )
        data = original.model_dump(mode="json")
        restored = TernaryConsciousness.model_validate(data)
        # The stored contestation should be preserved
        assert restored.ideological_contestation == pytest.approx(0.5, abs=1e-4)

    def test_native_no_contestation_stored(self) -> None:
        """Natively constructed objects have contestation_stored=None."""
        from babylon.models.entities.consciousness import TernaryConsciousness

        tc = TernaryConsciousness(r=0.5, l=0.3, f=0.2)
        assert tc.contestation_stored is None

    def test_legacy_has_contestation_stored(self) -> None:
        """Legacy-constructed objects store their contestation value."""
        from babylon.models.entities.consciousness import TernaryConsciousness

        tc = TernaryConsciousness(
            collective_identity=0.5,
            dominant_tendency=ConsciousnessTendency.LIBERAL,
            ideological_contestation=0.4,
        )
        assert tc.contestation_stored == pytest.approx(0.4, abs=1e-4)


@pytest.mark.unit
class TestSubstrateFloor:
    """Test SubstrateFloor model."""

    def test_create_synthetic(self) -> None:
        """SubstrateFloor creates with SYNTHETIC provenance."""
        from babylon.models.entities.consciousness import ProvenanceLevel, SubstrateFloor
        from babylon.models.enums import CommunityType

        sf = SubstrateFloor(
            community_type=CommunityType.NEW_AFRIKAN,
            floor_value=0.12,
            confidence=ProvenanceLevel.SYNTHETIC,
        )
        assert sf.floor_value == pytest.approx(0.12, abs=1e-4)
        assert sf.confidence == ProvenanceLevel.SYNTHETIC

    def test_create_with_sources(self) -> None:
        """SubstrateFloor with data sources and method."""
        from babylon.models.entities.consciousness import ProvenanceLevel, SubstrateFloor
        from babylon.models.enums import CommunityType

        sf = SubstrateFloor(
            community_type=CommunityType.INCARCERATED,
            floor_value=0.18,
            confidence=ProvenanceLevel.MEDIUM,
            data_sources=["Vera incarceration"],
            computation_method="incarceration_rate_proxy",
        )
        assert sf.confidence == ProvenanceLevel.MEDIUM
        assert len(sf.data_sources) == 1

    def test_frozen(self) -> None:
        """SubstrateFloor is frozen."""
        from babylon.models.entities.consciousness import ProvenanceLevel, SubstrateFloor
        from babylon.models.enums import CommunityType

        sf = SubstrateFloor(
            community_type=CommunityType.SETTLER,
            floor_value=0.0,
            confidence=ProvenanceLevel.HIGH,
        )
        with pytest.raises(ValidationError):
            sf.floor_value = 0.5  # type: ignore[misc]

    def test_default_floor_zero(self) -> None:
        """Default floor_value is 0.0."""
        from babylon.models.entities.consciousness import SubstrateFloor
        from babylon.models.enums import CommunityType

        sf = SubstrateFloor(community_type=CommunityType.ADULT)
        assert sf.floor_value == pytest.approx(0.0, abs=1e-4)


@pytest.mark.unit
class TestOrgContribution:
    """Test OrgContribution model."""

    def test_create(self) -> None:
        """OrgContribution creates with required fields."""
        from babylon.models.entities.consciousness import OrgContribution

        oc = OrgContribution(
            tendency=ConsciousnessTendency.REVOLUTIONARY,
            membership_density=0.1,
            cadre_level=0.8,
            cohesion=0.9,
        )
        assert oc.tendency == ConsciousnessTendency.REVOLUTIONARY
        assert oc.membership_density == pytest.approx(0.1, abs=1e-4)

    def test_frozen(self) -> None:
        """OrgContribution is frozen."""
        from babylon.models.entities.consciousness import OrgContribution

        oc = OrgContribution(
            tendency=ConsciousnessTendency.LIBERAL,
            membership_density=0.2,
            cadre_level=0.5,
            cohesion=0.5,
        )
        with pytest.raises(ValidationError):
            oc.membership_density = 0.9  # type: ignore[misc]


@pytest.mark.unit
class TestProvenanceLevel:
    """Test ProvenanceLevel enum."""

    def test_has_four_values(self) -> None:
        """ProvenanceLevel has exactly 4 values."""
        from babylon.models.entities.consciousness import ProvenanceLevel

        assert len(ProvenanceLevel) == 4

    def test_values(self) -> None:
        """ProvenanceLevel has HIGH, MEDIUM, LOW, SYNTHETIC."""
        from babylon.models.entities.consciousness import ProvenanceLevel

        assert ProvenanceLevel.HIGH.value == "high"
        assert ProvenanceLevel.MEDIUM.value == "medium"
        assert ProvenanceLevel.LOW.value == "low"
        assert ProvenanceLevel.SYNTHETIC.value == "synthetic"
