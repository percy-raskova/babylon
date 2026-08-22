"""Executable structure and continuity contract for Constitution v4.0.0.

The live constitution stays short.  The transition ledger in ADR221 carries
the exhaustive historical mapping from the two pinned predecessor snapshots.
"""

from __future__ import annotations

import hashlib
import re
import subprocess
from pathlib import Path
from typing import Final

import pytest
import yaml

pytestmark = [pytest.mark.unit]

_ROOT: Final[Path] = Path(__file__).resolve().parents[3]
_CONSTITUTION: Final[Path] = _ROOT / "CONSTITUTION.md"
_ADR_STEM: Final[str] = "ADR221_game_first_refoundation_v4"
_ADR_PATH: Final[Path] = _ROOT / "ai" / "decisions" / f"{_ADR_STEM}.yaml"
_INDEX_PATH: Final[Path] = _ROOT / "ai" / "decisions" / "index.yaml"
_MANIFEST_PATH: Final[Path] = (
    _ROOT / "tests" / "fixtures" / "governance" / "constitution_v3_2_manifest.yaml"
)
_V3_1_BLOB: Final[str] = "a265b85120ed2a90be40c72e63ee5bf27fc6e703"
_V3_2_BLOB: Final[str] = "e905e90d66bddc6e4eca36a3896428f5ce63de5b"
_V3_1_COMMIT: Final[str] = "3acd1089b6b4e68177c99b4f4cec245e7b74317c"
_V3_2_COMMIT: Final[str] = "cbfc67921283ccb6e00c4b0278288a232281440a"
_V3_2_BYTE_SIZE: Final[int] = 118_006
_V3_2_SHA256: Final[str] = "f9f295504f50b5c9f99323cea7d329aa0bdc46a07c0c4032bfb784810e7e3193"
_MAX_CONSTITUTION_BLOB_BYTES: Final[int] = 128_000
_MAX_MANIFEST_BYTES: Final[int] = 16_384
_MAX_PREDECESSOR_LINES: Final[int] = 1_024

_ARTICLE_HEADINGS: Final[tuple[str, ...]] = (
    "## Article I — Purpose and Player Promise",
    "## Article II — Theoretical Commitments",
    "## Article III — Emergence and Agency",
    "## Article IV — Evidence and Design Liberties",
    "## Article V — Deterministic Architecture",
    "## Article VI — Political-Economy Circuit",
    "## Article VII — Player Knowledge and Presentation",
    "## Article VIII — Behavioral Validation and Governance",
)

_UNDOTTED_SECTIONS: Final[tuple[str, ...]] = (
    "I.19.Apex",
    "IV",
    "V.Player",
    "V.Investigate",
    "V.State-AI",
)
_DISPOSITIONS: Final[frozenset[str]] = frozenset({"Retained", "Rewritten", "Re-homed", "Retired"})
_ARTICLE_REFERENCE: Final[re.Pattern[str]] = re.compile(r"Article (?:I|II|III|IV|V|VI|VII|VIII)")
_TRANSITION_REFERENCE: Final[re.Pattern[str]] = re.compile(
    r"transition\.(?:sources\.(?:v3_1|v3_2)|clauses(?:\.[A-Z0-9.a-z]+)?|"
    r"undotted_sections(?:\.[A-Z0-9.-]+)?|amendments(?:\.[A-Z]{1,2})?)"
)
_ARTICLE_HEADING: Final[re.Pattern[str]] = re.compile(
    r"^## (?P<article>I|II|III|IV|V|VI|VII|VIII|IX|X)\."
)
_EXPLICIT_CLAUSE: Final[re.Pattern[str]] = re.compile(
    r"^\*\*(?P<number>\d+\.\d+|\d+[a-z]?)(?:\.| )"
)
_ARTICLE_IV_CLAUSE: Final[re.Pattern[str]] = re.compile(r"^### IV\.(?P<number>\d+) ")
_AMENDMENT_HEADING: Final[re.Pattern[str]] = re.compile(r"^\*\*Amendment (?P<letter>[A-Z]{1,2}) —")
_AMENDMENT_REGISTRATION: Final[re.Pattern[str]] = re.compile(
    r"^Bump Rationale: [A-Z]+ — Amendments? (?P<letter>[A-Z]{1,2})"
)
_PLAYER_ROSTER: Final[re.Pattern[str]] = re.compile(
    r"### Player \(9 verbs\)\n\n\*\*(?P<verbs>[A-Za-z, ]+)\*\*\."
)


