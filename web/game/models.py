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


class HexState(models.Model):
    """Per-hex current state — denormalized R7 cache for map rendering.

    Wraps ``hex_latest``. County economics are broadcast from
    ``territory_snapshot``; hex-specific data (heat, org) comes
    from ``hex_activity``. Updated server-side via SQL UPSERT
    after each tick.
    """

    game = models.ForeignKey(
        GameSession,
        on_delete=models.CASCADE,
        db_column="game_id",
    )
    h3_index = models.CharField(max_length=16)
    tick = models.IntegerField()

    # Denormalized county economics
    county_fips = models.CharField(max_length=5)
    county_name = models.CharField(max_length=100)
    bea_ea_code = models.CharField(max_length=8, null=True, blank=True)
    msa_code = models.CharField(max_length=10, null=True, blank=True)
    state_fips = models.CharField(max_length=2, default="26")
    center_lat = models.FloatField()
    center_lng = models.FloatField()

    # Derived Marxian indicators
    profit_rate = models.FloatField(null=True, blank=True)
    exploitation_rate = models.FloatField(null=True, blank=True)
    occ = models.FloatField(null=True, blank=True)
    imperial_rent = models.FloatField(null=True, blank=True)
    g33_visibility = models.FloatField(null=True, blank=True)

    # Class distribution
    pop_bourgeoisie = models.IntegerField(default=0)
    pop_petit_bourgeoisie = models.IntegerField(default=0)
    pop_labor_aristocracy = models.IntegerField(default=0)
    pop_proletariat = models.IntegerField(default=0)
    pop_lumpenproletariat = models.IntegerField(default=0)
    pop_total = models.IntegerField(default=0)
    dominant_class = models.CharField(max_length=24, null=True, blank=True)

    # Faction balance
    faction_finance_capital = models.FloatField(null=True, blank=True)
    faction_security_state = models.FloatField(null=True, blank=True)
    faction_settler_populist = models.FloatField(null=True, blank=True)

    # Hex-specific fields
    heat = models.FloatField(default=0.0)
    heat_delta = models.FloatField(default=0.0)
    org_count = models.SmallIntegerField(default=0)
    actions_taken = models.SmallIntegerField(default=0)
    was_target = models.BooleanField(default=False)

    # Aggregated R8 terrain
    terrain_type = models.CharField(max_length=16, default="LAND")
    water_coverage = models.FloatField(default=0.0)
    internet_access = models.BooleanField(default=False)

    class Meta:
        managed = False
        db_table = "hex_latest"
        constraints = [
            models.UniqueConstraint(
                fields=["game", "h3_index"],
                name="unique_hex_latest_pk",
            ),
        ]

    def __str__(self) -> str:
        return f"HexState({self.game_id}, tick={self.tick}, {self.h3_index})"


# ═══════════════════════════════════════════════════════════════════════
# Spec 037: Game-Journal Unmanaged Models
# ═══════════════════════════════════════════════════════════════════════


class TerritorySnapshot(models.Model):
    """Per-county economic state per tick (append-only).

    Wraps ``territory_snapshot`` — the primary county-level time-series
    table written by the engine once per tick.
    """

    game = models.ForeignKey(
        GameSession,
        on_delete=models.CASCADE,
        db_column="game_id",
    )
    tick = models.IntegerField()
    county_fips = models.CharField(max_length=5)

    # ValueTensor4x3 (Departments I/IIa/IIb/III × c/v/s)
    c_dept_i = models.DecimalField(max_digits=18, decimal_places=4, null=True)
    v_dept_i = models.DecimalField(max_digits=18, decimal_places=4, null=True)
    s_dept_i = models.DecimalField(max_digits=18, decimal_places=4, null=True)
    c_dept_iia = models.DecimalField(max_digits=18, decimal_places=4, null=True)
    v_dept_iia = models.DecimalField(max_digits=18, decimal_places=4, null=True)
    s_dept_iia = models.DecimalField(max_digits=18, decimal_places=4, null=True)
    c_dept_iib = models.DecimalField(max_digits=18, decimal_places=4, null=True)
    v_dept_iib = models.DecimalField(max_digits=18, decimal_places=4, null=True)
    s_dept_iib = models.DecimalField(max_digits=18, decimal_places=4, null=True)
    c_dept_iii = models.DecimalField(max_digits=18, decimal_places=4, null=True)
    v_dept_iii = models.DecimalField(max_digits=18, decimal_places=4, null=True)
    s_dept_iii = models.DecimalField(max_digits=18, decimal_places=4, null=True)

    # Derived indicators
    profit_rate = models.FloatField(null=True)
    exploitation_rate = models.FloatField(null=True)
    occ = models.FloatField(null=True)
    imperial_rent = models.DecimalField(max_digits=18, decimal_places=4, null=True)
    g33_visibility = models.FloatField(null=True)

    # Class distribution
    pop_bourgeoisie = models.IntegerField(default=0)
    pop_petit_bourgeoisie = models.IntegerField(default=0)
    pop_labor_aristocracy = models.IntegerField(default=0)
    pop_proletariat = models.IntegerField(default=0)
    pop_lumpenproletariat = models.IntegerField(default=0)
    pop_total = models.IntegerField(default=0)

    # Faction balance
    faction_finance_capital = models.FloatField(null=True)
    faction_security_state = models.FloatField(null=True)
    faction_settler_populist = models.FloatField(null=True)

    heat = models.FloatField(default=0.0)
    attributes = models.JSONField(default=dict)

    class Meta:
        managed = False
        db_table = "territory_snapshot"
        constraints = [
            models.UniqueConstraint(
                fields=["game", "tick", "county_fips"],
                name="uq_territory_snapshot",
            ),
        ]

    def __str__(self) -> str:
        return f"TerritorySnapshot({self.game_id}, t={self.tick}, {self.county_fips})"


