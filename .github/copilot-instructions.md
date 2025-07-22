# 
This is a Python-based repository for Babylon, a text-based RPG simulating the interplay of political, economic, and social forces. Contributions should adhere to the following workflow and standards:

## Core Principles

- **Use Chroma, Memory, and GitHub MCPs** as necessary for feature development and maintenance.
- **Log to Memory at the end of every job:** After each significant task or job, record observations, notes, and positive developments to Memory for future reference and reproducibility.
- **Adhere to Test-Driven Development (TDD):** All new features and bug fixes should be covered by corresponding unit or integration tests.
- **Follow good Python coding standards:** Code should be idiomatic, clear, and maintainable. Use type hints where appropriate.

## Development Workflow

- **Dependency Management:** Use Poetry for dependency management and packaging.
    - Install dependencies: `poetry install`
    - Add a dependency: `poetry add <package>`
    - Run a shell: `poetry shell`
- **Testing:** Use the Pytest suite for all tests.
    - Run all tests: `poetry run pytest`
    - Add tests for each new feature or bugfix before or as you implement changes.
- **Formatting & Linting:** 
    - Format code with [black](https://black.readthedocs.io/) and organize imports with [isort](https://pycqa.github.io/isort/).
    - Lint with [flake8](https://flake8.pycqa.org/) or [ruff](https://docs.astral.sh/ruff/).
    - Typical commands:
        - `poetry run black .`
        - `poetry run isort .`
        - `poetry run flake8 .`
- **Documentation:** Document all public APIs, classes, and complex logic. Update the docs/ directory as needed.
- **Separation of Concerns:** Keep game logic, data, and I/O well separated. Use dependency injection for components where feasible to improve testability.

## Logging and Observability

- At the end of every significant job (feature, bugfix, or refactor), log to Memory:
    - What was done
    - Key design decisions
    - Any issues or surprises encountered
    - Notable improvements or successes
- Also make sure to maintain a TODO.md file that you update with your progress, suggestions for new tasks, etc
## Key Guidelines

1. Use Chroma, Memory, and GitHub MCPs thoughtfully—refer to project documentation for integration patterns.
2. Use Poetry for all dependency and environment management.
3. Write or update Pytest-based tests for every new feature or bugfix (TDD preferred).
4. Format, lint, and type-check before submitting code.
5. Document your code and update docs/ as needed.
6. Log observations, notes, and positive outcomes to Memory after each job.
7. Conventional commit messages
