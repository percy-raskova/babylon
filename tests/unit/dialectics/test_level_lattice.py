"""Unit tests for :mod:`babylon.domain.dialectics.core.level` — levels and Aufhebung.

Fixture: quantization levels on the integers. Level ``i`` carries the
skeleton "round down to a multiple of m_i" and the sheaf "round up to a
multiple of m_i", with moduli 1 ≺ 2 ≺ 4 ≺ 8 (coarser level = bigger
quantum — quantity organized into quality). Lawvere's resolution
condition ○_j(□_i(x)) == □_i(x) then reads: every i-skeleton is already
j-closed. The answers are hand-computable, which is what a known-answer
suite for the Aufhebung operator needs.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from babylon.domain.dialectics.core.level import Level, LevelLattice, LevelOperators

pytestmark = pytest.mark.math

_MODULI = {0: 1, 1: 2, 2: 4, 3: 8}


def _floor_to(m: int) -> LevelOperators[int]:
    return LevelOperators(
        skeleton=lambda x: (x // m) * m,
        sheaf=lambda x: ((x + m - 1) // m) * m,
    )


def _lattice() -> LevelLattice[int]:
    levels = [Level(index=i, name=f"mod-{m}") for i, m in sorted(_MODULI.items())]
    operators = {i: _floor_to(m) for i, m in _MODULI.items()}
    return LevelLattice(levels=levels, operators=operators, eq=lambda a, b: a == b)


class TestResolution:
    def test_resolved_when_skeleton_is_already_coarse(self) -> None:
        # □_1(8) = 8, and ○_2(8) = 8: the level-1 skeleton of 8 is 2-closed.
        assert _lattice().is_resolved_at(8, lower=1, higher=2)

    def test_unresolved_when_sheaf_moves_the_skeleton(self) -> None:
        # □_1(6) = 6, but ○_2(6) = 8 ≠ 6.
        assert not _lattice().is_resolved_at(6, lower=1, higher=2)

    def test_rejects_non_ascending_pair(self) -> None:
        with pytest.raises(ValueError, match="lower"):
            _lattice().is_resolved_at(8, lower=2, higher=1)

    def test_rejects_unknown_level(self) -> None:
        with pytest.raises(ValueError, match="[Uu]nknown level"):
            _lattice().is_resolved_at(8, lower=0, higher=9)


class TestAufhebung:
    def test_returns_least_resolving_level(self) -> None:
        # Probes are multiples of 8, so already 2-closed AND 1-closed;
        # the Aufhebung of level 0 must be the LEAST such level: 1.
        result = _lattice().aufhebung_of(0, probes=[8, 16, 24])
        assert result is not None
        assert result.index == 1

    def test_skips_levels_that_fail_any_probe(self) -> None:
        # 4 is 2-closed (○_2(4)=4) but not 3-closed (○_3(4)=8):
        # with probes {4, 8} level 2 resolves both, level 1 resolves both,
        # but probe 6 kills level 1 (○_1(6)=6 ok!) — use 5 instead:
        # □_0(5)=5, ○_1(5)=6≠5, ○_2(5)=8≠5, ○_3(5)=8≠5 → nothing resolves.
        assert _lattice().aufhebung_of(0, probes=[5]) is None

    def test_mixed_probes_pick_first_level_resolving_all(self) -> None:
        # 6 is 1-closed but not 2-closed; 8 is closed at every level.
        # Level 1 resolves both probes; level 2 fails probe 6.
        result = _lattice().aufhebung_of(0, probes=[6, 8])
        assert result is not None
        assert result.index == 1

    def test_no_higher_level_returns_none(self) -> None:
        assert _lattice().aufhebung_of(3, probes=[8]) is None

    def test_unknown_lower_level_raises(self) -> None:
        with pytest.raises(ValueError, match="[Uu]nknown level"):
            _lattice().aufhebung_of(42, probes=[8])

    def test_empty_probes_rejected(self) -> None:
        with pytest.raises(ValueError, match="probe"):
            _lattice().aufhebung_of(0, probes=[])


class TestConstruction:
    def test_levels_must_be_strictly_increasing(self) -> None:
        levels = [Level(index=1, name="a"), Level(index=1, name="b")]
        ops = {1: _floor_to(2)}
        with pytest.raises(ValueError, match="strictly increasing"):
            LevelLattice(levels=levels, operators=ops, eq=lambda a, b: a == b)

    def test_operators_must_cover_every_level(self) -> None:
        levels = [Level(index=0, name="a"), Level(index=1, name="b")]
        ops = {0: _floor_to(1)}
        with pytest.raises(ValueError, match="operator"):
            LevelLattice(levels=levels, operators=ops, eq=lambda a, b: a == b)

    def test_empty_lattice_rejected(self) -> None:
        with pytest.raises(ValueError, match="at least one"):
            LevelLattice(levels=[], operators={}, eq=lambda a, b: a == b)

    def test_level_index_must_be_non_negative(self) -> None:
        with pytest.raises(ValidationError):
            Level(index=-1, name="bad")
