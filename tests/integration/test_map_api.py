"""Tests for the HexMap Django API Endpoint."""

import json
import uuid
from unittest.mock import MagicMock

import pytest
from django.contrib.auth.models import User
from django.db import connection
from django.test import Client

import game.api
from game.models import GameSession


@pytest.fixture(autouse=True)
def _create_unmanaged_tables(db: None) -> None:
    """Create unmanaged model tables for the SQLite test DB.

    GameSession has managed=False (it lives in Postgres in production).
    For tests using the Django test runner with SQLite, we must create
    the table manually via raw DDL.
    """
    with connection.cursor() as cursor:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS game_session (
                id          CHAR(36) PRIMARY KEY,
                player_id   INTEGER,
                scenario    VARCHAR(64) NOT NULL,
                current_tick INTEGER NOT NULL DEFAULT 0,
                status      VARCHAR(16) NOT NULL DEFAULT 'active',
                config_json TEXT NOT NULL DEFAULT '{}',
                game_defines_json TEXT NOT NULL DEFAULT '{}',
                trace_level VARCHAR(8) NOT NULL DEFAULT 'NONE',
                rng_seed    BIGINT NOT NULL DEFAULT 0,
                created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


@pytest.mark.unit
@pytest.mark.django_db
class TestMapApi:
    """Verify that GET /api/games/{id}/map/ works correctly."""

    def _setup_bridge_and_session(self) -> tuple:
        """Create a mock bridge, inject it, and create a game session + user."""
        user = User.objects.create_user(username="mapuser", password="mappass123")  # type: ignore[no-untyped-call]
        client = Client()
        client.login(username="mapuser", password="mappass123")

        session_id = uuid.uuid4()
        session = GameSession.objects.create(
            id=session_id,
            player_id=user.id,
            scenario="two_node",
            current_tick=42,
            status="active",
        )

        mock_bridge = MagicMock()
        mock_bridge.get_map_snapshot.return_value = {
            "type": "FeatureCollection",
            "metadata": {
                "tick": 42,
                "scenario": "two_node",
                "h3_resolution": 7,
                "available_metrics": ["heat"],
            },
            "features": [],
        }
        return client, session, mock_bridge

    def test_get_map_snapshot(self):
        client, session, mock_bridge = self._setup_bridge_and_session()
        game.api._bridge_instance = mock_bridge

        response = client.get(f"/api/games/{session.id}/map/")
        assert response.status_code == 200

        data = json.loads(response.content)
        assert data["status"] == "ok"
        assert data["tick"] == 42
        assert data["session_id"] == str(session.id)

        # Verify the payload structure
        payload = data["data"]
        assert payload["type"] == "FeatureCollection"
        assert payload["metadata"]["tick"] == 42
        assert "features" in payload

        # Check call args — now includes zoom='county' (default)
        mock_bridge.get_map_snapshot.assert_called_once_with(
            session.id, tick=None, _layer=None, zoom="county"
        )

    def test_get_map_snapshot_with_tick(self):
        client, session, mock_bridge = self._setup_bridge_and_session()
        game.api._bridge_instance = mock_bridge

        response = client.get(f"/api/games/{session.id}/map/?tick=10")
        assert response.status_code == 200

        # Check call args — now includes zoom='county' (default)
        mock_bridge.get_map_snapshot.assert_called_once_with(
            session.id, tick=10, _layer=None, zoom="county"
        )

    def test_get_map_snapshot_unauthenticated(self):
        client = Client()
        session_id = uuid.uuid4()
        response = client.get(f"/api/games/{session_id}/map/")

        # DRF returns 403 for unauthenticated sessions
        assert response.status_code == 403

    def test_get_map_with_zoom_hex(self):
        """zoom=hex should pass through to bridge."""
        client, session, mock_bridge = self._setup_bridge_and_session()
        game.api._bridge_instance = mock_bridge

        response = client.get(f"/api/games/{session.id}/map/?zoom=hex")
        assert response.status_code == 200

        mock_bridge.get_map_snapshot.assert_called_once_with(
            session.id, tick=None, _layer=None, zoom="hex"
        )

    def test_get_map_with_zoom_bea(self):
        """zoom=bea should pass through to bridge."""
        client, session, mock_bridge = self._setup_bridge_and_session()
        game.api._bridge_instance = mock_bridge

        response = client.get(f"/api/games/{session.id}/map/?zoom=bea")
        assert response.status_code == 200

        mock_bridge.get_map_snapshot.assert_called_once_with(
            session.id, tick=None, _layer=None, zoom="bea"
        )

    def test_get_map_with_zoom_state(self):
        """zoom=state should pass through to bridge."""
        client, session, mock_bridge = self._setup_bridge_and_session()
        game.api._bridge_instance = mock_bridge

        response = client.get(f"/api/games/{session.id}/map/?zoom=state")
        assert response.status_code == 200

        mock_bridge.get_map_snapshot.assert_called_once_with(
            session.id, tick=None, _layer=None, zoom="state"
        )

    def test_get_map_invalid_zoom_returns_400(self):
        """Invalid zoom parameter should return 400."""
        client, session, mock_bridge = self._setup_bridge_and_session()
        game.api._bridge_instance = mock_bridge

        response = client.get(f"/api/games/{session.id}/map/?zoom=galaxy")
        assert response.status_code == 400

        data = json.loads(response.content)
        assert data["status"] == "error"
        assert "galaxy" in data["message"]

    def test_get_map_zoom_with_tick(self):
        """zoom + tick should both pass through."""
        client, session, mock_bridge = self._setup_bridge_and_session()
        game.api._bridge_instance = mock_bridge

        response = client.get(f"/api/games/{session.id}/map/?tick=5&zoom=msa")
        assert response.status_code == 200

        mock_bridge.get_map_snapshot.assert_called_once_with(
            session.id, tick=5, _layer=None, zoom="msa"
        )
