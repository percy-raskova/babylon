---
date: 2026-01-05T01:53:14-05:00
researcher: Claude
git_commit: 7b46481896761697e143df379ecaeb5e15d482bd
branch: dev
repository: babylon
topic: "Unit Test Health Assessment: Pytest Best Practices Analysis"
tags: [research, testing, pytest, code-quality, coverage, refactoring]
status: complete
last_updated: 2026-01-05
last_updated_by: Claude
---

# Research: Unit Test Health Assessment

**Date**: 2026-01-05T01:53:14-05:00
**Researcher**: Claude
**Git Commit**: 7b46481896761697e143df379ecaeb5e15d482bd
**Branch**: dev
**Repository**: babylon

## Research Question

Assess the health of unit tests in `tests/unit/`, evaluating pytest best practices, code complexity, mocks, assertions, modularity, and general testing best practices. Identify strengths, gaps, and improvement paths toward 90-95% code coverage.

## Executive Summary

| Metric | Current | Target | Status |
|--------|---------|--------|--------|
| Code Coverage | 54.3% | 90-95% | Gap: ~40% |
| Total Tests | 3,519 | - | Healthy |
| Pass Rate | 98.4% | 100% | 55 failing (UI) |
| Complexity | All A grades | A-B | Excellent |
| Test Files | 118 | - | Well-organized |

**Overall Assessment**: The test suite demonstrates **strong fundamentals** with excellent complexity scores, sophisticated custom tooling (fluent assertions, domain factory, centralized constants), and proper TDD discipline. The primary gap is **coverage of data ingestion and UI modules** (0% coverage on many data loaders). Achieving 90-95% coverage requires focused effort on data layer tests and mock infrastructure.

---

## Detailed Findings

### 1. Test Organization & Structure

**Directory Structure** (tests/unit/):
```
tests/unit/
├── ai/           # LLM provider, narrative director tests
├── config/       # Configuration and logging tests
├── data/         # Data normalization, loaders, corpus tests
├── engine/       # Core simulation engine tests (largest)
│   ├── adapters/
│   ├── history/
│   ├── observers/
│   └── systems/  # System-by-system tests
├── formulas/     # Pure math formula tests
├── ledger/       # Economic ledger tests
├── models/       # Pydantic model tests
│   └── components/
├── rag/          # RAG embedding/retrieval tests
├── tools/        # Analysis tool tests
├── topology/     # NetworkX topology tests
├── ui/           # DearPyGui UI tests
└── utils/        # Utility function tests
```

**Key Observations:**
- **729 test classes** vs 1 standalone function (highly class-organized)
- **47 conftest.py files** across the hierarchy (proper fixture layering)
- **149 total fixture definitions** (good reusability)
- Consistent naming: `test_<module>.py` pattern throughout

**conftest.py Hierarchy:**
- `tests/conftest.py` - Root fixtures (DomainFactory, random seeding)
- `tests/unit/conftest.py` - Unit test markers and base fixtures
- Domain-specific: `tests/unit/engine/conftest.py`, `tests/unit/models/conftest.py`, etc.

---

### 2. Pytest Markers (ADR008 Compliance)

The project follows ADR008 (Test Separation) with domain-specific markers:

| Marker | Count | Purpose |
|--------|-------|---------|
| `@pytest.mark.unit` | 291 | Default unit tests |
| `@pytest.mark.math` | 133 | Deterministic formula tests |
| `@pytest.mark.topology` | 81 | NetworkX graph tests |
| `@pytest.mark.ledger` | 57 | Economic state tests |
| `@pytest.mark.parametrize` | 29 | Parameterized tests |
| `@pytest.mark.integration` | 16 | Integration tests (misplaced in unit/) |
| `@pytest.mark.asyncio` | 10 | Async tests |
| `@pytest.mark.skipif` | 5 | Conditional skips |
| `@pytest.mark.red_phase` | 1 | TDD red phase marker |