def _constitution_text() -> str:
    """Return the live constitutional text."""
    return _CONSTITUTION.read_text(encoding="utf-8")


def _adr_entry() -> dict[str, object]:
    """Return ADR221's single keyed record."""
    document = yaml.safe_load(_ADR_PATH.read_text(encoding="utf-8"))
    assert list(document) == [_ADR_STEM]
    return document[_ADR_STEM]


def _transition() -> dict[str, object]:
    """Return ADR221's transition ledger."""
    transition = _adr_entry()["transition"]
    assert isinstance(transition, dict)
    return transition


def _manifest() -> dict[str, object]:
    """Return the checked, size-bounded v3.2 continuity manifest."""
    assert 0 < _MANIFEST_PATH.stat().st_size <= _MAX_MANIFEST_BYTES
    document = yaml.safe_load(_MANIFEST_PATH.read_text(encoding="utf-8"))
    assert isinstance(document, dict)
    return document


def _manifest_family(name: str) -> tuple[str, ...]:
    """Return one ordered family from the independent v3.2 manifest."""
    families = _manifest()["families"]
    assert isinstance(families, dict)
    identifiers = families[name]
    assert isinstance(identifiers, list)
    assert all(isinstance(identifier, str) for identifier in identifiers)
    return tuple(identifiers)


def _mapped_rows() -> tuple[dict[str, str], ...]:
    """Return every dotted, undotted, and amendment disposition row."""
    transition = _transition()
    rows: list[dict[str, str]] = []
    for family in ("clauses", "undotted_sections", "amendments"):
        mapping = transition[family]
        assert isinstance(mapping, dict)
        rows.extend(mapping.values())
    return tuple(rows)


def _git_blob_text(blob: str) -> str:
    """Read one size-bounded Git blob from the repository object store."""
    size_result = subprocess.run(  # noqa: S603
        ["git", "cat-file", "-s", blob],  # noqa: S607
        cwd=_ROOT,
        capture_output=True,
        text=True,
        check=True,
        timeout=5,
    )
    size = int(size_result.stdout.strip())
    assert 0 < size <= _MAX_CONSTITUTION_BLOB_BYTES
    blob_result = subprocess.run(  # noqa: S603
        ["git", "cat-file", "-p", blob],  # noqa: S607
        cwd=_ROOT,
        capture_output=True,
        text=True,
        check=True,
        timeout=5,
    )
    assert len(blob_result.stdout.encode("utf-8")) == size
    return blob_result.stdout


def _git_object_exists(spec: str) -> bool:
    """Return whether one Git object spec resolves without fetching."""
    result = subprocess.run(  # noqa: S603
        ["git", "cat-file", "-e", spec],  # noqa: S607
        cwd=_ROOT,
        capture_output=True,
        check=False,
        timeout=5,
    )
    return result.returncode == 0


def _git_object_id(spec: str) -> str:
    """Resolve one bounded predecessor path to its Git blob identity."""
    result = subprocess.run(  # noqa: S603
        ["git", "rev-parse", spec],  # noqa: S607
        cwd=_ROOT,
        capture_output=True,
        text=True,
        check=True,
        timeout=5,
    )
    return result.stdout.strip()


