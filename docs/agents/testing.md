# Testing

## Test Constants

Centralized in `tests/constants.py` using frozen dataclasses. See **ADR031**.

```python
from tests.constants import TestConstants
TC = TestConstants

def test_worker_wealth(self) -> None:
    worker = create_worker(wealth=TC.Wealth.WORKER_BASELINE)
    assert worker.wealth == TC.Wealth.WORKER_BASELINE
```

**Categories**: `Wealth`, `Probability`, `Ideology`, `Consciousness`, `Thresholds`, `Vitality`, `Organization`, `EconomicFlow`, `RevolutionaryFinance`, `MetabolicRift`, `TRPF`, `MarxCapitalExamples`

**What to Extract vs Keep Inline**:

| Extract to Constants                        | Keep Inline                                      |
| ------------------------------------------- | ------------------------------------------------ |
| Domain defaults (`DEFAULT_WEALTH = 10.0`)   | Type boundaries (`0.0`, `1.0` for Probability)   |
| Thresholds (`AWAKENING = 0.7`)              | Edge cases (`-0.001` for "just below zero")      |
| Scenario values (`PERIPHERY_WORKER = 20.0`) | Precision tests (`0.123456789` for quantization) |
| Theoretical values (`LOSS_AVERSION = 2.25`) | Computed results in assertions                   |

Type boundary tests verify the TYPE DEFINITION itself. The values 0.0 and 1.0 ARE the Probability contract. Extracting them reduces clarity.

## Factories

`tests/factories/DomainFactory` — creates test entities with sensible defaults. Override only what matters for the test.

## Fixtures

`conftest.py` hierarchy:

- Root: Session-scoped infrastructure
- Per-domain: Domain-specific fixtures
- Avoid duplication across conftest files

## Pytest Markers

```python
@pytest.mark.math        # Deterministic formulas (fast, pure)
@pytest.mark.ledger      # Economic/political state
@pytest.mark.topology    # Graph/network operations
@pytest.mark.integration # Database/ChromaDB (I/O bound)
@pytest.mark.ai          # AI/RAG evaluation (slow, non-deterministic)
@pytest.mark.unit        # Unit tests (default)
@pytest.mark.red_phase   # TDD RED phase (intentionally failing)
```

## Running Tests

```bash
poetry run pytest tests/unit/test_foo.py::test_specific    # Single test
poetry run pytest -k "test_name_pattern"                   # Pattern matching
mise run test:unit                                          # Fast gate
mise run test:int                                           # Integration
mise run test:scenario                                      # Slow, full arcs
mise run test:cov                                           # With coverage
mise run test:doctest                                       # Doctest examples
```
