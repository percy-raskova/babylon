"""Command palette ``Provider``: fuzzy navigation over the known-entity set.

Design canon R2 (``ai/_inbox/tui/20260719archiveinterfacedesign.md``):
"Wiki is the gameplay metaphor" — TUI/neovim/Obsidian pages, wikilinks,
fuzzy switcher, command palette. This module ships exactly one command
family: **open a known entity's page**. Per R4 ("no LLM in the input
path", generalized here to "no free-form-command input path either") the
palette carries **no verb commands** — Article V verbs are atomic, costed,
and OODA-gated, and belong in the verb plate (WO-26), never a fire-and-forget
palette pick. Full navigation history/breadcrumbs (jumplist, fuzzy-switcher
wiring into a nav shell) land in WO-47; this WO ships the ``Provider`` in
isolation and is composed into ``ArchiveApp.COMMANDS`` at WO-45 (shared-file
discipline: this module never touches ``tui/app.py``).

Textual 8.2.8 API (``ai/_inbox/tui/20260720-textual-828-docs-digest.md`` §5):
a ``Provider`` subclass need only implement ``search(query) -> Hits``
(required); ``discover()`` is optional, documented as "empty-input
suggestions, must be fast". Both are implemented here over the same
command set, mirroring upstream's own ``SystemCommandsProvider``
(``textual.system_commands``), which does the same discover/search split
over ``App.get_system_commands``.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol, runtime_checkable

from textual.command import DiscoveryHit, Hit, Hits, Provider
from textual.message import Message

from babylon.tui.router import BabylonTarget, parse_babylon_uri


@runtime_checkable
class _KnownEntityHost(Protocol):
    """Structural type for an ``App`` that exposes its known-entity set.

    Mirrors ``babylon.tui.directives._StatblockHost``: the palette never
    invents entities of its own. An app that does not (yet) implement this
    attribute — e.g. before WO-45 wires ``ArchiveApp.known_entities`` —
    yields an honestly empty command set (Constitution III.11), never a
    fabricated demo list.

    :ivar known_entities: every entity id (``"<kind>/<id>"`` shape, matching
        ``babylon.tui.wikilinks.known_target_resolver``'s input) the palette
        may offer to open.
    """

    known_entities: frozenset[str]


def _known_entities(app: object) -> frozenset[str]:
    """Read the known-entity set off ``app`` if it exposes one.

    :param app: the running ``App`` instance (duck-typed via
        :class:`_KnownEntityHost`).
    :returns: ``app.known_entities`` if present, else an empty set — honest
        absence, never a fabricated default (Constitution III.11).
    """
    return app.known_entities if isinstance(app, _KnownEntityHost) else frozenset()


class EntityNavigated(Message):
    """Posted when a palette hit is chosen: "open this entity's page".

    Read-only: choosing a hit only requests a navigation, never mutates
    game state (the palette carries no verb commands — R4). A future nav
    shell (WO-47) subscribes to route it; until then this is a well-formed,
    inert message — the same posture as the ``AMBER`` autopause token
    (``babylon.tui.theme``): reserved, not yet wired to a handler.

    :ivar target: the parsed navigation target for the chosen entity.
    """

    def __init__(self, target: BabylonTarget) -> None:
        self.target = target
        super().__init__()


def _help_text(target: BabylonTarget) -> str:
    """Build the palette's help text for a navigation hit.

    :param target: the parsed navigation target.
    :returns: e.g. ``"Open county — 26163"``.
    """
    return f"Open {target.kind} — {target.entity_id}"


class EntityNavigatorProvider(Provider):
    """Fuzzy command palette over the Archive's known-entity set.

    Exposes exactly one command shape per known entity: "open this page".
    No verb commands — Article V's nine verbs stay in the verb plate.
    Register at the app level via
    ``COMMANDS = App.COMMANDS | {EntityNavigatorProvider}`` (WO-45).
    """

    async def search(self, query: str) -> Hits:
        """Fuzzy-rank known entities against ``query``.

        :param query: the user's palette input.
        :yields: one :class:`~textual.command.Hit` per known entity that
            scores > 0 against ``query`` (the palette sorts by score;
            :class:`~textual.command.Hit` is itself orderable on it).
        """
        matcher = self.matcher(query)
        for entity_id in sorted(_known_entities(self.app)):
            score = matcher.match(entity_id)
            if score > 0:
                target = parse_babylon_uri(f"babylon://{entity_id}")
                yield Hit(
                    score,
                    matcher.highlight(entity_id),
                    self._open(target),
                    text=entity_id,
                    help=_help_text(target),
                )

    async def discover(self) -> Hits:
        """List every known entity as a default (empty-input) suggestion.

        :yields: one :class:`~textual.command.DiscoveryHit` per known
            entity, in deterministic (sorted-by-id) order.
        """
        for entity_id in sorted(_known_entities(self.app)):
            target = parse_babylon_uri(f"babylon://{entity_id}")
            yield DiscoveryHit(
                entity_id,
                self._open(target),
                text=entity_id,
                help=_help_text(target),
            )

    def _open(self, target: BabylonTarget) -> Callable[[], None]:
        """Build the zero-arg command callback that opens ``target``.

        :param target: the parsed navigation target to post when chosen.
        :returns: a callback posting :class:`EntityNavigated` on the
            provider's active screen.
        """

        def command() -> None:
            self.screen.post_message(EntityNavigated(target))

        return command


__all__ = [
    "EntityNavigated",
    "EntityNavigatorProvider",
]
