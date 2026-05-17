# Quickstart: Headless Postgres-Backed Simulation Runner

**Feature**: 064-headless-sim-runner
**Audience**: Operator (developer running the simulation), LLM coding agent
(parsing simulation output), CI engineer (gating on conservation invariants)

---

## Operator quickstart (5 minutes to first run)

### Prerequisites

```bash
# 1. Postgres test instance is up (port 5433, project default)
docker ps | rg babylon-pg-isolated  # OR pg_isready -h localhost -p 5433

# 2. SQLite reference DB exists and is populated
test -f data/sqlite/marxist-data-3NF.sqlite && ls -lh data/sqlite/marxist-data-3NF.sqlite

# 3. TIGER geometry has been bootstrapped into Postgres
#    (only needed once per Postgres deployment)
mise run data:tiger-counties
```

If step 2 fails, bootstrap the SQLite reference DB:

```bash
mise run data:tiger-sqlite
```

### Run the canonical Michigan + Canada simulation

```bash
mise run sim:e2e-michigan
```

After ~5–10 minutes, the command prints the artifact directory path on
stdout. Example:

```text
/home/user/projects/game/babylon/reports/sim-runs/2026-05-14T16-30-00Z/
```

The directory contains exactly three artifacts:

```text
reports/sim-runs/2026-05-14T16-30-00Z/
├── trace.csv       # 83,001 rows (1 header + 83 × 1000), ~2 MB
├── summary.json    # ~20 KB
└── manifest.json   # ~10 KB
```

### Common overrides

```bash
# Smaller scope: Detroit tri-county (fast smoke test, ~30 seconds)
mise run sim:e2e-michigan -- --scope detroit-tri-county

# Shorter run for iteration
mise run sim:e2e-michigan -- --ticks 100

# Fixed output directory for re-running into the same path (overwritten)
mise run sim:e2e-michigan -- --output-dir /tmp/babylon-run

# Override a single GameDefines parameter
mise run sim:e2e-michigan -- --defines path/to/overrides.toml

# Reproduce a previous run exactly
mise run sim:e2e-michigan -- --seed 2010 --start-year 2010
```

### Interrupting a long run

```bash
mise run sim:e2e-michigan
# (5 minutes in, Ctrl-C)
^C
# Partial artifacts in reports/sim-runs/<ts>/
# manifest.json has `partial: true` and exit code is 130
echo $?  # 130
```

---

## LLM-agent quickstart (parsing the output)

An LLM agent receives only the artifact directory path. The agent reads the
three files and answers run-level diagnostic questions.

### Step 1 — Parse manifest.json first

```python
import json
from pathlib import Path

bundle = Path("/home/user/projects/game/babylon/reports/sim-runs/2026-05-14T16-30-00Z/")
manifest = json.loads((bundle / "manifest.json").read_text())

# Sanity check: is this a complete run?
is_partial = manifest["generator"]["partial"]
print(f"Run completed cleanly: {not is_partial}")

# Reproducibility hash (use for diff-vs-baseline)
print(f"Input hash: {manifest['reproducibility']['input_hash']}")
```

### Step 2 — Read summary.json for diagnostic answers

```python
summary = json.loads((bundle / "summary.json").read_text())

# Q: Did the run succeed?
print(f"Exit reason: {summary['run_metadata']['exit_reason']}")
print(f"Ticks completed: {summary['run_metadata']['ticks_completed']} / "
      f"{summary['run_metadata']['ticks_requested']}")

# Q: What were the terminal aggregates?
ts = summary["terminal_state"]
print(f"Counties still alive: {ts['counties_alive']}")
print(f"Total surplus extracted at terminal tick: ${ts['total_s']:,.0f}")

# Q: Did any conservation invariants break?
violations = summary["conservation_audit"]
print(f"Conservation violations: {len(violations)}")
for v in violations[:5]:
    print(f"  tick {v['tick']:>4}  {v['invariant_name']:30} "
          f"severity={v['severity']}")

# Q: Which county changed economically the most?
snapshot = summary["county_terminal_snapshot"]
biggest_change = max(snapshot, key=lambda c: abs(c["delta_k_vs_initial"]))
print(f"Biggest change: {biggest_change['entity_id']} "
      f"Δk = ${biggest_change['delta_k_vs_initial']:,.0f}")
```

### Step 3 — Stream trace.csv for time-series questions

```python
import csv

trace_path = bundle / "trace.csv"
with trace_path.open() as fh:
    reader = csv.DictReader(fh)
    # Find the tick where Wayne County's revolution probability crossed 0.5
    for row in reader:
        if (row["entity_id"] == "26163"
                and row["entity_kind"] == "county"
                and row["p_revolution"]
                and float(row["p_revolution"]) > 0.5):
            print(f"Wayne flipped to majority p_revolution at tick {row['tick']}")
            break
```

### LLM-agent diagnostic checklist (US1 Acceptance Scenario 3)

The agent should be able to answer the following from ONLY the three
artifact files, in a single pass, without source-code access:

- [ ] **Did the run succeed?** → `summary.run_metadata.exit_reason`
- [ ] **How long did it run?** → `summary.run_metadata.ticks_completed` and
      `summary.performance.total_wallclock_sec`
