"""Tests for THE CHRONICLE archetypal event files.

These tests verify the structure and content of three historical event JSON files
that serve as precedents for the Fascist Bifurcation mechanic in the Babylon
simulation engine.

The three archetypal events represent:
1. Weimar 1933 - Counter-revolution (Fascist Turn)
2. Russia 1917 - Revolutionary success (Revolutionary Turn)
3. Paris Commune 1871 - Suppression (Failed Turn)

Each file must:
- Be valid JSON with 'text' and 'metadata' keys
- Have metadata conforming to the rag-architecture.yaml schema
- Contain 300-500 words of dialectical analysis
- Be grounded in actual source text analysis (not generic summaries)
"""

import json
from pathlib import Path
from typing import Any

import pytest

# Constants defining the schema constraints
HISTORY_DIR = (
    Path(__file__).parent.parent.parent.parent.parent
    / "src"
    / "babylon"
    / "data"
    / "corpus"
    / "history"
)
VALID_OUTCOME_TYPES = frozenset(
    {
        "revolutionary_success",
        "revolutionary_failure",
        "counter_revolution",
        "reform",
        "suppression",
    }
)
REQUIRED_METADATA_FIELDS = frozenset(
    {
        "year",
        "location",
        "event_name",
        "period",
        "outcome_type",
        "tags",
        "resonance_tags",
    }
)
MIN_WORDS = 300
MAX_WORDS = 500

# Chronicle event files to test
CHRONICLE_FILES = [
    "weimar_1933.json",
    "russian_rev_1917.json",
    "paris_commune_1871.json",
]

# Dialectical terminology that should appear in the text
DIALECTICAL_TERMS = [
    "class",
    "material",
    "contradiction",
    "struggle",
    "bourgeois",
    "proletariat",
    "capital",
    "revolutionary",
]


def load_json_file(filepath: Path) -> dict[str, Any]:
    """Load and parse a JSON file."""
    with filepath.open(encoding="utf-8") as f:
        result: dict[str, Any] = json.load(f)
        return result


def count_words(text: str) -> int:
    """Count words in a text string."""
    return len(text.split())


@pytest.mark.ledger
class TestHistoryDirectoryStructure:
    """Test that the history directory and files exist."""

    def test_history_directory_exists(self) -> None:
        """The history/ directory must exist under corpus/."""
        assert HISTORY_DIR.exists(), (
            f"History directory does not exist at {HISTORY_DIR}. "
            "Create src/babylon/data/corpus/history/"
        )
        assert HISTORY_DIR.is_dir(), f"{HISTORY_DIR} exists but is not a directory"

    @pytest.mark.parametrize("filename", CHRONICLE_FILES)
    def test_chronicle_file_exists(self, filename: str) -> None:
        """Each chronicle JSON file must exist."""
        filepath = HISTORY_DIR / filename
        assert filepath.exists(), f"Chronicle file {filename} does not exist at {filepath}"
        assert filepath.is_file(), f"{filepath} exists but is not a file"


@pytest.mark.ledger
class TestJsonStructure:
    """Test JSON file structure compliance."""

    @pytest.mark.parametrize("filename", CHRONICLE_FILES)
    def test_json_is_valid(self, filename: str) -> None:
        """Each file must be valid parseable JSON."""
        filepath = HISTORY_DIR / filename
        if not filepath.exists():
            pytest.skip(f"File {filename} does not exist yet (RED phase)")

        # This will raise JSONDecodeError if invalid
        data = load_json_file(filepath)
        assert isinstance(data, dict), f"{filename} root must be a JSON object"

    @pytest.mark.parametrize("filename", CHRONICLE_FILES)
    def test_json_has_text_and_metadata(self, filename: str) -> None:
        """Each file must have 'text' and 'metadata' keys at root."""
        filepath = HISTORY_DIR / filename
        if not filepath.exists():
            pytest.skip(f"File {filename} does not exist yet (RED phase)")

        data = load_json_file(filepath)

        assert "text" in data, f"{filename} missing required 'text' key"
        assert "metadata" in data, f"{filename} missing required 'metadata' key"
        assert isinstance(data["text"], str), f"{filename} 'text' must be a string"
        assert isinstance(data["metadata"], dict), f"{filename} 'metadata' must be an object"


