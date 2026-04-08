import json
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from game.models import GameSession, HexState


class Command(BaseCommand):
    help = "Seeds sim.hex_states from the mock fixture for a given GameSession."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("game_id", type=str, help="UUID of the GameSession")
        parser.add_argument(
            "--fixture",
            type=str,
            default="frontend/src/fixtures/mock_map_data.json",
            help="Path to the mock fixture JSON file relative to web directory",
        )

    @transaction.atomic
    def handle(self, *args: Any, **options: Any) -> None:  # noqa: ARG002
        game_id = options["game_id"]
        fixture_path_str = options["fixture"]

        try:
            session = GameSession.objects.get(pk=game_id)
        except GameSession.DoesNotExist as e:
            raise CommandError(f'GameSession "{game_id}" does not exist.') from e

        fixture_path = Path("web") / fixture_path_str
        if not fixture_path.exists():
            # Try from root or absolute if the relative one fails
            fixture_path = Path(fixture_path_str)
            if not fixture_path.exists():
                raise CommandError(f'Fixture file "{fixture_path_str}" does not exist.')

        try:
            with open(fixture_path) as f:
                data = json.load(f)
        except Exception as e:
            raise CommandError(f"Failed to read fixture: {e}") from e

        tick = data.get("metadata", {}).get("tick", 0)

        records_to_create = []
        for feature in data.get("features", []):
            props = feature.get("properties", {})
            records_to_create.append(
                HexState(
                    game=session,
                    tick=tick,
                    h3_index=props.get("h3_index"),
                    county_fips=props.get("county_fips"),
                    county_name=props.get("county_name"),
                    profit_rate=props.get("profit_rate"),
                    exploitation_rate=props.get("exploitation_rate"),
                    occ=props.get("occ"),
                    imperial_rent=props.get("imperial_rent"),
                    heat=props.get("heat"),
                    org_presence=props.get("org_presence", 0),
                    dominant_class=props.get("dominant_class"),
                    population=props.get("population"),
                )
            )

        if records_to_create:
            # Clear existing to enforce the unique constraint or just allow IntegrityError
            # based on user intent. We'll simply use bulk_create and if uniqueness is violated it throws IntegrityError,
            # which is what test_unique_constraint expects.
            HexState.objects.bulk_create(records_to_create)

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully seeded {len(records_to_create)} hexes for game {game_id} at tick {tick}."
            )
        )