**Configuration** (`pyproject.toml`):
```toml
[tool.pytest.ini_options]
markers = [
    "math: Deterministic formula tests",
    "ledger: Economic/political state tests",
    "topology: Graph/network tests",
    "integration: Database/ChromaDB tests",
    "ai: AI/RAG evaluation tests (slow)",
    "unit: Unit tests (default)",
    "red_phase: TDD RED phase (intentionally failing)"
]
```

---

### 3. Code Complexity Analysis (Radon)

**Cyclomatic Complexity**: All test files rated **A** (excellent)
- No function exceeds CC of 10
- Highest: `test_simulation_engine_fixture_equivalence` at B(8)

**Maintainability Index**:
| Rating | Files | Notes |
|--------|-------|-------|
| A (>20) | 116 | Excellent maintainability |
| B (10-20) | 1 | Moderate |
| C (<10) | 1 | `test_metrics_collector.py` (0.00 - likely stub) |

**Raw Metrics**:
- Total LOC: 57,339
- SLOC (Logical): 34,328
- Comment ratio: 8% (acceptable for tests)

---

### 4. Assertion Patterns

**Standard Assertions:**
- `assert ==`: 3,015 usages (primary pattern)
- `pytest.approx`: 411 usages (floating-point comparisons)
- `pytest.raises`: Used extensively for exception testing

**Custom Fluent Assertion Library** (`tests/assertions.py`):
```python
# Domain-specific fluent assertions
Assert(new_state).entity("C001").is_poorer_than(previous_state)
Assert(state).relationship("C001", "C002").has_tension_increased(previous)
```

Features:
- `Assert` - WorldState wrapper
- `EntityAssert` - Entity-level assertions (wealth, ideology, survival)
- `RelationshipAssert` - Edge assertions (tension, value_flow)
- Rich error messages with context
- Chainable API for multiple checks

**Floating-Point Handling**:
```python
# Pattern found throughout formulas tests
assert result == pytest.approx(expected, abs=0.001)
```

---

### 5. Fixture & Parametrization Patterns

**Fixture Scopes Used:**
- `function` (default) - Most fixtures
- `session` - Database engines, expensive setup
- `module` - Shared state within test modules
- `class` - Rarely used

**DomainFactory Pattern** (`tests/factories/domain.py`):
```python
factory = DomainFactory()
worker = factory.create_worker(wealth=100.0)
owner = factory.create_owner(organization=0.8)
state = factory.create_world_state(
    entities={"C001": worker, "C002": owner},
    relationships=[factory.create_relationship()]
)
```

Factory methods:
- `create_worker()` - Periphery proletariat defaults
- `create_owner()` - Core bourgeoisie defaults
- `create_relationship()` - EXPLOITATION edge defaults
- `create_world_state()` - Complete WorldState
- `create_territory()` - Territory defaults
- Event factories: `create_extraction_event()`, `create_spark_event()`, etc.

**Parametrization Examples:**
```python
# tests/unit/formulas/test_fundamental_theorem.py
@pytest.mark.parametrize("example", MarxCapitalExamples.all())
def test_rate_of_profit(example):
    rate = calculate_rate_of_profit(
        surplus_value=example.s,
        constant_capital=example.c,
        variable_capital=example.v,
    )
    assert rate == pytest.approx(example.expected_profit_rate, abs=0.001)
```

---

### 6. Centralized Constants (`tests/constants.py`)

Well-designed constant organization:

```python
@dataclass(frozen=True)
class CanonicalThresholds:
    """Universal threshold values."""
    POOL_HIGH: float = 0.7
    POOL_LOW: float = 0.3
    P_MIDPOINT: float = 0.5
    TICKS_STANDARD: int = 100

Canon = CanonicalThresholds  # Shorthand alias

# Domain-specific constants
class TestConstants:
    class Wealth: ...
    class Probability: ...
    class Ideology: ...
    class Consciousness: ...
```

Includes `MarxCapitalExamples` - parameterized test data from Marx's Capital.

---

### 7. Mock Usage Patterns

