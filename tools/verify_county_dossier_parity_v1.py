#!/usr/bin/env python3
"""Independently verify the bounded CountyDossierParityV1 contract corpus.

Language-neutral cross-check of the PER-22 county dossier golden-parity
vectors (contracts/county_dossier_parity_v1.yaml + _vectors.jsonl). The
Python oracle (``babylon.projection.county.project_county``) generated the
checked expectations; this verifier re-derives every display value from the
pinned binary64 bits, re-applies the grant-filtering rule, and refuses typed
drift without importing any production module. The Rust producer's matching
obligation lives in
rust/crates/babylon-persistence/tests/county_dossier_parity_vectors.rs.
"""

from __future__ import annotations

import argparse
import json
import math
import struct
from pathlib import Path
from typing import Any

import yaml

MEDIAN_WAGE_GRANT_KEY = "median-wage"
MEDIAN_WAGE_LABEL = "Median wage"
PHI_HOUR_GRANT_KEY = "phi-hour"
PHI_HOUR_LABEL = "Imperial rent Φ"
COUNTY_SUBJECT_GRANT_KEY = "subject"
CITATION_SOURCE_ID = "committed-tick-v1"
STATBLOCK_FORMAT = "%.6f"
DECISION_QUESTION = "Which neighboring place should organizers investigate next?"
NEGATIVE_ZERO_BITS = "8000000000000000"
CANONICAL_ZERO_DISPLAY = "0.000000"
COMPILED_META = {
    "contract": "CountyDossierParityV1",
    "version": 1,
    "issue": "PER-22",
    "byte_order": "big-endian",
    "oracle": "babylon.projection.county.project_county (src/babylon/projection/county.py)",
    "digest": (
        "value identity is exact binary64 bits; display parity is the canonical %.6f statblock text"
    ),
}
COMPILED_CONSTANTS = {
    "oracle_graph_attributes": ["tick_median_wage", "tick_phi_hour"],
    "committed_field_names": [MEDIAN_WAGE_GRANT_KEY, PHI_HOUR_GRANT_KEY],
    "county_subject_grant_key": COUNTY_SUBJECT_GRANT_KEY,
    "median_wage_grant_key": MEDIAN_WAGE_GRANT_KEY,
    "median_wage_label": MEDIAN_WAGE_LABEL,
    "phi_hour_grant_key": PHI_HOUR_GRANT_KEY,
    "phi_hour_label": PHI_HOUR_LABEL,
    "citation_source_id": CITATION_SOURCE_ID,
    "citation_locator_form": "campaign/{resolve_tick}/{territory_local_name}",
    "decision_question": DECISION_QUESTION,
    "statblock_format": STATBLOCK_FORMAT,
    "oracle_snap_grid": "1e-6 ROUND_HALF_UP (babylon.kernel.math.quantize)",
    "negative_zero_bits": NEGATIVE_ZERO_BITS,
    "canonical_zero_display": CANONICAL_ZERO_DISPLAY,
}
COMPILED_BOUNDS = {
    "contract_bytes": 32768,
    "vector_rows": 16,
    "vector_line_bytes": 16384,
    "vector_object_fields": 64,
    "max_links_per_county": 64,
    "county_geoid_bytes": 5,
    "place_geoid_bytes": 7,
    "max_tick": (1 << 63) - 1,
}
COMPILED_LAYOUTS = {
    "committed_field_v1": {
        "fields": ["median_wage_bits_hex16_or_null", "phi_hour_bits_hex16_or_null"],
        "encoding": "big-endian u64 binary64 bits, lowercase hex",
    },
    "vector_row_v1": {
        "fields": ["id", "kind=parity", "data"],
        "order": "exact scenario order",
    },
    "county_view_expectation_v1": {
        "present_fields": ["verified_tick", "median_wage_bits", "phi_hour_bits"],
        "absent_fields": [
            "population",
            "class_composition",
            "consciousness",
            "legitimacy",
            "p_acquiescence",
            "p_revolution",
            "bifurcation_score",
            "habitability",
            "sovereign_id",
        ],
        "reason": "Director ruling D2 (absence-maximal): only median-wage and phi-hour have committed sources",
    },
    "signal_v1": {
        "fields": ["grant_key", "label", "value"],
        "value": "canonical %.6f statblock of the committed bits; -0.0 -> 0.0",
        "order": "sorted by grant key",
    },
    "plan_signal_v1": {
        "fields": ["grant_key", "label", "value"],
        "detail": (
            "every committed field present at the tick, before grant "
            "filtering; the plan carries these even when a grant redacts "
            "them from the page"
        ),
    },
    "place_v1": {
        "fields": ["place_geoid", "known_name_or_null"],
        "order": "sorted by place GEOID",
        "known_name": "present only while the place subject grant covers the GEOID",
    },
}
COUNTY_VIEW_ABSENT_FIELDS = tuple(COMPILED_LAYOUTS["county_view_expectation_v1"]["absent_fields"])
LOWER_HEX = frozenset("0123456789abcdef")
REQUIRED_VECTOR_IDS = (
    "parity-wayne-normal",
    "parity-oakland-zero-wage",
    "parity-wayne-negative-zero",
    "parity-oakland-absent-phi",
    "parity-wayne-field-grant-redacted",
    "parity-wayne-place-redlink",
)


