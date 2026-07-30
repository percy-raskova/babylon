//! `K` — the state's CAPACITY, and its allocation (Lane A brick 3; heat
//! dossier §5.1 B and §5.3's argmax).
//!
//! **This module is where escalation stops being a threshold.** The old
//! mechanic asked "has heat crossed 0.7?" and answered with a constant,
//! which is question-begging twice over: it needs a number nobody can
//! derive, and it keys repression to accumulated conduct. Here the state has
//! a finite budget per instrument, ranks what it could do by yield per unit
//! spent, and takes candidates in that order until the budget runs out.
//! Escalation is what *happens* when a target rises in that ranking. **There
//! is no threshold constant in this file and none may be added** — a
//! reviewer finding one has found a bug.
//!
//! Two consequences fall out rather than being coded:
//!
//! - **Repression against a distributed organization declines itself.** A
//!   redundant structure divides its own yield ([`crate::exposure`]'s
//!   replaceability quotient), so it loses the ranking to a target worth
//!   more per unit spent. Nothing anywhere says "if the org is distributed,
//!   skip it."
//! - **Cheap modes beat expensive ones at equal damage.** Disinformation is
//!   the cheapest mode by state capacity and among the most expensive by
//!   movement cost — which is exactly why it dominates the historical
//!   record. That is the ranking's arithmetic, not a designer's thumb.
//!
//! **Yield is computed on `L`, never on truth.** A [`Candidate`]'s yield
//! comes from [`crate::exposure`] evaluated over a [`crate::dossier::Dossier`]
//! scope, so the state allocates against what it BELIEVES it would gain. It
//! can spend its budget badly. That is the point.
//!
//! **What a mode costs, and what modes exist, are content** (BSL rules), not
//! constants here. This module ranks and spends; it does not know what
//! `"INFILTRATION"` means.

use crate::substrate::{GraphError, NodeId};
use std::cmp::Ordering;
use std::collections::BTreeMap;

/// One action the state could take this tick, already priced.
#[derive(Debug, Clone, PartialEq)]
pub struct Candidate {
    /// Which budget this draws on — modes sharing an instrument compete for
    /// the same pool (§5.3: "modes compete for the same `K`").
    pub instrument: String,
    /// The mode being considered. Opaque here; its meaning is content.
    pub mode: String,
    /// Who it would be aimed at.
    pub target: NodeId,
    /// Expected damage, as the state BELIEVES it — normally
    /// [`crate::exposure::decapitation_value`] over a dossier scope.
    pub expected_yield: f64,
    /// Capacity units consumed if taken. Never zero (see
    /// [`Capacity::allocate`]).
    pub cost: u64,
}

/// One candidate the state actually funded.
#[derive(Debug, Clone, PartialEq)]
pub struct Allocation {
    /// The funded candidate.
    pub candidate: Candidate,
    /// Its yield per unit spent — the quantity that won it the slot.
    pub ratio: f64,
}

/// `K` — finite repressive capacity, per instrument.
///
/// Lives on the state apparatus's organization/institution nodes. Set by
/// fiscal and institutional capacity, spent by allocation, replenished
/// between ticks.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct Capacity {
    budgets: BTreeMap<String, u64>,
}

impl Capacity {
    /// A state with no capacity at all — it can see, but it cannot act.
    #[must_use]
    pub fn new() -> Self {
        Self::default()
    }

    /// Add units to one instrument's budget.
    pub fn replenish(&mut self, instrument: &str, units: u64) {
        *self.budgets.entry(instrument.to_owned()).or_insert(0) += units;
    }

    /// Units currently available to one instrument. An instrument never
    /// funded reads zero — the honest answer, since a state that has not
    /// built an apparatus does not have one.
    #[must_use]
    pub fn available(&self, instrument: &str) -> u64 {
        self.budgets.get(instrument).copied().unwrap_or(0)
    }

    /// Total unspent capacity across every instrument.
    #[must_use]
    pub fn total_available(&self) -> u64 {
        self.budgets.values().sum()
    }

