//! Designed finite controls for independently bounded source and resource families.
use crate::CapacityRow;
use crate::CommodityDefinition;
use crate::CorridorCapacity;
use crate::CorridorId;
use crate::GoodId;
use crate::InputOutputCoefficient;
use crate::InventoryRow;
use crate::LaborCapacityRow;
use crate::LaborCoefficient;
use crate::LogisticsNodeId;
use crate::MaterialCatalog;
use crate::MaterialCircuitState;
use crate::ProcessId;
use crate::ProcessOutput;
use crate::SiteId;
use crate::SiteLogisticsNode;
use crate::StaffingPolicy;
use crate::StaffingPoolBinding;
use crate::StaffingPoolId;
use crate::StaffingPoolState;
use crate::StaffingState;
use crate::StaffingWorkSource;
use babylon_material_circuit::MaterialCatalogDefinition;
use babylon_material_circuit::{
    MerchantHandling, MerchantHandlingCoefficient, MerchantRole, MAX_INPUT_COEFFICIENTS,
    MAX_INVENTORY_ROWS, MAX_MATERIAL_CIRCUIT_ROWS, MAX_STAFFING_WORK_SOURCES,
};
use std::collections::{BTreeMap, BTreeSet};

const FORMER_FAMILY_LIMIT: usize = 65_536;
const RESOURCE_PROCESSES: usize = 32_769;

fn identity(index: usize) -> [u8; 32] {
    let mut bytes = [0; 32];
    bytes[24..].copy_from_slice(
        &u64::try_from(index)
            .expect("the fixture value fits the target range")
            .to_be_bytes(),
    );
    bytes
}

fn empty_production() -> (MaterialCatalogDefinition, MaterialCircuitState) {
    let (catalog, mut state) = crate::opening();
    let mut catalog = catalog.into_definition();
    catalog.process_outputs.clear();
    catalog.input_coefficients.clear();
    catalog.labor_coefficients.clear();
    state.capacities.clear();
    state.inventory.clear();
    state.labor.clear();
    (catalog, state)
}

fn append_process(
    catalog: &mut MaterialCatalogDefinition,
    state: &mut MaterialCircuitState,
    index: usize,
    owner: SiteId,
    inputs: &[GoodId],
    batches: u64,
) {
    let id = ProcessId::from_bytes(identity(index));
    catalog.process_outputs.push(ProcessOutput {
        process_id: id,
        site_id: owner,
        good_id: crate::good(2),
        unit_id: crate::unit(2),
        quantity_per_batch: 1,
    });
    for input in inputs {
        catalog.input_coefficients.push(InputOutputCoefficient {
            process_id: id,
            good_id: *input,
            unit_id: crate::unit(2),
            quantity_per_batch: 1,
        });
    }
    catalog.labor_coefficients.push(LaborCoefficient {
        process_id: id,
        unit_id: crate::unit(1),
        quantity_per_batch: 1,
    });
    state.capacities.push(CapacityRow {
        process_id: id,
        site_id: owner,
        period: 2,
        available_batches: batches,
    });
}

fn labor_at(owner: SiteId, period: u64, available: u64) -> LaborCapacityRow {
    LaborCapacityRow {
        site_id: owner,
        unit_id: crate::unit(1),
        period,
        available,
    }
}

fn stock_at(owner: SiteId, input: GoodId, quantity: u64) -> InventoryRow {
    InventoryRow {
        site_id: owner,
        good_id: input,
        unit_id: crate::unit(2),
        quantity,
    }
}

