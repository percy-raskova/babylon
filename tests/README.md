# Test Suite Documentation

This document establishes testing patterns and guidelines for the Babylon test suite.

## Directory Structure

```
tests/
├── conftest.py          # Root fixtures (db, mocks, random isolation)
├── constants.py         # TestConstants from GameDefines (YAML-first)
├── README.md            # This file
├── unit/                # Fast, isolated unit tests
│   ├── ai/              # LLM, narrative, persona tests
│   ├── data/            # Data loader tests
│   ├── engine/          # Simulation engine tests
│   ├── formulas/        # Formula tests (math, property-based)
│   ├── models/          # Pydantic model tests
│   ├── rag/             # RAG retrieval tests
│   └── ui/              # UI tests (mocked DearPyGui)
├── integration/         # Multi-component integration tests
├── scenarios/           # Full simulation scenario tests
└── fixtures/            # Shared test data files
```

## Mock Patterns

### Use `spec=` for Internal Classes

When mocking internal Babylon classes, ALWAYS use `spec=` to ensure type safety.
This catches bugs where tests access attributes that don't exist on the real class.

```python
from unittest.mock import MagicMock
from babylon.engine.simulation import Simulation

# GOOD: spec= ensures mock follows Simulation interface
mock_sim = MagicMock(spec=Simulation)

# BAD: Plain mock allows any attribute access
mock_sim = MagicMock()  # Don't do this for internal classes
```

### Use Plain MagicMock for External Libraries

External library interfaces may change between versions. Using `spec=` on external
libraries can cause false test failures. Use plain MagicMock instead.

```python
from unittest.mock import MagicMock

# GOOD: External library, no spec needed
mock_response = MagicMock()
mock_response.status_code = 200
mock_response.choices = [MagicMock()]

# External libs where this applies:
# - OpenAI/DeepSeek API responses
# - ChromaDB clients/collections
# - HTTP responses (requests, httpx)
# - SQLAlchemy engines (but Session uses spec=, see data/conftest.py)
```

### Use `patch()` Context Manager (Not Decorators)

Prefer context manager style for clarity and explicit scoping:

```python
from unittest.mock import patch

# GOOD: Context manager - explicit scope
def test_something():
    with patch("babylon.config.base.BaseConfig.LOG_DIR", tmpdir):
        # test code here
        pass

# AVOID: Decorator stacking (harder to read, implicit scope)
@patch("module.thing")
@patch("module.other")
def test_something(mock_other, mock_thing):  # Order is reversed!
    pass
```

### Available Shared Mock Fixtures

The root `conftest.py` provides these fixtures:

| Fixture                  | Type                          | Description                               |
| ------------------------ | ----------------------------- | ----------------------------------------- |
| `mock_llm_provider`      | `MagicMock(spec=LLMProvider)` | Pre-configured LLM mock with `generate()` |
| `mock_chroma_client`     | `MagicMock`                   | ChromaDB client with query/add configured |
| `mock_chroma_collection` | `MagicMock`                   | ChromaDB collection with empty results    |
| `mock_simulation`        | `MagicMock(spec=Simulation)`  | Simulation mock for engine tests          |

The `tests/unit/data/conftest.py` provides:

| Fixture              | Type                      | Description                        |
| -------------------- | ------------------------- | ---------------------------------- |
| `mock_db_session`    | `MagicMock(spec=Session)` | SQLAlchemy session mock            |
| `in_memory_db`       | `Engine`                  | In-memory SQLite for loader tests  |
| `mock_http_response` | `MagicMock`               | HTTP response with status_code=200 |
| `mock_httpx_client`  | `MagicMock`               | httpx.Client mock                  |

**Example usage:**

```python
def test_narrative_generation(mock_llm_provider):
    """Test NarrativeDirector uses LLM provider."""
    mock_llm_provider.generate.return_value = "The workers rose up..."

    director = NarrativeDirector(llm=mock_llm_provider)
    result = director.narrate(state)

    assert "workers" in result
    mock_llm_provider.generate.assert_called_once()
```

## Test Constants (YAML-First)

All domain constants should come from `TestConstants`, which pulls from `GameDefines`:

```python
from tests.constants import TestConstants
TC = TestConstants

# GOOD: Semantic constant from YAML source
assert worker.wealth == TC.Wealth.WORKER_BASELINE

# BAD: Magic number with no traceability
assert worker.wealth == 10.0  # Where does this come from?
```