class CountyDossierParityRefusal(ValueError):
    """One typed independent-verifier refusal."""

    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def _bounded_file_bytes(path: Path, maximum: int, code: str) -> bytes:
    try:
        size = path.stat().st_size
    except OSError as error:
        raise CountyDossierParityRefusal("file_read", str(path)) from error
    if size > maximum:
        raise CountyDossierParityRefusal(code, str(size))
    try:
        return path.read_bytes()
    except OSError as error:
        raise CountyDossierParityRefusal("file_read", str(path)) from error


class _UniqueKeySafeLoader(yaml.SafeLoader):
    """SafeLoader that refuses duplicate mapping keys with a typed refusal."""


def _construct_unique_mapping(loader: yaml.SafeLoader, node: yaml.MappingNode) -> dict[str, Any]:
    mapping: dict[str, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=True)
        try:
            duplicate = key in mapping
        except TypeError as error:
            raise CountyDossierParityRefusal("invalid_schema", "unhashable key") from error
        if duplicate:
            raise CountyDossierParityRefusal("invalid_schema", f"duplicate key: {key}")
        mapping[key] = loader.construct_object(value_node, deep=True)
    return mapping


_UniqueKeySafeLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


def load_contract(path: Path) -> dict[str, Any]:
    """Load one bounded YAML mapping, refusing duplicate keys as typed drift."""
    raw = _bounded_file_bytes(path, COMPILED_BOUNDS["contract_bytes"], "schema_too_large")
    try:
        loaded = yaml.load(raw, Loader=_UniqueKeySafeLoader)  # noqa: S506
    except CountyDossierParityRefusal:
        raise
    except yaml.YAMLError as error:
        raise CountyDossierParityRefusal("invalid_schema", str(path)) from error
    if not isinstance(loaded, dict):
        raise CountyDossierParityRefusal("invalid_schema", "root mapping")
    return loaded


