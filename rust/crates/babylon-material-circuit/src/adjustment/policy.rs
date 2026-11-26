//! Which rules a market policy asks for.

use crate::{CommodityKind, GoodId, MaterialCatalog, MaterialCircuitError, UnitId};
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

/// Whether a product is a service that the market shares in proportion: the catalog has a market policy, the
/// product is a period service, and the policy leaves it out of its order of paying (ADR312, P12; ADR325, N3).
/// In the national world that is public provision. A storable good is never one, whatever the order holds.
/// `crate::services::kind` is the one reading of a product's kind; a product the catalog does not list is not one.
pub(crate) fn is_shared_service(catalog: &MaterialCatalog, good: GoodId, unit: UnitId) -> bool {
    let Some(order) = &catalog.market_clearing else {
        return false;
    };
    matches!(
        crate::services::kind(catalog, good, unit),
        Ok(CommodityKind::PeriodService { .. })
    ) && order.place(good, unit).is_none()
}

/// The fixture of the tests that need a catalog with services: goods 1 and 2 storable, 3 and 4 period services.
#[cfg(test)]
pub(in crate::adjustment) mod fixture {
    use super::*;
    use crate::{
        CapacitySupply, CommodityDefinition, FinalDemandPrincipalId, HouseholdNeed,
        HouseholdNeedBasis, MarketClearingPolicy, MaterialCatalogDefinition, ServiceStage,
    };

    pub(in crate::adjustment) fn good(n: u8) -> GoodId {
        GoodId::from_bytes([n; 32])
    }

    pub(in crate::adjustment) fn unit(n: u8) -> UnitId {
        UnitId::from_bytes([n; 32])
    }

    /// Goods 1 and 2 are storable, goods 3 and 4 are period services.
    pub(in crate::adjustment) fn catalog_with(order: Option<&[u8]>) -> MaterialCatalog {
        let service = |n: u8| CommodityDefinition {
            good_id: good(n),
            unit_id: unit(n),
            kind: CommodityKind::PeriodService {
                stage: ServiceStage::LocalServiceProvision,
            },
        };
        let storable = |n: u8| CommodityDefinition {
            good_id: good(n),
            unit_id: unit(n),
            kind: CommodityKind::Storable { grams_per_unit: 1 },
        };
        MaterialCatalog::try_new(MaterialCatalogDefinition {
            company_portfolios: None,
            company_payouts: vec![],
            capacity_policy: CapacitySupply::FiniteSchedule,
            site_logistics_nodes: vec![],
            process_outputs: vec![],
            input_coefficients: vec![],
            labor_coefficients: vec![],
            commodities: vec![storable(1), storable(2), service(3), service(4)],
            supplier_routes: vec![],
            route_stages: vec![],
            merchants: vec![],
            handling_coefficients: vec![],
            maintenance_binding: None,
            aid_mandates: vec![],
            household_time_policy: vec![],
            service_inputs: vec![],
            household_needs: vec![HouseholdNeed {
                principal_id: FinalDemandPrincipalId::from_bytes([9; 32]),
                good_id: good(1),
                unit_id: unit(1),
                basis: HouseholdNeedBasis::Persons,
                units_per_basis: 1,
            }],
            market_clearing: order.map(|order| MarketClearingPolicy {
                paying_order: order.iter().map(|&n| (good(n), unit(n))).collect(),
                household_wants: vec![],
                plans_from_spare_money: false,
                adjustments: vec![AdjustmentRule::RestingPrice],
            }),
        })
        .expect("the fixture catalog is valid")
    }
}

#[cfg(test)]
mod tests {
    use super::fixture;
    use super::*;

    #[test]
    fn is_shared_service() {
        let shared = |catalog: &MaterialCatalog, n: u8| {
            super::is_shared_service(catalog, fixture::good(n), fixture::unit(n))
        };
        let none = fixture::catalog_with(None);
        assert!(!shared(&none, 3), "no market policy: nothing is shared");
        let ordered = fixture::catalog_with(Some(&[1, 3]));
        assert!(!shared(&ordered, 2), "a storable good outside the order");
        assert!(!shared(&ordered, 1), "a storable good in the order");
        assert!(!shared(&ordered, 3), "a service in the order");
        assert!(shared(&ordered, 4), "a service outside the order");
        assert!(!shared(&ordered, 9), "a product the catalog does not list");
    }
}
