use crate::material_world::equipment_receipt::Currency;
use babylon_material_circuit::AccountId;
use babylon_material_circuit::AidBook;
use babylon_material_circuit::AttendancePlan;
use babylon_material_circuit::CapacityRow;
use babylon_material_circuit::CapacitySupply;
use babylon_material_circuit::CashAccount;
use babylon_material_circuit::CircuitAccounting;
use babylon_material_circuit::CommodityDefinition;
use babylon_material_circuit::CommodityKind;
use babylon_material_circuit::CorridorCapacity;
use babylon_material_circuit::CorridorId;
use babylon_material_circuit::EmploymentTerms;
use babylon_material_circuit::EquipmentBinding;
use babylon_material_circuit::EquipmentDefinition;
use babylon_material_circuit::EquipmentDefinitionId;
use babylon_material_circuit::FinalDemandPrincipal;
use babylon_material_circuit::FinalDemandPrincipalId;
use babylon_material_circuit::FinancialInstitutions;
use babylon_material_circuit::GoodId;
use babylon_material_circuit::GoodsPriceCostBasis;
use babylon_material_circuit::HistoricalCostBook;
use babylon_material_circuit::InputOutputCoefficient;
use babylon_material_circuit::InstallationInput;
use babylon_material_circuit::InstallationPolicy;
use babylon_material_circuit::InstallationTarget;
use babylon_material_circuit::InventoryRow;
use babylon_material_circuit::InvestmentPolicy;
use babylon_material_circuit::LaborCapacityRow;
use babylon_material_circuit::LaborCoefficient;
use babylon_material_circuit::LaborCompensation;
use babylon_material_circuit::LogisticsNodeId;
use babylon_material_circuit::MaterialCircuitState;
use babylon_material_circuit::MemberLaborCapacityRow;
use babylon_material_circuit::MonetaryBook;
use babylon_material_circuit::MonetaryCircuit;
use babylon_material_circuit::PriceDecision;
use babylon_material_circuit::PricePolicy;
use babylon_material_circuit::ProcessId;
use babylon_material_circuit::ProcessOutput;
use babylon_material_circuit::ProductionDemandPolicy;
use babylon_material_circuit::ProductiveEquipment;
use babylon_material_circuit::RecurringEconomy;
use babylon_material_circuit::RollingCapacitySupply;
use babylon_material_circuit::RollingProcessSupply;
use babylon_material_circuit::RouteId;
use babylon_material_circuit::RouteStage;
use babylon_material_circuit::RouteStageCapacity;
use babylon_material_circuit::SellerOffer;
use babylon_material_circuit::SharedCapacitySupply;
use babylon_material_circuit::SiteId;
use babylon_material_circuit::SiteLogisticsNode;
use babylon_material_circuit::StaffingMemberId;
use babylon_material_circuit::StockCarryingValue;
use babylon_material_circuit::SupplierRoute;
use babylon_material_circuit::SupplierTransport;
use babylon_material_circuit::UnitId;
include!("../../../../babylon-material-circuit/tests/support/equipment_fixture.rs");

#[test]
fn actual_equipment_close_receipts_roundtrip_with_wip_installation_wages_and_wear() {
    let mut state = opening();
    for period in 1..=5 {
        let transition = babylon_material_circuit::advance_material_circuit(&state)
            .expect("the authored material state advances one period");
        let bytes = super::super::encode_material_receipts(period, &transition)
            .expect("the fixture value encodes to its canonical bytes");
        let decoded = super::super::decode_material_receipts(&bytes)
            .expect("the canonical bytes decode into the declared type");
        assert_eq!(decoded.installation, transition.installation);
        assert_eq!(decoded.equipment_wear, transition.equipment_wear);
        assert_eq!(decoded.member_labor_use, transition.member_labor_use);
        assert_eq!(decoded.income, transition.income);
        assert!(super::super::decode_material_receipts(&bytes[..bytes.len() - 1]).is_err());
        state = transition.state;
    }
    assert!(equipment(&state).cohorts.is_empty());
    assert_eq!(equipment_cost(&state), money(0));
    assert_eq!(stock_cost(&state, good(4)), money(44));
    let mut state = opening();
    configure_investment(&mut state, 100, -10);
    let transition = babylon_material_circuit::advance_material_circuit(&state)
        .expect("the authored material state advances one period");
    let bytes = super::super::encode_material_receipts(1, &transition)
        .expect("the fixture value encodes to its canonical bytes");
    assert_eq!(
        super::super::decode_material_receipts(&bytes)
            .expect("the canonical bytes decode into the declared type")
            .investment,
        transition.investment
    );
}