    /// Rank `candidates` by yield per unit spent and fund them in that order
    /// until each instrument's budget is exhausted. **This is the escalation
    /// mechanic in full.**
    ///
    /// Spends from `self`, returning what was funded in the order it was
    /// funded (descending ratio). Candidates that do not fit are simply not
    /// returned — the state declining to act, which needs no separate
    /// representation.
    ///
    /// A candidate whose cost exceeds its instrument's *remaining* budget is
    /// skipped, and cheaper candidates behind it may still be funded. That is
    /// deliberate: a state that cannot afford the raid still runs the
    /// surveillance.
    ///
    /// **Determinism.** Ranking is a total order — ratio descending, then
    /// `(instrument, mode, target)` ascending — so a permuted candidate list
    /// produces a byte-identical allocation. Float ratios alone are only a
    /// partial order, and leaving ties to input order would put the tick hash
    /// at the mercy of iteration order upstream.
    ///
    /// # Errors
    /// Returns [`GraphError`] if any candidate has zero cost (its ratio would
    /// be infinite — a free action that always outranks everything, which is
    /// a content bug, not a strategy) or a non-finite yield.
    pub fn allocate(&mut self, candidates: &[Candidate]) -> Result<Vec<Allocation>, GraphError> {
        let mut ranked = Vec::with_capacity(candidates.len());
        for candidate in candidates {
            if candidate.cost == 0 {
                return Err(GraphError {
                    message: format!(
                        "candidate {}/{} against {:?} costs nothing — a free action \
                         outranks every priced one; price it in content",
                        candidate.instrument, candidate.mode, candidate.target
                    ),
                });
            }
            if !candidate.expected_yield.is_finite() {
                return Err(GraphError {
                    message: format!(
                        "candidate {}/{} against {:?} has a non-finite expected yield — \
                         refusing to rank it",
                        candidate.instrument, candidate.mode, candidate.target
                    ),
                });
            }
            // u64 -> f64 is exact to 2^53; costs are per-tick budget units,
            // orders of magnitude below that.
            #[allow(clippy::cast_precision_loss)]
            let ratio = candidate.expected_yield / candidate.cost as f64;
            ranked.push(Allocation {
                candidate: candidate.clone(),
                ratio,
            });
        }

        ranked.sort_by(|a, b| {
            b.ratio
                .partial_cmp(&a.ratio)
                .unwrap_or(Ordering::Equal)
                .then_with(|| a.candidate.instrument.cmp(&b.candidate.instrument))
                .then_with(|| a.candidate.mode.cmp(&b.candidate.mode))
                .then_with(|| a.candidate.target.cmp(&b.candidate.target))
        });

        let mut funded = Vec::new();
        for allocation in ranked {
            let remaining = self.available(&allocation.candidate.instrument);
            if allocation.candidate.cost <= remaining {
                self.budgets.insert(
                    allocation.candidate.instrument.clone(),
                    remaining - allocation.candidate.cost,
                );
                funded.push(allocation);
            }
        }
        Ok(funded)
    }
}

#[cfg(test)]
mod tests {
    use super::{Candidate, Capacity};
    use crate::substrate::NodeId;

    fn candidate(mode: &str, target: u64, expected_yield: f64, cost: u64) -> Candidate {
        Candidate {
            instrument: "political-police".to_owned(),
            mode: mode.to_owned(),
            target: NodeId(target),
            expected_yield,
            cost,
        }
    }

    #[test]
    fn a_state_with_no_capacity_can_see_but_not_act() {
        let mut capacity = Capacity::new();
        let funded = capacity.allocate(&[candidate("RAID", 1, 0.9, 5)]).unwrap();
        assert!(funded.is_empty(), "no budget, no action — and no error");
    }

    #[test]
    fn escalation_is_what_a_bigger_budget_buys_not_a_threshold_crossing() {
        // THE contract this module exists for. The same three candidates,
        // ranked identically, funded to different depths purely by budget.
        // Nothing in the engine asks "has heat crossed X".
        let candidates = [
            candidate("SURVEIL", 1, 0.2, 1),    // ratio 0.20
            candidate("INFILTRATE", 2, 0.9, 3), // ratio 0.30
            candidate("RAID", 3, 0.8, 8),       // ratio 0.10
        ];

        let mut lean = Capacity::new();
        lean.replenish("political-police", 3);
        let lean_funded = lean.allocate(&candidates).unwrap();
        assert_eq!(
            lean_funded
                .iter()
                .map(|a| a.candidate.mode.as_str())
                .collect::<Vec<_>>(),
            vec!["INFILTRATE"],
            "a lean state buys the best ratio it can afford"
        );

        let mut flush = Capacity::new();
        flush.replenish("political-police", 12);
        let flush_funded = flush.allocate(&candidates).unwrap();
        assert_eq!(
            flush_funded
                .iter()
                .map(|a| a.candidate.mode.as_str())
                .collect::<Vec<_>>(),
            vec!["INFILTRATE", "SURVEIL", "RAID"],
            "a flush state escalates by reaching further down the same ranking"
        );
    }

    #[test]
    fn a_redundant_target_declines_the_strike_by_itself() {
        // exposure's replaceability quotient divides a distributed org's
        // yield down; the ranking then declines it. There is no
        // "if distributed, skip" branch anywhere.
        let mut capacity = Capacity::new();
        capacity.replenish("political-police", 4);
        let funded = capacity
            .allocate(&[
                candidate("RAID", 1, 0.08, 4), // the distributed org
                candidate("RAID", 2, 0.60, 4), // the centralized one
            ])
            .unwrap();
        assert_eq!(funded.len(), 1);
        assert_eq!(
            funded[0].candidate.target,
            NodeId(2),
            "capacity went to the target worth more per unit spent"
        );
    }

