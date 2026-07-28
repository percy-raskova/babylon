"""Trade-policy coefficients — tariff/duty/tax levers (P26 U5f, ADR165).

Tariff rates, import duties, and trade taxes are instruments of the
international trade system, ADJUSTED via the Policy system (@17.47, the
LEGISLATE resolver + reform ceiling) and electoral outcomes — the first
concrete P25<->P26 coupling (ADR165 "Additional Director directive").

Every field here is a campaign START value. Once a campaign begins, rates
live as graph/session state written through PolicySystem's ``policy_overlays``
register (:mod:`babylon.engine.systems.policy`) — this file is read once at
init/re-init, never mutated mid-campaign, and never re-read by a running
system. All defaults are 0.0/``{}`` so a fresh campaign with no tariff
LEGISLATE motions ever drafted is byte-identical to pre-U5f behavior
(default-inert law).

See Also:
    :mod:`babylon.domain.economics.trade_policy` — the pure consumer,
    ``effective_trade(trade, tariff_rates, dampening=...)``.
    :class:`babylon.models.enums.politics.PolicyAxis` — ``TRADE_TARIFF``,
    the LEGISLATE instrument these rates are adjusted through post-init.
    ``specs/101-trade-activation/u5-engine-train-contracts.md`` §U5f.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TradePolicyDefines(BaseModel):
    """Tariff/duty/tax START values consumed by the trade dataflow.

    See Also:
        :mod:`babylon.domain.economics.trade_policy`: the pure
        ``effective_trade``/``tariff_dampening`` application.
        :class:`babylon.engine.systems.policy.PolicySystem`: the LEGISLATE
        resolver that moves the ``trade_tariff`` axis post-init (via the
        ``policy_overlays`` register — this file is never re-read).
    """

    model_config = ConfigDict(frozen=True)

    tariff_rates: dict[str, float] = Field(
        default_factory=dict,
        description=(
            "Per-node starting tariff rate in [0, 1] (the fraction of that "
            "node's trade value dampened before any LEGISLATE adjustment), "
            "keyed by the 8 INTERNATIONAL_NODES ids "
            "(persistence.postgres_initialization — not imported here to "
            "keep config below persistence in the layering order; the U5d "
            "attribution init owns key-set validation against the canonical "
            "tuple). Default {} => every node reads 0.0 via "
            "tariff_rates.get(node, 0.0) — byte-identical to pre-U5f "
            "behavior."
        ),
    )
    import_duty_rate: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description=(
            "National import-duty coefficient, applied uniformly across "
            "partner nodes (distinct from the per-node tariff_rates: a "
            "duty is levied at the border regardless of origin bloc). "
            "0.0 is inert."
        ),
    )
    trade_tax_rate: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description=(
            "National trade-tax coefficient — a general levy on "
            "cross-border flow, distinct from a tariff's bloc-targeted or "
            "a duty's border-crossing character. 0.0 is inert."
        ),
    )
    tariff_dampening_coefficient: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description=(
            "The linear pass-through from a tariff RATE to the trade-value "
            "DAMPENING fraction: dampening = coefficient x rate (bounded "
            "[0, 1] so rate x coefficient never exceeds 1.0 — an effective "
            "trade value can never go negative by construction). 1.0 is "
            "the neutral prior (full pass-through, dampening = rate "
            "exactly); a lower coefficient declares that trade responds "
            "less than 1:1 to a tariff (import-demand elasticity < 1). "
            "SYNTHETIC placeholder pending a calibrated elasticity source "
            "— disclosed here, not invented silently downstream. With "
            "tariff_rates defaulting to {}, this coefficient is inert "
            "regardless of its own value (0.0 rate x any coefficient = "
            "0.0 dampening)."
        ),
    )

    @field_validator("tariff_rates")
    @classmethod
    def _rates_in_unit_interval(cls, value: dict[str, float]) -> dict[str, float]:
        """Every per-node rate must sit in [0, 1] — a rate outside that
        range is a config footgun caught at construction (III.11)."""
        bad = {node: rate for node, rate in value.items() if not 0.0 <= rate <= 1.0}
        if bad:
            raise ValueError(f"tariff_rates must be in [0, 1] per node; got {bad}")
        return value


__all__ = ["TradePolicyDefines"]
