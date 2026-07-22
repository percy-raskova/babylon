"""Behavioral contract for the corpus manifest (ADR107, T5 U3).

Replaces the hardcoded ``MVP_CORPUS`` tuple in ``tools/ingest_corpus.py``
with a declarative manifest (mirrors
:mod:`babylon.intelligence.model_manifest`'s validation style). Unit tests
never touch the real ``~/Documents/ocr/`` tree — every glob-resolution test
below builds its own tmp fixture tree.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from babylon.intelligence.corpus_manifest import (
    APOCRYPHA_DIR_NAME,
    CanonStatus,
    CorpusFormat,
    CorpusManifest,
    CorpusRole,
    load_bundled_manifest,
    load_manifest,
    parse_manifest,
)

pytestmark = pytest.mark.unit


def _row(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "path_glob": "author-x/work-y/*.txt",
        "author": "Author X",
        "work": "Work Y",
        "role": ["narrator"],
        "format": "txt",
        "canon_status": "allow",
        "provenance": "test fixture row",
    }
    base.update(overrides)
    return base


# =============================================================================
# 1. Loader validation — closed vocabularies red loudly (Do item 4)
# =============================================================================


class TestClosedVocabularies:
    def test_valid_row_parses(self) -> None:
        manifest = parse_manifest({"rows": [_row()]})
        assert len(manifest.rows) == 1
        row = manifest.rows[0]
        assert row.canon_status is CanonStatus.ALLOW
        assert row.role == (CorpusRole.NARRATOR,)
        assert row.format is CorpusFormat.TXT

    def test_bad_role_reds_loudly(self) -> None:
        with pytest.raises(ValidationError):
            parse_manifest({"rows": [_row(role=["not_a_real_role"])]})

    def test_bad_canon_status_reds_loudly(self) -> None:
        with pytest.raises(ValidationError):
            parse_manifest({"rows": [_row(canon_status="maybe")]})

    def test_bad_format_reds_loudly(self) -> None:
        with pytest.raises(ValidationError):
            parse_manifest({"rows": [_row(format="pdf")]})

    def test_empty_role_list_reds_loudly(self) -> None:
        with pytest.raises(ValidationError):
            parse_manifest({"rows": [_row(role=[])]})

    def test_multi_valued_role_accepted(self) -> None:
        manifest = parse_manifest({"rows": [_row(role=["narrator", "doctrine", "atlas_cn"])]})
        assert manifest.rows[0].role == (
            CorpusRole.NARRATOR,
            CorpusRole.DOCTRINE,
            CorpusRole.ATLAS_CN,
        )


# =============================================================================
# 2. Apocrypha glob-fencing (ADR107) — both directions
# =============================================================================


class TestApocryphaFencing:
    def test_apocryphal_row_must_resolve_into_apocrypha_dir(self) -> None:
        with pytest.raises(ValidationError, match="apocryphal"):
            parse_manifest(
                {"rows": [_row(path_glob="author-x/work-y/*.txt", canon_status="apocryphal")]}
            )

    def test_non_apocryphal_row_forbidden_inside_apocrypha_dir(self) -> None:
        with pytest.raises(ValidationError, match=APOCRYPHA_DIR_NAME):
            parse_manifest(
                {
                    "rows": [
                        _row(path_glob=f"{APOCRYPHA_DIR_NAME}/content.jsonl", canon_status="allow")
                    ]
                }
            )

    def test_apocryphal_row_pointing_into_apocrypha_dir_is_valid(self) -> None:
        manifest = parse_manifest(
            {
                "rows": [
                    _row(
                        path_glob=f"{APOCRYPHA_DIR_NAME}/content.jsonl",
                        canon_status="apocryphal",
                        format="jsonl",
                    )
                ]
            }
        )
        assert manifest.rows[0].canon_status is CanonStatus.APOCRYPHAL


# =============================================================================
# 3. Deny-inside-allow precedence, presence, and deterministic ordering
#    (Do item 4) — every test below builds its own tmp fixture tree.
# =============================================================================


class TestDenyInsideAllowPrecedence:
    def test_deny_row_wins_inside_an_enclosing_allow_glob(self, tmp_path: Path) -> None:
        # The "Trotsky-quoted-for-rebuttal" case: one broad allow glob sweeps
        # over several authors' subdirectories; a deny row nested inside it
        # must still exclude that author's files.
        (tmp_path / "classics" / "marx").mkdir(parents=True)
        (tmp_path / "classics" / "trotsky").mkdir(parents=True)
        marx_file = tmp_path / "classics" / "marx" / "capital.txt"
        marx_file.write_text("value theory")
        trotsky_file = tmp_path / "classics" / "trotsky" / "permanent-revolution.txt"
        trotsky_file.write_text("denied position")

        manifest = parse_manifest(
            {
                "rows": [
                    _row(path_glob="classics/**/*.txt", canon_status="allow"),
                    _row(path_glob="classics/trotsky/**/*.txt", canon_status="deny"),
                ]
            }
        )

        resolved = manifest.resolve_ingestible_files(tmp_path)
        assert marx_file in resolved
        assert trotsky_file not in resolved

    def test_flag_bd_row_never_appears_in_ingestible_files(self, tmp_path: Path) -> None:
        work_dir = tmp_path / "nitzan-bichler" / "capital-as-power"
        work_dir.mkdir(parents=True)
        flagged_file = work_dir / "full.txt"
        flagged_file.write_text("adversarial-only steelman text")

        manifest = parse_manifest(
            {
                "rows": [
                    _row(path_glob="nitzan-bichler/capital-as-power/*.txt", canon_status="flag_bd")
                ]
            }
        )

        assert manifest.resolve_ingestible_files(tmp_path) == ()

    def test_apocryphal_row_never_appears_in_ingestible_files(self, tmp_path: Path) -> None:
        (tmp_path / APOCRYPHA_DIR_NAME).mkdir(parents=True)
        apocrypha_file = tmp_path / APOCRYPHA_DIR_NAME / "content.jsonl"
        apocrypha_file.write_text('{"text": "pastiche"}\n')

        manifest = parse_manifest(
            {
                "rows": [
                    _row(
                        path_glob=f"{APOCRYPHA_DIR_NAME}/content.jsonl",
                        canon_status="apocryphal",
                        format="jsonl",
                    )
                ]
            }
        )

        assert manifest.resolve_ingestible_files(tmp_path) == ()


class TestPresenceReporting:
    def test_absent_row_reports_empty_files_not_an_error(self, tmp_path: Path) -> None:
        # corpus_root exists but this row's work has not been extracted yet —
        # a MANIFEST fact, never an exception.
        manifest = parse_manifest(
            {
                "rows": [
                    _row(path_glob="fanon/the-wretched-of-the-earth/*.txt", canon_status="allow")
                ]
            }
        )

        targets = manifest.ingest_targets(tmp_path)
        assert len(targets) == 1
        assert targets[0].files == ()
        assert targets[0].present is False

    def test_entirely_absent_corpus_root_reports_empty_without_error(self, tmp_path: Path) -> None:
        missing_root = tmp_path / "does-not-exist"
        manifest = parse_manifest(
            {
                "rows": [
                    _row(path_glob="fanon/the-wretched-of-the-earth/*.txt", canon_status="allow")
                ]
            }
        )

        targets = manifest.ingest_targets(missing_root)
        assert targets[0].files == ()

    def test_present_row_reports_matched_files(self, tmp_path: Path) -> None:
        work_dir = tmp_path / "author-x" / "work-y"
        work_dir.mkdir(parents=True)
        (work_dir / "full.txt").write_text("body")

        manifest = parse_manifest({"rows": [_row()]})
        targets = manifest.ingest_targets(tmp_path)
        assert targets[0].present is True
        assert len(targets[0].files) == 1


class TestDeterministicOrdering:
    def test_files_within_a_row_are_sorted_regardless_of_creation_order(
        self, tmp_path: Path
    ) -> None:
        work_dir = tmp_path / "mao" / "selected-works-curated"
        work_dir.mkdir(parents=True)
        # Write chapters out of order on purpose.
        (work_dir / "ch-03.txt").write_text("three")
        (work_dir / "ch-01.txt").write_text("one")
        (work_dir / "ch-02.txt").write_text("two")

        manifest = parse_manifest(
            {"rows": [_row(path_glob="mao/selected-works-curated/*.txt", canon_status="allow")]}
        )

        files = manifest.ingest_targets(tmp_path)[0].files
        assert [f.name for f in files] == ["ch-01.txt", "ch-02.txt", "ch-03.txt"]

    def test_rows_are_returned_in_manifest_declaration_order(self, tmp_path: Path) -> None:
        manifest = parse_manifest(
            {
                "rows": [
                    _row(path_glob="zebra/work/*.txt", work="Zebra Work", canon_status="allow"),
                    _row(path_glob="apple/work/*.txt", work="Apple Work", canon_status="allow"),
                ]
            }
        )

        targets = manifest.ingest_targets(tmp_path)
        assert [t.row.work for t in targets] == ["Zebra Work", "Apple Work"]


# =============================================================================
# 4. load_manifest — the test-injectable file loader (never the real tree)
# =============================================================================


class TestLoadManifestFromPath:
    def test_load_manifest_reads_a_yaml_fixture(self, tmp_path: Path) -> None:
        manifest_path = tmp_path / "manifest.yaml"
        manifest_path.write_text(
            "rows:\n"
            "  - path_glob: 'author-x/work-y/*.txt'\n"
            "    author: 'Author X'\n"
            "    work: 'Work Y'\n"
            "    role: [narrator]\n"
            "    format: txt\n"
            "    canon_status: allow\n"
            "    provenance: 'fixture'\n"
        )

        manifest = load_manifest(manifest_path)
        assert isinstance(manifest, CorpusManifest)
        assert len(manifest.rows) == 1
        assert manifest.rows[0].author == "Author X"


# =============================================================================
# 5. The bundled production manifest — sanity checks against the real file
#    this unit ships (src/babylon/data/corpus/manifest.yaml). Still no I/O
#    against ~/Documents/ocr/ — glob resolution against the real corpus root
#    is exercised only by the presence tests above, on tmp fixtures.
# =============================================================================


class TestBundledManifest:
    def test_bundled_manifest_loads_and_validates(self) -> None:
        manifest = load_bundled_manifest()
        assert isinstance(manifest, CorpusManifest)
        assert len(manifest.rows) > 0

    def test_bundled_manifest_has_the_v1_nine_work_allow_set(self) -> None:
        manifest = load_bundled_manifest()
        assert len(manifest.allow_rows()) == 9

    def test_bundled_manifest_denies_the_ruled_out_authors(self) -> None:
        manifest = load_bundled_manifest()
        denied_authors = {row.author for row in manifest.deny_rows()}
        assert denied_authors == {
            "Leon Trotsky",
            "Karl Kautsky",
            "Communist Party USA",
            "Enver Hoxha",
        }

    def test_bundled_manifest_has_exactly_one_apocryphal_row_fenced(self) -> None:
        manifest = load_bundled_manifest()
        apocryphal = manifest.apocryphal_rows()
        assert len(apocryphal) == 1
        assert APOCRYPHA_DIR_NAME in Path(apocryphal[0].path_glob).parts

    def test_bundled_manifest_has_a_flag_bd_row(self) -> None:
        manifest = load_bundled_manifest()
        assert len(manifest.flag_bd_rows()) >= 1

    def test_bundled_manifest_no_row_glob_resolves_into_apocrypha_unless_apocryphal(
        self,
    ) -> None:
        manifest = load_bundled_manifest()
        for row in manifest.rows:
            resolves_into_apocrypha = APOCRYPHA_DIR_NAME in Path(row.path_glob).parts
            assert resolves_into_apocrypha == (row.canon_status is CanonStatus.APOCRYPHAL)
