"""Detroit-Windsor administrative RTD control contract."""

from __future__ import annotations

import copy
import hashlib
import json
import re
import subprocess
from collections.abc import Iterator
from pathlib import Path
from typing import cast

import pyarrow as pa  # type: ignore[import-untyped]
import pyarrow.parquet as pq  # type: ignore[import-untyped]
import pytest
import tools.build_detroit_rtd_control as builder
import yaml
from tools.build_detroit_rtd_control import (
    DEFAULT_CASE_ID,
    EXTRACTION_PATH,
    REFERENCE_ONLY,
    RULE_PATH,
    SCENARIO_PATH,
    WORLD_PATH,
    DetroitControlError,
    border_synthesis_draft,
    build_draft,
    control_bytes,
    load_extraction,
    validate_control_draft,
    verify_source_root,
)

from babylon.config.defines import GameDefines, canonical_defines_hash
from babylon.contracts.relational_territory_dossier_v1 import (
    RtdValidationError,
    canonical_draft_bytes,
    parse_draft,
    parse_vector_corpus,
    projection_hash,
    seal_draft,
)

ROOT = Path(__file__).resolve().parents[3]
FIXTURE_DIR = ROOT / "contracts" / "fixtures"
CONTROL_PATH = FIXTURE_DIR / "detroit_windsor_rtd_v1_admin_control.json"
VECTOR_PATH = ROOT / "contracts" / "relational_territory_dossier_v1_vectors.jsonl"
SOURCE_ROOT = Path("/media/user/data/babylon-data/backups/data-artifacts-v7")
HEX64 = re.compile(r"[0-9a-f]{64}")
COUNTIES = ("26163", "26125", "26099")
MAX_WIRE_VALUES = 4_096
MAX_VECTOR_CASES = 256
EXPECTED_PARQUET_COLUMNS = {
    "fact_qcew_county_rollup.parquet": (
        "county_id",
        "time_id",
        "ownership_id",
        "establishments",
        "employment",
        "total_wages_usd",
        "disclosure_code",
        "is_imputed",
    ),
    "fact_lodes_commuter_flow.parquet": (
        "home_county_id",
        "work_county_id",
        "time_id",
        "total_jobs",
    ),
    "fact_census_housing.parquet": (
        "county_id",
        "source_id",
        "tenure_id",
        "time_id",
        "race_id",
        "household_count",
    ),
    "fact_census_rent.parquet": (
        "county_id",
        "source_id",
        "time_id",
        "race_id",
        "median_rent_usd",
    ),
    "fact_census_rent_burden.parquet": (
        "county_id",
        "source_id",
        "burden_id",
        "time_id",
        "race_id",
        "household_count",
    ),
    "fact_coercive_infrastructure.parquet": (
        "county_id",
        "coercive_type_id",
        "source_id",
        "facility_count",
    ),
    "dim_county.parquet": ("county_id", "fips", "state_id", "county_name", "h3_res4"),
    "dim_state.parquet": ("state_id", "state_fips", "state_name", "state_abbrev"),
    "dim_data_source.parquet": (
        "source_id",
        "source_code",
        "source_year",
        "coverage_start_year",
        "coverage_end_year",
    ),
    "dim_time.parquet": ("time_id", "year", "month", "quarter", "is_annual"),
    "dim_ownership.parquet": (
        "ownership_id",
        "own_code",
        "own_title",
        "is_government",
        "is_private",
    ),
    "dim_housing_tenure.parquet": ("tenure_id", "tenure_type"),
    "dim_race.parquet": ("race_id", "race_code", "race_name", "display_order"),
    "dim_rent_burden.parquet": (
        "burden_id",
        "bracket_code",
        "burden_min_pct",
        "is_cost_burdened",
        "is_severely_burdened",
        "bracket_order",
    ),
    "dim_coercive_type.parquet": ("coercive_type_id", "code", "command_chain"),
}


