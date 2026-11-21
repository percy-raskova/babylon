use super::CommodityKind;
use super::GoodId;
use super::MaterialCircuitError;
use super::MaterialCircuitState;
use super::Result;
use super::ServiceConnection;
use super::UnitId;
use crate::MaterialCatalog;
use crate::SellerOffer;
use crate::SiteId;
use crate::{AccountId, CircuitAccounting, PricePolicy, MAX_MATERIAL_CIRCUIT_ROWS};
use std::collections::BTreeSet;

pub(crate) fn canonicalize(state: &mut MaterialCircuitState) {
    state.service_connections.sort();
    state.service_orders.sort_by_key(|r| r.order_id);
}
fn account_exists(
    catalog: &MaterialCatalog,
    state: &MaterialCircuitState,
    account: AccountId,
) -> bool {
    match account {
        AccountId::Site(id) => catalog
            .site_logistics_nodes
            .binary_search_by_key(&id, |r| r.site_id)
            .is_ok(),
        AccountId::Household(id) => state
            .final_demand_principals
            .binary_search_by_key(&id, |r| r.id)
            .is_ok(),
        _ => false,
    }
}
fn connection(
    state: &MaterialCircuitState,
    provider: SiteId,
    buyer: AccountId,
    good: GoodId,
    unit: UnitId,
) -> bool {
    state
        .service_connections
        .binary_search(&ServiceConnection {
            provider_site_id: provider,
            buyer,
            good_id: good,
            unit_id: unit,
        })
        .is_ok()
}
pub(crate) fn validate(catalog: &MaterialCatalog, state: &MaterialCircuitState) -> Result<()> {
    if state.service_connections.len() > crate::MAX_SERVICE_CONNECTIONS {
        return Err(MaterialCircuitError::RowLimit);
    }
    if catalog.commodities.len() > MAX_MATERIAL_CIRCUIT_ROWS
        || state.service_orders.len() > crate::MAX_SERVICE_ORDERS
    {
        return Err(MaterialCircuitError::RowLimit);
    }
    if state.service_connections.windows(2).any(|p| p[0] == p[1])
        || state
            .service_orders
            .windows(2)
            .any(|p| p[0].order_id == p[1].order_id)
    {
        return Err(MaterialCircuitError::DuplicateRow);
    }
    let mut providers = BTreeSet::new();
    for output in &catalog.process_outputs {
        if let Some(output_stage) = super::stage(catalog, output)? {
            if !providers.insert((output.site_id, output.good_id, output.unit_id)) {
                return Err(MaterialCircuitError::ServiceInvariant);
            }
            let start = catalog
                .input_coefficients
                .partition_point(|r| r.process_id < output.process_id);
            let end = catalog
                .input_coefficients
                .partition_point(|r| r.process_id <= output.process_id);
            for input in &catalog.input_coefficients[start..end] {
                if matches!(super::kind(catalog,input.good_id,input.unit_id)?,CommodityKind::PeriodService{stage} if stage>=output_stage)
                {
                    return Err(MaterialCircuitError::ServiceInvariant);
                }
            }
        }
    }
    for input in &catalog.input_coefficients {
        super::kind(catalog, input.good_id, input.unit_id)?;
    }
    for row in &state.inventory {
        if !matches!(
            super::kind(catalog, row.good_id, row.unit_id)?,
            CommodityKind::Storable { .. }
        ) {
            return Err(MaterialCircuitError::ServiceInvariant);
        }
    }
    for row in &state.service_connections {
        if !providers.contains(&(row.provider_site_id, row.good_id, row.unit_id))
            || !account_exists(catalog, state, row.buyer)
            || row.buyer == AccountId::Site(row.provider_site_id)
        {
            return Err(MaterialCircuitError::ServiceInvariant);
        }
    }
    for row in &state.service_orders {
        if row.quantity == 0
            || row.performance_period < state.period
            || !connection(
                state,
                row.provider_site_id,
                row.buyer,
                row.good_id,
                row.unit_id,
            )
        {
            return Err(MaterialCircuitError::ServiceInvariant);
        }
    }
    validate_policies(catalog, state, &providers)
}
fn validate_policies(
    catalog: &MaterialCatalog,
    state: &MaterialCircuitState,
    providers: &BTreeSet<(SiteId, GoodId, UnitId)>,
) -> Result<()> {
    let CircuitAccounting::Monetary(e) = &state.accounting else {
        return if state.service_orders.is_empty() {
            Ok(())
        } else {
            Err(MaterialCircuitError::MonetaryInvariant)
        };
    };
    let Some(r) = &e.recurring else { return Ok(()) };
    if catalog.service_inputs.len() > MAX_MATERIAL_CIRCUIT_ROWS {
        return Err(MaterialCircuitError::RowLimit);
    }
    let mut keys = BTreeSet::new();
    for policy in &catalog.service_inputs {
        if !keys.insert((policy.buyer_site_id, policy.good_id, policy.unit_id)) {
            return Err(MaterialCircuitError::DuplicateRow);
        }
        if policy.cash_floor.micro_units() < 0
            || policy.quantity_per_period == 0
            || !connection(
                state,
                policy.provider_site_id,
                AccountId::Site(policy.buyer_site_id),
                policy.good_id,
                policy.unit_id,
            )
            || r.offers
                .binary_search_by_key(
                    &(policy.provider_site_id, policy.good_id, policy.unit_id),
                    |o| (o.site_id, o.good_id, o.unit_id),
                )
                .is_err()
        {
            return Err(MaterialCircuitError::ServiceInvariant);
        }
    }
    refuse_unhandled_resale(catalog, &r.offers, &r.replenishment)?;
    for offer in &r.offers {
        let service = super::is_service(catalog, offer.good_id, offer.unit_id);
        match offer.pricing {
            PricePolicy::ServiceResponsive {
                minimum,
                maximum,
                step,
            } if service
                && providers.contains(&(offer.site_id, offer.good_id, offer.unit_id))
                && minimum.micro_units() > 0
                && minimum <= maximum
                && step.micro_units() > 0
                && offer.unit_price >= minimum
                && offer.unit_price <= maximum => {}
            PricePolicy::ServiceResponsive { .. } => {
                return Err(MaterialCircuitError::ServiceInvariant)
            }
            PricePolicy::Responsive { .. } if service => {
                return Err(MaterialCircuitError::ServiceInvariant)
            }
            _ => {}
        }
        if service && !providers.contains(&(offer.site_id, offer.good_id, offer.unit_id)) {
            return Err(MaterialCircuitError::ServiceInvariant);
        }
    }
    for policy in &r.production {
        // Preserve the first canonical match before later duplicate-process validation.
        let first = catalog
            .process_outputs
            .partition_point(|o| o.process_id < policy.process_id);
        let output = catalog
            .process_outputs
            .get(first)
            .filter(|o| o.process_id == policy.process_id)
            .ok_or(MaterialCircuitError::ProcessInvariant)?;
        if super::is_service(catalog, output.good_id, output.unit_id) && policy.output_buffer != 0 {
            return Err(MaterialCircuitError::ServiceInvariant);
        }
    }
    for row in &r.household_stocks {
        if !matches!(
            super::kind(catalog, row.good_id, row.unit_id)?,
            CommodityKind::Storable { .. }
        ) {
            return Err(MaterialCircuitError::ServiceInvariant);
        }
    }
    Ok(())
}

