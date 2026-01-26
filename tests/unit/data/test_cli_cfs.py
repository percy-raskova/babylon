"""Unit tests for CFS CLI command."""

from __future__ import annotations

import inspect

import pytest

from babylon.data import cli


@pytest.mark.unit
def test_cfs_command_exists() -> None:
    """CFS CLI command should exist."""
    assert hasattr(cli, "cfs")
    assert callable(cli.cfs)


@pytest.mark.unit
def test_cfs_cli_default_reset_is_true() -> None:
    """CFS CLI should default reset to True."""
    params = inspect.signature(cli.cfs).parameters
    assert params["reset"].default is True


@pytest.mark.unit
def test_cfs_cli_default_quiet_is_false() -> None:
    """CFS CLI should default quiet to False."""
    params = inspect.signature(cli.cfs).parameters
    assert params["quiet"].default is False


@pytest.mark.unit
def test_cfs_cli_default_year_is_none() -> None:
    """CFS CLI should default year to None (uses 2022)."""
    params = inspect.signature(cli.cfs).parameters
    assert params["year"].default is None


@pytest.mark.unit
def test_cfs_cli_has_year_option() -> None:
    """CFS CLI should have optional year parameter."""
    params = inspect.signature(cli.cfs).parameters
    assert "year" in params