class OrgSnapshot(models.Model):
    """Organization state per tick (append-only).

    Wraps ``org_snapshot``.
    """

    game = models.ForeignKey(
        GameSession,
        on_delete=models.CASCADE,
        db_column="game_id",
    )
    tick = models.IntegerField()
    org_id = models.CharField(max_length=64)
    org_type = models.CharField(max_length=24)
    home_county = models.CharField(max_length=5, null=True, blank=True)
    home_hex = models.CharField(max_length=16, null=True, blank=True)

    # OODA state
    ooda_phase = models.CharField(max_length=8, null=True, blank=True)
    action_points = models.IntegerField(null=True)
    action_points_max = models.IntegerField(null=True)

    # Resources
    cadre_count = models.IntegerField(default=0)
    sympathizer_count = models.IntegerField(default=0)
    cadre_labor = models.FloatField(default=0.0)
    sympathizer_labor = models.FloatField(default=0.0)
    material_resources = models.FloatField(default=0.0)

    # Health
    coherence = models.FloatField(null=True)
    reputation = models.FloatField(null=True)
    opsec = models.FloatField(null=True)

    # Ownership
    owner_type = models.CharField(max_length=16, null=True, blank=True)
    owner_id = models.CharField(max_length=64, null=True, blank=True)

    attributes = models.JSONField(default=dict)

    class Meta:
        managed = False
        db_table = "org_snapshot"
        constraints = [
            models.UniqueConstraint(
                fields=["game", "tick", "org_id"],
                name="uq_org_snapshot",
            ),
        ]

    def __str__(self) -> str:
        return f"OrgSnapshot({self.game_id}, t={self.tick}, {self.org_id})"


class EdgeSnapshot(models.Model):
    """Graph edge state per tick (append-only).

    Wraps ``edge_snapshot``.
    """

    game = models.ForeignKey(
        GameSession,
        on_delete=models.CASCADE,
        db_column="game_id",
    )
    tick = models.IntegerField()
    source_id = models.CharField(max_length=64)
    target_id = models.CharField(max_length=64)
    edge_type = models.CharField(max_length=32)
    edge_mode = models.CharField(max_length=16, null=True, blank=True)
    value_flow = models.DecimalField(max_digits=18, decimal_places=4, null=True)
    solidarity = models.FloatField(null=True)
    tension = models.FloatField(null=True)
    attributes = models.JSONField(default=dict)

    class Meta:
        managed = False
        db_table = "edge_snapshot"
        constraints = [
            models.UniqueConstraint(
                fields=["game", "tick", "source_id", "target_id", "edge_type"],
                name="uq_edge_snapshot",
            ),
        ]

    def __str__(self) -> str:
        return f"EdgeSnapshot({self.game_id}, t={self.tick}, {self.source_id}->{self.target_id})"


class CommunitySnapshot(models.Model):
    """Community hyperedge state per tick (append-only).

    Wraps ``community_snapshot``.
    """

    game = models.ForeignKey(
        GameSession,
        on_delete=models.CASCADE,
        db_column="game_id",
    )
    tick = models.IntegerField()
    community_id = models.CharField(max_length=64)
    community_type = models.CharField(max_length=32)
    hyperedge_category = models.CharField(max_length=24)
    contradiction_axis = models.CharField(max_length=24, null=True, blank=True)
    county_fips = models.CharField(max_length=5, null=True, blank=True)

    collective_identity = models.FloatField(null=True)
    ideological_contestation = models.FloatField(null=True)
    dominant_tendency = models.CharField(max_length=28, null=True, blank=True)

    reproduction_cost_modifier = models.FloatField(null=True)
    rent_access_modifier = models.FloatField(null=True)
    member_count = models.IntegerField(null=True)

    attributes = models.JSONField(default=dict)

    class Meta:
        managed = False
        db_table = "community_snapshot"
        constraints = [
            models.UniqueConstraint(
                fields=["game", "tick", "community_id"],
                name="uq_community_snapshot",
            ),
        ]

    def __str__(self) -> str:
        return f"CommunitySnapshot({self.game_id}, t={self.tick}, {self.community_id})"


