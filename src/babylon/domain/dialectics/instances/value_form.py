r"""The value-form adjunction: labor-time ⇄ money, and the imperial-rent defect Φ.

This instance grounds the Lawverian adjunction pattern in Babylon's tested
economics kernels. The **prime directive is reuse** — every arithmetic
quantity here already has a kernel (cited per function); the module adds the
*structure* (a frozen adjunction) and the *laws* (round-trip, conservation,
numeraire invariance), not new economics.

**Two adjoints, one defect.** :class:`ValueFormAdjunction` is the pure
numeraire map ``money = hours · τ`` — an isomorphism with ZERO defect. Φ
(imperial rent) is NOT the conversion error; it is the *counit defect of the
wage form* — the gap between what a wage commands and what the labor it buys
actually produced (:func:`phi_class`, the §6 contract form ``(W_c − V_c)/V_c``;
:func:`phi_hour`, the §9.3 sorting form ``wage_hourly − τ_eff``).

**Re-consumed orphan.** The typed poles reuse the C1.7-orphaned
:mod:`babylon.domain.economics.value` models: :class:`~babylon.domain.economics.value.AbstractLabor`
(pole A, hours) ⇄ :class:`~babylon.domain.economics.value.ExchangeValue` (pole B,
dollars). Before this module those models had no non-dormant consumer; the
adjunction re-consumes them as its genuine pole types.

**Φ tri-decomposition (§9.3).** :class:`PhiDecomposition` carries three
*separately measured* defects whose SUM is Φ — never a stored scalar:

- ``phi_unequal_exchange`` (Emmanuel/Amin) — kernel
  :meth:`~babylon.domain.economics.gamma.shadow_subsidy.DefaultShadowSubsidyCalculator.compute_phi_imperial`
  (``(1 − γ_basket)·Consumption``);
- ``phi_reproduction`` (Meillassoux) — kernel
  :func:`babylon.formulas.lifecycle.compute_shadow_subsidy` (the honest
  computable proxy: next-generation labor-power value minus rearing wages;
  Meillassoux externalized reproduction has no dedicated kernel);
- ``phi_domestic`` (Fortunati) — ``τ · L_unpaid``, computed directly here.

**D2 kernel-fork resolution (recorded per the design's D2 instruction).**
:meth:`~babylon.domain.economics.gamma.shadow_subsidy.DefaultShadowSubsidyCalculator.compute_phi_iii`
(``shadow_subsidy.py`` lines 116, 128-129) computes
``phi_labor_hours = (1 − γ_III)·L_unpaid`` and then ``· τ`` — i.e. it returns
``(1 − γ_III)·L_unpaid·τ``, which is **quadratic** in ``L_unpaid`` (since
``1 − γ_III = L_unpaid/L_total``). That is the narrower *invisible-fraction*
quantity, NOT the value of all unpaid care. Therefore Φ_domestic is computed
here as ``τ · L_unpaid`` (:func:`phi_domestic`, the conservation term) and the
kernel's Φ_III is carried separately as :func:`phi_iii_report`
(``PhiDecomposition.phi_iii_report``), explicitly **excluded** from the
conservation total.

**γ's three mechanisms are non-interchangeable (§9.3).** ``γ_basket`` (the
harmonic mean ``1/(α/γ_import + (1−α))``, ``basket_visibility.py`` — the
contract's "τa/τb" is a gloss) is international unequal exchange;
``γ_III = L_paid/(L_paid+L_unpaid)`` is reproductive visibility; and π
(throughput ``= τ_through/τ_national``, ``economics/throughput/calculator.py``)
is a POSITION metric, **not** a visibility mechanism — it never enters τ_eff or
any Φ component here (pinned by ``test_value_form.py::TestPiIsNotVisibility``).

**Two decoupled class axes.** :func:`class_position_by_phi_hour` sorts by the
FLOW defect Φ_hour. This is deliberately distinct from the canonical
STOCK axis (wealth-percentile) in
:class:`babylon.domain.economics.melt.class_position` (``melt/types.py`` lines 9-18):
a proletarian can have Φ_hour > 0 (cheap imports) yet hold no wealth. Do NOT
conflate them — this function does not touch the wealth-percentile classifier.

**Name-collision fence.** ``economics/tick/system/imperial_rent.py`` also
defines a ``phi_hour``, but that is a DIFFERENT quantity — per-county
production-chain rent per hour via the Leontief pipeline
(``CountyEconomicState.phi_hour``). The :func:`phi_hour` here is the *wage
defect* ``wage_hourly − τ_eff``. They are unrelated; do not conflate.

**Fortunati duplication flag (D0).** ``economics/shadow_labor.py`` is a
config-lens Fortunati duplicate of the data-driven ``economics/gamma/``
package. The gamma package is the kernel of record used here; reconciling the
duplicate is out of scope for Phase D (flag only).

**Transformation problem deferred (D6).** The four dormant spec-060 "arm"
integration tests (``test_aggregate_equalities.py`` etc.) stay gated: they
await a transformation-weight instance (Volume III equalization of the rate of
profit), which is NOT Phase D. The value form here is Volume I (value ⇄
price-of-labor-power); prices of production land in a later phase.

See Also:
    :mod:`babylon.domain.dialectics.instances.catalog`: rebinds the ``wage`` and
    ``imperial`` opposition measures onto this defect (Phase D5).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, computed_field

from babylon.domain.economics.gamma.shadow_subsidy import DefaultShadowSubsidyCalculator
from babylon.domain.economics.gamma.types import GammaBasket, GammaIII
from babylon.domain.economics.melt.types import ClassPosition
from babylon.domain.economics.value import AbstractLabor, ExchangeValue
from babylon.formulas.lifecycle import compute_shadow_subsidy

__all__ = [
    "PhiDecomposition",
    "ValueFormAdjunction",
    "class_position_by_phi_hour",
    "phi_class",
    "phi_domestic",
    "phi_hour",
    "phi_iii_report",
    "phi_reproduction",
    "phi_unequal_exchange",
    "visible_value",
]


class ValueFormAdjunction(BaseModel):
    """The labor-time ⇄ money numeraire map ``money = hours · τ``.

    A pure isomorphism with **zero defect**: it is the categorical unit/counit
    of the value form, not the site of exploitation. ``τ`` (MELT) and
    ``γ_basket`` are supplied by the caller's injected
    :class:`~babylon.domain.economics.melt.melt_calculator.MELTCalculator` and
    :class:`~babylon.domain.economics.melt.basket_visibility.BasketVisibilityCalculator`
    (dependency injection — this model stores plain floats and never hardwires
    a ``Default*`` calculator).

    Attributes:
        tau: MELT (Monetary Expression of Labor Time) in dollars per
            labor-hour; strictly positive.
        gamma_basket: Basket-visibility coefficient in ``(0, 1]``.

    Example:
        >>> adj = ValueFormAdjunction(tau=65.0, gamma_basket=0.68)
        >>> adj.to_money(adj.to_labor_hours(100.0))
        100.0
        >>> adj.tau_effective
        44.2
    """

    tau: float = Field(..., gt=0.0, description="MELT τ in $/labor-hour")
    gamma_basket: float = Field(..., gt=0.0, le=1.0, description="Basket visibility (0, 1]")

    model_config = ConfigDict(frozen=True, extra="forbid")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def tau_effective(self) -> float:
        """Effective MELT ``τ · γ_basket`` — the ``NationalParameters`` semantics.

        Matches ``parameters.py`` line 232 (``expected_tau_effective =
        tau * gamma_basket``): the imperial-subsidy-adjusted dollars per hour
        that the labor-aristocracy wage threshold is measured against.
        """
        return self.tau * self.gamma_basket

    def to_labor_hours(self, dollars: float) -> float:
        """Money → labor-time: ``dollars / τ`` (the counit / right adjoint).

        Args:
            dollars: A money quantity.

        Returns:
            The equivalent abstract labor-hours.
        """
        return dollars / self.tau

    def to_money(self, hours: float) -> float:
        """Labor-time → money: ``hours · τ`` (the unit / left adjoint).

        Args:
            hours: A quantity of abstract labor-hours.

        Returns:
            The equivalent money quantity.
        """
        return hours * self.tau

    def value_of(self, labor: AbstractLabor) -> ExchangeValue:
        """Money-form of abstract labor: ``price = snlt · τ``.

        Args:
            labor: Abstract labor (pole A), carrying socially-necessary
                labor-time (``snlt``, hours).

        Returns:
            The commodity's exchange-value (pole B) at price ``snlt · τ``.
        """
        return ExchangeValue(price=self.to_money(labor.snlt), snlt=labor.snlt)

    def labor_of(self, value: ExchangeValue) -> AbstractLabor:
        """Labor-form of exchange-value: ``snlt = price / τ``.

        Args:
            value: A commodity's exchange-value (pole B), carrying a price.

        Returns:
            The abstract labor (pole A) the price commands, ``price / τ``.
        """
        return AbstractLabor(snlt=self.to_labor_hours(value.price))


def phi_class(w_c: float, v_c: float) -> float:
    """The wage-form counit defect per class: ``(W_c − V_c) / V_c``.

    The §6 contract form of imperial rent — signed and dimensionless. Positive
    means the wage commands more value than the class produced (the imperial
    bribe / Fundamental Theorem ``W_c > V_c``); negative means super-exploited.

    Args:
        w_c: Wage commanded by the class (value the wage can buy).
        v_c: Value the class actually produced; must be strictly positive.

    Returns:
        The signed relative defect ``(W_c − V_c) / V_c``.

    Raises:
        ValueError: If ``v_c <= 0`` (the logic layer fails loud — a class that
            produced nothing has no defined rate of imperial rent).

    Example:
        >>> phi_class(w_c=100.0, v_c=80.0)
        0.25
    """
    if v_c <= 0.0:
        raise ValueError(f"v_c must be > 0 to define Φ_class, got {v_c}")
    return (w_c - v_c) / v_c


def phi_hour(wage_hourly: float, tau_effective: float) -> float:
    """The wage-form counit defect per hour: ``wage_hourly − τ_eff``.

    The §9.3 sorting form (dollars/hour). ``τ_eff = τ · γ_basket`` is the
    imperial-subsidy-adjusted value produced per hour; a wage above it is the
    labor-aristocracy bribe. (Distinct from the identically-named production
    -chain quantity in ``economics/tick/system/imperial_rent.py`` — see the
    module docstring's name-collision fence.)

    Args:
        wage_hourly: The hourly wage in dollars.
        tau_effective: Effective MELT in dollars/hour (``τ · γ_basket``).

    Returns:
        The signed hourly defect ``wage_hourly − τ_eff``.

    Example:
        >>> phi_hour(wage_hourly=50.0, tau_effective=44.2)
        5.8
    """
    return wage_hourly - tau_effective


def class_position_by_phi_hour(
    wage_hourly: float,
    tau_effective: float,
    v_reproduction: float,
) -> ClassPosition:
    """Sort a class on the FLOW axis by its hourly imperial-rent defect (§9.3).

    - ``Φ_hour ≥ 0`` → :attr:`~babylon.domain.economics.melt.types.ClassPosition.LABOR_ARISTOCRACY`
      (the wage exceeds value produced — pacified by the imperial bribe);
    - ``Φ_hour < 0 ∧ W ≥ V_repro`` →
      :attr:`~babylon.domain.economics.melt.types.ClassPosition.PROLETARIAT`
      (super-exploited but above the reproduction floor);
    - ``W < V_repro`` →
      :attr:`~babylon.domain.economics.melt.types.ClassPosition.LUMPENPROLETARIAT`
      (below reproduction; a.k.a. ``SUBPROLETARIAT``, ``melt/types.py`` line 230).

    This is the FLOW axis (extraction rate), deliberately decoupled from the
    canonical STOCK axis (wealth percentile) in
    :class:`babylon.domain.economics.melt.class_position` — the two are separate
    concerns (``melt/types.py`` lines 9-18) and this function does NOT touch the
    wealth-percentile classifier.

    Args:
        wage_hourly: The class's hourly wage in dollars.
        tau_effective: Effective MELT in dollars/hour (``τ · γ_basket``).
        v_reproduction: The reproduction / subsistence floor in dollars/hour.

    Returns:
        The :class:`~babylon.domain.economics.melt.types.ClassPosition` on the flow axis.
    """
    if phi_hour(wage_hourly, tau_effective) >= 0.0:
        return ClassPosition.LABOR_ARISTOCRACY
    if wage_hourly >= v_reproduction:
        return ClassPosition.PROLETARIAT
    return ClassPosition.LUMPENPROLETARIAT


def visible_value(tau: float, l_paid: float) -> float:
    """Value visible to the price system: ``τ · L_paid`` (the conservation V_visible).

    Args:
        tau: MELT in dollars per labor-hour.
        l_paid: Paid (commodified) labor-hours.

    Returns:
        ``τ · L_paid`` in dollars.
    """
    return tau * l_paid


def phi_domestic(tau: float, l_unpaid: float) -> float:
    """Fortunati domestic shadow labor: ``τ · L_unpaid`` (the conservation term).

    The value of ALL unpaid care hours. This — not the narrower
    :func:`phi_iii_report` quantity — is the conservation-identity shadow term
    (see the module docstring's D2 kernel-fork resolution).

    Args:
        tau: MELT in dollars per labor-hour.
        l_unpaid: Unpaid (invisible) labor-hours.

    Returns:
        ``τ · L_unpaid`` in dollars.
    """
    return tau * l_unpaid


def phi_unequal_exchange(gamma_basket: GammaBasket, consumption: float) -> float:
    """Emmanuel/Amin unequal exchange: ``(1 − γ_basket) · Consumption``.

    Reuses
    :meth:`~babylon.domain.economics.gamma.shadow_subsidy.DefaultShadowSubsidyCalculator.compute_phi_imperial`
    verbatim (``gamma/shadow_subsidy.py``). The flow-level derivation in
    ``formulas/unequal_exchange`` (``exchange_ratio`` → ``value_transfer``) is
    the cross-check: both must agree in sign and order of magnitude.

    Args:
        gamma_basket: The basket-visibility result (only its ``gamma_basket``
            field is consumed by the kernel).
        consumption: Total consumption in dollars.

    Returns:
        Φ_unequal_exchange in dollars.
    """
    return DefaultShadowSubsidyCalculator().compute_phi_imperial(gamma_basket, consumption)


def phi_reproduction(*, p_g2_labor_value: float, wage_paid_for_d_g2: float) -> float:
    """Meillassoux externalized reproduction (honest proxy, per D0).

    Meillassoux's externalized reproduction has no dedicated kernel; the
    computable proxy is
    :func:`babylon.formulas.lifecycle.compute_shadow_subsidy` — the
    intergenerational shadow subsidy ``max(0, P_g2 − wage)``: the value of
    next-generation labor-power minus the wages paid for its rearing.

    Args:
        p_g2_labor_value: Value of next-generation labor-power produced.
        wage_paid_for_d_g2: Wages advanced for child-rearing (the D phase).

    Returns:
        Φ_reproduction in dollars (always ``>= 0``).
    """
    return compute_shadow_subsidy(
        p_g2_labor_value=p_g2_labor_value,
        wage_paid_for_d_g2=wage_paid_for_d_g2,
    )


def phi_iii_report(gamma_iii: GammaIII, tau: float) -> float:
    """The kernel's narrower Φ_III: ``(1 − γ_III) · L_unpaid · τ`` (report only).

    Reuses
    :meth:`~babylon.domain.economics.gamma.shadow_subsidy.DefaultShadowSubsidyCalculator.compute_phi_iii`
    (called with ``melt=None`` to obtain its ``phi_iii_labor_hours =
    (1 − γ_III)·L_unpaid``, then scaled by ``τ`` in the instance's own units,
    avoiding the kernel's billions/1e9 assumption).

    This is the *invisible-fraction* quantity — quadratic in ``L_unpaid`` since
    ``1 − γ_III = L_unpaid/L_total`` — and is therefore STRICTLY SMALLER than
    :func:`phi_domestic` (``τ · L_unpaid``) whenever ``0 < γ_III < 1``. It is
    carried for reporting and is **NOT** the conservation term (D2 fork).

    Args:
        gamma_iii: The reproductive-visibility result (year, care hours, γ_III).
        tau: MELT in dollars per labor-hour.

    Returns:
        ``(1 − γ_III) · L_unpaid · τ`` in dollars — a report field, not
        conserved.
    """
    subsidy = DefaultShadowSubsidyCalculator().compute_phi_iii(gamma_iii, melt=None)
    return subsidy.phi_iii_labor_hours * tau


class PhiDecomposition(BaseModel):
    """Imperial rent Φ as the SUM of three separately-measured defects (§9.3).

    "A single scalar weight cannot carry Φ's three components." The total is a
    :func:`~pydantic.computed_field` over the three conservation components and
    is NEVER a stored primitive — a stored scalar could silently drift from its
    parts.

    Attributes:
        phi_unequal_exchange: Emmanuel/Amin international transfer.
        phi_reproduction: Meillassoux externalized reproduction (proxy).
        phi_domestic: Fortunati domestic shadow labor ``τ · L_unpaid``.
        phi_iii_report: The kernel's narrower ``(1 − γ_III)·L_unpaid·τ``
            invisible-fraction quantity (:func:`phi_iii_report`) — informational
            only, **excluded** from :attr:`total` (D2 fork).

    Example:
        >>> PhiDecomposition(
        ...     phi_unequal_exchange=3.0, phi_reproduction=5.0, phi_domestic=7.0
        ... ).total
        15.0
    """

    phi_unequal_exchange: float = Field(..., description="Emmanuel/Amin international transfer ($)")
    phi_reproduction: float = Field(..., description="Meillassoux externalized reproduction ($)")
    phi_domestic: float = Field(..., description="Fortunati domestic shadow labor τ·L_unpaid ($)")
    phi_iii_report: float = Field(
        default=0.0,
        description="Kernel's narrower Φ_III (report only; NOT in total)",
    )

    model_config = ConfigDict(frozen=True, extra="forbid")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total(self) -> float:
        """Φ = the SUM of the three conservation components (never stored).

        Excludes :attr:`phi_iii_report`, which is the narrower kernel quantity
        carried for reporting rather than conservation (D2 fork).
        """
        return self.phi_unequal_exchange + self.phi_reproduction + self.phi_domestic
