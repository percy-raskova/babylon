#!/usr/bin/env python3
"""Check, apply, or roll back Babylon's GitHub pull-request policy."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from typing import Protocol, cast
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.pr_policy import DEV_BLOCKING_CONTEXTS  # noqa: E402

REPOSITORY = "percy-raskova/babylon"
REPOSITORY_ENDPOINT = f"repos/{REPOSITORY}"
RULESETS_ENDPOINT = f"{REPOSITORY_ENDPOINT}/rulesets?includes_parents=false&per_page=100"
DEV_RULESET_ENDPOINT = f"{REPOSITORY_ENDPOINT}/rulesets/{{ruleset_id}}"
DEV_REF_ENDPOINT = f"{REPOSITORY_ENDPOINT}/git/ref/heads/dev"
LABELS_ENDPOINT = f"{REPOSITORY_ENDPOINT}/labels"
LABELS_LIST_ENDPOINT = f"{LABELS_ENDPOINT}?per_page=100"
CHECK_RUNS_ENDPOINT = f"{REPOSITORY_ENDPOINT}/commits/{{sha}}/check-runs?per_page=100"
DEFAULT_POLICY_PATH = Path(".github/settings/pr-policy.json")

MAX_RULESETS = 100
MAX_LABELS = 100
MAX_CHECK_RUNS = 100
API_TIMEOUT_SECONDS = 30
SHA_PATTERN = re.compile(r"[0-9a-f]{40}")
CANONICAL_AUTOMERGE_LABEL = "dependencies:automerge"
_UNKNOWN = object()

RULESET_WRITABLE_FIELDS = (
    "name",
    "target",
    "enforcement",
    "bypass_actors",
    "conditions",
    "rules",
)
REPOSITORY_POLICY_FIELDS = (
    "allow_merge_commit",
    "allow_squash_merge",
    "allow_rebase_merge",
    "allow_auto_merge",
    "delete_branch_on_merge",
)
LABEL_FIELDS = ("name", "color", "description")


class PolicyError(RuntimeError):
    """The requested policy transition is unsafe or unverifiable."""


class GitHubApiError(RuntimeError):
    """A GitHub CLI request failed or returned malformed JSON."""


class Api(Protocol):
    """Minimal GitHub API surface used by the transaction."""

    def get_json(self, endpoint: str) -> object: ...

    def send_json(self, method: str, endpoint: str, payload: dict[str, object]) -> object: ...


class GhApi:
    """GitHub API adapter implemented through the authenticated ``gh`` CLI."""

    @staticmethod
    def _run(args: list[str], input_text: str | None = None) -> str:
        try:
            result = subprocess.run(
                ["gh", "api", *args],
                input=input_text,
                capture_output=True,
                text=True,
                check=True,
                timeout=API_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired as error:
            raise GitHubApiError(f"gh api timed out after {API_TIMEOUT_SECONDS} seconds") from error
        except subprocess.CalledProcessError as error:
            detail = error.stderr.strip() or error.stdout.strip() or f"exit {error.returncode}"
            raise GitHubApiError(f"gh api failed: {detail}") from error
        except OSError as error:
            raise GitHubApiError(f"gh api could not start: {error}") from error
        return result.stdout

    def get_json(self, endpoint: str) -> object:
        output = self._run([endpoint])
        try:
            return json.loads(output)
        except json.JSONDecodeError as error:
            raise GitHubApiError(f"gh api returned invalid JSON for {endpoint}") from error

    def send_json(self, method: str, endpoint: str, payload: dict[str, object]) -> object:
        args = ["--method", method, endpoint]
        input_text: str | None = None
        if method != "DELETE":
            args.extend(["--input", "-"])
            input_text = json.dumps(payload, sort_keys=True)
        output = self._run(args, input_text)
        if not output.strip():
            return {}
        try:
            return json.loads(output)
        except json.JSONDecodeError as error:
            raise GitHubApiError(f"gh api returned invalid JSON for {method} {endpoint}") from error


def _object(value: object, description: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise PolicyError(f"{description} must be a JSON object")
    return cast(dict[str, object], value)


def _objects(value: object, description: str, maximum: int) -> list[dict[str, object]]:
    if not isinstance(value, list):
        raise PolicyError(f"{description} must be a JSON array")
    if len(value) >= maximum:
        raise PolicyError(f"{description} reached the {maximum}-item safety bound")
    if not all(isinstance(item, dict) for item in value):
        raise PolicyError(f"{description} contains a non-object item")
    return cast(list[dict[str, object]], value)


def _select_fields(payload: dict[str, object], fields: tuple[str, ...]) -> dict[str, object]:
    missing = [field for field in fields if field not in payload]
    if missing:
        raise PolicyError(f"GitHub payload is missing required field(s): {missing}")
    return {field: deepcopy(payload[field]) for field in fields}


def normalize_ruleset(payload: dict[str, object]) -> dict[str, object]:
    """Return only fields accepted by GitHub's ruleset update endpoint."""
    return _select_fields(payload, RULESET_WRITABLE_FIELDS)


