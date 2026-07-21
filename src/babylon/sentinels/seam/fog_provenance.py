"""Seam Sensor 4 (fog field mirror) — the Py<->TS field-list drift gate.

``src/babylon/projection/fog/filter.py``'s ``POLITICAL_FIELDS``/
``ORG_INTERNAL_STATE_FIELDS`` (the field vocabulary ``apply_fog`` ever gates —
relocated from ``web/game/fog/`` by Program 24 P1 WO-1, which left a re-export
shim this AST check cannot read literals through) and the frontend's
``src/frontend/src/lib/inspect/fogFields.ts`` ``FOG_FIELD_LABELS`` are two
independently hand-maintained lists that must agree exactly. ``fogFields.ts``'s
own doc comment names the exact risk this sensor closes: "same hand-pinned
single-source-of-truth pattern ``lib/inspect/provenance.ts`` uses ... no runtime
coupling, so nothing fails loudly if it drifts." A field added on only one side
means the UI either leaks a fogged field it has no label context for, or shows a
phantom label for a field the backend never treats as political.

This module is Sensor 3's (``provenance.py``) exact skeleton — ``ast`` for the
Python side, a regex over the ``.ts`` source for the frontend side — adapted for
a TS ``Record<string, string>`` object literal instead of an ``interface``
declaration (``FOG_FIELD_LABELS`` has no type shape to declare fields against;
its own object-literal KEYS are the declared vocabulary). Unlike Sensor 3
(advisory: a phantom map-emitter field awaits an owner ruling before it can
gate), this check is GATING — the fog political-field vocabulary is a closed,
already-agreed set (11 fields both sides, verified in the grounding
investigation), so any drift is an unambiguous defect, not a judgment call.

Layer-0.5 pure Python (``ast`` + regex, no engine, no Node); lives in the
always-on fast-gate via the seam CLI (``mise run check:seams``).
"""

from __future__ import annotations

import re
from pathlib import Path

from babylon.sentinels._ast import literal_str_tuple
from babylon.sentinels.base import SentinelCheckError

#: Repo root (this file is ``<root>/src/babylon/sentinels/seam/fog_provenance.py``).
_REPO_ROOT: Path = Path(__file__).resolve().parents[4]

_FILTER_PATH: Path = _REPO_ROOT / "src" / "babylon" / "projection" / "fog" / "filter.py"
_FOG_FIELDS_TS_PATH: Path = (
    _REPO_ROOT / "src" / "frontend" / "src" / "lib" / "inspect" / "fogFields.ts"
)

#: The two Python-side tuple literals whose union is the full political-field
#: vocabulary ``apply_fog`` ever gates (``ORG_POLITICAL_FIELDS`` is just their
#: concatenation — reading the two source tuples directly is simpler than
#: resolving a ``BinOp`` of two ``Name`` references over AST).
_POLITICAL_FIELDS_VAR: str = "POLITICAL_FIELDS"
_ORG_INTERNAL_STATE_FIELDS_VAR: str = "ORG_INTERNAL_STATE_FIELDS"

#: The frontend's mirrored label map.
_FOG_FIELD_LABELS_CONST: str = "FOG_FIELD_LABELS"


def _declared_object_literal_keys(path: Path, const_name: str) -> set[str]:
    """Extract the string keys of a TS ``export const NAME: Record<...> = {...}``.

    A small regex over the ``.ts`` source (no Node/TS parser at layer 0.5,
    mirroring :func:`~babylon.sentinels.seam.provenance._declared_interface_fields`):
    take the ``export const <name>: Record<...> = { ... }`` block and read each
    ``key:`` identifier line. ``FOG_FIELD_LABELS``'s keys are simple bare
    identifiers (never quoted), so a regex is sufficient.

    :param path: The ``fogFields.ts`` source.
    :param const_name: The exported const whose object-literal keys to read.
    :returns: The declared key set.
    :raises SentinelCheckError: If the file is missing, or the const is absent
        (a renamed/removed const must fail loud, never silently report empty).
    """
    try:
        source = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SentinelCheckError(f"cannot read {path}: {exc}") from exc

    match = re.search(
        rf"export\s+const\s+{re.escape(const_name)}\s*:\s*Record<[^>]*>\s*=\s*\{{(.*?)\}}",
        source,
        re.DOTALL,
    )
    if match is None:
        raise SentinelCheckError(f"{path}: const {const_name!r} not found (renamed/removed?)")
    body = match.group(1)
    return set(re.findall(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*:", body, re.MULTILINE))


def check_fog_field_mirror(
    filter_path: Path = _FILTER_PATH,
    ts_path: Path = _FOG_FIELDS_TS_PATH,
) -> list[str]:
    """GATING: ``filter.py``'s political field set vs ``fogFields.ts``'s mirror.

    Diffs the union of ``POLITICAL_FIELDS``/``ORG_INTERNAL_STATE_FIELDS``
    (Python, the engine-side gate ``apply_fog`` actually enforces) against the
    key set of ``FOG_FIELD_LABELS`` (TypeScript, the frontend's hand-pinned
    mirror) in both directions. A field on only the Python side means the
    frontend has no label context for a field it may receive already masked or
    already live; a field on only the TS side is a phantom label for a field
    the backend never gates as political.

    :param filter_path: The ``filter.py`` source (injectable so tests can
        supply a deliberately-drifted fixture to prove the check reds).
    :param ts_path: The ``fogFields.ts`` source (injectable).
    :returns: Sorted violation strings naming the missing/extra field per side
        (empty when the two sets match exactly).
    :raises SentinelCheckError: If either source cannot be read/parsed, or
        either declared symbol cannot be found — a moved/renamed source must
        fail loud, never silently report a clean match.
    """
    political = set(literal_str_tuple(filter_path, _POLITICAL_FIELDS_VAR))
    org_internal = set(literal_str_tuple(filter_path, _ORG_INTERNAL_STATE_FIELDS_VAR))
    python_fields = political | org_internal

    ts_fields = _declared_object_literal_keys(ts_path, _FOG_FIELD_LABELS_CONST)

    violations: list[str] = []
    for missing in sorted(python_fields - ts_fields):
        violations.append(
            f"{missing!r} is in filter.py's POLITICAL_FIELDS/ORG_INTERNAL_STATE_FIELDS "
            f"but fogFields.ts's FOG_FIELD_LABELS has no entry for it — the frontend "
            f"has no label for a field it may receive from apply_fog"
        )
    for extra in sorted(ts_fields - python_fields):
        violations.append(
            f"{extra!r} is a key in fogFields.ts's FOG_FIELD_LABELS but filter.py's "
            f"POLITICAL_FIELDS/ORG_INTERNAL_STATE_FIELDS has no such field — a phantom "
            f"label for a field the backend never treats as political"
        )
    return violations