/// A merchant that buys a product of the order of paying and also offers it must have a handling
/// coefficient for it: its limit price (P5) is its own price less the wages of handling. The limit
/// is asked for a service input and for a restocking purchase alike, so both are walked.
///
/// # Errors
/// `MerchantInvariant` for such a merchant with no handling coefficient.
fn refuse_unhandled_resale(
    catalog: &MaterialCatalog,
    offers: &[SellerOffer],
    replenishment: &[crate::ReplenishmentPolicy],
) -> Result<()> {
    let Some(policy) = &catalog.market_clearing else {
        return Ok(());
    };
    let service_buys = catalog
        .service_inputs
        .iter()
        .map(|i| (i.buyer_site_id, i.good_id, i.unit_id));
    let restock_buys = replenishment
        .iter()
        .map(|r| (r.buyer_site_id, r.good_id, r.unit_id));
    for (buyer, good, unit) in service_buys.chain(restock_buys) {
        let offered = offers
            .binary_search_by_key(&(buyer, good, unit), |o| (o.site_id, o.good_id, o.unit_id))
            .is_ok();
        if offered
            && policy.place(good, unit).is_some()
            && crate::transition::merchant_admission::merchant(catalog, buyer).is_some()
        {
            crate::transition::merchant_admission::hours_per_unit(catalog, buyer, good, unit)?;
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::clearing::limit_fixture;
    use crate::{
        CapacitySupply, CommodityDefinition, CorridorId, LogisticsNodeId, MarketClearingPolicy,
        MaterialCatalogDefinition, MerchantHandling, MerchantHandlingCoefficient, MerchantRole,
        ReplenishmentPolicy, ServiceInputPolicy, ServiceStage, SiteLogisticsNode,
    };
    use babylon_kernel::currency::Currency;

    /// Site 7 is a merchant and buys the service of good 1 from site 5; it is in the order of paying.
    fn catalog(merchant: bool, ordered: bool) -> MaterialCatalog {
        build(merchant, ordered, false, service_kind())
    }

    const STORED: CommodityKind = CommodityKind::Storable { grams_per_unit: 1 };

    fn service_kind() -> CommodityKind {
        CommodityKind::PeriodService {
            stage: ServiceStage::UtilityProvision,
        }
    }

    /// The same world, with or without a handling coefficient for site 7's good 1, and with or
    /// without the service input (a restocking buyer needs none).
    fn build(
        merchant: bool,
        ordered: bool,
        coefficient: bool,
        kind: CommodityKind,
    ) -> MaterialCatalog {
        let service = matches!(kind, CommodityKind::PeriodService { .. });
        MaterialCatalog::try_new(MaterialCatalogDefinition {
            company_portfolios: None,
            company_payouts: vec![],
            capacity_policy: CapacitySupply::FiniteSchedule,
            site_logistics_nodes: [5, 7]
                .into_iter()
                .map(|n| SiteLogisticsNode {
                    site_id: limit_fixture::site(n),
                    node_id: LogisticsNodeId::from_bytes([n; 32]),
                })
                .collect(),
            process_outputs: vec![],
            input_coefficients: vec![],
            labor_coefficients: vec![],
            commodities: vec![CommodityDefinition {
                good_id: limit_fixture::good(1),
                unit_id: limit_fixture::units(),
                kind,
            }],
            supplier_routes: vec![],
            route_stages: vec![],
            merchants: if merchant {
                vec![MerchantHandling {
                    site_id: limit_fixture::site(7),
                    location: "county:26163".parse().expect("the literal parses"),
                    role: MerchantRole::Retail,
                    capacity_id: CorridorId::from_bytes([7; 32]),
                    labor_unit_id: limit_fixture::hours(),
                }]
            } else {
                vec![]
            },
            handling_coefficients: if coefficient {
                vec![MerchantHandlingCoefficient {
                    site_id: limit_fixture::site(7),
                    good_id: limit_fixture::good(1),
                    unit_id: limit_fixture::units(),
                    hours_per_unit: 1,
                }]
            } else {
                vec![]
            },
            maintenance_binding: None,
            aid_mandates: vec![],
            household_time_policy: vec![],
            service_inputs: if service {
                vec![ServiceInputPolicy {
                    buyer_site_id: limit_fixture::site(7),
                    provider_site_id: limit_fixture::site(5),
                    good_id: limit_fixture::good(1),
                    unit_id: limit_fixture::units(),
                    quantity_per_period: 1,
                    maximum_purchase: 1,
                    cash_floor: Currency::from_micro_units(0),
                }]
            } else {
                vec![]
            },
            household_needs: vec![],
            market_clearing: ordered.then(|| MarketClearingPolicy {
                plans_from_spare_money: false,
                paying_order: vec![(limit_fixture::good(1), limit_fixture::units())],
                household_wants: vec![],
            }),
        })
        .expect("the fixture catalog is valid")
    }

    #[test]
    fn a_merchant_that_resells_what_it_buys_needs_its_handling_coefficient() {
        let resale = [limit_fixture::offer(7, 1, limit_fixture::dollars(5))];
        assert_eq!(
            refuse_unhandled_resale(&catalog(true, true), &resale, &[]),
            Err(MaterialCircuitError::MerchantInvariant)
        );
        // Without its own offer, without being a merchant or outside the order of paying, the
        // limit is never asked for a handling figure.
        assert_eq!(
            refuse_unhandled_resale(
                &catalog(true, true),
                &[limit_fixture::offer(5, 1, limit_fixture::dollars(5))],
                &[]
            ),
            Ok(())
        );
        assert_eq!(
            refuse_unhandled_resale(&catalog(false, true), &resale, &[]),
            Ok(())
        );
        assert_eq!(
            refuse_unhandled_resale(&catalog(true, false), &resale, &[]),
            Ok(())
        );
    }

    #[test]
    fn a_merchant_that_restocks_what_it_offers_needs_its_handling_coefficient() {
        let resale = [limit_fixture::offer(7, 1, limit_fixture::dollars(5))];
        let restock = [ReplenishmentPolicy {
            buyer_site_id: limit_fixture::site(7),
            supplier_site_id: limit_fixture::site(5),
            good_id: limit_fixture::good(1),
            unit_id: limit_fixture::units(),
            target_stock: 3,
            maximum_purchase: 3,
            cash_floor: Currency::from_micro_units(0),
        }];
        assert_eq!(
            refuse_unhandled_resale(&build(true, true, false, STORED), &resale, &restock),
            Err(MaterialCircuitError::MerchantInvariant)
        );
        // With its coefficient, or outside the order of paying, the limit has its figure.
        assert_eq!(
            refuse_unhandled_resale(&build(true, true, true, STORED), &resale, &restock),
            Ok(())
        );
        assert_eq!(
            refuse_unhandled_resale(&build(true, false, false, STORED), &resale, &restock),
            Ok(())
        );
    }
}
