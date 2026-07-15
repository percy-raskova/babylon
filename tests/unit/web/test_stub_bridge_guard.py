"""Seam Sensor 3 (provenance): the StubEngineBridge honesty guard.

``StubEngineBridge`` serves fabricated values through the real API contract. That
is legitimate in DEBUG (dev / stub settings), but serving it with DEBUG off would
render fake data as if it were real — the "rendered but fake" provenance
violation. ``_get_bridge`` must fail loud (Constitution III.11) in that case
rather than silently faking, and must still allow the Stub in DEBUG.
"""

from __future__ import annotations

from collections.abc import Generator

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings

import game.api as api

pytestmark = pytest.mark.unit


@pytest.fixture
def _uninitialized_bridge() -> Generator[None, None, None]:
    """Force the uninitialized-bridge path, restoring the singleton afterwards."""
    saved = api._bridge_instance
    api._bridge_instance = None
    try:
        yield
    finally:
        api._bridge_instance = saved


@pytest.mark.usefixtures("_uninitialized_bridge")
@override_settings(DEBUG=False)
def test_stub_bridge_refused_with_debug_off() -> None:
    """Production (DEBUG off) must refuse the fabricated-data Stub, loudly."""
    with pytest.raises(ImproperlyConfigured, match="Sensor 3 provenance"):
        api._get_bridge()


@pytest.mark.usefixtures("_uninitialized_bridge")
@override_settings(DEBUG=True)
def test_stub_bridge_allowed_with_debug_on() -> None:
    """DEBUG (dev) still gets the Stub fallback so the app boots without Postgres."""
    from game.stub_bridge import StubEngineBridge

    assert isinstance(api._get_bridge(), StubEngineBridge)
