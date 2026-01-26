"""Unit tests for geography CLI command."""

from __future__ import annotations

import inspect

import pytest

from babylon.data import cli


@pytest.mark.unit
def test_geography_command_exists() -> None:
    """Geography CLI command should exist."""
    assert hasattr(cli, "geography")
    assert callable(cli.geography)


@pytest.mark.unit
def test_geography_cli_default_reset_is_true() -> None:
    """Geography CLI should default reset to True."""
    params = inspect.signature(cli.geography).parameters
    assert params["reset"].default is True


@pytest.mark.unit
def test_geography_cli_default_quiet_is_false() -> None:
    """Geography CLI should default quiet to False."""
    params = inspect.signature(cli.geography).parameters
    assert params["quiet"].default is False


@pytest.mark.unit
def test_geography_cli_has_year_option() -> None:
    """Geography CLI should have optional year parameter."""
    params = inspect.signature(cli.geography).parameters
    assert "year" in params
    assert params["year"].default is None
