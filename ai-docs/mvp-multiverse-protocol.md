# Phase 3 MVP: The Multiverse Protocol

> **Thesis:** Graph + Math = History
>
> **Validation:** Run a Permutation Matrix of simulation scenarios and generate distinct AI narratives for each outcome.

## Status

| Attribute | Value |
|-----------|-------|
| Version | 1.0.0 |
| Created | 2025-12-09 |
| Status | ACTIVE |
| Supersedes | Any previous MVP definitions |

---

## 1. The Core Loop

The system runs a **10-tick simulation** where deterministic material conditions drive the outcome.

```
┌─────────────────────────────────────────────────────────────┐
│                    THE CORE LOOP                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ScenarioConfig ──► SimulationEngine ──► WorldState        │
│         │                   │                  │            │
│         │            [10 ticks]               │            │
│         │                   │                  │            │
│         │                   ▼                  │            │
│         │              EventBus ───────────────┤            │
│         │                   │                  │            │
│         │                   ▼                  ▼            │
│         │           NarrativeDirector ──► narrative.md      │
│         │                   │                               │
│         │                   ▼                               │
│         └───────────► log.json (math trace)                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Invariant:** The AI narrative MUST reflect the specific mathematical reality of its scenario.

---

## 2. The Permutation Matrix

### 2.1 The Three Variables

| Variable | Symbol | High State | Low State |
|----------|--------|------------|-----------|
| **Imperial Rent** | `Φ` | State can buy loyalty (bribes, welfare) | State is broke (austerity, desperation) |
| **Class Solidarity** | `σ` | Middle class aligns with proletariat | Middle class aligns with bourgeoisie |
| **Repression** | `ρ` | State can force compliance (police, military) | State apparatus is weak or fractured |

### 2.2 The 8 Scenarios

| # | Φ (Rent) | σ (Solidarity) | ρ (Repression) | Expected Outcome |
|---|----------|----------------|----------------|------------------|
| 0 | Low | Low | Low | **COLLAPSE** - State dissolves, power vacuum |
| 1 | Low | Low | High | **FASCISM** - Repression channels despair into nationalism |
| 2 | Low | High | Low | **REVOLUTION** - United working class seizes power |
| 3 | Low | High | High | **CIVIL WAR** - Armed resistance vs armed state |
| 4 | High | Low | Low | **DRIFT** - Bought off, atomized, apathetic |
| 5 | High | Low | High | **POLICE STATE** - Velvet glove over iron fist |
| 6 | High | High | Low | **REFORM** - Concessions to organized labor |
| 7 | High | High | High | **STALEMATE** - Neither side can move |

### 2.3 Scenario Configuration Schema

```python
@dataclass
class ScenarioConfig:
    """Configuration for a single simulation scenario."""

    name: str                      # e.g., "scenario_001_fascism"
    imperial_rent: float           # 0.0 (low) to 1.0 (high)
    class_solidarity: float        # 0.0 (low) to 1.0 (high)
    repression: float              # 0.0 (low) to 1.0 (high)

    # Derived from above
    @property
    def scenario_id(self) -> int:
        """Binary encoding: Φσρ -> 0-7"""
        phi = 1 if self.imperial_rent > 0.5 else 0
        sigma = 1 if self.class_solidarity > 0.5 else 0
        rho = 1 if self.repression > 0.5 else 0
        return (phi << 2) | (sigma << 1) | rho
```

---

## 3. Deliverables

### 3.1 The Artifact: `tools/run_multiverse.py`

A script that executes the full permutation matrix and generates artifacts.

**Usage:**
```bash
poetry run python tools/run_multiverse.py
```

**Output Structure:**
```
outputs/
└── run_2025-12-09T14-30-00/
    ├── manifest.json              # Run metadata, scenario configs
    ├── scenario_000_collapse/
    │   ├── config.json            # ScenarioConfig for this run
    │   ├── log.json               # Tick-by-tick mathematical state
    │   └── narrative.md           # AI-generated story
    ├── scenario_001_fascism/
    │   ├── config.json
    │   ├── log.json
    │   └── narrative.md
    ├── scenario_010_revolution/
    │   └── ...
    └── ... (8 total)
