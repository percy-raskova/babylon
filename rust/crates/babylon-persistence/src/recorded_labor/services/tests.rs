//! Hand off one service batch to industry and households, then expire the true residuals.
use super::close;
use crate::production_projection::recurring_fixture;
use crate::recorded_labor::book::{Book, Frame};
use crate::recorded_labor::model::{LaborBasis, LaborNode, RecordedLaborError};
use crate::test_support;
use babylon_kernel::currency::Currency;
use babylon_material_circuit::{
    AccountId, CommodityKind, FinalDemandPrincipalId, HouseholdServiceReceipt, MaterialCatalog,
    OrderId, ProcessOutput, ServiceOutputReceipt, ServicePerformanceReceipt, ServiceStage,
};

fn grant(
    output: &ProcessOutput,
    id: u8,
    buyer: AccountId,
    used: u64,
    unused: u64,
) -> ServicePerformanceReceipt {
    ServicePerformanceReceipt {
        period: 1,
        order_id: OrderId::from_bytes([id; 32]),
        provider_site_id: output.site_id,
        buyer,
        good_id: output.good_id,
        unit_id: output.unit_id,
        requested_quantity: used + unused + 1,
        admitted_quantity: used + unused + 1,
        performed_quantity: used + unused,
        used_quantity: used,
        unused_quantity: unused,
        expired_quantity: 1,
        unit_price: Currency::from_micro_units(i128::from(id)),
    }
}

#[test]
fn service_hours_follow_performance_and_exclude_unperformed_claims() {
    let (catalog, _) = recurring_fixture::materials();
    let mut definition = catalog.into_definition();
    let product = definition.process_outputs[0].clone();
    let user = definition.process_outputs[1].site_id;
    let phase = ServiceStage::UtilityProvision;
    definition
        .commodities
        .iter_mut()
        .find(|c| (c.good_id, c.unit_id) == (product.good_id, product.unit_id))
        .expect("defined output unit")
        .kind = CommodityKind::PeriodService { stage: phase };
    definition
        .supplier_routes
        .retain(|route| (route.good_id, route.unit_id) != (product.good_id, product.unit_id));
    let catalog = MaterialCatalog::try_new(definition).expect("captured service stage");
    let household = FinalDemandPrincipalId::from_bytes([9; 32]);
    let source = LaborNode::site(product.site_id, product.good_id, product.unit_id);
    let consumer = LaborNode::site(user, product.good_id, product.unit_id);
    let household_node = LaborNode::household(household, product.good_id, product.unit_id);
    let mut frame = Frame::new(Book::new());
    frame
        .credit(
            source,
            8,
            LaborBasis {
                recorded_micro_hours: 17,
                unknown_opening: true,
            },
        )
        .expect("service output");
    let mut receipts = test_support::material_receipts(1);
    receipts.service_outputs.push(ServiceOutputReceipt {
        period: 1,
        process_id: product.process_id,
        site_id: product.site_id,
        good_id: product.good_id,
        unit_id: product.unit_id,
        produced_quantity: 8,
        allocated_quantity: 7,
        expired_quantity: 1,
        direct_cost: Currency::from_micro_units(0),
        expired_cost: Currency::from_micro_units(0),
    });
    receipts.service_performance = vec![
        grant(&product, 1, AccountId::Site(user), 2, 1),
        grant(&product, 2, AccountId::Household(household), 3, 1),
    ];
    receipts.household_services.push(HouseholdServiceReceipt {
        period: 1,
        principal_id: household,
        good_id: product.good_id,
        unit_id: product.unit_id,
        required_quantity: 3,
        performed_quantity: 4,
        satisfied_quantity: 3,
        unmet_quantity: 0,
        unused_quantity: 1,
    });
    close::handoff(&mut frame, &catalog, phase, &receipts)
        .expect("settled performance and unallocated expiry");
    assert_eq!(frame.book[&consumer].basis.recorded_micro_hours, 6);
    assert_eq!(frame.book[&household_node].basis.recorded_micro_hours, 8);
    assert_eq!(frame.released_micro_hours, 3);
    assert_eq!(
        close::finish(&mut frame, &receipts),
        Err(RecordedLaborError::ReceiptMismatch("service use"))
    );
    let embodied = frame
        .take(consumer, 2)
        .expect("performed intermediate service used by later production");
    assert_eq!(
        embodied,
        LaborBasis {
            recorded_micro_hours: 4,
            unknown_opening: true
        }
    );
    close::finish(&mut frame, &receipts).expect("household use and unused grants");
    assert!(frame.book.is_empty());
    assert_eq!(frame.released_micro_hours, 13);
    assert_eq!(frame.direct_micro_hours, 0);
}
