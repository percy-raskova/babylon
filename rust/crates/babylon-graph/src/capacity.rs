//! `K` — an organization's CAPACITY, and its allocation (Lane A brick 3;
//! heat dossier §5.1 B and §5.3's argmax).
//!
//! **Capacity belongs to organizations** (Director ruling 2026-07-30,
//! ADR184). "The state" is not a node type: [`crate::substrate`]'s
//! vocabulary has `organization` (the thing that acts), `institution` (what
//! houses it) and `sovereign` (what claims territory). A budget with no
//! owner would make the state a force of nature rather than a set of
//! organizations with means — and the earlier draft of this module said "the
//! state" eleven times while [`Candidate`] carried a target and no actor,
//! which is that error written into a type.
//!
//! **The consequence is that repression and revolutionary action are the
//! same allocation.** A union local and a political police force both rank
//! what they could do by yield per unit spent and fund down the list until
//! the money runs out. Neither gets a privileged mechanic; the historical
//! asymmetry is the *size* of the budget and nothing else. The class
//! difference lives entirely in **replenishment** — tax and tribute on one
//! side, dues and expropriation on the other — which is why the frozen
//! Python engine grew `StateFinance` and `RevolutionaryFinance` as two names
//! for one shape (ADR184; do not transcribe the duplicate).
//!
//! **This module is where escalation stops being a threshold.** The old
//! mechanic asked "has heat crossed 0.7?" and answered with a constant,
//! which is question-begging twice over: it needs a number nobody can
//! derive, and it keys repression to accumulated conduct. Here an actor has
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
//! scope, so an actor allocates against what it BELIEVES it would gain. It
//! can spend its budget badly. That is the point, and it holds for both
//! sides: a movement misreads the state's apparatus exactly as the state
//! misreads a movement.
//!
//! **What a mode costs, and what modes exist, are content** (BSL rules), not
//! constants here. This module ranks and spends; it does not know what
//! `"INFILTRATION"` means.

use crate::substrate::{GraphError, NodeId};
use std::cmp::Ordering;
use std::collections::BTreeMap;

/// One action an organization could take this tick, already priced.
#[derive(Debug, Clone, PartialEq)]
pub struct Candidate {
    /// The organization proposing it — whose budget pays, and whose
    /// [`crate::dossier::Dossier`] the yield was computed over.
    ///
    /// A candidate without an actor would be an action nobody is taking;
    /// [`Capacity::allocate`] rejects one whose actor is not the budget's
    /// owner rather than quietly spending someone else's means.
    pub actor: NodeId,
    /// Which budget this draws on — modes sharing an instrument compete for
    /// the same pool (§5.3: "modes compete for the same `K`").
    pub instrument: String,
    /// The mode being considered. Opaque here; its meaning is content.
    pub mode: String,
    /// Who it would be aimed at.
    pub target: NodeId,
    /// Expected damage, as the actor BELIEVES it — normally
    /// [`crate::exposure::decapitation_value`] over a dossier scope.
    pub expected_yield: f64,
    /// Capacity units consumed if taken. Never zero (see
    /// [`Capacity::allocate`]).
    pub cost: u64,
}

/// One candidate the actor actually funded.
#[derive(Debug, Clone, PartialEq)]
pub struct Allocation {
    /// The funded candidate.
    pub candidate: Candidate,
    /// Its yield per unit spent — the quantity that won it the slot.
    pub ratio: f64,
}

/// `K` — one organization's finite capacity to act, per instrument.
///
/// Owned by the organization node whose means it is. Set by fiscal and
/// institutional capacity, spent by allocation, replenished between ticks —
/// and **replenishment is where the class difference lives**, not here.
/// This type cannot tell a police budget from a strike fund.
///
/// No `Default`: a capacity with no owner is the unowned budget ADR184
/// rules out.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Capacity {
    owner: NodeId,
    budgets: BTreeMap<String, u64>,
}

impl Capacity {
    /// An organization with no capacity at all — it can see, but it cannot
    /// act.
    #[must_use]
    pub fn new(owner: NodeId) -> Self {
        Self {
            owner,
            budgets: BTreeMap::new(),
        }
    }

