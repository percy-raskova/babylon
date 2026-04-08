# Suggested Commands

The project heavily utilizes `mise` as a task runner and environment manager.

### Core CI/Quality (Fast Gate)

- `mise run check` - Runs linter, formatter, typechecker, and unit tests.
- `mise run lint` - Run ruff linter (with fix).
- `mise run format` - Run ruff formatter.
- `mise run typecheck` - Run mypy (strict mode).
- `mise run clean` - Clean build artifacts.

### Testing (TDD is mandatory!)

- `mise run test:unit` - Fast unit tests.
- `mise run test:int` - Integration tests.
- `mise run test:all` - All non-AI tests.

### Simulation Execution & Tuning

- `mise run sim:run` - Start the main simulation entry point.
- `mise run sim:trace`, `sim:sweep`, `sim:profile` - Analysis workflows.
- `mise run tune:optuna`, `tune:landscape` - Parameter discovery.

### Web/UI

- `mise run web:dev` - Run Django + Vite DAEMON servers.
- `mise run web:stop` - Shut down servers.
- `mise run ui` - Launch Synopticon dashboard.