def normalize_repository(payload: dict[str, object]) -> dict[str, object]:
    """Return only repository merge-policy fields owned by PER-264."""
    return _select_fields(payload, REPOSITORY_POLICY_FIELDS)


def normalize_label(payload: dict[str, object]) -> dict[str, object]:
    """Return the stable label fields owned by PER-264."""
    return _select_fields(payload, LABEL_FIELDS)


def _canonical_label(payload: dict[str, object], description: str) -> dict[str, object]:
    label = normalize_label(payload)
    if label["name"] != CANONICAL_AUTOMERGE_LABEL:
        raise PolicyError(f"{description} must use the canonical automerge label")
    return label


def label_endpoint(name: str) -> str:
    """Return the endpoint for one exact label name."""
    return f"{REPOSITORY_ENDPOINT}/labels/{quote(name, safe='')}"


def load_policy(path: Path = DEFAULT_POLICY_PATH) -> dict[str, object]:
    """Load and minimally validate the checked-in desired policy."""
    try:
        raw = json.loads(path.read_text())
    except OSError as error:
        raise PolicyError(f"cannot read policy {path}: {error}") from error
    except json.JSONDecodeError as error:
        raise PolicyError(f"policy {path} is not valid JSON") from error
    policy = _object(raw, "policy")
    _object(policy.get("repository"), "policy.repository")
    _object(policy.get("dev_ruleset"), "policy.dev_ruleset")
    _object(policy.get("automerge_label"), "policy.automerge_label")
    _validate_policy(policy)
    return policy


def _exact_dev_scope(payload: dict[str, object]) -> bool:
    if payload.get("target") != "branch":
        return False
    conditions = _object(payload.get("conditions"), "dev ruleset conditions")
    ref_name = _object(conditions.get("ref_name"), "dev ruleset ref condition")
    return ref_name.get("include") == ["refs/heads/dev"] and ref_name.get("exclude") == []


def _dev_ruleset(api: Api) -> tuple[int, dict[str, object]]:
    summaries = _objects(api.get_json(RULESETS_ENDPOINT), "repository rulesets", MAX_RULESETS)
    matches: list[tuple[int, dict[str, object]]] = []
    for summary in summaries:
        ruleset_id = summary.get("id")
        if not isinstance(ruleset_id, int):
            raise PolicyError("ruleset summary has no integer id")
        payload = _object(
            api.get_json(DEV_RULESET_ENDPOINT.format(ruleset_id=ruleset_id)),
            f"ruleset {ruleset_id}",
        )
        conditions = _object(payload.get("conditions"), f"ruleset {ruleset_id} conditions")
        ref_name = _object(conditions.get("ref_name"), f"ruleset {ruleset_id} ref condition")
        includes = ref_name.get("include")
        if isinstance(includes, list) and "refs/heads/dev" in includes:
            if not _exact_dev_scope(payload):
                raise PolicyError(f"ruleset {ruleset_id} does not have exact dev-only branch scope")
            matches.append((ruleset_id, payload))
    if len(matches) != 1:
        raise PolicyError(f"expected exactly one dev ruleset, found {len(matches)}")
    return matches[0]


def _labels(api: Api) -> list[dict[str, object]]:
    return _objects(api.get_json(LABELS_LIST_ENDPOINT), "repository labels", MAX_LABELS)


