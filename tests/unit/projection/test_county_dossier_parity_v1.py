"""Golden-parity vectors for the PER-22 county dossier, generated from the oracle.

`project_county` (src/babylon/projection/county.py) remains the oracle: this
module feeds it a fixture-built graph/world reproducing each checked vector's
committed inputs and asserts the projected :class:`~babylon.projection.view_models.CountyView`
matches the vector bit-for-bit. Running the module as a script regenerates
``contracts/county_dossier_parity_v1_vectors.jsonl`` from the oracle; the
checked file must always equal that regeneration (the parity test below pins
it), and the Rust side must then match the same vectors
(``rust/crates/babylon-persistence/tests/county_dossier_parity_vectors.rs``).

Director ruling D2 (absence-maximal) leaves only ``median_wage`` and
``imperial_rent_phi`` with committed sources, so every other CountyView field
is pinned null here; see contracts/county_dossier_parity_v1.yaml for the full
contract, the 1e-6 grid scope of the bit-parity claim, and the recorded
off-grid quantization divergence.

Two oracle behaviors matter for the parity claim and are pinned, not hidden:

- Both committed fields are ``SnapToGrid`` model types (1e-6 grid,
  ROUND_HALF_UP), so the oracle canonicalizes ``-0.0`` to ``+0.0`` at the
  CountyView boundary — the same canonicalization the Rust producer applies
  before formatting. Negative-zero parity is exact on both sides.
- Off-grid committed values are quantized by the oracle while the Rust
  producer formats the raw committed bits, so every scenario commits only
  grid-exact values (``quantize(value) == value``); the verifier refuses an
  off-grid vector.
"""

from __future__ import annotations

import json
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tools.verify_county_dossier_parity_v1 import load_vectors

from babylon.kernel.math import quantize
from babylon.models.enums.topology import NodeType
from babylon.models.world_state import WorldState
from babylon.projection.county import project_county
from babylon.topology import BabylonGraph

ROOT = Path(__file__).resolve().parents[3]
VECTOR_PATH = ROOT / "contracts" / "county_dossier_parity_v1_vectors.jsonl"

WAYNE = "26163"
OAKLAND = "26125"

# Link sets Derived from the pinned Michigan spatial reference products
# (embedded fixture, digest-pinned; the Rust parity test cross-checks these
# against the same products through `michigan_spatial_reference_products_v1`).
WAYNE_LINKS: tuple[tuple[str, str], ...] = (
    ("2601380", "Allen Park city"),
    ("2607020", "Belleville city"),
    ("2621000", "Dearborn city"),
    ("2621020", "Dearborn Heights city"),
    ("2622000", "Detroit city"),
    ("2624740", "Ecorse city"),
    ("2628360", "Flat Rock city"),
    ("2631420", "Garden City city"),
    ("2632020", "Gibraltar city"),
    ("2635480", "Grosse Pointe city"),
    ("2635520", "Grosse Pointe Farms city"),
    ("2635540", "Grosse Pointe Park city"),
    ("2635580", "Grosse Pointe Woods city"),
    ("2636280", "Hamtramck city"),
    ("2636700", "Harper Woods city"),
    ("2638180", "Highland Park city"),
    ("2640680", "Inkster city"),
    ("2647800", "Lincoln Park city"),
    ("2649000", "Livonia city"),
    ("2652940", "Melvindale city"),
    ("2658980", "Northville city"),
    ("2665060", "Plymouth city"),
    ("2668760", "River Rouge city"),
    ("2668880", "Riverview city"),
    ("2669180", "Rockwood city"),
    ("2669420", "Romulus city"),
    ("2674960", "Southgate city"),
    ("2679000", "Taylor city"),
    ("2680420", "Trenton city"),
    ("2682453", "Village of Grosse Pointe Shores city"),
    ("2684940", "Wayne city"),
    ("2686000", "Westland city"),
    ("2688380", "Woodhaven city"),
    ("2688900", "Wyandotte city"),
)

