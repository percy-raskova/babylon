r"""The scale adjunction ``allocate ⊣ aggregate`` along the spatial hierarchy.

The spatial hierarchy (hex ≺ county ≺ state ≺ nation) carries two adjoint
motions: **allocate** pushes a parent quantity down to its children by share
(the left adjoint), and **aggregate** sums children back into their parent
(the right adjoint). :class:`ScaleAdjunction` is the GENERIC structure both
concrete kernels instantiate — the industry-rent→county allocator and the
CFS-flow aggregator (``geographic_flow.py``) operate on unrelated domains
today, but they are the same adjunction, and this instance names its laws.

**H3 aggregation is a sheaf (§9.1 earn-its-keep target).** Two conditions,
proven as tests rather than asserted as vocabulary — there is NO cohomology
and NO sheaf class here:

- *Gluing = conservation*: child sections glue to a parent section with no
  leakage — ``Σ children == Σ parents`` (``test_sheaf_gluing_conservation``).
- *Functoriality*: aggregation composes along the hierarchy,
  ``A_{6→5} ∘ A_{7→6} = A_{7→5}`` over real ``h3`` parentage
  (``test_sheaf_functoriality_h3``).

**Extensive vs intensive.** Extensive quantities (c, v, s, k dollars; labor
hours; population) SUM on aggregate — :meth:`aggregate`. Intensive quantities
(rates, ratios, per-capita values) take the share-weighted mean —
:meth:`aggregate_intensive`. Aggregate primitives, recompute derived.

**Naturality squares = the conservation-audit invariant families.**
``persistence/conservation_audit.py`` lines 158-180 name the invariants
``hex_to_county_sum_{c,v,s,k}``, ``county_to_state_sum_{c,v,s,k}`` and
``state_to_national_sum_{c,v,s,k}`` — three square FAMILIES. Each is a
naturality square: aggregating a quantity then reading it at the parent equals
reading it per child then aggregating (which, for extensive sums, is exactly
conservation). ``test_scale.py::TestNaturalitySquares`` gives one parametrized
law test per family over fixture data. Those 21 auditor names are a contract
with no-op evaluators today; **Phase D does NOT wire ``register_invariant``**
— that is spec-062's program. These tests demonstrate the square shape the
auditor will later enforce, not the wiring.

See Also:
    :class:`babylon.economics.tensor_hierarchy.geographic_flow.DefaultGeographicAggregator`:
    the CFS-flow kernel; ``test_scale.py`` proves it agrees with
    :meth:`ScaleAdjunction.aggregate` on a shared fixture (bind, don't rewrite).
"""

from __future__ import annotations

from collections.abc import Mapping

from pydantic import BaseModel, ConfigDict, model_validator

__all__ = ["ScaleAdjunction"]

_SHARE_SUM_TOL = 1e-9
"""Tolerance on the per-parent share sum (float-normalized shares rarely hit 1.0)."""


class ScaleAdjunction(BaseModel):
    """A child→parent partition with per-parent shares: ``allocate ⊣ aggregate``.

    Args:
        mapping: Total function ``child -> parent``; every child has exactly
            one parent.
        shares: ``child -> share of its parent`` in ``[0, 1]``; the shares of
            all children under any one parent must sum to ``1`` (validated).

    Raises:
        ValueError: If ``mapping`` and ``shares`` do not cover the same
            children, if any share is negative, or if any parent's shares do
            not sum to ``1`` (within :data:`_SHARE_SUM_TOL`).

    Example:
        >>> adj = ScaleAdjunction.uniform({"h1": "c1", "h2": "c1"})
        >>> adj.aggregate({"h1": 3.0, "h2": 4.0})["c1"]
        7.0
        >>> adj.aggregate(adj.allocate({"c1": 10.0}))["c1"]
        10.0
    """

    mapping: dict[str, str]
    shares: dict[str, float]

    model_config = ConfigDict(frozen=True)

    @model_validator(mode="after")
    def _validate_partition(self) -> ScaleAdjunction:
        """Enforce alignment, non-negativity, and the per-parent unit-sum law.

        The unit-sum law is what makes ``aggregate∘allocate = id`` hold; the
        §9.1 mutation probe (c) strips this check and the round-trip breaks.
        """
        if set(self.mapping) != set(self.shares):
            raise ValueError("mapping and shares must cover the same children")
        totals: dict[str, float] = {}
        for child, parent in self.mapping.items():
            share = self.shares[child]
            if share < 0.0:
                raise ValueError(f"share for child {child!r} is negative: {share}")
            totals[parent] = totals.get(parent, 0.0) + share
        for parent, total in totals.items():
            if abs(total - 1.0) > _SHARE_SUM_TOL:
                raise ValueError(f"shares under parent {parent!r} sum to {total}, not 1.0")
        return self

    @classmethod
    def uniform(cls, mapping: Mapping[str, str]) -> ScaleAdjunction:
        """Build an adjunction whose siblings split their parent evenly.

        Args:
            mapping: Total function ``child -> parent``.

        Returns:
            A :class:`ScaleAdjunction` with share ``1/n`` for each of a
            parent's ``n`` children.
        """
        counts: dict[str, int] = {}
        for parent in mapping.values():
            counts[parent] = counts.get(parent, 0) + 1
        shares = {child: 1.0 / counts[parent] for child, parent in mapping.items()}
        return cls(mapping=dict(mapping), shares=shares)

    def parents(self) -> tuple[str, ...]:
        """Return the distinct parents, lexicographically ordered for determinism."""
        return tuple(sorted(set(self.mapping.values())))

    def allocate(self, by_parent: Mapping[str, float]) -> dict[str, float]:
        """Push each parent's value down to its children by share (left adjoint).

        Args:
            by_parent: A value per parent.

        Returns:
            ``{child: by_parent[parent] * share}`` for every child.

        Raises:
            KeyError: If a child's parent is absent from ``by_parent`` (the
                logic layer fails loud rather than fabricating a zero).
        """
        return {
            child: by_parent[parent] * self.shares[child] for child, parent in self.mapping.items()
        }

    def aggregate(self, by_child: Mapping[str, float]) -> dict[str, float]:
        """Sum children into their parent (right adjoint; EXTENSIVE quantities).

        Args:
            by_child: A value per child.

        Returns:
            ``{parent: Σ children}`` for every parent.

        Raises:
            KeyError: If any child is absent from ``by_child``.
        """
        result: dict[str, float] = dict.fromkeys(self.parents(), 0.0)
        for child, parent in self.mapping.items():
            result[parent] += by_child[child]
        return result

    def aggregate_intensive(self, by_child: Mapping[str, float]) -> dict[str, float]:
        """Share-weighted mean of children into their parent (INTENSIVE quantities).

        Because a parent's shares sum to 1, ``Σ share·value`` is the
        share-weighted mean — the correct aggregation for rates and ratios,
        which must NOT be summed.

        Args:
            by_child: An intensive value per child.

        Returns:
            ``{parent: Σ share·value}`` for every parent.

        Raises:
            KeyError: If any child is absent from ``by_child``.
        """
        result: dict[str, float] = dict.fromkeys(self.parents(), 0.0)
        for child, parent in self.mapping.items():
            result[parent] += self.shares[child] * by_child[child]
        return result