def _find_label(labels: list[dict[str, object]], name: str) -> dict[str, object] | None:
    matches = [label for label in labels if label.get("name") == name]
    if len(matches) > 1:
        raise PolicyError(f"label {name!r} appears more than once")
    return matches[0] if matches else None


def _current_state(api: Api) -> dict[str, object]:
    ruleset_id, ruleset = _dev_ruleset(api)
    repository = _object(api.get_json(REPOSITORY_ENDPOINT), "repository")
    labels = _labels(api)
    return {
        "dev_ruleset_id": ruleset_id,
        "dev_ruleset": normalize_ruleset(ruleset),
        "repository": normalize_repository(repository),
        "automerge_label": _find_label(labels, CANONICAL_AUTOMERGE_LABEL),
    }


def _state_identity(state: dict[str, object]) -> dict[str, object]:
    ruleset_id = state.get("dev_ruleset_id")
    if not isinstance(ruleset_id, int):
        raise PolicyError("state has no integer dev_ruleset_id")
    ruleset = normalize_ruleset(_object(state.get("dev_ruleset"), "state dev ruleset"))
    if not _exact_dev_scope(ruleset):
        raise PolicyError("state ruleset does not have exact dev-only branch scope")
    label = state.get("automerge_label")
    normalized_label = (
        None
        if label is None
        else _canonical_label(_object(label, "state automerge label"), "state label")
    )
    return {
        "dev_ruleset_id": ruleset_id,
        "dev_ruleset": ruleset,
        "repository": normalize_repository(_object(state.get("repository"), "state repository")),
        "automerge_label": normalized_label,
    }


def check_policy(api: Api, policy: dict[str, object]) -> list[str]:
    """Return structural drift without mutating GitHub."""
    _validate_policy(policy)
    current = _current_state(api)
    desired_repository = normalize_repository(_object(policy["repository"], "repository policy"))
    desired_ruleset = normalize_ruleset(_object(policy["dev_ruleset"], "dev ruleset policy"))
    desired_label = _canonical_label(_object(policy["automerge_label"], "label policy"), "policy")
    drift: list[str] = []
    if current["repository"] != desired_repository:
        drift.append("repository merge settings differ")
    if current["dev_ruleset"] != desired_ruleset:
        drift.append("dev ruleset differs")
    existing_label = current["automerge_label"]
    if existing_label is None:
        drift.append("automerge label is absent")
    elif (
        _canonical_label(_object(existing_label, "current automerge label"), "current label")
        != desired_label
    ):
        drift.append("automerge label differs")
    return drift


def _dev_sha(api: Api) -> str:
    ref = _object(api.get_json(DEV_REF_ENDPOINT), "dev ref")
    target = _object(ref.get("object"), "dev ref object")
    sha = target.get("sha")
    if not isinstance(sha, str) or SHA_PATTERN.fullmatch(sha) is None:
        raise PolicyError("dev ref has no canonical 40-hex SHA")
    return sha


def _required_contexts(policy: dict[str, object]) -> list[str]:
    ruleset = _object(policy["dev_ruleset"], "dev ruleset policy")
    rules = _objects(ruleset.get("rules"), "dev rules", MAX_RULESETS)
    status_rules = [rule for rule in rules if rule.get("type") == "required_status_checks"]
    if len(status_rules) != 1:
        raise PolicyError("dev policy must contain exactly one required-status-checks rule")
    parameters = _object(status_rules[0].get("parameters"), "status-check parameters")
    checks = _objects(parameters.get("required_status_checks"), "required checks", MAX_CHECK_RUNS)
    if not checks:
        raise PolicyError("dev policy must contain at least one required status check")
    contexts = [check.get("context") for check in checks]
    if not all(isinstance(context, str) and context for context in contexts):
        raise PolicyError("required status check has no context")
    if len(set(contexts)) != len(contexts):
        raise PolicyError("required status check contexts must be unique")
    return cast(list[str], contexts)


def _validate_policy(policy: dict[str, object]) -> None:
    ruleset = normalize_ruleset(_object(policy.get("dev_ruleset"), "dev ruleset policy"))
    if not _exact_dev_scope(ruleset):
        raise PolicyError("desired ruleset must have exact dev-only branch scope")
    contexts = tuple(_required_contexts(policy))
    if contexts != DEV_BLOCKING_CONTEXTS:
        raise PolicyError("required checks must equal the complete dev check manifest")
    normalize_repository(_object(policy.get("repository"), "repository policy"))
    _canonical_label(_object(policy.get("automerge_label"), "label policy"), "policy")