def _control_payload() -> tuple[dict[str, object], str]:
    sealed = json.loads(CONTROL_PATH.read_bytes())
    expected_hash = sealed.pop("projection_hash")
    assert isinstance(expected_hash, str)
    return sealed, expected_hash


def _all_mappings(value: object) -> list[dict[str, object]]:
    found: list[dict[str, object]] = []
    pending = [value]
    for _value_index in range(MAX_WIRE_VALUES):
        if not pending:
            return found
        current = pending.pop()
        if isinstance(current, dict):
            found.append(current)
            children = tuple(current.values())
            if len(pending) + len(children) > MAX_WIRE_VALUES:
                raise AssertionError("wire traversal exceeds fixed test bound")
            pending.extend(children)
        elif isinstance(current, list):
            if len(pending) + len(current) > MAX_WIRE_VALUES:
                raise AssertionError("wire traversal exceeds fixed test bound")
            pending.extend(current)
    raise AssertionError("wire traversal did not terminate within fixed bound")


def _all_identities(value: object) -> list[dict[str, object]]:
    found: list[dict[str, object]] = []
    mappings = _all_mappings(value)
    for mapping_index in range(MAX_WIRE_VALUES):
        if mapping_index == len(mappings):
            return found
        mapping = mappings[mapping_index]
        if set(mapping) == {"domain", "authority", "local_id"}:
            found.append(mapping)
    return found


def _case(case_id: str) -> object:
    cases = parse_vector_corpus(VECTOR_PATH.read_bytes())
    matches = []
    for case_index in range(MAX_VECTOR_CASES):
        if case_index == len(cases):
            break
        if cases[case_index].case_id == case_id:
            matches.append(cases[case_index])
    assert len(matches) == 1
    return matches[0]


def test_detroit_control_parses_and_seals_to_checked_hash() -> None:
    payload, expected_hash = _control_payload()
    draft = parse_draft(payload)
    sealed = seal_draft(draft)
    assert sealed.projection_hash == expected_hash
    assert projection_hash(draft) == expected_hash
    assert draft.audience.value == "ADMIN_MATERIAL"
    assert draft.durability.value == "IN_MEMORY"
    assert draft.fog_policy_digest is None
    assert draft.knowledge_context_digest is None
    assert draft.actor is None
    assert len(draft.focus) == 3
    focus = []
    for focus_index in range(3):
        focus.append(draft.focus[focus_index].local_id)
    assert tuple(focus) == COUNTIES


def test_counties_have_independent_state_nation_and_cz_memberships() -> None:
    payload, _ = _control_payload()
    draft = parse_draft(payload)
    by_county: dict[str, set[tuple[str, str, str, str]]] = {}
    assert len(draft.scale_memberships) == 9
    for membership_index in range(9):
        membership = draft.scale_memberships[membership_index]
        by_county.setdefault(membership.member_ref.local_id, set()).add(
            (
                membership.scale_ref.domain,
                membership.scale_ref.authority,
                membership.scale_ref.local_id,
                membership.membership_kind.value,
            )
        )
    expected = {
        ("state", "census", "26", "ADMINISTRATIVE"),
        ("country", "iso-3166-1-alpha-2", "US", "NATIONAL"),
        ("commuting-zone", "ers", "11600", "COMMUTING_ZONE"),
    }
    assert by_county == dict.fromkeys(COUNTIES, expected)


def test_decision_surface_is_administrative_and_has_no_player_outputs() -> None:
    payload, _ = _control_payload()
    surface = parse_draft(payload).decision_surface
    assert surface.question_id.local_id == "territorial-relations/material-conditions"
    assert surface.action_refs == ()
    assert surface.receipt_refs == ()
    assert surface.archive_subject_refs == ()


