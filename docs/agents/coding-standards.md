# Coding Standards

## Pydantic First

All game objects are `pydantic.BaseModel`. No raw dicts anywhere.

## Constrained Types

Use domain-specific types instead of raw floats:

- `Probability` — [0.0, 1.0]
- `Currency` — non-negative float
- `Intensity` — [0.0, 1.0]
- `Ideology` — [-1.0, 1.0]
- `Coefficient` — smooth parameter, alpha-stable

## TDD Discipline

Red-Green-Refactor, mandatory for every change unless user explicitly waives:

1. **RED**: Write failing test first. Use `@pytest.mark.red_phase` if intentionally failing.
1. **GREEN**: Implement minimal code to pass.
1. **REFACTOR**: Clean up while keeping tests green.

## Conventional Commits

Use prefixes: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`

## Docstrings

Sphinx-compatible RST format:

- Use `::` for code blocks (not markdown backticks)
- `Args:`, `Returns:`, `Raises:` sections
- `:class:`, `:func:`, `:mod:` for cross-references
- Blank line before/after code blocks
- Examples should pass `pytest --doctest-modules`

**Maintainability Refactoring**: Move rich theory from function docstrings to RST files (`docs/reference/*.rst`). Module docstring = summary + See Also. Function docstring = one-liner + Args + Returns + minimal Example. This preserves Sphinx output while reducing LOC that penalizes MI scores.

## Import Order

```python
from __future__ import annotations

import pytest                          # stdlib first
from pydantic import ValidationError   # third-party second

from babylon.models import SocialClass # local imports third
from tests.constants import TestConstants
TC = TestConstants                      # alias AFTER all imports
```

## No `test_` Prefix in Production Code

Pytest auto-collects `test_` functions. Use `check_`, `verify_`, `validate_` for production functions that verify something.

## `__all__` Exports

Update `__init__.py` when adding public functions.

## Type Ignore Comments

Use specific error codes:

```python
# GOOD
import dearpygui.dearpygui as dpg  # type: ignore[import-untyped]

# BAD
import something  # type: ignore
```
