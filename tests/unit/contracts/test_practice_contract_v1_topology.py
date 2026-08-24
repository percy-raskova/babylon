"""Detached organization-practice topology validation contracts."""

from __future__ import annotations

import struct
from collections.abc import Callable

import pytest
from pydantic import ValidationError

from babylon.contracts.practice_contract_v1 import (
    PracticeContractViolation,
    validate_topology,
)
from babylon.contracts.practice_contract_v1_generated import (
    OrganizationPracticeTopologyEdgeV1,
    OrganizationPracticeTopologyRowV1,
    OrganizationPracticeTopologyV1,
    PracticeContractError,
    PracticeTargetDomainV1,
)


def _bits(value: float) -> int:
    return struct.unpack(">Q", struct.pack(">d", value))[0]


def _edge(target: int) -> OrganizationPracticeTopologyEdgeV1:
    return OrganizationPracticeTopologyEdgeV1(
        target_domain=PracticeTargetDomainV1.SOCIAL_CLASS,
        target_class_node_id_u64=target,
    )


def _row(
    node_id: int,
    *,
    active: bool = False,
    storage: float | None = None,
    edges: tuple[OrganizationPracticeTopologyEdgeV1, ...] = (),
) -> OrganizationPracticeTopologyRowV1:
    return OrganizationPracticeTopologyRowV1(
        node_id_u64=node_id,
        active_bool=active,
        action_budget_storage_f64_bits_u64=None if storage is None else _bits(storage),
        edges=edges,
    )


def _topology(
    rows: tuple[OrganizationPracticeTopologyRowV1, ...],
) -> OrganizationPracticeTopologyV1:
    return OrganizationPracticeTopologyV1(organizations=rows)


def _assert_error(expected: PracticeContractError, operation: Callable[[], object]) -> None:
    with pytest.raises(PracticeContractViolation) as caught:
        operation()
    assert caught.value.error is expected
    assert caught.value.error.value == expected.value


def test_topology_accepts_zero_and_exact_maximum_organizations() -> None:
    validate_topology(_topology(()))
    validate_topology(_topology(tuple(_row(node_id) for node_id in range(4_096))))


def test_topology_refuses_organization_max_plus_one() -> None:
    _assert_error(
        PracticeContractError.PRACTICE_TOPOLOGY_ORGANIZATION_LIMIT,
        lambda: validate_topology(_topology(tuple(_row(node_id) for node_id in range(4_097)))),
    )


@pytest.mark.parametrize(
    ("rows", "error"),
    [
        (
            (_row(2), _row(1)),
            PracticeContractError.PRACTICE_TOPOLOGY_ORGANIZATION_ORDER,
        ),
        (
            (_row(1), _row(1)),
            PracticeContractError.PRACTICE_TOPOLOGY_ORGANIZATION_DUPLICATE,
        ),
    ],
)
def test_topology_organization_identity_refusals_are_exact(
    rows: tuple[OrganizationPracticeTopologyRowV1, ...], error: PracticeContractError
) -> None:
    _assert_error(error, lambda: validate_topology(_topology(rows)))


def test_active_organization_requires_budget_storage() -> None:
    _assert_error(
        PracticeContractError.PRACTICE_TOPOLOGY_BUDGET_MISSING,
        lambda: validate_topology(_topology((_row(1, active=True),))),
    )


def test_budget_storage_is_validated_even_for_inactive_organization() -> None:
    _assert_error(
        PracticeContractError.PRACTICE_BUDGET_NEGATIVE,
        lambda: validate_topology(_topology((_row(1, storage=-1.0),))),
    )


def test_topology_accepts_inactive_absent_and_valid_budget_rows() -> None:
    validate_topology(_topology((_row(1), _row(2, storage=0.0))))
    validate_topology(_topology((_row(1, active=True, storage=1.0),)))


def test_topology_accepts_zero_and_exact_maximum_solidarity_edges() -> None:
    validate_topology(_topology((_row(1),)))
    validate_topology(_topology((_row(1, edges=tuple(_edge(target) for target in range(256))),)))


def test_topology_refuses_solidarity_edge_max_plus_one() -> None:
    _assert_error(
        PracticeContractError.PRACTICE_FOOTPRINT_LIMIT,
        lambda: validate_topology(
            _topology((_row(1, edges=tuple(_edge(target) for target in range(257))),))
        ),
    )


@pytest.mark.parametrize(
    ("edges", "error"),
    [
        (
            (_edge(2), _edge(1)),
            PracticeContractError.PRACTICE_TOPOLOGY_EDGE_ORDER,
        ),
        (
            (_edge(1), _edge(1)),
            PracticeContractError.PRACTICE_TOPOLOGY_EDGE_DUPLICATE,
        ),
    ],
)
def test_topology_edge_identity_refusals_are_exact(
    edges: tuple[OrganizationPracticeTopologyEdgeV1, ...], error: PracticeContractError
) -> None:
    _assert_error(error, lambda: validate_topology(_topology((_row(1, edges=edges),))))


@pytest.mark.parametrize("raw_code", [0, 2])
def test_topology_target_domain_is_closed_to_typed_social_class(raw_code: int) -> None:
    with pytest.raises(ValidationError):
        OrganizationPracticeTopologyEdgeV1(
            target_domain=raw_code,
            target_class_node_id_u64=1,
        )


def test_detached_topology_validation_is_not_execution_authorization() -> None:
    topology = _topology((_row(1, active=False, edges=(_edge(2),)),))
    assert validate_topology(topology) is None
    assert not hasattr(topology, "authorized")
    assert not hasattr(topology, "eligible")
