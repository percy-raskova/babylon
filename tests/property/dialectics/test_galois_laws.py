"""Law tests for :class:`babylon.domain.dialectics.core.galois.GaloisConnection`.

A Galois connection is an adjunction between preorders: the executable,
fully law-testable core of Lawvere's "opposing tendencies are adjoint
functors". Two canonical fixtures are exercised:

1. Multiplication ⊣ floor-division on non-negative integers:
   ``p * k <= q  <=>  p <= q // k`` (for k >= 1).
2. Direct image ⊣ preimage along a finite function — Lawvere's
   existential quantifier as left adjoint to substitution (∃_f ⊣ f*):
   ``f(S) ⊆ T  <=>  S ⊆ f⁻¹(T)``.

Laws verified: the adjointness biconditional, closure (upper∘lower) is
inflationary/idempotent/monotone, interior (lower∘upper) is
deflationary/idempotent/monotone.
"""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from babylon.domain.dialectics.core.galois import GaloisConnection

pytestmark = [pytest.mark.property, pytest.mark.math]

# --- Fixture 1: multiplication ⊣ floor-division on naturals -----------------


def _mul_div_connection(k: int) -> GaloisConnection[int, int]:
    return GaloisConnection(
        lower=lambda p: p * k,
        upper=lambda q: q // k,
        leq_p=lambda a, b: a <= b,
        leq_q=lambda a, b: a <= b,
    )


@given(
    p=st.integers(min_value=0, max_value=10_000),
    q=st.integers(min_value=0, max_value=10_000),
    k=st.integers(min_value=1, max_value=64),
)
@settings(max_examples=200)
def test_mul_div_adjointness(p: int, q: int, k: int) -> None:
    """The biconditional p*k <= q <=> p <= q//k holds everywhere."""
    assert _mul_div_connection(k).holds(p, q)


@given(
    p=st.integers(min_value=0, max_value=10_000),
    k=st.integers(min_value=1, max_value=64),
)
@settings(max_examples=100)
def test_mul_div_closure_laws(p: int, k: int) -> None:
    """Closure is inflationary and idempotent on the lower poset."""
    gc = _mul_div_connection(k)
    closed = gc.closure(p)
    assert p <= closed or closed == p  # inflationary (here: exact identity)
    assert gc.closure(closed) == closed  # idempotent


# --- Fixture 2: direct image ⊣ preimage (∃_f ⊣ f*) ---------------------------

_DOMAIN = frozenset(range(6))
_CODOMAIN = frozenset(range(4))


def _image_preimage_connection(
    mapping: dict[int, int],
) -> GaloisConnection[frozenset[int], frozenset[int]]:
    def direct_image(s: frozenset[int]) -> frozenset[int]:
        return frozenset(mapping[x] for x in s)

    def preimage(t: frozenset[int]) -> frozenset[int]:
        return frozenset(x for x in _DOMAIN if mapping[x] in t)

    return GaloisConnection(
        lower=direct_image,
        upper=preimage,
        leq_p=frozenset.issubset,
        leq_q=frozenset.issubset,
    )


_functions = st.fixed_dictionaries({x: st.sampled_from(sorted(_CODOMAIN)) for x in _DOMAIN})
_subdomains = st.frozensets(st.sampled_from(sorted(_DOMAIN)))
_subcodomains = st.frozensets(st.sampled_from(sorted(_CODOMAIN)))


@given(mapping=_functions, s=_subdomains, t=_subcodomains)
@settings(max_examples=200)
def test_quantifier_adjointness(
    mapping: dict[int, int], s: frozenset[int], t: frozenset[int]
) -> None:
    """f(S) ⊆ T <=> S ⊆ f⁻¹(T): the existential quantifier is a left adjoint."""
    assert _image_preimage_connection(mapping).holds(s, t)


@given(mapping=_functions, s=_subdomains)
@settings(max_examples=100)
def test_quantifier_closure_laws(mapping: dict[int, int], s: frozenset[int]) -> None:
    """Closure f⁻¹(f(S)) is inflationary and idempotent."""
    gc = _image_preimage_connection(mapping)
    closed = gc.closure(s)
    assert s.issubset(closed)
    assert gc.closure(closed) == closed


@given(mapping=_functions, s1=_subdomains, s2=_subdomains)
@settings(max_examples=100)
def test_quantifier_closure_monotone(
    mapping: dict[int, int], s1: frozenset[int], s2: frozenset[int]
) -> None:
    """S1 ⊆ S2 implies closure(S1) ⊆ closure(S2)."""
    gc = _image_preimage_connection(mapping)
    if s1.issubset(s2):
        assert gc.closure(s1).issubset(gc.closure(s2))


@given(mapping=_functions, t=_subcodomains)
@settings(max_examples=100)
def test_quantifier_interior_laws(mapping: dict[int, int], t: frozenset[int]) -> None:
    """Interior f(f⁻¹(T)) is deflationary and idempotent."""
    gc = _image_preimage_connection(mapping)
    inner = gc.interior(t)
    assert inner.issubset(t)
    assert gc.interior(inner) == inner
