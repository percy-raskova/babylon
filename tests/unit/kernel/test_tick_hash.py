"""Byte-level pins for the P27 tick hash (``docs/reference/determinism-contract.rst``,
*The P27 Tick Hash* chapter).

This is a **cross-implementation byte contract**, not an implementation detail:
the Rust kernel is required to compute the identical digest from the identical
state (Constitution III.7; user-CLAUDE.md contract rule 4, "contracts must be
language-agnostic to the byte"). Every test here therefore pins *bytes or a
digest*, never "whatever the implementation produces" — a test that merely
round-trips through our own encoder would prove nothing about a port.

The encoding rules under test come from the spec chapter's *Ordering*, *Float
and int encodings*, and *Ban on stringly fallbacks* sections.
"""

from __future__ import annotations

import hashlib
import struct
from enum import Enum, IntEnum

import pytest

from babylon.kernel.tick_hash import (
    Micros,
    TickHashEncodingError,
    canonical_tick_bytes,
    compute_tick_hash,
)


class TestTheWorkedExample:
    """The spec chapter's worked example, byte-for-byte.

    **Spec-defect note (2026-07-30).** The chapter's published example
    rendered the boolean ``active`` as the *quoted* string ``"true"``, which
    contradicts its own normative rule ("the literal ASCII tokens ``true`` /
    ``false`` (JSON's own literals)") and is inconsistent with how the same
    example renders integers (``"tick":1``, bare). The published sha merely
    re-derived that slip. The normative prose wins: bools are bare JSON
    literals, so the canonical bytes are 246 long, not 248. The spec's example
    was corrected in the same commit as this test.
    """

    EXPECTED_BYTES = (
        b'{"actions":[],"edges":[{"edge_type":"EXPLOITATION","source_id":"C001",'
        b'"target_id":"C002","value_flow":"4029000000000000"}],"nodes":[{"active":'
        b'true,"node_id":"C001","node_type":"social_class","wealth":'
        b'"4059000000000000"}],"rng_seed":2010,"tick":1}'
    )
    EXPECTED_SHA = "b256dbbca591c5af2b8cb23b9c4027ed1ac657d10b1e669aadb05670cd75d4a0"

    @staticmethod
    def _example() -> dict[str, object]:
        return {
            "tick": 1,
            "rng_seed": 2010,
            "nodes": [
                {
                    "node_id": "C001",
                    "node_type": "social_class",
                    "wealth": 100.0,
                    "active": True,
                }
            ],
            "edges": [
                {
                    "edge_type": "EXPLOITATION",
                    "source_id": "C001",
                    "target_id": "C002",
                    "value_flow": 12.5,
                }
            ],
            "actions": [],
        }

    def test_canonical_bytes_match_the_spec(self) -> None:
        assert canonical_tick_bytes(**self._example()) == self.EXPECTED_BYTES

    def test_byte_length_is_246(self) -> None:
        # Pinned separately: a length change is the cheapest signal that an
        # encoding rule drifted, and it is what a Rust port compares first.
        assert len(canonical_tick_bytes(**self._example())) == 246

    def test_digest_matches_the_spec(self) -> None:
        assert compute_tick_hash(**self._example()) == self.EXPECTED_SHA

    def test_digest_is_sha256_of_the_canonical_bytes(self) -> None:
        payload = self._example()
        assert (
            compute_tick_hash(**payload)
            == hashlib.sha256(canonical_tick_bytes(**payload)).hexdigest()
        )


