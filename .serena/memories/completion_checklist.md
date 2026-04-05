# Task Completion Checklist

When completing a task/unit of work within this repository, execute the following steps prior to stopping:

1. **Gate Check**: Run `mise run check` and ensure all linting, formatting, typechecking, and unit tests pass.
1. **Review Code MI**: Ensure rich background theory details are placed into Sphinx `docs/` rather than bloating function docstrings to optimize Maintainability Index.
1. **Docs Update (`ai-docs/`)**: Update Markdown/YAML specification files in `ai-docs/` to reflect the new state immediately. This is mandatory for architecture changes, state changes, and new systems.
   - `state.yaml` (Test counts, component changes)
   - `roadmap.md` (Milestones passed)
   - `architecture.yaml` (System integrations)
1. **Micro-Commits**: Produce atomic conventional commits for each distinct fix/feature. Never merge huge multi-step tasks into one massive commit.