def load_vectors(path: Path) -> list[dict[str, Any]]:
    """Load bounded JSONL rows without an unbounded whole-file read."""
    maximum = COMPILED_BOUNDS["vector_rows"] * (COMPILED_BOUNDS["vector_line_bytes"] + 1)
    raw = _bounded_file_bytes(path, maximum, "vectors_too_large")
    lines = raw.splitlines()
    if len(lines) > COMPILED_BOUNDS["vector_rows"]:
        raise CountyDossierParityRefusal("too_many_rows", str(len(lines)))
    rows: list[dict[str, Any]] = []
    for index in range(COMPILED_BOUNDS["vector_rows"]):
        if index >= len(lines):
            break
        line = lines[index]
        if not line or len(line) > COMPILED_BOUNDS["vector_line_bytes"]:
            raise CountyDossierParityRefusal("invalid_line_length", str(index + 1))
        try:
            row = json_loads_unique(line)
        except CountyDossierParityRefusal:
            raise
        except (ValueError, UnicodeDecodeError) as error:
            raise CountyDossierParityRefusal("invalid_json", str(index + 1)) from error
        if not isinstance(row, dict):
            raise CountyDossierParityRefusal("vector_row_shape", str(index + 1))
        rows.append(row)
    return rows


def json_loads_unique(line: str) -> Any:
    """Parse one JSONL line refusing duplicate keys and oversized objects."""

    def object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        if len(pairs) > COMPILED_BOUNDS["vector_object_fields"]:
            raise CountyDossierParityRefusal("json_object_fields", str(len(pairs)))
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise CountyDossierParityRefusal("duplicate_json_key", key)
            result[key] = value
        return result

    return json.loads(line, object_pairs_hook=object_pairs)


def _verify_compiled_contract(contract: dict[str, Any]) -> None:
    if contract.get("meta") != COMPILED_META:
        raise CountyDossierParityRefusal("compiled_contract_drift", "meta")
    if contract.get("constants") != COMPILED_CONSTANTS:
        raise CountyDossierParityRefusal("compiled_contract_drift", "constants")
    if contract.get("bounds") != COMPILED_BOUNDS:
        raise CountyDossierParityRefusal("compiled_contract_drift", "bounds")
    if contract.get("layouts") != COMPILED_LAYOUTS:
        raise CountyDossierParityRefusal("compiled_contract_drift", "layouts")
    if contract.get("production_decoder") != "prohibited":
        raise CountyDossierParityRefusal("compiled_contract_drift", "production_decoder")
    required = contract.get("vector_kinds")
    if not isinstance(required, dict):
        raise CountyDossierParityRefusal("invalid_schema", "vector_kinds")
    if required.get("required") != ["parity"]:
        raise CountyDossierParityRefusal("compiled_contract_drift", "vector_kinds")
    divergences = contract.get("known_divergences")
    if not isinstance(divergences, list) or len(divergences) != 1:
        raise CountyDossierParityRefusal("compiled_contract_drift", "known_divergences")
    divergence = divergences[0]
    if not isinstance(divergence, dict):
        raise CountyDossierParityRefusal("invalid_schema", "known_divergences[0]")
    if divergence.get("id") != "oracle-snap-to-grid":
        raise CountyDossierParityRefusal("compiled_contract_drift", "known_divergences")


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise CountyDossierParityRefusal("invalid_text", field)
    if "\x00" in value:
        raise CountyDossierParityRefusal("invalid_text", field)
    return value


def _geoid(value: object, field: str, width: int) -> str:
    if (
        not isinstance(value, str)
        or len(value) != width
        or not value.isascii()
        or not value.isdigit()
    ):
        raise CountyDossierParityRefusal("invalid_geoid", field)
    return value


def _bits(value: object, field: str) -> str | None:
    if value is None:
        return None
    if (
        not isinstance(value, str)
        or len(value) != 16
        or any(char not in LOWER_HEX for char in value)
    ):
        raise CountyDossierParityRefusal("invalid_bits", field)
    return value


def decode_bits(bits: str | None) -> float | None:
    """Decode one pinned bit pattern, refusing a non-finite committed value."""
    if bits is None:
        return None
    value = struct.unpack(">d", bytes.fromhex(bits))[0]
    if not math.isfinite(value):
        raise CountyDossierParityRefusal("non_finite_value", bits)
    return value


def encode_bits(value: float | None) -> str | None:
    """Encode one binary64 as big-endian bit hex, or pass absence on."""
    if value is None:
        return None
    return struct.pack(">d", value).hex()


