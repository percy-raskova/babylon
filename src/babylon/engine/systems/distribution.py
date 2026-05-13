"""Distribution system: Vol III Pt IV-VI surplus split at county scale.

Spec 062 T059 / FR-032 / FR-033. At county scale, surplus value ``s`` is
split into four components:

    s = p + i + r + t

where:
  - ``p`` = retained profit (residual)
  - ``i`` = interest (FRED Fed Funds Rate * county capital stock)
  - ``r`` = rent (BEA REIS county rent series)
  - ``t`` = taxes (effective tax rate × s)

Conservation: ``p + i + r + t`` MUST equal ``s`` exactly per FR-032/FR-033.

For the MVP the split coefficients come from GameDefines fallback constants
(0.05 / 0.10 / 0.30) so unit tests can exercise the conservation property
without the full Postgres-backed reference series in place. When the live
runtime is wired up via the lookup helper, the constants are replaced by
year-scoped ImmutableReferenceLookup queries.

See Also:
    ``specs/062-cross-scale-integration/spec.md`` FR-032/FR-033.
    :mod:`babylon.engine.systems.protocol`: System Protocol.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DistributionSplit:
    """Result of splitting county surplus value into the four components.

    ``p + i + r + t == s`` exactly (FR-032 / FR-033). The split is
    sign-preserving: negative surplus (rare; signals data drift) is not
    distributed and the entire amount is recorded as ``p`` so the
    conservation identity holds.
    """

    s: float
    p: float
    i: float
    r: float
    t: float

    def __post_init__(self) -> None:
        # Hard guarantee of conservation identity. Floating-point sum can
        # introduce relative drift up to ~1e-15 × |s|; the tolerance is
        # scale-aware so large s does not spuriously fail.
        residual = self.p + self.i + self.r + self.t - self.s
        tol = max(1e-9, abs(self.s) * 1e-9)
        if abs(residual) > tol:
            msg = (
                f"DistributionSplit conservation broken: "
                f"p+i+r+t-s={residual:.6e} (tol={tol:.6e}); got "
                f"p={self.p}, i={self.i}, r={self.r}, t={self.t}, s={self.s}"
            )
            raise ValueError(msg)


def split_surplus_to_pirt(
    *,
    s: float,
    interest_rate: float = 0.05,
    rent_rate: float = 0.10,
    tax_rate: float = 0.30,
) -> DistributionSplit:
    """Distribute county-scale ``s`` into ``(p, i, r, t)``.

    Args:
        s: Surplus value at the county scale this tick.
        interest_rate: Fraction of ``s`` paid as interest (FR-032 — derived
            from FRED Fed Funds in production, constant here for testing).
            Must satisfy ``0 <= interest_rate <= 1``.
        rent_rate: Fraction of ``s`` paid as rent (FR-032 — derived from
            BEA REIS in production). Must satisfy ``0 <= rent_rate <= 1``.
        tax_rate: Fraction of ``s`` paid as taxes. Must satisfy
            ``0 <= tax_rate <= 1``.

    Returns:
        DistributionSplit with ``p`` as residual, guaranteeing exact
        conservation per FR-032/FR-033.

    Raises:
        ValueError: If any rate is outside [0, 1] or if the sum of rates
            exceeds 1.0 (which would force negative residual profit).

    Example:
        >>> split = split_surplus_to_pirt(s=100.0, interest_rate=0.1, rent_rate=0.2, tax_rate=0.3)
        >>> split.t == 30.0
        True
        >>> split.r == 20.0
        True
        >>> split.i == 10.0
        True
        >>> split.p == 40.0
        True
    """
    for name, rate in (
        ("interest_rate", interest_rate),
        ("rent_rate", rent_rate),
        ("tax_rate", tax_rate),
    ):
        if not 0.0 <= rate <= 1.0:
            raise ValueError(f"{name} must be in [0, 1]; got {rate!r}")

    sum_rates = interest_rate + rent_rate + tax_rate
    if sum_rates > 1.0:
        raise ValueError(
            f"Sum of i/r/t rates ({sum_rates}) exceeds 1.0; residual profit p would be negative."
        )

    if s < 0:
        # Negative s shouldn't reach this function in normal operation.
        # Defensive path: put everything into p so the identity still holds.
        return DistributionSplit(s=s, p=s, i=0.0, r=0.0, t=0.0)

    i_amount = s * interest_rate
    r_amount = s * rent_rate
    t_amount = s * tax_rate
    p_amount = s - i_amount - r_amount - t_amount
    return DistributionSplit(s=s, p=p_amount, i=i_amount, r=r_amount, t=t_amount)


__all__ = ["split_surplus_to_pirt", "DistributionSplit"]
