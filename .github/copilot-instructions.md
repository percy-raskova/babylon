# Copilot Review Instructions — Babylon

**Primary reference:** [`CLAUDE.md`](../CLAUDE.md) (architecture, standards, the
Constitution pointer). These instructions tune your REVIEW: flag what our
deterministic gates cannot see. Rewritten 2026-07-30 under ADR181 — review
directives only, no architecture prose.

## What to flag (our invariants, in priority order)

1. **Determinism is law** (Constitution III.7): every tick produces a
   deterministic hash. Flag any float path that can emit `-0.0`, `NaN`, or
   `inf`; any reduction whose order is not fixed; any iteration over an
   unordered container that reaches an observable output; any wall-clock or
   `time.sleep`-based logic in tests.
2. **No imposed functional forms** (ADR172 ruling 5): a sigmoid / logistic /
   tanh / softmax STIPULATED inside a mechanic is a constitutional violation —
   S-curves must EMERGE from `P(revolution)`/`P(acquiescence)` and within-class
   dispersion. Flag any new stipulated curve in `src/babylon/` mechanics or
   `rust/` engine code, including via coefficient tables that encode one.
3. **Frozen Pydantic + `model_copy`**: `model_copy(update=...)` SKIPS
   validation (the phi_hour scar). Flag every `model_copy(update=...)` that
   writes a constrained scalar (`ge=`, `le=`, `Probability`, `Currency`,
   `Intensity`, `Coefficient`).
4. **Native hyperedge law** (Amendment D): `babylon-graph`'s exposed model has
   first-class hyperedges; Levi/incidence encodings are internal storage ONLY.
   Flag any API that expands a member list into pairwise edges or leaks an
   incidence representation.
5. **Cross-language transcription fidelity** (your best skill): Rust code in
   `rust/crates/` ports frozen Python reference semantics (`babylon.kernel`)
   and the normative `docs/reference/bsl-language.rst` (§-numbers,
   `E-LEX`/`E-PARSE`/`E-TYPE`/`E-LOAD`/`E-EVAL` codes). Flag any divergence
   between a doc comment's claim and the code, any operation the §3.2 Currency
   operator table does not license, and any error path that silently defaults
   instead of failing loud (Constitution III.11).
6. **Vocabulary honesty**: node/edge types and attributes in fixtures must be
   ones production actually stamps (`NodeType.*`, declared model fields —
   never invented strings or phantom attributes). Flag fixture-only vocabulary.
7. **The Python engine is FROZEN** (tag `p27-python-freeze`, Amendment AE):
   flag any PR adding engine capability in `src/babylon/engine/`,
   `src/babylon/domain/`, or `src/babylon/formulas/` — new capability lands
   Rust-side; Python changes are reference repairs or contract authoring only.
8. **Determinism-adjacent config**: flag `gh pr merge --auto` anywhere, venv
   cache keys gaining `restore-keys` (deliberate exact-match — a fallback
   resurrects a stale `babylon-tui` wheel), and scheduled workflows that do
   not exist on the default branch.

## What NOT to comment on

- Formatting, line length, import order — ruff/rustfmt own these; your one
  hallucination on record was a line-length claim.
- Naming preferences, doc phrasing style, unused dev-dependencies.
- Suggestions to add flexibility/configurability not asked for.
- The `web/` and `src/frontend/` trees (legacy per Amendment V, non-gating).

## House facts (so you don't re-derive them wrong)

- Graph substrate: **rustworkx** via `babylon.topology.BabylonGraph` (Python)
  and the `GraphSubstrate` trait (Rust). NetworkX was removed (Amendment L).
- Archive/RAG: **pgvector in Postgres** (ChromaDB retired, spec-037).
- Coefficients live in `GameDefines`/`defines.yaml` — a hardcoded coefficient
  in logic is a defect worth flagging.
- Governance: a human Director holds the ideological line; agents self-merge
  on green under `CLAUDE.md`'s merge protocol, which now REQUIRES harvesting
  your review — write comments an agent can act on: one defect, its
  consequence, the file:line.
