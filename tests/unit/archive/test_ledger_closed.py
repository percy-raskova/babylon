"""Ledger-closure sentinel (Program 24, The Archive — WO-52 P4 cutover gate).

``specs/24-archive/test-port-ledger.md`` claims, in prose, that every
behavioral assertion the legacy web client's disabled test estate makes has
a disposition — a landed contract test, an in-flight work order, or an
honest ``GAP``. A prose claim can rot silently the moment someone edits the
ledger without re-checking it against the source files. This module makes
the claim mechanically checked instead:

1. Every ``^class Test...`` in ``tests/unit/web/test_engine_bridge.py`` is
   named somewhere in the ledger.
2. Every ``src/frontend/e2e/*.spec.ts`` filename is named somewhere in the
   ledger.
3. Every disposition cell across the ledger's three per-item tables uses the
   closed vocabulary the ledger itself declares: ``PORTED`` / ``REWRITTEN``
   / ``RE-GUARDED`` / ``CARRIED(...)`` / ``RETIRED`` / ``GAP``.
4. The four former ``GAP`` rows (cutover blockers: the economy Wc-Vc
   aggregates, the economy chip contract, the field-state read-model, and
   balkanization factions) were CLOSED by the T3 gap-projections train
   (U2/U3/U4, ADR125) under the BD ruling "4 LOUD ledger gaps -> BUILD all"
   (ratified master plan, 2026-07-21). The check now pins the closed state:
   the four classes stay NAMED (as ``REWRITTEN (T3 ...)`` rows) and ZERO
   ``GAP`` cells remain — a reappearing ``GAP`` is a regression.
5. The checker is itself mutation-tested: each check is proven to fail on a
   ledger copy with the fact it depends on removed.

Kept local to this test module rather than promoted to
``src/babylon/sentinels``: this is a one-shot contract over one markdown
document, not a repo-wide static-analysis rule.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parents[3]
_ENGINE_BRIDGE_TEST = _REPO_ROOT / "tests" / "unit" / "web" / "test_engine_bridge.py"
_E2E_DIR = _REPO_ROOT / "src" / "frontend" / "e2e"
_LEDGER = _REPO_ROOT / "specs" / "24-archive" / "test-port-ledger.md"

# Repo loop-bound rule (CLAUDE.md Power-of-10 #2): both scans are capped well
# above any plausible real count, so the bound is provably never hit rather
# than provably sufficient by luck.
_MAX_LINES = 10_000
_MAX_SPEC_FILES = 200

_CLASS_RE = re.compile(r"^class (Test\w+)")

# The ledger's own declared vocabulary (test-port-ledger.md lines 10-13).
_DISPOSITION_RE = re.compile(r"^(PORTED|REWRITTEN|RE-GUARDED|RETIRED|GAP)\b|^CARRIED\s*\(")

# The four former cutover blockers (test-port-ledger.md "LOUD" section) —
# closed by T3 U2/U3/U4 (ADR125); must stay NAMED as REWRITTEN (T3 ...) rows.
_LOUD_GAP_CLASSES = (
    "TestEconomyDashboardFundamentalTheorem",
    "TestEconomyDashboardChipContract",
    "TestGetFieldState",
    "TestBalkanizationMapFields",
)


def _extract_classes(source_text: str) -> list[str]:
    """Every ``^class Test...`` name in *source_text*, in file order."""
    lines = source_text.splitlines()
    assert len(lines) <= _MAX_LINES, "test_engine_bridge.py grew past the scan's static bound"
    return [m.group(1) for line in lines[:_MAX_LINES] if (m := _CLASS_RE.match(line))]


def _missing_names(names: list[str], ledger_text: str) -> list[str]:
    """Names from *names* that do not appear anywhere in *ledger_text*."""
    return [name for name in names if name not in ledger_text]


def _slice_between(text: str, start_marker: str, end_marker: str) -> str:
    """The substring of *text* strictly between two literal section markers."""
    start = text.index(start_marker) + len(start_marker)
    end = text.index(end_marker, start)
    return text[start:end]


def _table_disposition_cells(table_block: str, disposition_index: int) -> list[str]:
    """Disposition-column cells from one markdown table block.

    Skips header and ``|---|---|`` separator rows. *disposition_index* is
    the 0-based pipe-delimited column position, which differs across the
    ledger's table shapes (confirmed by direct inspection, not guessed):
    4 columns in the main ``## Ledger`` table (index 2) and the ``### New
    dispositions`` table (index 3), 3 columns in ``### Already carried by
    the Ledger rows above`` (index 2).
    """
    lines = table_block.splitlines()
    assert len(lines) <= _MAX_LINES
    cells: list[str] = []
    for line in lines[:_MAX_LINES]:
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        inner = stripped.strip("|")
        if set(inner.replace("|", "").strip()) <= set("-: "):
            continue  # separator row, e.g. |---|---|---|
        parts = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(parts) <= disposition_index:
            continue
        cell = parts[disposition_index]
        if cell == "Disposition":
            continue  # header row
        cells.append(cell)
    return cells


def _all_disposition_cells(ledger_text: str) -> list[str]:
    """Every disposition cell across the ledger's three per-item tables."""
    main_table = _slice_between(ledger_text, "## Ledger\n", "## Deviations recorded")
    carried_table = _slice_between(
        ledger_text,
        "### Already carried by the Ledger rows above (17)\n",
        "### New dispositions",
    )
    new_table = _slice_between(ledger_text, "### New dispositions (46)\n", "### LOUD")
    return (
        _table_disposition_cells(main_table, 2)
        + _table_disposition_cells(carried_table, 2)
        + _table_disposition_cells(new_table, 3)
    )