class EconomicSummary(models.Model):
    """Game-level economic aggregates per tick (append-only).

    Wraps ``economic_summary``.
    """

    game = models.ForeignKey(
        GameSession,
        on_delete=models.CASCADE,
        db_column="game_id",
    )
    tick = models.IntegerField()

    avg_profit_rate = models.FloatField(null=True)
    avg_exploitation_rate = models.FloatField(null=True)
    avg_occ = models.FloatField(null=True)
    total_imperial_rent = models.DecimalField(max_digits=18, decimal_places=4, null=True)
    avg_g33_visibility = models.FloatField(null=True)

    total_bourgeoisie = models.IntegerField(null=True)
    total_petit_bourgeoisie = models.IntegerField(null=True)
    total_labor_aristocracy = models.IntegerField(null=True)
    total_proletariat = models.IntegerField(null=True)
    total_lumpenproletariat = models.IntegerField(null=True)
    total_population = models.IntegerField(null=True)

    avg_faction_finance = models.FloatField(null=True)
    avg_faction_security = models.FloatField(null=True)
    avg_faction_settler = models.FloatField(null=True)

    total_heat = models.FloatField(null=True)
    total_orgs = models.IntegerField(null=True)
    total_player_orgs = models.IntegerField(null=True)
    total_solidaristic_edges = models.IntegerField(null=True)
    total_antagonistic_edges = models.IntegerField(null=True)

    percolation_ratio = models.FloatField(null=True)
    fascist_convergence = models.BooleanField(default=False)

    narrative_text = models.TextField(null=True, blank=True)
    attributes = models.JSONField(null=True)

    class Meta:
        managed = False
        db_table = "economic_summary"
        constraints = [
            models.UniqueConstraint(
                fields=["game", "tick"],
                name="uq_economic_summary",
            ),
        ]

    def __str__(self) -> str:
        return f"EconomicSummary({self.game_id}, t={self.tick})"


class TickEvent(models.Model):
    """Simulation event log per tick (append-only).

    Wraps ``tick_event``.
    """

    game = models.ForeignKey(
        GameSession,
        on_delete=models.CASCADE,
        db_column="game_id",
    )
    tick = models.IntegerField()
    event_id = models.AutoField(primary_key=True)
    event_type = models.CharField(max_length=48)
    severity = models.CharField(max_length=12, null=True, blank=True)
    source_id = models.CharField(max_length=64, null=True, blank=True)
    target_id = models.CharField(max_length=64, null=True, blank=True)
    county_fips = models.CharField(max_length=5, null=True, blank=True)
    h3_index = models.CharField(max_length=16, null=True, blank=True)
    summary = models.TextField()
    detail = models.JSONField(null=True)

    class Meta:
        managed = False
        db_table = "tick_event"

    def __str__(self) -> str:
        return f"TickEvent({self.game_id}, t={self.tick}, {self.event_type})"


# ═══════════════════════════════════════════════════════════════════════
# V2 Dialectic Engine — Tick-Keyed JSONB Snapshots
# ═══════════════════════════════════════════════════════════════════════


class DialecticSnapshot(models.Model):
    """Tick-keyed JSONB snapshot of a Dialectic instance.

    Stores the full serialized state of each Dialectic per tick,
    enabling time-travel queries and historical replay.

    Unlike the v1 snapshot tables (managed=False), this table is
    Django-managed to support the v2 migration strategy.
    """

    game = models.ForeignKey(
        GameSession,
        on_delete=models.CASCADE,
        db_column="game_id",
    )
    tick = models.IntegerField(db_index=True)
    dialectic_id = models.UUIDField(
        db_index=True,
        help_text="Maps to Dialectic.id from the engine.",
    )
    type_tag = models.CharField(
        max_length=64,
        db_index=True,
        help_text="Discriminator for Dialectic subclass.",
    )
    weight = models.FloatField()
    state_json = models.JSONField(help_text="Full serialized Dialectic via Pydantic model_dump().")
    parent_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="Predecessor dialectic if produced by sublation.",
    )

    class Meta:
        db_table = "dialectic_snapshot"
        ordering = ["tick"]
        constraints = [
            models.UniqueConstraint(
                fields=["game", "tick", "dialectic_id"],
                name="uq_dialectic_snapshot",
            ),
        ]

    def __str__(self) -> str:
        return f"DialecticSnapshot({self.game_id}, t={self.tick}, {self.type_tag})"


class MorphismSnapshot(models.Model):
    """Tick-keyed snapshot of a Morphism edge.

    Stores morphism wiring at each tick to track how the dialectical
    graph evolves over time.
    """

    game = models.ForeignKey(
        GameSession,
        on_delete=models.CASCADE,
        db_column="game_id",
    )
    tick = models.IntegerField(db_index=True)
    morphism_id = models.UUIDField(db_index=True)
    source_dialectic_id = models.UUIDField()
    target_dialectic_id = models.UUIDField()
    relation = models.CharField(max_length=32)
    weight = models.FloatField(default=1.0)
    metadata_json = models.JSONField(default=dict)

    class Meta:
        db_table = "morphism_snapshot"
        ordering = ["tick"]
        constraints = [
            models.UniqueConstraint(
                fields=["game", "tick", "morphism_id"],
                name="uq_morphism_snapshot",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"MorphismSnapshot({self.game_id}, t={self.tick}, "
            f"{self.source_dialectic_id}->{self.target_dialectic_id})"
        )