def _extract_v3_2_manifest(text: str) -> dict[str, object]:
    """Independently extract transition families and the player roster."""
    lines = text.splitlines()
    assert 0 < len(lines) <= _MAX_PREDECESSOR_LINES
    dotted: list[str] = []
    named: list[str] = []
    amendments: set[str] = set()
    list_counts = {"VI": 0, "VII": 0, "VIII": 0}
    article = ""
    for line in lines[:_MAX_PREDECESSOR_LINES]:
        article_match = _ARTICLE_HEADING.match(line)
        if article_match is not None:
            article = article_match.group("article")
            if article == "IV":
                named.append("IV")
            continue
        explicit_match = _EXPLICIT_CLAUSE.match(line)
        if article in {"I", "II", "III", "IX", "X"} and explicit_match is not None:
            dotted.append(f"{article}.{explicit_match.group('number')}")
        if article in list_counts and line.startswith("1. **"):
            list_counts[article] += 1
            dotted.append(f"{article}.{list_counts[article]}")
        article_iv_match = _ARTICLE_IV_CLAUSE.match(line)
        if article == "IV" and article_iv_match is not None:
            dotted.append(f"IV.{article_iv_match.group('number')}")
        if article == "I" and line.startswith("**Apex Abstraction clause**"):
            named.append("I.19.Apex")
        if article == "V" and line.startswith("### Player (9 verbs)"):
            named.append("V.Player")
        if article == "V" and line.startswith("**Investigate Sub-Verbs**"):
            named.append("V.Investigate")
        if article == "V" and line.startswith("### State AI (6 verbs)"):
            named.append("V.State-AI")
        amendment_match = _AMENDMENT_HEADING.match(line)
        if article == "IX" and amendment_match is not None:
            amendments.add(amendment_match.group("letter"))
        registration_match = _AMENDMENT_REGISTRATION.match(line)
        if registration_match is not None:
            amendments.add(registration_match.group("letter"))

    roster_match = _PLAYER_ROSTER.search(text)
    assert roster_match is not None
    roster = [verb.strip() for verb in roster_match.group("verbs").split(",")]
    return {
        "player_verbs": roster,
        "families": {
            "dotted_clauses": dotted,
            "named_sections": named,
            "registered_amendments": sorted(amendments, key=lambda value: (len(value), value)),
        },
    }


def test_constitution_has_exactly_the_approved_eight_articles() -> None:
    """Article names and order are the v4 public orientation contract."""
    headings = tuple(
        line for line in _constitution_text().splitlines() if line.startswith("## Article ")
    )
    assert headings == _ARTICLE_HEADINGS


def test_constitution_states_the_game_first_promise_and_evidence_classes() -> None:
    """A fresh reader can recover purpose, method, and the validation standard."""
    text = " ".join(_constitution_text().split())
    required = (
        "Version 4.0.0",
        "entertainment",
        "expressive",
        "emergent",
        "not a forecast",
        "not a scientific reproduction",
        "Observed",
        "Derived",
        "Calibrated",
        "Designed",
        "computational identity",
        "scientific truth",
        "decision question",
        "causal signatures",
        "heterogeneity",
        "hysteresis",
        "counterfactual responsiveness",
        "Amendment AH — Game-First Refoundation",
    )
    missing = tuple(phrase for phrase in required if phrase not in text)
    assert missing == ()


def test_constitution_pins_the_exact_v4_primitive_and_retained_invariants() -> None:
    """AH carries each retained formal invariant in the live law."""
    raw_text = _constitution_text()
    text = " ".join(raw_text.split())
    required = (
        "D = (A, Ā, w, T, σ)",
        "material position and conceived interest",
        "Nothing can abstract over dialectical motion",
        "law, a falsifiable prediction, or a running computation",
        "must never expand into a pairwise clique",
        "Every materialized projection must be deterministic",
    )
    assert tuple(phrase for phrase in required if phrase not in text) == ()
    assert "D = (A, A-bar, w, T, s)" not in raw_text


def test_material_action_effects_always_become_next_week_intents() -> None:
    """Only epistemic feedback, never material mutation, can resolve now."""
    text = " ".join(_constitution_text().split())
    assert "All material effects become next-week intents" in text
    assert "only non-material knowledge, previews, and receipts" in text
    assert "unless an explicitly governed rule requires immediate resolution" not in text