def _engine_bridge_classes() -> list[str]:
    return _extract_classes(_ENGINE_BRIDGE_TEST.read_text(encoding="utf-8"))


def _e2e_spec_filenames() -> list[str]:
    files = sorted(_E2E_DIR.glob("*.spec.ts"))
    assert len(files) <= _MAX_SPEC_FILES
    return [path.name for path in files]


# ---------------------------------------------------------------------------
# 1. Every engine_bridge test class is dispositioned.
# ---------------------------------------------------------------------------


class TestEngineBridgeClassesAllDispositioned:
    def test_class_count_matches_the_wo52_baseline(self) -> None:
        # A drift in this count (a class added/removed/renamed) means the
        # ledger's own "all 63 disabled classes" claim needs re-verifying,
        # not that this bound should silently move.
        assert len(_engine_bridge_classes()) == 63

    def test_every_class_is_named_somewhere_in_the_ledger(self) -> None:
        classes = _engine_bridge_classes()
        assert classes, "the class extractor found nothing — check the regex against the file"
        ledger_text = _LEDGER.read_text(encoding="utf-8")
        missing = _missing_names(classes, ledger_text)
        assert missing == [], f"undispositioned engine_bridge classes: {missing}"


# ---------------------------------------------------------------------------
# 2. Every e2e spec file is dispositioned.
# ---------------------------------------------------------------------------


class TestE2ESpecsAllDispositioned:
    def test_spec_file_count_matches_the_wo52_baseline(self) -> None:
        assert len(_e2e_spec_filenames()) == 11

    def test_every_spec_file_is_named_somewhere_in_the_ledger(self) -> None:
        specs = _e2e_spec_filenames()
        assert specs, "the e2e glob found nothing — check src/frontend/e2e/ exists"
        ledger_text = _LEDGER.read_text(encoding="utf-8")
        missing = _missing_names(specs, ledger_text)
        assert missing == [], f"undispositioned e2e spec files: {missing}"


# ---------------------------------------------------------------------------
# 3. The disposition vocabulary is closed.
# ---------------------------------------------------------------------------


class TestDispositionVocabularyClosed:
    def test_every_disposition_cell_uses_the_closed_vocabulary(self) -> None:
        ledger_text = _LEDGER.read_text(encoding="utf-8")
        cells = _all_disposition_cells(ledger_text)
        # 28 (main Ledger table, post-WO-52-sentinel additions) + 17 (already
        # carried) + 46 (new dispositions) = 91 as of this writing.
        assert len(cells) >= 91, f"expected >=91 parsed disposition rows, got {len(cells)}"
        bad = [cell for cell in cells if not _DISPOSITION_RE.match(cell)]
        assert bad == [], f"disposition cells outside the closed vocabulary: {bad}"


# ---------------------------------------------------------------------------
# 4. The four LOUD rows are CLOSED (T3 U2/U3/U4) and stay that way.
# ---------------------------------------------------------------------------


