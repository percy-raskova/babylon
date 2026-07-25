"""Computed backlink index for the Wiki view (design §C3).

Replaces the current backlinks-as-convention ("incidence") with a real "what links here",
derived cheaply by inverting each page's outbound wikilinks. Link grammar is
:data:`babylon.tui.wikilinks.WIKILINK_RE` — reused, never re-derived. Full property-query
language is a post-1.0 BFM concern; this is the v1.0 semantic floor.
"""

from __future__ import annotations

from babylon.tui.wikilinks import WIKILINK_RE


def _outbound(markdown: str) -> set[str]:
    return {m.group(1).strip() for m in WIKILINK_RE.finditer(markdown)}


def build_backlink_index(pages: dict[str, str]) -> dict[str, tuple[str, ...]]:
    """Return target-slug → sorted sources linking to it. Targets with no inbound links absent."""
    inbound: dict[str, set[str]] = {}
    for source, markdown in pages.items():
        for target in _outbound(markdown):
            inbound.setdefault(target, set()).add(source)
    return {target: tuple(sorted(sources)) for target, sources in inbound.items()}


def facets_by_type(pages: dict[str, str]) -> dict[str, tuple[str, ...]]:
    """Group page slugs by their type prefix (``county/26163`` → type ``county``)."""
    facets: dict[str, set[str]] = {}
    for slug in pages:
        page_type = slug.split("/", 1)[0]
        facets.setdefault(page_type, set()).add(slug)
    return {t: tuple(sorted(members)) for t, members in facets.items()}
