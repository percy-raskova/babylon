//! The paid opening uses the same four-person recurring control as goods projections.
use super::super::ProductionProjectionError;
use super::projection;
use babylon_graph::stable_element::StableElementKey;
use babylon_graph::stable_state;
use babylon_graph::stable_state::StableGraphState;
use babylon_graph::stable_state::StableGraphStateRowsInput;
use babylon_material_circuit::{
    CircuitAccounting, StaffingMemberBinding, StaffingPolicy, StaffingPoolBinding, StaffingPoolId,
    StaffingWorkSource,
};
use babylon_tick::material_staffing::StaffingComposition;
use babylon_tick::material_staffing::{
    StaffingMemberNodeBinding, StaffingNodeBinding, EMPLOYED_POPULATION, PREVIOUS_UNRETAINED_HOURS,
    RESERVE_POPULATION,
};
use babylon_tick::material_world::MaterialWorldRegister;

fn paid_opening() -> (StaffingComposition, StableGraphState, MaterialWorldRegister) {
    let state = crate::production_projection::recurring_fixture::opening();
    let CircuitAccounting::Monetary(economy) = &state.accounting else {
        panic!("paid control")
    };
    let residence = state.final_demand_principals[0].location;
    let mut nodes = vec![];
    let mut values = vec![];
    let mut bindings = vec![];
    for (index, terms) in economy.employment.iter().enumerate() {
        let workplace = format!("workplace-{index}");
        let member = format!("member-{index}");
        let key = |name: &str| StableElementKey::Node {
            scenario: "paid-opening".into(),
            local_name: name.into(),
        };
        let hours = economy
            .member_labor
            .iter()
            .find(|row| row.period == 1 && row.member_id == terms.member_id)
            .expect("the fixture holds the searched element")
            .available_hours;
        let people = hours / 4;
        nodes.extend([
            (workplace.clone(), "BUSINESS".into()),
            (member.clone(), "SOCIAL_CLASS".into()),
        ]);
        values.extend([
            (
                workplace.clone(),
                PREVIOUS_UNRETAINED_HOURS.into(),
                0_f64.to_bits(),
            ),
            (
                member.clone(),
                EMPLOYED_POPULATION.into(),
                f64::from(u32::try_from(people).expect("the fixture value fits the target range"))
                    .to_bits(),
            ),
            (member.clone(), RESERVE_POPULATION.into(), 0_f64.to_bits()),
        ]);
        let source = state
            .process_outputs
            .iter()
            .find(|row| row.site_id == terms.site_id)
            .map_or(StaffingWorkSource::MerchantHandling(terms.site_id), |row| {
                StaffingWorkSource::Production(row.process_id)
            });
        let pool = StaffingPoolBinding::try_new(
            StaffingPoolId::from_bytes(terms.site_id.as_bytes()),
            terms.site_id,
            terms.unit_id,
            people,
            StaffingPolicy::one_period(4).expect("the one-period fixture advances"),
            vec![source],
        )
        .expect("the authored fixture satisfies the constructor invariants");
        let member_binding =
            StaffingMemberBinding::try_new(terms.member_id, terms.payee, residence, people)
                .expect("the authored fixture satisfies the constructor invariants");
        bindings.push(
            StaffingNodeBinding::try_new(
                key(&workplace),
                pool,
                vec![
                    StaffingMemberNodeBinding::try_new(key(&member), member_binding)
                        .expect("the authored fixture satisfies the constructor invariants"),
                ],
            )
            .expect("the authored fixture satisfies the constructor invariants"),
        );
    }
    let graph = stable_state::compose_stable_graph_state_from_rows(
        "paid-opening",
        StableGraphStateRowsInput {
            nodes,
            node_f64: values,
            edges: vec![],
            hyperedges: vec![],
            edge_f64: vec![],
            node_currency: vec![],
            hyperedge_f64: vec![],
        },
    )
    .expect("the authored rows compose a stable graph state");
    (
        StaffingComposition::try_new(bindings)
            .expect("the authored fixture satisfies the constructor invariants"),
        graph,
        MaterialWorldRegister::try_new(0, state)
            .expect("the authored fixture satisfies the constructor invariants"),
    )
}

#[test]
fn paid_projection_joins_resident_accounts_hours_and_compensation() {
    let (composition, graph, register) = paid_opening();
    let accounts =
        projection::project_staffing_accounts(&composition, &graph, &register, None, &[], None)
            .expect("the fixture projection accepts the authored input");
    assert_eq!(accounts.iter().map(|r| r.employed).sum::<u64>(), 4);
    assert_eq!(
        accounts
            .iter()
            .flat_map(|r| &r.members)
            .map(|r| r.next_opening_hours)
            .sum::<u64>(),
        16
    );
    for row in accounts.iter().flat_map(|r| &r.members) {
        assert_eq!(
            row.residence,
            register.state().final_demand_principals[0].location
        );
        assert_eq!(
            row.compensation,
            Some(
                crate::production_observation::ProductionLaborCompensation::Wage {
                    hourly_micro_units: 1
                }
            )
        );
    }
    let mut bindings = composition.bindings().to_vec();
    let first = &bindings[0];
    let member = &first.members()[0];
    let changed = StaffingMemberBinding::try_new(
        member.member().member_id(),
        member.member().household_id(),
        "county:26099"
            .parse()
            .expect("the authored literal parses as the declared type"),
        member.member().labor_force(),
    )
    .expect("the authored fixture satisfies the constructor invariants");
    bindings[0] = StaffingNodeBinding::try_new(
        first.subject().clone(),
        first.pool().clone(),
        vec![
            StaffingMemberNodeBinding::try_new(member.subject().clone(), changed)
                .expect("the authored fixture satisfies the constructor invariants"),
        ],
    )
    .expect("the authored fixture satisfies the constructor invariants");
    let forged = StaffingComposition::try_new(bindings)
        .expect("the authored fixture satisfies the constructor invariants");
    assert_eq!(
        projection::project_staffing_accounts(&forged, &graph, &register, None, &[], None),
        Err(ProductionProjectionError::State)
    );
}
