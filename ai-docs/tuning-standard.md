# How to Tune Babylon

**Version:** 1.0.0
**Created:** 2025-12-30
**Status:** ACTIVE

This guide documents the standard workflow for parameter tuning in Babylon using Bayesian Optimization.

---

## Why Bayesian Optimization?

### The Problem with Grid Search

Traditional grid search is computationally infeasible for Babylon:

| Parameters | Values Each | Total Evaluations | Time @ 1s/sim |
|------------|-------------|-------------------|---------------|
| 3          | 10          | 1,000             | 17 minutes    |
| 5          | 10          | 100,000           | 28 hours      |
| 7          | 10          | 10,000,000        | 116 days      |

Babylon has 10+ tunable parameters. Grid search doesn't scale.

### The "Cliff" Problem

Babylon has **discontinuous failure states**. A simulation can go from stable (wealth=8.0) to collapsed (wealth=0.0) in a single tick. This creates sharp "cliffs" in the objective landscape.

**Why this matters:**
- Gradient descent assumes smooth landscapes - it fails on cliffs
- Random search wastes evaluations on clearly bad regions
- TPE (Tree-structured Parzen Estimator) models the landscape probabilistically and navigates cliffs

### Computational Efficiency

TPE + Hyperband Pruning provides **10-50x speedup** over exhaustive search:
- TPE focuses sampling on promising regions
- Hyperband kills failing simulations early (no point running 52 ticks if Comprador dies at tick 5)

---

## The Workflow

### Step 1: Define the Search Space

The search space specifies which parameters to tune and their valid ranges.

```python
# Example search space definition
search_space = {
    "economy.extraction_efficiency": (0.1, 0.9),      # continuous
    "economy.comprador_cut": (0.5, 1.0),              # continuous
    "economy.super_wage_rate": (0.05, 0.35),          # continuous
    "survival.default_subsistence": (0.1, 0.5),       # continuous
    "survival.steepness_k": (1.0, 10.0),              # continuous
}
```

**Guidelines:**
- Start with 3-5 parameters (high priority from `parameter-analysis.yaml`)
- Use domain knowledge to set reasonable bounds
- Avoid parameters that break invariants (e.g., probabilities must be [0,1])

### Step 2: Define the Objective Function

The objective function measures simulation quality. We optimize for the **Playable Boundary** - challenging but not impossible.

```python
def objective(trial):
    """Multi-component objective for the 'edge of chaos'."""

    # Run simulation with suggested parameters
    params = {
        "extraction_efficiency": trial.suggest_float("extraction", 0.1, 0.9),
        "comprador_cut": trial.suggest_float("comprador_cut", 0.5, 1.0),
    }

    ticks, rent_pool, consciousness_var = run_simulation(params)

    # Component 1: Survival (40% weight)
    # Longer survival = better, but cap at 52 ticks
    survival_score = min(ticks, 52) / 52

    # Component 2: Rent Pool Health (30% weight)
    # Pool should stay in "goldilocks zone" (20-80% of initial)
    pool_ratio = rent_pool / INITIAL_POOL
    pool_score = 1.0 - abs(0.5 - pool_ratio)  # Peak at 50%

    # Component 3: Drama (20% weight)
    # Higher consciousness variance = more interesting dynamics
    drama_score = min(consciousness_var, 0.5) / 0.5

    # Component 4: Near-Death Experience (10% weight)
    # Closer to death threshold = more dramatic (but not dead)
    survival_margin = min_wealth / DEATH_THRESHOLD
    nde_score = 1.0 / (1.0 + survival_margin)  # Higher when closer to death

    return 0.4 * survival_score + 0.3 * pool_score + 0.2 * drama_score + 0.1 * nde_score
```

**Key Insight:** We're NOT maximizing wealth or survival time alone. We want the simulation to be *interesting* - close to failure but not failing.

### Step 3: Run the Tuning Agent

```bash
# Run optimization study (100-500 trials recommended)
poetry run python tools/tune_agent.py \
    --n-trials 200 \
    --study-name imperial_circuit_v1 \
    --pruning hyperband

# Resume an interrupted study
poetry run python tools/tune_agent.py \
    --study-name imperial_circuit_v1 \
    --resume
```

