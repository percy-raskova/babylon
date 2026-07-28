"""Behavioral contract for the LEGISLATE resolver (P25 U9, ADR135).

``resolve_legislate`` is the pure pipeline the-electoral-question.md §2.4
names: agenda item → veto gauntlet (preemption, judicial) → fiscal check
(the funding identity / L-CEILING) → enactment with the delivery gap and the
capital-strike arm. Everything here is pure — the PolicySystem does the
graph I/O; these laws never see a graph.
"""

from __future__ import annotations

import pytest

from babylon.config.defines import GameDefines
from babylon.domain.politics.policy import (
    FiscalTerrain,
    PolicyAgendaItem,
    PolicyResolution,
    PolicyResolutionKind,
    VetoGauntlet,
    policy_incidence,
    resolve_legislate,
)
from babylon.models.enums import PolicyAxis

pytestmark = pytest.mark.unit

_DEFINES = GameDefines().politics


def _item(
    axis: PolicyAxis = PolicyAxis.SOCIAL_WAGE,
    magnitude: float = 0.1,
    promised: float = 50.0,
    sovereign_id: str = "SOV_USA_FED",
) -> PolicyAgendaItem:
    return PolicyAgendaItem(
        sovereign_id=sovereign_id,
        axis=axis,
        magnitude=magnitude,
        promised=promised,
        drafted_tick=1,
    )


def _terrain(
    t_claim: float = 100.0,
    phi_inflow: float = 40.0,
    interest_rate: float = 0.05,
    debt_stock: float = 0.0,
    total_surplus: float = 1000.0,
) -> FiscalTerrain:
    return FiscalTerrain(
        t_claim=t_claim,
        phi_inflow=phi_inflow,
        interest_rate=interest_rate,
        debt_stock=debt_stock,
        total_surplus=total_surplus,
    )


class TestPolicyIncidence:
    def test_social_wage_incidence_is_promise_over_surplus(self) -> None:
        item = _item(promised=150.0)
        assert policy_incidence(item, total_surplus=1000.0) == pytest.approx(0.15)

    def test_promise_with_no_measured_surplus_claims_everything(self) -> None:
        item = _item(promised=10.0)
        assert policy_incidence(item, total_surplus=0.0) == 1.0

    def test_regulatory_redistributive_axes_carry_magnitude_as_incidence(self) -> None:
        for axis in (PolicyAxis.WAGE_FLOOR, PolicyAxis.LABOR_LAW):
            item = _item(axis=axis, magnitude=0.3, promised=0.0)
            assert policy_incidence(item, total_surplus=1000.0) == pytest.approx(0.3)

    def test_state_apparatus_axes_have_zero_capital_incidence(self) -> None:
        for axis in (PolicyAxis.POLICE_BUDGET, PolicyAxis.BORDER_REGIME, PolicyAxis.WAR_POSTURE):
            item = _item(axis=axis, magnitude=0.9, promised=0.0)
            assert policy_incidence(item, total_surplus=1000.0) == 0.0


class TestVetoGauntletOrder:
    def test_preemption_fires_for_lower_sovereign_past_envelope(self) -> None:
        item = _item(sovereign_id="SOV_MI_STATE", magnitude=0.9)
        gauntlet = VetoGauntlet(administers_parent="SOV_USA_FED")
        res = resolve_legislate(item, _terrain(), gauntlet, _DEFINES)
        assert res.kind is PolicyResolutionKind.PREEMPTED
        assert res.preempting_sovereign == "SOV_USA_FED"

    def test_apex_sovereign_is_never_preempted(self) -> None:
        item = _item(magnitude=0.9, promised=0.0, axis=PolicyAxis.BORDER_REGIME)
        res = resolve_legislate(item, _terrain(), VetoGauntlet(), _DEFINES)
        assert res.kind is PolicyResolutionKind.ENACTED

    def test_judicial_strike_down_by_class_balance_tolerance(self) -> None:
        """A revanchist bench (low liberal_technocratic weight) voids
        redistribution a liberal bench tolerates."""
        item = _item(promised=200.0)  # incidence 0.2 on surplus 1000
        liberal = VetoGauntlet(judicial_benches=(("INST_COURT", 0.6),))
        revanchist = VetoGauntlet(judicial_benches=(("INST_COURT", 0.1),))
        enacted = resolve_legislate(item, _terrain(), liberal, _DEFINES)
        struck = resolve_legislate(item, _terrain(), revanchist, _DEFINES)
        assert enacted.kind is PolicyResolutionKind.ENACTED
        assert struck.kind is PolicyResolutionKind.STRUCK
        assert struck.striking_institution == "INST_COURT"

    def test_preemption_precedes_judicial_review(self) -> None:
        """An item both preemptable and strikeable dies to preemption —
        jurisdiction is checked before the bench ever sees it."""
        item = _item(sovereign_id="SOV_MI_STATE", magnitude=0.9, promised=900.0)
        gauntlet = VetoGauntlet(
            administers_parent="SOV_USA_FED",
            judicial_benches=(("INST_COURT", 0.0),),
        )
        res = resolve_legislate(item, _terrain(), gauntlet, _DEFINES)
        assert res.kind is PolicyResolutionKind.PREEMPTED


