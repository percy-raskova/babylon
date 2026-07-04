# Quickstart: Verify the Cold Collapse Migration

All commands run from the repo root (`worktrees/w090`). The frontend `node_modules` / `.venv` are
shared symlinks — never `npm install` / `poetry install`.

## 1. The blocking gate

```bash
mise run web:check          # tsc + eslint + prettier + vitest (Vitest total >= 310)
```

## 2. The banned-font gate

```bash
rg -i 'roboto mono|inter' web/frontend/src/index.css   # MUST be empty
```

## 3. Token contract (unit)

```bash
cd web/frontend && npx vitest run src/theme/tokens.contract.test.ts
# asserts canon token values present, banned fonts absent, self-hosted @font-face,
# and the six DATA_RAMPS match canon
```

## 4. Fonts are self-hosted (offline)

```bash
ls web/frontend/public/fonts/*/            # woff2 + license per family
rg -i 'googleapis|gstatic' web/frontend/src/index.css web/frontend/index.html  # MUST be empty
```

## 5. Visual review against canon previews

Open side by side and confirm the running chrome matches:
- `design/mockups/preview/colors-cold-collapse.html` — palette
- `design/mockups/preview/colors-data.html` — the six ramps (data surfaces: NO CRT texture)
- `design/mockups/preview/type-specimens.html` — the four families
- `design/mockups/preview/effects-crt.html` — CRT texture (chrome only)

Optional live check:
```bash
mise run web:dev            # Django :8000 + Vite :5173 (Lane W owns these ports this phase)
# then browse http://localhost:5173 and DevTools > Network: no font requests leave the machine
```

## 6. Amendment + constitution untouched

```bash
test -f specs/090-cold-collapse/article-vii-amendment.md && echo "amendment drafted"
git diff --stat .specify/memory/constitution.md   # MUST be empty (BD ratifies, not us)
```

## Definition of done

- [ ] `mise run web:check` green, Vitest >= 310
- [ ] `rg -i 'roboto mono|inter' web/frontend/src/index.css` empty
- [ ] token-contract test GREEN (was RED pre-migration)
- [ ] four families self-hosted with licenses; no Google Fonts at runtime
- [ ] six ramps match canon; lenses resolve to their canon ramp
- [ ] Article VII amendment drafted; constitution.md unchanged
