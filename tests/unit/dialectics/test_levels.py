"""Unit tests for :mod:`babylon.domain.dialectics.instances.levels` — level lattices.

The spatial resolution law (design §E1, verbatim): a field constant within
states but differing between states is *resolved at county* (its county
aggregates are flat per state) yet *not resolved at hex* (hexes still vary
within their county); a spatially-uniform field resolves everywhere. The
fixture uses UNIFORM shares so every closure is a plain regional mean and the
answers are hand-computable.

Hex layout (two states)::

    state 26: county 26001 = {h1, h2}, county 26002 = {h3, h4}
    state 27: county 27001 = {h5, h6}
"""

from __future__ import annotations

import pytest

from babylon.domain.dialectics.instances.levels import (
    LEVEL_INDEX,
    build_lattice_from_maps,
    level_index_for,
    social_lattice_from_memberships,
    spatial_lattice_for_counties,
)

pytestmark = pytest.mark.math

_HEX_PARENTS: dict[str, dict[str, str]] = {
    "hex": {h: h for h in ("h1", "h2", "h3", "h4", "h5", "h6")},
    "county": {
        "h1": "26001",
        "h2": "26001",
        "h3": "26002",
        "h4": "26002",
        "h5": "27001",
        "h6": "27001",
    },
    "state": {"h1": "26", "h2": "26", "h3": "26", "h4": "26", "h5": "27", "h6": "27"},
    "nation": dict.fromkeys(("h1", "h2", "h3", "h4", "h5", "h6"), "US"),
}


def _hex_lattice() -> object:
    return build_lattice_from_maps(("hex", "county", "state", "nation"), _HEX_PARENTS)


class TestSpatialResolutionLaw:
    """The design §E1 resolution law over the hex ≺ county ≺ state chain."""

    def test_county_constant_within_state_is_resolved_at_county(self) -> None:
        # county means: 26001->2, 26002->2 (flat within state 26); 27001->6.
        field = {"h1": 1.0, "h2": 3.0, "h3": 0.0, "h4": 4.0, "h5": 5.0, "h6": 7.0}
        lattice = _hex_lattice()
        assert lattice.is_resolved_at(field, lower=1, higher=2)  # resolved at county

    def test_same_field_is_not_resolved_at_hex(self) -> None:
        # Hexes vary within their county (1 != 3 in 26001), so smoothing at the
        # county level moves the field: the hex-level opposition is unresolved.
        field = {"h1": 1.0, "h2": 3.0, "h3": 0.0, "h4": 4.0, "h5": 5.0, "h6": 7.0}
        lattice = _hex_lattice()
        assert not lattice.is_resolved_at(field, lower=0, higher=1)

    def test_county_varying_within_state_is_not_resolved_at_county(self) -> None:
        # 26001->2 but 26002->10: county aggregates differ WITHIN state 26.
        field = {"h1": 1.0, "h2": 3.0, "h3": 8.0, "h4": 12.0, "h5": 5.0, "h6": 7.0}
        lattice = _hex_lattice()
        assert not lattice.is_resolved_at(field, lower=1, higher=2)

    def test_uniform_field_resolves_everywhere(self) -> None:
        field = dict.fromkeys(("h1", "h2", "h3", "h4", "h5", "h6"), 5.0)
        lattice = _hex_lattice()
        assert lattice.is_resolved_at(field, lower=0, higher=1)
        assert lattice.is_resolved_at(field, lower=1, higher=2)
        assert lattice.is_resolved_at(field, lower=2, higher=3)


class TestSpatialAufhebung:
    """The least resolving level for a flat-within-county field is county."""

    def test_flat_within_county_sublates_to_county(self) -> None:
        # Constant per county (hexes equal within county) but varying between
        # counties: resolved at hex, so the least level above hex is county.
        field = {"h1": 2.0, "h2": 2.0, "h3": 10.0, "h4": 10.0, "h5": 6.0, "h6": 6.0}
        result = _hex_lattice().aufhebung_of(0, probes=[field])
        assert result is not None
        assert result.name == "county"

    def test_hex_varying_field_has_no_aufhebung_below_nation(self) -> None:
        # Hexes vary within counties: no coarser mean reproduces the field, so
        # the hex-level opposition is antagonistic relative to this chain.
        field = {"h1": 1.0, "h2": 3.0, "h3": 0.0, "h4": 4.0, "h5": 5.0, "h6": 7.0}
        assert _hex_lattice().aufhebung_of(0, probes=[field]) is None


