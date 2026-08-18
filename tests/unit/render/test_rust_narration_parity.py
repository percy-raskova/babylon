"""Cross-language severity/narration parity: the Rust client's transcribed
severity taxonomy and narration templates must track their frozen Python
sources (B3 wave-1 Task 4.6, plan
`docs/superpowers/plans/2026-08-17-b3-null-hypothesis-viewer.md` §2.2).

Modelled line-for-line on ``test_rust_theme_parity.py`` (the §9b palette
guard): ``severity.rs``/``narration.rs`` are an FFI boundary no import can
cross, so this guard PARSES the Rust source instead of importing it.

**Two checks.**

1. Every ``SeverityRow`` in ``severity.rs::SEVERITY_TAXONOMY`` must name a
   real ``event_severity.py::SEVERITY_TAXONOMY`` member with the SAME
   ``(kind, terminal_proximity)`` — the identical drift class
   ``test_rust_constant_matches_truecolor_palette`` already guards for
   ``palette.rs``.
2. Every ``{slot}`` a ``narration.rs::NarrationSpec``'s ``template``/
   ``because`` string reads must be a wire key
   ``babylon.engine.event_builders.EVENT_BUILDERS``' OWN builder for that
   ``EventType`` also reads — the same static check
   ``test_chronicle_adapter.py::
   test_summary_builders_only_read_wire_keys_event_builders_also_reads``
   already performs Python-side, extended cross-language. A NARROW, CITED
   exemption list covers the handful of slots BSL's payload-flattening
   (``decomposition.bsl:377-386``'s ``population-transferred-to-*``) or
   ``control_ratio.py::_emit_crisis``'s own raw ``payload={...}`` dict
   (``max_controllable``/``control_capacity``, both real wire keys
   ``ControlRatioCrisisEvent``'s builder simply never reads) makes
   unverifiable against ``EVENT_BUILDERS`` alone — never a silent gap.
"""

from __future__ import annotations

import ast
import inspect
import re
import types
from pathlib import Path

import pytest

from babylon.engine import event_builders as _event_builders_module
from babylon.models.event_severity import (
    SEVERITY_TAXONOMY,
    EventKind,
    TerminalProximity,
)

_CRATE_SRC = Path(__file__).resolve().parents[3] / "rust" / "crates" / "babylon-client" / "src"
_SEVERITY_RS = _CRATE_SRC / "severity.rs"
_NARRATION_RS = _CRATE_SRC / "narration.rs"

# --------------------------------------------------------------------------- #
# severity.rs parsing                                                         #
# --------------------------------------------------------------------------- #

#: `rustfmt` lays `SeverityRow { .. }` out ONE FIELD PER LINE once the
#: one-line form exceeds its width (as every row here does) — `\s*`
#: between tokens (not a literal `" "`) and `re.DOTALL` tolerate that
#: layout without caring which shape is on disk today.
_SEVERITY_ROW_RE = re.compile(
    r'SeverityRow\s*\{\s*event_type:\s*"(?P<event_type>[A-Z_]+)",\s*'
    r"kind:\s*EventKind::(?P<kind>\w+),\s*"
    r"proximity:\s*TerminalProximity::(?P<proximity>\w+),",
    re.DOTALL,
)

_RUST_KIND_TO_PYTHON: dict[str, EventKind] = {
    "Alarm": EventKind.ALARM,
    "Crossing": EventKind.CROSSING,
    "Flow": EventKind.FLOW,
    "Act": EventKind.ACT,
}
_RUST_PROXIMITY_TO_PYTHON: dict[str, TerminalProximity] = {
    "TerminalAdjacent": TerminalProximity.TERMINAL_ADJACENT,
    "TerminalApproach": TerminalProximity.TERMINAL_APPROACH,
    "IntraLevel": TerminalProximity.INTRA_LEVEL,
    "Na": TerminalProximity.NA,
}


def _rust_severity_rows() -> dict[str, tuple[EventKind, TerminalProximity]]:
    """Parse ``severity.rs``'s one-line ``SeverityRow`` entries."""
    source = _SEVERITY_RS.read_text(encoding="utf-8")
    found = {
        m["event_type"]: (
            _RUST_KIND_TO_PYTHON[m["kind"]],
            _RUST_PROXIMITY_TO_PYTHON[m["proximity"]],
        )
        for m in _SEVERITY_ROW_RE.finditer(source)
    }
    assert found, f"no SeverityRow rows parsed from {_SEVERITY_RS}"
    return found


_PYTHON_TAXONOMY_BY_EVENT: dict[str, tuple[EventKind, TerminalProximity]] = {
    row.event_type.name: (row.kind, row.terminal_proximity) for row in SEVERITY_TAXONOMY
}