class TestFundingIdentity:
    def test_fully_funded_promise_delivers_fully(self) -> None:
        item = _item(promised=50.0)
        res = resolve_legislate(item, _terrain(), VetoGauntlet(), _DEFINES)
        assert res.kind is PolicyResolutionKind.ENACTED
        assert res.delivered == pytest.approx(50.0)
        assert res.ratio == pytest.approx(1.0)
        assert res.gap == pytest.approx(0.0)
        assert res.borrowed == pytest.approx(0.0)

    def test_l_ceiling_binds_delivery_to_funded_plus_borrowed(self) -> None:
        """L-CEILING: delivered ≤ t_claim + φ_share·Φ − debt_service +
        borrowed, and never exceeds the promise."""
        terrain = _terrain(t_claim=60.0, phi_inflow=40.0)
        item = _item(promised=200.0)
        res = resolve_legislate(item, terrain, VetoGauntlet(), _DEFINES)
        funded = 60.0 + _DEFINES.phi_social_share * 40.0
        shortfall = 200.0 - funded
        borrowed = shortfall * _DEFINES.debt_finance_share
        assert res.borrowed == pytest.approx(borrowed)
        assert res.delivered == pytest.approx(funded + borrowed)
        assert res.delivered <= res.promised
        assert res.gap == pytest.approx(200.0 - res.delivered)
        assert 0.0 <= res.ratio < 1.0

    def test_debt_service_shrinks_the_funded_ceiling(self) -> None:
        light = resolve_legislate(_item(promised=200.0), _terrain(), VetoGauntlet(), _DEFINES)
        indebted = resolve_legislate(
            _item(promised=200.0),
            _terrain(debt_stock=1000.0, interest_rate=0.05),
            VetoGauntlet(),
            _DEFINES,
        )
        assert indebted.delivered < light.delivered

    def test_bond_discipline_blocks_borrowing(self) -> None:
        """Once debt_service / t_claim crosses the threshold, deficit
        financing is refused and delivery collapses to the funded ceiling."""
        terrain = _terrain(t_claim=100.0, phi_inflow=0.0, debt_stock=1000.0, interest_rate=0.05)
        assert _DEFINES.bond_discipline_threshold < 50.0 / 100.0
        res = resolve_legislate(_item(promised=200.0), terrain, VetoGauntlet(), _DEFINES)
        assert res.borrowed == 0.0
        assert res.delivered == pytest.approx(100.0 - 50.0)

    def test_regulatory_axis_needs_no_funding(self) -> None:
        item = _item(axis=PolicyAxis.WAGE_FLOOR, magnitude=0.05, promised=0.0)
        res = resolve_legislate(
            item, _terrain(t_claim=0.0, phi_inflow=0.0), VetoGauntlet(), _DEFINES
        )
        assert res.kind is PolicyResolutionKind.ENACTED
        assert res.ratio == pytest.approx(1.0)
        assert res.gap == pytest.approx(0.0)


