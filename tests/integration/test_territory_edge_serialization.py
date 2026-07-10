"""Spec 061 US6 / T084 + T085: Territory + Edge spec-061 fields are present.

Tests the bridge ``_serialize_territory`` + ``_serialize_edge`` helpers
emit the new spec 061 fields (FR-013 + FR-014).

Spec-109 A2 (Constitution III.11) superseded the original FR-013 contract:
``consciousness``/``solidarity``/``dominant_community`` were fabricated
0.0/"" defaults when the engine attr was absent — no wired system computes
a territory-level aggregate for them, so they are honest ``None`` now,
never a plausible-looking placeholder. ``wealth`` IS a real Territory
field (Feature 021) and is read directly rather than defaulted.
"""

from __future__ import annotations

from typing import Any

from web.game.engine_bridge import _serialize_edge, _serialize_territory


class _StubTerritory:
    def __init__(self, **kw: Any) -> None:
        self.id = kw.get("id", "terr-x")
        self.name = kw.get("name", "X County")
        self.h3_index = kw.get("h3_index", "8a1fb46622dffff")
        self.h3_resolution = kw.get("h3_resolution", 7)
        self.county_fips = kw.get("county_fips", "26163")
        self.heat = kw.get("heat", 0.1)
        self.sector_type = kw.get("sector_type", "core")
        self.territory_type = kw.get("territory_type", "county")
        self.profile = kw.get("profile", "low_profile")
        self.rent_level = kw.get("rent_level", 0.3)
        self.population = kw.get("population", 1_000)
        self.under_eviction = kw.get("under_eviction", False)
        self.biocapacity = kw.get("biocapacity", 0.9)
        # Real Territory fields (spec-109 A2 widened _serialize_territory to
        # read these directly, matching the pydantic model's own defaults —
        # see babylon.models.entities.territory.Territory).
        self.max_biocapacity = kw.get("max_biocapacity", 100.0)
        self.extraction_intensity = kw.get("extraction_intensity", 0.0)
        self.wealth = kw.get("wealth", 0.0)
        self.median_wage = kw.get("median_wage", 0.0)
        self.reserve_ratio = kw.get("reserve_ratio", 0.0)
        self.foreclosure_rate = kw.get("foreclosure_rate", 0.0)
        self.eviction_rate = kw.get("eviction_rate", 0.0)
        self.displacement_rate = kw.get("displacement_rate", 0.0)
        self.concentrated_ownership = kw.get("concentrated_ownership", 0.0)
        self.absentee_landlord_share = kw.get("absentee_landlord_share", 0.0)
        self.host_id = kw.get("host_id")
        self.occupant_id = kw.get("occupant_id")


class _StubEdge:
    def __init__(self, **kw: Any) -> None:
        self.source_id = kw.get("source_id", "a")
        self.target_id = kw.get("target_id", "b")
        self.edge_type = kw.get("edge_type", "SOLIDARITY")
        self.value_flow = kw.get("value_flow", 1.0)
        self.tension = kw.get("tension", 0.0)
        self.solidarity_strength = kw.get("solidarity_strength", 0.5)
        for k in ("rate_of_profit", "rent_burden", "age_ticks"):
            if k in kw:
                setattr(self, k, kw[k])


class TestTerritorySerializationFR013:
    def test_extended_fields_present(self) -> None:
        out = _serialize_territory(_StubTerritory())
        for key in ("consciousness", "solidarity", "wealth", "dominant_community"):
            assert key in out, f"missing {key}"

    def test_ungrounded_fields_are_honest_none_not_fabricated(self) -> None:
        """Spec-109 A2: no wired system computes a territory-level
        consciousness/solidarity/dominant-community aggregate — the honest
        value is None, never a plausible-looking 0.0/"" placeholder."""
        out = _serialize_territory(_StubTerritory())
        assert out["consciousness"] is None
        assert out["solidarity"] is None
        assert out["dominant_community"] is None

    def test_wealth_is_a_real_field_read_directly(self) -> None:
        """``wealth`` (Feature 021) IS a Territory model field — its default
        of 0.0 comes from the model, not a getattr fallback."""
        out = _serialize_territory(_StubTerritory())
        assert out["wealth"] == 0.0

    def test_wealth_passes_through_when_set(self) -> None:
        out = _serialize_territory(_StubTerritory(wealth=12_500.0))
        assert out["wealth"] == 12_500.0


class TestEdgeSerializationFR014:
    def test_id_is_deterministic_from_source_target_mode(self) -> None:
        e = _serialize_edge(_StubEdge(source_id="x", target_id="y", edge_type="SOLIDARITY"))
        assert e["id"] == "x-y-SOLIDARITY"

    def test_optional_fields_default_to_none_when_attribute_absent(self) -> None:
        out = _serialize_edge(_StubEdge())
        assert out["rate_of_profit"] is None
        assert out["rent_burden"] is None
        assert out["age_ticks"] is None

    def test_optional_fields_pass_through_when_attribute_present(self) -> None:
        out = _serialize_edge(_StubEdge(rate_of_profit=0.18, rent_burden=0.42, age_ticks=12))
        assert out["rate_of_profit"] == 0.18
        assert out["rent_burden"] == 0.42
        assert out["age_ticks"] == 12
