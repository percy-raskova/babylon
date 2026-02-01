# Babylon: Transformation Problem Resolution & Sprint Guidance

**Status:** Theoretical decisions finalized. Ready for implementation planning.

---

## The Problem We Resolved

The original sprint roadmap identified the "Value-to-Price Transformation Operator" as a blocker. This framing was incorrect. The transformation problem—how labor values convert to market prices—is a 150-year theoretical dispute with incompatible resolutions carrying different political implications.

We evaluated four candidate frameworks:

| Framework | Core Claim | Political Alignment with MLM-TW |
|-----------|-----------|--------------------------------|
| Bortkiewicz-Sweezy | Simultaneous equilibrium | Hostile. Eliminates crisis theory via Okishio theorem. Associated with analytical Marxism's rejection of dependency theory. |
| TSSI | Temporal, single-system | Neutral. Rehabilitates Marx but methodologically nationalist—doesn't foreground core-periphery. |
| New Interpretation | V defined ex post from actual wages | Hostile. Makes super-exploitation theoretically incoherent. If V = actual wage, you can't be paid below V. |
| Shaikh Iterative | Convergence procedure | Neutral. Technical reconciliation, not a political framework. |

**None of these are the theoretical home of MLM-TW.**

---

## The Chosen Methodology: Emmanuel-Amin Synthesis

Babylon's theoretical commitments follow Emmanuel's "Unequal Exchange" (1969) and Amin's extensions. The key insight: wage differentials are the *cause* of unequal exchange, not the result. When commodities trade at world prices, more peripheral labor-hours exchange for fewer core labor-hours. This is structural extraction, not market imperfection.

### Implementation Consequences

We do not need a general Value-to-Price Transformation Operator. We need to track **divergences**:

1. **Imperial Rent (Φ):** Defined as `Φ = W_core - V_core`, where `V_core` is derived from Dept IIa reproduction requirements (what the wage *would* need to be absent imperial extraction). This is computable from existing tensor infrastructure.

2. **Super-Exploitation Rate:** Peripheral wages *below* local reproduction requirements. The gap Amin identifies. Also derivable from Dept IIa data.

3. **Temporal Dynamics:** Use TSSI's temporal structure for crisis/accumulation modeling. Values from period t inform dynamics in period t+1. No simultaneity.

**The transformation "problem" dissolves because we're not deriving general prices from values—we're measuring the gaps that MLM-TW identifies as the locus of imperial extraction.**

---

## Revised Sprint Guidance

### Sprint 1 (Material Base) — Approved as Written
The "Real Wage Deflator" using Dept IIa is correct. One clarification: we're calibrating to BLS price data as empirical ground truth, not deriving prices from values. This is intentional—the simulation asks whether *deviations* from reproduction requirements predict political outcomes.

### Sprint 2 (Exploitation Logic) — Requires Revision

**Remove:** "Value-Price Divergence calculated via the Transformation Operator"

**Replace with:**
- Imperial Rent calculation: `Φ = W_actual - V_reproduction` where V_reproduction comes from Dept IIa tensor contraction
- TRPF calculated from organic composition as specified, but profit rates need *not* equalize (TSSI permits persistent differentials)

**Revise "Profit Equalization Test":** The test should verify that Wayne and Oakland counties show *different* profit rate dynamics consistent with their industrial composition—not convergence to equilibrium.

### Sprint 3 (Superstructure) — Needs Theoretical Justification

The "ideology as 1-form" and "metric tensor for repression" formulations are flagged for review. Before implementation, we need to establish:
- What invariance properties justify differential geometric language?
- Is this notation doing mathematical work or merely aesthetic?

**Do not block Sprint 1-2 on Sprint 3 resolution.** Sprint 3 can be descoped to simpler representations if the geometric formalism doesn't earn its keep.

---

## Role Clarification

**Theoretical decisions (Percy + Claude):** Transformation methodology, what quantities mean, political alignment of frameworks.

**Project management (Gemini):** Sprint sequencing, test coverage strategy, dependency tracking, scope control, timeline estimation.

The "blocker" is resolved. Gemini should proceed with Sprint 1 implementation planning using Sub-Option A2 (real FIPS data in test fixtures). The transformation operator is not a prerequisite—the divergence-tracking approach sidesteps it.

---

## Key Quantities to Track (Implementation Reference)

| Quantity | Definition | Data Source | Political Meaning |
|----------|-----------|-------------|-------------------|
| V_reproduction | Dept IIa value required to reproduce labor power locally | BEA + QCEW tensor | Material floor for wages |
| W_actual | Observed wages | QCEW | What workers actually receive |
| Φ (Imperial Rent) | W_actual - V_reproduction (when positive) | Derived | Core workers' share of imperial extraction |
| Super-exploitation | V_reproduction - W_actual (when positive) | Derived | Peripheral workers paid below reproduction |
| r (Profit Rate) | s / (c + v) from local tensor | Derived | TRPF dynamics |

---

## Open Questions (Not Blockers)

1. How to model the *transfer mechanism* for imperial rent at the world-system level (beyond Detroit test case)
2. Whether Shaikh's iterative procedure is useful for calibration even if not theoretically central
3. Sprint 3 geometric formalism—defer until Sprint 2 complete
