"""The per-table registry loader for ``data-catalog.yaml`` (Program 21).

``data-catalog.yaml`` is the canonical machine-readable data catalog
(Constitution III.4.1). Historically it carried *source-level* provenance only
(agency, dataset, vintage); the Data Constitution program adds a ``tables:``
block declaring, for every reference-DB table and view: its source lineage,
extractor, code consumers, guarding tests, triage disposition, and CI-subset
policy. This module loads that block into frozen :class:`CatalogTable` rows.

Unlike the hand-written ``.py`` literals of the coverage/synthetic registries,
the catalog **is** a maintained YAML source of truth — so the registry loads
the YAML at check time (mirroring ``GameDefines.load_default()`` reading
``defines.yaml``), and a missing, unparseable, or table-less catalog raises
:class:`~babylon.sentinels.base.SentinelCheckError` (infrastructure failure,
exit 2 — never a silent pass; Constitution III.11).

The static checks over these rows live in
:mod:`babylon.sentinels.coverage.checks`; the DB-probe tier lives in
:mod:`babylon.sentinels.coverage.db_probe`.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, model_validator

from babylon.sentinels.base import SentinelCheckError

#: Repo root (this file is ``<root>/src/babylon/sentinels/coverage/catalog.py``).
_REPO_ROOT: Path = Path(__file__).resolve().parents[4]

#: The canonical catalog location (repo root, Constitution III.4.1).
CATALOG_PATH: Path = _REPO_ROOT / "data-catalog.yaml"

#: The subset generator whose ``TABLE`` policy dict is the second SoT the
#: parity check reconciles against.
SUBSET_GENERATOR_PATH: Path = _REPO_ROOT / "tools" / "make_reference_subset.py"


class CatalogTable(BaseModel):
    """One reference-DB table or view declared in ``data-catalog.yaml``.

    Frozen and ``extra="forbid"`` so a malformed row is a loud failure at load
    time (Constitution III.11) rather than a quiet ``None`` at check time.

    :ivar name: the ``sqlite_master`` object name (``fact_*``/``dim_*``/
        ``bridge_*`` table or ``view_*`` view).
    :ivar kind: ``"table"`` or ``"view"`` — drives the empty-base-table probe.
    :ivar source: lineage pointer — an ``id`` from ``categories[].sources[]``
        or ``"derived"``/``"internal"`` for computed/infrastructure objects.
    :ivar extractor: loader/ingest lineage — a live repo path, an archaeology
        note (e.g. ``"deleted @ 4ce7c96a^ tools/etl.py"``), or ``None``.
    :ivar reads: views only — the base tables the view SELECTs from (the
        empty-view probe target). Must be empty for ``kind="table"``.
    :ivar consumers: repo-relative ``.py`` paths that read this object at
        runtime or in tools; existence is asserted by the static sensor.
    :ivar tests: repo-relative test paths guarding this object; existence is
        asserted by the static sensor.
    :ivar disposition: the Data Constitution triage verdict. ``amputate`` is a
        *proposal* — execution always requires an owner ruling.
    :ivar subset_policy: the CI-subset scope; for base tables this MUST equal
        the generator's ``TABLE[name].scope`` (parity-checked); views are never
        copied into subsets and must declare ``"skip"``.
    :ivar material_relation: the material relation the data grounds
        (Aleksandrov Test); required, non-blank.
    :ivar notes: free-text clarification.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    kind: Literal["table", "view"]
    source: str
    extractor: str | None = None
    reads: tuple[str, ...] = ()
    consumers: tuple[str, ...] = ()
    tests: tuple[str, ...] = ()
    disposition: Literal["keep", "fill", "artifact", "amputate", "investigate"]
    subset_policy: Literal["full", "michigan", "skip"]
    material_relation: str
    notes: str = ""

    @model_validator(mode="after")
    def _validate_shape(self) -> CatalogTable:
        """Reject malformed rows loudly at construction (III.11).

        :returns: ``self`` when valid.
        :raises ValueError: on a blank ``name``/``source``/``material_relation``,
            a view without ``reads`` (or a table with them), a view whose
            ``subset_policy`` is not ``"skip"``, or a non-``.py`` path in
            ``consumers``/``tests``.
        """
        if not self.name.strip():
            raise ValueError("CatalogTable.name must be non-empty")
        if not self.source.strip():
            raise ValueError(f"{self.name!r}: source must be non-empty")
        if not self.material_relation.strip():
            raise ValueError(f"{self.name!r}: material_relation must be non-empty (Aleksandrov)")
        if self.kind == "view" and not self.reads:
            raise ValueError(f"{self.name!r}: a view must declare the base tables it reads")
        if self.kind == "table" and self.reads:
            raise ValueError(f"{self.name!r}: only views declare reads")
        if self.kind == "view" and self.subset_policy != "skip":
            raise ValueError(
                f"{self.name!r}: views are never copied into ci-data subsets — "
                "subset_policy must be 'skip'"
            )
        for field_name, paths in (("consumers", self.consumers), ("tests", self.tests)):
            for entry in paths:
                if not entry.endswith(".py"):
                    raise ValueError(
                        f"{self.name!r}: {field_name} entry {entry!r} is not a .py path"
                    )
        return self