- [ ] **Did any end-game condition fire?** →
      `summary.end_game_event` (present iff early-terminated)
- [ ] **Which conservation invariants violated and when?** →
      `summary.conservation_audit[*]`
- [ ] **What were the terminal-tick aggregates?** →
      `summary.terminal_state`
- [ ] **Per-county terminal snapshot?** →
      `summary.county_terminal_snapshot[*]`
- [ ] **Time-series for any specific county?** → stream trace.csv filtered
      by `entity_id`
- [ ] **What columns exist in trace.csv?** →
      `manifest.column_dictionaries.trace_csv`
- [ ] **Can I reproduce this run?** → Yes, run with same flags as
      `summary.run_metadata`; verify identical
      `manifest.reproducibility.input_hash`

---

## CI engineer quickstart (regression gating)

### Add the runner to CI as a long-form gate

Recommended: opt-in nightly or weekly job, NOT every-PR.

```yaml
# .github/workflows/sim-e2e.yml (illustrative; project uses local CI)
jobs:
  sim-e2e:
    runs-on: ubuntu-latest
    env:
      BABYLON_PG_DSN: ${{ secrets.BABYLON_PG_DSN }}
    steps:
      - uses: actions/checkout@v4
      - run: poetry install
      - run: mise run data:tiger-sqlite
      - run: mise run data:tiger-counties
      - name: Run headless e2e
        run: |
          ARTIFACT_DIR=$(mise run sim:e2e-michigan)
          echo "ARTIFACT_DIR=$ARTIFACT_DIR" >> "$GITHUB_ENV"
      - name: Gate on conservation invariants
        run: |
          python -c "
          import json, sys
          summary = json.load(open('${ARTIFACT_DIR}/summary.json'))
          violations = summary['conservation_audit']
          critical = [v for v in violations if v['severity'] == 'critical']
          if critical:
              print(f'FAIL: {len(critical)} critical violations')
              sys.exit(1)
          "
      - name: Compare against baseline
        run: |
          python tools/regression_test.py \
            --bundle ${ARTIFACT_DIR} \
            --baseline tests/baselines/michigan-e2e.json
      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: sim-e2e-bundle
          path: ${{ env.ARTIFACT_DIR }}
```

### Adding a new baseline after intentional behavior change

```bash
# After approving an intentional engine math change:
mise run sim:e2e-michigan
cp reports/sim-runs/<latest-ts>/summary.json tests/baselines/michigan-e2e.json
git commit tests/baselines/ -m "test(baseline): update michigan-e2e after engine math change"
```

---

## Verifying determinism

Run twice with the same seed and confirm byte-identical artifacts modulo
the non-deterministic fields (timestamps, hostname, working dir):

```bash
mise run sim:e2e-michigan -- --output-dir /tmp/run-a --seed 2010
mise run sim:e2e-michigan -- --output-dir /tmp/run-b --seed 2010

# trace.csv MUST be byte-identical
diff /tmp/run-{a,b}/trace.csv && echo "trace.csv determinism: PASS"

# input_hash in manifests MUST match
jq -r '.reproducibility.input_hash' /tmp/run-a/manifest.json
jq -r '.reproducibility.input_hash' /tmp/run-b/manifest.json
```

---

## Working with the tools/ statistical suite

All existing analysis tools continue to work; they now route through the
new runner under the hood.

```bash
# Monte Carlo (100 samples) — uses runner internally per sample
mise run sim:monte-carlo 100 42      # 100 samples, seed=42

# Parameter sweep
mise run sim:sweep                   # default: extraction_efficiency 0.05–0.50

# Sensitivity analysis
mise run tune:morris 20
mise run tune:sobol 512

# 2D landscape
mise run tune:landscape economy.extraction_efficiency 0.05 0.50 \
                         survival.repression_level 0.0 1.0

# Profiling
mise run sim:profile 100             # cProfile output → results/sim-profile.prof

# Health audit (3 scenarios)
mise run qa:audit
```

Each of these wraps `tools/shared.run_simulation(...)`, which internally
calls `babylon.engine.headless_runner.run(...)`. All output shapes are
identical to the pre-064 state.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Exit code 3, message "SQLite reference DB not found" | Missing reference data | `mise run data:tiger-sqlite` |
| Exit code 3, message "Hex hydration produced zero rows" | TIGER not yet in Postgres | `mise run data:tiger-counties` |
| Exit code 4, message "Postgres unreachable" | Container not running | `docker ps`; restart `babylon-pg-isolated` |
| Exit code 2, message "Unknown scope" | Typo in `--scope` | See `contracts/cli_contract.yaml` → `predefined_scopes` |
| Run hangs at "session_init" for >2 minutes | Likely hex hydration on a fresh Postgres at statewide scale | Wait — first-run Michigan hydration is ~60 seconds |
| `summary.conservation_audit` contains violations | Engine math regression OR data drift | Compare against baseline; if intentional, regenerate baseline |
| `mise run sim:monte-carlo` fails immediately | tools/shared.run_simulation routes failed | Run a single `sim:e2e-michigan` first to confirm runner is healthy |
