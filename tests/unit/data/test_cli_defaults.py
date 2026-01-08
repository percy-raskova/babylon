"""Unit tests for data CLI defaults."""

from __future__ import annotations

import inspect

import pytest

from babylon.data import cli


@pytest.mark.unit
def test_census_cli_default_year() -> None:
    """Census CLI should default to 2021."""
    params = inspect.signature(cli.census).parameters
    assert params["year"].default == 2021
