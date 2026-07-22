"""Declared exemptions for the tutorial option-coverage sentinel.

Every option row this gate finds uncovered by the authored tutorial scripts is
either wired into a future step or recorded here, dated and owned, per
:mod:`babylon.sentinels.exemptions`'s standard shape. A key is
``("binding", <class_name>, <textual-key>)`` -- matching
:func:`babylon.sentinels._ast.declared_bindings`'s own triple, so an exemption
can never collide across two different classes' same key (``LobbyScreen``'s
``"a"`` and ``ArchiveApp``'s ``"a"`` are two distinct keys, by design --
:mod:`babylon.game.tutorial`'s own anchor-grammar docstring).
"""

from __future__ import annotations

from babylon.sentinels.exemptions import SentinelExemption

TUTORIAL_COVERAGE_EXEMPTIONS: tuple[SentinelExemption, ...] = (
    SentinelExemption(
        key=("binding", "ArchiveApp", "ctrl+i"),
        reason=(
            "ArchiveApp.jump_forward (ctrl+i) is the jumplist-forward half of a "
            "pair whose backward half (ctrl+o, jump_back) IS exercised by "
            "wayne_opening_arc's jump_back_to_wayne step. The opening arc teaches "
            "one jumplist round-trip (navigate away, then walk back) -- teaching "
            "the forward walk too is a natural next beat for a follow-up script, "
            "not a gap in the first-session arc's own scope."
        ),
        owner="Persephone Raskova",
        date="2026-07-22",
        tracking_task="N/A (future opening-arc-extension unit per "
        "ai/_inbox/t6-tutorial-bdd-ruling.md; not a wired gap)",
    ),
    SentinelExemption(
        key=("binding", "LobbyScreen", "a"),
        reason=(
            "LobbyScreen.toggle_archive (a) reveals ARCHIVED campaign rows -- an "
            "administrative lobby action the first-session opening arc has no "
            "reason to teach (wayne_opening_arc's own boot_into_lobby step mints "
            "a fresh campaign and moves on; there is nothing archived yet to "
            "toggle into view)."
        ),
        owner="Persephone Raskova",
        date="2026-07-22",
        tracking_task="N/A (secondary lobby chrome, not a game-loop verb)",
    ),
    SentinelExemption(
        key=("binding", "LobbyScreen", "d"),
        reason=(
            "LobbyScreen.delete_step (d) is a destructive campaign-deletion "
            "action -- deliberately not exercised by a teaching script whose own "
            "job is to mint and enter a campaign, never to delete the one it just "
            "made."
        ),
        owner="Persephone Raskova",
        date="2026-07-22",
        tracking_task="N/A (destructive administrative action, out of scope for "
        "a first-session teaching arc)",
    ),
    SentinelExemption(
        key=("binding", "LobbyScreen", "escape"),
        reason=(
            "LobbyScreen.leave (escape) exits the lobby without choosing a "
            "campaign -- the opening arc's own point is to choose one "
            "(boot_into_lobby's 'n' -> begin_the_operation), so the abandon path "
            "is intentionally untaught, not overlooked."
        ),
        owner="Persephone Raskova",
        date="2026-07-22",
        tracking_task="N/A (the arc teaches choosing a campaign, not abandoning the lobby)",
    ),
)