```

### 3.2 log.json Schema

```json
{
  "scenario_id": 1,
  "scenario_name": "fascism",
  "config": {
    "imperial_rent": 0.2,
    "class_solidarity": 0.2,
    "repression": 0.8
  },
  "ticks": [
    {
      "tick": 0,
      "world_state": {
        "classes": [...],
        "tensions": {...},
        "events": []
      }
    },
    {
      "tick": 1,
      "world_state": {...},
      "events": ["AGITATION_SPIKE", "REPRESSION_DEPLOYED"]
    }
  ],
  "outcome": {
    "type": "counter_revolution",
    "dominant_faction": "fascist_movement",
    "final_tick": 10
  }
}
```

### 3.3 narrative.md Requirements

**MANDATORY:** The narrative must reflect scenario-specific mathematical reality.

| Scenario | Narrative MUST Include | Narrative MUST NOT Include |
|----------|------------------------|---------------------------|
| High Repression | Police crackdowns, arrests, curfews | Peaceful transitions, open protests |
| Low Solidarity | Atomized individuals, betrayals | Mass movements, worker unity |
| High Imperial Rent | Bribes, welfare, consumerism | Economic desperation, bread riots |
| Revolution | Seizure of means of production | Gradual reform, electoral politics |

---

## 4. Architecture Updates

### 4.1 SimulationEngine Refactor

**Current:** Engine initialized with hardcoded defaults.

**Required:** Engine accepts `ScenarioConfig` for parameterized batch runs.

```python
class SimulationEngine:
    def __init__(self, config: SimulationConfig, scenario: ScenarioConfig | None = None):
        self.scenario = scenario or ScenarioConfig.default()
        self._apply_scenario_parameters()

    def _apply_scenario_parameters(self) -> None:
        """Inject scenario variables into initial WorldState."""
        # Set imperial_rent on state apparatus
        # Set solidarity edges in social graph
        # Set repression capacity on state nodes
```

**Files to Modify:**
- `src/babylon/engine/engine.py`
- `src/babylon/engine/models/config.py`

### 4.2 NarrativeDirector Async Support

**Current:** Synchronous generation causes timeouts on bulk runs.

**Required:** Async generation with batch queue.

```python
class NarrativeDirector:
    async def generate_narrative_async(
        self,
        world_state: WorldState,
        event_log: list[Event],
    ) -> str:
        """Generate narrative without blocking."""
        context = await self._retrieve_context_async(event_log)
        narrative = await self._llm.generate_async(context)
        return narrative

    async def generate_batch(
        self,
        scenarios: list[tuple[WorldState, list[Event]]],
    ) -> list[str]:
        """Generate narratives for multiple scenarios concurrently."""
        return await asyncio.gather(*[
            self.generate_narrative_async(state, events)
            for state, events in scenarios
        ])