#[test]
fn equipment_receipt_refuses_invalid_work_cost_partitions_duplicates_and_old_version() {
    let mut transition = babylon_material_circuit::advance_material_circuit(&opening())
        .expect("the authored material state advances one period");
    let original = transition.clone();
    transition.installation[0].used_hours = 1;
    assert!(super::super::encode_material_receipts(1, &transition).is_err());
    transition = original.clone();
    transition
        .installation
        .push(transition.installation[0].clone());
    assert!(super::super::encode_material_receipts(1, &transition).is_err());
    transition = original;
    transition.installation[0].closing_carrying = money(27);
    assert!(super::super::encode_material_receipts(1, &transition).is_err());
    let mut state = opening();
    for _ in 0..3 {
        state = babylon_material_circuit::advance_material_circuit(&state)
            .expect("the authored material state advances one period")
            .state;
    }
    let mut transition = babylon_material_circuit::advance_material_circuit(&state)
        .expect("the authored material state advances one period");
    transition.equipment_wear[0].closing_carrying = money(0);
    assert!(super::super::encode_material_receipts(4, &transition).is_err());
    let old = b"babylon.material-tick-receipts.v11\0";
    assert!(super::super::decode_material_receipts(old).is_err());
}

#[test]
fn goods_cost_from_real_equipment_close_roundtrips_and_restart_does_not_reuse_it() {
    let mut state = opening();
    for _ in 0..3 {
        state = babylon_material_circuit::advance_material_circuit(&state)
            .expect("the authored material state advances one period")
            .state;
    }
    configure_output_quote(&mut state);
    let transition = babylon_material_circuit::advance_material_circuit(&state)
        .expect("the authored material state advances one period");
    let bytes = super::super::encode_material_receipts(4, &transition)
        .expect("the fixture value encodes to its canonical bytes");
    let decoded = super::super::decode_material_receipts(&bytes)
        .expect("the canonical bytes decode into the declared type");
    assert_eq!(decoded.prices, transition.prices);
    assert_eq!(decoded.prices[0].cost.quantity, 2);
    assert_eq!(decoded.prices[0].cost.carrying_cost, money(29));
    assert_eq!(decoded.prices[0].reason, PriceDecision::CostPressure);
    let restored = babylon_material_circuit::decode_material_circuit_state(
        &babylon_material_circuit::encode_material_circuit_state(&transition.state)
            .expect("the canonical material state encodes"),
    )
    .expect("the canonical material bytes decode");
    let next = babylon_material_circuit::advance_material_circuit(&restored)
        .expect("the authored material state advances one period");
    assert_eq!(
        next,
        babylon_material_circuit::advance_material_circuit(&transition.state)
            .expect("the authored material state advances one period")
    );
    assert_eq!(next.prices[0].cost.basis, GoodsPriceCostBasis::Unavailable);
    let next_bytes = super::super::encode_material_receipts(5, &next)
        .expect("the fixture value encodes to its canonical bytes");
    assert_eq!(
        super::super::decode_material_receipts(&next_bytes)
            .expect("the canonical bytes decode into the declared type")
            .prices,
        next.prices
    );
}

#[test]
fn installation_decisions_roundtrip_and_refuse_false_starts_positions_and_old_format() {
    let original = babylon_material_circuit::advance_material_circuit(&opening())
        .expect("the authored material state advances one period");
    let bytes = super::super::encode_material_receipts(1, &original)
        .expect("the fixture value encodes to its canonical bytes");
    let decoded = super::super::decode_material_receipts(&bytes)
        .expect("the canonical bytes decode into the declared type");
    assert_eq!(
        decoded.installation_decisions,
        original.installation_decisions
    );
    assert_eq!(decoded.installation_decisions[0].started_units, 1);
    for mutation in 0..5 {
        let mut changed = original.clone();
        match mutation {
            0 => changed.installation_decisions.clear(),
            1 => changed.installation_decisions[0].started_units = 0,
            2 => changed.installation_decisions[0].pending_units = 1,
            3 => changed.installation_decisions[0].period = 2,
            _ => changed
                .installation_decisions
                .push(changed.installation_decisions[0].clone()),
        }
        assert!(
            super::super::encode_material_receipts(1, &changed).is_err(),
            "mutation {mutation}"
        );
    }
    assert!(decoded.household_time.is_empty());
    assert!(decoded.aid.is_empty());
    assert!(decoded.collections.is_empty());
    // Empty time34, aid35 and collection36 each retain a tag and u64 count.
    let start = bytes.len() - 3 * (1 + 8) - super::super::installation_decision::ROW_BYTES;
    let mut malformed = bytes.clone();
    malformed[start + 112..start + 120].copy_from_slice(&0_u64.to_be_bytes());
    assert!(super::super::decode_material_receipts(&malformed).is_err());
    let mut old = bytes.clone();
    let domain = super::super::RECEIPT_DOMAIN.len();
    old[domain..domain + 4].copy_from_slice(&13_u32.to_be_bytes());
    assert!(super::super::decode_material_receipts(&old).is_err());
    for length in [start - 1, start, start + 72, bytes.len() - 1] {
        assert!(super::super::decode_material_receipts(&bytes[..length]).is_err());
    }
}
