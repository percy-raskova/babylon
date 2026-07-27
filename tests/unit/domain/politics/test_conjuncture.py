"""Behavioral contract for the popular-front conjuncture measure (P25 U12, ADR139).

``consolidation_pressure`` is the SINGLE consolidation-pressure measure of
the-electoral-question.md §3.4: the false-consciousness fraction from
``(national_identity, class_consciousness)`` ideology pairs plus the
political-violence route (sovereign stance majority / extraction policy /
``state_violence_index`` graph attrs) — the SAME material signals
``EndgameDetector._axis_fascist_consolidation`` reads. One math, two
adapters: the detector delegates its gate inputs to it (EXACT semantics
preserved — pinned here) and ``ElectoralSystem`` @17.45 calls it for the
``popular_front_trigger`` crossing.

``resolve_popular_front_arm`` is the delegated-judgment arm-selection rule
(BD delegated judgment at charter, ADR127 precedent): the forced choice §3.4
poses to EVERY line resolves by the org's acquired doctrine stances —
apparatus-entangled stances (entryism, governance_road) commit to the
defense of the liberal state; every other line (incl. abstentionists and
orgs that never took the electoral question) holds autonomy.
"""

from __future__ import annotations

import pytest

from babylon.domain.politics.conjuncture import (
    PopularFrontArm,
    consolidation_pressure,
    resolve_popular_front_arm,
)

pytestmark = pytest.mark.unit

#: The EndgameDefines default the detector is calibrated against.
_FRACTION = 0.9


class TestFalseConsciousnessRoute:
    """The spec-116 fraction gate: fascist_share / fascist_majority_fraction."""

    def test_full_fascist_terrain_saturates(self) -> None:
        pressure = consolidation_pressure(
            ((0.9, 0.1), (0.8, 0.2)),
            uphold_stance_majority=False,
            intensify_extraction_majority=False,
            state_violence_index=0.0,
            state_violence_index_max=1.0,
            fascist_majority_fraction=_FRACTION,
        )
        assert pressure == pytest.approx(1.0)

    def test_partial_fraction_scales_by_threshold(self) -> None:
        # 4 of 6 fascist = 0.6667; gated against 0.9 -> 0.7407...
        ideologies = tuple([(0.9, 0.1)] * 4 + [(0.1, 0.9)] * 2)
        pressure = consolidation_pressure(
            ideologies,
            uphold_stance_majority=False,
            intensify_extraction_majority=False,
            state_violence_index=0.0,
            state_violence_index_max=1.0,
            fascist_majority_fraction=_FRACTION,
        )
        assert pressure == pytest.approx((4.0 / 6.0) / _FRACTION)

    def test_tie_is_not_fascist(self) -> None:
        # national_identity == class_consciousness is NOT false consciousness
        # (the detector's strict >).
        pressure = consolidation_pressure(
            ((0.5, 0.5), (0.3, 0.3)),
            uphold_stance_majority=False,
            intensify_extraction_majority=False,
            state_violence_index=0.0,
            state_violence_index_max=1.0,
            fascist_majority_fraction=_FRACTION,
        )
        assert pressure == pytest.approx(0.0)

    def test_empty_terrain_is_absent_not_consolidated(self) -> None:
        pressure = consolidation_pressure(
            (),
            uphold_stance_majority=False,
            intensify_extraction_majority=False,
            state_violence_index=0.0,
            state_violence_index_max=1.0,
            fascist_majority_fraction=_FRACTION,
        )
        assert pressure == pytest.approx(0.0)

    def test_ideology_less_entities_are_neither_bearing_nor_fascist(self) -> None:
        # A None entry (no ideology object) does not count in EITHER tally —
        # the detector's exact (0.0 > 0.0) == False semantics.
        pressure = consolidation_pressure(
            (None, (0.9, 0.1)),
            uphold_stance_majority=False,
            intensify_extraction_majority=False,
            state_violence_index=0.0,
            state_violence_index_max=1.0,
            fascist_majority_fraction=_FRACTION,
        )
        assert pressure == pytest.approx(1.0)

    def test_zero_threshold_degenerates_to_detector_semantics(self) -> None:
        # The detector's _gate_reach: threshold <= 0 -> 1.0 iff value >=
        # threshold (always true for a fraction in [0, 1]).
        pressure = consolidation_pressure(
            ((0.1, 0.9),),
            uphold_stance_majority=False,
            intensify_extraction_majority=False,
            state_violence_index=0.0,
            state_violence_index_max=1.0,
            fascist_majority_fraction=0.0,
        )
        assert pressure == pytest.approx(1.0)