@pytest.mark.parametrize(("event_type", "expected"), sorted(_rust_severity_rows().items()))
def test_rust_severity_row_matches_python_taxonomy(
    event_type: str, expected: tuple[EventKind, TerminalProximity]
) -> None:
    """Each ``severity.rs`` row's ``(kind, proximity)`` equals
    ``event_severity.py::SEVERITY_TAXONOMY``'s own row for the same
    ``EventType``."""
    assert event_type in _PYTHON_TAXONOMY_BY_EVENT, (
        f"{event_type} is not a member of event_severity.py's own SEVERITY_TAXONOMY — "
        "severity.rs must transcribe a real row, never invent one"
    )
    assert _PYTHON_TAXONOMY_BY_EVENT[event_type] == expected, (
        f"{event_type}: severity.rs declares {expected} but event_severity.py declares "
        f"{_PYTHON_TAXONOMY_BY_EVENT[event_type]} — update the Rust side (event_severity.py "
        "is the SSOT)"
    )


def test_all_twelve_transcribed_severity_rows_are_present() -> None:
    """§2.2's own table names exactly 12 rows — an unmapped/missing row is
    unguarded drift."""
    rows = _rust_severity_rows()
    assert len(rows) == 12, (
        f"expected 12 transcribed severity rows, got {len(rows)}: {sorted(rows)}"
    )


# --------------------------------------------------------------------------- #
# narration.rs parsing                                                        #
# --------------------------------------------------------------------------- #

_NARRATION_SPEC_RE = re.compile(
    r"NarrationSpec\s*\{\s*"
    r'event_type:\s*"(?P<event_type>[A-Z_]+)",\s*'
    r"subject_key:\s*(?:Some\(\"(?P<subject_key>[a-z0-9-]+)\"\)|None),\s*"
    r'template:\s*(?:"(?P<template>(?:[^"\\]|\\.)*)"|(?P<template_const>[A-Z_]+)),\s*'
    r'because:\s*(?:Some\("(?P<because>(?:[^"\\]|\\.)*)"\)|None),\s*'
    r'source:\s*"(?P<source>[^"]*)",\s*'
    r"\}",
    re.DOTALL,
)

#: A real `{slot}` name always starts with a letter (`subject`, `pop-d`,
#: `avg-organization`, …) — requiring that excludes the ONE other `{...}`
#: shape these strings contain: a Rust `\u{XXXX}` unicode escape (e.g. the
#: em dash `\u{2014}` several `because:` lines use), whose braced part is
#: bare hex digits, never a slot.
_SLOT_RE = re.compile(r"\{([a-z][a-z0-9-]*)\}")


class _NarrationRow:
    def __init__(self, event_type: str, template: str | None, because: str | None) -> None:
        self.event_type = event_type
        self.template = template
        self.because = because

    def slots(self) -> set[str]:
        """Every `{key}` this row's template/because reference, `{subject}`
        excluded (the one reserved non-wire slot name) and kebab-case
        normalized to the Python side's snake_case."""
        text = " ".join(part for part in (self.template, self.because) if part)
        return {name.replace("-", "_") for name in _SLOT_RE.findall(text) if name != "subject"}


def _rust_narration_rows() -> list[_NarrationRow]:
    """Parse ``narration.rs``'s ``NarrationSpec`` block literals."""
    source = _NARRATION_RS.read_text(encoding="utf-8")
    rows = [
        _NarrationRow(m["event_type"], m["template"], m["because"])
        for m in _NARRATION_SPEC_RE.finditer(source)
    ]
    assert rows, f"no NarrationSpec rows parsed from {_NARRATION_RS}"
    return rows


def _dict_literal_assigned_to(module: types.ModuleType, name: str) -> ast.Dict:
    """Parse ``module``'s source and return the ``ast.Dict`` literal bound
    to the module-level name ``name``. (Mirrors ``test_chronicle_adapter.
    py``'s own helper of the same name — reimplemented locally so this
    file stays self-contained, matching this repo's own no-cross-test-file-
    import convention.)"""
    tree = ast.parse(inspect.getsource(module))
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == name
            and isinstance(node.value, ast.Dict)
        ):
            return node.value
    raise AssertionError(f"no top-level `{name}: ... = {{...}}` dict literal in {module.__name__}")


def _wire_keys_by_event_type(dict_literal: ast.Dict) -> dict[str, frozenset[str]]:
    """Map each ``EventType.X`` key to the frozenset of string-literal keys
    its builder lambda reads via ``payload.get("key", ...)``. Loop bound:
    ``len(dict_literal.keys)``."""
    result: dict[str, frozenset[str]] = {}
    pairs = zip(dict_literal.keys, dict_literal.values, strict=True)
    for key_node, value_node in pairs:  # loop bound: len(EventType)
        assert isinstance(key_node, ast.Attribute), f"expected `EventType.X` key, got {key_node}"
        keys: set[str] = set()
        for call in ast.walk(value_node):  # loop bound: len(ast.walk(value_node))
            if (
                isinstance(call, ast.Call)
                and isinstance(call.func, ast.Attribute)
                and call.func.attr == "get"
                and call.args
                and isinstance(call.args[0], ast.Constant)
                and isinstance(call.args[0].value, str)
            ):
                keys.add(call.args[0].value)
        result[key_node.attr] = frozenset(keys)
    return result