def test_control_has_exact_material_facets_and_census_conflicts_only_as_gaps() -> None:
    payload, _ = _control_payload()
    draft = parse_draft(payload)
    assert len(draft.facets) == 23
    metric_ids = []
    for facet_index in range(23):
        metric_ids.append(draft.facets[facet_index].metric_id.local_id)
    assert metric_ids.count("production/qcew-county-establishments") == 3
    assert metric_ids.count("production/qcew-county-employment") == 3
    assert metric_ids.count("production/qcew-county-total-wages-usd") == 3
    assert metric_ids.count("circulation/lodes-county-commuter-total-jobs") == 9
    assert metric_ids.count("carceral/facility-count") == 5
    census = {
        "reproduction/census-housing-households",
        "reproduction/census-median-rent-usd",
        "reproduction/census-rent-burden-households",
    }
    assert census.isdisjoint(metric_ids)
    conflicts = []
    for gap_index in range(20):
        gap = draft.gaps[gap_index]
        if gap.requested_metric_or_relation.local_id in census:
            conflicts.append(gap)
    assert len(conflicts) == 3
    for conflict_index in range(3):
        assert conflicts[conflict_index].status.value == "UNKNOWN"
        assert conflicts[conflict_index].reason_code.value == "PROVENANCE_COORDINATE_CONFLICT"
        assert conflicts[conflict_index].required_producer_or_null == "PER-28"


def test_control_excludes_pre_per21_msa_canada_and_reduction_fields() -> None:
    payload, _ = _control_payload()
    identities = _all_identities(payload)
    for identity_index in range(MAX_WIRE_VALUES):
        if identity_index == len(identities):
            break
        identity = identities[identity_index]
        assert identity["domain"] not in {"h3", "h3-cell"}
        assert identity["local_id"] != "19820"
    draft = parse_draft(payload)
    for flow_index in range(9):
        assert draft.flows[flow_index].destination_ref.authority != "canada"
    mappings = _all_mappings(payload)
    for mapping_index in range(MAX_WIRE_VALUES):
        if mapping_index == len(mappings):
            break
        fields = tuple(mappings[mapping_index])
        for field_index in range(128):
            if field_index == len(fields):
                break
            assert "score" not in fields[field_index]
            assert "stage" not in fields[field_index]


def test_world_identity_recomputes_authoritative_input_digests() -> None:
    identity = json.loads(WORLD_PATH.read_bytes())
    assert identity["verified_tick"] == 1
    assert identity["scenario_digest"] == hashlib.sha256(SCENARIO_PATH.read_bytes()).hexdigest()
    assert identity["rule_digest"] == hashlib.sha256(RULE_PATH.read_bytes()).hexdigest()
    assert identity["template_digest"] == hashlib.sha256(EXTRACTION_PATH.read_bytes()).hexdigest()
    assert identity["definitions_digest"] == canonical_defines_hash(GameDefines.load_default())
    assert HEX64.fullmatch(identity["graph_state_hash"])
    assert HEX64.fullmatch(identity["nominal_world_hash"])
    assert identity["graph_state_hash"] != "0" * 64
    assert identity["nominal_world_hash"] != "0" * 64
    assert identity["graph_state_hash"] != identity["nominal_world_hash"]