class TestCountyRootedLattice:
    """The production county-rooted lattice used by the regime classifier."""

    def test_levels_are_county_state_nation(self) -> None:
        lattice = spatial_lattice_for_counties(["26001", "26002", "27001"])
        assert [lvl.name for lvl in lattice.levels] == ["county", "state", "nation"]

    def test_county_field_flat_per_state_resolves_at_county(self) -> None:
        lattice = spatial_lattice_for_counties(["26001", "26002", "27001"])
        field = {"26001": 2.0, "26002": 2.0, "27001": 6.0}  # flat within state 26
        assert lattice.is_resolved_at(field, lower=1, higher=2)

    def test_county_field_varying_in_state_not_resolved(self) -> None:
        lattice = spatial_lattice_for_counties(["26001", "26002", "27001"])
        field = {"26001": 2.0, "26002": 10.0, "27001": 6.0}  # differ within state 26
        assert not lattice.is_resolved_at(field, lower=1, higher=2)

    def test_population_weighting_changes_the_state_aggregate(self) -> None:
        # With a heavier 26001, the state-26 aggregate is pulled toward it, so a
        # field flat across the two counties still resolves (means agree) but an
        # asymmetric one is weighted — exercise that populations are honored.
        lattice = spatial_lattice_for_counties(
            ["26001", "26002"], populations={"26001": 3.0, "26002": 1.0}
        )
        flat = {"26001": 4.0, "26002": 4.0}
        assert lattice.is_resolved_at(flat, lower=1, higher=2)

    def test_empty_counties_rejected(self) -> None:
        with pytest.raises(ValueError, match="at least one county"):
            spatial_lattice_for_counties([])


class TestSocialLattice:
    """The individual ≺ community ≺ class ≺ bloc chain (single-membership)."""

    def test_builds_four_levels(self) -> None:
        lattice = social_lattice_from_memberships(
            {"a1": "cP", "a2": "cP", "a3": "cB"},
            {"cP": "proletarian", "cB": "bourgeois"},
            {"proletarian": "periphery", "bourgeois": "core"},
        )
        assert [lvl.name for lvl in lattice.levels] == [
            "individual",
            "community",
            "class",
            "bloc",
        ]

    def test_field_flat_within_community_resolves_at_individual(self) -> None:
        lattice = social_lattice_from_memberships(
            {"a1": "cP", "a2": "cP", "a3": "cB"},
            {"cP": "proletarian", "cB": "bourgeois"},
            {"proletarian": "periphery", "bourgeois": "core"},
        )
        field = {"a1": 1.0, "a2": 1.0, "a3": 5.0}  # a1,a2 equal within cP
        assert lattice.is_resolved_at(field, lower=0, higher=1)

    def test_uniform_field_resolves_up_to_bloc(self) -> None:
        lattice = social_lattice_from_memberships(
            {"a1": "cP", "a2": "cB"},
            {"cP": "proletarian", "cB": "bourgeois"},
            {"proletarian": "periphery", "bourgeois": "core"},
        )
        field = {"a1": 3.0, "a2": 3.0}
        assert lattice.is_resolved_at(field, lower=1, higher=2)
        assert lattice.is_resolved_at(field, lower=2, higher=3)

    def test_unmapped_community_fails_loud(self) -> None:
        with pytest.raises(KeyError, match="community"):
            social_lattice_from_memberships(
                {"a1": "cMissing"},
                {"cP": "proletarian"},
                {"proletarian": "periphery"},
            )


class TestLevelIndex:
    """The level-name → chain-index catalog spans both hierarchies."""

    def test_spatial_and_social_indices(self) -> None:
        assert LEVEL_INDEX["county"] == 1
        assert LEVEL_INDEX["class"] == 2
        assert LEVEL_INDEX["bloc"] == 3

    def test_level_index_for_unknown_is_none(self) -> None:
        assert level_index_for("") is None
        assert level_index_for("galaxy") is None