class TestLoudGapsClosed:
    def test_all_four_former_gap_classes_stay_named(self) -> None:
        ledger_text = _LEDGER.read_text(encoding="utf-8")
        missing = _missing_names(list(_LOUD_GAP_CLASSES), ledger_text)
        assert missing == [], f"a closed cutover-blocker silently vanished: {missing}"

    def test_zero_rows_are_tagged_gap(self) -> None:
        # T3 closed all four LOUD gaps (ADR125); the honest-GAP vocabulary
        # stays legal for FUTURE rows, but today a GAP cell reappearing means
        # either a regression or an undispositioned new gap — both loud.
        ledger_text = _LEDGER.read_text(encoding="utf-8")
        cells = _all_disposition_cells(ledger_text)
        gap_cells = [cell for cell in cells if cell.startswith("GAP")]
        assert gap_cells == [], f"expected zero GAP rows post-T3, found: {gap_cells}"

    def test_all_four_closures_are_tagged_rewritten_t3(self) -> None:
        ledger_text = _LEDGER.read_text(encoding="utf-8")
        for marker in ("REWRITTEN (T3 U2)", "REWRITTEN (T3 U3)", "REWRITTEN (T3 U4)"):
            assert marker in ledger_text, f"missing closure disposition: {marker}"


# ---------------------------------------------------------------------------
# 5. Mutation-validate the checker itself (STANDING RULE: sentinel every
#    error class — a checker that cannot fail is not a checker).
# ---------------------------------------------------------------------------


class TestSentinelCatchesMutation:
    """Each check above proven RED against a ledger with the fact removed."""

    def test_containment_check_reds_when_a_class_is_dropped(self) -> None:
        real_ledger = _LEDGER.read_text(encoding="utf-8")
        assert "TestWireFeed" in real_ledger  # sanity: present once, no substring collisions
        mutated = real_ledger.replace("TestWireFeed", "")
        assert _missing_names(["TestWireFeed"], mutated) == ["TestWireFeed"]

    def test_containment_check_reds_when_a_spec_file_is_dropped(self) -> None:
        real_ledger = _LEDGER.read_text(encoding="utf-8")
        assert "first-session.spec.ts" in real_ledger
        mutated = real_ledger.replace("first-session.spec.ts", "")
        assert _missing_names(["first-session.spec.ts"], mutated) == ["first-session.spec.ts"]

    def test_vocabulary_check_reds_on_an_invented_disposition_word(self) -> None:
        real_ledger = _LEDGER.read_text(encoding="utf-8")
        assert "| PORTED (WO-27) |" in real_ledger  # the TestWireFeed row's disposition cell
        mutated = real_ledger.replace("| PORTED (WO-27) |", "| SHIPPED (WO-27) |")
        cells = _all_disposition_cells(mutated)
        bad = [cell for cell in cells if not _DISPOSITION_RE.match(cell)]
        assert bad == ["SHIPPED (WO-27)"]

    def test_closure_check_reds_when_a_closed_row_regresses_to_gap(self) -> None:
        # Mutate on the disposition CELL, not the row's full prose (the prose
        # drifted once already and broke the old fixture) — flipping the
        # balkanization closure back to GAP must red the zero-GAP check.
        real_ledger = _LEDGER.read_text(encoding="utf-8")
        closed_cell = "| REWRITTEN (T3 U4) |"
        assert closed_cell in real_ledger, "the U4 closure cell drifted — update the fixture"
        mutated = real_ledger.replace(closed_cell, "| GAP (LOUD) |")
        cells = _all_disposition_cells(mutated)
        gap_cells = [cell for cell in cells if cell.startswith("GAP")]
        assert gap_cells == ["GAP (LOUD)"], "a regressed GAP cell must be seen by the checker"

    def test_containment_check_reds_when_a_closed_class_vanishes(self) -> None:
        # The class name appears in its REWRITTEN row AND the struck-through
        # LOUD prose item (deliberate redundancy) — scrub every mention and
        # the containment check must red.
        real_ledger = _LEDGER.read_text(encoding="utf-8")
        assert real_ledger.count("TestBalkanizationMapFields") >= 2
        mutated = real_ledger.replace("TestBalkanizationMapFields", "")
        missing = _missing_names(["TestBalkanizationMapFields"], mutated)
        assert missing == ["TestBalkanizationMapFields"]
