"""The P27 tick hash — one canonical per-tick **content** fingerprint.

Normative specification: ``docs/reference/determinism-contract.rst``, chapter
*The P27 Tick Hash*. This module is the Python reference implementation of that
byte layout; ``babylon-kernel`` (Rust) is required to produce the identical
digest from the identical state, so **every byte here is contract**, not
convenience (Constitution III.7).

Why this exists alongside ``tick_commit.determinism_hash``
-----------------------------------------------------------

Today's ``determinism_hash`` is ``sha256(f"{session_id}:{tick}:{rng_seed}")`` —
three scalars, **no world state at all**. It proves *replay lineage* (the same
session+tick+seed reproduces the same label) and is structurally incapable of
noticing a dropped node, a lost edge, or a corrupted attribute. This hash is
the other half: it says nothing about run identity (the session id is
deliberately not an input) and everything about content.

The two are **additive, not substitutes**. Whether the older hash is renamed or
upgraded in place is a reserved Director question
(``reports/social-topology-spine-dossier.md`` §8 Q2); nothing in this module
touches it.

Encoding rules, in one place
-----------------------------

- **Keys** sort alphabetically, recursively, at every nesting level.
- **Nodes** sort ascending by ``node_id`` (string comparison); **edges** by
  ``(source_id, target_id)``. Graph-backend iteration order is unspecified and
  must never reach the digest.
- **Actions** keep their given order — the sequence in which actions applied is
  itself state, not an artifact of storage.
- **Integers** are bare JSON numbers; **fixed-point micro-unit currency**
  (:class:`Micros`) is a decimal **string**, because a JSON number is an
  IEEE-754 ``f64`` in every mainstream library and would silently round an
  ``i128``.
- **Floats** are the raw big-endian IEEE-754 bit pattern as 16 lowercase hex
  characters, sidestepping cross-language shortest-round-trip disagreement on
  ties, ``-0.0``, and subnormals.
- **Booleans** are bare ``true``/``false``.
- **Anything else** is a loud :class:`TickHashEncodingError` (III.11) — there is
  no ``default=str`` fallback, which is exactly the hazard
  ``conservation_audit.py``'s hash carries today.
"""

from __future__ import annotations

import hashlib
import json
import math
import struct
from collections.abc import Mapping, Sequence

__all__ = [
    "Micros",
    "TickHashEncodingError",
    "canonical_tick_bytes",
    "compute_tick_hash",
]


class Micros(int):
    """A fixed-point currency value in micro-units, encoded as a decimal string.

    Python's ``int`` is arbitrary-precision, so a plain ``int`` would serialize
    losslessly *here* while a Rust ``serde_json`` ``i128`` would not. Tagging
    the value at the call site keeps the distinction explicit and type-checked
    rather than inferred from magnitude, which would make the encoding depend
    on the data.

    :param value: the micro-unit amount.
    """

    __slots__ = ()


class TickHashEncodingError(TypeError):
    """A value reached the hash with no encoding rule (Constitution III.11).

    Deliberately fatal: coercing an unknown value to its ``str()`` would let a
    schema change slip through the one gate meant to catch it.
    """


def _encode_float(value: float, *, field: str) -> str:
    """Render an ``f64`` as its big-endian bit pattern in lowercase hex.

    :param value: the float to encode.
    :param field: the field name, for error messages.
    :returns: exactly 16 lowercase hex characters.
    :raises TickHashEncodingError: if ``value`` is NaN, which has many bit
        patterns and no meaningful equality, and so cannot participate in a
        change-detection hash.
    """
    if math.isnan(value):
        raise TickHashEncodingError(
            f"field {field!r} is NaN; NaN has no canonical bit pattern and "
            "cannot enter the tick hash"
        )
    return struct.pack(">d", value).hex()


def _encode_value(value: object, *, field: str) -> object:
    """Convert one value to its canonical JSON-ready form.

    :param value: the value to encode.
    :param field: the field name that held it, for error messages.
    :returns: a value ``json.dumps`` renders per the spec's byte layout.
    :raises TickHashEncodingError: if no encoding rule covers ``value``.
    """
    # Order matters: `bool` is a subclass of `int`, and `Micros` is too.
    if isinstance(value, bool):
        return value
    if isinstance(value, Micros):
        return str(int(value))
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return _encode_float(value, field=field)
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        return _encode_record(value)
    if isinstance(value, (list, tuple)):
        return [_encode_value(item, field=field) for item in value]
    raise TickHashEncodingError(
        f"field {field!r} holds {type(value).__name__}, for which there is "
        "no encoding rule; the tick hash has no stringly fallback"
    )