def oracle_snap(value: float) -> float:
    """Mirror of the oracle's SnapToGrid quantization (1e-6 grid, ROUND_HALF_UP).

    Both committed CountyView fields are SnapToGrid model types, so the oracle
    projects ``quantize(value)``; see ``babylon.kernel.math.quantize``. A
    committed value that is not a fixed point of this quantization is outside
    the bit-parity claim (the contract's known divergence) and refuses here.
    """
    if value == 0.0:
        return 0.0
    scaled = value * 1_000_000
    if not math.isfinite(scaled):
        raise CountyDossierParityRefusal(
            "value_out_of_domain", "committed value overflows the snap grid"
        )
    if value > 0:
        return math.floor(scaled + 0.5) / 1_000_000
    return -math.floor(-scaled + 0.5) / 1_000_000


def canonical_statblock(value: float) -> str:
    """The contract's canonical ``%.6f`` display: -0.0 canonicalizes to 0.0."""
    if value == 0.0:
        value = 0.0
    return f"{value:.6f}"


def _tick(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise CountyDossierParityRefusal("invalid_tick", field)
    if value <= 0 or value > COMPILED_BOUNDS["max_tick"]:
        raise CountyDossierParityRefusal("invalid_tick", field)
    return value


def _validated_rows(vectors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if len(vectors) > COMPILED_BOUNDS["vector_rows"]:
        raise CountyDossierParityRefusal("too_many_rows", str(len(vectors)))
    seen_ids: set[str] = set()
    for index, row in enumerate(vectors):
        row_id = row.get("id")
        if (
            set(row) != {"id", "kind", "data"}
            or not isinstance(row_id, str)
            or not row_id
            or row.get("kind") != "parity"
            or not isinstance(row.get("data"), dict)
        ):
            raise CountyDossierParityRefusal("vector_row_shape", str(index + 1))
        if row_id in seen_ids:
            raise CountyDossierParityRefusal("duplicate_vector_id", row_id)
        seen_ids.add(row_id)
    return vectors


def _data(data: Any, field: str) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise CountyDossierParityRefusal("invalid_data", field)
    return data


HARD_REFUSAL_CODES = frozenset({"invalid_key_set", "value_out_of_domain"})


def _exact_keys(value: Any, field: str, required: tuple[str, ...]) -> dict[str, Any]:
    """Require one mapping whose key set equals the pinned key set exactly."""
    if not isinstance(value, dict) or set(value) != set(required):
        raise CountyDossierParityRefusal("invalid_key_set", field)
    return value


def _validate_row(row: dict[str, Any]) -> str | None:
    """Re-derive one row's expectations from its inputs; None means parity held.

    A missing member is not an explicit null and a stray nested key is drift
    even when every required member matches, so every pinned key set is
    enforced exactly; those refusals (and out-of-domain committed values)
    propagate as typed hard refusals instead of row-scoped mismatch strings.
    """
    row_id = row["id"]
    data = _data(row["data"], "data")
    try:
        _exact_keys(
            data,
            "data",
            (
                "county_geoid",
                "territory_local_name",
                "title",
                "tick",
                "committed",
                "grants",
                "links",
                "expected",
            ),
        )
        _geoid(data.get("county_geoid"), "county_geoid", COMPILED_BOUNDS["county_geoid_bytes"])
        _text(data.get("territory_local_name"), "territory_local_name")
        _text(data.get("title"), "title")
        tick = _tick(data.get("tick"), "tick")
        committed = _exact_keys(
            data.get("committed"), "committed", ("median_wage_bits", "phi_hour_bits")
        )
        median_bits = _bits(committed.get("median_wage_bits"), "committed.median_wage_bits")
        phi_bits = _bits(committed.get("phi_hour_bits"), "committed.phi_hour_bits")
        median = decode_bits(median_bits)
        phi = decode_bits(phi_bits)
        # Domain: CountyView.median_wage is the non-negative Currency type
        # (src/babylon/projection/view_models.py); imperial_rent_phi is the
        # signed SignedLaborHours type, so a negative phi stays in-domain.
        if median is not None and median < 0.0:
            raise CountyDossierParityRefusal("value_out_of_domain", "median_wage_bits")
        grants = _exact_keys(
            data.get("grants"), "grants", ("county_subject", "field_keys", "place_subjects")
        )
        county_subject = grants.get("county_subject")
        field_keys = _string_list(grants.get("field_keys"), "grants.field_keys")
        place_subjects = _string_list(grants.get("place_subjects"), "grants.place_subjects")
        links = _links(data.get("links"))
        expected = _exact_keys(
            data.get("expected"), "expected", ("county_view", "plan_signals", "signals", "places")
        )
        for field in ("places", "signals", "plan_signals"):
            entries = expected.get(field)
            if not isinstance(entries, list):
                continue  # the parity comparison below reports the mismatch
            entry_keys = (
                ("place_geoid", "known_name")
                if field == "places"
                else ("grant_key", "label", "value")
            )
            for index, entry in enumerate(entries):
                _exact_keys(entry, f"{field}[{index}]", entry_keys)
        county_view = _exact_keys(
            expected.get("county_view"),
            "county_view",
            ("verified_tick", "median_wage_bits", "phi_hour_bits", *COUNTY_VIEW_ABSENT_FIELDS),
        )
    except CountyDossierParityRefusal as error:
        if error.code in HARD_REFUSAL_CODES:
            raise
        return f"{row_id}: {error.code} {error.detail}"
    if county_subject is not True:
        return f"{row_id}: parity vectors pin the county subject grant present"
    known_fields = set(field_keys)
    if known_fields - {MEDIAN_WAGE_GRANT_KEY, PHI_HOUR_GRANT_KEY}:
        return f"{row_id}: unknown field grant key"
    granted_places = set(place_subjects)
    for geoid_field in granted_places:
        if geoid_field not in {link[0] for link in links}:
            return f"{row_id}: place subject grant {geoid_field} has no link"
    # Grid scope first: the oracle's SnapToGrid quantization is the contract's
    # known divergence, and an off-grid committed value refuses here before any
    # derived display value is compared.
    snapped: dict[str, float] = {}
    for name, value in (("median_wage", median), ("phi_hour", phi)):
        if value is None:
            continue
        snapped[name] = oracle_snap(value)
        if snapped[name] != value:
            return f"{row_id}: off-grid committed value: {name}"
    # Signal parity: every committed field renders into the plan; grants filter
    # the visible list. The plan level pins each formatted value cross-language
    # even when a grant redacts it from the rendered page.
    derived_plan = []
    derived_visible = []
    for grant_key, label, value in (
        (MEDIAN_WAGE_GRANT_KEY, MEDIAN_WAGE_LABEL, median),
        (PHI_HOUR_GRANT_KEY, PHI_HOUR_LABEL, phi),
    ):
        if value is None:
            continue
        signal = {
            "grant_key": grant_key,
            "label": label,
            "value": canonical_statblock(value),
        }
        derived_plan.append(signal)
        if grant_key in known_fields:
            derived_visible.append(signal)
    if expected.get("plan_signals") != derived_plan:
        return f"{row_id}: plan signal parity mismatch"
    if expected.get("signals") != derived_visible:
        return f"{row_id}: signal parity mismatch"
    # Place parity: links sorted by GEOID; known_name follows the subject grant.
    derived_places = [
        {
            "place_geoid": link_geoid,
            "known_name": link_name if link_geoid in granted_places else None,
        }
        for link_geoid, link_name in links
    ]
    if expected.get("places") != derived_places:
        return f"{row_id}: place parity mismatch"
    # Oracle-side expectation: the oracle projects the SnapToGrid-quantized
    # value (both committed fields are SnapToGrid types), so county_view bits
    # follow quantize(committed); the grid fixed-point check above already
    # refused the known off-grid divergence. The exact county_view key set
    # (including every D2-null member) was enforced before this block.
    for name, value in (("median_wage", median), ("phi_hour", phi)):
        if value is None:
            if county_view.get(f"{name}_bits") is not None:
                return f"{row_id}: county_view {name}_bits drift"
            continue
        if county_view.get(f"{name}_bits") != encode_bits(snapped[name]):
            return f"{row_id}: county_view {name}_bits drift"
    if county_view.get("verified_tick") != tick:
        return f"{row_id}: county_view verified_tick drift"
    for field in COUNTY_VIEW_ABSENT_FIELDS:
        if county_view.get(field) is not None:
            return f"{row_id}: county_view {field} must be null under D2"
    # The negative-zero case must be exercised, not vacuous: the committed
    # sign bit differs from the canonicalized oracle bits and both sides of
    # the parity claim display the canonical zero.
    if median_bits == NEGATIVE_ZERO_BITS:
        if county_view.get("median_wage_bits") != "0" * 16:
            return f"{row_id}: negative-zero county_view bits must canonicalize"
        if canonical_statblock(median) != CANONICAL_ZERO_DISPLAY:
            return f"{row_id}: canonical -0.0 display drift"
    return None


def _string_list(value: object, field: str) -> list[str]:
    if not isinstance(value, list):
        raise CountyDossierParityRefusal("invalid_grants", field)
    result = []
    for index, item in enumerate(value):
        result.append(_text(item, f"{field}[{index}]"))
    if len(set(result)) != len(result):
        raise CountyDossierParityRefusal("duplicate_grant_key", field)
    return result


def _links(value: object) -> list[tuple[str, str]]:
    if not isinstance(value, list) or len(value) > COMPILED_BOUNDS["max_links_per_county"]:
        raise CountyDossierParityRefusal("invalid_links", "links")
    links = []
    seen: set[str] = set()
    for index, link in enumerate(value):
        _exact_keys(link, f"links[{index}]", ("place_geoid", "place_name"))
        geoid = _geoid(
            link.get("place_geoid"),
            f"links[{index}].place_geoid",
            COMPILED_BOUNDS["place_geoid_bytes"],
        )
        if geoid in seen:
            raise CountyDossierParityRefusal("duplicate_link", f"links[{index}]")
        seen.add(geoid)
        links.append((geoid, _text(link.get("place_name"), f"links[{index}].place_name")))
    if [geoid for geoid, _ in links] != sorted(geoid for geoid, _ in links):
        raise CountyDossierParityRefusal("invalid_link_order", "links")
    return links


def verify_all(contract: dict[str, Any], vectors: list[dict[str, Any]]) -> list[str]:
    """Verify all bounded rows, returning row-scoped mismatches.

    Structural drift (a non-exact nested key set, an out-of-domain committed
    value) refuses as a typed CountyDossierParityRefusal instead of a string.
    """
    _verify_compiled_contract(contract)
    rows = _validated_rows(vectors)
    ids = [row["id"] for row in rows]
    if ids != list(REQUIRED_VECTOR_IDS):
        raise CountyDossierParityRefusal("vector_id_drift", repr(ids))
    errors: list[str] = []
    for row in rows:
        error = _validate_row(row)
        if error is not None:
            errors.append(error)
    return errors


def main() -> int:
    """Verify repository contract paths or explicit alternatives."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--schema",
        type=Path,
        default=Path("contracts/county_dossier_parity_v1.yaml"),
    )
    parser.add_argument(
        "--vectors",
        type=Path,
        default=Path("contracts/county_dossier_parity_v1_vectors.jsonl"),
    )
    arguments = parser.parse_args()
    try:
        errors = verify_all(load_contract(arguments.schema), load_vectors(arguments.vectors))
    except CountyDossierParityRefusal as error:
        print(error)
        return 1
    for error in errors:
        print(error)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