_EVENT_BUILDERS_WIRE_KEYS: dict[str, frozenset[str]] = _wire_keys_by_event_type(
    _dict_literal_assigned_to(_event_builders_module, "_BUILDERS")
)

#: (event_type, slot) pairs `EVENT_BUILDERS` alone cannot verify, each
#: cited to the REAL ground truth that does — never a silent gap (the
#: `_SWEEP_EXEMPTIONS` shape `test_rust_theme_parity.py` already uses).
_NARRATION_SLOT_EXEMPTIONS: dict[tuple[str, str], str] = {
    ("CLASS_DECOMPOSITION", "population_transferred_to_enforcer"): (
        "decomposition.bsl:383-384 (D171 item 1): BSL flattens Python's nested "
        "`population_transferred: {to_enforcer, to_proletariat}` dict into two flat "
        "wire keys; EVENT_BUILDERS' own ClassDecompositionEvent never reads the "
        "nested dict either, so there is no EVENT_BUILDERS wire key to check against — "
        "verified instead against decomposition.bsl's own emit form directly."
    ),
    ("CLASS_DECOMPOSITION", "population_transferred_to_proletariat"): (
        "decomposition.bsl:383-384 (D171 item 1) — same as the enforcer row above."
    ),
    ("CONTROL_RATIO_CRISIS", "max_controllable"): (
        "control_ratio.py:196 (`_emit_crisis`'s own `payload={...}` dict literal): a "
        "REAL wire key on every CONTROL_RATIO_CRISIS payload, but ControlRatioCrisisEvent's "
        "EVENT_BUILDERS entry never reads it (event_builders.py:226-233) — verified "
        "instead against control_ratio.py's own raw payload dict."
    ),
    ("CONTROL_RATIO_CRISIS", "control_capacity"): (
        "control_ratio.py:195 (`_emit_crisis`'s own `payload={...}` dict literal) — "
        "same as max_controllable above."
    ),
}


@pytest.mark.parametrize(
    ("event_type", "template_or_because"),
    [(row.event_type, part) for row in _rust_narration_rows() for part in ("template", "because")],
)
def test_narration_slots_are_wire_keys_event_builders_reads(
    event_type: str, template_or_because: str
) -> None:
    """Every ``{slot}`` a transcribed ``NarrationSpec`` row's template/
    because line reads must be a wire key ``EVENT_BUILDERS``' own builder
    for that ``EventType`` also reads — or a declared, cited exemption
    (see the module doc)."""
    rows = [row for row in _rust_narration_rows() if row.event_type == event_type]
    assert rows, f"no NarrationSpec row parsed for {event_type}"
    row = rows[0]
    text = row.template if template_or_because == "template" else row.because
    if text is None:
        pytest.skip(f"{event_type} declares no {template_or_because}")
    slots = {name.replace("-", "_") for name in _SLOT_RE.findall(text) if name != "subject"}
    engine_keys = _EVENT_BUILDERS_WIRE_KEYS.get(event_type, frozenset())
    for slot in sorted(slots):  # loop bound: len(slots), a handful per row
        exemption = _NARRATION_SLOT_EXEMPTIONS.get((event_type, slot))
        if exemption is not None:
            continue
        assert slot in engine_keys, (
            f"{event_type}.{{{slot}}}: not a wire key event_builders.EVENT_BUILDERS' own "
            f"builder for {event_type} reads ({sorted(engine_keys)}), and no exemption is "
            "declared in _NARRATION_SLOT_EXEMPTIONS — either the slot name drifted from the "
            "real wire key, or a new exemption is owed with its own citation"
        )


def test_eight_narration_rows_are_present() -> None:
    """The two wave-1 stories' own eight landed EventTypes — an unmapped/
    missing row is unguarded drift."""
    rows = _rust_narration_rows()
    assert len(rows) == 8, (
        f"expected 8 transcribed narration rows, got {len(rows)}: "
        f"{sorted(r.event_type for r in rows)}"
    )


def test_every_narration_slot_exemption_names_a_real_parsed_slot() -> None:
    """A stale exemption (its slot no longer appears in any row) is itself
    a drift signal — this test would rather fail loud than let one rot."""
    all_slots: set[tuple[str, str]] = set()
    for row in _rust_narration_rows():
        for slot in row.slots():
            all_slots.add((row.event_type, slot))
    stale = set(_NARRATION_SLOT_EXEMPTIONS) - all_slots
    assert not stale, f"stale narration slot exemption(s), no longer read by any row: {stale}"
