import pytest
from django.core.management import call_command
from django.db.utils import IntegrityError

from game.models import GameSession, HexState


@pytest.fixture
def test_game(db):
    game = GameSession.objects.create(scenario="detroit_test")
    return game


@pytest.mark.django_db
def test_seed_command_populates(test_game):
    """Running seed_hex_data creates rows matching fixture count."""
    call_command(
        "seed_hex_data", str(test_game.id), fixture="web/frontend/src/fixtures/mock_map_data.json"
    )
    count = HexState.objects.filter(game=test_game).count()
    # At least we generated 50 hexes, let's just make sure it's 50
    assert count == 50


@pytest.mark.django_db
def test_unique_constraint(test_game):
    """Duplicate (game_id, tick, h3_index) raises IntegrityError."""
    HexState.objects.create(
        game=test_game, tick=0, h3_index="872b5912affffff", county_fips="26163", county_name="Wayne"
    )

    with pytest.raises(IntegrityError):
        HexState.objects.create(
            game=test_game,
            tick=0,
            h3_index="872b5912affffff",
            county_fips="26163",
            county_name="Wayne",
        )


@pytest.mark.django_db
def test_county_fips_values(test_game):
    """All rows have county_fips in {26163, 26125, 26099}."""
    call_command(
        "seed_hex_data", str(test_game.id), fixture="web/frontend/src/fixtures/mock_map_data.json"
    )

    invalid_fips = HexState.objects.filter(game=test_game).exclude(
        county_fips__in=["26163", "26125", "26099"]
    )
    assert invalid_fips.count() == 0
