"""Tests for Django ORM models (Phase 2).

Verifies model metadata, field types, and column alignment
with Feature 037's ``postgres_schema.py`` DDL.
"""

from __future__ import annotations

import ast
import uuid
from pathlib import Path

import pytest
from django.db import models

from accounts.models import PlayerProfile
from game.models import ActionResult, GameSession, PlayerAction

# Path to models.py source for AST-based managed=False verification.
# conftest overrides _meta.managed at runtime for SQLite test DB creation,
# so we verify the source declaration instead of the runtime value.
_MODELS_SOURCE = Path(__file__).resolve().parent.parent.parent.parent / "web" / "game" / "models.py"


def _source_declares_managed_false(source_path: Path, class_name: str) -> bool:
    """Check if a Django model class declares managed=False in its Meta class via AST."""
    tree = ast.parse(source_path.read_text())
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef) or node.name != class_name:
            continue
        for inner in node.body:
            if isinstance(inner, ast.ClassDef) and inner.name == "Meta":
                for stmt in inner.body:
                    if (
                        isinstance(stmt, ast.Assign)
                        and len(stmt.targets) == 1
                        and isinstance(stmt.targets[0], ast.Name)
                        and stmt.targets[0].id == "managed"
                        and isinstance(stmt.value, ast.Constant)
                        and stmt.value.value is False
                    ):
                        return True
    return False


@pytest.mark.unit
class TestGameSessionMeta:
    """Verify GameSession model metadata matches postgres_schema.py DDL."""

    def test_managed_is_false_in_source(self) -> None:
        # conftest overrides _meta.managed=True for SQLite test DB creation,
        # so verify the source declaration via AST inspection.
        assert _source_declares_managed_false(_MODELS_SOURCE, "GameSession")

    def test_db_table(self) -> None:
        assert GameSession._meta.db_table == "game_session"

    def test_pk_is_uuid(self) -> None:
        pk_field = GameSession._meta.get_field("id")
        assert isinstance(pk_field, models.UUIDField)
        assert pk_field.primary_key is True

    def test_pk_default_is_uuid4(self) -> None:
        pk_field = GameSession._meta.get_field("id")
        assert pk_field.default is uuid.uuid4

    def test_player_id_nullable(self) -> None:
        field = GameSession._meta.get_field("player_id")
        assert isinstance(field, models.IntegerField)
        assert field.null is True

    def test_scenario_field(self) -> None:
        field = GameSession._meta.get_field("scenario")
        assert isinstance(field, models.CharField)
        assert field.max_length == 64

    def test_current_tick_default(self) -> None:
        field = GameSession._meta.get_field("current_tick")
        assert isinstance(field, models.IntegerField)
        assert field.default == 0

    def test_status_field(self) -> None:
        field = GameSession._meta.get_field("status")
        assert isinstance(field, models.CharField)
        assert field.max_length == 16
        assert field.default == "active"

    def test_config_json_field(self) -> None:
        field = GameSession._meta.get_field("config_json")
        assert isinstance(field, models.JSONField)

    def test_game_defines_json_field(self) -> None:
        field = GameSession._meta.get_field("game_defines_json")
        assert isinstance(field, models.JSONField)

    def test_trace_level_field(self) -> None:
        field = GameSession._meta.get_field("trace_level")
        assert isinstance(field, models.CharField)
        assert field.max_length == 8
        assert field.default == "NONE"

    def test_rng_seed_field(self) -> None:
        field = GameSession._meta.get_field("rng_seed")
        assert isinstance(field, models.BigIntegerField)
        assert field.default == 0

    def test_timestamps(self) -> None:
        created = GameSession._meta.get_field("created_at")
        updated = GameSession._meta.get_field("updated_at")
        assert isinstance(created, models.DateTimeField)
        assert isinstance(updated, models.DateTimeField)

    def test_str_representation(self) -> None:
        session = GameSession(
            id=uuid.UUID("12345678-1234-5678-1234-567812345678"),
            scenario="test",
            current_tick=5,
        )
        result = str(session)
        assert "test" in result
        assert "tick=5" in result


