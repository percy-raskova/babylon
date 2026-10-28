//! Current native service receipt partitions; state-dependent causality stays in the engine.
use super::monetary_receipt;
use super::MaterialWorldError;
use super::ReceiptCursor;
use babylon_kernel::currency::Currency;
use babylon_material_circuit::FinalDemandPrincipalId;
use babylon_material_circuit::GoodId;
use babylon_material_circuit::HouseholdServiceReceipt;
use babylon_material_circuit::MaterialCircuitError;
use babylon_material_circuit::OrderId;
use babylon_material_circuit::ProcessId;
use babylon_material_circuit::ServiceMarketReceipt;
use babylon_material_circuit::ServiceOutputReceipt;
use babylon_material_circuit::ServicePerformanceReceipt;
use babylon_material_circuit::ServicePriceDecision;
use babylon_material_circuit::SiteId;
use babylon_material_circuit::UnitId;
pub(super) const PERFORMANCE_BYTES: usize = 233;
pub(super) const HOUSEHOLD_BYTES: usize = 144;
pub(super) const MARKET_BYTES: usize = 233;
pub(super) const OUTPUT_BYTES: usize = 192;
fn refusal(_: MaterialCircuitError) -> MaterialWorldError {
    MaterialWorldError::Wire
}
fn period(actual: u64, tick: u64) -> Result<(), MaterialWorldError> {
    if actual == tick && tick > 0 {
        Ok(())
    } else {
        Err(MaterialWorldError::Wire)
    }
}
fn amount(c: &mut ReceiptCursor<'_>) -> Result<Currency, MaterialWorldError> {
    Ok(Currency::from_micro_units(i128::from_be_bytes(c.take()?)))
}
pub(super) fn validate_order(
    performance: &[ServicePerformanceReceipt],
    households: &[HouseholdServiceReceipt],
    markets: &[ServiceMarketReceipt],
    outputs: &[ServiceOutputReceipt],
) -> Result<(), MaterialWorldError> {
    if performance
        .windows(2)
        .any(|r| r[0].order_id >= r[1].order_id)
        || households.windows(2).any(|r| {
            (r[0].principal_id, r[0].good_id, r[0].unit_id)
                >= (r[1].principal_id, r[1].good_id, r[1].unit_id)
        })
        || markets.windows(2).any(|r| {
            (r[0].site_id, r[0].good_id, r[0].unit_id) >= (r[1].site_id, r[1].good_id, r[1].unit_id)
        })
        || outputs.windows(2).any(|r| {
            (r[0].site_id, r[0].good_id, r[0].unit_id) >= (r[1].site_id, r[1].good_id, r[1].unit_id)
        })
    {
        return Err(MaterialWorldError::Wire);
    }
    Ok(())
}
pub(super) fn encode_performance(
    rows: &[ServicePerformanceReceipt],
    tick: u64,
    b: &mut Vec<u8>,
) -> Result<(), MaterialWorldError> {
    for r in rows {
        r.validate().map_err(refusal)?;
        period(r.period, tick)?;
        b.extend_from_slice(&r.period.to_be_bytes());
        b.extend_from_slice(&r.order_id.as_bytes());
        b.extend_from_slice(&r.provider_site_id.as_bytes());
        let (tag, id) = monetary_receipt::account_parts(r.buyer);
        b.push(tag);
        b.extend_from_slice(&id);
        b.extend_from_slice(&r.good_id.as_bytes());
        b.extend_from_slice(&r.unit_id.as_bytes());
        for q in [
            r.requested_quantity,
            r.admitted_quantity,
            r.performed_quantity,
            r.used_quantity,
            r.unused_quantity,
            r.expired_quantity,
        ] {
            b.extend_from_slice(&q.to_be_bytes());
        }
        b.extend_from_slice(&r.unit_price.micro_units().to_be_bytes());
    }
    Ok(())
}
pub(super) fn decode_performance(
    c: &mut ReceiptCursor<'_>,
    tick: u64,
) -> Result<ServicePerformanceReceipt, MaterialWorldError> {
    let period_value = c.u64()?;
    let order_id = OrderId::from_bytes(c.take()?);
    let provider_site_id = SiteId::from_bytes(c.take()?);
    let [tag] = c.take()?;
    let buyer = monetary_receipt::account(tag, c.take()?)?;
    let r = ServicePerformanceReceipt {
        period: period_value,
        order_id,
        provider_site_id,
        buyer,
        good_id: GoodId::from_bytes(c.take()?),
        unit_id: UnitId::from_bytes(c.take()?),
        requested_quantity: c.u64()?,
        admitted_quantity: c.u64()?,
        performed_quantity: c.u64()?,
        used_quantity: c.u64()?,
        unused_quantity: c.u64()?,
        expired_quantity: c.u64()?,
        unit_price: amount(c)?,
    };
    r.validate().map_err(refusal)?;
    period(r.period, tick)?;
    Ok(r)
}
pub(super) fn encode_households(
    rows: &[HouseholdServiceReceipt],
    tick: u64,
    b: &mut Vec<u8>,
) -> Result<(), MaterialWorldError> {
    for r in rows {
        r.validate().map_err(refusal)?;
        period(r.period, tick)?;
        b.extend_from_slice(&r.period.to_be_bytes());
        for id in [
            r.principal_id.as_bytes(),
            r.good_id.as_bytes(),
            r.unit_id.as_bytes(),
        ] {
            b.extend_from_slice(&id);
        }
        for q in [
            r.required_quantity,
            r.performed_quantity,
            r.satisfied_quantity,
            r.unmet_quantity,
            r.unused_quantity,
        ] {
            b.extend_from_slice(&q.to_be_bytes());
        }
    }
    Ok(())
}
pub(super) fn decode_household(
    c: &mut ReceiptCursor<'_>,
    tick: u64,
) -> Result<HouseholdServiceReceipt, MaterialWorldError> {
    let r = HouseholdServiceReceipt {
        period: c.u64()?,
        principal_id: FinalDemandPrincipalId::from_bytes(c.take()?),
        good_id: GoodId::from_bytes(c.take()?),
        unit_id: UnitId::from_bytes(c.take()?),
        required_quantity: c.u64()?,
        performed_quantity: c.u64()?,
        satisfied_quantity: c.u64()?,
        unmet_quantity: c.u64()?,
        unused_quantity: c.u64()?,
    };
    r.validate().map_err(refusal)?;
    period(r.period, tick)?;
    Ok(r)
}
pub(super) fn encode_markets(
    rows: &[ServiceMarketReceipt],
    tick: u64,
    b: &mut Vec<u8>,
) -> Result<(), MaterialWorldError> {
    for r in rows {
        r.validate().map_err(refusal)?;
        period(r.period, tick)?;
        b.extend_from_slice(&r.period.to_be_bytes());
        b.extend_from_slice(&r.next_period.to_be_bytes());
        for id in [
            r.process_id.as_bytes(),
            r.site_id.as_bytes(),
            r.good_id.as_bytes(),
            r.unit_id.as_bytes(),
        ] {
            b.extend_from_slice(&id);
        }
        for q in [
            r.requested_quantity,
            r.admitted_quantity,
            r.performed_quantity,
            r.available_capacity,
        ] {
            b.extend_from_slice(&q.to_be_bytes());
        }
        for m in [r.direct_cost, r.old_price, r.next_price] {
            b.extend_from_slice(&m.micro_units().to_be_bytes());
        }
        b.push(r.reason as u8);
        b.extend_from_slice(&r.planned_quantity.to_be_bytes());
    }
    Ok(())
}
pub(super) fn decode_market(
    c: &mut ReceiptCursor<'_>,
    tick: u64,
) -> Result<ServiceMarketReceipt, MaterialWorldError> {
    let r = ServiceMarketReceipt {
        period: c.u64()?,
        next_period: c.u64()?,
        process_id: ProcessId::from_bytes(c.take()?),
        site_id: SiteId::from_bytes(c.take()?),
        good_id: GoodId::from_bytes(c.take()?),
        unit_id: UnitId::from_bytes(c.take()?),
        requested_quantity: c.u64()?,
        admitted_quantity: c.u64()?,
        performed_quantity: c.u64()?,
        available_capacity: c.u64()?,
        direct_cost: amount(c)?,
        old_price: amount(c)?,
        next_price: amount(c)?,
        reason: match c.take::<1>()? {
            [1] => ServicePriceDecision::Fixed,
            [2] => ServicePriceDecision::Hold,
            [3] => ServicePriceDecision::FundedUnmet,
            [4] => ServicePriceDecision::CostPressure,
            [5] => ServicePriceDecision::SpareCapacity,
            _ => return Err(MaterialWorldError::Wire),
        },
        planned_quantity: c.u64()?,
    };
    r.validate().map_err(refusal)?;
    period(r.period, tick)?;
    Ok(r)
}

