"""Pytest fixtures and utilities for babylon.models tests.

This module provides shared fixtures and helper functions for testing
the Pydantic models in the babylon.models package.
"""

from typing import Any

import pytest
from pydantic import BaseModel, create_model


@pytest.fixture
def make_model() -> Any:
    """Factory fixture to create test models with specific field types.

    Usage:
        def test_probability(make_model):
            Model = make_model(prob=Probability)
            instance = Model(prob=0.5)
            assert instance.prob == 0.5

    Returns:
        A function that creates Pydantic models with the specified fields.
    """

    def _make_model(**field_types: Any) -> type[BaseModel]:
        """Create a test model with the given field types.

        Args:
            **field_types: Field names mapped to their types.
                          All fields are required.

        Returns:
            A dynamically created Pydantic BaseModel subclass.
        """
        fields = {name: (ftype, ...) for name, ftype in field_types.items()}
        return create_model("TestModel", **fields)

    return _make_model


@pytest.fixture
def sample_social_class_data() -> dict[str, Any]:
    """Sample data for creating a SocialClass instance.

    Returns valid data matching the Phase 1 blueprint.
    """
    return {
        "id": "C001",
        "name": "Periphery Mine Worker",
        "role": "periphery_proletariat",
        "wealth": 20.0,
        "ideology": -0.3,
    }


@pytest.fixture
def sample_relationship_data() -> dict[str, Any]:
    """Sample data for creating a Relationship instance.

    Returns valid data for the Phase 1 exploitation edge.
    """
    return {
        "source_id": "C001",
        "target_id": "C002",
        "edge_type": "exploitation",
        "value_flow": 80.0,
        "tension": 0.5,
    }
