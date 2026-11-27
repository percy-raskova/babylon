"""Task 13 of stage 5: the rebuilt scenario, from the builder."""

from __future__ import annotations

import ast
import json
import re
import sys
import tomllib
from dataclasses import replace
from fractions import Fraction
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools"))

import make_national_county_reference as county  # type: ignore[import-not-found]  # noqa: E402
import make_national_opening_numbers as mk  # type: ignore[import-not-found]  # noqa: E402
import national_opening_abroad as ab  # type: ignore[import-not-found]  # noqa: E402
import national_opening_recut as r  # type: ignore[import-not-found]  # noqa: E402
import national_opening_tiers as t_mod  # type: ignore[import-not-found]  # noqa: E402
import national_opening_units as u  # type: ignore[import-not-found]  # noqa: E402

ROOT = county.ROOT
ReferenceBuildError = county.ReferenceBuildError
F = Fraction
FIXTURE = (
    ROOT / "rust/crates/babylon-persistence/tests/fixtures/national_twelve_trades.defines.toml"
)
TEMPLATE_TEXT = mk.TEMPLATE.read_text(encoding="utf-8")
SETTINGS = r.Settings()

# ---- a hand opening of the twelve trades ---------------------------------------------------

PRODUCTS: dict[str, tuple[str, int, int, tuple[int, int] | None]] = {
    # key: (kind, price micros, grams, handling)
    "food": ("storable", 2_000_000, 14_000, (1, 5)),
    "resources": ("storable", 3_000_000, 10_000, None),
    "materials": ("storable", 4_000_000, 5_000, (1, 4)),
    "equipment": ("storable", 800_000_000, 250_000, None),
    "utility": ("utility", 1_000_000, 0, None),
    "housing": ("utility", 9_000_000, 0, None),
    "household_services": ("service", 6_000_000, 0, None),
    "business_services": ("utility", 5_000_000, 0, None),
    "public_provision": ("service", 1_000_000, 0, None),
    "consumer_goods": ("storable", 7_000_000, 5_000, (1, 2)),
    "leisure": ("service", 8_000_000, 0, None),
}
RECIPES: dict[str, tuple[int, int, dict[str, int], int | None]] = {
    # trade: (units a batch, hours a batch, inputs, margin)
    "food": (16, 16, {"materials": 1, "utility": 1}, 250),
    "extraction": (8, 16, {"resource_deposit": 8, "utility": 1}, 300),
    "energy_utilities": (160, 16, {"resources": 8}, 100),
    "manufacturing": (8, 16, {"resources": 8}, 200),
    "capital_goods": (1, 16, {"resources": 8}, 150),
    "construction_housing": (16, 16, {"materials": 1}, 120),
    "household_services": (8, 160, {"materials": 1}, 110),
    "business_services": (16, 160, {"utility": 1}, 90),
    "public_provisioning": (160, 160, {"materials": 1}, None),
    "consumer_goods": (8, 16, {"materials": 2, "business_services": 1}, 400),
    "leisure_hospitality": (16, 160, {"food": 2}, 500),
}
PRODUCT_OF = r.TWELVE.product