OAKLAND_LINKS: tuple[tuple[str, str], ...] = (
    ("2604105", "Auburn Hills city"),
    ("2607660", "Berkley city"),
    ("2608160", "Beverly Hills village"),
    ("2608460", "Bingham Farms village"),
    ("2608640", "Birmingham city"),
    ("2609180", "Bloomfield Hills city"),
    ("2616160", "Clawson city"),
    ("2627380", "Farmington city"),
    ("2627440", "Farmington Hills city"),
    ("2627760", "Fenton city"),
    ("2627880", "Ferndale city"),
    ("2630340", "Franklin village"),
    ("2637420", "Hazel Park city"),
    ("2638700", "Holly village"),
    ("2640000", "Huntington Woods city"),
    ("2642460", "Keego Harbor city"),
    ("2644440", "Lake Angelus city"),
    ("2644940", "Lake Orion village"),
    ("2646320", "Lathrup Village city"),
    ("2646940", "Leonard village"),
    ("2650560", "Madison Heights city"),
    ("2653960", "Milford village"),
    ("2658980", "Northville city"),
    ("2659440", "Novi city"),
    ("2659920", "Oak Park city"),
    ("2661020", "Orchard Lake Village city"),
    ("2661220", "Ortonville village"),
    ("2662020", "Oxford village"),
    ("2664900", "Pleasant Ridge city"),
    ("2665440", "Pontiac city"),
    ("2669020", "Rochester city"),
    ("2669035", "Rochester Hills city"),
    ("2670040", "Royal Oak city"),
    ("2674900", "Southfield city"),
    ("2675100", "South Lyon city"),
    ("2677860", "Sylvan Lake city"),
    ("2680700", "Troy city"),
    ("2682450", "Village of Clarkston city"),
    ("2683060", "Walled Lake city"),
    ("2688140", "Wixom city"),
    ("2688260", "Wolverine Lake village"),
)

TICK = 42
COUNTY_SUBJECT_GRANT = "subject"
MEDIAN_WAGE_GRANT_KEY = "median-wage"
MEDIAN_WAGE_LABEL = "Median wage"
PHI_HOUR_GRANT_KEY = "phi-hour"
PHI_HOUR_LABEL = "Imperial rent Φ"


@dataclass(frozen=True)
class Scenario:
    """One county parity scenario; committed values are exact binary64 bits."""

    row_id: str
    county_geoid: str
    territory_local_name: str
    title: str
    links: tuple[tuple[str, str], ...]
    median_wage_bits: str | None
    phi_hour_bits: str | None
    granted_field_keys: tuple[str, ...]
    granted_place_subjects: tuple[str, ...]


SCENARIOS: tuple[Scenario, ...] = (
    Scenario(
        row_id="parity-wayne-normal",
        county_geoid=WAYNE,
        territory_local_name="wayne",
        title="Wayne County",
        links=WAYNE_LINKS,
        median_wage_bits="4035000000000000",  # 21.0
        phi_hour_bits="3ff0000000000000",  # 1.0
        granted_field_keys=(MEDIAN_WAGE_GRANT_KEY, PHI_HOUR_GRANT_KEY),
        granted_place_subjects=("2622000",),
    ),
    Scenario(
        row_id="parity-oakland-zero-wage",
        county_geoid=OAKLAND,
        territory_local_name="oakland",
        title="Oakland County",
        links=OAKLAND_LINKS,
        median_wage_bits="0000000000000000",  # 0.0
        phi_hour_bits="3fd8000000000000",  # 0.375
        granted_field_keys=(MEDIAN_WAGE_GRANT_KEY, PHI_HOUR_GRANT_KEY),
        granted_place_subjects=(),
    ),
    Scenario(
        row_id="parity-wayne-negative-zero",
        county_geoid=WAYNE,
        territory_local_name="wayne",
        title="Wayne County",
        links=WAYNE_LINKS,
        median_wage_bits="8000000000000000",  # -0.0
        phi_hour_bits="4079cb3333333333",  # 412.7
        granted_field_keys=(MEDIAN_WAGE_GRANT_KEY, PHI_HOUR_GRANT_KEY),
        granted_place_subjects=(),
    ),
    Scenario(
        row_id="parity-oakland-absent-phi",
        county_geoid=OAKLAND,
        territory_local_name="oakland",
        title="Oakland County",
        links=OAKLAND_LINKS,
        median_wage_bits="4033d9999999999a",  # 19.85
        phi_hour_bits=None,
        granted_field_keys=(MEDIAN_WAGE_GRANT_KEY, PHI_HOUR_GRANT_KEY),
        granted_place_subjects=(),
    ),
    Scenario(
        row_id="parity-wayne-field-grant-redacted",
        county_geoid=WAYNE,
        territory_local_name="wayne",
        title="Wayne County",
        links=WAYNE_LINKS,
        median_wage_bits="4035000000000000",  # 21.0
        phi_hour_bits="3ff0000000000000",  # 1.0
        granted_field_keys=(PHI_HOUR_GRANT_KEY,),
        granted_place_subjects=(),
    ),
    Scenario(
        row_id="parity-wayne-place-redlink",
        county_geoid=WAYNE,
        territory_local_name="wayne",
        title="Wayne County",
        links=WAYNE_LINKS,
        median_wage_bits="4035000000000000",  # 21.0
        phi_hour_bits="3ff0000000000000",  # 1.0
        granted_field_keys=(MEDIAN_WAGE_GRANT_KEY, PHI_HOUR_GRANT_KEY),
        granted_place_subjects=(),
    ),
)


