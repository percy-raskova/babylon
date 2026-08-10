//! The per-AST-node fuel cost model (`bsl-language.rst` §3.7 / §4.5 — the
//! NORMATIVE source for every constant below; this module transcribes it, it
//! does not originate it). The determinism contract's fuel chapter is a
//! pointer to that table, deliberately: exactly one normative table exists.
//!
//! Two tiers, distinguished per §3.7: the five BASE rows are copied from the
//! design document's Phase-0 cost model and are **pinned by conformance
//! vector — revising one is a vector re-bless**; the remaining rows are the
//! language reference's completion of that model and are
//! `[draft ruling — Phase 1 review]`. Neither tier is a tuning knob.

use std::collections::HashMap;

/// The §3.7 cost table, one constant per row. Changing any constant here
/// requires the conformance-vector re-bless the reference chapter mandates
/// — never edit silently.
pub mod cost {
    /// Base row (vector-pinned): `cost(literal) = 0`. Enum-refs and field
    /// paths (qnames) share this row per the draft
    /// `cost(field path | enum-ref) = 0` — static, like a literal.
    pub const LITERAL: u64 = 0;
    /// Base row (vector-pinned): `cost(variable-ref) = 1`.
    pub const VARIABLE_REF: u64 = 1;
    /// Base row (vector-pinned): `cost(arith | cmp | bool) = 1 + Σ children`.
    /// One row, one constant — the three operator families share it.
    pub const ARITH_CMP_BOOL_BASE: u64 = 1;
    /// Base row (vector-pinned):
    /// `cost(intrinsic call) = 5 + declared_cost(callee) + Σ cost(args)`.
    pub const INTRINSIC_CALL_BASE: u64 = 5;
    /// Base row (vector-pinned):
    /// `cost(fold) = 2 + cost(query) + ceiling(query) × (cost(body) + cost(weight))`.
    pub const FOLD_BASE: u64 = 2;

    /// Draft row (Phase 1 review):
    /// `cost(if) = 1 + cost(cond) + max(cost(then), cost(else))`.
    pub const IF_BASE: u64 = 1;
    /// Draft row (Phase 1 review):
    /// `cost(exists | forall) = 2 + cost(query) + ceiling(query) × cost(body)`.
    pub const EXISTS_FORALL_BASE: u64 = 2;
    /// Draft row (Phase 1 review):
    /// `cost(query) = 1 + cost(element predicate, if any)`.
    pub const QUERY_BASE: u64 = 1;
    /// Draft row (Phase 1 review): `cost(update-op) = 1 + cost(operand)`
    /// — `add` | `sub` | `set` | `scale`.
    pub const UPDATE_OP_BASE: u64 = 1;
    /// Draft row (Phase 1 review):
    /// `cost(structural verb) = 3 + Σ cost(operands)`.
    pub const STRUCTURAL_VERB_BASE: u64 = 3;
    /// Draft row (Phase 1 review):
    /// `cost(guard) = 1 + cost(cond) + Σ cost(effect-items)`.
    pub const GUARD_BASE: u64 = 1;
    /// Draft row (R9 chapters C1/C2/C3/C9, D38): every §2.10 accessor —
    /// `field-of`, `edge-between`, `the`, `metric-of` — charges a
    /// variable-reference base of 1 plus its operands, and is **never
    /// multiplied by a ceiling**: none of them ranges over a set. That is
    /// what keeps the Power-of-10 Rule 2 claim static as the accessor set
    /// grows. `cost(the) = 1` falls out of the same row (it has no operand).
    pub const ACCESSOR_BASE: u64 = 1;
    /// Draft row (R9 chapter C5): `cost(select-max | select-min) =
    /// 2 + cost(query) + ceiling(query) × cost(score)`.
    pub const SELECTION_BASE: u64 = 2;
    /// Draft row (R9 chapter C6): `cost(for-each) =
    /// 2 + cost(query) + ceiling(query) × Σ cost(effect-items)`.
    pub const FOR_EACH_BASE: u64 = 2;
    // cost(members list) = Σ cost(members) — grouping, no base cost: no
    // constant exists on purpose, so no code path can charge one.
    // cost(domain) = 0 and cost(:as name) = 0 (§3.7, R9 C4/C8) likewise get
    // no constant: a row that charges nothing must have no charging path.
}

/// Declared per-`NodeType` / per-`EdgeType` / per-`HyperedgeType` cardinality
/// ceilings from a scenario manifest (§3.7: the bound is computed "against
/// declared cardinality ceilings, not the runtime graph"; §2.9 `manifest`).
/// Phase 1 takes this as an opaque lookup; parsing the manifest form itself
/// is Phase 2 content work.
///
/// **Two axes, since Amendment D** (§3.7 member-count axis): a hyperedge type
/// declares both how many hyperedges may exist (`:ceiling`) and how many
/// members any one of them may carry (`:max-members`). A fold over
/// `members-of` bounds against the second; without it there is no static
/// bound at all.
///
/// Keys are the enum-ref as written in content — `"NodeType/SOCIAL_CLASS"`,
/// `"EdgeType/SOLIDARITY"`, `"HyperedgeType/ECONOMIC_SECTOR"`.
#[derive(Debug, Clone, Default)]
pub struct CardinalityCeilings {
    ceilings: HashMap<String, u64>,
    max_members: HashMap<String, u64>,
}

impl CardinalityCeilings {
    /// Build from the two declared maps (`:ceiling` rows, `:max-members`
    /// values on `HyperedgeType` rows).
    #[must_use]
    pub fn new(ceilings: HashMap<String, u64>, max_members: HashMap<String, u64>) -> Self {
        Self {
            ceilings,
            max_members,
        }
    }

    /// The declared `:ceiling` of a node/edge/hyperedge type. `None` means
    /// the manifest declares no ceiling for that type — the bound checker
    /// treats that as a loud load error, never as `0` (a silent `0` would
    /// UNDER-count the bound, the exact inversion of III.11).
    #[must_use]
    pub fn ceiling(&self, graph_element_type: &str) -> Option<u64> {
        self.ceilings.get(graph_element_type).copied()
    }

    /// The declared `:max-members` of a hyperedge type. `None` for a
    /// node/edge type — and a `None` here on a `members-of` fold is
    /// `E-LOAD-042` (§2.9: `:max-members` is mandatory on a `HyperedgeType`
    /// row), never a silent zero.
    #[must_use]
    pub fn max_members(&self, hyperedge_type: &str) -> Option<u64> {
        self.max_members.get(hyperedge_type).copied()
    }
}

/// The declared `:cost` of each kernel intrinsic (§2.7 `intrinsic-decl`),
/// keyed by intrinsic name. The table's *contents* are Phase 2 work; the
/// bound checker only needs the lookup so `cost(intrinsic call)` is
/// computable from content alone. A call to a name absent here is
/// `E-LOAD-021` — never a default cost.
#[derive(Debug, Clone, Default)]
pub struct IntrinsicCosts {
    costs: HashMap<String, u64>,
}

impl IntrinsicCosts {
    /// Build from declared `(intrinsic <name> … :cost <n>)` rows.
    #[must_use]
    pub fn new(costs: HashMap<String, u64>) -> Self {
        Self { costs }
    }

    /// The declared cost of `name`, or `None` if undeclared.
    #[must_use]
    pub fn declared_cost(&self, name: &str) -> Option<u64> {
        self.costs.get(name).copied()
    }
}
