"""σ-gradient Φ attribution — the ruled Option C share math (P26 U5d).

Pure functions, no I/O — the persistence layer supplies the inputs
(anchored σ gaps from the σ-index artifact + Ricci world sample, disjoint
partner trade volumes from ``fact_bilateral_trade_annual``, tiers from the
Ricci ``region_type`` partition) and consumes the ``{node: share}`` map at
session-init time. Nothing here runs in-tick (the determinism red line:
``u4-phi-attribution-options.md`` §7).

The treatment rule (``u5a-core-bloc-theory.md``, ADR165 Q1/Q2):

- **CORE** blocs source zero Φ — Amin (no first-order core→core wage
  differential), Wallerstein (the core is accumulation's terminus), MIM
  (the whole first-world increment is Third World surplus), and the Ricci
  data itself (zero CORE OUTFLOW rows in all 51) converge.
- **SEMI_PERIPHERY** blocs carry a damped weight ``w_semi`` — derived from
  the Ricci sample's own OUTFLOW intensities via :func:`derive_w_semi`
  (the delegated-decision analog of ADR165 D1), never an invented
  constant.
- **PERIPHERY** blocs carry the ruled undamped form
  ``max(0, σ_US − σ_i)^p × trade_i`` (program-10 §3's "value transfer
  up-gradient" coupling).

Shares renormalize to Σ = 1.0 — conservation (spec-101 D3) is preserved by
construction; a world with zero attributable mass raises
:class:`AttributionInputError` instead of fabricating a map
(Constitution III.11).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

__all__ = [
    "AttributionInputError",
    "TIER_CORE",
    "TIER_PERIPHERY",
    "TIER_SEMI_PERIPHERY",
    "compute_bloc_shares",
    "derive_w_semi",
    "nearest_vintage",
]

TIER_CORE = "CORE"
TIER_SEMI_PERIPHERY = "SEMI_PERIPHERY"
TIER_PERIPHERY = "PERIPHERY"

_KNOWN_TIERS = frozenset({TIER_CORE, TIER_SEMI_PERIPHERY, TIER_PERIPHERY})


class AttributionInputError(ValueError):
    """The attribution inputs are contradictory or empty — fail loud."""


def compute_bloc_shares(
    *,
    tiers: Mapping[str, str],
    sigma_gap: Mapping[str, float],
    trade: Mapping[str, float],
    w_semi: float,
    gap_exponent: float = 1.0,
) -> dict[str, float]:
    """Fold tiers × σ-gaps × trade volumes into normalized Φ shares.

    :param tiers: ``{node: TIER_*}`` — the Ricci ``region_type`` partition
        mapped onto the engine nodes.
    :param sigma_gap: ``{node: max(0, σ_US − σ_i)}`` — the anchored
        down-gradient distance (already clamped upstream; a residual
        negative is clamped again here defensively).
    :param trade: ``{node: disjoint partner trade volume}`` (USD millions,
        the U5c partner sets — never the containing blocs).
    :param w_semi: SEMI_PERIPHERY damping in ``[0, 1]``
        (:func:`derive_w_semi`).
    :param gap_exponent: the declared ``p`` (default 1.0 — linear gap).
    :returns: ``{node: share}`` over the same keys, sorted, Σ = 1.0.
    :raises AttributionInputError: key mismatch, unknown tier, or zero
        total attributable mass.
    """
    keys = set(tiers)
    if keys != set(sigma_gap) or keys != set(trade):
        raise AttributionInputError(
            "tiers/sigma_gap/trade must cover the same node set: "
            f"tiers={sorted(tiers)}, sigma_gap={sorted(sigma_gap)}, trade={sorted(trade)}"
        )
    unknown = {node: tier for node, tier in tiers.items() if tier not in _KNOWN_TIERS}
    if unknown:
        raise AttributionInputError(f"unknown world-system tier(s): {unknown}")

    tier_weight = {TIER_CORE: 0.0, TIER_SEMI_PERIPHERY: w_semi, TIER_PERIPHERY: 1.0}
    raw: dict[str, float] = {}
    for node in sorted(keys):
        gap = max(0.0, sigma_gap[node])
        raw[node] = tier_weight[tiers[node]] * (gap**gap_exponent) * trade[node]

    total = sum(raw.values())
    if total <= 0.0:
        raise AttributionInputError(
            "zero total attributable mass — every bloc is CORE-tier, gapless, "
            "or trade-less; refusing to fabricate an attribution map"
        )
    return {node: mass / total for node, mass in raw.items()}


def derive_w_semi(
    *,
    semi_outflow_pct_gdp: Sequence[float],
    periphery_outflow_pct_gdp: Sequence[float],
) -> float:
    """Derive the SEMI_PERIPHERY damping from the Ricci sample itself.

    ``w_semi = mean(semi OUTFLOW %GDP) / mean(periphery OUTFLOW %GDP)``,
    clamped to ``[0, 1]`` — semi-peripheries drain in proportion to how
    intensely the data says they actually drain, relative to the
    periphery benchmark. Data-derived, never an invented coefficient
    (the ADR165 D1 delegation pattern).

    :raises AttributionInputError: an empty sample on either side.
    """
    if not semi_outflow_pct_gdp or not periphery_outflow_pct_gdp:
        raise AttributionInputError(
            "w_semi derivation needs non-empty OUTFLOW samples for both tiers"
        )
    semi_mean = sum(semi_outflow_pct_gdp) / len(semi_outflow_pct_gdp)
    periphery_mean = sum(periphery_outflow_pct_gdp) / len(periphery_outflow_pct_gdp)
    if periphery_mean <= 0.0:
        raise AttributionInputError(
            f"periphery OUTFLOW mean must be positive, got {periphery_mean}"
        )
    return min(1.0, max(0.0, semi_mean / periphery_mean))


def nearest_vintage(year: int, vintages: tuple[int, ...]) -> int:
    """Deterministic vintage rule: latest vintage ≤ ``year``, else earliest.

    :raises AttributionInputError: no vintages at all.
    """
    if not vintages:
        raise AttributionInputError("no vintages available")
    at_or_before = [v for v in vintages if v <= year]
    if at_or_before:
        return max(at_or_before)
    return min(vintages)
