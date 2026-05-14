"""Frozen-model + LookupPolicy enum test (T023).

Validates :class:`CoefficientLookupPolicy` per data-model.md §2.5.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from babylon.economics.coefficient_lookup import (
    CoefficientLookupPolicy,
    LookupPolicy,
)


@pytest.mark.cross_scale
class TestLookupPolicyEnum:
    def test_slowly_varying_value(self) -> None:
        assert LookupPolicy.SLOWLY_VARYING == "slowly_varying"

    def test_event_discrete_value(self) -> None:
        assert LookupPolicy.EVENT_DISCRETE == "event_discrete"

    def test_exhaustive(self) -> None:
        assert {p.value for p in LookupPolicy} == {
            "slowly_varying",
            "event_discrete",
        }


@pytest.mark.cross_scale
class TestCoefficientLookupPolicyModel:
    def test_valid_construction(self) -> None:
        policy = CoefficientLookupPolicy(
            series_id="bea_io_imports",
            policy=LookupPolicy.SLOWLY_VARYING,
            canonical_reference="BEA Make-Use-Imports 2010-2024",
        )
        assert policy.series_id == "bea_io_imports"
        assert policy.policy is LookupPolicy.SLOWLY_VARYING

    def test_is_frozen(self) -> None:
        policy = CoefficientLookupPolicy(
            series_id="bea_io_imports",
            policy=LookupPolicy.SLOWLY_VARYING,
            canonical_reference="BEA Make-Use-Imports 2010-2024",
        )
        with pytest.raises(ValidationError):
            policy.series_id = "something_else"  # type: ignore[misc]

    def test_empty_series_id_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CoefficientLookupPolicy(
                series_id="",
                policy=LookupPolicy.SLOWLY_VARYING,
                canonical_reference="ref",
            )

    def test_empty_canonical_reference_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CoefficientLookupPolicy(
                series_id="x",
                policy=LookupPolicy.SLOWLY_VARYING,
                canonical_reference="",
            )