def test_constitution_rejects_superseded_product_promises() -> None:
    """Deterministic computation must never become predetermined history."""
    text = _constitution_text()
    prohibited = (
        "Collapse is default",
        "Player shapes character, not outcome",
        "testing MLM-TW political economy against empirical data",
        "MUST reproduce observed",
        "Failure = theory or implementation wrong",
        "the only gate that matters",
    )
    found = tuple(phrase for phrase in prohibited if phrase in text)
    assert found == ()


def test_transition_adr_pins_both_predecessor_blobs_and_resolves_citations() -> None:
    """The refoundation preserves v3.1 and the immediate v3.2/AG authority."""
    transition = _transition()
    sources = transition["sources"]
    assert isinstance(sources, dict)
    assert set(sources) == {"v3_1", "v3_2"}
    assert sources["v3_1"] == {
        "version": "3.1.0",
        "blob": _V3_1_BLOB,
        "note": "Requested AF-era predecessor snapshot.",
    }
    assert sources["v3_2"] == {
        "version": "3.2.0",
        "blob": _V3_2_BLOB,
        "note": "Immediate predecessor and source of Amendment AG authority.",
    }
    resolution = transition["citation_resolution"]
    assert isinstance(resolution, dict)
    assert set(resolution) == {"dotted_clauses", "named_sections", "amendments", "post_ah"}
    for family in ("dotted_clauses", "named_sections", "amendments"):
        assert "pinned v3.2" in resolution[family]


def test_transition_adr_records_the_primitive_notation_ruling_exactly() -> None:
    """AH changes v3.2's ``s`` to ``sigma`` without rewriting history."""
    notation = _transition()["primitive_notation"]
    assert isinstance(notation, dict)
    assert set(notation) == {"v3_2", "v4", "ruling"}
    assert notation["v3_2"] == "D = (A, Ā, w, T, s)"
    assert notation["v4"] == "D = (A, Ā, w, T, σ)"
    assert "Amendment AH" in notation["ruling"]
    assert "does not rewrite" in notation["ruling"]


def test_v3_2_manifest_is_complete_unique_and_exactly_pinned() -> None:
    """The checked manifest is the CI-safe independent continuity oracle."""
    manifest = _manifest()
    assert set(manifest) == {"source", "families"}
    source = manifest["source"]
    assert source == {
        "version": "3.2.0",
        "blob": _V3_2_BLOB,
        "byte_size": _V3_2_BYTE_SIZE,
        "sha256": _V3_2_SHA256,
        "player_verbs": [
            "Educate",
            "Aid",
            "Attack",
            "Mobilize",
            "Campaign",
            "Move",
            "Investigate",
            "Reproduce",
            "Negotiate",
        ],
    }
    families = manifest["families"]
    assert isinstance(families, dict)
    assert set(families) == {"dotted_clauses", "named_sections", "registered_amendments"}
    for family_name in ("dotted_clauses", "named_sections", "registered_amendments"):
        identifiers = _manifest_family(family_name)
        assert identifiers
        assert len(identifiers) == len(set(identifiers))
    assert _manifest_family("named_sections") == _UNDOTTED_SECTIONS


def test_checked_manifest_player_roster_matches_the_governed_matrix() -> None:
    """The normal unit gate needs no Git history to protect the v3.2 roster."""
    from babylon.game.actions.matrix import verbs_in_matrix

    source = _manifest()["source"]
    assert isinstance(source, dict)
    roster = source["player_verbs"]
    assert isinstance(roster, list)
    normalized = tuple(sorted(verb.lower() for verb in roster))
    assert normalized == verbs_in_matrix()


