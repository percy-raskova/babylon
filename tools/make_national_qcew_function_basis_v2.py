#!/usr/bin/env python3
"""Version 2 of the national QCEW function cut: twelve trades.

Consumer goods and leisure are cut out of version 1's ten trades. This module
validates the version 2 mapping and builds on version 1's helpers; it never
edits version 1's mapping, builder or tables.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Final

import make_national_qcew_function_basis as basis
from make_national_county_reference import ROOT, ReferenceBuildError, _unique_object

MAPPING_V2_PATH: Final = ROOT / "contracts/national_qcew_function_mapping_v2.json"
FUNCTION_IDS_V2: Final = (
    "food",
    "extraction",
    "energy_utilities",
    "manufacturing",
    "consumer_goods",
    "capital_goods",
    "construction_housing",
    "distribution_transport",
    "household_services",
    "leisure_hospitality",
    "business_services",
    "public_provisioning",
)


def validate_mapping_v2(document: dict[str, Any]) -> basis.FunctionMapping:
    """Repeat version 1's checks under the version 2 contract name and ids."""
    if (
        document.get("contract") != "NationalQcewFunctionMappingV2"
        or document.get("evidence_class") != "Designed"
        or document.get("source_vintage") != 2024
    ):
        raise ReferenceBuildError("function_mapping_identity")
    if set(document.get("ownership_codes", {})) != set(basis.OWNERSHIP_CODES):
        raise ReferenceBuildError("function_mapping_ownership")
    functions = document.get("functions", [])
    if [item.get("id") for item in functions] != list(FUNCTION_IDS_V2):
        raise ReferenceBuildError("function_mapping_functions")
    codes: dict[str, str] = {}
    for function in functions:
        if not function.get("qualification") or not function.get("naics_codes"):
            raise ReferenceBuildError("function_mapping_qualification")
        for code in function["naics_codes"]:
            basis.aggregation_level(code)
            if code in codes or code == "99":
                raise ReferenceBuildError(f"duplicate_naics: {code}")
            codes[code] = function["id"]
    if document.get("residual_naics_codes") != ["99"]:
        raise ReferenceBuildError("function_mapping_residual")
    selected = frozenset((*codes, "99"))
    for code in selected:
        for other in selected - {code}:
            if other.startswith(code) or (
                code in basis.SECTORS and basis.parent_sector(other) == code
            ):
                raise ReferenceBuildError(f"overlapping_naics: {code}/{other}")
    return basis.FunctionMapping(document, codes, selected)


def load_mapping_v2(path: Path = MAPPING_V2_PATH) -> basis.FunctionMapping:
    return validate_mapping_v2(json.loads(path.read_bytes(), object_pairs_hook=_unique_object))