pub(super) fn encode_outputs(
    rows: &[ServiceOutputReceipt],
    tick: u64,
    b: &mut Vec<u8>,
) -> Result<(), MaterialWorldError> {
    for r in rows {
        r.validate().map_err(refusal)?;
        period(r.period, tick)?;
        b.extend_from_slice(&r.period.to_be_bytes());
        for id in [
            r.process_id.as_bytes(),
            r.site_id.as_bytes(),
            r.good_id.as_bytes(),
            r.unit_id.as_bytes(),
        ] {
            b.extend_from_slice(&id);
        }
        for q in [
            r.produced_quantity,
            r.allocated_quantity,
            r.expired_quantity,
        ] {
            b.extend_from_slice(&q.to_be_bytes());
        }
        for m in [r.direct_cost, r.expired_cost] {
            b.extend_from_slice(&m.micro_units().to_be_bytes());
        }
    }
    Ok(())
}
pub(super) fn decode_output(
    c: &mut ReceiptCursor<'_>,
    tick: u64,
) -> Result<ServiceOutputReceipt, MaterialWorldError> {
    let r = ServiceOutputReceipt {
        period: c.u64()?,
        process_id: ProcessId::from_bytes(c.take()?),
        site_id: SiteId::from_bytes(c.take()?),
        good_id: GoodId::from_bytes(c.take()?),
        unit_id: UnitId::from_bytes(c.take()?),
        produced_quantity: c.u64()?,
        allocated_quantity: c.u64()?,
        expired_quantity: c.u64()?,
        direct_cost: amount(c)?,
        expired_cost: amount(c)?,
    };
    r.validate().map_err(refusal)?;
    period(r.period, tick)?;
    Ok(r)
}