class TestOrdering:
    """*Ordering*: keys alphabetical recursively, nodes by ``node_id``, edges
    by ``(source_id, target_id)`` — never backend iteration order."""

    def test_keys_sort_alphabetically_regardless_of_insertion_order(self) -> None:
        forward = canonical_tick_bytes(
            tick=0,
            rng_seed=0,
            nodes=[{"node_id": "A", "node_type": "territory", "zeta": 1, "alpha": 2}],
            edges=[],
            actions=[],
        )
        reversed_insertion = canonical_tick_bytes(
            tick=0,
            rng_seed=0,
            nodes=[{"alpha": 2, "zeta": 1, "node_type": "territory", "node_id": "A"}],
            edges=[],
            actions=[],
        )
        assert forward == reversed_insertion
        assert b'"alpha":2,"node_id":"A","node_type":"territory","zeta":1' in forward

    def test_key_sorting_is_recursive_through_nested_records(self) -> None:
        nested = canonical_tick_bytes(
            tick=0,
            rng_seed=0,
            nodes=[{"node_id": "A", "attrs": {"zeta": 1, "alpha": 2}}],
            edges=[],
            actions=[],
        )
        assert b'"attrs":{"alpha":2,"zeta":1}' in nested

    def test_nodes_sort_ascending_by_node_id_as_strings(self) -> None:
        # String comparison, not numeric: "C10" sorts before "C9".
        out = canonical_tick_bytes(
            tick=0,
            rng_seed=0,
            nodes=[{"node_id": "C9"}, {"node_id": "C10"}, {"node_id": "C1"}],
            edges=[],
            actions=[],
        )
        assert out.index(b'"C1"') < out.index(b'"C10"') < out.index(b'"C9"')

    def test_edges_sort_by_source_then_target(self) -> None:
        out = canonical_tick_bytes(
            tick=0,
            rng_seed=0,
            nodes=[],
            edges=[
                {"source_id": "B", "target_id": "A"},
                {"source_id": "A", "target_id": "Z"},
                {"source_id": "A", "target_id": "B"},
            ],
            actions=[],
        )
        assert out == (
            b'{"actions":[],"edges":['
            b'{"source_id":"A","target_id":"B"},'
            b'{"source_id":"A","target_id":"Z"},'
            b'{"source_id":"B","target_id":"A"}],'
            b'"nodes":[],"rng_seed":0,"tick":0}'
        )

    def test_action_order_is_preserved_not_sorted(self) -> None:
        # Actions are a *sequence of events applied this tick*; their order is
        # itself state. The spec's Ordering section sorts nodes and edges only.
        forward = canonical_tick_bytes(
            tick=0, rng_seed=0, nodes=[], edges=[], actions=[{"verb": "B"}, {"verb": "A"}]
        )
        assert forward.index(b'"B"') < forward.index(b'"A"')


class TestFloatEncoding:
    """*IEEE-754 f64*: raw big-endian bit pattern, 16 lowercase hex chars.

    The whole point of the departure from shortest-round-trip decimal is
    cross-language byte agreement on the awkward values, so those are what we
    pin."""

    @pytest.mark.parametrize(
        "value",
        [100.0, 12.5, 0.0, -0.0, 1e-308, 5e-324, 1.7976931348623157e308, 0.1, -1.5],
    )
    def test_float_is_the_big_endian_bit_pattern(self, value: float) -> None:
        expected = struct.pack(">d", value).hex()
        out = canonical_tick_bytes(
            tick=0, rng_seed=0, nodes=[{"node_id": "A", "v": value}], edges=[], actions=[]
        )
        assert f'"v":"{expected}"'.encode() in out
        assert len(expected) == 16

    def test_negative_zero_is_distinguishable_from_positive_zero(self) -> None:
        # A shortest-round-trip decimal encoder can render both as "0.0"; the
        # bit-pattern rule exists precisely so this distinction survives.
        positive = compute_tick_hash(
            tick=0, rng_seed=0, nodes=[{"node_id": "A", "v": 0.0}], edges=[], actions=[]
        )
        negative = compute_tick_hash(
            tick=0, rng_seed=0, nodes=[{"node_id": "A", "v": -0.0}], edges=[], actions=[]
        )
        assert positive != negative

    def test_hex_is_lowercase(self) -> None:
        out = canonical_tick_bytes(
            tick=0, rng_seed=0, nodes=[{"node_id": "A", "v": 255.5}], edges=[], actions=[]
        )
        assert b'"v":"406ff00000000000"' in out

    def test_nan_is_a_loud_failure(self) -> None:
        # NaN has multiple bit patterns and no meaningful equality; it must
        # never silently enter a change-detection hash.
        with pytest.raises(TickHashEncodingError, match="NaN"):
            canonical_tick_bytes(
                tick=0,
                rng_seed=0,
                nodes=[{"node_id": "A", "v": float("nan")}],
                edges=[],
                actions=[],
            )


