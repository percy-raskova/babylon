"""The corpus manifest — canon-as-data for the narrator's grounding corpus (ADR107, T5 U3).

Replaces the hardcoded ``MVP_CORPUS`` tuple that used to live in
``tools/ingest_corpus.py`` (a fuzzy-keyword-matching search against an
arbitrary external mirror path) with a declarative manifest of rows —
mirroring :mod:`babylon.intelligence.model_manifest`'s shape (frozen
Pydantic models, closed ``StrEnum`` vocabularies, a pure ``parse_manifest``
function, loud validation).

Each row names a ``path_glob`` that resolves against a *corpus root* — the
durable OCR/extraction tree at ``~/Documents/ocr/`` (see that tree's own
``MANIFEST.yaml`` for extraction provenance) — supplied by the caller at
load/resolve time. This module never hardcodes an absolute, user-specific
path; production code passes the real tree, unit tests build tmp fixtures.

Four canon dispositions (ADR107 widens the original allow/deny/flag_bd
triad to four so the apocrypha row can even be represented):

* ``allow`` — canon; eligible for narrator/RAG ingestion.
* ``deny`` — ruled OUT. Honored even *inside* an enclosing allow glob: the
  exclusion is computed as a set-difference over matched files, never a
  directory-level carve-out, so a denied sub-path wins over whatever allow
  glob happens to sweep over it (the "Trotsky-quoted-for-rebuttal" case).
* ``flag_bd`` — adversarial-only (Divergence Channel, ADR072). Never
  reachable from :meth:`CorpusManifest.ingest_targets` — only ``allow`` rows
  ever populate that set.
* ``apocryphal`` — kept deliberately, structurally fenced: a row may resolve
  into an ``_apocrypha/`` directory only if it declares this status, and a
  row declaring this status may resolve nowhere else. Enforced by
  :meth:`CorpusRow._check_apocrypha_fencing`, not by trusting every future
  ``path_glob`` author to remember a deny row (ADR107 consequences).

Presence vs. validity: a row whose glob matches nothing on a given box is a
MANIFEST fact (nothing has been extracted there yet), never a validation
error — :meth:`CorpusManifest.ingest_targets` reports empty matches for such
rows rather than raising.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, model_validator

#: Directory name the apocrypha class is fenced to (ADR107). No non-apocryphal
#: row's ``path_glob`` may resolve into it, and no apocryphal row may resolve
#: anywhere else.
APOCRYPHA_DIR_NAME = "_apocrypha"


class CorpusRole(StrEnum):
    """Where a chunk may surface — rides chunk ``metadata`` jsonb for ``@>`` retrieval.

    Orthogonal to :class:`CanonStatus`: role says WHERE a chunk can surface
    once ingested; canon_status says WHETHER it is ever ingested at all.
    """

    NARRATOR = "narrator"
    ATLAS_RU = "atlas_ru"
    ATLAS_CN = "atlas_cn"
    ATLAS_US = "atlas_us"
    CONCEPT_CARD = "concept_card"
    GLOSSARY = "glossary"
    DOCTRINE = "doctrine"


class CanonStatus(StrEnum):
    """The four canon dispositions (ADR107)."""

    ALLOW = "allow"
    DENY = "deny"
    FLAG_BD = "flag_bd"
    APOCRYPHAL = "apocryphal"


class CorpusFormat(StrEnum):
    """Source format a ``path_glob``'s matched files are stored in."""

    TXT = "txt"
    HTML = "html"
    MARKDOWN = "md"
    JSONL = "jsonl"


class CorpusRow(BaseModel):
    """One row of the corpus manifest: a glob, its canon disposition, provenance."""

    model_config = ConfigDict(frozen=True)

    path_glob: str
    author: str
    work: str
    role: tuple[CorpusRole, ...]
    format: CorpusFormat
    canon_status: CanonStatus
    provenance: str

    @model_validator(mode="after")
    def _check_role_nonempty(self) -> CorpusRow:
        if not self.role:
            raise ValueError(f"row {self.work!r} ({self.author!r}) must declare at least one role")
        return self

    @model_validator(mode="after")
    def _check_apocrypha_fencing(self) -> CorpusRow:
        # ADR107: the _apocrypha/ directory is structurally fenced — a glob
        # resolving into it must be tagged apocryphal, and nothing else may
        # point there. This is enforced here (loud, at load time) rather than
        # trusting every future path_glob author to remember a deny row.
        points_into_apocrypha = APOCRYPHA_DIR_NAME in Path(self.path_glob).parts
        if points_into_apocrypha and self.canon_status is not CanonStatus.APOCRYPHAL:
            raise ValueError(
                f"row {self.work!r} path_glob {self.path_glob!r} resolves into "
                f"{APOCRYPHA_DIR_NAME}/ but canon_status is "
                f"{self.canon_status.value!r}, not apocryphal (ADR107 glob-fencing)"
            )
        if self.canon_status is CanonStatus.APOCRYPHAL and not points_into_apocrypha:
            raise ValueError(
                f"row {self.work!r} is canon_status=apocryphal but path_glob "
                f"{self.path_glob!r} does not resolve into {APOCRYPHA_DIR_NAME}/"
            )
        return self