def bits_to_float(bits: str | None) -> float | None:
    """Decode one pinned big-endian binary64 bit pattern, or pass absence on."""
    if bits is None:
        return None
    return struct.unpack(">d", bytes.fromhex(bits))[0]


def float_to_bits(value: float | None) -> str | None:
    """Encode one binary64 as its big-endian bit pattern, or pass absence on."""
    if value is None:
        return None
    return struct.pack(">d", value).hex()


def canonical_statblock(value: float) -> str:
    """Format with the Python statblock's ``%.6f`` discipline, canonicalizing -0.0.

    Mirrors the Rust producer's `format_county_statblock_value_v1`: negative
    zero canonicalizes to positive zero before formatting so a sign-only bit
    difference never re-publishes a page. The oracle's CountyView boundary
    applies the same canonicalization through its SnapToGrid types.
    """
    if value == 0.0:
        value = 0.0
    return f"{value:.6f}"


def _project(scenario: Scenario) -> Any:
    """Run the oracle against the fixture graph/world for one scenario."""
    graph = BabylonGraph()
    attributes: dict[str, Any] = {"county_fips": scenario.county_geoid}
    median_wage = bits_to_float(scenario.median_wage_bits)
    phi_hour = bits_to_float(scenario.phi_hour_bits)
    if median_wage is not None:
        attributes["tick_median_wage"] = median_wage
    if phi_hour is not None:
        attributes["tick_phi_hour"] = phi_hour
    graph.add_node(scenario.territory_local_name, NodeType.TERRITORY, **attributes)
    return project_county(
        scenario.county_geoid,
        graph=graph,
        world=WorldState(entities={}),
        tick=TICK,
    )


def build_vector_rows() -> list[dict[str, Any]]:
    """Regenerate every vector row from the Python oracle and the contract rules."""
    rows = []
    for scenario in SCENARIOS:
        view = _project(scenario)
        committed = {
            "median_wage_bits": scenario.median_wage_bits,
            "phi_hour_bits": scenario.phi_hour_bits,
        }
        signals = []
        plan_signals = []
        for grant_key, label, bits in (
            (MEDIAN_WAGE_GRANT_KEY, MEDIAN_WAGE_LABEL, scenario.median_wage_bits),
            (PHI_HOUR_GRANT_KEY, PHI_HOUR_LABEL, scenario.phi_hour_bits),
        ):
            if bits is None:
                continue
            plan_signals.append(
                {
                    "grant_key": grant_key,
                    "label": label,
                    "value": canonical_statblock(bits_to_float(bits)),
                }
            )
            if grant_key in scenario.granted_field_keys:
                signals.append(plan_signals[-1])
        rows.append(
            {
                "id": scenario.row_id,
                "kind": "parity",
                "data": {
                    "county_geoid": scenario.county_geoid,
                    "territory_local_name": scenario.territory_local_name,
                    "title": scenario.title,
                    "tick": TICK,
                    "committed": committed,
                    "grants": {
                        "county_subject": True,
                        "field_keys": list(scenario.granted_field_keys),
                        "place_subjects": list(scenario.granted_place_subjects),
                    },
                    "links": [
                        {"place_geoid": geoid, "place_name": name} for geoid, name in scenario.links
                    ],
                    "expected": {
                        "county_view": {
                            "verified_tick": view.verified_tick,
                            "median_wage_bits": float_to_bits(view.median_wage),
                            "phi_hour_bits": float_to_bits(view.imperial_rent_phi),
                            "population": view.population,
                            "class_composition": view.class_composition,
                            "consciousness": view.consciousness,
                            "legitimacy": view.legitimacy,
                            "p_acquiescence": view.p_acquiescence,
                            "p_revolution": view.p_revolution,
                            "bifurcation_score": view.bifurcation_score,
                            "habitability": view.habitability,
                            "sovereign_id": view.sovereign_id,
                        },
                        "plan_signals": plan_signals,
                        "signals": signals,
                        "places": [
                            {
                                "place_geoid": geoid,
                                "known_name": (
                                    name if geoid in scenario.granted_place_subjects else None
                                ),
                            }
                            for geoid, name in scenario.links
                        ],
                    },
                },
            }
        )
    return rows


