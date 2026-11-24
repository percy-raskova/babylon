//! Fulfillment occurs only once, when the food leaves its donor.
use super::aid;
use crate::production_projection::recurring_fixture;
use crate::recorded_labor::book::{Book, Frame};
use crate::recorded_labor::model::{LaborBasis, LaborNode};
use crate::recorded_labor::view::{self, PeriodView};
use crate::test_support;
use babylon_kernel::currency::Currency;
use babylon_material_circuit::{
    AccountId, AidFreightLot, AidMandate, AidOutcome, AidReceipt, AidReceiving, AidTransport,
    CircuitAccounting, FinalDemandPrincipalId, FreightLotId, MaterialCatalog,
    MaterialCatalogDefinition, MaterialCircuitState, UnitId,
};
use babylon_tick::material_world::MaterialTickReceipts;

fn period_view<'a>(
    state: &'a MaterialCircuitState,
    receipts: &'a MaterialTickReceipts,
) -> PeriodView<'a> {
    PeriodView {
        period: receipts.resolve_tick,
        before: state,
        after: state,
        receipts: view::receipt_view(receipts, &[]),
    }
}

fn routed_mandate(definition: &MaterialCatalogDefinition) -> AidMandate {
    let stage = &definition.route_stages[0];
    let route_id = stage.route_id;
    let transport = AidTransport::Routed {
        route_id,
        from_node_id: stage.from_node_id,
        to_node_id: stage.to_node_id,
    };
    let good = definition.commodities[0].good_id;
    let unit = definition.commodities[0].unit_id;
    let donor = FinalDemandPrincipalId::from_bytes([6; 32]);
    let recipient = FinalDemandPrincipalId::from_bytes([7; 32]);
    let payer = AccountId::Household(donor);
    let mandate_id = [4; 32];
    let zero = Currency::from_micro_units(0);
    AidMandate {
        id: mandate_id,
        source_hash: [5; 32],
        donor_actor: 1,
        donor_contributor_id: 1,
        recipient_actor: 2,
        payer,
        donor,
        recipient,
        good_id: good,
        unit_id: unit,
        labor_unit_id: UnitId::from_bytes([8; 32]),
        hours_per_unit: 2,
        maximum_quantity: 4,
        maximum_cash: Currency::from_micro_units(1),
        initial_quantity: 1,
        initial_cash: zero,
        food_receiving: AidReceiving::Accept,
        cash_receiving: AidReceiving::Accept,
        transport,
    }
}

#[test]
fn partial_aid_loss_moves_the_remaining_food_and_fulfillment_hours_to_the_recipient() {
    let (catalog, mut state) = recurring_fixture::materials();
    let mut definition = catalog.into_definition();
    let mandate = routed_mandate(&definition);
    let (donor, recipient, payer, good, unit, transport, mandate_id) = (
        mandate.donor,
        mandate.recipient,
        mandate.payer,
        mandate.good_id,
        mandate.unit_id,
        mandate.transport,
        mandate.id,
    );
    let route_id = definition.route_stages[0].route_id;
    let commitment = babylon_material_circuit::aid_commitment_id(mandate_id, 1);
    let zero = Currency::from_micro_units(0);
    definition.aid_mandates = vec![mandate];
    let catalog = MaterialCatalog::try_new(definition).expect("capture fulfillment terms");
    let lot_id = FreightLotId::from_bytes([3; 32]);
    let CircuitAccounting::Monetary(economy) = &mut state.accounting else {
        panic!("monetary opening")
    };
    economy.aid.freight = vec![AidFreightLot {
        lot_id,
        commitment_id: commitment,
        mandate_id,
        route_id,
        dispatch_period: 1,
        current_stage_index: 0,
        stage_arrival_period: 2,
        donor,
        recipient,
        good_id: good,
        unit_id: unit,
        quantity: 3,
    }];
    let mut frame = Frame::new(Book::new());
    let source = LaborNode::household(donor, good, unit);
    let target = LaborNode::household(recipient, good, unit);
    frame
        .credit(
            source,
            4,
            LaborBasis {
                recorded_micro_hours: 7,
                unknown_opening: true,
            },
        )
        .expect("food shelf");
    let mut receipts = test_support::material_receipts(1);
    let mut actual = AidReceipt {
        commitment_id: commitment,
        mandate_id,
        period: 1,
        dispatch_period: 1,
        transport,
        payer,
        donor,
        recipient,
        good_id: good,
        unit_id: unit,
        outcome: AidOutcome::Dispatched,
        quantity: 3,
        carrying_amount: zero,
        cash_amount: zero,
        contribution_hours: 6,
    };
    receipts.aid = vec![actual.clone()];
    aid::aid_dispatch(&mut frame, &catalog, &period_view(&state, &receipts))
        .expect("three packages and six actual fulfillment hours");
    assert_eq!(frame.book[&source].basis.recorded_micro_hours, 2);
    assert_eq!(
        frame.book[&LaborNode::freight(lot_id)]
            .basis
            .recorded_micro_hours,
        6_000_005
    );
    actual.period = 2;
    actual.contribution_hours = 0;
    actual.quantity = 2;
    actual.outcome = AidOutcome::Granted;
    let mut lost = actual.clone();
    lost.outcome = AidOutcome::Lost;
    lost.quantity = 1;
    receipts.resolve_tick = 2;
    receipts.aid = vec![actual, lost];
    aid::aid_arrivals(&mut frame, &period_view(&state, &receipts))
        .expect("stage loss followed by handoff");
    assert_eq!(frame.direct_micro_hours, 6_000_000);
    assert_eq!(frame.released_micro_hours, 2_000_001);
    assert_eq!(
        frame.book[&target].basis,
        LaborBasis {
            recorded_micro_hours: 4_000_004,
            unknown_opening: true
        }
    );
    assert_eq!(frame.quantity(LaborNode::freight(lot_id)), 0);
}