def load_catalog_tables(path: Path = CATALOG_PATH) -> tuple[CatalogTable, ...]:
    """Load the ``tables:`` block of ``data-catalog.yaml`` into frozen rows.

    :param path: Catalog file to read (injectable for efficacy tests).
    :returns: One :class:`CatalogTable` per declared table/view.
    :raises SentinelCheckError: If the file is missing, unparseable, carries no
        ``tables:`` block, or any row fails validation — all infrastructure
        failures (exit 2), never swallowed into a false pass.
    """
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SentinelCheckError(f"cannot read data catalog {path}: {exc}") from exc
    try:
        document = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        raise SentinelCheckError(f"cannot parse data catalog {path}: {exc}") from exc
    if not isinstance(document, dict) or "tables" not in document:
        raise SentinelCheckError(
            f"data catalog {path} has no 'tables' block — the per-table registry "
            "is missing (Program 21 backfill absent?)"
        )
    rows_raw = document["tables"]
    if not isinstance(rows_raw, list) or not rows_raw:
        raise SentinelCheckError(f"data catalog {path}: 'tables' must be a non-empty list")
    try:
        return tuple(CatalogTable(**row) for row in rows_raw)
    except (TypeError, ValueError) as exc:
        raise SentinelCheckError(f"data catalog {path}: malformed table row — {exc}") from exc


def subset_policy_map(path: Path = SUBSET_GENERATOR_PATH) -> dict[str, str]:
    """Statically parse the generator's ``TABLE`` policy dict into name→scope.

    Reads ``tools/make_reference_subset.py`` with :mod:`ast` (no import — the
    generator opens databases at module scope elsewhere, and layer-0.5 must
    stay static). Matches entries of the shape
    ``"table_name": TablePolicy("scope", ...)``.

    :param path: Generator source to parse (injectable for tests).
    :returns: Mapping of table name to declared scope literal.
    :raises SentinelCheckError: If the file is missing/unparseable or no
        ``TABLE`` dict assignment is found.
    """
    try:
        source = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SentinelCheckError(f"cannot read subset generator {path}: {exc}") from exc
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        raise SentinelCheckError(f"cannot parse subset generator {path}: {exc}") from exc
    for node in tree.body:
        dict_node = _table_dict_value(node)
        if dict_node is not None:
            return _scopes_from_dict(dict_node, path)
    raise SentinelCheckError(f"no module-level TABLE dict found in {path}")


def _table_dict_value(node: ast.stmt) -> ast.Dict | None:
    """Return the dict literal assigned to ``TABLE``, if ``node`` is it."""
    if (
        isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and node.target.id == "TABLE"
        and isinstance(node.value, ast.Dict)
    ):
        return node.value
    if isinstance(node, ast.Assign) and isinstance(node.value, ast.Dict):
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "TABLE":
                return node.value
    return None


def _scopes_from_dict(dict_node: ast.Dict, path: Path) -> dict[str, str]:
    """Extract ``name -> scope`` from ``TABLE``'s dict literal.

    :param dict_node: The parsed ``TABLE`` dict.
    :param path: Source path, for error messages only.
    :returns: Mapping of table name to the first positional/keyword scope
        argument of its ``TablePolicy(...)`` call.
    :raises SentinelCheckError: If an entry is not the expected
        ``"name": TablePolicy("scope", ...)`` shape.
    """
    policies: dict[str, str] = {}
    for key, value in zip(dict_node.keys, dict_node.values, strict=True):
        if not (isinstance(key, ast.Constant) and isinstance(key.value, str)):
            raise SentinelCheckError(f"{path}: TABLE key is not a string literal")
        scope = _policy_scope(value)
        if scope is None:
            raise SentinelCheckError(
                f"{path}: TABLE[{key.value!r}] is not a TablePolicy('<scope>', ...) call"
            )
        policies[key.value] = scope
    return policies


def _policy_scope(value: ast.expr) -> str | None:
    """Return the scope literal of a ``TablePolicy(...)`` call node, else None."""
    if not (isinstance(value, ast.Call) and isinstance(value.func, ast.Name)):
        return None
    if value.func.id != "TablePolicy":
        return None
    if value.args and isinstance(value.args[0], ast.Constant):
        arg = value.args[0].value
        return arg if isinstance(arg, str) else None
    for keyword in value.keywords:
        if keyword.arg == "scope" and isinstance(keyword.value, ast.Constant):
            arg = keyword.value.value
            return arg if isinstance(arg, str) else None
    return None
