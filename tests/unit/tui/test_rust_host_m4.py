"""Contract for the M4 "Topology + the 3D lane" ``RustClientHost`` read
surface (Task 30, ADR150): ``topology_json``/``field_state_json`` (call1/
call0).

Companion to ``test_host_contract.py`` (M0/M1), ``test_rust_host_m2.py``
(M2), and ``test_rust_host_m3.py`` (M3): pinned against
``docs/superpowers/specs/2026-07-27-m4-topology-contracts.md`` §1/§2. Unit
tier only (no Postgres, no Textual, no real engine) — this file tests the
HOST's own thin-passthrough/null-conversion contract, exactly like every
sibling ``*_json`` method in ``host.py``: the heavy envelope-building logic
(``paoh``/``egotree``/``incidence``/``adjacency`` ordering + layout, the
field-state projection) lives in :meth:`~babylon.game.session.GameSession.
topology_view`/:meth:`~babylon.game.session.GameSession.field_state_view`,
which this file's ``_FakeSession`` double stands in for — mirroring
``test_rust_host_m3.py``'s own ``_FakeSession`` convention (only the members
the M4 surface actually calls, returning canned data rather than
re-deriving it).

The per-kind envelope literals below are transcribed VERBATIM from the
contract's own §1 examples (down to the ``"union_local"`` placeholder
community id, which is not a real ``CommunityType`` member — irrelevant at
this layer, since ``host.py`` never inspects envelope contents, only
serializes whatever the bound session hands back).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from uuid import UUID

import pytest

from babylon.projection.view_models import FieldStateView
from babylon.tui.campaign_menu import InMemoryCampaignCatalog
from babylon.tui.host import RustClientHost

pytestmark = [pytest.mark.unit]

_DEFINES_HASH = "f00dface" * 8
_ENGINE_VERSION = "7.7.7"
_SESSION_ID = UUID("00000000-0000-0000-0000-0000000000f4")

# --------------------------------------------------------------------------- #
# The four contract §1 envelope literals, transcribed verbatim.               #
# --------------------------------------------------------------------------- #

PAOH_ENVELOPE = {
    "kind": "paoh",
    "verified_tick": 500,
    "nodes": ["C001", "C002"],
    "edges": [{"community_id": "union_local", "formation_tick": None, "members": ["C001", "C002"]}],
    "layout": {"C001": [0.0, 1.0], "C002": [0.9510, 0.3090]},
}

EGOTREE_ENVELOPE = {
    "kind": "egotree",
    "verified_tick": 500,
    "root_id": "C001",
    "root_side": "member",
    "children": [{"node_id": "union_local", "neighbors": ["C002"]}],
}

INCIDENCE_ENVELOPE = {
    "kind": "incidence",
    "verified_tick": 500,
    "nodes": ["C001"],
    "hyperedges": ["union_local"],
    "cells": [[True]],
}

ADJACENCY_ENVELOPE = {
    "kind": "adjacency",
    "verified_tick": 500,
    "nodes": ["C001", "C002"],
    "cells": [[False, True], [True, False]],
}


# --------------------------------------------------------------------------- #
# Fakes.                                                                       #
# --------------------------------------------------------------------------- #


@dataclass
class _FakeSession:
    """A minimal ``CampaignHandle`` double covering only ``topology_view``/
    ``field_state_view`` — mirrors ``test_rust_host_m3.py``'s own
    ``_FakeSession`` convention (only the members M4's host surface actually
    calls)."""

    session_id: UUID = _SESSION_ID
    tick: int = 0
    topology_calls: list[tuple[str, str | None]] = field(default_factory=list)
    topology_by_call: dict[tuple[str, str | None], dict[str, object] | None] = field(
        default_factory=dict
    )
    field_state_calls: int = 0
    field_state_result: FieldStateView | None = None

    def topology_view(self, kind: str, focus: str | None = None) -> dict[str, object] | None:
        self.topology_calls.append((kind, focus))
        return self.topology_by_call.get((kind, focus))

    def field_state_view(self) -> FieldStateView | None:
        self.field_state_calls += 1
        return self.field_state_result


class _RaisingTopologySession:
    """Simulates ``GameSession.topology_view``'s own loud failure for a
    ``kind`` naming none of the four RULED kinds (contract §1) — a
    caller-protocol error, never absence, so the host must never launder it
    into ``"null"``."""

    def topology_view(self, kind: str, focus: str | None = None) -> dict[str, object] | None:
        msg = f"GameSession.topology_view: unrecognized kind {kind!r}"
        raise ValueError(msg)

    def field_state_view(self) -> FieldStateView | None:
        raise AssertionError("not exercised by this double")


def _host(**kwargs: object) -> RustClientHost:
    return RustClientHost(
        InMemoryCampaignCatalog(),
        defines_hash=_DEFINES_HASH,
        engine_version=_ENGINE_VERSION,
        **kwargs,  # type: ignore[arg-type]
    )


def _args(kind: str, *, focus: str | None = None) -> str:
    """The Rust-built ``topology_json`` argument (§1's pinned field order)."""
    return json.dumps({"kind": kind, "focus": focus})


# --------------------------------------------------------------------------- #
# No session bound -> "null" (both methods).                                  #
# --------------------------------------------------------------------------- #


class TestNoSessionNull:
    def test_topology_json_is_null_when_unbound(self) -> None:
        host = _host()
        assert host.topology_json(_args("paoh")) == "null"

    def test_field_state_json_is_null_when_unbound(self) -> None:
        host = _host()
        assert host.field_state_json() == "null"

    def test_topology_json_still_parses_malformed_args_even_when_unbound(self) -> None:
        host = _host()
        with pytest.raises(ValueError):
            host.topology_json("{not valid json")


# --------------------------------------------------------------------------- #
# Per-kind envelope shape + field order — pass-through pin.                   #
# --------------------------------------------------------------------------- #


class TestTopologyJsonPerKindEnvelopeShape:
    def test_paoh_envelope_round_trips_with_pinned_field_order(self) -> None:
        session = _FakeSession(topology_by_call={("paoh", None): PAOH_ENVELOPE})
        host = _host()
        host.bind_session(session, None)  # type: ignore[arg-type]

        raw = host.topology_json(_args("paoh"))

        assert json.loads(raw) == PAOH_ENVELOPE
        assert list(json.loads(raw).keys()) == ["kind", "verified_tick", "nodes", "edges", "layout"]
        assert session.topology_calls == [("paoh", None)]

    def test_egotree_envelope_round_trips_with_pinned_field_order(self) -> None:
        session = _FakeSession(topology_by_call={("egotree", "C001"): EGOTREE_ENVELOPE})
        host = _host()
        host.bind_session(session, None)  # type: ignore[arg-type]

        raw = host.topology_json(_args("egotree", focus="C001"))

        assert json.loads(raw) == EGOTREE_ENVELOPE
        assert list(json.loads(raw).keys()) == [
            "kind",
            "verified_tick",
            "root_id",
            "root_side",
            "children",
        ]
        assert session.topology_calls == [("egotree", "C001")]

    def test_incidence_envelope_round_trips_with_pinned_field_order(self) -> None:
        session = _FakeSession(topology_by_call={("incidence", None): INCIDENCE_ENVELOPE})
        host = _host()
        host.bind_session(session, None)  # type: ignore[arg-type]

        raw = host.topology_json(_args("incidence"))

        assert json.loads(raw) == INCIDENCE_ENVELOPE
        assert list(json.loads(raw).keys()) == [
            "kind",
            "verified_tick",
            "nodes",
            "hyperedges",
            "cells",
        ]

    def test_adjacency_envelope_round_trips_with_pinned_field_order(self) -> None:
        session = _FakeSession(topology_by_call={("adjacency", None): ADJACENCY_ENVELOPE})
        host = _host()
        host.bind_session(session, None)  # type: ignore[arg-type]

        raw = host.topology_json(_args("adjacency"))

        assert json.loads(raw) == ADJACENCY_ENVELOPE
        assert list(json.loads(raw).keys()) == ["kind", "verified_tick", "nodes", "cells"]

    def test_focus_is_ignored_for_the_three_non_egotree_kinds_but_still_threaded(self) -> None:
        """``focus`` is IGNORED by the three non-``egotree`` kinds (contract
        §1) — this host method never special-cases it either way, always
        threading whatever Rust sent straight to ``session.topology_view``;
        the fake's own dict-key lookup exercises the case where a caller
        sends a non-``None`` focus alongside ``paoh``."""
        session = _FakeSession(topology_by_call={("paoh", "C001"): PAOH_ENVELOPE})
        host = _host()
        host.bind_session(session, None)  # type: ignore[arg-type]

        raw = host.topology_json(_args("paoh", focus="C001"))

        assert json.loads(raw) == PAOH_ENVELOPE
        assert session.topology_calls == [("paoh", "C001")]


class TestPaohMembersSerializeSorted:
    """§1: "``members`` serializes SORTED (frozenset -> sorted list;
    determinism)." Verified here as a pass-through pin: the host must not
    disturb an already-sorted ``members`` list ``GameSession.topology_view``
    hands it."""

    def test_members_list_order_is_preserved_through_the_host(self) -> None:
        envelope = {
            "kind": "paoh",
            "verified_tick": 12,
            "nodes": ["C001", "C002", "C003"],
            "edges": [
                {
                    "community_id": "settler",
                    "formation_tick": None,
                    "members": ["C001", "C002", "C003"],
                }
            ],
            "layout": {},
        }
        session = _FakeSession(topology_by_call={("paoh", None): envelope})
        host = _host()
        host.bind_session(session, None)  # type: ignore[arg-type]

        payload = json.loads(host.topology_json(_args("paoh")))

        assert payload["edges"][0]["members"] == ["C001", "C002", "C003"]


# --------------------------------------------------------------------------- #
# egotree null cases.                                                         #
# --------------------------------------------------------------------------- #


class TestEgotreeNullCases:
    def test_focus_none_is_null(self) -> None:
        session = _FakeSession(topology_by_call={("egotree", None): None})
        host = _host()
        host.bind_session(session, None)  # type: ignore[arg-type]

        assert host.topology_json(_args("egotree", focus=None)) == "null"
        assert session.topology_calls == [("egotree", None)]

    def test_unresolvable_focus_is_null(self) -> None:
        session = _FakeSession(topology_by_call={("egotree", "not_a_real_id"): None})
        host = _host()
        host.bind_session(session, None)  # type: ignore[arg-type]

        assert host.topology_json(_args("egotree", focus="not_a_real_id")) == "null"

    def test_recognized_root_with_zero_edges_is_the_same_null(self) -> None:
        # The projection's own ``levi_ego_tree`` honest ``None`` (a real
        # root, zero bipartite edges) collapses to the identical "null" a
        # missing/unresolvable focus produces (contract §1).
        session = _FakeSession(topology_by_call={("egotree", "C999"): None})
        host = _host()
        host.bind_session(session, None)  # type: ignore[arg-type]

        assert host.topology_json(_args("egotree", focus="C999")) == "null"

    def test_a_real_focus_still_resolves_normally(self) -> None:
        session = _FakeSession(topology_by_call={("egotree", "C001"): EGOTREE_ENVELOPE})
        host = _host()
        host.bind_session(session, None)  # type: ignore[arg-type]

        assert json.loads(host.topology_json(_args("egotree", focus="C001"))) == EGOTREE_ENVELOPE


class TestUnrecognizedKindPropagatesLoudly:
    def test_unrecognized_kind_raises_value_error_never_null(self) -> None:
        host = _host()
        host.bind_session(_RaisingTopologySession(), None)  # type: ignore[arg-type]

        with pytest.raises(ValueError, match="bogus"):
            host.topology_json(_args("bogus"))


# --------------------------------------------------------------------------- #
# field_state_json — call0, live-graph pass-through.                          #
# --------------------------------------------------------------------------- #


class TestFieldStateJson:
    def test_bound_session_serializes_the_view_model(self) -> None:
        view = FieldStateView(field_state_id="USA", verified_tick=7)
        session = _FakeSession(field_state_result=view)
        host = _host()
        host.bind_session(session, None)  # type: ignore[arg-type]

        raw = host.field_state_json()

        assert raw == view.model_dump_json()
        assert json.loads(raw)["field_state_id"] == "USA"
        assert json.loads(raw)["verified_tick"] == 7
        # call0: no arguments cross the seam.
        assert session.field_state_calls == 1

    def test_bound_session_returning_none_is_null(self) -> None:
        session = _FakeSession(field_state_result=None)
        host = _host()
        host.bind_session(session, None)  # type: ignore[arg-type]

        assert host.field_state_json() == "null"

    def test_repeated_calls_hit_the_session_every_time_no_cache(self) -> None:
        view = FieldStateView(field_state_id="USA", verified_tick=1)
        session = _FakeSession(field_state_result=view)
        host = _host()
        host.bind_session(session, None)  # type: ignore[arg-type]

        host.field_state_json()
        host.field_state_json()
        host.field_state_json()

        assert session.field_state_calls == 3
