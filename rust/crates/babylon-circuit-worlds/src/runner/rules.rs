//! The rules of a run: which are on, from which period, and why one was not turned on.

use crate::WorldError;
use babylon_material_circuit::AdjustmentRule;
use std::error::Error;
use std::fmt::{Display, Formatter, Result as FmtResult};

/// A rule of the run and the first period closed under it.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct RuleOn {
    /// The rule.
    pub rule: AdjustmentRule,
    /// The first period closed under it.
    pub from: u64,
}

/// Where a rule's switch stands for the next period.
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum Switch {
    /// On from `from`; it holds until the run is started over.
    On {
        /// The first period closed under the rule.
        from: u64,
    },
    /// Off; `turn_on` would turn it on from the next period.
    Ready,
    /// Off; it waits for these rules, in the order of `AdjustmentRule`.
    Waits {
        /// The rules it needs that are not on.
        needs: Vec<AdjustmentRule>,
    },
}

/// Why a rule was not turned on. Nothing changes then.
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum RuleError {
    /// The run is stopped.
    Stopped,
    /// A rule of this kind is on already.
    AlreadyOn {
        /// The rule that is on.
        rule: AdjustmentRule,
        /// The first period closed under it.
        from: u64,
    },
    /// A rule it needs is not on.
    Waits {
        /// The rule that was asked for.
        rule: AdjustmentRule,
        /// The rules it needs that are not on.
        needs: Vec<AdjustmentRule>,
    },
    /// The engine's admission refused the catalog of the next period with the rule.
    Refused {
        /// The rule that was asked for.
        rule: AdjustmentRule,
        /// The refusal.
        error: WorldError,
    },
}

/// The rule's name, as the scene and the refusals say it.
#[must_use]
pub const fn rule_name(rule: AdjustmentRule) -> &'static str {
    match rule {
        AdjustmentRule::HiringWithinMeans => "A bound on hiring",
        AdjustmentRule::SeekingInPlace => "People look for work in their place",
        AdjustmentRule::StopWithoutPay => "No money, no work",
        AdjustmentRule::RestingPrice => "A resting price",
        AdjustmentRule::OwnerRestart { .. } => "The owner restarts a stopped workplace",
        AdjustmentRule::GoodsStepDown => "A goods price steps down",
    }
}

fn lower_name(rule: AdjustmentRule) -> String {
    rule_name(rule).to_lowercase()
}

impl Display for RuleError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FmtResult {
        match self {
            Self::Stopped => write!(f, "the run is stopped"),
            Self::AlreadyOn { rule, from } => write!(
                f,
                "{} is on from period {from} and holds until you start over",
                rule_name(*rule)
            ),
            Self::Waits { rule, needs } => {
                let needs: Vec<String> = needs.iter().map(|need| lower_name(*need)).collect();
                write!(f, "{} waits for {}", rule_name(*rule), needs.join(" and "))
            }
            Self::Refused { rule, error } => match error {
                WorldError::Engine(inner) => {
                    write!(f, "the engine refused {}: {inner:?}", lower_name(*rule))
                }
                other => write!(f, "the engine refused {}: {other}", lower_name(*rule)),
            },
        }
    }
}

impl Error for RuleError {}
