"""Deterministic record/load for :class:`~babylon.projection.view_models.CountyView`.

Pure I/O over an already-projected view-model — this module never touches the
engine, a scenario, or a database. It exists so downstream view-consumer tests
(Program 24 P1 keel item 5) run against a committed fixture file instead of a
live tick: ``tools/record_projection_fixtures.py`` is the only caller that
drives the engine to produce the :class:`~babylon.projection.view_models.CountyView`
this module then records.

Determinism contract: :func:`record_county_fixture` writes ``model_dump(mode="json")``
through ``json.dumps(..., sort_keys=True)`` plus a trailing newline — the same
:class:`~babylon.projection.view_models.CountyView` always serializes to the
same bytes, so recording it twice (even from two independent harvester runs)
produces a byte-identical file.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from babylon.projection.view_models import (
    CountyView,
    NationalView,
    hydrate_county,
    hydrate_national,
)

__all__ = [
    "load_county_fixture",
    "load_national_fixture",
    "record_county_fixture",
    "record_national_fixture",
]


def record_county_fixture(view: CountyView, path: Path) -> None:
    """Serialize ``view`` to ``path`` as deterministic, sorted-key JSON.

    :param view: The projected county dossier to persist.
    :param path: Destination file. The parent directory is NOT created here —
        callers (the harvester) own directory setup, so a typo'd path fails
        loud instead of silently minting a stray directory tree.
    :raises OSError: if ``path``'s parent directory does not exist or is not
        writable.
    """
    payload: dict[str, Any] = view.model_dump(mode="json")
    text = json.dumps(payload, sort_keys=True, indent=2) + "\n"
    path.write_text(text, encoding="utf-8")


def load_county_fixture(path: Path) -> CountyView:
    """Hydrate a :class:`CountyView` from a fixture written by :func:`record_county_fixture`.

    :param path: The fixture file to load.
    :returns: The validated, frozen :class:`CountyView`.
    :raises FileNotFoundError: if ``path`` does not exist — a missing fixture
        is a loud failure (Constitution III.11), never a silently-substituted
        default view.
    :raises ValueError: if ``path``'s content is not valid JSON.
    :raises pydantic.ValidationError: if the JSON parses but does not hydrate
        to a valid :class:`CountyView` (wrong shape, out-of-range value, an
        invented field the model rejects under ``extra="forbid"``).
    """
    if not path.is_file():
        raise FileNotFoundError(f"no projection fixture at {path}")
    raw = path.read_text(encoding="utf-8")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"malformed JSON in projection fixture {path}: {exc}") from exc
    return hydrate_county(data)


def record_national_fixture(view: NationalView, path: Path) -> None:
    """Serialize ``view`` to ``path`` as deterministic, sorted-key JSON.

    :param view: The projected national dossier to persist.
    :param path: Destination file. The parent directory is NOT created here —
        callers (the harvester) own directory setup, so a typo'd path fails
        loud instead of silently minting a stray directory tree.
    :raises OSError: if ``path``'s parent directory does not exist or is not
        writable.
    """
    payload: dict[str, Any] = view.model_dump(mode="json")
    text = json.dumps(payload, sort_keys=True, indent=2) + "\n"
    path.write_text(text, encoding="utf-8")


def load_national_fixture(path: Path) -> NationalView:
    """Hydrate a :class:`NationalView` from a fixture written by :func:`record_national_fixture`.

    :param path: The fixture file to load.
    :returns: The validated, frozen :class:`NationalView`.
    :raises FileNotFoundError: if ``path`` does not exist — a missing fixture
        is a loud failure (Constitution III.11), never a silently-substituted
        default view.
    :raises ValueError: if ``path``'s content is not valid JSON.
    :raises pydantic.ValidationError: if the JSON parses but does not hydrate
        to a valid :class:`NationalView` (wrong shape, out-of-range value, an
        invented field the model rejects under ``extra="forbid"``).
    """
    if not path.is_file():
        raise FileNotFoundError(f"no projection fixture at {path}")
    raw = path.read_text(encoding="utf-8")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"malformed JSON in projection fixture {path}: {exc}") from exc
    return hydrate_national(data)