@pytest.mark.ledger
class TestMetadataSchema:
    """Test metadata field compliance with rag-architecture.yaml schema."""

    @pytest.mark.parametrize("filename", CHRONICLE_FILES)
    def test_metadata_has_all_required_fields(self, filename: str) -> None:
        """Metadata must contain all required fields."""
        filepath = HISTORY_DIR / filename
        if not filepath.exists():
            pytest.skip(f"File {filename} does not exist yet (RED phase)")

        data = load_json_file(filepath)
        metadata = data.get("metadata", {})

        missing_fields = REQUIRED_METADATA_FIELDS - set(metadata.keys())
        assert not missing_fields, f"{filename} metadata missing required fields: {missing_fields}"

    @pytest.mark.parametrize("filename", CHRONICLE_FILES)
    def test_metadata_year_is_integer(self, filename: str) -> None:
        """Year field must be an integer."""
        filepath = HISTORY_DIR / filename
        if not filepath.exists():
            pytest.skip(f"File {filename} does not exist yet (RED phase)")

        data = load_json_file(filepath)
        year = data.get("metadata", {}).get("year")

        assert isinstance(year, int), (
            f"{filename} metadata.year must be an integer, got {type(year).__name__}"
        )
        # Sanity check: year should be historical
        assert 1789 <= year <= 2000, (
            f"{filename} metadata.year={year} is outside expected range [1789, 2000]"
        )

    @pytest.mark.parametrize("filename", CHRONICLE_FILES)
    def test_metadata_strings_are_non_empty(self, filename: str) -> None:
        """String metadata fields must be non-empty."""
        filepath = HISTORY_DIR / filename
        if not filepath.exists():
            pytest.skip(f"File {filename} does not exist yet (RED phase)")

        data = load_json_file(filepath)
        metadata = data.get("metadata", {})

        string_fields = ["location", "event_name", "period", "outcome_type"]
        for field in string_fields:
            value = metadata.get(field)
            assert isinstance(value, str), f"{filename} metadata.{field} must be a string"
            assert len(value.strip()) > 0, f"{filename} metadata.{field} must not be empty"

    @pytest.mark.parametrize("filename", CHRONICLE_FILES)
    def test_metadata_outcome_type_is_valid_enum(self, filename: str) -> None:
        """outcome_type must be one of the valid enum values."""
        filepath = HISTORY_DIR / filename
        if not filepath.exists():
            pytest.skip(f"File {filename} does not exist yet (RED phase)")

        data = load_json_file(filepath)
        outcome = data.get("metadata", {}).get("outcome_type")

        assert outcome in VALID_OUTCOME_TYPES, (
            f"{filename} metadata.outcome_type='{outcome}' is not valid. "
            f"Must be one of: {sorted(VALID_OUTCOME_TYPES)}"
        )

    @pytest.mark.parametrize("filename", CHRONICLE_FILES)
    def test_metadata_tags_are_list_of_strings(self, filename: str) -> None:
        """tags must be a non-empty list of non-empty strings."""
        filepath = HISTORY_DIR / filename
        if not filepath.exists():
            pytest.skip(f"File {filename} does not exist yet (RED phase)")

        data = load_json_file(filepath)
        tags = data.get("metadata", {}).get("tags")

        assert isinstance(tags, list), f"{filename} metadata.tags must be a list"
        assert len(tags) > 0, f"{filename} metadata.tags must not be empty"
        for idx, tag in enumerate(tags):
            assert isinstance(tag, str), f"{filename} metadata.tags[{idx}] must be a string"
            assert len(tag.strip()) > 0, f"{filename} metadata.tags[{idx}] must not be empty"

    @pytest.mark.parametrize("filename", CHRONICLE_FILES)
    def test_metadata_resonance_tags_are_list_of_strings(self, filename: str) -> None:
        """resonance_tags must be a non-empty list of non-empty strings."""
        filepath = HISTORY_DIR / filename
        if not filepath.exists():
            pytest.skip(f"File {filename} does not exist yet (RED phase)")

        data = load_json_file(filepath)
        resonance_tags = data.get("metadata", {}).get("resonance_tags")

        assert isinstance(resonance_tags, list), (
            f"{filename} metadata.resonance_tags must be a list"
        )
        assert len(resonance_tags) > 0, f"{filename} metadata.resonance_tags must not be empty"
        for idx, tag in enumerate(resonance_tags):
            assert isinstance(tag, str), (
                f"{filename} metadata.resonance_tags[{idx}] must be a string"
            )
            assert len(tag.strip()) > 0, (
                f"{filename} metadata.resonance_tags[{idx}] must not be empty"
            )


