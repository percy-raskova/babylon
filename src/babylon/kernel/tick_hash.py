"""The frozen P27 reference serializer for one per-tick content fingerprint.

Normative specification: ``docs/reference/determinism-contract.rst``, chapter
*The P27 Tick Hash*. This module preserves that Python JSON layout and its exact
tests as executable reference evidence. It is not an input or alternate path
for `TickContentHashV1`. The Rust replay path has one separate canonical binary
identity defined by ``contracts/tick_content_hash_v1.yaml``.

Why this exists alongside ``tick_commit.replay_identity_hash``
---------------------------------------------------------------

The replay-identity stamp (named ``determinism_hash`` until ADR179 T2 renamed
it, migration 0044) is ``sha256(f"{session_id}:{tick}:{rng_seed}")`` —
three scalars, **no world state at all**. It proves *replay lineage* (the same
session+tick+seed reproduces the same label) and is structurally incapable of
noticing a dropped node, a lost edge, or a corrupted attribute. This hash is
the other half: it says nothing about run identity (the session id is
deliberately not an input) and everything about content.

Within the frozen Python evidence, the two are **additive, not substitutes** —
ruled so by ADR179 T2 (the dossier's §8 Q2). The commit marker keeps its
replay-lineage role under the honest name ``replay_identity_hash``; this
module's digest is ``content_hash`` in the regression checkpoints.

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
- **``None``** is the bare literal ``null``. An optional field that is unset is
  real state, and ``null`` is unambiguous in every JSON implementation
  (a Rust ``Option::None`` serializes to exactly this). This does **not**
  reopen the stringly-fallback hazard: that ban is on values whose type has no
  rule, and hashing ``null`` explicitly makes a wrongly-defaulted field *more*
  visible, not less — ``null`` and ``0.0`` are different bytes.
- **Sets** (``set``/``frozenset``) become their members in ascending
  canonical-serialization order. Python's set iteration order is hash-seed
  dependent and is not a property any port could reproduce.
- **Enum members** are their declared string value, never re-cased. A
  non-string-valued member (an ``IntEnum``) is a loud failure: it would hash as
  a bare integer, silently aliasing a genuine integer field, and its numbering
  is an internal detail no port should have to reproduce.
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
from enum import Enum

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


def _encode_enum(value: Enum, *, field: str) -> str:
    """Render an enum member as its declared value, never re-cased.

    ``NodeType.SOCIAL_CLASS`` → ``"social_class"``, ``EdgeType.EXPLOITATION``
    → ``"EXPLOITATION"`` — whichever casing the enum itself declares.

    :param value: the enum member.
    :param field: the field name, for error messages.
    :returns: the member's declared string value.
    :raises TickHashEncodingError: if the member's value is not a string.
        An ``IntEnum`` would otherwise hash as a bare integer and silently
        alias a genuine integer field, and its numbering is an internal
        detail no port should be required to reproduce.
    """
    member_value = value.value
    if not isinstance(member_value, str):
        raise TickHashEncodingError(
            f"field {field!r} holds {type(value).__name__}."
            f"{value.name}, whose value is {type(member_value).__name__}, "
            "not a string; only string-valued enum members may enter the "
            "tick hash"
        )
    return member_value


def _encode_value(value: object, *, field: str) -> object:
    """Convert one value to its canonical JSON-ready form.

    :param value: the value to encode.
    :param field: the field name that held it, for error messages.
    :returns: a value ``json.dumps`` renders per the spec's byte layout.
    :raises TickHashEncodingError: if no encoding rule covers ``value``.
    """
    # Order matters: `bool` is a subclass of `int`, and `Micros` is too.
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, Micros):
        return str(int(value))
    if isinstance(value, Enum):
        return _encode_enum(value, field=field)
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
    if isinstance(value, (set, frozenset)):
        return _encode_set(value, field=field)
    raise TickHashEncodingError(
        f"field {field!r} holds {type(value).__name__}, for which there is "
        "no encoding rule; the tick hash has no stringly fallback"
    )


def _encode_set(value: set[object] | frozenset[object], *, field: str) -> list[object]:
    """Render a set as its members in canonical order.

    Python's set iteration order is hash-seed dependent and is never a
    property a port could reproduce, so the members are sorted by their own
    canonical serialization — a total order that works regardless of member
    type, unlike sorting the raw members (which raises on a mixed-type set).

    This mirrors the rule ``babylon-graph``'s ``members_of`` already enforces
    for hyperedge members: membership is a set, and declared order is
    unobservable.

    :param value: the set to encode.
    :param field: the field name, for error messages.
    :returns: the encoded members in ascending canonical-serialization order.
    :raises TickHashEncodingError: propagated from any member with no rule.
    """
    encoded = [_encode_value(member, field=field) for member in value]
    return sorted(encoded, key=lambda item: json.dumps(item, sort_keys=True, separators=(",", ":")))


def _encode_record(record: Mapping[str, object]) -> dict[str, object]:
    """Encode every field of one record.

    Key *ordering* is left to ``json.dumps(sort_keys=True)`` so that sorting
    happens in exactly one place, recursively, for records at any depth.

    :param record: the node, edge, or action record.
    :returns: the same mapping with every value canonically encoded.
    :raises TickHashEncodingError: if any key is not a string — ``sort_keys``
        cannot order a mixed-type key set, so the byte output would depend on
        insertion order.
    """
    for key in record:
        if not isinstance(key, str):
            raise TickHashEncodingError(
                f"record key {key!r} is {type(key).__name__}, not str; "
                "canonical key ordering is undefined for non-string keys"
            )
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
