"""Tests for the HexMap Django API Endpoint."""

import json
import uuid
from unittest.mock import MagicMock

import pytest
from django.contrib.auth.models import User
from django.test import Client

import game.api
from game.models import GameSession


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

        # Check call args
        mock_bridge.get_map_snapshot.assert_called_once_with(session.id, tick=None)

    def test_get_map_snapshot_with_tick(self):
        client, session, mock_bridge = self._setup_bridge_and_session()
        game.api._bridge_instance = mock_bridge

        response = client.get(f"/api/games/{session.id}/map/?tick=10")
        assert response.status_code == 200

        # Check call args
        mock_bridge.get_map_snapshot.assert_called_once_with(session.id, tick=10)

    def test_get_map_snapshot_unauthenticated(self):
        client = Client()
        session_id = uuid.uuid4()
        response = client.get(f"/api/games/{session_id}/map/")

        # DRF returns 403 for unauthenticated sessions
        assert response.status_code == 403