#[cfg(test)]
mod tests {
    use super::*;
    use babylon_material_circuit::AccountId;
    #[test]
    fn all_service_encoders_roundtrip_their_current_typed_receipts() {
        let money = Currency::from_micro_units;
        let performance = ServicePerformanceReceipt {
            period: 1,
            order_id: OrderId::from_bytes([1; 32]),
            provider_site_id: SiteId::from_bytes([1; 32]),
            buyer: AccountId::Site(SiteId::from_bytes([2; 32])),
            good_id: GoodId::from_bytes([3; 32]),
            unit_id: UnitId::from_bytes([4; 32]),
            requested_quantity: 3,
            admitted_quantity: 3,
            performed_quantity: 2,
            used_quantity: 1,
            unused_quantity: 1,
            expired_quantity: 1,
            unit_price: money(2),
        };
        let household = HouseholdServiceReceipt {
            period: 1,
            principal_id: FinalDemandPrincipalId::from_bytes([1; 32]),
            good_id: performance.good_id,
            unit_id: performance.unit_id,
            required_quantity: 2,
            performed_quantity: 3,
            satisfied_quantity: 2,
            unmet_quantity: 0,
            unused_quantity: 1,
        };
        let market = ServiceMarketReceipt {
            period: 1,
            next_period: 2,
            process_id: ProcessId::from_bytes([1; 32]),
            site_id: performance.provider_site_id,
            good_id: performance.good_id,
            unit_id: performance.unit_id,
            requested_quantity: 3,
            admitted_quantity: 3,
            performed_quantity: 2,
            available_capacity: 4,
            direct_cost: money(10),
            old_price: money(2),
            next_price: money(3),
            reason: ServicePriceDecision::FundedUnmet,
            planned_quantity: 3,
        };
        let output = ServiceOutputReceipt {
            period: 1,
            process_id: market.process_id,
            site_id: market.site_id,
            good_id: market.good_id,
            unit_id: market.unit_id,
            produced_quantity: 4,
            allocated_quantity: 2,
            expired_quantity: 2,
            direct_cost: money(10),
            expired_cost: money(6),
        };
        let mut bytes = vec![];
        encode_performance(std::slice::from_ref(&performance), 1, &mut bytes)
            .expect("the fixture value encodes to its canonical bytes");
        encode_households(std::slice::from_ref(&household), 1, &mut bytes)
            .expect("the fixture value encodes to its canonical bytes");
        encode_markets(std::slice::from_ref(&market), 1, &mut bytes)
            .expect("the fixture value encodes to its canonical bytes");
        encode_outputs(std::slice::from_ref(&output), 1, &mut bytes)
            .expect("the fixture value encodes to its canonical bytes");
        assert_eq!(
            bytes.len(),
            PERFORMANCE_BYTES + HOUSEHOLD_BYTES + MARKET_BYTES + OUTPUT_BYTES
        );
        let mut cursor = ReceiptCursor {
            bytes: &bytes,
            position: 0,
        };
        assert_eq!(
            decode_performance(&mut cursor, 1)
                .expect("the canonical bytes decode into the declared type"),
            performance
        );
        assert_eq!(
            decode_household(&mut cursor, 1)
                .expect("the canonical bytes decode into the declared type"),
            household
        );
        assert_eq!(
            decode_market(&mut cursor, 1)
                .expect("the canonical bytes decode into the declared type"),
            market
        );
        assert_eq!(
            decode_output(&mut cursor, 1)
                .expect("the canonical bytes decode into the declared type"),
            output
        );
        assert_eq!(cursor.position, bytes.len());
    }
}

