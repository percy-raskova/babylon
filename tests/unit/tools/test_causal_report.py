"""Qualify actual evidence, exact Git identities, and declared baseline changes."""

import hashlib
import json
import subprocess
from pathlib import Path

import pytest
from tools.devtools.causal_report import CASES, qualify, validate_artifacts
from tools.devtools.historical_extract import canonical_bytes


def _git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=repo, text=True).strip()


def _commit(repo: Path, message: str) -> str:
    _git(repo, "add", ".")
    _git(
        repo,
        "-c",
        "user.name=Evidence Test",
        "-c",
        "user.email=evidence@example.invalid",
        "-c",
        "core.hooksPath=/dev/null",
        "commit",
        "-qm",
        message,
    )
    return _git(repo, "rev-parse", "HEAD")


def _evidence(path: Path, head: str) -> None:
    path.mkdir(exist_ok=True)
    cases = []
    for case in CASES:
        delivery, opening = case.split("-")
        experiment = {
            "schema": "SimulationExperimentV1",
            "profile": "delivery_stock",
            "epoch": None,
            "horizon": 16,
            "seed": 319,
            "source_snapshot_sha256": None,
            "starting_snapshot": None,
            "interventions": [
                {"kind": "opening_sheet_stock", "kilograms": int(opening)},
                {"kind": "regional_delivery", "delivery": delivery},
            ],
        }
        resolved = {"horizon": 16, "experiment": experiment, "normalized": {"horizon_ticks": 16}}
        encoded = json.dumps(resolved, sort_keys=True, separators=(",", ":"))
        cases.append(
            {
                "case": case,
                "preset": delivery,
                "opening_sheet_kg": int(opening),
                "experiment": experiment,
                "resolved_defines": resolved,
                "canonical_defines_utf8": encoded,
                "defines_sha256": hashlib.sha256(encoded.encode()).hexdigest(),
            }
        )
    inputs = {"schema": "SimulationExperimentMatrixV1", "periods": 16, "cases": cases}
    summary = {
        "schema": "MichiganDeliveryStockSummaryV1",
        "food_control_equal": True,
        "cases": [
            {
                "case": case,
                "foundation": {"hash": "a" * 64},
                "period_evidence_sha256": "b" * 64,
                "final_subassemblies": 30,
            }
            for case in CASES
        ],
    }
    staffing = {
        "opening_employed": 1,
        "opening_reserve": 1,
        "hires": 0,
        "separations": 0,
        "closing_employed": 1,
        "closing_reserve": 1,
    }
    rows = [
        {
            "schema": "MichiganDeliveryStockPeriodV1",
            "case": case,
            "period": period,
            "world_sha256": "a" * 64,
            "processes": [
                {"process": name, "staffing": staffing}
                for name in [
                    "sheet-rolling",
                    "panel-forming",
                    "subassembly-making",
                    "meal-milling",
                    "meal-packaging",
                ]
            ],
            "routes": [
                {"route": name} for name in ["sheet-transfer", "panel-transfer", "food-transfer"]
            ],
            "metal_input_equivalent_kg": 100,
            "food_kg": 100,
        }
        for case in CASES
        for period in range(1, 17)
    ]
    (path / "inputs.json").write_bytes(canonical_bytes(inputs))
    (path / "summary.json").write_bytes(canonical_bytes(summary))
    (path / "periods.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows))
    manifest = {
        "schema": "MichiganDeliveryStockExperimentManifestV1",
        "status": "complete",
        "inputs": inputs,
        "experiment_digest": hashlib.sha256(
            json.dumps(inputs, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        "files_sha256": {
            name: hashlib.sha256((path / name).read_bytes()).hexdigest()
            for name in ["inputs.json", "summary.json", "periods.jsonl"]
        },
        "provenance": {"source_sha": head, "source_tree_clean": True},
    }
    (path / "manifest.json").write_bytes(canonical_bytes(manifest))


def _refresh(path: Path, name: str) -> None:
    manifest = json.loads((path / "manifest.json").read_text())
    manifest["files_sha256"][name] = hashlib.sha256((path / name).read_bytes()).hexdigest()
    (path / "manifest.json").write_bytes(canonical_bytes(manifest))


def _repo(tmp_path: Path, *, blessed: bool = True) -> tuple[Path, Path, str, str]:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    (repo / "seed.txt").write_text("source")
    base = _commit(repo, "chore: initial source")
    evidence = tmp_path / "evidence"
    _evidence(evidence, base)
    _, baseline = validate_artifacts(evidence)
    baseline_path = repo / "tests/baselines/michigan_causal.json"
    baseline_path.parent.mkdir(parents=True)
    baseline_path.write_bytes(canonical_bytes(baseline))
    head = _commit(
        repo,
        "test(baselines): initial causal baseline\n\nBaselines: blessed(causal-initial)"
        if blessed
        else "test: unblessed baseline",
    )
    _evidence(evidence, head)
    return repo, evidence, base, head


def test_initial_baseline_is_honestly_not_comparable_and_requires_ceremony(tmp_path: Path) -> None:
    repo, evidence, base, head = _repo(tmp_path)
    result = qualify(evidence, repo, base, pr_head_revision=head)
    assert result["accepted"] is True
    assert result["classification"] == "not_comparable"
    assert result["initial_baseline_creation"] is True
    assert result["evaluated_checkout_sha"] == head
    assert result["pr_head_sha"] == head
    assert result["base_sha"] == base


def test_baseline_without_ceremony_cannot_qualify(tmp_path: Path) -> None:
    repo, evidence, base, _ = _repo(tmp_path, blessed=False)
    result = qualify(evidence, repo, base)
    assert result["accepted"] is False
    assert result["classification"] == "unexplained"
    assert result["ceremony_violations"]


def test_implementation_hash_change_preserves_semantic_baseline(tmp_path: Path) -> None:
    repo, evidence, _, head = _repo(tmp_path)
    rows = [json.loads(line) for line in (evidence / "periods.jsonl").read_text().splitlines()]
    for row in rows:
        row["world_sha256"] = "c" * 64
    (evidence / "periods.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows))
    _refresh(evidence, "periods.jsonl")
    result = qualify(evidence, repo, head)
    assert result["accepted"] is True
    assert result["classification"] == "unchanged"


def test_unexplained_behavior_change_fails_even_with_valid_checksums(tmp_path: Path) -> None:
    repo, evidence, _, head = _repo(tmp_path)
    summary = json.loads((evidence / "summary.json").read_text())
    summary["cases"][0]["final_subassemblies"] = 29
    (evidence / "summary.json").write_bytes(canonical_bytes(summary))
    _refresh(evidence, "summary.json")
    result = qualify(evidence, repo, head)
    assert result["accepted"] is False
    assert result["classification"] == "unexplained"
    assert result["behavior_differences"][0]["path"] == "$.summary.cases[0].final_subassemblies"


def test_intentional_behavior_change_needs_committed_matching_ceremony(tmp_path: Path) -> None:
    repo, evidence, _, head = _repo(tmp_path)
    summary = json.loads((evidence / "summary.json").read_text())
    summary["cases"][0]["final_subassemblies"] = 29
    (evidence / "summary.json").write_bytes(canonical_bytes(summary))
    _refresh(evidence, "summary.json")
    _, baseline = validate_artifacts(evidence)
    (repo / "tests/baselines/michigan_causal.json").write_bytes(canonical_bytes(baseline))
    changed_head = _commit(
        repo, "test(baselines): changed result\n\nBaselines: blessed(causal-change)"
    )
    manifest = json.loads((evidence / "manifest.json").read_text())
    manifest["provenance"]["source_sha"] = changed_head
    (evidence / "manifest.json").write_bytes(canonical_bytes(manifest))
    result = qualify(evidence, repo, head)
    assert result["accepted"] is True
    assert result["classification"] == "intentionally_changed"
    assert result["base_baseline_differences"]


def test_corrupt_or_missing_evidence_cannot_become_success(tmp_path: Path) -> None:
    path = tmp_path / "evidence"
    _evidence(path, "a" * 40)
    with (path / "periods.jsonl").open("ab") as stream:
        stream.write(b"{}\n")
    with pytest.raises(ValueError, match="corrupt"):
        validate_artifacts(path)
    _refresh(path, "periods.jsonl")
    with pytest.raises((ValueError, KeyError)):
        validate_artifacts(path)


def test_short_revisions_and_wrong_evaluated_source_refused(tmp_path: Path) -> None:
    repo, evidence, base, head = _repo(tmp_path)
    with pytest.raises(ValueError, match="exact 40"):
        qualify(evidence, repo, base[:12])
    _evidence(evidence, base)
    with pytest.raises(ValueError, match="evaluated checkout"):
        qualify(evidence, repo, head)


def test_synthetic_merge_records_checkout_head_and_updated_base_separately(tmp_path: Path) -> None:
    repo, evidence, original_base, head = _repo(tmp_path)
    _git(repo, "checkout", "-qb", "updated-base", original_base)
    (repo / "independent.txt").write_text("base advanced independently")
    updated_base = _commit(repo, "chore: advance base")
    _git(
        repo,
        "-c",
        "user.name=Evidence Test",
        "-c",
        "user.email=evidence@example.invalid",
        "-c",
        "core.hooksPath=/dev/null",
        "merge",
        "--no-ff",
        "-qm",
        "synthetic merge",
        head,
    )
    evaluated = _git(repo, "rev-parse", "HEAD")
    _evidence(evidence, evaluated)
    result = qualify(evidence, repo, updated_base, pr_head_revision=head)
    assert result["accepted"] is True
    assert result["evaluated_checkout_sha"] == evaluated
    assert result["pr_head_sha"] == head
    assert result["base_sha"] == updated_base
    assert len({evaluated, head, updated_base}) == 3


def test_uncommitted_baseline_cannot_supply_intentional_change(tmp_path: Path) -> None:
    repo, evidence, base, _ = _repo(tmp_path)
    baseline_path = repo / "tests/baselines/michigan_causal.json"
    baseline = json.loads(baseline_path.read_text())
    baseline["summary"]["cases"][0]["final_subassemblies"] = 123
    baseline_path.write_bytes(canonical_bytes(baseline))
    with pytest.raises(ValueError, match="working baseline"):
        qualify(evidence, repo, base)


@pytest.mark.parametrize("failure", ["conservation", "staffing", "food_control", "incomplete"])
def test_receipts_and_complete_execution_are_required_even_with_valid_checksums(
    tmp_path: Path, failure: str
) -> None:
    evidence = tmp_path / "evidence"
    _evidence(evidence, "a" * 40)
    rows = [json.loads(line) for line in (evidence / "periods.jsonl").read_text().splitlines()]
    if failure == "conservation":
        rows[-1]["food_kg"] = 99
    elif failure == "staffing":
        rows[0]["processes"][0]["staffing"]["hires"] = 1
    elif failure == "food_control":
        rows[-1]["processes"][-1]["observed_food"] = 2
    else:
        rows.pop()
    (evidence / "periods.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows))
    _refresh(evidence, "periods.jsonl")
    with pytest.raises(ValueError):
        validate_artifacts(evidence)


def test_causal_cli_has_no_optional_python_dependency(tmp_path: Path) -> None:
    import sys

    result = subprocess.run(
        [sys.executable, "-S", "-m", "tools.devtools.causal_report", "--help"],
        cwd=Path(__file__).resolve().parents[3],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("mutation", ["seed", "parameters", "captured_experiment"])
def test_input_integrity_refuses_altered_seed_or_unbound_resolved_parameters(
    tmp_path: Path, mutation: str
) -> None:
    evidence = tmp_path / "evidence"
    _evidence(evidence, "a" * 40)
    inputs = json.loads((evidence / "inputs.json").read_text())
    case = inputs["cases"][0]
    if mutation == "seed":
        case["experiment"]["seed"] = 999
    elif mutation == "parameters":
        case["resolved_defines"]["horizon"] = 15
    else:
        case["resolved_defines"]["experiment"]["seed"] = 999
        case["canonical_defines_utf8"] = json.dumps(case["resolved_defines"])
        case["defines_sha256"] = hashlib.sha256(case["canonical_defines_utf8"].encode()).hexdigest()
    (evidence / "inputs.json").write_bytes(canonical_bytes(inputs))
    manifest = json.loads((evidence / "manifest.json").read_text())
    manifest["inputs"] = inputs
    manifest["experiment_digest"] = hashlib.sha256(
        json.dumps(inputs, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    (evidence / "manifest.json").write_bytes(canonical_bytes(manifest))
    _refresh(evidence, "inputs.json")
    with pytest.raises(ValueError):
        validate_artifacts(evidence)


def test_unconsumed_source_text_does_not_change_semantic_baseline(tmp_path: Path) -> None:
    evidence = tmp_path / "evidence"
    _evidence(evidence, "a" * 40)
    _, before = validate_artifacts(evidence)
    inputs = json.loads((evidence / "inputs.json").read_text())
    for case in inputs["cases"]:
        case["resolved_defines"]["rule_source"] = "; changed comment only"
        case["resolved_defines"]["defines"] = {"unconsumed_statewide_parameter": 17}
        case["canonical_defines_utf8"] = json.dumps(case["resolved_defines"])
        case["defines_sha256"] = hashlib.sha256(case["canonical_defines_utf8"].encode()).hexdigest()
    (evidence / "inputs.json").write_bytes(canonical_bytes(inputs))
    manifest = json.loads((evidence / "manifest.json").read_text())
    manifest["inputs"] = inputs
    manifest["experiment_digest"] = hashlib.sha256(
        json.dumps(inputs, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    (evidence / "manifest.json").write_bytes(canonical_bytes(manifest))
    _refresh(evidence, "inputs.json")
    _, after = validate_artifacts(evidence)
    assert before == after