class ManifestTarget(BaseModel):
    """One ``allow`` row plus its deny-subtracted, existing-only matched files.

    ``files`` is already sorted (deterministic ordering). An empty tuple is a
    MANIFEST fact — the row's work has not been extracted onto this box yet —
    never an error.
    """

    model_config = ConfigDict(frozen=True)

    row: CorpusRow
    files: tuple[Path, ...]

    @property
    def present(self) -> bool:
        """Whether this row currently matches any file on disk."""
        return len(self.files) > 0


class CorpusManifest(BaseModel):
    """A validated, ordered set of corpus rows."""

    model_config = ConfigDict(frozen=True)

    rows: tuple[CorpusRow, ...]

    def allow_rows(self) -> tuple[CorpusRow, ...]:
        return tuple(r for r in self.rows if r.canon_status is CanonStatus.ALLOW)

    def deny_rows(self) -> tuple[CorpusRow, ...]:
        return tuple(r for r in self.rows if r.canon_status is CanonStatus.DENY)

    def flag_bd_rows(self) -> tuple[CorpusRow, ...]:
        return tuple(r for r in self.rows if r.canon_status is CanonStatus.FLAG_BD)

    def apocryphal_rows(self) -> tuple[CorpusRow, ...]:
        return tuple(r for r in self.rows if r.canon_status is CanonStatus.APOCRYPHAL)

    def ingest_targets(self, corpus_root: Path) -> tuple[ManifestTarget, ...]:
        """Allow rows (in manifest order), each with deny-subtracted, existing files.

        This is the enumeration contract that replaces ``MVP_CORPUS``: allow
        minus deny, existing-files-only, deterministic ordering. Deny rows are
        honored INSIDE allow globs — a denied sub-path's matched files are
        removed from an allow row's matches by set difference, never by a
        directory-level exclusion — so a deny row nested inside a broader
        allow glob still wins (the Trotsky-quoted-for-rebuttal case).

        A row whose matched-files tuple ends up empty is a MANIFEST fact
        (nothing extracted onto this box yet), never an error.
        """
        deny_files: set[Path] = set()
        for row in self.deny_rows():
            deny_files.update(_glob_matches(corpus_root, row.path_glob))

        targets: list[ManifestTarget] = []
        for row in self.allow_rows():
            matched = tuple(
                f for f in _glob_matches(corpus_root, row.path_glob) if f not in deny_files
            )
            targets.append(ManifestTarget(row=row, files=matched))
        return tuple(targets)

    def resolve_ingestible_files(self, corpus_root: Path) -> tuple[Path, ...]:
        """Flat, deterministically sorted union of every allow row's matched files."""
        files: set[Path] = set()
        for target in self.ingest_targets(corpus_root):
            files.update(target.files)
        return tuple(sorted(files))


def _glob_matches(corpus_root: Path, path_glob: str) -> list[Path]:
    """Resolve one ``path_glob`` against ``corpus_root``.

    An absent corpus_root (or a glob matching nothing) returns an empty list
    rather than raising — presence is reported separately from validity.
    """
    if not corpus_root.exists():
        return []
    return sorted(corpus_root.glob(path_glob))


def parse_manifest(raw: dict[str, Any]) -> CorpusManifest:
    """Parse a YAML mapping (a ``rows:`` list) into a validated manifest."""
    return CorpusManifest(rows=tuple(raw.get("rows", [])))


def load_manifest(path: Path) -> CorpusManifest:
    """Load and validate a corpus manifest from an explicit YAML path.

    Test-injectable by design: production code loads the bundled manifest via
    :func:`load_bundled_manifest`; unit tests pass a tmp-fixture path instead
    of ever touching the real ``~/Documents/ocr/`` tree.
    """
    with path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    return parse_manifest(raw or {})


def load_bundled_manifest() -> CorpusManifest:
    """Load the manifest shipped in the package (``babylon/data/corpus/manifest.yaml``)."""
    from importlib import resources

    data = resources.files("babylon.data.corpus").joinpath("manifest.yaml")
    with resources.as_file(data) as path:
        return load_manifest(path)