#[cfg(test)]
mod engine_test {
    use super::*;
    use babylon_material_circuit;
    use babylon_material_circuit::AccountId;
    use babylon_material_circuit::AidBook;
    use babylon_material_circuit::CapacityReservations;
    use babylon_material_circuit::CapacityRow;
    use babylon_material_circuit::CapacitySupply;
    use babylon_material_circuit::CashAccount;
    use babylon_material_circuit::CircuitAccounting;
    use babylon_material_circuit::CommodityDefinition;
    use babylon_material_circuit::CommodityKind;
    use babylon_material_circuit::EmploymentTerms;
    use babylon_material_circuit::FinalDemandPrincipal;
    use babylon_material_circuit::FinancialInstitutions;
    use babylon_material_circuit::HistoricalCostBook;
    use babylon_material_circuit::HouseholdTimeAccounting;
    use babylon_material_circuit::LaborCapacityRow;
    use babylon_material_circuit::LaborCoefficient;
    use babylon_material_circuit::LogisticsNodeId;
    use babylon_material_circuit::MaterialCatalog;
    use babylon_material_circuit::MaterialCircuitState;
    use babylon_material_circuit::MaterialPurchase;
    use babylon_material_circuit::MonetaryBook;
    use babylon_material_circuit::MonetaryCircuit;
    use babylon_material_circuit::ProcessOutput;
    use babylon_material_circuit::ProductionCommitment;
    use babylon_material_circuit::ServiceConnection;
    use babylon_material_circuit::ServiceOrder;
    use babylon_material_circuit::ServiceStage;
    use babylon_material_circuit::SiteLogisticsNode;
    #[allow(
        clippy::too_many_lines,
        reason = "one fixture assembles the whole conserved circuit so the decoder test starts from a real state"
    )]
    fn opening() -> (MaterialCatalog, MaterialCircuitState) {
        let site = SiteId::from_bytes([1; 32]);
        let person = FinalDemandPrincipalId::from_bytes([2; 32]);
        let good = GoodId::from_bytes([3; 32]);
        let unit = UnitId::from_bytes([4; 32]);
        let process = ProcessId::from_bytes([5; 32]);
        let labor = UnitId::from_bytes([6; 32]);
        let money = Currency::from_micro_units;
        let book = MonetaryBook::open(vec![
            CashAccount {
                id: AccountId::Site(site),
                cash: money(2),
            },
            CashAccount {
                id: AccountId::Household(person),
                cash: money(3),
            },
        ])
        .expect("the fixture opens the authored source");
        let costs = HistoricalCostBook::open(&book, vec![], vec![], vec![], vec![])
            .expect("the fixture opens the authored source");
        let catalog = MaterialCatalog::try_new(MaterialCatalog {
            capacity_policy: CapacitySupply::FiniteSchedule,
            site_logistics_nodes: vec![SiteLogisticsNode {
                site_id: site,
                node_id: LogisticsNodeId::from_bytes([1; 32]),
            }],
            process_outputs: vec![ProcessOutput {
                process_id: process,
                site_id: site,
                good_id: good,
                unit_id: unit,
                quantity_per_batch: 2,
            }],
            input_coefficients: vec![],
            labor_coefficients: vec![LaborCoefficient {
                process_id: process,
                unit_id: labor,
                quantity_per_batch: 1,
            }],
            commodities: vec![CommodityDefinition {
                good_id: good,
                unit_id: unit,
                kind: CommodityKind::PeriodService {
                    stage: ServiceStage::UtilityProvision,
                },
            }],
            supplier_routes: vec![],
            route_stages: vec![],
            merchants: vec![],
            handling_coefficients: vec![],
            maintenance_binding: None,
            aid_mandates: vec![],
            household_time_policy: vec![],
            service_inputs: vec![],
            household_needs: vec![],
            catalog_digest: babylon_material_circuit::UNSEALED_CATALOG_DIGEST,
        })
        .expect("the fixture catalog canonicalizes");
        let state = MaterialCircuitState {
            period: 1,
            accounting: CircuitAccounting::Monetary(Box::new(MonetaryCircuit {
                aid: AidBook::default(),
                household_time: HouseholdTimeAccounting::NotModeled,
                financial: FinancialInstitutions::empty(),
                member_labor: vec![babylon_material_circuit::MemberLaborCapacityRow {
                    member_id: babylon_material_circuit::StaffingMemberId::from_bytes(
                        site.as_bytes(),
                    ),
                    period: 1,
                    available_hours: 1,
                }],
                book,
                costs,
                recurring: None,
                employment: vec![EmploymentTerms {
                    member_id: babylon_material_circuit::StaffingMemberId::from_bytes(
                        (site).as_bytes(),
                    ),
                    site_id: site,
                    unit_id: labor,
                    payee: person,
                    compensation: babylon_material_circuit::LaborCompensation::Wage(money(1)),
                }],
            })),
            service_connections: vec![ServiceConnection {
                provider_site_id: site,
                buyer: AccountId::Household(person),
                good_id: good,
                unit_id: unit,
            }],
            service_orders: vec![],
            route_stage_capacities: vec![],
            inventory: vec![],
            orders: vec![],
            freight: vec![],
            corridor_capacities: vec![],
            capacities: vec![CapacityRow {
                process_id: process,
                site_id: site,
                period: 1,
                available_batches: 1,
            }],
            labor: vec![LaborCapacityRow {
                site_id: site,
                unit_id: labor,
                period: 1,
                available: 1,
            }],
            production_commitments: vec![ProductionCommitment {
                process_id: process,
                site_id: site,
                period: 1,
                planned_batches: 1,
            }],
            final_demand_principals: vec![FinalDemandPrincipal {
                id: person,
                location: "county:26163"
                    .parse()
                    .expect("the authored literal parses as the declared type"),
            }],
            final_demand_orders: vec![],
            maintenance_service: None,
            capacity_reservations: CapacityReservations::default(),
        };
        (catalog, state)
    }
    #[test]
    fn actual_service_close_roundtrips_the_complete_receipt_envelope() {
        let (catalog, state) = opening();
        let connection = &state.service_connections[0];
        let (state, _) = babylon_material_circuit::admit_material_purchase(
            &catalog,
            &state,
            MaterialPurchase::Service(ServiceOrder {
                order_id: OrderId::from_bytes([9; 32]),
                performance_period: 1,
                provider_site_id: connection.provider_site_id,
                buyer: connection.buyer,
                good_id: connection.good_id,
                unit_id: connection.unit_id,
                quantity: 1,
            }),
            Currency::from_micro_units(2),
        )
        .expect("the fixture admits the authored purchase");
        let result = babylon_material_circuit::advance_material_circuit(&catalog, &state)
            .expect("the authored material state advances one period");
        let bytes = super::super::encode_material_receipts(1, &result)
            .expect("the fixture value encodes to its canonical bytes");
        let decoded = super::super::decode_material_receipts(&bytes)
            .expect("the canonical bytes decode into the declared type");
        assert_eq!(decoded.service_performance, result.service_performance);
        assert_eq!(decoded.service_outputs, result.service_outputs);
        assert_eq!(decoded.income, result.income);
        assert_eq!(decoded.money_transfers, result.money_transfers);
        assert_eq!(decoded.labor_use, result.labor_use);
        assert_eq!(
            (
                decoded.service_outputs[0].produced_quantity,
                decoded.service_outputs[0].allocated_quantity,
                decoded.service_outputs[0].expired_cost.micro_units()
            ),
            (2, 1, 1)
        );
        assert!(result.state.inventory.is_empty() && result.state.freight.is_empty());
    }
}