class TestCapitalStrike:
    def test_incidence_past_tolerance_arms_the_strike(self) -> None:
        item = _item(promised=300.0)  # incidence 0.3 > capital_tolerance 0.15
        res = resolve_legislate(item, _terrain(), VetoGauntlet(), _DEFINES)
        assert res.kind is PolicyResolutionKind.ENACTED
        assert res.capital_strike is True
        assert res.incidence == pytest.approx(0.3)

    def test_incidence_within_tolerance_does_not_strike(self) -> None:
        item = _item(promised=50.0)  # incidence 0.05
        res = resolve_legislate(item, _terrain(), VetoGauntlet(), _DEFINES)
        assert res.capital_strike is False


class TestDeterminism:
    def test_same_inputs_same_resolution(self) -> None:
        item = _item(promised=137.5)
        gauntlet = VetoGauntlet(judicial_benches=(("INST_A", 0.4), ("INST_B", 0.2)))
        first = resolve_legislate(item, _terrain(), gauntlet, _DEFINES)
        second = resolve_legislate(item, _terrain(), gauntlet, _DEFINES)
        assert first == second
        assert isinstance(first, PolicyResolution)


class TestTradeTariffAxis:
    """P26 U5f (ADR165): trade_tariff reuses the regulatory-redistributive
    gauntlet exactly like wage_floor/labor_law — the minimal, pattern-
    faithful LEGISLATE instrument for the first P25<->P26 coupling."""

    def test_incidence_is_the_overlay_magnitude(self) -> None:
        item = _item(axis=PolicyAxis.TRADE_TARIFF, magnitude=0.12, promised=0.0)
        assert policy_incidence(item, total_surplus=1000.0) == pytest.approx(0.12)

    def test_needs_no_funding(self) -> None:
        item = _item(axis=PolicyAxis.TRADE_TARIFF, magnitude=0.05, promised=0.0)
        res = resolve_legislate(
            item, _terrain(t_claim=0.0, phi_inflow=0.0), VetoGauntlet(), _DEFINES
        )
        assert res.kind is PolicyResolutionKind.ENACTED
        assert res.ratio == pytest.approx(1.0)
        assert res.gap == pytest.approx(0.0)

    def test_subject_to_the_preemption_envelope(self) -> None:
        item = _item(axis=PolicyAxis.TRADE_TARIFF, magnitude=0.9, sovereign_id="SOV_MI_STATE")
        gauntlet = VetoGauntlet(administers_parent="SOV_USA_FED")
        res = resolve_legislate(item, _terrain(), gauntlet, _DEFINES)
        assert res.kind is PolicyResolutionKind.PREEMPTED
        assert res.preempting_sovereign == "SOV_USA_FED"

    def test_subject_to_judicial_strike_down(self) -> None:
        item = _item(axis=PolicyAxis.TRADE_TARIFF, magnitude=0.4, promised=0.0)
        revanchist = VetoGauntlet(judicial_benches=(("INST_COURT", 0.1),))
        res = resolve_legislate(item, _terrain(), revanchist, _DEFINES)
        assert res.kind is PolicyResolutionKind.STRUCK
        assert res.striking_institution == "INST_COURT"

    def test_arms_the_capital_strike_past_tolerance(self) -> None:
        item = _item(axis=PolicyAxis.TRADE_TARIFF, magnitude=0.3, promised=0.0)
        res = resolve_legislate(item, _terrain(), VetoGauntlet(), _DEFINES)
        assert res.kind is PolicyResolutionKind.ENACTED
        assert res.capital_strike is True

    def test_zero_magnitude_is_a_true_no_op_enactment(self) -> None:
        """The default-inert pin at the resolver grain: a trade_tariff
        motion carrying the GameDefines-inert magnitude (0.0) enacts with
        zero incidence, no strike, no gap, no borrowing — the resolver-
        level twin of TradePolicyDefines' zero-rate defaults."""
        item = _item(axis=PolicyAxis.TRADE_TARIFF, magnitude=0.0, promised=0.0)
        res = resolve_legislate(item, _terrain(), VetoGauntlet(), _DEFINES)
        assert res.kind is PolicyResolutionKind.ENACTED
        assert res.incidence == 0.0
        assert res.capital_strike is False
        assert res.gap == pytest.approx(0.0)
        assert res.borrowed == pytest.approx(0.0)


