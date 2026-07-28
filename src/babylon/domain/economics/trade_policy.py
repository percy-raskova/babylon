"""Tariff-dampened effective trade values (P26 U5f, ADR165 directive).

Pure function, no I/O: the trade/attribution dataflow (U5d) composes raw
per-node trade volumes with the LEGISLATE-adjusted tariff rates
(``TradePolicyDefines`` START values, moved post-init by PolicySystem's
``policy_overlays`` register via the ``trade_tariff`` axis) and calls this
at init/re-init time — ``trade_i x (1 - tariff_dampening(rate_i))``
(``specs/101-trade-activation/u5-engine-train-contracts.md`` §U5f). This
module never runs in-tick — the determinism red line stays put: the tick
path reads ``external_nodes_phi`` exactly as today.
"""

from __future__ import annotations

from collections.abc import Mapping

__all__ = ["TradePolicyInputError", "effective_trade", "tariff_dampening"]


class TradePolicyInputError(ValueError):
    """Trade or tariff inputs are negative or outside the declared range."""


def tariff_dampening(rate: float, coefficient: float) -> float:
    """Translate one tariff RATE into a trade-value DAMPENING fraction.

    ``dampening = coefficient x rate`` — the linear form named by
    :attr:`~babylon.config.defines.trade_policy.TradePolicyDefines.
    tariff_dampening_coefficient`. Both operands are bounded to ``[0, 1]``
    so the product never exceeds ``1.0``: an effective trade value can
    never go negative by construction.

    :param rate: the node's tariff rate, ``[0, 1]``.
    :param coefficient: the dampening pass-through coefficient, ``[0, 1]``.
    :returns: the dampening fraction in ``[0, 1]``.
    :raises TradePolicyInputError: ``rate`` or ``coefficient`` outside
        ``[0, 1]``.
    """
    if not 0.0 <= rate <= 1.0:
        raise TradePolicyInputError(f"tariff rate out of bounds [0, 1]: {rate}")
    if not 0.0 <= coefficient <= 1.0:
        raise TradePolicyInputError(
            f"tariff dampening coefficient out of bounds [0, 1]: {coefficient}"
        )
    return rate * coefficient


def effective_trade(
    trade: Mapping[str, float],
    tariff_rates: Mapping[str, float],
    *,
    dampening: float,
) -> dict[str, float]:
    """Apply tariff dampening to raw per-node trade values (pure, sorted).

    :param trade: ``{node: raw trade value}`` (non-negative — the U5c
        disjoint-partner-crosswalk volumes).
    :param tariff_rates: ``{node: tariff rate in [0, 1]}`` — the LEGISLATE-
        adjusted START values (``TradePolicyDefines.tariff_rates``, moved
        post-init by PolicySystem's overlay register). A node absent from
        this mapping reads rate ``0.0`` (default-inert law: a node no
        tariff motion was ever enacted against trades at its raw value).
    :param dampening: the tariff-dampening coefficient
        (``TradePolicyDefines.tariff_dampening_coefficient``), applied
        identically to every node.
    :returns: ``{node: trade x (1 - tariff_dampening(rate, dampening))}``,
        sorted by node id (determinism, III.7).
    :raises TradePolicyInputError: a negative trade value, or a rate/
        coefficient outside ``[0, 1]`` (via :func:`tariff_dampening`).
    """
    result: dict[str, float] = {}
    for node in sorted(trade):
        value = trade[node]
        if value < 0.0:
            raise TradePolicyInputError(f"negative trade value for node {node!r}: {value}")
        rate = tariff_rates.get(node, 0.0)
        result[node] = value * (1.0 - tariff_dampening(rate, dampening))
    return result
