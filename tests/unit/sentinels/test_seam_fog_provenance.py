"""Seam Sensor 4 (fog field-list mirror) — the Py<->TS drift gate + efficacy proof.

``web/game/fog/filter.py``'s ``POLITICAL_FIELDS``/``ORG_INTERNAL_STATE_FIELDS``
and ``src/frontend/src/lib/inspect/fogFields.ts``'s ``FOG_FIELD_LABELS`` are two
independently hand-maintained lists that must agree exactly: a field added on
only one side means the UI either leaks a fogged field with no label, or shows
a phantom label for a field the backend never gates. Nothing runtime-couples
them (``fogFields.ts``'s own doc comment says so), so this static AST+regex
diff — Sensor 3's ``provenance.py`` pattern, adapted for a TS object literal
instead of an interface — is the only thing that catches the drift.

Verifies (1) the live tree agrees today (no drift), and (2) the check is not
vacuous: it reds on a planted phantom on EITHER side, names the field, and
fails loud (never silently empty) when either declared symbol is moved/renamed.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from babylon.sentinels.base import SentinelCheckError
from babylon.sentinels.seam import checks as sensor1
from babylon.sentinels.seam.fog_provenance import (
    _declared_object_literal_keys,
    check_fog_field_mirror,
)

pytestmark = pytest.mark.unit

# A minimal filter.py fixture mirroring the real POLITICAL_FIELDS/
# ORG_INTERNAL_STATE_FIELDS shape (3 fields total: 2 political, 1 org-internal).
_FAKE_FILTER_PY = """
POLITICAL_FIELDS: tuple[str, ...] = (
    "heat",
    "agitation",
)
ORG_INTERNAL_STATE_FIELDS: tuple[str, ...] = (
    "cohesion",
)
"""

# The matching fogFields.ts fixture — same 3 keys.
_FAKE_FOG_FIELDS_TS = """
export const FOG_FIELD_LABELS: Record<string, string> = {
  heat: "Repression Heat",
  agitation: "Mass Agitation",
  cohesion: "Organizational Cohesion",
};
"""


def _write(tmp_path: Path, name: str, text: str) -> Path:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def test_live_check_is_clean() -> None:
    """The real filter.py POLITICAL_FIELDS+ORG_INTERNAL_STATE_FIELDS union and
    the real fogFields.ts FOG_FIELD_LABELS keys match exactly today (11 fields
    each side, verified by direct enumeration in the grounding investigation)."""
    assert check_fog_field_mirror() == []


def test_reds_on_a_planted_python_phantom(tmp_path: Path) -> None:
    """A field added to filter.py's political lists but absent from
    fogFields.ts is named as missing-on-the-TS-side (efficacy, mutation (a))."""
    filter_py = _write(
        tmp_path,
        "filter.py",
        _FAKE_FILTER_PY.replace(
            '"agitation",\n)',
            '"agitation",\n    "totally_fake_field",\n)',
        ),
    )
    fog_fields_ts = _write(tmp_path, "fogFields.ts", _FAKE_FOG_FIELDS_TS)

    findings = check_fog_field_mirror(filter_path=filter_py, ts_path=fog_fields_ts)

    assert len(findings) == 1
    assert "totally_fake_field" in findings[0]
    assert "fogFields.ts" in findings[0]


def test_reds_on_a_removed_ts_field(tmp_path: Path) -> None:
    """Removing a key from fogFields.ts that filter.py still declares is named
    as missing-on-the-TS-side (efficacy, mutation (b))."""
    filter_py = _write(tmp_path, "filter.py", _FAKE_FILTER_PY)
    fog_fields_ts = _write(
        tmp_path,
        "fogFields.ts",
        _FAKE_FOG_FIELDS_TS.replace('  cohesion: "Organizational Cohesion",\n', ""),
    )

    findings = check_fog_field_mirror(filter_path=filter_py, ts_path=fog_fields_ts)

    assert len(findings) == 1
    assert "cohesion" in findings[0]


def test_reds_on_a_planted_ts_phantom(tmp_path: Path) -> None:
    """A key present in fogFields.ts with no matching filter.py field is named
    as a phantom label on the TS side (reverse-direction efficacy)."""
    filter_py = _write(tmp_path, "filter.py", _FAKE_FILTER_PY)
    fog_fields_ts = _write(
        tmp_path,
        "fogFields.ts",
        _FAKE_FOG_FIELDS_TS.replace(
            '  cohesion: "Organizational Cohesion",\n',
            '  cohesion: "Organizational Cohesion",\n  definitely_not_real: "Fake",\n',
        ),
    )

    findings = check_fog_field_mirror(filter_path=filter_py, ts_path=fog_fields_ts)

    assert len(findings) == 1
    assert "definitely_not_real" in findings[0]


def test_missing_political_fields_var_is_loud_not_empty(tmp_path: Path) -> None:
    """A filter.py missing POLITICAL_FIELDS entirely raises (III.11), never
    silently reports a clean match."""
    filter_py = _write(
        tmp_path,
        "filter.py",
        'ORG_INTERNAL_STATE_FIELDS: tuple[str, ...] = ("cohesion",)\n',
    )
    fog_fields_ts = _write(tmp_path, "fogFields.ts", _FAKE_FOG_FIELDS_TS)

    with pytest.raises(SentinelCheckError):
        check_fog_field_mirror(filter_path=filter_py, ts_path=fog_fields_ts)


def test_missing_fog_field_labels_const_is_loud_not_empty(tmp_path: Path) -> None:
    """A fogFields.ts with no FOG_FIELD_LABELS const raises, never reports empty."""
    fog_fields_ts = _write(
        tmp_path,
        "fogFields.ts",
        "export const SOMETHING_ELSE: Record<string, string> = { x: 'y' };\n",
    )
    with pytest.raises(SentinelCheckError):
        _declared_object_literal_keys(fog_fields_ts, "FOG_FIELD_LABELS")


def test_fog_field_mirror_is_registered_in_gating_checks() -> None:
    """WIRING: check_fog_field_mirror sits in the tuple checks.main() iterates.

    Proves the check is not merely defined but actually reachable from the
    sensor's own dispatch path — a deleted or mistyped ``_GATING_CHECKS`` entry
    must fail this test even though the direct-call tests above remain green.
    """
    wired_checks = [check for _, check in sensor1._GATING_CHECKS]
    assert check_fog_field_mirror in wired_checks
