//! Independent admission controls for measured household policy and claim families.
use crate::EconomicLocation;
use crate::ForeignCounterpart;
use babylon_material_circuit::AccountId;
use babylon_material_circuit::CashAccount;
use babylon_material_circuit::CommodityDefinition;
use babylon_material_circuit::CommodityKind;
use babylon_material_circuit::EquityCarryingValue;
use babylon_material_circuit::FinalDemandPrincipal;
use babylon_material_circuit::FinalDemandPrincipalId;
use babylon_material_circuit::FinancialInstitutions;
use babylon_material_circuit::GoodId;
use babylon_material_circuit::HistoricalCostBook;
use babylon_material_circuit::HouseholdCohort;
use babylon_material_circuit::HouseholdKind;
use babylon_material_circuit::HouseholdNeed;
use babylon_material_circuit::HouseholdNeedBasis;
use babylon_material_circuit::HouseholdPurchasePolicy;
use babylon_material_circuit::InstitutionLocation;
use babylon_material_circuit::LaborCoefficient;
use babylon_material_circuit::LogisticsNodeId;
use babylon_material_circuit::MaterialCatalog;
use babylon_material_circuit::MaterialCircuitError;
use babylon_material_circuit::MaterialCircuitState;
use babylon_material_circuit::MonetaryBook;
use babylon_material_circuit::OwnershipClaim;
use babylon_material_circuit::PricePolicy;
use babylon_material_circuit::ProcessId;
use babylon_material_circuit::ProcessOutput;
use babylon_material_circuit::ProductionDemandPolicy;
use babylon_material_circuit::PublicAccountId;
use babylon_material_circuit::RecurringEconomy;
use babylon_material_circuit::SellerOffer;
use babylon_material_circuit::ServiceConnection;
use babylon_material_circuit::ServiceStage;
use babylon_material_circuit::SiteId;
use babylon_material_circuit::SiteLogisticsNode;
use babylon_material_circuit::TaxBasis;
use babylon_material_circuit::TaxPolicy;
use babylon_material_circuit::UnitId;

const POLICY_LIMIT: usize = 131_072;