def hand_written(*, rate: int = 1500, fund: int = 800, wage_rate: int | None = None) -> u.Written:
    products = {
        key: u.Product(
            key,
            f"{key} label",
            f"{key} unit",
            kind,  # type: ignore[arg-type]
            F(1),
            price,
            price // 4,
            price * 4,
            max(1, price // 40),
            grams,
            handling,
        )
        for key, (kind, price, grams, handling) in PRODUCTS.items()
    }
    recipes = {
        trade: u.Recipe(trade, n, hours, dict(inputs), margin, F(1), F(1))
        for trade, (n, hours, inputs, margin) in RECIPES.items()
    }
    return u.Written(
        products=products,
        recipes=recipes,
        machine_price_micros=800_000_000,
        workers_per_machine=dict.fromkeys(RECIPES, 4),
        machine_life_periods=100,
        wage_tax_bps=rate if wage_rate is None else wage_rate,
        operating_income_tax_bps=rate,
        fund_share_bps=fund,
        import_bps={
            "food": 2000,
            "resources": 100,
            "materials": 300,
            "consumer_goods": 400,
            "equipment": 0,
            "business_services": 700,
        },
        batch_hours_lost={},
        demand_moved={},
        machines_worn=F(5),
    )


def hand_tiers(
    comfort: dict[str, int] | None = None, luxury: dict[str, int] | None = None
) -> t_mod.Tiers:
    return t_mod.Tiers(
        comfort=comfort
        or {
            "food": 20,
            "materials": 8,
            "consumer_goods": 30,
            "utility": 20,
            "housing": 9,
            "business_services": 90,
            "household_services": 30,
        },
        luxury=luxury
        or {
            "food": 14,
            "materials": 5,
            "consumer_goods": 30,
            "utility": 14,
            "housing": 7,
            "business_services": 90,
            "household_services": 20,
            "leisure": 1000,
        },
        exact={},
        luxury_scale_bps={("26163", "earning_owner"): 12_500},
        no_earner_estimate={},
        residence_estimate={},
        reach={},
        demand_gap={},
        own_price_gap={},
        state_services={},
        country_services={},
        place_bodies={},
        share_by_part_bps={"26163": 4000, "01001/below": 0},
        place_grant_micros={"01001/below": 123_456},
    )


def hand_regions(scale: int | None = None) -> dict[str, ab.RegionOpening]:
    goods = sorted(SETTINGS.crossing)
    out: dict[str, ab.RegionOpening] = {}
    for index, key in enumerate(sorted(REGION_KEYS)):
        out[key] = ab.RegionOpening(
            key=key,
            function_weights_bps=(1000, 500, 800, 500, 1000, 700, 700, 1000, 1000, 500, 1800, 500),
            export_bps=dict.fromkeys(goods, 100 + index),
            money_per_person_micros=1_000_000,
            sales_micros=10,
            purchases_micros=10,
            luxury_scale_bps=scale if key in ("canada", "dependency") else None,
        )
    return out


REGION_KEYS = (
    "canada",
    "mexico",
    "china",
    "russia",
    "india",
    "japan",
    "european_union",
    "remaining_europe",
    "latin_america_caribbean",
    "west_asia_north_africa",
    "sub_saharan_africa",
    "remaining_asia_pacific",
    "dependency",
)


def rendered(
    *,
    template: str = TEMPLATE_TEXT,
    w: u.Written | None = None,
    t: t_mod.Tiers | None = None,
    regs: dict[str, ab.RegionOpening] | None = None,
) -> str:
    return mk.render(
        template,
        w or hand_written(),
        t or hand_tiers(),
        regs or hand_regions(scale=12_500),
        SETTINGS,
    )


# ---- the template ------------------------------------------------------------------------


def test_the_template_has_every_marker() -> None:
    markers = {
        line.split()[1] for line in TEMPLATE_TEXT.split("\n") if line.startswith("#@builder")
    }
    facts = mk.template_facts(TEMPLATE_TEXT)
    blocks = mk._blocks(
        hand_written(),
        hand_tiers(),
        hand_regions(),
        SETTINGS,
        facts,
        mk.template_cargo(TEMPLATE_TEXT),
    )
    assert markers == set(blocks)
    for key in (
        "crossing_services",
        "country_services",
        "share_by_part",
        "place_grants",
        "programs",
    ):
        assert key in markers


def test_the_template_facts_are_the_fixtures() -> None:
    facts = mk.template_facts(TEMPLATE_TEXT)
    commodities = tomllib.loads(FIXTURE.read_text(encoding="utf-8"))["commodity"]
    for key, row in commodities.items():
        if key == "resource_deposit":
            assert facts.labels[key][0] == row["label"]
            continue
        assert facts.labels[key] == (row["label"], row["unit_label"])
        assert facts.prices[key] == row["opening_price_micros"]
        if row["grams_per_unit"] > 0:
            assert facts.grams[key] == row["grams_per_unit"]
        else:
            assert key not in facts.grams
    cargo = mk.template_cargo(TEMPLATE_TEXT)
    assert cargo == {k: v["cargo_class"] for k, v in commodities.items() if "cargo_class" in v}


def test_the_template_keeps_the_fixtures_hand_made_sections() -> None:
    text = tomllib.loads(rendered())
    fixture = tomllib.loads(FIXTURE.read_text(encoding="utf-8"))
    for section in (
        "organizer",
        "aid",
        "grain",
        "companies",
        "household_lifecycle",
        "county_review",
        "city_pd",
        "household_support_claimant",
        "households",
    ):
        assert text[section] == fixture[section], section
    assert text["companies"]["opening_treasury_bps"] == 0
    for key in ("place_services", "journey_timing", "service_reach"):
        assert text["markets"][key] == fixture["markets"][key]
    assert text["grain"]["basis"] == fixture["grain"]["basis"]


def test_render_refuses_a_stray_marker() -> None:
    with pytest.raises(ReferenceBuildError, match=r"^template_marker: nonsense"):
        rendered(template=TEMPLATE_TEXT + "\n#@builder nonsense\n")
    leftover = TEMPLATE_TEXT.replace("#@builder financial", "x = 1 #@builder financial")
    assert leftover != TEMPLATE_TEXT
    with pytest.raises(ReferenceBuildError, match=r"^template_marker: "):
        rendered(template=leftover)
    missing = TEMPLATE_TEXT.replace("#@builder processes\n", "")
    assert missing != TEMPLATE_TEXT
    with pytest.raises(ReferenceBuildError, match=r"^template_marker: processes"):
        rendered(template=missing)
    twice = TEMPLATE_TEXT + "\n#@builder financial\n"
    with pytest.raises(ReferenceBuildError, match=r"^template_marker: financial"):
        rendered(template=twice)


def test_a_template_that_takes_working_capital_is_refused() -> None:
    changed = TEMPLATE_TEXT.replace("opening_treasury_bps = 0", "opening_treasury_bps = 5000")
    assert changed != TEMPLATE_TEXT
    with pytest.raises(ReferenceBuildError, match=r"^template_marker: opening_treasury_bps"):
        rendered(template=changed)


# ---- what render writes --------------------------------------------------------------------


def _value_lines(text: str) -> list[str]:
    out = []
    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", "[")) or "=" not in stripped:
            continue
        out.append(stripped.split("=", 1)[1].split("#", 1)[0])
    return out


def _floats(node: object) -> list[object]:
    if isinstance(node, float):
        return [node]
    if isinstance(node, dict):
        return [x for v in node.values() for x in _floats(v)]
    if isinstance(node, list):
        return [x for v in node for x in _floats(v)]
    return []


def test_render_writes_integers_only() -> None:
    text = rendered()
    document = tomllib.loads(text)
    assert not _floats(document)
    for value in _value_lines(text):
        # Text in quotes may hold a full stop; a figure may not.
        assert "." not in re.sub(r'"[^"]*"', "", value), value
    fixture = tomllib.loads(FIXTURE.read_text(encoding="utf-8"))
    assert set(document["commodity"]) == set(fixture["commodity"])
    assert set(document["process"]) == set(fixture["process"])
    assert document["schema_version"] == 8
    assert "builder" not in document
    assert text.endswith("\n")
    assert "\r" not in text
    assert all(not line.endswith(" ") for line in text.split("\n"))


def test_render_is_deterministic() -> None:
    assert rendered() == rendered()


def test_render_writes_the_keys_of_the_rulings() -> None:
    document = tomllib.loads(rendered())
    markets = document["markets"]
    assert markets["crossing_services"] == ["business_services"]
    assert markets["country_services"] == ["business_services", "leisure", "utility"]
    assert markets["paying_order"] == list(SETTINGS.paying_order)
    assert set(markets["import_bps"]) == set(SETTINGS.crossing)
    for key in ("utility", "business_services", "housing"):
        assert document["commodity"][key]["kind"] == "utility"
    for key in ("household_services", "leisure", "public_provision"):
        assert document["commodity"][key]["kind"] == "service"
    for key, region in [*document["counterpart"].items(), ("dependency", document["dependency"])]:
        assert set(region["export_bps"]) == set(SETTINGS.crossing), key
        assert region["price_scale_bps"] == 10_000
        assert sum(region["function_weights_bps"]) == 10_000
    fund = document["fund"]
    assert fund["evidence_class"] == "Designed"
    assert fund["wage_tax_share_bps"] == fund["operating_income_tax_share_bps"] == 800
    assert fund["reserve_periods"] == 2
    assert fund["share_by_part"] == {"01001/below": 0, "26163": 4000}
    assert document["place_grants"] == [
        {"amount_per_period_micros": 123_456, "part": "01001/below"}
    ]
    programs = {p["key"]: p for p in document["programs"]}
    assert set(programs) == {"laid_off", "no_earner", "residence"}
    for key, recipients in (
        ("no_earner", "no_earner_at_opening"),
        ("residence", "collective_residence_at_opening"),
    ):
        assert programs[key] == {
            "key": key,
            "kind": "own_needs",
            "rank": 0,
            "recipients": recipients,
            "share_bps": 10_000,
        }
    assert programs["laid_off"]["wage_share_bps"] == 5000
    assert programs["laid_off"]["half_periods"] == 13
    financial = document["financial"]
    assert financial["wage_tax_bps"] == financial["operating_income_tax_bps"] == 1500
    assert financial["private_distribution_bps"] == 10_000
    assert document["household_time"]["unmet_hours_per_unit"] == {"food": 1}
    assert document["equipment"]["machine_life_periods"] == 100
    assert len(document["equipment"]["workers_per_machine"]) == 11
    assert [n["good"] for n in document["household_needs"]] == [g for g, _ in mk.NEED_ROWS]
    assert [n["units_per_basis"] for n in document["household_needs"]] == [28] * 5 + [1]


def test_render_writes_each_shop_good_with_its_handling_and_cargo() -> None:
    document = tomllib.loads(rendered())
    commodity = document["commodity"]
    for key in ("food", "materials", "consumer_goods"):
        assert (commodity[key]["handling_hours"], commodity[key]["handling_units"]) == {
            "food": (1, 5),
            "materials": (1, 4),
            "consumer_goods": (1, 2),
        }[key]
    assert "handling_hours" not in commodity["resources"]
    assert commodity["resources"]["cargo_class"] == "dry_bulk"
    assert "cargo_class" not in commodity["utility"]
    assert commodity["resource_deposit"]["grams_per_unit"] == 10_000
    assert commodity["resource_deposit"]["unit_label"] == "resources unit"
    process = document["process"]
    assert "margin_bps" not in process["public_provisioning"]
    assert process["extraction"]["inputs"]["resource_deposit"] == 8
    assert process["leisure_hospitality"]["output"] == "leisure"


def test_render_writes_the_luxury_scales_where_the_compiler_admits_them() -> None:
    document = tomllib.loads(rendered())
    scales = document["luxury_scale"]["by_account"]
    assert scales["26163:EarningOwner"] == 12_500
    assert scales["canada:pooled-external"] == 12_500
    for code in ab.DEPENDENCY_CODES:
        assert scales[f"{code}:pooled-external"] == 12_500
    assert len(scales) == 1 + 1 + 6


def test_the_wants_cover_the_census_scenario_s_products() -> None:
    document = tomllib.loads(rendered())
    wants = document["household_wants"]
    goods = {(row["tier"], row["good"]) for row in wants}
    for good in ("consumer_goods", "business_services"):
        assert ("comfort", good) in goods
        assert ("luxury", good) in goods
    assert ("luxury", "leisure") in goods
    assert ("comfort", "leisure") not in goods
    assert all(row["basis"] == "persons" for row in wants)
    assert document["markets"]["country_services"] == sorted(SETTINGS.country_services)
    # A product whose rows all round to 0 is refused.
    no_leisure = hand_tiers(luxury={"food": 14, "consumer_goods": 30, "business_services": 90})
    with pytest.raises(ReferenceBuildError, match=r"^wants_cover: leisure"):
        rendered(t=no_leisure)
    no_services = hand_tiers(
        comfort={"food": 20, "consumer_goods": 30}, luxury={"leisure": 1000, "consumer_goods": 1}
    )
    with pytest.raises(ReferenceBuildError, match=r"^wants_cover: business_services"):
        rendered(t=no_services)


def test_one_rate_on_both_taxes() -> None:
    with pytest.raises(ReferenceBuildError, match=r"^scenario_shape: rates"):
        rendered(w=hand_written(wage_rate=1400))


def test_a_scenario_over_its_bound_is_refused() -> None:
    padded = TEMPLATE_TEXT + "# " + "x" * mk.POLICY_BOUND + "\n"
    with pytest.raises(ReferenceBuildError, match=r"^scenario_size"):
        rendered(template=padded)


def test_a_setting_not_ruled_is_refused() -> None:
    absent = Path("/nonexistent/accounts.csv.gz")
    settings = replace(SETTINGS, place_body="one_share")  # type: ignore[arg-type]
    with pytest.raises(ReferenceBuildError, match=r"^setting_not_ruled: place_body"):
        mk.build(
            accounts=absent,
            pay=absent,
            census=absent,
            settings=settings,
            scenario_out=absent,
            metadata_out=absent,
        )
    r.check_ruled(SETTINGS)


# ---- the balances as written ---------------------------------------------------------------


def test_a_residual_over_a_hundredth_is_refused() -> None:
    mk.check_balances({"1": (F(1000), F(10)), "2": (F(1000), F(-10))})
    with pytest.raises(ReferenceBuildError, match=r"^balance: 2"):
        mk.check_balances({"1": (F(1000), F(10)), "2": (F(1000), F(11))})
    with pytest.raises(ReferenceBuildError, match=r"^balance: 4"):
        mk.check_balances({"4": (F(0), F(0))})


def test_decimals_are_half_up_and_exact() -> None:
    assert mk.decimal(F(1, 3)) == "0.333333333"
    assert mk.decimal(F(2, 3)) == "0.666666667"
    assert mk.decimal(F(-1, 2000000000)) == "0.000000000"
    assert mk.decimal(F(-5, 4)) == "-1.250000000"
    assert mk.fr(F(7, 2)) == {"decimal": "3.500000000", "exact": "7/2"}


def test_no_float_in_the_module() -> None:
    tree = ast.parse((ROOT / "tools/make_national_opening_numbers.py").read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant):
            assert not isinstance(node.value, float), node.lineno
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in {"float", "round"}, node.lineno
        if isinstance(node, ast.Import | ast.ImportFrom):
            names = [a.name for a in node.names] + [getattr(node, "module", None) or ""]
            assert "statistics" not in names
            assert "math" not in names


# ---- the committed scenario --------------------------------------------------------------


def _committed_metadata() -> dict[str, Any]:
    loaded = json.loads(mk.METADATA_OUT.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def test_the_committed_scenario_names_its_inputs() -> None:
    meta = _committed_metadata()
    inputs = meta["inputs"]
    assert inputs["accounts_sha256"] == mk._digest(r.ACCOUNTS_PATH)
    assert inputs["pay_sha256"] == mk._digest(mk.PAY_PATH)
    assert inputs["template_sha256"] == mk._digest(mk.TEMPLATE)
    assert inputs["census_text_sha256"] == r.read_census(r.CENSUS_PATH).sha256
    assert set(inputs["builder_sources_sha256"]) == {
        str(path.relative_to(ROOT)) for path in mk.BUILDER_SOURCES
    }
    for path in mk.BUILDER_SOURCES:
        assert inputs["builder_sources_sha256"][str(path.relative_to(ROOT))] == mk._digest(path)
    assert meta["contract"] == "NationalOpeningNumbersV1"
    assert meta["issue"] == "PER-371"
    assert meta["scenario_bytes"] == mk.SCENARIO_OUT.stat().st_size


def test_the_committed_scenario_fits_its_bound() -> None:
    data = mk.SCENARIO_OUT.read_bytes()
    assert len(data) <= mk.POLICY_BOUND
    assert tomllib.loads(data.decode("utf-8"))["schema_version"] == 8
    assert data.endswith(b"\n")
    assert b"\r" not in data


def test_the_committed_files_are_under_the_repository_size_rule() -> None:
    assert mk.METADATA_OUT.stat().st_size <= 1_048_576
    assert mk.SCENARIO_OUT.stat().st_size <= 1_048_576


def test_the_committed_metadata_has_the_keys_task_15_reads() -> None:
    meta = _committed_metadata()
    dues = meta["benefits"]["estimated_dues_micros"]
    assert set(dues) == {"no_earner", "residence"}
    for kind in dues.values():
        assert all(isinstance(v, int) for v in kind.values())
    shops = meta["shops"]["estimated_price_micros"]
    for part, keys in shops.items():
        for label, goods in keys.items():
            assert label in r.BUDGET_LABEL.values(), (part, label)
            assert set(goods) == {"consumer_goods", "food", "materials"}
            assert all(isinstance(v, int) for v in goods.values())
    for trade, row in meta["trades"].items():
        # decision 6: each recipe's three errors, the ones `batch` judges it by
        assert set(row["recipe_hours_error"]) == {"decimal", "exact"}, trade
        assert row["recipe_input_errors"], trade
        for err in row["recipe_input_errors"].values():
            assert set(err) == {"decimal", "exact"}, trade
    moved = meta["recut"]["moved"]
    assert set(moved) <= {"R1", "R2", "R3", "O4_inventories"}
    for products in moved.values():
        for value in products.values():
            assert set(value) == {"decimal", "exact"}
    scenario = tomllib.loads(mk.SCENARIO_OUT.read_text(encoding="utf-8"))
    assert set(scenario["fund"]["share_by_part"]) == set(meta["parts"]["rows"])
    assert meta["regenerate"].endswith("tools/make_national_opening_numbers.py")


# ---- the committed tables (slow) -----------------------------------------------------------


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> tuple[dict[str, Any], Path]:
    folder = tmp_path_factory.mktemp("rebuilt")
    meta = mk.build(
        accounts=r.ACCOUNTS_PATH,
        pay=mk.PAY_PATH,
        census=r.CENSUS_PATH,
        scenario_out=folder / "defines.toml",
        metadata_out=folder / "defines.metadata.json",
    )
    return meta, folder


@pytest.mark.slow
def test_the_committed_scenario_is_what_the_builder_writes(built: Any) -> None:
    _, folder = built
    assert (folder / "defines.toml").read_bytes() == mk.SCENARIO_OUT.read_bytes()
    assert (folder / "defines.metadata.json").read_bytes() == mk.METADATA_OUT.read_bytes()


@pytest.mark.slow
def test_the_balances_as_written_close_within_one_percent(built: Any) -> None:
    meta, _ = built
    for name, row in sorted(meta["balances"]["as_written"].items()):
        flow = F(row["flow"]["decimal"])
        residual = F(row["residual"]["decimal"])
        print(
            f"balance {name}: flow {row['flow']['decimal']}, residual {row['residual']['decimal']}"
        )  # noqa: T201
        assert flow > 0
        assert abs(residual) * 100 <= flow, name
    print(f"largest part residual {meta['parts']['largest_residual']}")  # noqa: T201


@pytest.mark.slow
def test_every_observed_job_is_needed_as_written(built: Any) -> None:
    """At the written figures and the national prices (Task 11's `demand_gap` basis), the
    hours each trade's recipe needs are within 1% of its census hours. At each account's own
    prices the same count is reported, not asserted: Task 11's `own_price_gap` says what own
    prices move."""
    meta, _ = built
    for trade, row in sorted(meta["jobs_as_written"].items()):
        needed = F(row["needed_hours"]["decimal"])
        census_hours = row["census_hours"]
        own = meta["jobs_at_own_prices"][trade]
        print(  # noqa: T201
            f"{trade}: needs {row['needed_hours']['decimal']} of {census_hours} hours "
            f"(at own prices {own['ratio']['decimal']} of them)"
        )
        assert census_hours > 0
        assert abs(needed - census_hours) * 100 <= census_hours, trade
