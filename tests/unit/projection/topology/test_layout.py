"""Contract tests for :mod:`babylon.projection.topology.layout` (M4 §1, Task 30).

Pure-function tests, no engine/graph/database — mirrors the sibling
``test_paoh.py``/``test_incidence.py``/``test_levi.py`` convention (no
``pytestmark`` — these modules are auto-collected under ``tests/unit``).
"""

from __future__ import annotations

import math

import pytest

from babylon.projection.topology.layout import bipartite_shell_layout


class TestEmptyRings:
    def test_both_empty_returns_empty_dict(self) -> None:
        assert bipartite_shell_layout([], []) == {}

    def test_only_members_empty(self) -> None:
        layout = bipartite_shell_layout([], ["settler"])
        assert layout == {"settler": pytest.approx((0.45, 0.0))}

    def test_only_communities_empty(self) -> None:
        layout = bipartite_shell_layout(["C001"], [])
        assert layout == {"C001": pytest.approx((1.0, 0.0))}


class TestMemberRingUnitRadius:
    """Members sit on the OUTER unit-radius circle (contract §1)."""

    def test_single_member_sits_at_angle_zero(self) -> None:
        layout = bipartite_shell_layout(["C001"], [])
        x, y = layout["C001"]
        assert x == pytest.approx(1.0)
        assert y == pytest.approx(0.0)

    def test_two_members_are_antipodal_on_the_unit_circle(self) -> None:
        layout = bipartite_shell_layout(["C001", "C002"], [])
        x0, y0 = layout["C001"]
        x1, y1 = layout["C002"]
        assert (x0, y0) == pytest.approx((1.0, 0.0))
        assert (x1, y1) == pytest.approx((-1.0, 0.0), abs=1e-9)

    def test_four_members_sit_at_the_cardinal_points_in_sorted_order(self) -> None:
        # Lexicographic order: A, B, C, D -> angles 0, 90, 180, 270 degrees.
        layout = bipartite_shell_layout(["D", "B", "A", "C"], [])
        assert layout["A"] == pytest.approx((1.0, 0.0), abs=1e-9)
        assert layout["B"] == pytest.approx((0.0, 1.0), abs=1e-9)
        assert layout["C"] == pytest.approx((-1.0, 0.0), abs=1e-9)
        assert layout["D"] == pytest.approx((0.0, -1.0), abs=1e-9)

    def test_every_member_position_lies_on_the_unit_circle(self) -> None:
        layout = bipartite_shell_layout(["C001", "C002", "C003", "C004", "C005"], [])
        for x, y in layout.values():
            assert math.hypot(x, y) == pytest.approx(1.0)


class TestCommunityRingRadius045:
    """Communities sit on the INNER radius-0.45 circle (contract §1)."""

    def test_single_community_sits_at_angle_zero_radius_045(self) -> None:
        layout = bipartite_shell_layout([], ["settler"])
        x, y = layout["settler"]
        assert x == pytest.approx(0.45)
        assert y == pytest.approx(0.0)

    def test_every_community_position_lies_on_the_045_circle(self) -> None:
        layout = bipartite_shell_layout([], ["settler", "women", "trans", "queer"])
        for x, y in layout.values():
            assert math.hypot(x, y) == pytest.approx(0.45)


class TestBothRingsTogether:
    def test_layout_contains_both_member_and_community_ids(self) -> None:
        layout = bipartite_shell_layout(["C001", "C002"], ["settler", "women"])
        assert set(layout) == {"C001", "C002", "settler", "women"}

    def test_member_and_community_rings_are_independent(self) -> None:
        # Adding a community must not perturb the member ring's own angles.
        members_only = bipartite_shell_layout(["C001", "C002"], [])
        both = bipartite_shell_layout(["C001", "C002"], ["settler"])
        assert both["C001"] == pytest.approx(members_only["C001"])
        assert both["C002"] == pytest.approx(members_only["C002"])


class TestDeterminismAndOrderIndependence:
    def test_input_order_does_not_affect_the_result(self) -> None:
        first = bipartite_shell_layout(["C003", "C001", "C002"], ["women", "settler"])
        second = bipartite_shell_layout(["C001", "C002", "C003"], ["settler", "women"])
        assert first == pytest.approx(second)

    def test_duplicate_ids_are_deduplicated_before_laying_out(self) -> None:
        with_dupes = bipartite_shell_layout(["C001", "C001", "C002"], [])
        without_dupes = bipartite_shell_layout(["C001", "C002"], [])
        assert with_dupes == pytest.approx(without_dupes)

    def test_repeated_calls_are_byte_stable(self) -> None:
        first = bipartite_shell_layout(["C001", "C002", "C003"], ["settler", "women", "trans"])
        second = bipartite_shell_layout(["C001", "C002", "C003"], ["settler", "women", "trans"])
        assert first == second


class TestOverlapIsAnError:
    def test_id_in_both_rings_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="C001"):
            bipartite_shell_layout(["C001", "C002"], ["C001"])
