//! Which rules a market policy asks for.

use crate::MaterialCircuitError;
use std::mem;

/// One rule of ADR314 measured in rounds eight to ten, asked for by a market policy.
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)]
pub enum AdjustmentRule {
    /// A workplace asks for hands only for the hours its inputs and its money can use.
    HiringWithinMeans,
    /// People not needed look for work at the other workplaces of their place (A14).
    SeekingInPlace,
    /// A workplace that cannot pay the hours its plan asked keeps only those it paid (A17).
    StopWithoutPay,
    /// A workplace that employs nobody and offered nothing holds its price.
    RestingPrice,
    /// Its owner restarts a stopped workplace with the owner's own money (A17, A19, ADR318 L1),
    /// for `outlay_periods` periods of one batch's cost a batch.
    OwnerRestart {
        /// How many periods of one batch's cost the owner puts in.
        outlay_periods: u64,
    },
    /// A goods price steps down when goods beyond the buffer went unsold, under its cost if it must (A1;
    /// ADR321, K1).
    GoodsStepDown,
}

const NEEDS_NONE: &[AdjustmentRule] = &[];
const NEEDS_STOP: &[AdjustmentRule] = &[AdjustmentRule::SeekingInPlace];
const NEEDS_RESTART: &[AdjustmentRule] = &[
    AdjustmentRule::HiringWithinMeans,
    AdjustmentRule::StopWithoutPay,
    AdjustmentRule::RestingPrice,
];

impl AdjustmentRule {
    /// The rule's tag in the catalog bytes: 1 to 6 in the order above.
    pub(crate) const fn tag(self) -> u8 {
        match self {
            Self::HiringWithinMeans => 1,
            Self::SeekingInPlace => 2,
            Self::StopWithoutPay => 3,
            Self::RestingPrice => 4,
            Self::OwnerRestart { .. } => 5,
            Self::GoodsStepDown => 6,
        }
    }

    /// The rules this one needs, in the order above: `StopWithoutPay` needs `SeekingInPlace`; `OwnerRestart`
    /// needs `HiringWithinMeans`, `StopWithoutPay` and `RestingPrice`; the others need none. The one table that
    /// `refuse_combinations` and the runner read.
    ///
    /// A need is direct: the restart needs the stop rule, which needs the seekers in turn.
    #[must_use]
    pub const fn needs(self) -> &'static [AdjustmentRule] {
        match self {
            Self::StopWithoutPay => NEEDS_STOP,
            Self::OwnerRestart { .. } => NEEDS_RESTART,
            Self::HiringWithinMeans
            | Self::SeekingInPlace
            | Self::RestingPrice
            | Self::GoodsStepDown => NEEDS_NONE,
        }
    }
}

/// Whether `rules` asks for a rule of this kind.
pub(crate) fn asks(rules: &[AdjustmentRule], rule: AdjustmentRule) -> bool {
    rules
        .iter()
        .any(|row| mem::discriminant(row) == mem::discriminant(&rule))
}

/// The restart's periods of outlay, when the list asks for the restart.
pub(crate) fn restart_outlay_periods(rules: &[AdjustmentRule]) -> Option<u64> {
    rules.iter().find_map(|rule| match rule {
        AdjustmentRule::OwnerRestart { outlay_periods } => Some(*outlay_periods),
        _ => None,
    })
}

/// The refusals of a list of rules that hold whatever is built: the list is in the order of
/// `AdjustmentRule`, no kind twice, every rule has the rules it needs, and the restart has a period of outlay.
///
/// # Errors
/// `MarketClearingInvariant` for the first refusal.
pub(crate) fn refuse_combinations(rules: &[AdjustmentRule]) -> Result<(), MaterialCircuitError> {
    let in_order = rules.windows(2).all(|pair| pair[0].tag() < pair[1].tag());
    let needs_met = rules
        .iter()
        .all(|rule| rule.needs().iter().all(|need| asks(rules, *need)));
    if !in_order || !needs_met || restart_outlay_periods(rules) == Some(0) {
        return Err(MaterialCircuitError::MarketClearingInvariant);
    }
    Ok(())
}

/// Admission's last word on the rules: the combinations. Every rule is built.
///
/// # Errors
/// `MarketClearingInvariant`.
pub(crate) fn admit(rules: &[AdjustmentRule]) -> Result<(), MaterialCircuitError> {
    refuse_combinations(rules)
}