    /// The organization whose means these are.
    #[must_use]
    pub fn owner(&self) -> NodeId {
        self.owner
    }

    /// Add units to one instrument's budget.
    pub fn replenish(&mut self, instrument: &str, units: u64) {
        *self.budgets.entry(instrument.to_owned()).or_insert(0) += units;
    }

    /// Units currently available to one instrument. An instrument never
    /// funded reads zero — the honest answer, since an organization that has
    /// not built an apparatus does not have one.
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
    /// returned — the actor declining to act, which needs no separate
    /// representation.
    ///
    /// A candidate whose cost exceeds its instrument's *remaining* budget is
    /// skipped, and cheaper candidates behind it may still be funded. That is
    /// deliberate: an actor that cannot afford the raid still runs the
    /// surveillance.
    ///
    /// **Determinism.** Ranking is a total order — ratio descending, then
    /// `(instrument, mode, target, cost, expected_yield)` ascending — so a
    /// permuted candidate list produces a byte-identical allocation. Float
    /// ratios alone are only a partial order, and leaving ties to input order
    /// would put the tick hash at the mercy of iteration order upstream. The
    /// chain runs to the last field that can differ: two candidates equal on
    /// all of them are indistinguishable, so their order cannot be observed.
    ///
    /// # Errors
    /// Returns [`GraphError`] if any candidate has zero cost (its ratio would
    /// be infinite — a free action that always outranks everything, which is
    /// a content bug, not a strategy), a non-finite yield, or an actor other
    /// than this budget's owner.
    pub fn allocate(&mut self, candidates: &[Candidate]) -> Result<Vec<Allocation>, GraphError> {
        let mut ranked = Vec::with_capacity(candidates.len());
        for candidate in candidates {
            if candidate.actor != self.owner {
                return Err(GraphError {
                    message: format!(
                        "candidate {}/{} is proposed by {:?} but this capacity \
                         belongs to {:?} — an organization spends its own means",
                        candidate.instrument, candidate.mode, candidate.actor, self.owner
                    ),
                });
            }
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
                // The same action against the same target at two prices ties
                // on every field above. Cheaper first, then `total_cmp` as
                // the closing tiebreak — a genuine total order on f64,
                // correct for negative yields where a bit-pattern compare
                // would invert. Without these two the sort is stable-but-
                // input-ordered and the tick hash inherits upstream
                // iteration order.
                .then_with(|| a.candidate.cost.cmp(&b.candidate.cost))
                .then_with(|| {
                    a.candidate
                        .expected_yield
                        .total_cmp(&b.candidate.expected_yield)
                })
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

    /// The organization whose budget every test below spends.
    const ACTOR: NodeId = NodeId(7);

    fn candidate(mode: &str, target: u64, expected_yield: f64, cost: u64) -> Candidate {
        Candidate {
            actor: ACTOR,
            instrument: "political-police".to_owned(),
            mode: mode.to_owned(),
            target: NodeId(target),
            expected_yield,
            cost,
        }
    }

    #[test]
    fn an_organization_spends_only_its_own_means() {
        // The ADR184 invariant. Silently funding another organization's
        // candidate would make the budget a shared pool — which is the
        // unowned "state capacity" this module was rebuilt to remove.
        let mut capacity = Capacity::new(ACTOR);
        capacity.replenish("political-police", 100);
        let mut someone_else = candidate("RAID", 1, 0.9, 5);
        someone_else.actor = NodeId(999);
        let err = capacity.allocate(&[someone_else]).unwrap_err();
        assert!(
            err.message.contains("spends its own means"),
            "{}",
            err.message
        );
    }

    #[test]
    fn the_same_allocation_serves_a_movement_and_a_police_force() {
        // ADR184's substantive claim: nothing in this type distinguishes
        // repression from revolutionary action. Identical ranking, identical
        // budget, identical outcome — the only difference between the two
        // actors is which node owns the capacity and where it was
        // replenished from, neither of which the allocator can see.
        let police = NodeId(7);
        let local = NodeId(8);
        let priced = |actor: NodeId, mode: &str, target: u64, y: f64, cost: u64| Candidate {
            actor,
            instrument: "cadre".to_owned(),
            mode: mode.to_owned(),
            target: NodeId(target),
            expected_yield: y,
            cost,
        };

        let mut state_side = Capacity::new(police);
        state_side.replenish("cadre", 4);
        let state_funded = state_side
            .allocate(&[
                priced(police, "INFILTRATE", 1, 0.9, 3),
                priced(police, "RAID", 2, 0.8, 8),
            ])
            .unwrap();

        let mut movement_side = Capacity::new(local);
        movement_side.replenish("cadre", 4);
        let movement_funded = movement_side
            .allocate(&[
                priced(local, "INFILTRATE", 1, 0.9, 3),
                priced(local, "RAID", 2, 0.8, 8),
            ])
            .unwrap();

        assert_eq!(
            state_funded
                .iter()
                .map(|a| (a.candidate.mode.as_str(), a.candidate.cost))
                .collect::<Vec<_>>(),
            movement_funded
                .iter()
                .map(|a| (a.candidate.mode.as_str(), a.candidate.cost))
                .collect::<Vec<_>>(),
            "the allocator cannot tell a police budget from a strike fund"
        );
        assert_eq!(state_side.owner(), police);
        assert_eq!(movement_side.owner(), local);
    }

    #[test]
    fn an_organization_with_no_capacity_can_see_but_not_act() {
        let mut capacity = Capacity::new(ACTOR);
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

        let mut lean = Capacity::new(ACTOR);
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

        let mut flush = Capacity::new(ACTOR);
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
        let mut capacity = Capacity::new(ACTOR);
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
        let mut capacity = Capacity::new(ACTOR);
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
        let mut capacity = Capacity::new(ACTOR);
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
            let mut capacity = Capacity::new(ACTOR);
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
    fn candidates_differing_only_in_price_still_rank_deterministically() {
        // The guard above cannot reach this case: its candidates differ in
        // mode or target, which resolves every tie before the comparator
        // runs out of fields. Two candidates sharing (instrument, mode,
        // target) at an equal ratio tie on ALL of them, and a stable sort
        // then falls back to input order — putting the tick hash at the
        // mercy of whatever produced the list. The same action against the
        // same target at two prices is a content shape nothing forbids.
        let dear = candidate("RAID", 1, 0.5, 5); // ratio 0.1
        let cheap = candidate("RAID", 1, 0.4, 4); // ratio 0.1, same triple
        let orders = [
            vec![dear.clone(), cheap.clone()],
            vec![cheap.clone(), dear.clone()],
        ];
        let mut results = Vec::new();
        for order in &orders {
            let mut capacity = Capacity::new(ACTOR);
            capacity.replenish("political-police", 7); // room for exactly one
            let funded = capacity.allocate(order).unwrap();
            results.push(funded.iter().map(|a| a.candidate.cost).collect::<Vec<_>>());
        }
        assert_eq!(
            results[0], results[1],
            "input order must not decide which of two equally-rated \
             candidates the state can afford"
        );
    }

    #[test]
    fn spending_draws_down_the_budget_and_never_overspends() {
        let mut capacity = Capacity::new(ACTOR);
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
        let mut capacity = Capacity::new(ACTOR);
        capacity.replenish("political-police", 5);
        capacity.replenish("courts", 5);
        let funded = capacity
            .allocate(&[
                Candidate {
                    actor: ACTOR,
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
        let mut capacity = Capacity::new(ACTOR);
        capacity.replenish("political-police", 10);
        let err = capacity
            .allocate(&[candidate("FREE", 1, 0.5, 0)])
            .unwrap_err();
        assert!(err.message.contains("costs nothing"), "{}", err.message);
    }

    #[test]
    fn a_non_finite_yield_is_refused_not_ranked() {
        let mut capacity = Capacity::new(ACTOR);
        capacity.replenish("political-police", 10);
        for bad in [f64::NAN, f64::INFINITY] {
            let err = capacity
                .allocate(&[candidate("RAID", 1, bad, 2)])
                .unwrap_err();
            assert!(err.message.contains("non-finite"), "{}", err.message);
        }
    }
}