**Exception**: Type boundary values (0.0, 1.0 for Probability) are kept inline
because they document the TYPE definition itself.

## Pytest Markers

```python
@pytest.mark.math        # Deterministic formulas (fast, pure)
@pytest.mark.ledger      # Economic/political state
@pytest.mark.topology    # Graph/network operations
@pytest.mark.integration # Database/ChromaDB (I/O bound)
@pytest.mark.ai          # AI/RAG evaluation (slow, non-deterministic)
@pytest.mark.unit        # Unit tests (default)
@pytest.mark.slow        # Long-running tests (excluded from pre-commit)
@pytest.mark.property    # Hypothesis property-based tests
```

**Running specific markers:**

```bash
poetry run pytest -m "not ai"        # Exclude AI tests (CI default)
poetry run pytest -m "math"          # Only formula tests
poetry run pytest -m "not slow"      # Exclude slow tests (pre-commit)
```

## Property-Based Testing (Hypothesis)

Formula tests use Hypothesis to verify properties across input domains:

```python
from hypothesis import given, strategies as st

@pytest.mark.math
class TestProbabilityBounds:
    @given(
        wealth=st.floats(min_value=0.0, max_value=1e6, allow_nan=False),
        subsistence=st.floats(min_value=0.01, max_value=1e6, allow_nan=False),
    )
    def test_psa_is_valid_probability(self, wealth: float, subsistence: float):
        """P(S|A) always returns value in [0, 1]."""
        p_sa = calculate_acquiescence_probability(
            wealth=Currency(wealth),
            subsistence_threshold=Currency(subsistence),
        )
        assert 0.0 <= float(p_sa) <= 1.0
```

**Hypothesis configuration** (in `pyproject.toml`):

- `deadline = 500` - Allow 500ms for complex formulas
- `max_examples = 100` - Balance thoroughness vs speed

## Writing Tests

### TDD Flow

1. **Red**: Write failing test first
1. **Green**: Write minimal code to pass
1. **Refactor**: Clean up while keeping tests green

### Test Structure

```python
@pytest.mark.unit
class TestSomething:
    """Tests for Something functionality."""

    def test_happy_path(self):
        """Something does expected thing with valid input."""
        result = something(valid_input)
        assert result == expected

    def test_edge_case(self):
        """Something handles edge case gracefully."""
        result = something(edge_input)
        assert result == edge_expected

    def test_error_case(self):
        """Something raises appropriate error for invalid input."""
        with pytest.raises(ValueError, match="expected message"):
            something(invalid_input)
```

### Parametrization

Use `pytest.mark.parametrize` for similar tests:

```python
@pytest.mark.parametrize(
    "field,expected",
    [
        ("wealth", TC.Wealth.DEFAULT),
        ("organization", TC.Probability.LOW),
        ("repression_faced", TC.Probability.MIDPOINT),
    ],
)
def test_social_class_defaults(field: str, expected: float):
    """SocialClass has expected defaults from GameDefines."""
    worker = SocialClass(id="C001", name="Test", role=SocialRole.PERIPHERY_PROLETARIAT)
    assert getattr(worker, field) == expected
```

## Common Fixtures

### Random State Isolation

All tests automatically get deterministic random state (seed=42):

```python
# In root conftest.py - autouse=True
@pytest.fixture(autouse=True)
def _isolate_random_state():
    random.seed(42)  # Reproducible across test orderings
    # ... cleanup restores original state
```

### Temporary Directories

```python
def test_file_output(test_dir):
    """Test writes to session-scoped temp directory."""
    output_path = Path(test_dir) / "output.json"
    write_output(output_path)
    assert output_path.exists()
```

### In-Memory Database

```python
def test_loader(in_memory_db, mock_db_session):
    """Test loader with mocked database."""
    loader = MyLoader(session=mock_db_session)
    loader.load(data)
    mock_db_session.commit.assert_called_once()
```

## References

- **Test Constants**: `tests/constants.py`
- **GameDefines (YAML source)**: `src/babylon/data/defines.yaml`
- **ADR008 (Test Separation)**: `ai-docs/decisions/ADR008_test_separation.yaml`
- **Hypothesis docs**: https://hypothesis.readthedocs.io/
