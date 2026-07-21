"""The key-figure read-model — ``project_key_figure``, a permanent honest-absence dossier.

Mirrors :mod:`babylon.projection.county`'s ``project_<kind>`` shape for
signature parity across Program 24 P2 Lane P, but projects a kind with **no
live producer at all** — unlike a county, where individual fields go absent
per-run while the kind itself is real.

**Independent verification (WO-21 mandate: run ``mise run check:vocabulary``
and confirm before claiming fields):**

- The backing ``KeyFigure`` model and ``WorldState.key_figures`` were
  formally retired under Constitution III.10
  (``ai/decisions/ADR084_retire_dead_models.yaml``, 2026-07-18, "Constitution
  III.10 formal retirement of dead speculative constructs"). No scenario,
  seed, OODA system, or bridge in this engine version ever populated
  ``WorldState.key_figures`` — verified independently there by a full-repo
  grep for ``key_figures=`` before the retirement, and the field no longer
  exists at all after it.
- ``babylon.models.enums.topology.NodeType.KEY_FIGURE`` was reclassified by
  the same ADR from the "production-stamped" section to "declared but NOT
  production-stamped" (joining ``hex``/``community``/``person``): it exists
  purely to type ``classify_topology()``'s COMMAND-edge test fixtures.
- ``babylon.sentinels.vocabulary.registry`` confirms the closure: ``key_figure``
  was dropped from ``MODEL_FIELDS_BY_NODE_TYPE`` (no declared attribute
  schema survives the retirement), and ``UNSTAMPED_QUERY_ALLOWLIST`` — the
  frozen, must-only-shrink registry of node types production queries but
  never stamps — does NOT carry ``"key_figure"``. Writing a graph query for
  ``NodeType.KEY_FIGURE`` in this module would therefore either (a) trip the
  vocabulary sentinel's "every queried type has a producer" rule, or (b)
  require growing a list explicitly documented as append-never. Neither is
  acceptable, so this module does not query the graph for key-figure nodes
  at all — the honest design for a kind with zero producers is to not
  pretend there is something to look up.

**One producer per field:**

.. list-table:: Field-producer rulings
   :header-rows: 1

   * - Field
     - Producer
   * - ``key_figure_id`` / ``verified_tick``
     - Caller-supplied identity/staleness anchor — no engine producer is
       needed or possible.
   * - *(every other conceivable field)*
     - **NONE.** ADR084 retired the sole model that would back one; there is
       no declared attribute schema left to read even inside a hand-built
       test/fixture graph that stamps a ``key_figure`` node.

Absence discipline (Constitution III.11): every dossier this module projects
is the honest-absence page — there is no field left to attribute, ever, for
any id, in this engine version. This is the WO-21
``mise run check:vocabulary`` finding made explicit and permanent in code,
not silently worked around with a query that would iterate an empty set on
every call.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from babylon.projection.view_models import KeyFigureView

if TYPE_CHECKING:
    from babylon.kernel.graph_protocol import GraphProtocol
    from babylon.models.world_state import WorldState

__all__ = ["DEAD_PRODUCER_REMEDY", "key_figure_statblocks", "project_key_figure"]


DEAD_PRODUCER_REMEDY: Final[str] = (
    "no key-figure data producer exists in this engine version -- ADR084 retired the "
    "backing KeyFigure model (2026-07-18, ai/decisions/ADR084_retire_dead_models.yaml); "
    "NodeType.KEY_FIGURE is declared vocabulary only, typing classify_topology()'s "
    "COMMAND-edge test fixtures, with no MODEL_FIELDS_BY_NODE_TYPE entry and no "
    "production stamp"
)
"""The dossier's sole absence remedy text.

Deliberately not a "Verb(Noun) to attribute X" imperative like
:mod:`babylon.projection.vault.render`'s ``_REMEDY_BY_FIELD`` — there is no
verb a player could invoke to attribute this field, because there is no
field. The remedy names the ADR that killed the producer instead, so a
reader (or a future maintainer re-deriving this dossier from scratch) lands
on the actual cause rather than a plausible-looking action that does
nothing. Kept ASCII-only and single-line: it is spliced directly into a
Jinja-rendered Markdown fence's info string
(:mod:`babylon.projection.vault.render_key_figure`), where an em dash or a
literal newline would corrupt the fence.
"""


def key_figure_statblocks(view: KeyFigureView) -> tuple[tuple[str, str], ...]:
    """The per-kind statblock-row builder (Lane P convention; WO-45 consumes it).

    Every Lane P kind exposes one of these so Program 24 P2 WO-45's
    dispatch-registry composition can call ``project_<kind>`` then
    ``<kind>_statblocks(view)`` uniformly across kinds, without app.py
    special-casing any one of them.

    :param view: the projected key-figure dossier. Accepted only for
        signature parity with the other kinds' statblock-row builders (all
        of which read real fields off their view) — ``KeyFigureView``
        declares no field a statblock could ever tabulate, so the answer is
        the same for every possible ``view``.
    :returns: An empty tuple, always — not a withheld or truncated result,
        the honest and complete one for a kind with no live producer.
    """
    del view  # unused: no KeyFigureView field ever carries statblock data.
    return ()


def project_key_figure(
    key_figure_id: str,
    *,
    graph: GraphProtocol,  # noqa: ARG001 -- no field has a graph producer (ADR084); kept for project_<kind> signature parity
    world: WorldState,  # noqa: ARG001 -- WorldState.key_figures was removed (ADR084); kept for project_<kind> signature parity
    tick: int,
) -> KeyFigureView:
    """Project one key figure's (permanently absent) state into a :class:`KeyFigureView`.

    :param key_figure_id: The graph node id naming the key figure. Never
        resolved against the graph — see the module docstring for why doing
        so would trip the vocabulary sentinel or require growing a
        must-only-shrink allowlist.
    :param graph: Unused — accepted only for signature parity with the other
        ``project_<kind>`` functions (Program 24 P2 Lane P recipe).
    :param world: Unused — accepted only for signature parity; ADR084
        removed ``WorldState.key_figures``, so there is no world-side source
        to read.
    :param tick: The committed tick this dossier is projected from —
        becomes the dossier's ``verified_tick`` staleness anchor.
    :returns: The frozen, validated key-figure dossier. It carries no field
        beyond identity/provenance, by construction — see
        :class:`~babylon.projection.view_models.KeyFigureView`'s docstring.
    :raises pydantic.ValidationError: if ``key_figure_id`` is empty or
        ``tick`` is negative — a malformed *identity*, not an absent
        producer, fails loud (Constitution III.11's other half).
    """
    return KeyFigureView(key_figure_id=key_figure_id, verified_tick=tick)
