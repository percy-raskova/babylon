"""Qualify the four-case causal experiment against governed semantic baselines.

Normal verification reads the candidate baseline from its exact evaluated Git
revision. A changed baseline requires the repository's existing ceremony gate.
``--capture-baseline`` deliberately only creates a candidate artifact: its later
commit still requires the governed ceremony before normal qualification passes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

from tools.check_baseline_ceremony import check_range

BASELINE_PATH = "tests/baselines/michigan_causal.json"
CASES = ("standard-0", "delayed-0", "standard-320", "delayed-320")
PROCESSES = {
    "sheet-rolling",
    "panel-forming",
    "subassembly-making",
    "meal-milling",
    "meal-packaging",
}
ROUTES = {"sheet-transfer", "panel-transfer", "food-transfer"}
MAX_BYTES = 4 * 1024 * 1024
HEX_SHA = re.compile(r"^[0-9a-f]{40}$")
HEX_DIGEST = re.compile(r"^[0-9a-f]{64}$")


def canonical_bytes(value: object) -> bytes:
    # Keep the required Rust CI report independent of data-analysis dependencies.
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def digest_file(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _validate_case(case: dict[str, Any]) -> None:
    delivery, opening = case["case"].split("-")
    expected = {
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
    experiment = case["experiment"]
    actual = {
        **experiment,
        "interventions": sorted(experiment["interventions"], key=lambda row: row["kind"]),
    }
    if (
        actual != expected
        or type(experiment["seed"]) is not int
        or type(experiment["horizon"]) is not int
        or case["opening_sheet_kg"] != int(opening)
    ):
        raise ValueError("case inputs differ from the admitted fixed delivery/stock experiment")
    encoded = case["canonical_defines_utf8"].encode()
    if (
        hashlib.sha256(encoded).hexdigest() != case["defines_sha256"]
        or _json(encoded) != case["resolved_defines"]
    ):
        raise ValueError("resolved parameters differ from their captured definitions or digest")
    if case["resolved_defines"].get("experiment") != experiment:
        raise ValueError("resolved definitions do not capture the submitted typed experiment")


def _json(raw: str | bytes) -> Any:
    def invalid_number(value: str) -> None:
        raise ValueError(f"nonfinite JSON number: {value}")

    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    return json.loads(raw, parse_constant=invalid_number, object_pairs_hook=unique_object)


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=True)
    return result.stdout.strip()


def _exact_revision(repo: Path, revision: str) -> str:
    if not HEX_SHA.fullmatch(revision):
        raise ValueError("revision must be an exact 40-character Git SHA")
    if _git(repo, "rev-parse", "--verify", revision + "^{commit}") != revision:
        raise ValueError("revision does not resolve to the requested exact commit")
    return revision


def _baseline_at(repo: Path, revision: str, baseline_path: str) -> dict[str, Any] | None:
    paths = _git(repo, "ls-tree", "--name-only", revision, "--", baseline_path).splitlines()
    if not paths:
        return None
    value = _json(_git(repo, "show", f"{revision}:{baseline_path}"))
    if not isinstance(value, dict) or value.get("schema") != "MichiganCausalBaselineV1":
        raise ValueError("baseline schema is not comparable to the current semantic contract")
    return value


def _nonnegative(value: object, field: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{field} must be a nonnegative integer")
    return value


def validate_artifacts(directory: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    required = ("manifest.json", "inputs.json", "summary.json", "periods.jsonl")
    if (directory / "failure.json").exists():
        raise ValueError("experiment retained a failure artifact")
    if sum((directory / name).stat().st_size for name in required) > MAX_BYTES:
        raise ValueError("experiment exceeded its 4 MiB artifact bound")
    manifest = _json((directory / "manifest.json").read_bytes())
    if (
        manifest.get("schema") != "MichiganDeliveryStockExperimentManifestV1"
        or manifest.get("status") != "complete"
    ):
        raise ValueError("experiment manifest must declare complete current-schema evidence")
    checksums = manifest["files_sha256"]
    if set(checksums) != set(required) - {"manifest.json"}:
        raise ValueError("manifest checksum inventory differs from required evidence")
    for name, checksum in checksums.items():
        if not HEX_DIGEST.fullmatch(checksum) or digest_file(directory / name) != checksum:
            raise ValueError(f"corrupt required artifact: {name}")
    inputs = _json((directory / "inputs.json").read_bytes())
    summary = _json((directory / "summary.json").read_bytes())
    rows = [_json(line) for line in (directory / "periods.jsonl").read_bytes().splitlines()]
    if (
        inputs != manifest["inputs"]
        or inputs.get("schema") != "SimulationExperimentMatrixV1"
        or inputs.get("periods") != 16
    ):
        raise ValueError("captured experiment matrix differs from manifest or required horizon")
    compact = json.dumps(inputs, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    if hashlib.sha256(compact).hexdigest() != manifest["experiment_digest"]:
        raise ValueError("manifest experiment digest differs from captured input identity")
    if [r["case"] for r in inputs["cases"]] != list(CASES):
        raise ValueError("captured cases differ from the four-case qualification matrix")
    for case in inputs["cases"]:
        _validate_case(case)
    if (
        summary.get("schema") != "MichiganDeliveryStockSummaryV1"
        or summary.get("food_control_equal") is not True
        or [r["case"] for r in summary["cases"]] != list(CASES)
    ):
        raise ValueError("summary must include complete cases and equal food control")
    expected = [(case, period) for case in CASES for period in range(1, 17)]
    if [(row["case"], row["period"]) for row in rows] != expected:
        raise ValueError("required evidence must contain four complete ordered 16-period cases")
    controls: dict[int, dict[str, Any]] = {}
    totals: dict[str, tuple[int, int]] = {}
    for row in rows:
        if row["schema"] != "MichiganDeliveryStockPeriodV1":
            raise ValueError("unexpected period evidence schema")
        for key, value in row.items():
            if key.endswith("_sha256") and (
                not isinstance(value, str) or not HEX_DIGEST.fullmatch(value)
            ):
                raise ValueError("invalid period provenance digest")
        if {p["process"] for p in row["processes"]} != PROCESSES or len(row["processes"]) != 5:
            raise ValueError("period evidence must contain each authoritative process")
        if {route["route"] for route in row["routes"]} != ROUTES or len(row["routes"]) != 3:
            raise ValueError("period evidence must contain each authoritative route")
        mass = (
            _nonnegative(row["metal_input_equivalent_kg"], "metal mass"),
            _nonnegative(row["food_kg"], "food mass"),
        )
        if row["case"] in totals and totals[row["case"]] != mass:
            raise ValueError("conserved inventory including transit changed across periods")
        totals[row["case"]] = mass
        for process in row["processes"]:
            staffing = process["staffing"]
            for field in (
                "opening_employed",
                "opening_reserve",
                "hires",
                "separations",
                "closing_employed",
                "closing_reserve",
            ):
                _nonnegative(staffing[field], "staffing." + field)
            if (
                staffing["opening_employed"] + staffing["hires"] - staffing["separations"]
                != staffing["closing_employed"]
                or staffing["opening_reserve"] - staffing["hires"] + staffing["separations"]
                != staffing["closing_reserve"]
            ):
                raise ValueError("staffing receipt does not conserve employed and reserve slots")
        food = {
            "processes": [
                p for p in row["processes"] if p["process"] in {"meal-milling", "meal-packaging"}
            ],
            "routes": [r for r in row["routes"] if r["route"] == "food-transfer"],
            "food_kg": row["food_kg"],
        }
        if row["period"] in controls and controls[row["period"]] != food:
            raise ValueError("food control evidence differs across causal cases")
        controls[row["period"]] = food
    projected_inputs = [
        {
            # Only the resolved regional mechanics enter the behavioral baseline.
            # Captured source text, hashes and unused statewide authoring values
            # remain checksum-verified evidence without causing false drift.
            key: value["normalized"] if key == "resolved_defines" else value
            for key, value in case.items()
            if key not in {"canonical_defines_utf8", "defines_sha256"}
        }
        for case in inputs["cases"]
    ]
    projected_summary = {
        **summary,
        "cases": [
            {
                key: value
                for key, value in case.items()
                if key not in {"foundation", "period_evidence_sha256"}
            }
            for case in summary["cases"]
        ],
    }
    projected_rows = [
        {key: value for key, value in row.items() if not key.endswith("_sha256")} for row in rows
    ]
    return manifest, {
        "schema": "MichiganCausalBaselineV1",
        "inputs": {"schema": inputs["schema"], "periods": 16, "cases": projected_inputs},
        "summary": projected_summary,
        "periods": projected_rows,
    }


def differences(before: object, after: object, path: str = "$") -> list[dict[str, Any]]:
    if type(before) is not type(after):
        return [{"path": path, "before": before, "after": after}]
    if isinstance(before, dict) and isinstance(after, dict):
        result = []
        for key in sorted(set(before) | set(after)):
            if key not in before or key not in after:
                result.append(
                    {
                        "path": f"{path}.{key}",
                        "before": before.get(key),
                        "after": after.get(key),
                        "kind": "added" if key not in before else "removed",
                    }
                )
            else:
                result.extend(differences(before[key], after[key], f"{path}.{key}"))
        return result
    if isinstance(before, list) and isinstance(after, list):
        if len(before) != len(after):
            return [{"path": path, "before": before, "after": after, "kind": "length_changed"}]
        return [
            change
            for i, (a, b) in enumerate(zip(before, after, strict=True))
            for change in differences(a, b, f"{path}[{i}]")
        ]
    return [] if before == after else [{"path": path, "before": before, "after": after}]


def qualify(
    directory: Path,
    repo: Path,
    base_revision: str,
    *,
    pr_head_revision: str | None = None,
    baseline_path: str = BASELINE_PATH,
) -> dict[str, Any]:
    if not baseline_path.startswith("tests/baselines/") or ".." in Path(baseline_path).parts:
        raise ValueError("candidate baseline must belong to the governed baseline estate")
    evaluated = _exact_revision(repo, _git(repo, "rev-parse", "HEAD"))
    base = _exact_revision(repo, base_revision)
    pr_head = _exact_revision(repo, pr_head_revision) if pr_head_revision else None
    _git(repo, "merge-base", "--is-ancestor", base, evaluated)
    if pr_head:
        _git(repo, "merge-base", "--is-ancestor", pr_head, evaluated)
    manifest, observed = validate_artifacts(directory)
    if (
        manifest["provenance"]["source_sha"] != evaluated
        or manifest["provenance"]["source_tree_clean"] is not True
    ):
        raise ValueError(
            "experiment evaluated checkout differs from the current exact source revision"
        )
    candidate = _baseline_at(repo, evaluated, baseline_path)
    previous = _baseline_at(repo, base, baseline_path)
    if candidate is None:
        raise ValueError("candidate revision has no committed governed baseline")
    if _json((repo / baseline_path).read_bytes()) != candidate:
        raise ValueError("working baseline differs from the committed evaluated revision")
    unexpected = differences(candidate, observed)
    changed = differences(previous, candidate) if previous is not None else []
    violations = check_range(f"{base}..{evaluated}", repo)
    if unexpected or violations:
        classification, accepted = "unexplained", False
    elif previous is None:
        classification, accepted = "not_comparable", True
    elif changed:
        classification, accepted = "intentionally_changed", True
    else:
        classification, accepted = "unchanged", True
    return {
        "schema": "MichiganCausalQualificationV1",
        "classification": classification,
        "accepted": accepted,
        "initial_baseline_creation": previous is None,
        "comparison_note": "Initial baseline creation: no prior baseline exists at the exact base revision."
        if previous is None
        else "Candidate observations match the committed semantic baseline."
        if not unexpected
        else "Observed behavior differs from the committed candidate baseline.",
        "evaluated_checkout_sha": evaluated,
        "pr_head_sha": pr_head,
        "base_sha": base,
        "baseline_path": baseline_path,
        "manifest_sha256": digest_file(directory / "manifest.json"),
        "candidate_baseline_sha256": hashlib.sha256(canonical_bytes(candidate)).hexdigest(),
        "ceremony_violations": violations,
        "behavior_differences": unexpected,
        "base_baseline_differences": changed,
    }


def write_qualification(result: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "qualification.json").write_bytes(canonical_bytes(result))
    lines = [
        "# Michigan causal qualification",
        "",
        f"Classification: **{result['classification']}**. Required qualification: **{'passed' if result['accepted'] else 'failed'}**.",
        "",
        result["comparison_note"],
        "",
        f"Evaluated checkout: `{result['evaluated_checkout_sha']}`",
        f"PR head: `{result['pr_head_sha'] or 'not a PR run'}`",
        f"Exact base: `{result['base_sha']}`",
        "",
        f"Unexplained behavioral differences: {len(result['behavior_differences'])}. Changes from the base baseline: {len(result['base_baseline_differences'])}.",
        "",
    ]
    lines += [f"- {error}" for error in result["ceremony_violations"]]
    for label, key in [
        ("Unexplained behavior", "behavior_differences"),
        ("Changed baseline", "base_baseline_differences"),
    ]:
        if result[key]:
            lines += ["", f"## {label}", "", "| Field | Before | After |", "|---|---|---|"]
            for change in result[key][:30]:
                values = [
                    str(change[side]).replace("|", "\\|").replace("\n", " ")[:180]
                    for side in ("before", "after")
                ]
                lines.append(f"| `{change['path']}` | {values[0]} | {values[1]} |")
            if len(result[key]) > 30:
                lines += ["", "Remaining differences are retained in `qualification.json`."]
    (output / "summary.md").write_text("\n".join(lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--base-revision")
    parser.add_argument("--pr-head-revision")
    parser.add_argument("--baseline-path", default=BASELINE_PATH)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--capture-baseline", type=Path)
    args = parser.parse_args()
    try:
        if args.capture_baseline:
            _, baseline = validate_artifacts(args.artifacts)
            args.capture_baseline.parent.mkdir(parents=True, exist_ok=True)
            args.capture_baseline.write_bytes(canonical_bytes(baseline))
            print(
                "Candidate baseline captured; a governed ceremony commit is required before qualification."
            )
            return 0
        if not args.base_revision or not args.output:
            parser.error("normal qualification requires --base-revision and --output")
        result = qualify(
            args.artifacts,
            args.repo,
            args.base_revision,
            pr_head_revision=args.pr_head_revision,
            baseline_path=args.baseline_path,
        )
        write_qualification(result, args.output)
        return 0 if result["accepted"] else 2
    except (ValueError, OSError, KeyError, TypeError, subprocess.CalledProcessError) as error:
        if args.output:
            args.output.mkdir(parents=True, exist_ok=True)
            (args.output / "summary.md").write_text(
                f"# Michigan causal qualification failed\n\nRequired evidence failed: {error}\n"
            )
            (args.output / "qualification.json").write_bytes(
                canonical_bytes(
                    {
                        "schema": "MichiganCausalQualificationV1",
                        "classification": "not_comparable",
                        "accepted": False,
                        "error": str(error),
                    }
                )
            )
        print(f"causal qualification failed: {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
