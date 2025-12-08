"""Pytest fixtures for component tests.

Shared fixtures and helper functions for testing the Component system.
"""

from typing import Any

import pytest
from pydantic import BaseModel, create_model


@pytest.fixture
def make_model() -> Any:
    """Factory fixture to create test models with specific field types.

    Usage:
        def test_component(make_model):
            Model = make_model(value=Currency)
            instance = Model(value=10.0)
            assert instance.value == 10.0

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
