# Part VII: Lessons Learned

## When Vibe Coding Works

Vibe coding excels when:

### 1. You know what you want to build

The AI is an amplifier, not a decision-maker. If you can describe the outcome clearly, AI accelerates implementation. If you don't know what you want, AI generates confident nonsense.

### 2. You can verify the output

Tests, type checks, manual review—some verification mechanism must exist. Without verification, AI-generated code is a liability.

### 3. The domain has good training data

AI assistance is most reliable for common patterns: web APIs, data processing, CRUD operations. Niche domains with sparse training data get worse results.

### 4. You maintain the discipline stack

Hooks, tests, types, documentation. Without these, vibe coding degrades rapidly.

### 5. You're willing to read and understand

The AI writes; you review. If you paste without reading, you're not vibe coding. You're gambling.

## When Vibe Coding Fails

Vibe coding struggles when:

### 1. Requirements are ambiguous

AI generates plausible implementations of misunderstood requirements. If you don't know what you want, neither does the AI.

### 2. Novelty is required

AI produces conventional solutions. If you need something genuinely novel, AI can scaffold but not innovate.

### 3. Security is paramount

AI can generate insecure code with confidence. Security review requires human expertise.

### 4. Performance is critical

AI produces working code, not optimal code. Performance tuning requires understanding tradeoffs.

### 5. The codebase is unique

AI is trained on public code. Private, unusual, or legacy codebases don't match its patterns.

## How to Build the Discipline Stack

For developers wanting to adopt disciplined vibe coding:

### 1. Start with pre-commit hooks

This is the lowest-effort, highest-impact change. Linting, formatting, and basic tests on every commit.

### 2. Adopt TDD for new features

Don't refactor existing code to TDD. Write new features test-first. Let coverage grow organically.

### 3. Add type hints gradually

Start with new files. Configure MyPy with incremental strictness. Don't try to type the whole codebase at once.

### 4. Document decisions, not code

Don't write comments explaining what code does. Write ADRs explaining why you made architectural choices.

### 5. Use memory tools if available

Claude-mem, custom RAG, or even a well-maintained text file. Anything that preserves context between sessions.

## The Role of Human Judgment

After all the tools, hooks, tests, and types—human judgment remains essential.

The AI doesn't know:

- What the business actually needs
- Which tradeoffs are acceptable
- What security posture is required
- How the code fits into the larger system
- Whether the tests actually test the right things

These require judgment. They require understanding. They require the human in the loop.

Vibe coding doesn't replace human judgment. It gives human judgment more leverage. Freed from syntax and boilerplate, you can focus on what matters: Is this the right thing to build? Does it actually work? Will it serve its users?