@pytest.mark.skipif(not (_ROOT / ".git").exists(), reason="Git metadata absent from source archive")
def test_checked_manifest_matches_the_supplied_predecessor_commits() -> None:
    """Repository checkouts fail loudly if CI omits the bounded history supply."""
    v3_1_spec = f"{_V3_1_COMMIT}:CONSTITUTION.md"
    v3_2_spec = f"{_V3_2_COMMIT}:CONSTITUTION.md"
    assert _git_object_exists(v3_1_spec), (
        "repository checkout is missing the pinned v3.1 Constitution commit; "
        "the test-unit workflow must run its bounded predecessor fetch"
    )
    assert _git_object_exists(v3_2_spec), (
        "repository checkout is missing the pinned v3.2 Constitution commit; "
        "the test-unit workflow must run its bounded predecessor fetch"
    )
    assert _git_object_id(v3_1_spec) == _V3_1_BLOB
    assert _git_object_id(v3_2_spec) == _V3_2_BLOB

    predecessor = _git_blob_text(v3_2_spec)
    predecessor_bytes = predecessor.encode("utf-8")
    source = _manifest()["source"]
    assert isinstance(source, dict)
    assert len(predecessor_bytes) == source["byte_size"]
    assert hashlib.sha256(predecessor_bytes).hexdigest() == source["sha256"]
    extracted = _extract_v3_2_manifest(predecessor)
    assert extracted["player_verbs"] == source["player_verbs"]
    assert extracted["families"] == _manifest()["families"]


def test_transition_adr_maps_every_old_dotted_clause_exactly_once() -> None:
    """No clause disappears through an article-level summary."""
    transition = _transition()
    clauses = transition["clauses"]
    assert isinstance(clauses, dict)
    assert tuple(clauses) == _manifest_family("dotted_clauses")


def test_transition_adr_maps_every_old_undotted_section_exactly_once() -> None:
    """Named v3 sections receive the same explicit treatment as clauses."""
    sections = _transition()["undotted_sections"]
    assert isinstance(sections, dict)
    assert tuple(sections) == _manifest_family("named_sections")


def test_transition_adr_maps_every_registered_amendment_exactly_once() -> None:
    """AG survives; AB is absent because no Amendment AB was ever registered."""
    transition = _transition()
    amendments = transition["amendments"]
    assert isinstance(amendments, dict)
    assert tuple(amendments) == _manifest_family("registered_amendments")
    assert amendments["AG"]["disposition"] == "Rewritten"


def test_materially_changed_player_and_projection_law_is_rewritten() -> None:
    """The ledger never calls a narrowed or re-bound obligation retained."""
    transition = _transition()
    clauses = transition["clauses"]
    amendments = transition["amendments"]
    assert isinstance(clauses, dict)
    assert isinstance(amendments, dict)
    for clause in ("I.11", "II.5", "II.8"):
        assert clauses[clause]["disposition"] == "Rewritten"
    for amendment in ("V", "W"):
        assert amendments[amendment]["disposition"] == "Rewritten"


def test_every_transition_row_is_a_complete_auditable_record() -> None:
    """No mapping family permits blank authority or unexplained disposition."""
    for row in _mapped_rows():
        assert set(row) == {"disposition", "destination", "rationale"}
        assert row["disposition"] in _DISPOSITIONS
        assert row["destination"].strip()
        assert row["rationale"].strip()


def test_every_destination_resolves_to_an_article_path_or_transition_anchor() -> None:
    """Every disposition names resolvable authority, not a vague category."""
    for row in _mapped_rows():
        references = tuple(part.strip() for part in row["destination"].split(";"))
        assert references
        for reference in references:
            if _ARTICLE_REFERENCE.fullmatch(reference):
                continue
            if _TRANSITION_REFERENCE.fullmatch(reference):
                continue
            assert (_ROOT / reference.partition(" §")[0]).is_file(), reference


def test_adr_is_catalogued_with_the_modern_record_shape() -> None:
    """The ADR filename, key, required fields, and index entry stay in lockstep."""
    entry = _adr_entry()
    required = {
        "status",
        "date",
        "title",
        "context",
        "decision",
        "transition",
        "consequences",
        "supersedes",
        "related",
    }
    assert required <= set(entry)
    assert entry["status"] == "accepted"
    index = yaml.safe_load(_INDEX_PATH.read_text(encoding="utf-8"))
    assert index["decisions"][_ADR_STEM] == {
        "title": entry["title"],
        "status": "accepted",
        "date": "2026-08-22",
        "file": f"{_ADR_STEM}.yaml",
    }
