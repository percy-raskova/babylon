"""org_probe: the two-org world backing the Organization estate's Python byte
gates (Task 11, spec §11).

Deliberately minimal — one SocialClass, one Territory, one CivilSocietyOrg,
one StateApparatus — so ``state.organizations`` and the ``NodeType.ORGANIZATION``
graph nodes it projects are real, non-fixture evidence rather than a stamped
placeholder (CLAUDE.md's "no fixture-stamped attribute shapes" gotcha).
"""

from __future__ import annotations

import pytest

from babylon.engine.scenarios.org_probe import create_org_probe_scenario
from babylon.models.enums import NodeType

pytestmark = pytest.mark.unit


def test_org_probe_seeds_two_orgs_visible_to_the_graph() -> None:
    state, _config, _defines = create_org_probe_scenario()
    assert len(state.organizations) == 2
    kinds = {type(o).__name__ for o in state.organizations.values()}
    assert kinds == {"CivilSocietyOrg", "StateApparatus"}
    graph = state.to_graph()
    org_nodes = [
        n for n, d in graph.nodes(data=True) if d.get("_node_type") == NodeType.ORGANIZATION.value
    ]
    assert len(org_nodes) == 2


def test_org_probe_is_deterministic() -> None:
    a = create_org_probe_scenario()[0]
    b = create_org_probe_scenario()[0]
    assert a.model_dump() == b.model_dump()


def test_org_probe_config_carries_a_fixed_seed() -> None:
    _state, config, _defines = create_org_probe_scenario()
    assert config.rng_seed == 42
