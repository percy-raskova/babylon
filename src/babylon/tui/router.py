"""Parse ``babylon://`` URIs into a frozen navigation target.

The wikilink rule (``babylon.tui.wikilinks``) emits two href shapes:

* ``babylon://<target>`` — a known entity, addressed bare (no kind segment).
* ``babylon://redlink/<target>`` — an unresolved target.

Other Archive UI (statblocks, the command palette, future ``babylon://<kind>/<id>``
links) may address entities with an explicit kind segment. This module parses
all three shapes into one frozen :class:`BabylonTarget`; anything else raises
loudly (Constitution III.11 — no silent best-effort parsing of a malformed URI).
"""

from __future__ import annotations

import re
from typing import Final
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, field_validator

SCHEME: Final = "babylon"
REDLINK_KIND: Final = "redlink"
BARE_KIND: Final = "wikilink"
"""Kind assigned to bare ``babylon://<id>`` hrefs (no explicit kind segment)."""

_KIND_RE: Final = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
"""A kind segment, or a bare (no-path) target: a single path token, no ``/``."""

_ENTITY_ID_RE: Final = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]*$")
"""An entity id following an explicit kind: may itself be ``/``-shaped (e.g.
wikilink targets conventionally look like ``county/26163``)."""


class InvalidBabylonUri(ValueError):
    """Raised when a string is not a well-formed ``babylon://`` URI."""


class BabylonTarget(BaseModel):
    """A parsed ``babylon://`` navigation target.

    :ivar kind: the entity kind (e.g. ``"county"``), ``"wikilink"`` for a
        bare ``babylon://<id>`` href, or ``"redlink"`` for an unresolved one.
    :ivar entity_id: the raw identifier segment.
    :ivar redlink: ``True`` when the target is unresolved (``kind`` is then
        always ``"redlink"``).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: str
    entity_id: str
    redlink: bool = False

    @field_validator("kind", "entity_id")
    @classmethod
    def check_non_empty(cls, value: str) -> str:
        """Reject blank segments — a parsed target is never partially empty.

        :param value: the field value under validation.
        :raises ValueError: if ``value`` is empty.
        :returns: ``value`` unchanged.
        """
        if not value:
            raise ValueError("must be non-empty")
        return value


def parse_babylon_uri(uri: str) -> BabylonTarget:
    """Parse a ``babylon://`` URI into a :class:`BabylonTarget`.

    Accepted shapes:

    * ``babylon://<id>`` — bare form; ``kind="wikilink"``, ``redlink=False``.
    * ``babylon://redlink/<id>`` — ``kind="redlink"``, ``redlink=True``.
    * ``babylon://<kind>/<id>`` — explicit kind, ``redlink=False``.

    :param uri: the candidate URI string.
    :raises InvalidBabylonUri: if the scheme is wrong, a required segment is
        missing, or a segment fails the entity-id character class.
    :returns: the parsed, frozen target.
    """
    parts = urlsplit(uri)
    if parts.scheme != SCHEME:
        raise InvalidBabylonUri(f"not a {SCHEME}:// uri: {uri!r}")
    netloc = parts.netloc
    path = parts.path.lstrip("/")
    if not netloc:
        raise InvalidBabylonUri(f"missing host/kind segment: {uri!r}")
    if not _KIND_RE.match(netloc):
        raise InvalidBabylonUri(f"malformed kind/id segment: {uri!r}")

    if not path:
        # Bare form: babylon://<id> — netloc IS the id, kind defaults.
        return BabylonTarget(kind=BARE_KIND, entity_id=netloc)

    if not _ENTITY_ID_RE.match(path):
        raise InvalidBabylonUri(f"malformed entity id: {uri!r}")

    if netloc == REDLINK_KIND:
        return BabylonTarget(kind=REDLINK_KIND, entity_id=path, redlink=True)
    return BabylonTarget(kind=netloc, entity_id=path)


def format_babylon_uri(target: BabylonTarget) -> str:
    """Render a :class:`BabylonTarget` back to its ``babylon://`` URI form.

    Round-trips with :func:`parse_babylon_uri`: ``parse_babylon_uri(
    format_babylon_uri(t)) == t`` for any ``t`` produced by that function.

    :param target: the target to render.
    :returns: the URI string.
    """
    prefix = REDLINK_KIND if target.redlink else target.kind
    return f"{SCHEME}://{prefix}/{target.entity_id}"


__all__ = [
    "SCHEME",
    "REDLINK_KIND",
    "BARE_KIND",
    "InvalidBabylonUri",
    "BabylonTarget",
    "parse_babylon_uri",
    "format_babylon_uri",
]