    #[test]
    fn a_cheap_mode_outranks_an_expensive_one_at_higher_damage() {
        // Why disinformation dominates the historical record: cheapest by
        // state capacity, dear by movement cost. Arithmetic, not a thumb.
        let mut capacity = Capacity::new();
        capacity.replenish("political-police", 2);
        let funded = capacity
            .allocate(&[
                candidate("LIQUIDATE", 1, 0.95, 20), // ratio 0.0475
                candidate("BAD_JACKET", 2, 0.40, 1), // ratio 0.40
            ])
            .unwrap();
        assert_eq!(funded[0].candidate.mode, "BAD_JACKET");
    }

    #[test]
    fn an_unaffordable_candidate_does_not_block_a_cheaper_one_behind_it() {
        // A state that cannot afford the raid still runs the surveillance.
        let mut capacity = Capacity::new();
        capacity.replenish("political-police", 2);
        let funded = capacity
            .allocate(&[
                candidate("RAID", 1, 9.0, 10), // best ratio, unaffordable
                candidate("SURVEIL", 2, 0.5, 2),
            ])
            .unwrap();
        assert_eq!(funded.len(), 1);
        assert_eq!(funded[0].candidate.mode, "SURVEIL");
    }

    #[test]
    fn allocation_is_invariant_under_candidate_permutation() {
        // The tick-hash contract. Float ratios alone are a PARTIAL order;
        // ties broken by input order would leave the hash at the mercy of
        // upstream iteration.
        let a = candidate("RAID", 1, 0.5, 5); // ratio 0.1
        let b = candidate("RAID", 2, 0.4, 4); // ratio 0.1 — an exact tie
        let c = candidate("SURVEIL", 3, 0.2, 2); // ratio 0.1 — another
        let orders = [
            vec![a.clone(), b.clone(), c.clone()],
            vec![c.clone(), b.clone(), a.clone()],
            vec![b.clone(), a.clone(), c.clone()],
        ];
        let mut results = Vec::new();
        for order in &orders {
            let mut capacity = Capacity::new();
            capacity.replenish("political-police", 100);
            let funded = capacity.allocate(order).unwrap();
            results.push(
                funded
                    .iter()
                    .map(|x| (x.candidate.mode.clone(), x.candidate.target))
                    .collect::<Vec<_>>(),
            );
        }
        assert_eq!(results[0], results[1]);
        assert_eq!(results[1], results[2]);
    }

    #[test]
    fn spending_draws_down_the_budget_and_never_overspends() {
        let mut capacity = Capacity::new();
        capacity.replenish("political-police", 10);
        let funded = capacity
            .allocate(&[
                candidate("A", 1, 1.0, 6),
                candidate("B", 2, 1.0, 6),
                candidate("C", 3, 1.0, 4),
            ])
            .unwrap();
        assert_eq!(funded.len(), 2, "6 + 4 fits in 10; the second 6 does not");
        assert_eq!(capacity.available("political-police"), 0);
        assert_eq!(capacity.total_available(), 0);
    }

    #[test]
    fn instruments_hold_separate_budgets() {
        let mut capacity = Capacity::new();
        capacity.replenish("political-police", 5);
        capacity.replenish("courts", 5);
        let funded = capacity
            .allocate(&[
                Candidate {
                    instrument: "courts".to_owned(),
                    mode: "PROSECUTE".to_owned(),
                    target: NodeId(1),
                    expected_yield: 0.5,
                    cost: 5,
                },
                candidate("RAID", 2, 0.5, 5),
            ])
            .unwrap();
        assert_eq!(funded.len(), 2, "each drew on its own pool");
        assert_eq!(capacity.available("courts"), 0);
        assert_eq!(capacity.available("political-police"), 0);
    }

    #[test]
    fn a_free_action_is_loud_never_infinitely_attractive() {
        let mut capacity = Capacity::new();
        capacity.replenish("political-police", 10);
        let err = capacity
            .allocate(&[candidate("FREE", 1, 0.5, 0)])
            .unwrap_err();
        assert!(err.message.contains("costs nothing"), "{}", err.message);
    }

    #[test]
    fn a_non_finite_yield_is_refused_not_ranked() {
        let mut capacity = Capacity::new();
        capacity.replenish("political-police", 10);
        for bad in [f64::NAN, f64::INFINITY] {
            let err = capacity
                .allocate(&[candidate("RAID", 1, bad, 2)])
                .unwrap_err();
            assert!(err.message.contains("non-finite"), "{}", err.message);
        }
    }
}