```

**Files to Modify:**
- `src/babylon/ai/director.py`

### 4.3 Corpus Tag Distinctiveness

**Requirement:** ChromaDB must distinguish between ideological outcome types for narrative flavor.

**Tags Required:**
- `fascism` - Counter-revolutionary nationalism
- `communism` - Revolutionary proletarian victory
- `liberalism` - Reform within capitalist framework
- `collapse` - State failure, power vacuum

**Verification Query:**
```python
# These should return DISTINCT, non-overlapping chunks
canon.query("fascist victory", filter={"tags": "fascism"})
canon.query("communist revolution", filter={"tags": "communism"})
```

**Files to Verify:**
- `src/babylon/data/corpus/history/*.json` (THE_CHRONICLE)
- `src/babylon/rag/rag_pipeline.py`

---

## 5. Execution Plan

### Sprint 1: The Engine (Parameterized Scenarios)

**Goal:** SimulationEngine runs 8 distinct scenarios with mathematically divergent outcomes.

| Task | Description | Files |
|------|-------------|-------|
| 1.1 | Create `ScenarioConfig` dataclass | `src/babylon/engine/models/scenario.py` |
| 1.2 | Refactor Engine to accept scenario injection | `src/babylon/engine/engine.py` |
| 1.3 | Implement `_apply_scenario_parameters()` | `src/babylon/engine/engine.py` |
| 1.4 | Write scenario divergence tests | `tests/unit/engine/test_scenario_divergence.py` |

**Acceptance Criteria:**
- [ ] Running Scenario 0 and Scenario 7 produces different `WorldState` at tick 10
- [ ] Mathematical trace shows variable impact (e.g., high repression → more REPRESSION_DEPLOYED events)

### Sprint 2: The Narrator (RAG Integration)

**Goal:** NarrativeDirector generates scenario-appropriate narratives using RAG context.

| Task | Description | Files |
|------|-------------|-------|
| 2.1 | Add async generation methods | `src/babylon/ai/director.py` |
| 2.2 | Connect EventBus to narrative triggers | `src/babylon/engine/event_bus.py` |
| 2.3 | Implement narrative coherence validation | `tests/integration/test_narrative_coherence.py` |
| 2.4 | Add ideological tag filtering to RAG queries | `src/babylon/rag/rag_pipeline.py` |

**Acceptance Criteria:**
- [ ] "High Repression" scenario narrative mentions police/military action
- [ ] "Revolution" scenario narrative mentions worker seizure of power
- [ ] No cross-contamination (fascist narrative doesn't describe communist victory)

### Sprint 3: The Matrix (Batch Execution)

**Goal:** `run_multiverse.py` executes all 8 scenarios and generates complete artifact set.

| Task | Description | Files |
|------|-------------|-------|
| 3.1 | Create `run_multiverse.py` script | `tools/run_multiverse.py` |
| 3.2 | Implement output directory structure | `tools/run_multiverse.py` |
| 3.3 | Add manifest.json generation | `tools/run_multiverse.py` |
| 3.4 | Implement parallel scenario execution | `tools/run_multiverse.py` |
| 3.5 | Add narrative coherence spot-check | `tools/run_multiverse.py` |

**Acceptance Criteria:**
- [ ] Single command produces 8 complete scenario folders
- [ ] Each folder contains valid `config.json`, `log.json`, `narrative.md`
- [ ] Total runtime < 5 minutes (with async narrative generation)

---

## 6. De-Scoped Features

The following are explicitly OUT OF SCOPE for this MVP:

| Feature | Reason | Future Phase |
|---------|--------|--------------|
| Audio/Soundtrack | Complexity, not core thesis | Phase 4+ |
| UI Visualization | Console output sufficient for validation | Phase 4+ |
| Save/Load mid-scenario | 10 ticks is fast enough to re-run | Phase 4+ |
| Player input | Scenarios are deterministic permutations | Phase 4+ |

---

## 7. Success Metrics

### 7.1 Mathematical Divergence

**Test:** Run all 8 scenarios, compare final `WorldState`.

**Pass Criteria:** No two scenarios have identical final states.

### 7.2 Narrative Coherence

**Test:** Human review of 8 narratives for scenario-appropriate content.

**Pass Criteria:**
- 8/8 narratives correctly reflect their scenario's mathematical outcome
- 0/8 narratives contain contradictory elements (e.g., "peaceful revolution under martial law")

### 7.3 Thesis Validation

**The thesis "Graph + Math = History" is validated if:**

1. The same initial conditions always produce the same outcome (determinism)
2. Different initial conditions produce different outcomes (divergence)
3. AI narratives accurately describe the mathematical reality (coherence)

```
IF determinism AND divergence AND coherence:
    THESIS = VALIDATED
ELSE:
    THESIS = NEEDS_REVISION
```

---

## Appendix A: Scenario Binary Encoding

```
Scenario ID = (Φ << 2) | (σ << 1) | ρ

Where:
  Φ = 1 if imperial_rent > 0.5 else 0
  σ = 1 if class_solidarity > 0.5 else 0
  ρ = 1 if repression > 0.5 else 0

Examples:
  000 (0) = Low Rent, Low Solidarity, Low Repression = COLLAPSE
  001 (1) = Low Rent, Low Solidarity, High Repression = FASCISM
  010 (2) = Low Rent, High Solidarity, Low Repression = REVOLUTION
  011 (3) = Low Rent, High Solidarity, High Repression = CIVIL WAR
  100 (4) = High Rent, Low Solidarity, Low Repression = DRIFT
  101 (5) = High Rent, Low Solidarity, High Repression = POLICE STATE
  110 (6) = High Rent, High Solidarity, Low Repression = REFORM
  111 (7) = High Rent, High Solidarity, High Repression = STALEMATE
```
