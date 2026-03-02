"""Tests for compute_ternary_consciousness() (Feature 034, US1).

Covers 6 acceptance scenarios from spec.md plus edge cases.
TDD red phase: these tests are written BEFORE the function exists.
"""

from __future__ import annotations

import pytest

from babylon.models.entities.consciousness import OrgContribution, TernaryConsciousness
from babylon.models.enums import CommunityType, ConsciousnessTendency


@pytest.mark.unit
class TestComputeTernaryConsciousness:
    """Acceptance scenarios from spec 034 US1."""

    def test_as1_rev_and_liberal_orgs(self) -> None:
        """AS1: Community with rev + liberal orgs produces expected r/l/f.

        Population 1000, rev org with 100 members (density=0.1),
        liberal org with 200 members (density=0.2). Unorganized 700
        default to liberal.

        Expected: r=0.1, l=0.2+0.7=0.9, f=0.0 → normalized simplex.
        """
        from babylon.formulas.consciousness import compute_ternary_consciousness

        org_landscape = [
            OrgContribution(
                tendency=ConsciousnessTendency.REVOLUTIONARY,
                membership_density=0.1,
                cadre_level=1.0,
                cohesion=1.0,
            ),
            OrgContribution(
                tendency=ConsciousnessTendency.LIBERAL,
                membership_density=0.2,
                cadre_level=1.0,
                cohesion=1.0,
            ),
        ]
        result = compute_ternary_consciousness(
            community_type=CommunityType.NEW_AFRIKAN,
            org_landscape=org_landscape,
            substrate_floor=0.0,
        )
        assert isinstance(result, TernaryConsciousness)
        assert float(result.r) == pytest.approx(0.1, abs=1e-3)
        # l = organized liberal (0.2) + unorganized (0.7) = 0.9
        assert float(result.l) == pytest.approx(0.9, abs=1e-3)
        assert float(result.f) == pytest.approx(0.0, abs=1e-3)

    def test_as2_no_orgs_liberal_default(self) -> None:
        """AS2: No organizations → substrate_floor/liberal default."""
        from babylon.formulas.consciousness import compute_ternary_consciousness

        result = compute_ternary_consciousness(
            community_type=CommunityType.NEW_AFRIKAN,
            org_landscape=[],
            substrate_floor=0.12,
        )
        assert float(result.r) == pytest.approx(0.12, abs=1e-3)
        assert float(result.l) == pytest.approx(0.88, abs=1e-3)
        assert float(result.f) == pytest.approx(0.0, abs=1e-3)

    def test_as3_doubling_membership_increases_r(self) -> None:
        """AS3: Doubling rev org membership increases r proportionally."""
        from babylon.formulas.consciousness import compute_ternary_consciousness

        org_single = [
            OrgContribution(
                tendency=ConsciousnessTendency.REVOLUTIONARY,
                membership_density=0.1,
                cadre_level=1.0,
                cohesion=1.0,
            ),
        ]
        org_double = [
            OrgContribution(
                tendency=ConsciousnessTendency.REVOLUTIONARY,
                membership_density=0.2,
                cadre_level=1.0,
                cohesion=1.0,
            ),
        ]
        r1 = compute_ternary_consciousness(
            community_type=CommunityType.SETTLER,
            org_landscape=org_single,
            substrate_floor=0.0,
        )
        r2 = compute_ternary_consciousness(
            community_type=CommunityType.SETTLER,
            org_landscape=org_double,
            substrate_floor=0.0,
        )
        assert float(r2.r) > float(r1.r)
        # With full cadre/cohesion, doubling density should double r
        assert float(r2.r) == pytest.approx(2.0 * float(r1.r), abs=1e-3)

    def test_as4_cointelpro_drops_to_floor(self) -> None:
        """AS4: Destroy all rev orgs → r drops to substrate_floor, not zero."""
        from babylon.formulas.consciousness import compute_ternary_consciousness

        floor = 0.12
        # All rev orgs destroyed — empty landscape
        result = compute_ternary_consciousness(
            community_type=CommunityType.NEW_AFRIKAN,
            org_landscape=[],
            substrate_floor=floor,
        )
        assert float(result.r) == pytest.approx(floor, abs=1e-3)
        assert float(result.r) > 0.0

    def test_as5_floor_differential(self) -> None:
        """AS5: Identical org landscape, different floors → r differs by floor."""
        from babylon.formulas.consciousness import compute_ternary_consciousness

        orgs = [
            OrgContribution(
                tendency=ConsciousnessTendency.LIBERAL,
                membership_density=0.3,
                cadre_level=1.0,
                cohesion=1.0,
            ),
        ]
        na_floor = 0.12
        settler_floor = 0.0

        na = compute_ternary_consciousness(
            community_type=CommunityType.NEW_AFRIKAN,
            org_landscape=orgs,
            substrate_floor=na_floor,
        )
        settler = compute_ternary_consciousness(
            community_type=CommunityType.SETTLER,
            org_landscape=orgs,
            substrate_floor=settler_floor,
        )
        # r should differ by floor differential
        assert float(na.r) - float(settler.r) == pytest.approx(na_floor - settler_floor, abs=1e-3)

    def test_as6_backward_compat_properties(self) -> None:
        """AS6: Computed consciousness exposes backward-compat properties."""
        from babylon.formulas.consciousness import compute_ternary_consciousness

        orgs = [
            OrgContribution(
                tendency=ConsciousnessTendency.REVOLUTIONARY,
                membership_density=0.4,
                cadre_level=1.0,
                cohesion=1.0,
            ),
        ]
        result = compute_ternary_consciousness(
            community_type=CommunityType.NEW_AFRIKAN,
            org_landscape=orgs,
            substrate_floor=0.0,
        )
        # collective_identity = r
        assert result.collective_identity == pytest.approx(float(result.r), abs=1e-6)
        # dominant_tendency is derivable
        assert isinstance(result.dominant_tendency, ConsciousnessTendency)
        # ideological_contestation is Shannon entropy (no contestation_stored)
        assert result.contestation_stored is None
        assert 0.0 <= result.ideological_contestation <= 1.0