**Libraries Used:**
- `unittest.mock` (standard library) - Primary
- `pytest-mock` (mocker fixture) - Some tests
- `monkeypatch` (pytest built-in) - Environment/config patching

**Mocking Domains:**
| Domain | Mock Target | Files |
|--------|-------------|-------|
| AI/LLM | `LLMProvider`, `NarrativeDirector` | `test_llm_provider.py`, `test_director_*.py` |
| RAG | `ChromaDB`, embeddings | `test_embedding_event_loop.py`, `test_retrieval.py` |
| Logging | `logging.Logger` | `test_log.py`, `test_logging_config.py` |
| UI | DearPyGui internals | `test_dpg_runner.py` |

**Common Patterns:**
```python
# Patch decorator pattern
@patch('babylon.ai.llm_provider.DeepSeekProvider')
def test_provider_init(mock_provider):
    ...

# Context manager pattern
with patch.object(logger, 'info') as mock_info:
    ...

# MagicMock for complex objects
mock_client = MagicMock(spec=ChromaDB)
mock_client.query.return_value = {...}
```

---

### 8. Coverage Analysis

**Current Coverage: 54.3%** (6,451 / 11,884 lines)

**100% Coverage Modules** (Strengths):
- `src/babylon/systems/formulas/*.py` - All formula modules
- `src/babylon/utils/math.py`
- `src/babylon/utils/log.py`

**0% Coverage Modules** (Gaps):
| Module | Missing Lines | Priority |
|--------|---------------|----------|
| `data/cli.py` | 227 | Medium |
| `data/fred/loader_3nf.py` | 324 | High |
| `data/census/parser.py` | 98 | High |
| `data/energy/api_client.py` | 136 | High |
| `data/energy/loader_3nf.py` | 121 | High |
| `data/trade/loader_3nf.py` | ~150 | High |
| `data/materials/loader_3nf.py` | ~150 | High |
| `ui/terminal.py` | ~200 | Low |
| `__main__.py` | 38 | Low |

**Coverage by Domain:**
- Formulas: 100%
- Engine/Systems: ~70-80%
- Models: ~75%
- Data loaders: 0-20%
- UI: ~30%

---

## Strengths

### 1. Excellent Code Complexity
All test files rated A for cyclomatic complexity and maintainability. Tests are simple, focused, and readable.

### 2. Sophisticated Custom Tooling
- **Fluent assertion library** - Domain-specific, readable assertions
- **DomainFactory** - Centralized entity creation with sensible defaults
- **Centralized constants** - Single source of truth for test values

### 3. Strong Formula Test Coverage
Mathematical core (survival calculus, imperial rent, solidarity transmission) has 100% coverage with parameterized tests using theoretical examples.

### 4. Proper TDD Discipline
- `@pytest.mark.red_phase` marker for TDD workflow
- Clear separation of fast/slow tests per ADR008
- Comprehensive fixture hierarchy

### 5. Good Test Organization
- Consistent class-based test grouping
- Hierarchical conftest.py structure
- Domain-aligned directory structure

---

## Gaps & Weaknesses

### 1. Data Loader Coverage Gap (Critical)
**0% coverage** on most data ingestion code:
- Census, FRED, Energy, Trade, Materials loaders
- API clients and parsers
- This represents ~1,500 untested lines

### 2. Limited Parametrization
Only **29 parametrize markers** across 3,519 tests. Many test classes have repetitive test methods that could be consolidated.

### 3. UI Test Failures
55 failing tests in `test_dpg_runner.py` - appears to be testing non-existent UI code (module import failures).

### 4. Mock Inconsistency
Mixed use of `unittest.mock`, `pytest-mock`, and `monkeypatch` without clear pattern. Some tests use `MagicMock` without `spec=` (can hide API changes).

### 5. Missing Integration Between Unit Tests
Some "integration" markers in `tests/unit/` suggest boundary confusion.

---

## Improvement Recommendations

### Phase 1: Quick Wins (Target: 65% coverage)

1. **Delete or fix failing UI tests** (`test_dpg_runner.py`)
   - 55 tests importing non-existent module
   - Either implement the module or remove dead tests

