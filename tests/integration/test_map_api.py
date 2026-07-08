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
        # hex_latest DDL copied verbatim from tests/unit/web/conftest.py
        # (models the composite UNIQUE(game_id, h3_index) of the Postgres
        # PRIMARY KEY in postgres_schema.py).
        cursor.execute(
            """CREATE TABLE IF NOT EXISTS hex_latest (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id CHAR(32) NOT NULL REFERENCES game_session(id) ON DELETE CASCADE,
                tick INTEGER NOT NULL,
                h3_index VARCHAR(20) NOT NULL,
                county_fips VARCHAR(5) NOT NULL,
                county_name VARCHAR(100) NOT NULL,
                bea_ea_code VARCHAR(8),
                msa_code VARCHAR(10),
                state_fips VARCHAR(2) NOT NULL DEFAULT '26',
                center_lat REAL NOT NULL,
                center_lng REAL NOT NULL,
                profit_rate REAL,
                exploitation_rate REAL,
                occ REAL,
                imperial_rent REAL,
                g33_visibility REAL,
                pop_bourgeoisie INTEGER DEFAULT 0,
                pop_petit_bourgeoisie INTEGER DEFAULT 0,
                pop_labor_aristocracy INTEGER DEFAULT 0,
                pop_proletariat INTEGER DEFAULT 0,
                pop_lumpenproletariat INTEGER DEFAULT 0,
                pop_total INTEGER DEFAULT 0,
                dominant_class VARCHAR(24),
                faction_finance_capital REAL,
                faction_security_state REAL,
                faction_settler_populist REAL,
                heat REAL DEFAULT 0.0,
                heat_delta REAL DEFAULT 0.0,
                org_count INTEGER DEFAULT 0,
                actions_taken INTEGER DEFAULT 0,
                was_target BOOLEAN DEFAULT 0,
                terrain_type VARCHAR(16) DEFAULT 'LAND',
                water_coverage REAL DEFAULT 0.0,
                internet_access BOOLEAN DEFAULT 0,
                UNIQUE(game_id, h3_index)
            )"""
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


@pytest.mark.unit
@pytest.mark.django_db
class TestMapFeaturesAfterCreateGame:
    """P0 #7 (RED): a real game must project territories into hex_latest so
    GET /api/games/{id}/map/?zoom=hex returns features > 0."""

    def test_map_features_positive_after_create_game(self):
        from game.engine_bridge import EngineBridge, _build_initial_state_for_scenario

        user = User.objects.create_user(username="hexuser", password="hexpass123")
        client = Client()
        client.login(username="hexuser", password="hexpass123")

        session_id = uuid.uuid4()

        mock_persistence = MagicMock()

        # Mimic PostgresRuntime.create_session: it inserts the game_session
        # row the HexState FK points at (same table Django reads in prod).
        def _create_session(**kwargs):
            GameSession.objects.create(
                id=session_id,
                player_id=user.id,
                scenario=kwargs["scenario"],
                current_tick=0,
                status="active",
            )
            return session_id

        mock_persistence.create_session.side_effect = _create_session
        mock_persistence.persist_tick.return_value = None
        mock_persistence.hydrate_graph.return_value = _build_initial_state_for_scenario(
            "wayne_county"
        ).to_graph()

        bridge = EngineBridge(mock_persistence)
        game.api._bridge_instance = bridge

        created_id = bridge.create_game(scenario="wayne_county", rng_seed=42)
        assert created_id == session_id

        response = client.get(f"/api/games/{session_id}/map/?zoom=hex")
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data["status"] == "ok"
        assert len(data["data"]["features"]) > 0