@pytest.mark.unit
class TestComputeEdgeCases:
    """Edge cases for compute_ternary_consciousness()."""

    def test_single_tendency_near_vertex(self) -> None:
        """Single dominant org pins consciousness near a vertex."""
        from babylon.formulas.consciousness import compute_ternary_consciousness

        orgs = [
            OrgContribution(
                tendency=ConsciousnessTendency.FASCIST,
                membership_density=0.9,
                cadre_level=1.0,
                cohesion=1.0,
            ),
        ]
        result = compute_ternary_consciousness(
            community_type=CommunityType.SETTLER,
            org_landscape=orgs,
            substrate_floor=0.0,
        )
        # f should dominate, l gets unorganized fraction (0.1)
        assert float(result.f) > 0.8
        assert float(result.l) < 0.15

    def test_empty_landscape_no_floor(self) -> None:
        """No orgs, no floor → pure liberal default."""
        from babylon.formulas.consciousness import compute_ternary_consciousness

        result = compute_ternary_consciousness(
            community_type=CommunityType.SETTLER,
            org_landscape=[],
            substrate_floor=0.0,
        )
        assert float(result.r) == pytest.approx(0.0, abs=1e-6)
        assert float(result.l) == pytest.approx(1.0, abs=1e-3)
        assert float(result.f) == pytest.approx(0.0, abs=1e-6)

    def test_substrate_floor_dominates(self) -> None:
        """Substrate floor > org contribution → floor wins."""
        from babylon.formulas.consciousness import compute_ternary_consciousness

        orgs = [
            OrgContribution(
                tendency=ConsciousnessTendency.REVOLUTIONARY,
                membership_density=0.05,
                cadre_level=0.5,
                cohesion=0.5,
            ),
        ]
        # Floor of 0.2 exceeds org contribution of 0.05*0.5*0.5=0.0125
        result = compute_ternary_consciousness(
            community_type=CommunityType.INCARCERATED,
            org_landscape=orgs,
            substrate_floor=0.2,
        )
        assert float(result.r) >= 0.2

    def test_cadre_and_cohesion_weight(self) -> None:
        """Lower cadre_level and cohesion reduce effective contribution."""
        from babylon.formulas.consciousness import compute_ternary_consciousness

        full = [
            OrgContribution(
                tendency=ConsciousnessTendency.REVOLUTIONARY,
                membership_density=0.2,
                cadre_level=1.0,
                cohesion=1.0,
            ),
        ]
        half = [
            OrgContribution(
                tendency=ConsciousnessTendency.REVOLUTIONARY,
                membership_density=0.2,
                cadre_level=0.5,
                cohesion=0.5,
            ),
        ]
        r_full = compute_ternary_consciousness(
            community_type=CommunityType.SETTLER,
            org_landscape=full,
            substrate_floor=0.0,
        )
        r_half = compute_ternary_consciousness(
            community_type=CommunityType.SETTLER,
            org_landscape=half,
            substrate_floor=0.0,
        )
        assert float(r_full.r) > float(r_half.r)

    def test_simplex_always_holds(self) -> None:
        """All computed results satisfy simplex constraint."""
        from babylon.formulas.consciousness import compute_ternary_consciousness

        for density in [0.0, 0.1, 0.5, 0.9, 1.0]:
            orgs = [
                OrgContribution(
                    tendency=ConsciousnessTendency.REVOLUTIONARY,
                    membership_density=density,
                    cadre_level=0.8,
                    cohesion=0.7,
                ),
            ]
            result = compute_ternary_consciousness(
                community_type=CommunityType.SETTLER,
                org_landscape=orgs,
                substrate_floor=0.0,
            )
            total = float(result.r) + float(result.l) + float(result.f)
            assert total == pytest.approx(1.0, abs=1e-4)

    def test_multiple_orgs_same_tendency(self) -> None:
        """Multiple orgs of same tendency stack contributions."""
        from babylon.formulas.consciousness import compute_ternary_consciousness

        orgs = [
            OrgContribution(
                tendency=ConsciousnessTendency.REVOLUTIONARY,
                membership_density=0.1,
                cadre_level=1.0,
                cohesion=1.0,
            ),
            OrgContribution(
                tendency=ConsciousnessTendency.REVOLUTIONARY,
                membership_density=0.15,
                cadre_level=1.0,
                cohesion=1.0,
            ),
        ]
        result = compute_ternary_consciousness(
            community_type=CommunityType.SETTLER,
            org_landscape=orgs,
            substrate_floor=0.0,
        )
        # Combined density = 0.25
        assert float(result.r) == pytest.approx(0.25, abs=1e-3)

    def test_total_density_exceeds_one_capped(self) -> None:
        """If total org density > 1.0, unorganized = 0."""
        from babylon.formulas.consciousness import compute_ternary_consciousness

        orgs = [
            OrgContribution(
                tendency=ConsciousnessTendency.REVOLUTIONARY,
                membership_density=0.6,
                cadre_level=1.0,
                cohesion=1.0,
            ),
            OrgContribution(
                tendency=ConsciousnessTendency.LIBERAL,
                membership_density=0.5,
                cadre_level=1.0,
                cohesion=1.0,
            ),
        ]
        result = compute_ternary_consciousness(
            community_type=CommunityType.SETTLER,
            org_landscape=orgs,
            substrate_floor=0.0,
        )
        # Total density > 1.0 — no unorganized fraction, just normalize
        total = float(result.r) + float(result.l) + float(result.f)
        assert total == pytest.approx(1.0, abs=1e-4)
        # r should be roughly 0.6/(0.6+0.5) ≈ 0.545
        assert float(result.r) == pytest.approx(0.6 / 1.1, abs=1e-2)