class TestPeripheryMirror:
    """U12 E (§4): in low-Φ sovereigns the same machinery with no rent
    cushion — every gauntlet bar contracts by ``periphery_ceiling_factor``
    and the ceiling arrives immediately. Peripheral status requires a
    MEASURED Φ share (III.11): an unmeasured terrain is never classified."""

    @staticmethod
    def _peripheral_terrain(**overrides: float | bool) -> FiscalTerrain:
        base: dict[str, float | bool] = {
            "t_claim": 100.0,
            "phi_inflow": 0.0,  # measured, and measured to be nothing
            "interest_rate": 0.05,
            "debt_stock": 0.0,
            "total_surplus": 1000.0,
            "phi_measured": True,
        }
        base.update(overrides)
        return FiscalTerrain.model_validate(base)

    def test_unmeasured_phi_is_never_peripheral(self) -> None:
        # The default _terrain() carries phi_measured=False — identical
        # verdicts to the pre-E resolver on every path.
        item = _item(axis=PolicyAxis.SOCIAL_WAGE, promised=80.0)
        gauntlet = VetoGauntlet(judicial_benches=(("INST_J", 0.6),))
        res = resolve_legislate(item, _terrain(phi_inflow=0.0), gauntlet, _DEFINES)
        assert res.kind is PolicyResolutionKind.ENACTED

    def test_core_share_above_floor_is_not_peripheral(self) -> None:
        # phi 40/1000 = 0.04 < 0.05 floor would be peripheral — use 100.
        item = _item(axis=PolicyAxis.SOCIAL_WAGE, promised=80.0)
        gauntlet = VetoGauntlet(judicial_benches=(("INST_J", 0.6),))
        res = resolve_legislate(
            item,
            self._peripheral_terrain(phi_inflow=100.0),  # share 0.10 >= floor
            gauntlet,
            _DEFINES,
        )
        assert res.kind is PolicyResolutionKind.ENACTED

    def test_peripheral_bench_strikes_what_the_core_enacts(self) -> None:
        """The comprador bench: incidence 0.08 clears the core bar
        (0.6 x 0.5 = 0.3) but not the contracted one (0.3 x 0.25 = 0.075)."""
        item = _item(axis=PolicyAxis.SOCIAL_WAGE, promised=80.0)
        gauntlet = VetoGauntlet(judicial_benches=(("INST_J", 0.6),))
        struck = resolve_legislate(item, self._peripheral_terrain(), gauntlet, _DEFINES)
        assert struck.kind is PolicyResolutionKind.STRUCK
        assert struck.striking_institution == "INST_J"

    def test_peripheral_preemption_envelope_contracts(self) -> None:
        """CLIENT_STATE conditionality on the jurisdictional arm: magnitude
        0.1 sits inside the core envelope (0.2) but past the contracted one
        (0.2 x 0.25 = 0.05)."""
        item = _item(axis=PolicyAxis.WAGE_FLOOR, magnitude=0.1)
        gauntlet = VetoGauntlet(administers_parent="SOV_METROPOLE")
        preempted = resolve_legislate(item, self._peripheral_terrain(), gauntlet, _DEFINES)
        assert preempted.kind is PolicyResolutionKind.PREEMPTED
        core = resolve_legislate(item, _terrain(), gauntlet, _DEFINES)
        assert core.kind is PolicyResolutionKind.ENACTED

    def test_peripheral_capital_tolerance_contracts(self) -> None:
        """Capital-flight exposure: incidence 0.05 is calm in the core
        (tolerance 0.15) and a strike on the periphery (0.15 x 0.25 =
        0.0375)."""
        item = _item(axis=PolicyAxis.SOCIAL_WAGE, promised=50.0)
        res = resolve_legislate(item, self._peripheral_terrain(), VetoGauntlet(), _DEFINES)
        assert res.kind is PolicyResolutionKind.ENACTED
        assert res.capital_strike is True
        core = resolve_legislate(item, _terrain(phi_inflow=100.0), VetoGauntlet(), _DEFINES)
        assert core.capital_strike is False