class TestIntegerAndCurrencyEncoding:
    """*Integers* stay bare decimal; *Currency* i128 micro-units become
    decimal **strings** so no JSON f64 ever touches them."""

    def test_plain_integers_are_bare_json_numbers(self) -> None:
        out = canonical_tick_bytes(
            tick=7, rng_seed=42, nodes=[{"node_id": "A", "count": -13}], edges=[], actions=[]
        )
        assert b'"count":-13' in out
        assert b'"rng_seed":42' in out
        assert b'"tick":7' in out

    def test_micros_are_decimal_strings_never_bare_numbers(self) -> None:
        out = canonical_tick_bytes(
            tick=0,
            rng_seed=0,
            nodes=[{"node_id": "A", "wealth": Micros(1234567)}],
            edges=[],
            actions=[],
        )
        assert b'"wealth":"1234567"' in out

    def test_micros_survive_beyond_f64_exact_integer_range(self) -> None:
        # 2**53 + 1 is the canonical value an f64 cannot represent; a Rust
        # serde_json bare-number encoding would silently round it.
        beyond = 2**53 + 1
        out = canonical_tick_bytes(
            tick=0,
            rng_seed=0,
            nodes=[{"node_id": "A", "wealth": Micros(beyond)}],
            edges=[],
            actions=[],
        )
        assert f'"wealth":"{beyond}"'.encode() in out
        assert float(beyond) != beyond or True  # documents why: f64 cannot hold it

    def test_negative_micros_keep_a_single_leading_minus(self) -> None:
        out = canonical_tick_bytes(
            tick=0,
            rng_seed=0,
            nodes=[{"node_id": "A", "wealth": Micros(-42)}],
            edges=[],
            actions=[],
        )
        assert b'"wealth":"-42"' in out


class TestBooleanEncoding:
    """*Booleans*: bare ``true``/``false``, not ``"True"``/``"False"``, and not
    ``defines_hash``'s bool-as-int hazard."""

    def test_true_is_a_bare_json_literal(self) -> None:
        out = canonical_tick_bytes(
            tick=0, rng_seed=0, nodes=[{"node_id": "A", "active": True}], edges=[], actions=[]
        )
        assert b'"active":true' in out

    def test_false_is_a_bare_json_literal(self) -> None:
        out = canonical_tick_bytes(
            tick=0, rng_seed=0, nodes=[{"node_id": "A", "active": False}], edges=[], actions=[]
        )
        assert b'"active":false' in out

    def test_bool_never_degrades_to_an_integer(self) -> None:
        # `bool` is a subclass of `int` in Python; an isinstance-ordering bug
        # would render True as 1 and match a genuine integer field.
        as_bool = compute_tick_hash(
            tick=0, rng_seed=0, nodes=[{"node_id": "A", "v": True}], edges=[], actions=[]
        )
        as_int = compute_tick_hash(
            tick=0, rng_seed=0, nodes=[{"node_id": "A", "v": 1}], edges=[], actions=[]
        )
        assert as_bool != as_int


class TestNoneEncoding:
    """``None`` is the bare literal ``null``.

    An optional field that is unset is real state — the live graph is full of
    them (``county_fips``, ``aligned_faction_id``) — and ``null`` is
    unambiguous in every JSON implementation. This is the rule the spec
    originally omitted, found by hashing an actual graph."""

    def test_none_is_a_bare_null(self) -> None:
        out = canonical_tick_bytes(
            tick=0, rng_seed=0, nodes=[{"node_id": "A", "county_fips": None}], edges=[], actions=[]
        )
        assert b'"county_fips":null' in out

    def test_null_is_distinguishable_from_a_defaulted_zero(self) -> None:
        # The reason hashing null does not hide the `data.get(field, 0.0)`
        # bug class it might look like it hides: it makes it *visible*.
        unset = compute_tick_hash(
            tick=0, rng_seed=0, nodes=[{"node_id": "A", "v": None}], edges=[], actions=[]
        )
        defaulted = compute_tick_hash(
            tick=0, rng_seed=0, nodes=[{"node_id": "A", "v": 0.0}], edges=[], actions=[]
        )
        assert unset != defaulted

    def test_null_is_distinguishable_from_the_empty_string(self) -> None:
        unset = compute_tick_hash(
            tick=0, rng_seed=0, nodes=[{"node_id": "A", "v": None}], edges=[], actions=[]
        )
        empty = compute_tick_hash(
            tick=0, rng_seed=0, nodes=[{"node_id": "A", "v": ""}], edges=[], actions=[]
        )
        assert unset != empty