class TestOracleParity:
    """The checked vectors are exactly what the oracle regenerates."""

    def test_checked_vectors_equal_oracle_regeneration(self) -> None:
        """Regenerating from the oracle must reproduce the checked file exactly."""
        checked = load_vectors(VECTOR_PATH)
        assert build_vector_rows() == checked

    def test_oracle_projects_committed_bits_exactly(self) -> None:
        """median_wage and imperial_rent_phi carry the SnapToGrid-projected bits.

        Grid-exact committed values are fixed points, so the projection is the
        identity except for the -0.0 -> 0.0 canonicalization both sides share.
        """
        for scenario in SCENARIOS:
            view = _project(scenario)
            for bits, projected in (
                (scenario.median_wage_bits, view.median_wage),
                (scenario.phi_hour_bits, view.imperial_rent_phi),
            ):
                expected = float_to_bits(quantize(bits_to_float(bits))) if bits else None
                assert float_to_bits(projected) == expected, (
                    scenario.row_id,
                    bits,
                )

    def test_d2_ruling_pins_every_other_field_absent(self) -> None:
        """Under D2 absence-maximal only the two committed fields may be present."""
        for scenario in SCENARIOS:
            view = _project(scenario)
            assert view.population is None, scenario.row_id
            assert view.class_composition is None, scenario.row_id
            assert view.consciousness is None, scenario.row_id
            assert view.legitimacy is None, scenario.row_id
            assert view.p_acquiescence is None, scenario.row_id
            assert view.p_revolution is None, scenario.row_id
            assert view.bifurcation_score is None, scenario.row_id
            assert view.habitability is None, scenario.row_id
            assert view.sovereign_id is None, scenario.row_id

    def test_committed_values_are_grid_fixed_points(self) -> None:
        """Parity is scoped to the oracle's 1e-6 grid: quantize is identity here."""
        for scenario in SCENARIOS:
            for bits in (scenario.median_wage_bits, scenario.phi_hour_bits):
                if bits is None:
                    continue
                value = bits_to_float(bits)
                assert quantize(value) == value, (scenario.row_id, bits)

    def test_negative_zero_oracle_value_is_canonicalized_like_the_producer(self) -> None:
        """The oracle's SnapToGrid boundary turns -0.0 into +0.0, as the producer does.

        Committed state hashing and the Rust display formatting both treat
        -0.0 == 0.0; the oracle joins them at the CountyView boundary, so the
        parity claim is exact — the committed sign bit stays pinned in the
        vector's ``committed`` block while ``expected.county_view`` carries
        the canonicalized bits.
        """
        scenario = next(item for item in SCENARIOS if item.row_id == "parity-wayne-negative-zero")
        view = _project(scenario)
        assert view.median_wage == 0.0
        assert struct.pack(">d", view.median_wage) == struct.pack(">d", 0.0)
        assert f"{view.median_wage:.6f}" == "0.000000"
        assert canonical_statblock(view.median_wage) == "0.000000"


def main() -> None:
    """Regenerate the checked vector corpus from the oracle."""
    rows = build_vector_rows()
    VECTOR_PATH.write_text(
        "".join(json.dumps(row, separators=(",", ":"), sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    print(f"wrote {len(rows)} vectors to {VECTOR_PATH}")


if __name__ == "__main__":
    main()