class TestPoliticalViolenceRoute:
    """The spec-070 FR-031 route: mean of the three binary gates."""

    def test_all_three_gates_saturate(self) -> None:
        pressure = consolidation_pressure(
            (),
            uphold_stance_majority=True,
            intensify_extraction_majority=True,
            state_violence_index=1.0,
            state_violence_index_max=1.0,
            fascist_majority_fraction=_FRACTION,
        )
        assert pressure == pytest.approx(1.0)

    def test_two_of_three_gates_reads_two_thirds(self) -> None:
        pressure = consolidation_pressure(
            (),
            uphold_stance_majority=True,
            intensify_extraction_majority=True,
            state_violence_index=0.5,
            state_violence_index_max=1.0,
            fascist_majority_fraction=_FRACTION,
        )
        assert pressure == pytest.approx(2.0 / 3.0)

    def test_violence_below_max_fails_the_gate(self) -> None:
        pressure = consolidation_pressure(
            (),
            uphold_stance_majority=False,
            intensify_extraction_majority=False,
            state_violence_index=0.99,
            state_violence_index_max=1.0,
            fascist_majority_fraction=_FRACTION,
        )
        assert pressure == pytest.approx(0.0)

    def test_absent_violence_index_defaults_cannot_fire(self) -> None:
        # The honest-absent defaults (0.0 / 1.0) can never reach the max.
        pressure = consolidation_pressure(
            (),
            uphold_stance_majority=True,
            intensify_extraction_majority=True,
            state_violence_index=0.0,
            state_violence_index_max=1.0,
            fascist_majority_fraction=_FRACTION,
        )
        assert pressure == pytest.approx(2.0 / 3.0)


class TestMaxOfRoutes:
    """The axis's overall progress is the BETTER of the two routes."""

    def test_violence_route_wins_when_better(self) -> None:
        pressure = consolidation_pressure(
            ((0.9, 0.1), (0.1, 0.9)),  # fc fraction 0.5 -> gate 0.5556
            uphold_stance_majority=True,
            intensify_extraction_majority=True,
            state_violence_index=0.0,
            state_violence_index_max=1.0,
            fascist_majority_fraction=_FRACTION,
        )
        assert pressure == pytest.approx(2.0 / 3.0)

    def test_false_consciousness_route_wins_when_better(self) -> None:
        pressure = consolidation_pressure(
            ((0.9, 0.1), (0.1, 0.9)),  # fc gate 0.5556
            uphold_stance_majority=True,
            intensify_extraction_majority=False,
            state_violence_index=0.0,
            state_violence_index_max=1.0,
            fascist_majority_fraction=_FRACTION,
        )
        assert pressure == pytest.approx(0.5 / _FRACTION)


class TestArmSelection:
    """The §3.4 forced choice, resolved by doctrine stance (delegated ruling)."""

    @pytest.mark.parametrize("stance", ["entryism", "governance_road"])
    def test_apparatus_entangled_stances_commit(self, stance: str) -> None:
        assert resolve_popular_front_arm((stance,)) is PopularFrontArm.COMMIT

    @pytest.mark.parametrize(
        "stance",
        ["abstention_boycott", "class_struggle_elections", "independent_ballot_line"],
    )
    def test_autonomous_stances_hold_autonomy(self, stance: str) -> None:
        assert resolve_popular_front_arm((stance,)) is PopularFrontArm.AUTONOMY

    def test_no_stance_holds_autonomy(self) -> None:
        # An org that never took the electoral question has no liberal-state
        # entanglement to defend.
        assert resolve_popular_front_arm(()) is PopularFrontArm.AUTONOMY

    def test_non_reformist_doctrine_holds_autonomy(self) -> None:
        assert resolve_popular_front_arm(("armed_vanguard",)) is PopularFrontArm.AUTONOMY

    def test_entanglement_dominates_a_mixed_portfolio(self) -> None:
        # An org holding both an autonomous and an entangled line is already
        # inside the machine: it commits.
        assert (
            resolve_popular_front_arm(("abstention_boycott", "entryism")) is PopularFrontArm.COMMIT
        )