2. **Add data loader unit tests with mocks**
   - Mock API clients for FRED, Census, Energy
   - Test parsing logic in isolation
   - Example structure:
   ```python
   @pytest.fixture
   def mock_census_api(mocker):
       return mocker.patch('babylon.data.census.api_client.CensusAPI')

   def test_census_loader_parses_response(mock_census_api):
       mock_census_api.return_value.get.return_value = SAMPLE_RESPONSE
       loader = CensusLoader()
       result = loader.load()
       assert result.dimensions_loaded['dim_state'] == 52
   ```

3. **Enable `--cov-fail-under=60`** in CI to prevent regression

### Phase 2: Systematic Improvement (Target: 80% coverage)

1. **Consolidate repetitive tests with parametrize**
   - Many `TestDomainFactory*` tests test single attributes
   - Consolidate:
   ```python
   @pytest.mark.parametrize("attr,expected", [
       ("id", "C001"),
       ("name", "Test Worker"),
       ("role", SocialRole.PERIPHERY_PROLETARIAT),
       ("wealth", 0.5),
   ])
   def test_create_worker_defaults(attr, expected):
       worker = DomainFactory().create_worker()
       assert getattr(worker, attr) == expected
   ```

2. **Standardize mock patterns**
   - Use `pytest-mock` (mocker fixture) consistently
   - Always use `spec=` or `autospec=True` for safety
   - Create mock fixtures in conftest for common mocks

3. **Add missing edge case tests**
   - Boundary conditions for constrained types
   - Error paths in exception handling
   - Empty/null input handling

### Phase 3: Excellence (Target: 90-95% coverage)

1. **Property-based testing** (Hypothesis)
   - Particularly for formula edge cases
   - Example:
   ```python
   from hypothesis import given, strategies as st

   @given(wages=st.floats(0, 1000), value=st.floats(0, 1000))
   def test_imperial_rent_properties(wages, value):
       rent = calculate_imperial_rent(wages, value)
       assert rent >= 0 or wages > value  # Rent is non-negative when extracting
   ```

2. **Snapshot testing** for complex outputs
   - Simulation state after N ticks
   - Event sequences

3. **Coverage enforcement per module**
   - `formulas/`: 100% required
   - `engine/systems/`: 90% required
   - `data/`: 80% required
   - `ui/`: 70% required

---

## Test Health Metrics Dashboard

| Category | Score | Notes |
|----------|-------|-------|
| **Coverage** | C (54%) | Major gap in data layer |
| **Complexity** | A | All tests simple and focused |
| **Organization** | A | Excellent structure |
| **Assertions** | A | Custom fluent library |
| **Fixtures** | B+ | Good but could use more factory patterns |
| **Parametrization** | C | Under-utilized |
| **Mocking** | B- | Inconsistent patterns |
| **Documentation** | B | Constants documented, tests less so |

**Overall Grade: B-** (Strong foundation, coverage gap)

---

## Code References

- Test constants: `tests/constants.py`
- Fluent assertions: `tests/assertions.py`
- Domain factory: `tests/factories/domain.py`
- Root fixtures: `tests/conftest.py`
- Unit test config: `tests/unit/conftest.py`
- ADR on test separation: `ai-docs/decisions/ADR008_test_separation.yaml`

---

## Related Documentation

- [ADR008: Test Separation](../../../ai-docs/decisions/ADR008_test_separation.yaml)
- [ADR031: Test Constants Architecture](../../../ai-docs/decisions/index.yaml)
- [pytest documentation](https://docs.pytest.org/en/stable/)
- [Python Testing Best Practices](https://pytest-with-eric.com/introduction/python-unit-testing-best-practices/)

---

## Open Questions

1. Should UI tests (`test_dpg_runner.py`) be moved to integration or deleted?
2. Is 90-95% coverage realistic for CLI/UI code, or should those have lower thresholds?
3. Should `hypothesis` be added for property-based testing of formulas?
4. What's the strategy for testing external API clients (Census, FRED, EIA)?