fn identity(n: usize) -> [u8; 32] {
    let mut id = [0; 32];
    id[24..].copy_from_slice(
        &u64::try_from(n)
            .expect("the fixture value fits the target range")
            .to_be_bytes(),
    );
    id
}
fn resident(n: usize) -> FinalDemandPrincipalId {
    FinalDemandPrincipalId::from_bytes(identity(n))
}
fn workplace(n: usize) -> SiteId {
    SiteId::from_bytes(identity(n))
}
fn public_id(n: usize) -> PublicAccountId {
    PublicAccountId::from_bytes(identity(n))
}
fn empty_accounts(
    sites: usize,
    households: usize,
    publics: usize,
) -> (MaterialCatalog, MaterialCircuitState) {
    let (catalog, mut state) = crate::opening([0; 5]);
    let mut catalog = catalog;
    catalog.site_logistics_nodes = (0..sites)
        .map(|n| SiteLogisticsNode {
            site_id: workplace(n),
            node_id: LogisticsNodeId::from_bytes(identity(n)),
        })
        .collect();
    state.final_demand_principals = (0..households)
        .map(|n| FinalDemandPrincipal {
            id: resident(n),
            location: EconomicLocation::Foreign(ForeignCounterpart::Canada),
        })
        .collect();
    let ids = (0..sites)
        .map(|n| AccountId::Site(workplace(n)))
        .chain((0..households).map(|n| AccountId::Household(resident(n))))
        .chain((0..publics).map(|n| AccountId::Public(public_id(n))));
    let e = crate::economy_mut(&mut state);
    e.book = MonetaryBook::open(
        ids.map(|id| CashAccount {
            id,
            cash: crate::money(0),
        })
        .collect(),
    )
    .expect("the fixture opens the authored source");
    e.costs = HistoricalCostBook::open(&e.book, vec![], vec![], vec![], vec![])
        .expect("the fixture opens the authored source");
    e.financial = FinancialInstitutions::empty();
    e.financial.locations = (0..publics)
        .map(|n| InstitutionLocation {
            account: AccountId::Public(public_id(n)),
            location: EconomicLocation::Foreign(ForeignCounterpart::Canada),
        })
        .collect();
    catalog.catalog_digest = [0; 32];
    let catalog = MaterialCatalog::try_new(catalog).expect("the fixture catalog is valid");
    (catalog, state)
}
fn canonical_roundtrip(
    catalog: &MaterialCatalog,
    state: &MaterialCircuitState,
) -> MaterialCircuitState {
    let bytes = babylon_material_circuit::encode_material_circuit_state(catalog, state)
        .expect("all admitted rows must encode");
    let restored = babylon_material_circuit::decode_material_circuit_state(catalog, &bytes)
        .expect("all encoded rows must decode");
    assert_eq!(
        babylon_material_circuit::encode_material_circuit_state(catalog, &restored)
            .expect("the canonical material state encodes"),
        bytes
    );
    assert_eq!(
        crate::economy(&restored)
            .book
            .total_cash_and_reserves()
            .expect("the fixture book totals without overflow"),
        crate::money(0)
    );
    assert_eq!(crate::economy(&restored).employment.len(), 0);
    assert_eq!(crate::economy(&restored).member_labor.len(), 0);
    restored
}
fn service_needs() -> (MaterialCatalog, MaterialCircuitState) {
    // Four distinct native services per explicit one-person household. No stock,
    // cash, employment, service orders or performed work is created by admission.
    let (mut catalog, mut state) = empty_accounts(1, POLICY_LIMIT / 4, 0);
    let unit = UnitId::from_bytes(identity(1));
    let hours = UnitId::from_bytes(identity(2));
    let mut rows = RecurringEconomy {
        service_inputs: vec![],
        households: vec![],
        household_stocks: vec![],
        household_needs: vec![],
        household_purchases: vec![],
        offers: vec![],
        replenishment: vec![],
        production: vec![],
        attendance: vec![],
        last_household_admission_period: 0,
        last_household_consumption_period: 0,
    };
    for n in 0..POLICY_LIMIT / 4 {
        rows.households.push(HouseholdCohort {
            kind: HouseholdKind::Ordinary,
            principal_id: resident(n),
            households: 1,
            persons: 1,
        });
        for commodity in 0..4 {
            let good = GoodId::from_bytes(identity(commodity));
            rows.household_needs.push(HouseholdNeed {
                principal_id: resident(n),
                good_id: good,
                unit_id: unit,
                basis: HouseholdNeedBasis::Persons,
                units_per_basis: 1,
            });
            rows.household_purchases.push(HouseholdPurchasePolicy {
                principal_id: resident(n),
                retailer_site_id: workplace(0),
                good_id: good,
                unit_id: unit,
                target_closing_stock: 0,
                maximum_purchase: 1,
                enabled: true,
            });
            state.service_connections.push(ServiceConnection {
                provider_site_id: workplace(0),
                buyer: AccountId::Household(resident(n)),
                good_id: good,
                unit_id: unit,
            });
        }
    }
    declare_services(&mut catalog, &mut rows, unit, hours);
    catalog.household_needs.clone_from(&rows.household_needs);
    catalog.catalog_digest = [0; 32];
    let catalog = MaterialCatalog::try_new(catalog).expect("the fixture catalog is valid");
    crate::economy_mut(&mut state).recurring = Some(Box::new(rows));
    (catalog, state)
}
fn declare_services(
    catalog: &mut MaterialCatalog,
    rows: &mut RecurringEconomy,
    unit: UnitId,
    hours: UnitId,
) {
    for commodity in 0..4 {
        let good = GoodId::from_bytes(identity(commodity));
        let process = ProcessId::from_bytes(identity(commodity));
        catalog.commodities.push(CommodityDefinition {
            good_id: good,
            unit_id: unit,
            kind: CommodityKind::PeriodService {
                stage: ServiceStage::UtilityProvision,
            },
        });
        catalog.process_outputs.push(ProcessOutput {
            process_id: process,
            site_id: workplace(0),
            good_id: good,
            unit_id: unit,
            quantity_per_batch: 1,
        });
        catalog.labor_coefficients.push(LaborCoefficient {
            process_id: process,
            unit_id: hours,
            quantity_per_batch: 1,
        });
        rows.production.push(ProductionDemandPolicy {
            process_id: process,
            site_id: workplace(0),
            output_buffer: 0,
            planned_batches: 0,
        });
        rows.offers.push(SellerOffer {
            site_id: workplace(0),
            good_id: good,
            unit_id: unit,
            unit_price: crate::money(1),
            pricing: PricePolicy::Fixed,
        });
    }
}
#[test]
fn household_policy_bound_preserves_every_need_and_purchase_and_checks_the_tail() {
    let (catalog, state) = service_needs();
    let restored = canonical_roundtrip(&catalog, &state);
    let rows = crate::economy(&restored)
        .recurring
        .as_ref()
        .expect("the fixture set the optional field before this read");
    assert_eq!(rows.household_needs.len(), POLICY_LIMIT);
    assert_eq!(rows.household_purchases.len(), POLICY_LIMIT);
    assert_eq!(
        rows.households.iter().map(|r| r.persons).sum::<u64>(),
        32_768
    );
    assert_eq!(
        rows.household_needs
            .last()
            .expect("the fixture sequence is non-empty")
            .principal_id,
        resident(32_767)
    );
    for purchases in [false, true] {
        let mut duplicate = restored.clone();
        let r = crate::economy_mut(&mut duplicate)
            .recurring
            .as_mut()
            .expect("the fixture set the optional field before this borrow");
        if purchases {
            r.household_purchases[POLICY_LIMIT - 1] = r.household_purchases[0].clone();
        } else {
            r.household_needs[POLICY_LIMIT - 1] = r.household_needs[0].clone();
        }
        assert_eq!(
            babylon_material_circuit::encode_material_circuit_state(&catalog, &duplicate),
            Err(MaterialCircuitError::DuplicateRow)
        );
        let mut excess = restored.clone();
        let r = crate::economy_mut(&mut excess)
            .recurring
            .as_mut()
            .expect("the fixture set the optional field before this borrow");
        if purchases {
            r.household_purchases.push(r.household_purchases[0].clone());
        } else {
            r.household_needs.push(r.household_needs[0].clone());
        }
        assert_eq!(
            babylon_material_circuit::encode_material_circuit_state(&catalog, &excess),
            Err(MaterialCircuitError::RowLimit)
        );
    }
    let mut disconnected = restored;
    disconnected.service_connections.pop();
    assert_eq!(
        babylon_material_circuit::encode_material_circuit_state(&catalog, &disconnected),
        Err(MaterialCircuitError::ServiceInvariant)
    );
}
#[test]
fn household_ownership_bound_preserves_all_claims_and_exact_equity_keys() {
    let (catalog, mut state) = empty_accounts(2, POLICY_LIMIT / 2, 0);
    let e = crate::economy_mut(&mut state);
    e.financial.ownership = (0..2)
        .flat_map(|issuer| {
            (0..POLICY_LIMIT / 2).map(move |n| OwnershipClaim {
                issuer_site_id: workplace(issuer),
                beneficiary: AccountId::Household(resident(n)),
                shares: 1,
            })
        })
        .collect();
    let equity = e
        .financial
        .ownership
        .iter()
        .map(|r| EquityCarryingValue {
            owner: r.beneficiary,
            issuer_site_id: r.issuer_site_id,
            amount: crate::money(0),
        })
        .collect();
    e.costs = HistoricalCostBook::open(&e.book, vec![], vec![], equity, vec![])
        .expect("every captured owner claim has a carrying row");
    let restored = canonical_roundtrip(&catalog, &state);
    let e = crate::economy(&restored);
    assert_eq!(e.financial.ownership.len(), POLICY_LIMIT);
    assert_eq!(e.costs.snapshot().equity.len(), POLICY_LIMIT);
    let mut duplicate = restored.clone();
    let rows = &mut crate::economy_mut(&mut duplicate).financial.ownership;
    rows[POLICY_LIMIT - 1] = rows[0].clone();
    assert_eq!(
        babylon_material_circuit::encode_material_circuit_state(&catalog, &duplicate),
        Err(MaterialCircuitError::DuplicateRow)
    );
    let mut excess = restored.clone();
    let rows = &mut crate::economy_mut(&mut excess).financial.ownership;
    rows.push(rows[0].clone());
    assert_eq!(
        babylon_material_circuit::encode_material_circuit_state(&catalog, &excess),
        Err(MaterialCircuitError::RowLimit)
    );
    let mut snapshot = e.costs.snapshot();
    snapshot.equity[POLICY_LIMIT - 1] = snapshot.equity[0].clone();
    assert_eq!(
        HistoricalCostBook::from_snapshot(snapshot),
        Err(MaterialCircuitError::DuplicateRow)
    );
    let mut snapshot = e.costs.snapshot();
    snapshot.equity.push(snapshot.equity[0].clone());
    assert_eq!(
        HistoricalCostBook::from_snapshot(snapshot),
        Err(MaterialCircuitError::RowLimit)
    );
}
#[test]
fn household_tax_bound_is_one_policy_per_account_including_the_last_payer() {
    // Two captured public recipients can tax each other; no payer taxes itself.
    let (catalog, mut state) = empty_accounts(65_534, 65_536, 2);
    let e = crate::economy_mut(&mut state);
    e.financial.taxes = e
        .book
        .snapshot()
        .accounts
        .iter()
        .map(|r| TaxPolicy {
            payer: r.id,
            public_recipient: public_id(usize::from(r.id == AccountId::Public(public_id(0)))),
            basis: TaxBasis::PositiveOperatingIncome,
            rate_bps: 1000,
            cash_floor: crate::money(0),
        })
        .collect();
    assert_eq!(e.financial.taxes.len(), POLICY_LIMIT);
    let restored = canonical_roundtrip(&catalog, &state);
    assert_eq!(
        crate::economy(&restored).financial.taxes.len(),
        POLICY_LIMIT
    );
    let mut duplicate = restored.clone();
    let rows = &mut crate::economy_mut(&mut duplicate).financial.taxes;
    rows[POLICY_LIMIT - 1] = rows[0].clone();
    assert_eq!(
        babylon_material_circuit::encode_material_circuit_state(&catalog, &duplicate),
        Err(MaterialCircuitError::DuplicateRow)
    );
    let mut excess = restored;
    let rows = &mut crate::economy_mut(&mut excess).financial.taxes;
    rows.push(rows[0].clone());
    assert_eq!(
        babylon_material_circuit::encode_material_circuit_state(&catalog, &excess),
        Err(MaterialCircuitError::RowLimit)
    );
}
