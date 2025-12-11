# Part II: Empirical Evidence from Babylon

## The Numbers

Babylon is a geopolitical simulation engine modeling the collapse of American hegemony through Marxist-Leninist-Maoist Third Worldist theory. It's a complex technical project with mathematical foundations, graph-based architecture, and AI narrative integration. Here's what the git history reveals:

### Commit Statistics

| Metric | Value |
|--------|-------|
| Total commits | 531 |
| Time span | November 30, 2024 to December 11, 2025 |
| AI-assisted commits | 151 (28.4%) |
| Human commits | 380 (71.6%) |

### Codebase Size

| Metric | Value |
|--------|-------|
| Production code | 16,154 lines |
| Test code | 28,231 lines |
| Test:code ratio | 1.7:1 |
| Test functions | 1,444 across 73 files |

### Architecture Documentation

| Metric | Value |
|--------|-------|
| Architecture Decision Records | 20+ |
| YAML specification files | 25+ |
| Design documents | 28 markdown files |

### Development Tools Used

- Claude Code (primary)
- Aider (secondary)
- Devin AI (experimental)
- GitHub Copilot (legacy)

## What the Commits Reveal

The git history tells a story of *structured chaos*. Development happens in intense bursts—140 commits in 4 days (December 7-11, 2025)—followed by periods of dormancy. This is not the steady drumbeat of traditional software development. It's the rhythm of creative flow: inspiration, execution, rest.

The commit messages follow conventional commit format (`feat:`, `fix:`, `docs:`, `refactor:`), enforced by pre-commit hooks. Even in the intensity of a 58-commit day, every commit is categorized, every change is traceable. The discipline doesn't disappear under pressure—it's what enables the pressure.

Here's a sample of recent commits:

```
feat(engine): add Carceral Geography to TerritorySystem (Sprint 3.7)
feat(observer): add TopologyMonitor for condensation detection (Sprint 3.1)
refactor(models): replace IdeologicalComponent with George Jackson Model
docs(ai-docs): add observer-layer.yaml with Bondi Algorithm aesthetic
fix(engine): calculate wages from tribute flow, not accumulated wealth
```

Notice the sprint numbers, the specific component references, the mix of features, fixes, and documentation. This is not chaos. This is vibe coding with discipline.

## The AI-Assisted vs Human Commit Breakdown

AI-assisted commits cluster around specific activity types:

### High AI assistance (>50% of commits in category)

- Documentation generation
- Test boilerplate
- Infrastructure/tooling
- Type annotations
- Formatting/linting fixes

### Low AI assistance (<20% of commits in category)

- Core algorithm design
- Architecture decisions
- Bug fixes in game logic
- Mathematical formula implementation

The pattern is clear: AI handles the scaffolding, humans handle the soul. The division of labor isn't random—it's rational. AI excels at mechanical tasks with clear patterns. Humans excel at judgment calls with unclear tradeoffs.

## Code Quality Metrics

The codebase enforces quality through tooling:

```toml
# From pyproject.toml
[tool.mypy]
strict = true
disallow_untyped_defs = true
warn_return_any = true

[tool.ruff.lint]
select = ["E", "W", "F", "I", "B", "C4", "UP", "ARG", "SIM"]
```

MyPy strict mode means every function has type annotations, every variable has a declared type. Ruff catches style violations, potential bugs, unnecessary complexity. These aren't aspirational—they're enforced. Every commit passes through pre-commit hooks that verify compliance.

The result: you can read any function in the codebase and know exactly what types it accepts and returns. You can refactor with confidence because the type checker will catch mistakes. You can onboard new contributors (human or AI) because the code is self-documenting.

This is what vibe coding produces when paired with discipline.