def _encode_record(record: Mapping[str, object]) -> dict[str, object]:
    """Encode every field of one record.

    Key *ordering* is left to ``json.dumps(sort_keys=True)`` so that sorting
    happens in exactly one place, recursively, for records at any depth.

    :param record: the node, edge, or action record.
    :returns: the same mapping with every value canonically encoded.
    """
    return {key: _encode_value(value, field=key) for key, value in record.items()}


def _sort_key_node(node: Mapping[str, object]) -> str:
    """Sort key for nodes: ascending ``node_id``, string comparison.

    :param node: the node record.
    :returns: the node's identifier.
    :raises TickHashEncodingError: if the record carries no ``node_id``, which
        would otherwise make the ordering — and so the digest — arbitrary.
    """
    node_id = node.get("node_id")
    if not isinstance(node_id, str):
        raise TickHashEncodingError(
            "every node record needs a string 'node_id' to order the tick "
            f"hash deterministically; got {node_id!r}"
        )
    return node_id


def _sort_key_edge(edge: Mapping[str, object]) -> tuple[str, str]:
    """Sort key for edges: ascending ``(source_id, target_id)``.

    :param edge: the edge record.
    :returns: the endpoint pair.
    :raises TickHashEncodingError: if either endpoint is missing or not a string.
    """
    source, target = edge.get("source_id"), edge.get("target_id")
    if not isinstance(source, str) or not isinstance(target, str):
        raise TickHashEncodingError(
            "every edge record needs string 'source_id' and 'target_id' to "
            f"order the tick hash deterministically; got {source!r}, {target!r}"
        )
    return (source, target)


def canonical_tick_bytes(
    *,
    tick: int,
    rng_seed: int,
    nodes: Sequence[Mapping[str, object]],
    edges: Sequence[Mapping[str, object]],
    actions: Sequence[Mapping[str, object]],
) -> bytes:
    """Serialize one tick's content to its canonical bytes.

    Exposed alongside :func:`compute_tick_hash` because a digest mismatch
    between two implementations is undiagnosable without the bytes that
    produced it — this is the artifact a Rust port diffs against.

    :param tick: the current tick index.
    :param rng_seed: the session's fixed RNG seed. Note this is the *seed*, not
        the session identifier, which never enters the hash.
    :param nodes: every graph node, in any order.
    :param edges: every graph edge, in any order.
    :param actions: the actions applied this tick, **in application order**.
    :returns: the exact UTF-8 bytes the digest is taken over.
    :raises TickHashEncodingError: if any value has no encoding rule, or a node
        or edge record lacks the identifiers its ordering needs.
    """
    payload = {
        "tick": tick,
        "rng_seed": rng_seed,
        "nodes": [_encode_record(node) for node in sorted(nodes, key=_sort_key_node)],
        "edges": [_encode_record(edge) for edge in sorted(edges, key=_sort_key_edge)],
        "actions": [_encode_record(action) for action in actions],
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode(
        "utf-8"
    )


def compute_tick_hash(
    *,
    tick: int,
    rng_seed: int,
    nodes: Sequence[Mapping[str, object]],
    edges: Sequence[Mapping[str, object]],
    actions: Sequence[Mapping[str, object]],
) -> str:
    """Compute the canonical per-tick content hash.

    :param tick: the current tick index.
    :param rng_seed: the session's fixed RNG seed.
    :param nodes: every graph node, in any order.
    :param edges: every graph edge, in any order.
    :param actions: the actions applied this tick, in application order.
    :returns: a 64-character lowercase hex SHA-256 digest.
    :raises TickHashEncodingError: propagated from :func:`canonical_tick_bytes`.
    """
    return hashlib.sha256(
        canonical_tick_bytes(
            tick=tick, rng_seed=rng_seed, nodes=nodes, edges=edges, actions=actions
        )
    ).hexdigest()