def _verify_green_dev(api: Api, policy: dict[str, object], expected_sha: str) -> None:
    actual_sha = _dev_sha(api)
    if actual_sha != expected_sha:
        raise PolicyError(f"dev moved: expected {expected_sha}, found {actual_sha}")
    payload = _object(
        api.get_json(CHECK_RUNS_ENDPOINT.format(sha=expected_sha)),
        "dev check runs",
    )
    total_count = payload.get("total_count")
    if type(total_count) is not int or total_count >= MAX_CHECK_RUNS:
        raise PolicyError(f"dev check runs reached the {MAX_CHECK_RUNS}-item safety bound")
    runs = _objects(payload.get("check_runs"), "dev check runs", MAX_CHECK_RUNS)
    latest: dict[str, dict[str, object]] = {}
    for candidate in runs:
        name = candidate.get("name")
        if not isinstance(name, str):
            raise PolicyError("check run has no name")
        run_id = candidate.get("id")
        if type(run_id) is not int:
            raise PolicyError(f"check run {name!r} has no integer id")
        started_at = candidate.get("started_at")
        if started_at is not None and not isinstance(started_at, str):
            raise PolicyError(f"check run {name!r} has a non-string started_at")
        prior = latest.get(name)
        current_key = (started_at or "", run_id)
        prior_id = prior.get("id") if prior is not None else 0
        if type(prior_id) is not int:
            raise PolicyError(f"prior check run {name!r} has no integer id")
        prior_key = (
            str(prior.get("started_at") or "") if prior is not None else "",
            prior_id,
        )
        if prior is None or current_key >= prior_key:
            latest[name] = candidate
    problems: list[str] = []
    for context in _required_contexts(policy):
        selected = latest.get(context)
        if selected is None:
            problems.append(f"{context}: missing")
            continue
        status = str(selected.get("status") or "")
        conclusion = str(selected.get("conclusion") or "")
        if status != "completed" or conclusion != "success":
            problems.append(f"{context}: status={status}, conclusion={conclusion}")
    if problems:
        raise PolicyError("exact dev checks are not green: " + "; ".join(problems))


def _write_snapshot(path: Path, state: dict[str, object], dev_sha: str) -> None:
    snapshot = {"dev_sha": dev_sha, **deepcopy(state)}
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8") as snapshot_file:
            snapshot_file.write(json.dumps(snapshot, indent=2, sort_keys=True) + "\n")
            snapshot_file.flush()
            os.fsync(snapshot_file.fileno())
    except FileExistsError as error:
        raise PolicyError(f"snapshot path already exists: {path}") from error


def _label_update_payload(label: dict[str, object]) -> dict[str, object]:
    return {
        "new_name": label["name"],
        "color": label["color"],
        "description": label["description"],
    }


def _restore_label(api: Api, prior: object, current: object = _UNKNOWN) -> None:
    if prior is None:
        name = (
            str(
                _canonical_label(_object(current, "current automerge label"), "current label")[
                    "name"
                ]
            )
            if current is not _UNKNOWN and current is not None
            else CANONICAL_AUTOMERGE_LABEL
        )
        api.send_json("DELETE", label_endpoint(name), {"name": name})
        return
    prior_label = _canonical_label(_object(prior, "snapshot automerge label"), "snapshot label")
    if current is None:
        api.send_json("POST", LABELS_ENDPOINT, prior_label)
        return
    current_name = (
        str(_canonical_label(_object(current, "current automerge label"), "current label")["name"])
        if current is not _UNKNOWN
        else str(prior_label["name"])
    )
    api.send_json(
        "PATCH",
        label_endpoint(current_name),
        _label_update_payload(prior_label),
    )


def _component_differences(
    current: dict[str, object],
    desired: dict[str, object],
) -> tuple[bool, bool, bool]:
    current_identity = _state_identity(current)
    desired_identity = _state_identity(desired)
    return (
        current_identity["dev_ruleset"] != desired_identity["dev_ruleset"],
        current_identity["repository"] != desired_identity["repository"],
        current_identity["automerge_label"] != desired_identity["automerge_label"],
    )


