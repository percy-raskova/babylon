"""Repository layer bridging Django ORM ↔ Pydantic Dialectic models.

Handles serialization (Pydantic → Django) and deserialization
(Django → Pydantic) of Dialectic and Morphism instances for the v2
engine's tick-keyed JSONB persistence.

Usage::

    from web.game.repositories import DialecticRepository

    repo = DialecticRepository()

    # Save a World snapshot
    repo.save_world(game_session, world)

    # Load the latest World for a game
    world = repo.load_world(game_session)

See Also:
    :class:`web.game.models.DialecticSnapshot`
    :class:`web.game.models.MorphismSnapshot`
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from babylon.engine.dialectics.registry import default_registry
from babylon.engine.dialectics.world import Morphism, World

from .models import DialecticSnapshot, GameSession, MorphismSnapshot


class DialecticRepository:
    """Bridges Django ORM and the v2 Pydantic dialectic models.

    Serialization: ``Dialectic.model_dump()`` → ``state_json`` JSONB
    Deserialization: ``type_tag`` lookup via registry → ``Class(**state_json)``
    """

    def save_world(self, session: GameSession, world: World) -> int:
        """Persist a World snapshot to Django-managed tables.

        Creates one ``DialecticSnapshot`` row per dialectic and one
        ``MorphismSnapshot`` row per morphism, all keyed by tick.

        Args:
            session: The GameSession foreign key.
            world: The World state to persist.

        Returns:
            Number of rows written (dialectics + morphisms).
        """
        rows_written = 0

        # Bulk-create dialectic snapshots
        dialectic_rows = [
            DialecticSnapshot(
                game=session,
                tick=world.tick,
                dialectic_id=d.id,
                type_tag=d.type_tag,
                weight=d.weight,
                state_json=d.model_dump(mode="json"),
                parent_id=d.parent_id,
            )
            for d in world.dialectics.values()
        ]
        if dialectic_rows:
            DialecticSnapshot.objects.bulk_create(dialectic_rows, ignore_conflicts=True)
            rows_written += len(dialectic_rows)

        # Bulk-create morphism snapshots
        morphism_rows = [
            MorphismSnapshot(
                game=session,
                tick=world.tick,
                morphism_id=m.id,
                source_dialectic_id=m.source_id,
                target_dialectic_id=m.target_id,
                relation=m.relation,
                weight=m.weight,
                metadata_json=m.metadata,
            )
            for m in world.morphisms
        ]
        if morphism_rows:
            MorphismSnapshot.objects.bulk_create(morphism_rows, ignore_conflicts=True)
            rows_written += len(morphism_rows)

        return rows_written

    def load_world(self, session: GameSession, tick: int | None = None) -> World:
        """Load a World from the latest (or specified) tick.

        Deserializes dialectics from JSONB via the type registry,
        and reconstructs morphisms.

        Args:
            session: The GameSession to load from.
            tick: Specific tick to load. None = latest.

        Returns:
            Reconstructed World instance.
        """
        # Determine tick
        if tick is None:
            latest = (
                DialecticSnapshot.objects.filter(game=session)
                .order_by("-tick")
                .values_list("tick", flat=True)
                .first()
            )
            if latest is None:
                return World(tick=0)
            tick = latest

        # Load dialectics
        dialect_rows = DialecticSnapshot.objects.filter(game=session, tick=tick)
        dialectics: dict[UUID, Any] = {}
        for row in dialect_rows:
            cls = default_registry.lookup(row.type_tag)
            dialectic = cls.model_validate(row.state_json)
            dialectics[dialectic.id] = dialectic

        # Load morphisms
        morph_rows: Any = MorphismSnapshot.objects.filter(game=session, tick=tick)
        morphisms: list[Morphism] = []
        for morph_row in morph_rows:
            morphisms.append(
                Morphism(
                    id=morph_row.morphism_id,
                    source_id=morph_row.source_dialectic_id,
                    target_id=morph_row.target_dialectic_id,
                    relation=morph_row.relation,
                    weight=morph_row.weight,
                    metadata=morph_row.metadata_json or {},
                )
            )

        return World(
            tick=tick,
            dialectics=dialectics,
            morphisms=morphisms,
        )

    def load_dialectic_history(
        self,
        session: GameSession,
        dialectic_id: UUID,
    ) -> list[dict[str, Any]]:
        """Load the time-series of a specific dialectic's snapshots.

        Args:
            session: The GameSession to query.
            dialectic_id: UUID of the dialectic to trace.

        Returns:
            List of dicts with tick, weight, state_json, type_tag.
        """
        rows: Any = (
            DialecticSnapshot.objects.filter(game=session, dialectic_id=dialectic_id)
            .order_by("tick")
            .values("tick", "weight", "type_tag", "state_json", "parent_id")
        )
        return list(rows)