fn source_ownership_case() -> (MaterialCatalog, MaterialCircuitState, StaffingState) {
    let (mut catalog, mut state) = empty_production();
    let mut sources = [Vec::new(), Vec::new()];
    for index in 0..FORMER_FAMILY_LIMIT {
        let pool = usize::from(index >= FORMER_FAMILY_LIMIT / 2);
        let owner =
            crate::site(u8::try_from(pool + 1).expect("the fixture value fits the target range"));
        let batches = u64::from(index == 0 || index == FORMER_FAMILY_LIMIT - 1);
        append_process(
            &mut catalog,
            &mut state,
            index,
            owner,
            &[crate::good(1)],
            batches,
        );
        sources[pool].push(StaffingWorkSource::Production(ProcessId::from_bytes(
            identity(index),
        )));
    }
    sources[1].push(StaffingWorkSource::MerchantHandling(crate::site(2)));
    let mut pools = Vec::new();
    for (index, sources) in sources.into_iter().enumerate() {
        let owner =
            crate::site(u8::try_from(index + 1).expect("the fixture value fits the target range"));
        state.inventory.push(stock_at(owner, crate::good(1), 1));
        state.labor.push(labor_at(owner, 1, 0));
        catalog.site_logistics_nodes.push(SiteLogisticsNode {
            site_id: owner,
            node_id: LogisticsNodeId::from_bytes(owner.as_bytes()),
        });
        let binding = StaffingPoolBinding::try_new(
            StaffingPoolId::from_bytes(owner.as_bytes()),
            owner,
            crate::unit(1),
            1,
            StaffingPolicy::one_period(1).expect("the one-period fixture advances"),
            sources,
        )
        .expect("the authored fixture satisfies the constructor invariants");
        pools.push(
            StaffingPoolState::try_new(binding, 0, 1, 0)
                .expect("the authored fixture satisfies the constructor invariants"),
        );
    }
    catalog.merchants.push(MerchantHandling {
        site_id: crate::site(2),
        location: "county:26163"
            .parse()
            .expect("the authored literal parses as the declared type"),
        role: MerchantRole::Retail,
        capacity_id: CorridorId::from_bytes([17; 32]),
        labor_unit_id: crate::unit(1),
    });
    catalog
        .handling_coefficients
        .push(MerchantHandlingCoefficient {
            site_id: crate::site(2),
            good_id: crate::good(2),
            unit_id: crate::unit(2),
            hours_per_unit: 1,
        });
    state.corridor_capacities.push(CorridorCapacity {
        corridor_id: CorridorId::from_bytes([17; 32]),
        period: 1,
        available_grams: 0,
    });
    let catalog = MaterialCatalog::try_new(catalog).expect("the fixture catalog is valid");
    (
        catalog,
        state,
        StaffingState::try_new(1, pools)
            .expect("the authored fixture satisfies the constructor invariants"),
    )
}

#[test]
fn staffing_requests_above_former_global_bound_preserve_sources_and_people() {
    let (catalog, state, people) = source_ownership_case();
    let original = state.clone();
    let bindings: Vec<_> = people.pools().iter().map(|p| p.binding().clone()).collect();
    assert_eq!(bindings[0].work_sources().len(), 32_768);
    assert_eq!(bindings[1].work_sources().len(), 32_769);
    let expected: BTreeSet<_> = bindings
        .iter()
        .flat_map(|binding| {
            binding.work_sources().iter().map(|source| {
                (
                    *source,
                    binding.pool_id(),
                    binding.site_id(),
                    binding.unit_id(),
                )
            })
        })
        .collect();
    assert_eq!(expected.len(), FORMER_FAMILY_LIMIT + 1);
    assert!(expected.len() <= MAX_STAFFING_WORK_SOURCES);
    assert!(bindings
        .iter()
        .all(|b| b.work_sources().len() <= MAX_MATERIAL_CIRCUIT_ROWS));
    let closed =
        crate::close_material_period(&catalog, &state).expect("the material period closes");
    let requests = closed
        .staffing_requests(&catalog, &bindings)
        .expect("the complete source union fits its independent global bound");
    assert_eq!(requests.len(), expected.len());
    assert_eq!(
        requests
            .iter()
            .map(|r| { (r.work_source(), r.pool_id(), r.site_id(), r.unit_id()) })
            .collect::<BTreeSet<_>>(),
        expected
    );
    let active = [0, FORMER_FAMILY_LIMIT - 1].map(|i| ProcessId::from_bytes(identity(i)));
    for request in &requests {
        let hours = u64::from(
            matches!(request.work_source(), StaffingWorkSource::Production(id) if active.contains(&id)),
        );
        assert_eq!((request.period(), request.hours()), (1, hours));
    }
    let staffing =
        crate::advance_staffing(&people, &requests).expect("the fixture staffing advances");
    assert_eq!(staffing.state().pools().len(), 2);
    assert_eq!(staffing.receipts().len(), 2);
    assert!(staffing.receipts().iter().all(|r| r.hires() == 1));
    for pool in staffing.state().pools() {
        assert_eq!(
            (
                pool.employed(),
                pool.reserve(),
                pool.binding().labor_force()
            ),
            (1, 0, 1)
        );
    }
    assert!(people
        .pools()
        .iter()
        .all(|p| (p.employed(), p.reserve()) == (0, 1)));
    let actual = closed
        .finish_with_labor(&catalog, staffing.next_labor().to_vec())
        .expect("the fixture completes with labor");
    assert_eq!(
        actual
            .state
            .production_commitments
            .iter()
            .map(|r| { (r.process_id, r.planned_batches) })
            .collect::<BTreeMap<_, _>>(),
        BTreeMap::from([(active[0], 1), (active[1], 1)])
    );
    assert_eq!(actual.production.len(), 0);
    assert_eq!(actual.state.inventory, state.inventory);
    assert_eq!(state, original);
}

