"""Django ORM models wrapping Feature 037 PostgreSQL tables.

These models use ``managed = False`` because Feature 037's
``postgres_schema.py`` owns the DDL via raw SQL. Django provides
queryable ORM access without controlling schema migrations.

Column names and types match the DDL in
``src/babylon/persistence/postgres_schema.py`` exactly.
"""

from __future__ import annotations

import uuid

from django.db import models


class GameSession(models.Model):
    """Wraps the ``game_session`` table (Feature 037).

    UUID primary key, stores session config and game state metadata.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    player_id = models.IntegerField(null=True, blank=True)
    scenario = models.CharField(max_length=64)
    current_tick = models.IntegerField(default=0)
    status = models.CharField(max_length=16, default="active")
    config_json = models.JSONField(default=dict)
    game_defines_json = models.JSONField(default=dict)
    trace_level = models.CharField(max_length=8, default="NONE")
    rng_seed = models.BigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = "game_session"

    def __str__(self) -> str:
        return f"GameSession({self.id}, {self.scenario}, tick={self.current_tick})"


class PlayerAction(models.Model):
    """Wraps the ``game_turn`` table (Feature 037).

    Represents a player or NPC action submission for a given tick.
    One turn per org per tick (enforced by DB unique constraint).
    """

    id = models.BigAutoField(primary_key=True)
    session = models.ForeignKey(
        GameSession,
        on_delete=models.CASCADE,
        db_column="session_id",
    )
    tick = models.IntegerField()
    org_id = models.CharField(max_length=64)
    verb = models.CharField(max_length=16)
    action_type = models.CharField(max_length=32, null=True, blank=True)
    target_id = models.CharField(max_length=64, null=True, blank=True)
    target_community = models.CharField(max_length=32, null=True, blank=True)
    params_json = models.JSONField(null=True, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    resolved = models.BooleanField(default=False)

    class Meta:
        managed = False
        db_table = "game_turn"
        constraints = [
            models.UniqueConstraint(
                fields=["session", "tick", "org_id"],
                name="unique_session_tick_org",
            ),
        ]

    def __str__(self) -> str:
        return f"PlayerAction({self.session_id}, tick={self.tick}, {self.org_id}:{self.verb})"


class GameEventLog(models.Model):
    """Audit log for significant game events, stored in PostgreSQL.

    Unlike ``game_session`` and ``game_turn`` (managed=False, owned by
    Feature 037), this table is managed by Django migrations. It captures
    API-level events (game creation, tick resolution, errors) for
    operational visibility and debugging.
    """

    class EventCategory(models.TextChoices):
        GAME_CREATE = "game_create", "Game Created"
        GAME_PAUSE = "game_pause", "Game Paused"
        GAME_RESUME = "game_resume", "Game Resumed"
        TICK_RESOLVE = "tick_resolve", "Tick Resolved"
        ACTION_SUBMIT = "action_submit", "Action Submitted"
        ENGINE_ERROR = "engine_error", "Engine Error"
        AUTH_LOGIN = "auth_login", "User Login"
        AUTH_LOGOUT = "auth_logout", "User Logout"
        AUTH_FAIL = "auth_fail", "Login Failed"

    id = models.BigAutoField(primary_key=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    category = models.CharField(max_length=32, choices=EventCategory.choices, db_index=True)
    session_id = models.UUIDField(null=True, blank=True, db_index=True)
    user_id = models.IntegerField(null=True, blank=True, db_index=True)
    tick = models.IntegerField(null=True, blank=True)
    message = models.TextField()
    details = models.JSONField(null=True, blank=True)
    correlation_id = models.CharField(max_length=64, null=True, blank=True)

    class Meta:
        db_table = "game_event_log"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["session_id", "tick"], name="idx_event_session_tick"),
        ]

    def __str__(self) -> str:
        return f"GameEventLog({self.category}, {self.timestamp})"


class ActionResult(models.Model):
    """Wraps the ``action_result`` table (Feature 037).

    Outcome record produced after the engine resolves a tick.
    """

    id = models.BigAutoField(primary_key=True)
    session = models.ForeignKey(
        GameSession,
        on_delete=models.CASCADE,
        db_column="session_id",
    )
    tick = models.IntegerField()
    org_id = models.CharField(max_length=64)
    action_type = models.CharField(max_length=32)
    target_id = models.CharField(max_length=64, null=True, blank=True)
    target_community = models.CharField(max_length=32, null=True, blank=True)
    initiative_score = models.FloatField()
    action_cost = models.FloatField()
    success = models.BooleanField()
    consciousness_delta = models.FloatField(null=True, blank=True)
    heat_delta = models.FloatField(null=True, blank=True)
    details = models.JSONField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = "action_result"

    def __str__(self) -> str:
        return f"ActionResult({self.session_id}, tick={self.tick}, {self.org_id})"
