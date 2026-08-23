"""The ADR177-governed verb 3×3 (Director, live session 2026-07-30; #398).

ADR177's axes, made canonical data: rows are the player-facing
motions (Build org / Project power / Manage resources), columns the
engine-facing targets (the org's own node / org↔class edges / org↔org
edges). Every canonical verb occupies exactly one cell; the ratification
recorded two structural facts as LAW rather than accidents:

- **the Iskra double cell** — Build-org × Population holds BOTH
  ``educate`` (the slow consciousness build) and ``campaign`` (the
  broadcast build): agitation and propaganda are distinct practices, and
  the paper-as-collective-organizer reading places both as Build-org
  motions.
- **the honest empty cell** — Manage-resources × Organization holds NO
  verb: nothing replenishes ``budget`` or mints ``PRESENCE`` until the
  funding train (rulings 14/38's doctrine-pair surface) lands its verb.

The matrix is the coordinate system the G3 cost/efficacy lever hangs
coefficients off (per doctrine-pair, per cell) and the sentinel
``tests/unit/game/actions/test_verb_matrix.py`` pins byte-for-byte:
moving a verb is a Director ruling, never a refactor.
"""

from __future__ import annotations

from typing import Final

MATRIX_ROWS: Final[tuple[str, str, str]] = ("build_org", "project_power", "manage_resources")
MATRIX_COLUMNS: Final[tuple[str, str, str]] = ("organization", "population", "other_actors")

#: The ratified assignment — cell -> verbs, in ratified order. The empty
#: tuple IS content: the declared-empty funding cell.
RATIFIED_MATRIX: Final[dict[tuple[str, str], tuple[str, ...]]] = {
    ("build_org", "organization"): ("reproduce",),
    ("build_org", "population"): ("educate", "campaign"),
    ("build_org", "other_actors"): ("negotiate",),
    ("project_power", "organization"): ("move",),
    ("project_power", "population"): ("mobilize",),
    ("project_power", "other_actors"): ("attack",),
    ("manage_resources", "organization"): (),
    ("manage_resources", "population"): ("aid",),
    ("manage_resources", "other_actors"): ("investigate",),
}


def verbs_in_matrix() -> tuple[str, ...]:
    """Every verb the matrix places, sorted (deterministic iteration key)."""
    return tuple(sorted(verb for cell in RATIFIED_MATRIX.values() for verb in cell))


def cell_of(verb: str) -> tuple[str, str]:
    """The (row, column) cell a canonical verb occupies.

    :raises KeyError: if ``verb`` is not placed by the ratified matrix —
        loud by design (III.11): an unplaced verb reaching a cell lookup
        means the matrix and the registry have drifted, which the
        sentinel forbids.
    """
    for cell, verbs in RATIFIED_MATRIX.items():  # loop bound: 9 cells
        if verb in verbs:
            return cell
    msg = f"verb {verb!r} is not placed by the ADR177-governed matrix"
    raise KeyError(msg)