class TestStringAndEnumEncoding:
    def test_string_valued_enum_encodes_as_its_declared_value(self) -> None:
        class NodeKind(Enum):
            SOCIAL_CLASS = "social_class"

        out = canonical_tick_bytes(
            tick=0,
            rng_seed=0,
            nodes=[{"node_id": "A", "node_type": NodeKind.SOCIAL_CLASS}],
            edges=[],
            actions=[],
        )
        assert b'"node_type":"social_class"' in out

    def test_enum_value_casing_is_reproduced_not_normalized(self) -> None:
        class EdgeKind(Enum):
            EXPLOITATION = "EXPLOITATION"

        out = canonical_tick_bytes(
            tick=0,
            rng_seed=0,
            nodes=[],
            edges=[{"source_id": "A", "target_id": "B", "edge_type": EdgeKind.EXPLOITATION}],
            actions=[],
        )
        assert b'"edge_type":"EXPLOITATION"' in out

    def test_a_string_valued_enum_hashes_as_its_plain_string(self) -> None:
        # A port that stores the type as a plain string must agree with one
        # that stores it as an enum; the enum is our representation, not
        # content.
        class NodeKind(Enum):
            SOCIAL_CLASS = "social_class"

        as_enum = compute_tick_hash(
            tick=0,
            rng_seed=0,
            nodes=[{"node_id": "A", "node_type": NodeKind.SOCIAL_CLASS}],
            edges=[],
            actions=[],
        )
        as_string = compute_tick_hash(
            tick=0,
            rng_seed=0,
            nodes=[{"node_id": "A", "node_type": "social_class"}],
            edges=[],
            actions=[],
        )
        assert as_enum == as_string

    def test_int_valued_enum_is_a_loud_failure(self) -> None:
        # It would hash as a bare integer, silently aliasing a genuine
        # integer field, and its numbering is an internal detail.
        class Tier(IntEnum):
            FIRST = 1

        with pytest.raises(TickHashEncodingError, match="not a string"):
            canonical_tick_bytes(
                tick=0,
                rng_seed=0,
                nodes=[{"node_id": "A", "tier": Tier.FIRST}],
                edges=[],
                actions=[],
            )

    def test_enum_member_names_are_reproduced_verbatim_never_recased(self) -> None:
        out = canonical_tick_bytes(
            tick=0,
            rng_seed=0,
            nodes=[{"node_id": "A", "node_type": "social_class"}],
            edges=[{"source_id": "A", "target_id": "B", "edge_type": "EXPLOITATION"}],
            actions=[],
        )
        assert b'"node_type":"social_class"' in out
        assert b'"edge_type":"EXPLOITATION"' in out

    def test_non_ascii_is_escaped_so_the_byte_stream_stays_ascii(self) -> None:
        # ensure_ascii keeps the hashed bytes independent of any host's
        # Unicode normalization posture.
        out = canonical_tick_bytes(
            tick=0, rng_seed=0, nodes=[{"node_id": "Ω"}], edges=[], actions=[]
        )
        assert b"\\u03a9" in out
        out.decode("ascii")  # raises if a raw multibyte sequence leaked in