fn combined_resources_case() -> (MaterialCatalog, MaterialCircuitState, Vec<LaborCapacityRow>) {
    let (mut catalog, mut state) = empty_production();
    for input in [crate::good(3), crate::good(4)] {
        catalog.commodities.push(CommodityDefinition {
            good_id: input,
            unit_id: crate::unit(2),
            kind: babylon_material_circuit::CommodityKind::Storable { grams_per_unit: 1 },
        });
    }
    let mut next_labor = Vec::new();
    for index in 0..RESOURCE_PROCESSES {
        let owner = SiteId::from_bytes(identity(index));
        append_process(
            &mut catalog,
            &mut state,
            index,
            owner,
            &[crate::good(1), crate::good(3), crate::good(4)],
            1,
        );
        for input in [crate::good(1), crate::good(3), crate::good(4)] {
            let missing = index == RESOURCE_PROCESSES - 1 && input == crate::good(4);
            state
                .inventory
                .push(stock_at(owner, input, u64::from(!missing)));
        }
        state.labor.push(labor_at(owner, 1, 0));
        next_labor.push(labor_at(
            owner,
            2,
            u64::from(index != RESOURCE_PROCESSES - 2),
        ));
    }
    let catalog = MaterialCatalog::try_new(catalog).expect("the fixture catalog is valid");
    (catalog, state, next_labor)
}

#[test]
fn planning_above_former_combined_bound_honors_late_input_and_labor_scarcity() {
    let (catalog, state, next_labor) = combined_resources_case();
    let original = state.clone();
    let input_keys: BTreeSet<_> = state
        .inventory
        .iter()
        .map(|r| (r.site_id, r.good_id, r.unit_id))
        .collect();
    let labor_keys: BTreeSet<_> = next_labor.iter().map(|r| (r.site_id, r.unit_id)).collect();
    assert_eq!((input_keys.len(), labor_keys.len()), (98_307, 32_769));
    assert_eq!(input_keys.len() + labor_keys.len(), 131_076);
    assert!(catalog.input_coefficients.len() <= MAX_INPUT_COEFFICIENTS);
    assert!(state.inventory.len() <= MAX_INVENTORY_ROWS);
    assert!(catalog.process_outputs.len() <= MAX_MATERIAL_CIRCUIT_ROWS);
    assert!(state.capacities.len() <= MAX_MATERIAL_CIRCUIT_ROWS);
    assert!(state.labor.len() <= MAX_MATERIAL_CIRCUIT_ROWS);
    let closed =
        crate::close_material_period(&catalog, &state).expect("the material period closes");
    assert_eq!(closed.inventory(), state.inventory);
    let actual = closed
        .finish_with_labor(&catalog, next_labor.clone())
        .expect("admitted input and labor families fit their combined resource bound");
    assert_eq!(actual.state.period, 2);
    assert_eq!(actual.state.labor, next_labor);
    let plans: BTreeMap<_, _> = actual
        .state
        .production_commitments
        .iter()
        .map(|r| (r.process_id, r.planned_batches))
        .collect();
    assert_eq!(plans.len(), RESOURCE_PROCESSES - 2);
    for index in 0..RESOURCE_PROCESSES {
        let expected = if index < RESOURCE_PROCESSES - 2 {
            Some(&1)
        } else {
            None
        };
        assert_eq!(plans.get(&ProcessId::from_bytes(identity(index))), expected);
    }
    assert_eq!(actual.production.len(), 0);
    assert_eq!(actual.state.inventory, state.inventory);
    assert_eq!(state, original);
}
