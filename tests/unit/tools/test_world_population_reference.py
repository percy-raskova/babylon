"""Population context preserves source scope and avoids duplicate residents."""

from __future__ import annotations

import csv
import gzip
import json
import sys
from decimal import Decimal
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))
import make_world_population_reference as builder  # type: ignore[import-not-found]  # noqa: E402


def test_decimal_population_does_not_promote_spreadsheet_tails_to_people() -> None:
    assert builder.persons("8161972.5719999997") == 8_161_972_572
    assert builder.persons("0.0005") == 0
    assert builder.persons("0.0015") == 2
    for raw in ("NaN", "Infinity", "-1", " 1", "1e90"):
        with pytest.raises(builder.ReferenceBuildError):
            builder.persons(raw)


def test_committed_population_scope_and_totals() -> None:
    with gzip.open(builder.ARTIFACT_OUT, "rt", newline="") as stream:
        rows = list(csv.DictReader(stream))
    by_id = {row["identity_id"]: row for row in rows}
    assert len(rows) == len(by_id) == 252
    assert list(by_id) == sorted(by_id)
    assert by_id["m49:250"]["source_notes"] == "26"
    assert by_id["m49:156"]["source_notes"] == "5"
    assert by_id["m49:158"]["population_persons"] == "23213962"
    assert by_id["m49:248"]["population_persons"] == "30654"
    assert by_id["m49:248"]["population_evidence"] == "Designed"
    assert by_id["m49:246"]["population_persons"] == "5586656"
    assert by_id["m49:246"]["source_population_thousands_raw"] == "5617.31"
    assert by_id["m49:581"]["population_persons"] == ""
    assert by_id["m49:581"]["status"] == "not_published"
    for identity, parent in [("m49:744", "m49:578"), ("m49:162", "m49:036")]:
        assert by_id[identity]["status"] == "included_in_parent"
        assert by_id[identity]["accounted_in_identity"] == parent
        assert by_id[identity]["population_persons"] == ""
    for identity in ("census:5082", "census:5083"):
        assert by_id[identity]["status"] == "trade_only"
        assert by_id[identity]["accounted_in_identity"] == "m49:275"
        assert by_id[identity]["population_persons"] == ""
    assert sum(int(r["population_persons"] or 0) for r in rows) == 8_161_972_576


def test_projection_and_domestic_source_boundaries_are_explicit() -> None:
    metadata = json.loads(builder.METADATA_OUT.read_text())
    assert metadata["source_kind"] == "UN WPP2024 medium-fertility projection"
    assert metadata["source_date"] == "2024-07-01"
    assert metadata["country_area_source_rows"] == 237
    assert metadata["rounding_residual_persons"] == 4
    assert metadata["runtime_consumers"] == []
    assert metadata["domestic_runtime_source"] == "ACS 2024 five-year county capture"
    totals = {row["scope"]: row for row in metadata["scope_totals"]}
    assert totals["european_union"]["known_population_persons"] == 450_228_882
    assert totals["remaining_europe"]["known_population_persons"] == 151_518_908
    assert totals["us_dependency"]["known_population_persons"] == 3_585_929
    assert totals["us_dependency"]["not_published_identities"] == ["m49:581"]
    assert Decimal(metadata["world_source_thousands_raw"]) == Decimal("8161972.5719999997")


def test_population_registry_and_exact_source_pins() -> None:
    import hashlib

    import yaml

    metadata = json.loads(builder.METADATA_OUT.read_text())
    manifest = yaml.safe_load((ROOT / "data-artifacts.yaml").read_text())
    (entry,) = [r for r in manifest["artifacts"] if r["name"] == "world_population_reference_2024"]
    assert entry["sha256"] == metadata["artifact"]["sha256"]
    assert entry["rows"] == 252
    assert hashlib.sha256(builder.ARTIFACT_OUT.read_bytes()).hexdigest() == entry["sha256"]
    for key, path in [
        ("source_manifest", builder.SOURCE_MANIFEST),
        ("scope_policy", builder.POLICY_PATH),
        ("membership", builder.MEMBERSHIP_PATH),
    ]:
        assert metadata[key]["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.mark.parametrize("quantity", [True, False, 1.5, "30654", -1, 0, 6_000_000])
def test_population_apportionment_refuses_nonintegral_or_unfunded_people(quantity: object) -> None:
    policy = {
        "apportionments": [{"parent": "m49:246", "child": "m49:248", "persons": quantity}],
        "included_in_parent": {},
    }
    with pytest.raises(builder.ReferenceBuildError, match="population_apportionment"):
        builder.capture({"m49:246": {"M": "5617.31"}}, policy)
