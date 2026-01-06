# thoughts/

Working notes for context preservation between sessions. Not user documentation - just working memory.

## Structure

```
thoughts/
├── plans/      # Implementation plans before coding
├── research/   # Notes when investigating unfamiliar areas
├── handoffs/   # Context dumps when stopping work
├── decisions/  # Records of why X was chosen over Y
├── percy/      # Personal notes, scratchpad, works-in-progress
└── archive/    # Completed or superseded documents
```

## Naming Convention

```
YYYY-MM-DD_brief-description.md
```

## When to Write

- **plans/**: Before implementing anything non-trivial
- **research/**: When learning how something works
- **handoffs/**: When stopping work for the day or switching context
- **decisions/**: When making a choice that future-you might question
- **percy/**: Anything personal - drafts, ideas, quick notes

## Archive Policy

Move documents to `archive/` when:
- Status changes to `completed` or `superseded`
- The plan was implemented
- The decision was made and documented elsewhere (ai-docs/decisions/)
- The research question was answered and absorbed into ai-docs/

Preserve the original path in archive: `archive/plans/2025-01-04_feature-x.md`

## Frontmatter

All documents should have:

```yaml
---
date: 2025-01-04
author: human|claude
commit: abc123  # git rev-parse --short HEAD
status: active|completed|superseded
---
```

## File References

Use `path/to/file.py:45-67` format instead of pasting code blocks. Keeps docs small and navigable.

## Importing from claude-mem

Significant discoveries from claude-mem can be imported to `thoughts/` for permanence:

```bash
# Example: Import observation #15142 about branch protection
# Copy the observation content and create:
# thoughts/research/2025-01-04_branch-protection-config.md
```

Use this when a claude-mem observation contains insights worth preserving beyond session memory.