class TestBanOnStringlyFallbacks:
    """*Ban on stringly fallbacks* (Constitution III.11): a value with no
    encoding rule is a hash-time load failure, never ``str(obj)``."""

    def test_unknown_type_raises_rather_than_stringifying(self) -> None:
        class Opaque:
            def __str__(self) -> str:
                return "looks-harmless"

        with pytest.raises(TickHashEncodingError, match="no encoding rule"):
            canonical_tick_bytes(
                tick=0, rng_seed=0, nodes=[{"node_id": "A", "v": Opaque()}], edges=[], actions=[]
            )

    def test_non_string_record_keys_raise(self) -> None:
        # sort_keys cannot order a mixed-type key set, so the byte output
        # would silently depend on insertion order.
        with pytest.raises(TickHashEncodingError, match="canonical key ordering"):
            canonical_tick_bytes(
                tick=0,
                rng_seed=0,
                nodes=[{"node_id": "A", "attrs": {1: "x"}}],
                edges=[],
                actions=[],
            )

    def test_the_error_names_the_offending_field_and_type(self) -> None:
        with pytest.raises(TickHashEncodingError) as caught:
            canonical_tick_bytes(
                tick=0,
                rng_seed=0,
                nodes=[{"node_id": "A", "unhashable_field": complex(1, 2)}],
                edges=[],
                actions=[],
            )
        message = str(caught.value)
        assert "unhashable_field" in message
        assert "complex" in message


class TestWhatIsDeliberatelyNotInTheHash:
    def test_session_id_is_not_an_input(self) -> None:
        # The spec is explicit: "the session identifier never enters this
        # hash, keeping it independent of run identity, unlike
        # tick_commit.determinism_hash today". Passing one is a signature
        # error, not a silently-ignored kwarg.
        with pytest.raises(TypeError):
            compute_tick_hash(  # type: ignore[call-arg]
                tick=0,
                rng_seed=0,
                nodes=[],
                edges=[],
                actions=[],
                session_id="deadbeef",
            )

    def test_two_sessions_with_identical_state_hash_identically(self) -> None:
        # The positive statement of the same rule, and the property that makes
        # this hash able to detect a topology loss that determinism_hash cannot.
        state = {
            "tick": 5,
            "rng_seed": 2010,
            "nodes": [{"node_id": "A", "wealth": 1.0}],
            "edges": [],
            "actions": [],
        }
        assert compute_tick_hash(**state) == compute_tick_hash(**state)


class TestItDetectsWhatDeterminismHashCannot:
    """The reason this exists (dossier R1): today's gate cannot see topology."""

    BASE: dict[str, object] = {
        "tick": 5,
        "rng_seed": 2010,
        "nodes": [
            {"node_id": "A", "node_type": "social_class", "wealth": 100.0},
            {"node_id": "B", "node_type": "social_class", "wealth": 50.0},
        ],
        "edges": [{"source_id": "A", "target_id": "B", "edge_type": "EXPLOITATION"}],
        "actions": [],
    }

    def test_a_dropped_edge_moves_the_hash(self) -> None:
        lost = {**self.BASE, "edges": []}
        assert compute_tick_hash(**lost) != compute_tick_hash(**self.BASE)  # type: ignore[arg-type]

    def test_a_dropped_node_moves_the_hash(self) -> None:
        lost = {**self.BASE, "nodes": [self.BASE["nodes"][0]]}  # type: ignore[index]
        assert compute_tick_hash(**lost) != compute_tick_hash(**self.BASE)  # type: ignore[arg-type]

    def test_a_single_changed_attribute_moves_the_hash(self) -> None:
        drifted = {
            **self.BASE,
            "nodes": [
                {"node_id": "A", "node_type": "social_class", "wealth": 100.000001},
                {"node_id": "B", "node_type": "social_class", "wealth": 50.0},
            ],
        }
        assert compute_tick_hash(**drifted) != compute_tick_hash(**self.BASE)  # type: ignore[arg-type]

    def test_an_edge_retargeted_to_a_different_node_moves_the_hash(self) -> None:
        retargeted = {
            **self.BASE,
            "edges": [{"source_id": "B", "target_id": "A", "edge_type": "EXPLOITATION"}],
        }
        assert compute_tick_hash(**retargeted) != compute_tick_hash(**self.BASE)  # type: ignore[arg-type]
