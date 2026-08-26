"""Exact decision-index contract for the V1 material circuit."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

DECISIONS_DIR = Path(__file__).resolve().parents[3] / "ai" / "decisions"
ADR_STEM = "ADR238_material_circuit_v1"
ADR_PATH = DECISIONS_DIR / f"{ADR_STEM}.yaml"
INDEX_PATH = DECISIONS_DIR / "index.yaml"
CONTRACT_PATH = DECISIONS_DIR.parents[1] / "contracts" / "material_circuit_v1.yaml"
EXPECTED_TITLE = (
    "Material Circuit V1 makes orders, exact stocks, delayed delivery, "
    "realization, and Leontief production one conserved Rust transition"
)


def _mapping(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_adr238_records_the_exact_order_inventory_and_production_law() -> None:
    decision = _mapping(ADR_PATH)[ADR_STEM]
    index = _mapping(INDEX_PATH)

    assert decision["status"] == "accepted"
    assert decision["date"] == "2026-08-26"
    assert decision["title"] == EXPECTED_TITLE
    assert decision["crate"] == "babylon-material-circuit"
    assert decision["live_activation"] is False

    decision_text = " ".join(str(decision["decision"]).split())
    for required_text in (
        "Every material identity is a distinct 32-byte type",
        "unsigned 64-bit integers",
        "floor(available * requested_i / total_requested)",
        "canonical process order receives none",
        "debits supplier inventory and creates one sparse lot",
        "derive the following-week production commitment",
        "does not activate gameplay",
    ):
        assert required_text in decision_text

    assert index["meta"]["version"] == "1.85.0"
    assert index["decisions"][ADR_STEM] == {
        "title": EXPECTED_TITLE,
        "status": "accepted",
        "date": "2026-08-26",
        "file": ADR_PATH.name,
    }


def test_adr238_schema_pins_conservation_bounds_and_inert_activation() -> None:
    contract = _mapping(CONTRACT_PATH)

    assert contract["encoding"] == {
        "byte_order": "big-endian",
        "integer_encoding": "unsigned-fixed-width",
        "quantity_encoding": "u64",
        "identity_encoding": "raw-32-bytes",
        "row_count_encoding": "u32",
        "trailing_bytes": "forbidden",
        "noncanonical_row_order": "forbidden",
    }
    assert contract["access_modes"] == {"commodity_sale": 1}
    assert contract["limits"] == {
        "rows_per_family": {
            "value": 65_536,
            "classification": "Designed",
            "purpose": (
                "serialization, memory, and transition fuel ceiling, not material abundance"
            ),
        },
        "production_resource_groups": {
            "value": 131_072,
            "derivation": (
                "rows_per_family * 2 for the disjoint input and labor resource families"
            ),
        },
    }
    assert contract["canonical_order"]["priority"] == (
        "canonical order grants no material priority"
    )
    assert contract["base_vector"] == {
        "canonical_bytes": 1_555,
        "digest_hex": "3576baa1af2a38be8a1376259dc4423a470607ad9eef5969715931e16b30620a",
    }
    assert any("gameplay activation" in surface for surface in contract["excluded_surfaces"])