def _restore_components(
    api: Api,
    before: dict[str, object],
    current: dict[str, object] | None,
    *,
    restore_ruleset: bool,
    restore_repository: bool,
    restore_label: bool,
) -> list[str]:
    ruleset_id = before.get("dev_ruleset_id")
    if not isinstance(ruleset_id, int):
        raise PolicyError("snapshot has no integer dev_ruleset_id")
    ruleset = normalize_ruleset(_object(before.get("dev_ruleset"), "snapshot dev ruleset"))
    repository = normalize_repository(_object(before.get("repository"), "snapshot repository"))
    current_label = current.get("automerge_label") if current is not None else _UNKNOWN
    errors: list[str] = []
    if restore_ruleset:
        try:
            api.send_json("PUT", DEV_RULESET_ENDPOINT.format(ruleset_id=ruleset_id), ruleset)
        except (GitHubApiError, PolicyError, OSError) as error:
            errors.append(f"ruleset restore failed: {error}")
    if restore_repository:
        try:
            api.send_json("PATCH", REPOSITORY_ENDPOINT, repository)
        except (GitHubApiError, PolicyError, OSError) as error:
            errors.append(f"repository restore failed: {error}")
    if restore_label:
        try:
            _restore_label(api, before.get("automerge_label"), current_label)
        except (GitHubApiError, PolicyError, OSError) as error:
            errors.append(f"label restore failed: {error}")
    return errors


def _restore_snapshot(
    api: Api,
    before: dict[str, object],
    *,
    attempted_ruleset: bool,
    attempted_repository: bool,
    attempted_label: bool,
) -> None:
    _state_identity(before)
    current: dict[str, object] | None = None
    restore_flags = (attempted_ruleset, attempted_repository, attempted_label)
    try:
        current = _current_state(api)
        if current["dev_ruleset_id"] != before["dev_ruleset_id"]:
            raise PolicyError("dev ruleset ID changed; restore refused")
        restore_flags = _component_differences(current, before)
    except (GitHubApiError, OSError):
        pass
    errors = _restore_components(
        api,
        before,
        current,
        restore_ruleset=restore_flags[0],
        restore_repository=restore_flags[1],
        restore_label=restore_flags[2],
    )
    try:
        restored = _state_identity(_current_state(api)) == _state_identity(before)
    except (GitHubApiError, PolicyError, OSError) as error:
        errors.append(f"rollback readback failed: {error}")
        restored = False
    if not restored:
        errors.append("rollback readback does not match snapshot")
    if errors and not restored:
        raise PolicyError("; ".join(errors))


def _apply_label(api: Api, desired: dict[str, object], current: object) -> None:
    if current is None:
        api.send_json("POST", LABELS_ENDPOINT, desired)
        return
    current_label = _canonical_label(_object(current, "current automerge label"), "current label")
    if current_label != desired:
        api.send_json(
            "PATCH",
            label_endpoint(str(current_label["name"])),
            _label_update_payload(desired),
        )


