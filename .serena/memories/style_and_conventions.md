# Code Style and Conventions

**Core Philosophy:**

- **TDD Requirement (Red/Green/Refactor)**: All changes MUST follow Test-Driven Development unless explicitly waived by user. Write failing test first (`@pytest.mark.red_phase`), implement minimal code to pass, refactor.
- **Pydantic First**: No raw dicts. All game entities use strict Pydantic BaseModels constraints (`Probability`, `Currency`, `Intensity`).
- **Strict Typing**: MyPy strict mode, explicit return types.
- **Docstrings**: MUST use Sphinx-compatible `RST` docstrings for all public elements. Theory heavy. Example: `:param name:`, `:returns:`, `:raises Error:`, etc.
- **Test Constants**: Hardcoded magics are forbidden within tests except boundary tests (0.0, 1.0). Use `tests/constants.py` via `TC.Category.VARIABLE`.
- **Git Workflow**: Benevolent Dictator model. Branch structure: `feature/*`, `fix/*`, `refactor/*`, branching from `dev`. Use Conventional Commits (`feat(scope): msg`). Commit early and often (after every logical unit).