def test_builder_check_compares_exact_checked_bytes() -> None:
    assert CONTROL_PATH.read_bytes() == control_bytes()
    result = subprocess.run(
        ["uv", "run", "python", "tools/build_detroit_rtd_control.py", "--check"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_extraction_ledger_is_closed_and_reference_only_set_is_exact() -> None:
    ledger = load_extraction()
    artifacts = ledger["artifacts"]
    gaps = ledger["gaps"]
    assert isinstance(artifacts, list) and len(artifacts) == 19
    assert isinstance(gaps, list) and len(gaps) == 20
    reference_only = []
    for artifact_index in range(19):
        row = artifacts[artifact_index]
        assert isinstance(row, dict)
        if row["verification_mode"] == "REFERENCE_DIGEST_ONLY":
            reference_only.append(row["artifact_id"])
    assert tuple(reference_only) == REFERENCE_ONLY


@pytest.mark.parametrize(
    ("target", "count", "error"),
    [
        ("artifacts", 20, "DETROIT_ARTIFACT_LIMIT"),
        ("gaps", 21, "DETROIT_GAP_LIMIT"),
        ("selectors", 129, "DETROIT_SELECTOR_LIMIT"),
        ("selected_rows", 129, "DETROIT_SELECTED_ROW_LIMIT"),
        ("provenance_locators", 33, "DETROIT_LOCATOR_LIMIT"),
        ("metric_contracts", 129, "DETROIT_METRIC_LIMIT"),
    ],
)
def test_ledger_fixed_bounds_refuse_plus_one(
    tmp_path: Path, target: str, count: int, error: str
) -> None:
    ledger = copy.deepcopy(load_extraction())
    if target in {"artifacts", "gaps"}:
        rows = ledger[target]
        assert isinstance(rows, list)
        rows.append(copy.deepcopy(rows[0]))
    else:
        artifacts = ledger["artifacts"]
        assert isinstance(artifacts, list) and isinstance(artifacts[0], dict)
        replacement: list[object] = []
        for replacement_index in range(129):
            if replacement_index == count:
                break
            replacement.append(
                f"locator-{replacement_index}"
                if target == "provenance_locators"
                else {"index": replacement_index}
            )
        artifacts[0][target] = replacement
    path = tmp_path / "extraction.yaml"
    path.write_text(yaml.safe_dump(ledger, sort_keys=False))
    with pytest.raises(DetroitControlError, match=error):
        load_extraction(path)


def test_ledger_raw_size_alias_duplicate_and_unknown_fields_refuse(tmp_path: Path) -> None:
    oversized = tmp_path / "oversized.yaml"
    oversized.write_bytes(b" " * 1_048_577)
    with pytest.raises(DetroitControlError, match="DETROIT_LEDGER_SIZE"):
        load_extraction(oversized)
    alias = tmp_path / "alias.yaml"
    alias.write_text("schema: &value x\ncopy: *value\n")
    with pytest.raises(DetroitControlError, match="DETROIT_LEDGER_ALIAS"):
        load_extraction(alias)
    duplicate = tmp_path / "duplicate.yaml"
    duplicate.write_text("schema: x\nschema: y\n")
    with pytest.raises(DetroitControlError, match="DETROIT_LEDGER_DUPLICATE_KEY"):
        load_extraction(duplicate)
    ledger = copy.deepcopy(load_extraction())
    ledger["unknown"] = True
    unknown = tmp_path / "unknown.yaml"
    unknown.write_text(yaml.safe_dump(ledger, sort_keys=False))
    with pytest.raises(DetroitControlError, match="DETROIT_LEDGER_UNKNOWN_FIELD"):
        load_extraction(unknown)


def test_duplicate_selector_and_fourth_reference_only_refuse_pre_open() -> None:
    duplicate = copy.deepcopy(load_extraction())
    artifacts = duplicate["artifacts"]
    assert isinstance(artifacts, list) and isinstance(artifacts[0], dict)
    selectors = artifacts[0]["selectors"]
    assert isinstance(selectors, list)
    selectors.append(copy.deepcopy(selectors[0]))
    with pytest.raises(DetroitControlError, match="DETROIT_SELECTOR_DUPLICATE"):
        verify_source_root(Path("/definitely/not/opened"), duplicate)
    fourth = copy.deepcopy(load_extraction())
    rows = fourth["artifacts"]
    assert isinstance(rows, list) and isinstance(rows[6], dict)
    rows[6]["verification_mode"] = "REFERENCE_DIGEST_ONLY"
    with pytest.raises(DetroitControlError, match="DETROIT_ARTIFACT_MODE"):
        verify_source_root(Path("/definitely/not/opened"), fourth)


def test_selected_value_and_cz_mapping_mutations_refuse_without_fixture_writes() -> None:
    originals = (CONTROL_PATH.read_bytes(), EXTRACTION_PATH.read_bytes(), WORLD_PATH.read_bytes())
    ledger = copy.deepcopy(load_extraction())
    artifacts = ledger["artifacts"]
    assert isinstance(artifacts, list) and isinstance(artifacts[0], dict)
    selected = artifacts[0]["selected_rows"]
    assert isinstance(selected, list) and isinstance(selected[0], dict)
    selected[0]["employment"] = 336296
    with pytest.raises(DetroitControlError, match="DETROIT_SOURCE_VALUE"):
        verify_source_root(SOURCE_ROOT, ledger)
    bridge = copy.deepcopy(artifacts[15])
    assert isinstance(bridge, dict)
    mappings = bridge["selected_rows"]
    assert isinstance(mappings, list) and isinstance(mappings[0], dict)
    mappings[0]["cz_id"] = "99999"
    with pytest.raises(DetroitControlError, match="DETROIT_CZ_MAPPING"):
        builder._verify_csv(ROOT / bridge["relative_path"], bridge, 15)  # noqa: SLF001
    _assert_unchanged(originals)


def test_metric_registry_mismatch_refuses_before_source_open() -> None:
    ledger = copy.deepcopy(load_extraction())
    artifacts = ledger["artifacts"]
    assert isinstance(artifacts, list) and isinstance(artifacts[0], dict)
    contracts = artifacts[0]["metric_contracts"]
    assert isinstance(contracts, list) and isinstance(contracts[0], dict)
    contracts[0]["producer"] = "wrong"
    with pytest.raises(DetroitControlError, match="DETROIT_METRIC_REGISTRY"):
        verify_source_root(Path("/definitely/not/opened"), ledger)


@pytest.mark.parametrize(
    ("mutation", "error"),
    [
        ("missing", "DETROIT_METRIC_MISSING"),
        ("extra", "DETROIT_METRIC_EXTRA"),
        ("duplicate", "DETROIT_METRIC_DUPLICATE"),
    ],
)
def test_metric_declarations_are_exact_before_source_open(mutation: str, error: str) -> None:
    ledger = copy.deepcopy(load_extraction())
    artifacts = ledger["artifacts"]
    assert isinstance(artifacts, list)
    qcew = artifacts[0]
    lodes = artifacts[1]
    assert isinstance(qcew, dict) and isinstance(lodes, dict)
    contracts = qcew["metric_contracts"]
    lodes_contracts = lodes["metric_contracts"]
    assert isinstance(contracts, list) and isinstance(lodes_contracts, list)
    if mutation == "missing":
        contracts.pop()
    elif mutation == "extra":
        contracts.append(copy.deepcopy(lodes_contracts[0]))
    else:
        contracts.append(copy.deepcopy(contracts[0]))
    with pytest.raises(DetroitControlError, match=error):
        verify_source_root(Path("/definitely/not/opened"), ledger)


def test_qcew_scan_uses_mutated_ledger_selector() -> None:
    ledger = copy.deepcopy(load_extraction())
    artifacts = ledger["artifacts"]
    assert isinstance(artifacts, list) and isinstance(artifacts[0], dict)
    selectors = artifacts[0]["selectors"]
    assert isinstance(selectors, list) and isinstance(selectors[0], dict)
    selectors[0]["time_id"] = 999
    with pytest.raises(DetroitControlError, match="DETROIT_SOURCE_CARDINALITY"):
        verify_source_root(SOURCE_ROOT, ledger)


@pytest.mark.parametrize(
    ("mutation", "error"),
    [
        ("missing-field", "DETROIT_SELECTOR_FIELDS"),
        ("extra-field", "DETROIT_SELECTOR_FIELDS"),
        ("wrong-type", "DETROIT_SELECTOR_TYPE"),
        ("extra-selector", "DETROIT_SELECTOR_CARDINALITY"),
    ],
)
def test_selector_shape_type_and_cardinality_are_closed_pre_open(mutation: str, error: str) -> None:
    ledger = copy.deepcopy(load_extraction())
    artifacts = ledger["artifacts"]
    assert isinstance(artifacts, list) and isinstance(artifacts[0], dict)
    selectors = artifacts[0]["selectors"]
    assert isinstance(selectors, list) and isinstance(selectors[0], dict)
    if mutation == "missing-field":
        selectors[0].pop("ownership_id")
    elif mutation == "extra-field":
        selectors[0]["unknown"] = 1
    elif mutation == "wrong-type":
        selectors[0]["time_id"] = "28"
    else:
        extra = copy.deepcopy(selectors[0])
        extra["time_id"] = 999
        selectors.append(extra)
    with pytest.raises(DetroitControlError, match=error):
        verify_source_root(Path("/definitely/not/opened"), ledger)


@pytest.mark.parametrize(
    ("mutation", "error"),
    [
        ("artifact-unknown", "DETROIT_ARTIFACT_UNKNOWN_FIELD"),
        ("artifact-missing", "DETROIT_ARTIFACT_UNKNOWN_FIELD"),
        ("metric-unknown", "DETROIT_METRIC_UNKNOWN_FIELD"),
        ("metric-missing", "DETROIT_METRIC_UNKNOWN_FIELD"),
        ("selected-unknown", "DETROIT_SELECTED_ROW_FIELDS"),
        ("selected-missing", "DETROIT_SELECTED_ROW_FIELDS"),
        ("selected-wrong-type", "DETROIT_SELECTED_ROW_TYPE"),
        ("gap-reason", "DETROIT_GAP_SEMANTICS"),
        ("gap-missing", "DETROIT_GAP_FIELDS"),
        ("absolute-path", "DETROIT_ARTIFACT_PATH"),
        ("traversal-path", "DETROIT_ARTIFACT_PATH"),
        ("wrong-relative-path", "DETROIT_ARTIFACT_LAYOUT"),
        ("wrong-mode", "DETROIT_ARTIFACT_MODE"),
    ],
)
def test_nested_ledger_contract_is_closed_pre_open(mutation: str, error: str) -> None:
    ledger = copy.deepcopy(load_extraction())
    artifacts = ledger["artifacts"]
    gaps = ledger["gaps"]
    assert isinstance(artifacts, list) and isinstance(artifacts[0], dict)
    assert isinstance(gaps, list) and isinstance(gaps[0], dict)
    selected = artifacts[0]["selected_rows"]
    contracts = artifacts[0]["metric_contracts"]
    assert isinstance(selected, list) and isinstance(selected[0], dict)
    assert isinstance(contracts, list) and isinstance(contracts[0], dict)
    if mutation == "artifact-unknown":
        artifacts[0]["unknown"] = 1
    elif mutation == "artifact-missing":
        artifacts[0].pop("schema")
    elif mutation == "metric-unknown":
        contracts[0]["unknown"] = 1
    elif mutation == "metric-missing":
        contracts[0].pop("digest")
    elif mutation == "selected-unknown":
        selected[0]["unknown"] = 1
    elif mutation == "selected-missing":
        selected[0].pop("employment")
    elif mutation == "selected-wrong-type":
        selected[0]["employment"] = "336295"
    elif mutation == "gap-reason":
        gaps[0]["reason"] = "MISSING_GOVERNED_PRODUCER"
    elif mutation == "gap-missing":
        gaps[0].pop("producer")
    elif mutation == "absolute-path":
        artifacts[0]["relative_path"] = "/tmp/fact_qcew_county_rollup.parquet"
    elif mutation == "traversal-path":
        artifacts[0]["relative_path"] = "../fact_qcew_county_rollup.parquet"
    elif mutation == "wrong-relative-path":
        artifacts[0]["relative_path"] = "wrong.parquet"
    else:
        artifacts[0]["verification_mode"] = "TRACKED_CSV"
    with pytest.raises(DetroitControlError, match=error):
        verify_source_root(Path("/definitely/not/opened"), ledger)


def test_physical_source_symlink_cannot_escape_root(tmp_path: Path) -> None:
    outside = tmp_path / "outside.parquet"
    outside.write_bytes(b"not parquet")
    source_root = tmp_path / "source"
    source_root.mkdir()
    (source_root / "fact_qcew_county_rollup.parquet").symlink_to(outside)
    with pytest.raises(DetroitControlError, match="DETROIT_ARTIFACT_PATH"):
        verify_source_root(source_root)


def test_parquet_scan_reads_only_required_columns(monkeypatch: pytest.MonkeyPatch) -> None:
    real_parquet_file = pq.ParquetFile
    seen: dict[str, tuple[str, ...]] = {}

    class ParquetFileSpy:
        def __init__(self, path: Path) -> None:
            self._path = path
            self._delegate = real_parquet_file(path)

        @property
        def metadata(self) -> object:
            return cast(object, self._delegate.metadata)

        @property
        def schema_arrow(self) -> pa.Schema:
            return cast(pa.Schema, self._delegate.schema_arrow)

        def iter_batches(
            self,
            *,
            row_groups: list[int],
            batch_size: int,
            columns: list[str] | None = None,
        ) -> Iterator[pa.RecordBatch]:
            seen[self._path.name] = () if columns is None else tuple(columns)
            return cast(
                Iterator[pa.RecordBatch],
                self._delegate.iter_batches(
                    row_groups=row_groups,
                    batch_size=batch_size,
                    columns=columns,
                ),
            )

    monkeypatch.setattr(pq, "ParquetFile", ParquetFileSpy)
    assert verify_source_root(SOURCE_ROOT) == REFERENCE_ONLY
    assert seen == EXPECTED_PARQUET_COLUMNS


def test_exact_source_root_metadata_rows_values_and_bits_verify() -> None:
    assert verify_source_root(SOURCE_ROOT) == REFERENCE_ONLY


def test_default_builder_never_selects_border_opt_in() -> None:
    payload = build_draft(DEFAULT_CASE_ID)
    flows = payload["flows"]
    assert isinstance(flows, list)
    assert len(flows) == 9
    for flow_index in range(9):
        flow = flows[flow_index]
        assert isinstance(flow, dict)
        assert flow.get("flow_kind") != "BORDER_SYNTHESIS"
    with pytest.raises(DetroitControlError, match="DETROIT_DEFAULT_CASE"):
        build_draft("border-synthesis-opt-in")


def test_border_synthesis_vector_is_separate_derived_opt_in() -> None:
    case = _case("border-synthesis-opt-in")
    draft = parse_draft(case.draft)  # type: ignore[attr-defined]
    border = []
    for flow_index in range(10):
        flow = draft.flows[flow_index]
        if flow.flow_kind.value == "BORDER_SYNTHESIS":
            border.append(flow)
    assert len(border) == 1
    assert border[0].origin_ref.model_dump() == {
        "domain": "place",
        "authority": "census",
        "local_id": "2622000",
    }
    assert border[0].destination_ref.model_dump() == {
        "domain": "external",
        "authority": "babylon.rtd.v1",
        "local_id": "canada",
    }
    assert border[0].payload_facets == ()
    provenance = {}
    for provenance_index in range(20):
        row = draft.provenance[provenance_index]
        provenance[row.provenance_id.local_id] = row
    assert provenance["border-synthesis-opt-in"].evidence_class.value == "Derived"
    assert "lodes" not in provenance["border-synthesis-opt-in"].locator.casefold()
    for flow_index in range(10):
        flow = draft.flows[flow_index]
        assert not (
            flow.flow_kind.value == "COMMUTER_JOBS" and flow.destination_ref.local_id == "canada"
        )


def test_admin_control_is_shared_vector_with_independent_checked_bytes() -> None:
    case = _case(DEFAULT_CASE_ID)
    draft = parse_draft(case.draft)  # type: ignore[attr-defined]
    assert canonical_draft_bytes(draft).hex() == case.canonical_utf8_hex  # type: ignore[attr-defined]
    assert projection_hash(draft) == case.projection_hash  # type: ignore[attr-defined]
    rebuilt = validate_control_draft(build_draft())
    assert canonical_draft_bytes(rebuilt) == canonical_draft_bytes(draft)


def _mutated_control() -> tuple[dict[str, object], tuple[bytes, bytes, bytes]]:
    payload, _ = _control_payload()
    originals = (CONTROL_PATH.read_bytes(), EXTRACTION_PATH.read_bytes(), WORLD_PATH.read_bytes())
    return copy.deepcopy(payload), originals


def _assert_unchanged(originals: tuple[bytes, bytes, bytes]) -> None:
    assert originals == (
        CONTROL_PATH.read_bytes(),
        EXTRACTION_PATH.read_bytes(),
        WORLD_PATH.read_bytes(),
    )


@pytest.mark.parametrize(
    ("mutation", "error"),
    [
        ("h3", "RTD_H3_BEFORE_PER21"),
        ("msa", "RTD_MSA_EVIDENCE"),
        ("canada-commuter", "RTD_CANADA_CONTROL"),
        ("weighted-overlap", "RTD_UNSUPPORTED_DOWNSCALE"),
        ("player-action", "RTD_FORBIDDEN_REDUCTION"),
        ("missing-gap", "DETROIT_REQUIRED_GAP"),
        ("extra-gap", "DETROIT_UNREGISTERED_GAP"),
    ],
)
def test_t1_boundary_mutations_refuse_atomically(mutation: str, error: str) -> None:
    payload, originals = _mutated_control()
    _apply_boundary_mutation(payload, mutation)
    if mutation == "extra-gap":
        assert len(payload["gaps"]) == 21  # type: ignore[arg-type]
    expected_error: type[Exception] = (
        DetroitControlError if error.startswith("DETROIT_") else RtdValidationError
    )
    with pytest.raises(expected_error, match=error):
        validate_control_draft(payload)
    _assert_unchanged(originals)


def _apply_boundary_mutation(payload: dict[str, object], mutation: str) -> None:
    if mutation == "h3":
        payload["focus"] = [
            *payload["focus"],  # type: ignore[misc]
            {"domain": "h3-cell", "authority": "h3", "local_id": "8928308280fffff"},
        ]
    elif mutation == "msa":
        membership = copy.deepcopy(payload["scale_memberships"][0])  # type: ignore[index]
        membership["membership_id"]["local_id"] = "msa-mutation"
        membership["scale_ref"] = {"domain": "msa", "authority": "omb", "local_id": "19820"}
        payload["scale_memberships"] = [*payload["scale_memberships"], membership]  # type: ignore[misc]
    elif mutation == "canada-commuter":
        flows = payload["flows"]
        assert isinstance(flows, list) and isinstance(flows[0], dict)
        flows[0]["destination_ref"] = {
            "domain": "external",
            "authority": "babylon.rtd.v1",
            "local_id": "canada",
        }
    elif mutation == "weighted-overlap":
        payload["scale_memberships"][0]["membership_kind"] = "WEIGHTED_OVERLAP"  # type: ignore[index]
    elif mutation == "player-action":
        payload["decision_surface"]["action_refs"] = [payload["focus"][0]]  # type: ignore[index]
    elif mutation == "missing-gap":
        payload["gaps"] = payload["gaps"][:-1]  # type: ignore[index]
    elif mutation == "extra-gap":
        extra = copy.deepcopy(payload["gaps"][0])  # type: ignore[index]
        extra["gap_id"]["local_id"] = "unregistered-twenty-first"
        payload["gaps"] = [*payload["gaps"], extra]  # type: ignore[misc]
    else:
        raise AssertionError(mutation)


def test_border_builder_helper_matches_shared_vector() -> None:
    expected = parse_draft(border_synthesis_draft())
    case = _case("border-synthesis-opt-in")
    actual = parse_draft(case.draft)  # type: ignore[attr-defined]
    assert canonical_draft_bytes(expected) == canonical_draft_bytes(actual)
