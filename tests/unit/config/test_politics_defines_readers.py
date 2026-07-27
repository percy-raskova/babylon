"""No politics define ships unread (P25 U13, ADR140).

The commitment written into ``config/defines/politics.py``'s module
docstring since U7: every field names its consuming unit, and U13
re-verifies that no field ships unread (the Vol I U8 lesson — a
coefficient nobody reads is a modding surface that silently lies). This
sweep greps every declared ``PoliticsDefines`` field name across the
production read surfaces (engine + domain + ooda); a field with zero hits
is a red gate, not a doc note.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from babylon.config.defines.politics import PoliticsDefines

pytestmark = pytest.mark.unit

_SRC = Path(__file__).resolve().parents[3] / "src" / "babylon"
_READ_ROOTS = ("engine", "domain", "ooda")


def _production_text() -> str:
    chunks: list[str] = []
    for root in _READ_ROOTS:
        for path in sorted((_SRC / root).rglob("*.py")):
            chunks.append(path.read_text(encoding="utf-8"))
    return "\n".join(chunks)


def test_every_politics_define_has_a_production_reader() -> None:
    text = _production_text()
    unread = [name for name in PoliticsDefines.model_fields if f".{name}" not in text]
    assert unread == [], (
        f"politics defines with no production reader: {unread} — a coefficient "
        "nobody reads is a lying modding surface (III.1; the U13 sweep)"
    )
