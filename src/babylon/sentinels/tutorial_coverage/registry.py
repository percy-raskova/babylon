"""Declared exemptions for the tutorial option-coverage sentinel.

Re-keyed WHOLESALE at the M7 cutover (2026-07-28,
``docs/superpowers/specs/2026-07-28-m7-cutover-contracts.md`` §5.5): the old
``("binding", <TextualClass>, <key>)`` rows named classes the ceremony
deleted, so every row here is keyed ``("binding", <KeybarSurface>, <key>)``
against :func:`babylon.sentinels._rust.declared_keybar_hints`'s option
universe (62 rows measured at the re-key). The 24-step
``WAYNE_OPENING_ARC`` covers 11 of those options through its ``binding:``
anchors; every other row is recorded below, dated and owned, per
:mod:`babylon.sentinels.exemptions`'s standard shape — grouped through
:func:`_category` because the honest reason is per-CATEGORY (a navigation
composite is exempt for the same reason on every surface), while the
governance stays per-ROW (the ``exemption-grounded`` dual check keeps each
key honest against the live keybar forever).
"""

from __future__ import annotations

from babylon.sentinels.exemptions import SentinelExemption

_OWNER = "Persephone Raskova"
_DATE = "2026-07-28"


def _category(
    keys: tuple[tuple[str, str], ...], reason: str, tracking_task: str
) -> tuple[SentinelExemption, ...]:
    """One exemption row per ``(surface, key)``, sharing a category reason.

    :param keys: the exempted ``(surface, key)`` pairs.
    :param reason: the category's shared, honest reason.
    :param tracking_task: the category's shared tracking disposition.
    :returns: the built rows, in declaration order.
    """
    return tuple(
        SentinelExemption(
            key=("binding", surface, key),
            reason=reason,
            owner=_OWNER,
            date=_DATE,
            tracking_task=tracking_task,
        )
        for surface, key in keys
    )


#: Composite/continuous navigation display hints. The keybar itself renders
#: these click-unregistered ("there is no single key event a click could
#: honestly synthesize" — keybar.rs's own doctrine); a tutorial script hits
#: the same wall, and navigation is exercised implicitly by every arc step's
#: own movement.
_NAV_COMPOSITES = _category(
    (
        ("Lobby", "↑↓"),
        ("Lobby", "j/k"),
        ("Wiki", "↑↓"),
        ("Wiki", "n/p"),
        ("Wiki", "PgUp/PgDn"),
        ("TopologyGlyph", "↑↓"),
        ("Topology3d", "←→↑↓"),
        ("Topology3d", "+/-"),
        ("Map", "←→↑↓"),
        ("Map", "+/-"),
        ("Map", "wheel"),
        ("Dashboard", "wheel"),
        ("RailWatchlist", "↑↓"),
        ("Rail", "↑↓"),
        ("Overlay", "↑↓"),
        ("Overlay", "type"),
    ),
    reason=(
        "composite/continuous navigation display hint — no single scriptable "
        "key event exists (the keybar renders these click-unregistered for "
        "the same reason); navigation is exercised implicitly by every arc "
        "step's own movement"
    ),
    tracking_task="N/A (permanent: display-only hint class)",
)

#: The global chrome trio and the EVERYWHERE help section (which keybar.rs
#: declares on its ``BareWiki`` placeholder surface — the extractor reads
#: that attribution verbatim, deterministically).
_GLOBAL_CHROME = _category(
    (
        ("Global", "?"),
        ("Global", "/"),
        ("Global", "q"),
        ("BareWiki", "?"),
        ("BareWiki", "/"),
        ("BareWiki", "q"),
        ("BareWiki", "↑↓"),
        ("BareWiki", "Tab/S-Tab"),
        ("BareWiki", "1-4"),
        ("BareWiki", "K"),
    ),
    reason=(
        "global/meta chrome (help, palette, back) and the EVERYWHERE help "
        "section's duplicate rows — the palette itself IS exercised by the "
        "arc's three palette:* steps (the anchor grammar keys one anchor per "
        "step, and those steps' anchors name their destination pages); ? and "
        "q are discoverability chrome, not game verbs; the 1-4/K duplicates "
        "are taught under their Wiki-surface rows"
    ),
    tracking_task="N/A (permanent: meta-chrome, or taught under another key)",
)

#: Per-surface Esc return rows — the M5/M6 contracts' own escape-to-wiki
#: convention, not a teachable game verb.
_ESC_RETURNS = _category(
    (
        ("Wiki", "Esc"),
        ("TopologyGlyph", "Esc"),
        ("Topology3d", "Esc"),
        ("Map", "Esc"),
        ("Dashboard", "Esc"),
        ("RailWatchlist", "Esc"),
        ("Rail", "Esc"),
        ("Overlay", "Esc"),
    ),
    reason=(
        "pane/rail/overlay return chrome (the Esc-to-wiki convention the "
        "M5/M6 contracts pin) — the arc leaves panes implicitly, and a "
        "return key is not a teachable game verb"
    ),
    tracking_task="N/A (permanent: return chrome)",
)

#: Pane-local interaction keys the 24-step OPENING arc deliberately leaves
#: for discovery: the arc teaches pane ENTRY (``binding:Wiki:1-4``); a
#: per-pane key tour (lens/tier switching, 3D camera, chart pages) is a
#: post-1.0 tutorial beat, not an opening-arc one.
_PANE_INTERACTIONS = _category(
    (
        ("TopologyGlyph", "g"),
        ("TopologyGlyph", "s"),
        ("Topology3d", "0"),
        ("Topology3d", "s"),
        ("Topology3d", "f"),
        ("Topology3d", "g"),
        ("Map", "l"),
        ("Map", "y"),
        ("Map", "0"),
        ("Dashboard", "c"),
        ("Dashboard", "m"),
    ),
    reason=(
        "pane-local interaction key the 24-step OPENING arc deliberately "
        "leaves for discovery — the arc teaches pane entry (binding:Wiki:1-4); "
        "a per-pane key tour is a post-1.0 tutorial beat"
    ),
    tracking_task="#335 (post-1.0 tutorial expansion — the wiki-content architecture train)",
)

#: Rail/lobby traversal the arc exercises through steps whose anchors are
#: (by the one-anchor-per-step grammar) option:*/bridging beats rather than
#: binding: rows.
_TRAVERSAL_TAUGHT_ELSEWHERE = _category(
    (
        ("Lobby", "Enter"),
        ("Wiki", "Tab"),
        ("RailWatchlist", "Enter"),
        ("RailWatchlist", "p"),
        ("Rail", "Enter"),
        ("Overlay", "Enter"),
    ),
    reason=(
        "exercised by the arc in substance, anchored elsewhere by the "
        "one-anchor-per-step grammar: the lobby load Enter is the arc's "
        "un-anchored bridging press (the teach-beat anchor is the briefing "
        "Enter, binding:Wiki:Enter); Tab/rail-Enter are pressed by the "
        "option:watchlist-rail:enter and option:chronicle-rail:enter steps; "
        "the rail's lowercase p pin duplicates the taught binding:Wiki:P; "
        "the palette Enter is pressed by all three palette:* steps"
    ),
    tracking_task="N/A (taught in substance under other anchors)",
)

TUTORIAL_COVERAGE_EXEMPTIONS: tuple[SentinelExemption, ...] = (
    _NAV_COMPOSITES
    + _GLOBAL_CHROME
    + _ESC_RETURNS
    + _PANE_INTERACTIONS
    + _TRAVERSAL_TAUGHT_ELSEWHERE
)
