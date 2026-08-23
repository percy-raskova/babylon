"""The ADR177-governed verb 3×3 — a sentinel, not documentation.

The Director ratified the matrix AS DRAFTED (live session 2026-07-30,
recorded on #398; ADR177): nine registered resolvers over the canonical
axes, with two DECLARED structural facts —

- **the Iskra double cell**: Build-org × Population holds BOTH ``educate``
  and ``campaign`` (agitation and propaganda are distinct practices; the
  matrix records the distinction rather than flattening it);
- **the honest empty cell**: Manage-resources × Organization holds NO
  verb until the funding train (rulings 14/38's doctrine-pair surface)
  lands it — declared, never papered over.

These pins make the ratification byte-checkable: moving a verb without the
Director ruling that ADR177 requires turns the gate red. A new or changed
governed vocabulary follows Constitution v4 Article VIII's Director ceremony,
schema/conformance, and recording-ADR path.
"""

from __future__ import annotations

import pytest

from babylon.game.actions.matrix import (
    MATRIX_COLUMNS,
    MATRIX_ROWS,
    RATIFIED_MATRIX,
    verbs_in_matrix,
)
from babylon.game.actions.registry import ACTION_REGISTRY
from babylon.projection.verbs.preview import CANONICAL_VERBS, VERB_TO_ACTION_TYPE

pytestmark = [pytest.mark.unit]


class TestRatifiedShape:
    def test_axes_are_adr177_governed(self) -> None:
        assert MATRIX_ROWS == ("build_org", "project_power", "manage_resources")
        assert MATRIX_COLUMNS == ("organization", "population", "other_actors")

    def test_all_nine_cells_declared(self) -> None:
        assert set(RATIFIED_MATRIX) == {
            (row, column) for row in MATRIX_ROWS for column in MATRIX_COLUMNS
        }

    def test_matrix_covers_exactly_the_canonical_verbs_once_each(self) -> None:
        placed = [verb for cell in RATIFIED_MATRIX.values() for verb in cell]
        assert len(placed) == len(set(placed)), "a verb may occupy only one cell"
        assert set(placed) == CANONICAL_VERBS

    def test_the_iskra_double_cell(self) -> None:
        assert RATIFIED_MATRIX[("build_org", "population")] == ("educate", "campaign")

    def test_the_declared_empty_cell(self) -> None:
        """Manage-resources × Organization: empty until the funding train."""
        assert RATIFIED_MATRIX[("manage_resources", "organization")] == ()

    def test_single_verb_cells_as_ratified(self) -> None:
        assert RATIFIED_MATRIX[("build_org", "organization")] == ("reproduce",)
        assert RATIFIED_MATRIX[("build_org", "other_actors")] == ("negotiate",)
        assert RATIFIED_MATRIX[("project_power", "organization")] == ("move",)
        assert RATIFIED_MATRIX[("project_power", "population")] == ("mobilize",)
        assert RATIFIED_MATRIX[("project_power", "other_actors")] == ("attack",)
        assert RATIFIED_MATRIX[("manage_resources", "population")] == ("aid",)
        assert RATIFIED_MATRIX[("manage_resources", "other_actors")] == ("investigate",)


class TestEveryCellVerbIsALiveResolver:
    """The matrix names only verbs the engine actually resolves — a cell
    naming a resolver-less verb would ratify dead surface (the exact
    failure ActionType.STRIKE's no-resolver correction documented)."""

    def test_every_matrix_verb_has_a_live_registry_row(self) -> None:
        for verb in verbs_in_matrix():
            spec = ACTION_REGISTRY[verb]
            assert spec.status == "LIVE", f"{verb} is not LIVE"
            assert spec.effect_ref == VERB_TO_ACTION_TYPE[verb].value

    def test_verbs_in_matrix_is_sorted_and_complete(self) -> None:
        assert verbs_in_matrix() == tuple(sorted(CANONICAL_VERBS))