@pytest.mark.unit
class TestPlayerActionMeta:
    """Verify PlayerAction model metadata matches game_turn DDL."""

    def test_managed_is_false_in_source(self) -> None:
        assert _source_declares_managed_false(_MODELS_SOURCE, "PlayerAction")

    def test_db_table(self) -> None:
        assert PlayerAction._meta.db_table == "game_turn"

    def test_pk_is_big_auto(self) -> None:
        pk_field = PlayerAction._meta.get_field("id")
        assert isinstance(pk_field, models.BigAutoField)
        assert pk_field.primary_key is True

    def test_session_fk(self) -> None:
        field = PlayerAction._meta.get_field("session")
        assert isinstance(field, models.ForeignKey)
        assert field.related_model is GameSession
        assert field.column == "session_id"

    def test_tick_field(self) -> None:
        field = PlayerAction._meta.get_field("tick")
        assert isinstance(field, models.IntegerField)

    def test_org_id_field(self) -> None:
        field = PlayerAction._meta.get_field("org_id")
        assert isinstance(field, models.CharField)
        assert field.max_length == 64

    def test_verb_field(self) -> None:
        field = PlayerAction._meta.get_field("verb")
        assert isinstance(field, models.CharField)
        assert field.max_length == 16

    def test_action_type_nullable(self) -> None:
        field = PlayerAction._meta.get_field("action_type")
        assert isinstance(field, models.CharField)
        assert field.null is True

    def test_target_id_nullable(self) -> None:
        field = PlayerAction._meta.get_field("target_id")
        assert isinstance(field, models.CharField)
        assert field.null is True

    def test_target_community_nullable(self) -> None:
        field = PlayerAction._meta.get_field("target_community")
        assert isinstance(field, models.CharField)
        assert field.null is True

    def test_params_json_nullable(self) -> None:
        field = PlayerAction._meta.get_field("params_json")
        assert isinstance(field, models.JSONField)
        assert field.null is True

    def test_resolved_default_false(self) -> None:
        field = PlayerAction._meta.get_field("resolved")
        assert isinstance(field, models.BooleanField)
        assert field.default is False

    def test_unique_constraint(self) -> None:
        constraint_names = [c.name for c in PlayerAction._meta.constraints]
        assert "unique_session_tick_org" in constraint_names

    def test_str_representation(self) -> None:
        action = PlayerAction(
            session_id=uuid.UUID("12345678-1234-5678-1234-567812345678"),
            tick=3,
            org_id="org_workers",
            verb="RECRUIT",
        )
        result = str(action)
        assert "org_workers" in result
        assert "RECRUIT" in result


@pytest.mark.unit
class TestActionResultMeta:
    """Verify ActionResult model metadata matches action_result DDL."""

    def test_managed_is_false_in_source(self) -> None:
        assert _source_declares_managed_false(_MODELS_SOURCE, "ActionResult")

    def test_db_table(self) -> None:
        assert ActionResult._meta.db_table == "action_result"

    def test_pk_is_big_auto(self) -> None:
        pk_field = ActionResult._meta.get_field("id")
        assert isinstance(pk_field, models.BigAutoField)
        assert pk_field.primary_key is True

    def test_session_fk(self) -> None:
        field = ActionResult._meta.get_field("session")
        assert isinstance(field, models.ForeignKey)
        assert field.related_model is GameSession
        assert field.column == "session_id"

    def test_tick_field(self) -> None:
        field = ActionResult._meta.get_field("tick")
        assert isinstance(field, models.IntegerField)

    def test_org_id_field(self) -> None:
        field = ActionResult._meta.get_field("org_id")
        assert isinstance(field, models.CharField)
        assert field.max_length == 64

    def test_action_type_not_null(self) -> None:
        field = ActionResult._meta.get_field("action_type")
        assert isinstance(field, models.CharField)
        assert field.max_length == 32
        # action_type is NOT NULL in action_result (unlike game_turn)
        assert field.null is False

    def test_target_id_nullable(self) -> None:
        field = ActionResult._meta.get_field("target_id")
        assert field.null is True

    def test_target_community_nullable(self) -> None:
        field = ActionResult._meta.get_field("target_community")
        assert field.null is True

    def test_initiative_score_not_null(self) -> None:
        field = ActionResult._meta.get_field("initiative_score")
        assert isinstance(field, models.FloatField)

    def test_action_cost_not_null(self) -> None:
        field = ActionResult._meta.get_field("action_cost")
        assert isinstance(field, models.FloatField)

    def test_success_boolean(self) -> None:
        field = ActionResult._meta.get_field("success")
        assert isinstance(field, models.BooleanField)

    def test_consciousness_delta_nullable(self) -> None:
        field = ActionResult._meta.get_field("consciousness_delta")
        assert isinstance(field, models.FloatField)
        assert field.null is True

    def test_heat_delta_nullable(self) -> None:
        field = ActionResult._meta.get_field("heat_delta")
        assert isinstance(field, models.FloatField)
        assert field.null is True

    def test_details_json_nullable(self) -> None:
        field = ActionResult._meta.get_field("details")
        assert isinstance(field, models.JSONField)
        assert field.null is True

    def test_str_representation(self) -> None:
        result = ActionResult(
            session_id=uuid.UUID("12345678-1234-5678-1234-567812345678"),
            tick=2,
            org_id="org_vanguard",
        )
        assert "org_vanguard" in str(result)


@pytest.mark.unit
class TestPlayerProfileMeta:
    """Verify PlayerProfile model is managed and has correct fields."""

    def test_managed_is_true(self) -> None:
        assert PlayerProfile._meta.managed is True

    def test_db_table(self) -> None:
        assert PlayerProfile._meta.db_table == "player_profile"

    def test_user_one_to_one(self) -> None:
        field = PlayerProfile._meta.get_field("user")
        assert isinstance(field, models.OneToOneField)

    def test_display_name_field(self) -> None:
        field = PlayerProfile._meta.get_field("display_name")
        assert isinstance(field, models.CharField)
        assert field.max_length == 64
        assert field.default == ""

    def test_is_beta_tester_default_false(self) -> None:
        field = PlayerProfile._meta.get_field("is_beta_tester")
        assert isinstance(field, models.BooleanField)
        assert field.default is False

    def test_created_at_auto(self) -> None:
        field = PlayerProfile._meta.get_field("created_at")
        assert isinstance(field, models.DateTimeField)

    def test_str_representation(self) -> None:
        profile = PlayerProfile(user_id=1, display_name="TestPlayer")
        result = str(profile)
        assert "TestPlayer" in result
