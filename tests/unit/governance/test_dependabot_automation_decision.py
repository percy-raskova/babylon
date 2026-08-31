"""Decision contract for bounded Dependabot automation outcomes."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[3]
ADR_KEY = "ADR245_dependabot_bounded_retry_and_label_transport"
ADR_PATH = ROOT / "ai" / "decisions" / f"{ADR_KEY}.yaml"
INDEX_PATH = ROOT / "ai" / "decisions" / "index.yaml"


def _mapping(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_dependabot_decision_records_bounded_retry_and_transport_law() -> None:
    decision = _mapping(ADR_PATH)[ADR_KEY]
    text = " ".join(str(decision["decision"]).split())

    assert decision["status"] == "accepted"
    assert decision["date"] == "2026-08-30"
    assert decision["issue"] == "PER-264"
    for outcome in range(5):
        assert f"{outcome} is" in text
    assert "hard refusal outranks pending evidence" in text
    assert "only after" in text and "Dependabot" in text and "provenance" in text
    assert "at most eight times" in text
    assert "exactly thirty seconds" in text
    assert "retries only outcome 4" in text
    assert "eighth outcome 4 exits 4" in text
    assert "Issues REST GET, POST, and DELETE" in text
    assert "never uses `gh pr edit`" in text
    assert "No merge mutation is retried" in text
    assert "ADR230_exact_head_pr_and_dependabot_policy" in decision["related"]


def test_decision_index_resolves_to_dependabot_automation_record() -> None:
    index = _mapping(INDEX_PATH)

    assert index["decisions"][ADR_KEY] == {
        "title": (
            "Dependabot automation uses typed merge outcomes, bounded exact-head "
            "evidence retries, and Issues REST label transport"
        ),
        "status": "accepted",
        "date": "2026-08-30",
        "file": ADR_PATH.name,
    }