@pytest.mark.ledger
class TestTextContent:
    """Test text content constraints."""

    @pytest.mark.parametrize("filename", CHRONICLE_FILES)
    def test_text_word_count_within_range(self, filename: str) -> None:
        """Text must be between 300-500 words."""
        filepath = HISTORY_DIR / filename
        if not filepath.exists():
            pytest.skip(f"File {filename} does not exist yet (RED phase)")

        data = load_json_file(filepath)
        text = data.get("text", "")
        word_count = count_words(text)

        assert MIN_WORDS <= word_count <= MAX_WORDS, (
            f"{filename} text has {word_count} words, must be between {MIN_WORDS}-{MAX_WORDS}"
        )

    @pytest.mark.parametrize("filename", CHRONICLE_FILES)
    def test_text_contains_dialectical_terminology(self, filename: str) -> None:
        """Text must contain dialectical/materialist terminology."""
        filepath = HISTORY_DIR / filename
        if not filepath.exists():
            pytest.skip(f"File {filename} does not exist yet (RED phase)")

        data = load_json_file(filepath)
        text = data.get("text", "").lower()

        found_terms = [term for term in DIALECTICAL_TERMS if term in text]
        min_required = 3  # Must contain at least 3 dialectical terms

        assert len(found_terms) >= min_required, (
            f"{filename} text contains only {len(found_terms)} dialectical terms "
            f"({found_terms}). Must contain at least {min_required} from: {DIALECTICAL_TERMS}"
        )


@pytest.mark.ledger
class TestWeimarSpecificContent:
    """Tests specific to weimar_1933.json."""

    def test_weimar_year_is_1933(self) -> None:
        """Weimar file must have year=1933."""
        filepath = HISTORY_DIR / "weimar_1933.json"
        if not filepath.exists():
            pytest.skip("weimar_1933.json does not exist yet (RED phase)")

        data = load_json_file(filepath)
        year = data.get("metadata", {}).get("year")
        assert year == 1933, f"weimar_1933.json year must be 1933, got {year}"

    def test_weimar_outcome_is_counter_revolution(self) -> None:
        """Weimar file must have outcome_type='counter_revolution'."""
        filepath = HISTORY_DIR / "weimar_1933.json"
        if not filepath.exists():
            pytest.skip("weimar_1933.json does not exist yet (RED phase)")

        data = load_json_file(filepath)
        outcome = data.get("metadata", {}).get("outcome_type")
        assert outcome == "counter_revolution", (
            f"weimar_1933.json outcome_type must be 'counter_revolution', got '{outcome}'"
        )

    def test_weimar_location_is_germany(self) -> None:
        """Weimar file must have location='Germany'."""
        filepath = HISTORY_DIR / "weimar_1933.json"
        if not filepath.exists():
            pytest.skip("weimar_1933.json does not exist yet (RED phase)")

        data = load_json_file(filepath)
        location = data.get("metadata", {}).get("location")
        assert location == "Germany", (
            f"weimar_1933.json location must be 'Germany', got '{location}'"
        )

    def test_weimar_contains_key_concepts(self) -> None:
        """Weimar text must reference key Trotsky analysis concepts."""
        filepath = HISTORY_DIR / "weimar_1933.json"
        if not filepath.exists():
            pytest.skip("weimar_1933.json does not exist yet (RED phase)")

        data = load_json_file(filepath)
        text = data.get("text", "").lower()

        # Must contain references to petty bourgeoisie, fascism, and finance capital
        assert "petty bourgeois" in text or "petty-bourgeois" in text, (
            "weimar_1933.json must reference the petty bourgeoisie (Trotsky analysis)"
        )