def apply_policy(
    api: Api,
    policy: dict[str, object],
    expected_dev_sha: str,
    snapshot_path: Path,
) -> None:
    """Apply one coherent policy transaction and roll it back on any mismatch."""
    if SHA_PATTERN.fullmatch(expected_dev_sha) is None:
        raise PolicyError("--expected-dev-sha must be one canonical 40-hex SHA")
    _validate_policy(policy)
    _verify_green_dev(api, policy, expected_dev_sha)
    before = _current_state(api)
    _write_snapshot(snapshot_path, before, expected_dev_sha)
    if _state_identity(_current_state(api)) != _state_identity(before):
        raise PolicyError("GitHub settings changed after snapshot; no mutation was attempted")
    if _dev_sha(api) != expected_dev_sha:
        raise PolicyError("dev moved after green evidence; no mutation was attempted")

    desired_repository = normalize_repository(_object(policy["repository"], "repository policy"))
    desired_ruleset = normalize_ruleset(_object(policy["dev_ruleset"], "dev ruleset policy"))
    desired_label = _canonical_label(_object(policy["automerge_label"], "label policy"), "policy")
    ruleset_id = before["dev_ruleset_id"]
    if not isinstance(ruleset_id, int):
        raise PolicyError("current state has no integer dev_ruleset_id")

    current_label = before["automerge_label"]
    label_differs = (
        current_label is None
        or _canonical_label(_object(current_label, "current automerge label"), "current label")
        != desired_label
    )
    repository_differs = before["repository"] != desired_repository
    ruleset_differs = before["dev_ruleset"] != desired_ruleset
    label_attempted = False
    repository_attempted = False
    ruleset_attempted = False

    try:
        if label_differs:
            label_attempted = True
            _apply_label(api, desired_label, current_label)
        if repository_differs:
            repository_attempted = True
            api.send_json("PATCH", REPOSITORY_ENDPOINT, desired_repository)
        if ruleset_differs:
            ruleset_attempted = True
            api.send_json(
                "PUT",
                DEV_RULESET_ENDPOINT.format(ruleset_id=ruleset_id),
                desired_ruleset,
            )
        drift = check_policy(api, policy)
        if drift:
            raise PolicyError("GitHub policy readback mismatch: " + "; ".join(drift))
        if _dev_sha(api) != expected_dev_sha:
            raise PolicyError("dev moved during policy apply")
    except (GitHubApiError, PolicyError, OSError) as primary_error:
        try:
            _restore_snapshot(
                api,
                before,
                attempted_ruleset=ruleset_attempted,
                attempted_repository=repository_attempted,
                attempted_label=label_attempted,
            )
        except (GitHubApiError, PolicyError, OSError) as rollback_error:
            raise PolicyError(
                f"policy apply failed ({primary_error}); rollback also failed ({rollback_error})"
            ) from rollback_error
        raise


def load_snapshot(path: Path) -> dict[str, object]:
    """Load a previously retained transaction snapshot."""
    try:
        payload = json.loads(path.read_text())
    except OSError as error:
        raise PolicyError(f"cannot read snapshot {path}: {error}") from error
    except json.JSONDecodeError as error:
        raise PolicyError(f"snapshot {path} is not valid JSON") from error
    return _object(payload, "snapshot")


def rollback_policy(api: Api, snapshot: dict[str, object]) -> None:
    """Restore one snapshot only while its exact dev evidence is still current."""
    desired = _state_identity(snapshot)
    expected_dev_sha = snapshot.get("dev_sha")
    if not isinstance(expected_dev_sha, str) or SHA_PATTERN.fullmatch(expected_dev_sha) is None:
        raise PolicyError("snapshot has no canonical dev SHA")
    if _dev_sha(api) != expected_dev_sha:
        raise PolicyError("snapshot dev SHA is stale; rollback refused")

    _restore_snapshot(
        api,
        snapshot,
        attempted_ruleset=True,
        attempted_repository=True,
        attempted_label=True,
    )
    if _state_identity(_current_state(api)) != desired:
        raise PolicyError("manual rollback readback mismatch")
    if _dev_sha(api) != expected_dev_sha:
        raise PolicyError("dev moved during manual rollback")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--rollback", type=Path)
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY_PATH)
    parser.add_argument("--expected-dev-sha")
    parser.add_argument("--snapshot", type=Path)
    args = parser.parse_args()

    api = GhApi()
    try:
        if args.rollback is not None:
            rollback_policy(api, load_snapshot(args.rollback))
            print(f"github-pr-policy: restored {args.rollback}")
            return 0
        policy = load_policy(args.policy)
        if args.check:
            drift = check_policy(api, policy)
            for problem in drift:
                print(f"github-pr-policy: DRIFT — {problem}")
            return 1 if drift else 0
        if args.expected_dev_sha is None or args.snapshot is None:
            parser.error("--apply requires --expected-dev-sha and --snapshot")
        apply_policy(api, policy, args.expected_dev_sha, args.snapshot)
        print(f"github-pr-policy: applied at dev {args.expected_dev_sha}")
        print(f"github-pr-policy: rollback snapshot retained at {args.snapshot}")
        return 0
    except (GitHubApiError, PolicyError, OSError) as error:
        print(f"github-pr-policy: REFUSED — {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