**Expected Runtime:**
- 100 trials: ~10-20 minutes (with pruning)
- 500 trials: ~1-2 hours (with pruning)
- Without pruning: 5-10x longer

### Step 4: Analyze the Pareto Front

Launch the Optuna Dashboard for visual analysis:

```bash
optuna-dashboard sqlite:///optuna.db
```

**What to look for:**

1. **Parameter Importance Plot**
   - Which parameters have the most impact on the objective?
   - If a parameter has low importance, consider fixing it to reduce search space

2. **Slice Plots**
   - How does each parameter affect the objective?
   - Look for non-linear relationships and cliffs

3. **Pareto Front** (for multi-objective)
   - Trade-offs between competing objectives (stability vs drama)
   - Choose parameters based on desired gameplay feel

4. **Trial History**
   - How many trials were pruned early?
   - If >80% pruned, search space may be too aggressive

---

## Hyperband Pruning Rules

Babylon uses aggressive early termination to save computation:

| Condition | Tick Threshold | Action |
|-----------|----------------|--------|
| P_c wealth < 0.01 | Before tick 10 | Prune immediately |
| P_w wealth < 0.001 | Before tick 15 | Prune immediately |
| Rent pool < 10.0 | Before tick 20 | Prune immediately |

**Why these rules?**
- If the Comprador dies in 10 ticks, no parameter adjustment will save the run
- Early death indicates fundamentally broken parameter combination
- Pruning saves 80%+ of computation on doomed trials

---

## The "Cliff" Warning

Babylon's failure states are discontinuous. Small parameter changes can cause catastrophic outcomes:

```
extraction_efficiency = 0.79 -> Survives 52 ticks
extraction_efficiency = 0.80 -> Dies at tick 23
extraction_efficiency = 0.81 -> Dies at tick 8
```

**Implications:**
1. **Don't use gradient descent** - gradients don't exist at cliffs
2. **Don't trust interpolation** - the landscape is not smooth
3. **Always validate** - run full simulations on suggested optima
4. **Expect multi-modality** - there may be multiple "good" regions

---

## Tool Reference

| Tool | Purpose | When to Use |
|------|---------|-------------|
| `tune_agent.py` | Bayesian optimization | Primary tuning tool |
| `landscape_analysis.py` | 2D grid visualization | Visualize parameter interactions |
| `parameter_analysis.py trace` | Time-series analysis | Deep-dive on specific params |
| `audit_simulation.py` | Health report | Validate suggested parameters |
| `tune_parameters.py` | Manual sweep | One-off explorations |

---

## Recommended Workflow

1. **Start with audit** - Run `mise run qa:audit` to understand baseline
2. **Identify suspects** - Review `parameter-analysis.yaml` for high-priority params
3. **Run optimization** - Use `tune_agent.py` with 200+ trials
4. **Analyze results** - Use Optuna Dashboard to understand landscape
5. **Validate optima** - Run full simulations on best parameters
6. **Document findings** - Update `balance-tuning.yaml` with discoveries
7. **Iterate** - Narrow search space and repeat

---

## Appendix: Algorithm Details

### Tree-structured Parzen Estimator (TPE)

TPE models P(x|y) instead of P(y|x):
- Divides trials into "good" (y < threshold) and "bad" (y >= threshold)
- Builds separate density estimates for each group
- Samples from regions where P(good)/P(bad) is high

**Advantages:**
- Works with non-smooth objectives
- Handles mixed parameter types
- Sample-efficient (learns from all trials)

### Hyperband (Successive Halving)

Resource allocation strategy:
1. Start many trials with small budget (few ticks)
2. Evaluate and keep top performers
3. Increase budget and repeat
4. Final trials run to completion

**In Babylon terms:**
- Budget = number of simulation ticks
- Promising trials get more ticks
- Doomed trials are killed early

---

## References

- `ai-docs/parameter-analysis.yaml` - Detailed methodology specification
- `ai-docs/tooling.yaml` - Tool configuration and dependencies
- `ai-docs/balance-tuning.yaml` - Registry of discovered findings
- [Optuna Documentation](https://optuna.readthedocs.io/)
- [TPE Paper](https://papers.nips.cc/paper/2011/hash/86e8f7ab32cfd12577bc2619bc635690-Abstract.html)