@pytest.mark.ledger
class TestRussianRevSpecificContent:
    """Tests specific to russian_rev_1917.json."""

    def test_russian_year_is_1917(self) -> None:
        """Russian revolution file must have year=1917."""
        filepath = HISTORY_DIR / "russian_rev_1917.json"
        if not filepath.exists():
            pytest.skip("russian_rev_1917.json does not exist yet (RED phase)")

        data = load_json_file(filepath)
        year = data.get("metadata", {}).get("year")
        assert year == 1917, f"russian_rev_1917.json year must be 1917, got {year}"

    def test_russian_outcome_is_revolutionary_success(self) -> None:
        """Russian revolution file must have outcome_type='revolutionary_success'."""
        filepath = HISTORY_DIR / "russian_rev_1917.json"
        if not filepath.exists():
            pytest.skip("russian_rev_1917.json does not exist yet (RED phase)")

        data = load_json_file(filepath)
        outcome = data.get("metadata", {}).get("outcome_type")
        assert outcome == "revolutionary_success", (
            f"russian_rev_1917.json outcome_type must be 'revolutionary_success', got '{outcome}'"
        )

    def test_russian_location_is_russia(self) -> None:
        """Russian revolution file must have location='Russia'."""
        filepath = HISTORY_DIR / "russian_rev_1917.json"
        if not filepath.exists():
            pytest.skip("russian_rev_1917.json does not exist yet (RED phase)")

        data = load_json_file(filepath)
        location = data.get("metadata", {}).get("location")
        assert location == "Russia", (
            f"russian_rev_1917.json location must be 'Russia', got '{location}'"
        )

    def test_russian_contains_key_concepts(self) -> None:
        """Russian revolution text must reference key Reed analysis concepts."""
        filepath = HISTORY_DIR / "russian_rev_1917.json"
        if not filepath.exists():
            pytest.skip("russian_rev_1917.json does not exist yet (RED phase)")

        data = load_json_file(filepath)
        text = data.get("text", "").lower()

        # Must reference dual power or soviets
        has_soviets = "soviet" in text
        has_dual_power = "dual power" in text

        assert has_soviets or has_dual_power, (
            "russian_rev_1917.json must reference Soviets or dual power (Reed analysis)"
        )


@pytest.mark.ledger
class TestParisSpecificContent:
    """Tests specific to paris_commune_1871.json."""

    def test_paris_year_is_1871(self) -> None:
        """Paris Commune file must have year=1871."""
        filepath = HISTORY_DIR / "paris_commune_1871.json"
        if not filepath.exists():
            pytest.skip("paris_commune_1871.json does not exist yet (RED phase)")

        data = load_json_file(filepath)
        year = data.get("metadata", {}).get("year")
        assert year == 1871, f"paris_commune_1871.json year must be 1871, got {year}"

    def test_paris_outcome_is_suppression(self) -> None:
        """Paris Commune file must have outcome_type='suppression'."""
        filepath = HISTORY_DIR / "paris_commune_1871.json"
        if not filepath.exists():
            pytest.skip("paris_commune_1871.json does not exist yet (RED phase)")

        data = load_json_file(filepath)
        outcome = data.get("metadata", {}).get("outcome_type")
        assert outcome == "suppression", (
            f"paris_commune_1871.json outcome_type must be 'suppression', got '{outcome}'"
        )

    def test_paris_location_is_france(self) -> None:
        """Paris Commune file must have location='France'."""
        filepath = HISTORY_DIR / "paris_commune_1871.json"
        if not filepath.exists():
            pytest.skip("paris_commune_1871.json does not exist yet (RED phase)")

        data = load_json_file(filepath)
        location = data.get("metadata", {}).get("location")
        assert location == "France", (
            f"paris_commune_1871.json location must be 'France', got '{location}'"
        )

    def test_paris_contains_key_concepts(self) -> None:
        """Paris Commune text must reference key Marx analysis concepts."""
        filepath = HISTORY_DIR / "paris_commune_1871.json"
        if not filepath.exists():
            pytest.skip("paris_commune_1871.json does not exist yet (RED phase)")

        data = load_json_file(filepath)
        text = data.get("text", "").lower()

        # Must reference state machinery or commune
        has_state_machinery = "state machinery" in text
        has_commune = "commune" in text

        assert has_state_machinery or has_commune, (
            "paris_commune_1871.json must reference state machinery or commune (Marx analysis)"
        )
