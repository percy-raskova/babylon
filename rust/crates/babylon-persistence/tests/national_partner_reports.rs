//! Disclosed partner knowledge in an ordinary national campaign.
use babylon_kernel::replay::{ReplaySeed, ReplaySessionId};
use babylon_material_circuit::AccountId;
use babylon_material_circuit::MaterialCatalog;
use babylon_material_circuit::MaterialCircuitState;
use babylon_material_circuit::{
    CircuitAccounting, FinalDemandPrincipalId, HouseholdTimeAccounting, HouseholdTimeBook,
};
use babylon_material_circuit::{MoneyTransferPurpose, OutboundOrderId, UnitId};
use babylon_persistence::economic_catalog::{self, CapturedEconomicCatalog};
use babylon_persistence::identity::CampaignId;
use babylon_persistence::observer_reader::CommittedMaterialReceipts;
use babylon_persistence::qualification_audit::aid;
use babylon_persistence::qualification_audit::aid::{Audit, Boundary, Refusal};
use babylon_practice_contract::OrganizerConfig;
use babylon_practice_contract::OrganizerView;
use babylon_practice_contract::{OrganizerPartnerFacts, OrganizerReport, OrganizerServiceReport};
use babylon_tick::material_world::MaterialReceiptHandle;
use babylon_tick::material_world::MaterialTickReceipts;
use std::collections::BTreeSet;
use uuid::Uuid;

#[test]
fn national_opening_shares_only_dated_food_assessments_for_the_known_partners() {
    let captured = CapturedEconomicCatalog::capture_national_campaign(
        economic_catalog::national_catalog_input(),
        CampaignId::from_uuid(Uuid::from_u128(0x0026_1631_7031)),
    )
    .expect("national policy and opening material");
    let session = captured
        .create_foundation(
            ReplaySessionId::try_from("national-partner-reports").expect("session identity"),
            ReplaySeed::new(319),
        )
        .expect("ordinary national foundation")
        .into_session()
        .expect("national session");
    let partners = session
        .material()
        .organizer_config()
        .expect("captured organizer")
        .aid_bindings
        .iter()
        .map(|binding| binding.partner.actor_id)
        .collect::<BTreeSet<_>>();
    assert_eq!(partners.len(), 2);
    let snapshot =
        aid::material_disclosure(session.catalog(), session.material(), session.duration())
            .expect("lawful opening disclosure");
    let config = session.material().organizer_config().expect("organizer");
    check_opening(
        &snapshot.view,
        &partners,
        config,
        session.catalog(),
        session.material().state(),
    );
    let opening_witness = aid::opening_reports(session.catalog(), session.material())
        .expect("authenticated opening reports");
    assert_eq!(opening_witness.len(), 2);
    println!(
        "Qualification opening reports {}",
        serde_json::to_string(&opening_witness).expect("serialized producer")
    );
    let mut audit = Audit::default();
    audit
        .open(session.catalog(), session.material(), &snapshot)
        .expect("independent opening");
    let state = session.material().organizer_state().expect("state");
    let actions = babylon_practice_contract::organizer_action_batch(
        config,
        state,
        None,
        session.graph_session().session_identity().clone(),
    )
    .expect("ordinary close");
    let candidate = session
        .prepare_advance(&actions)
        .expect("first material close with reports");
    let committed = candidate.material().register();
    let actual = babylon_tick::material_world::decode_material_receipts(
        candidate.material().receipt_bytes(),
    )
    .expect("typed actual close");
    let end = aid::material_disclosure(session.catalog(), committed, session.duration())
        .expect("completed disclosure");
    assert_eq!(end.view.aid_partners, snapshot.view.aid_partners);
    let CircuitAccounting::Monetary(economy) = &committed.state().accounting else {
        panic!("modeled cash")
    };
    let HouseholdTimeAccounting::Modeled(book) = &economy.household_time else {
        panic!("modeled household hours")
    };
    let admitted = CommittedMaterialReceipts {
        campaign_id: CampaignId::from_uuid(Uuid::from_bytes(config.campaign_id)),
        identity: *candidate.identity(),
        material_register_bytes: committed.canonical_bytes().len(),
        receipts: MaterialReceiptHandle::new(actual.clone()),
        household_contributions: book.contributions.clone(),
    };
    let check = |receipts: MaterialTickReceipts| {
        let mut changed = admitted.clone();
        changed.receipts = MaterialReceiptHandle::new(receipts);
        audit
            .clone()
            .read(session.catalog(), &changed, committed, &end)
    };
    let verified = check(actual.clone()).expect("complete independently authenticated granted set");
    assert_eq!(verified.version, 3);
    assert_eq!(verified.partner_reports.len(), 6);
    println!(
        "Qualification closed aid {}",
        serde_json::to_string(&verified).expect("serialized producer")
    );
    check_crossed_quantities(config, &actual, &check);
    check_crossed_transfers(config, &actual, &check);
    check_granted_reports(&end.view, &partners, config, &actual, book);
}

fn check_granted_reports(
    view: &OrganizerView,
    partners: &BTreeSet<u64>,
    config: &OrganizerConfig,
    actual: &MaterialTickReceipts,
    book: &HouseholdTimeBook,
) {
    let reports: Vec<_> = view
        .observations
        .iter()
        .filter(|r| r.observed_period == 1 && partners.contains(&r.subject_id))
        .collect();
    assert_eq!(reports.len(), 6);
    for row in reports {
        assert_eq!(
            (row.acquired_period, row.source_actor_id),
            (1, row.subject_id)
        );
        let binding = config
            .aid_bindings
            .iter()
            .find(|b| b.partner.actor_id == row.subject_id)
            .expect("known report subject");
        let principal = FinalDemandPrincipalId::from_bytes(binding.recipient_principal_id);
        let OrganizerReport::Partner { facts, .. } = &row.report else {
            panic!("partner report")
        };
        check_completed(principal, actual, book, facts);
    }
}
fn check_crossed_quantities(
    config: &OrganizerConfig,
    actual: &MaterialTickReceipts,
    check: &impl Fn(MaterialTickReceipts) -> Result<Boundary, Refusal>,
) {
    let principal =
        FinalDemandPrincipalId::from_bytes(config.aid_bindings[0].recipient_principal_id);
    let food = &config.aid_bindings[0].report_sharing.food[0];
    let mut missing = actual.clone();
    missing
        .household_consumption
        .retain(|r| !(r.principal_id == principal && r.good_id.as_bytes() == food.good_id));
    assert!(
        check(missing).is_err(),
        "missing basis cannot support a zero or positive claim"
    );
    let mut crossed = actual.clone();
    let time = crossed
        .household_time
        .iter_mut()
        .find(|r| r.principal_id == principal)
        .expect("target time receipt");
    time.labor_unit_id = UnitId::from_bytes([0; 32]);
    assert!(check(crossed).is_err(), "wrong labor unit");
    let mut crossed = actual.clone();
    let service = crossed
        .household_services
        .iter_mut()
        .find(|r| {
            r.principal_id == principal
                && config.aid_bindings[0]
                    .report_sharing
                    .essential_services
                    .iter()
                    .any(|c| c.good_id == r.good_id.as_bytes())
        })
        .expect("granted service");
    service.period += 1;
    assert!(check(crossed).is_err(), "wrong service date");
    let mut crossed = actual.clone();
    let r = crossed
        .household_consumption
        .iter_mut()
        .find(|r| r.principal_id == principal && r.good_id.as_bytes() == food.good_id)
        .expect("granted food");
    r.principal_id =
        FinalDemandPrincipalId::from_bytes(config.aid_bindings[1].recipient_principal_id);
    assert!(
        check(crossed).is_err(),
        "same commodity for the other recipient"
    );
}

fn check_crossed_transfers(
    config: &OrganizerConfig,
    actual: &MaterialTickReceipts,
    check: &impl Fn(MaterialTickReceipts) -> Result<Boundary, Refusal>,
) {
    let service_orders = actual
        .service_performance
        .iter()
        .filter(|p| {
            config.aid_bindings.iter().any(|b| {
                p.buyer
                    == AccountId::Household(FinalDemandPrincipalId::from_bytes(
                        b.recipient_principal_id,
                    ))
                    && b.report_sharing.essential_services.iter().any(|c| {
                        p.good_id.as_bytes() == c.good_id && p.unit_id.as_bytes() == c.unit_id
                    })
            })
        })
        .map(|p| OutboundOrderId::Service(p.order_id))
        .collect::<BTreeSet<_>>();
    let retail_orders = actual
        .local_fulfillments
        .iter()
        .filter(|h| {
            config.aid_bindings.iter().any(|b| {
                h.demand_principal_id.as_bytes() == b.recipient_principal_id
                    && b.report_sharing.food.iter().any(|c| {
                        h.good_id.as_bytes() == c.good_id && h.unit_id.as_bytes() == c.unit_id
                    })
            })
        })
        .map(|h| OutboundOrderId::LocalFinalDemand(h.order_id))
        .collect::<BTreeSet<_>>();
    let mut verified_leg = BTreeSet::new();
    for (index, transfer) in
        actual
            .money_transfers
            .iter()
            .enumerate()
            .filter(|(_, t)| match t.purpose {
                MoneyTransferPurpose::DeliverySettlement(order) => {
                    retail_orders.contains(&order) || service_orders.contains(&order)
                }
                MoneyTransferPurpose::PurchaseRefund(order) => service_orders.contains(&order),
                _ => false,
            })
    {
        let leg = match transfer.purpose {
            MoneyTransferPurpose::DeliverySettlement(OutboundOrderId::LocalFinalDemand(_)) => {
                "retail settlement"
            }
            MoneyTransferPurpose::DeliverySettlement(OutboundOrderId::Service(_)) => {
                "service settlement"
            }
            MoneyTransferPurpose::PurchaseRefund(OutboundOrderId::Service(_)) => "service refund",
            _ => unreachable!("scoped typed transfer"),
        };
        if !verified_leg.insert(leg) {
            continue;
        }
        let mut changed = actual.clone();
        changed.money_transfers[index].credit.delta = transfer.debit.delta;
        assert!(check(changed).is_err(), "crossed signed recipient {leg}");
    }
    println!("Qualification exercised national transfer legs {verified_leg:?}");
}

fn check_completed(
    principal: FinalDemandPrincipalId,
    actual: &MaterialTickReceipts,
    book: &HouseholdTimeBook,
    facts: &OrganizerPartnerFacts,
) {
    match facts {
        OrganizerPartnerFacts::FoodProvision {
            commodity,
            required,
            consumed,
            unmet,
            closing,
            purchased,
            settled_micros,
        } => {
            let source = actual
                .household_consumption
                .iter()
                .find(|r| {
                    r.principal_id == principal
                        && r.good_id.as_bytes() == commodity.good_id
                        && r.unit_id.as_bytes() == commodity.unit_id
                })
                .expect("exact consumption receipt");
            assert_eq!(
                (*required, *consumed, *unmet, *closing),
                (
                    source.required_quantity,
                    source.consumed_quantity,
                    source.unmet_quantity,
                    source.closing_quantity
                )
            );
            let handoffs: Vec<_> = actual
                .local_fulfillments
                .iter()
                .filter(|r| {
                    r.demand_principal_id == principal
                        && r.good_id == source.good_id
                        && r.unit_id == source.unit_id
                })
                .collect();
            assert_eq!(*purchased, handoffs.iter().map(|r| r.quantity).sum::<u64>());
            let paid = actual
                .money_transfers
                .iter()
                .filter(|t| {
                    handoffs.iter().any(|r| {
                        t.purpose
                            == MoneyTransferPurpose::DeliverySettlement(
                                OutboundOrderId::LocalFinalDemand(r.order_id),
                            )
                    })
                })
                .map(|t| t.credit.delta.micro_units())
                .sum::<i128>();
            assert_eq!(*settled_micros, paid);
        }
        OrganizerPartnerFacts::EssentialServices { services } => {
            check_services(principal, actual, services);
        }
        OrganizerPartnerFacts::ParticipationTime {
            labor_unit,
            contributed,
            remaining,
            ..
        } => {
            let source = actual
                .household_time
                .iter()
                .find(|r| r.principal_id == principal && r.labor_unit_id.as_bytes() == *labor_unit)
                .expect("exact gross hour partition");
            let spent = book
                .contributions
                .iter()
                .filter(|r| r.period == 1 && r.contribution.principal_id == principal)
                .map(|r| r.contribution.hours)
                .sum::<u64>();
            assert_eq!(
                (*contributed, *remaining),
                (spent, source.contribution_available_hours - spent)
            );
        }
        OrganizerPartnerFacts::OpeningAssessment { .. } => {
            panic!("opening assessment after close")
        }
    }
}

fn check_services(
    principal: FinalDemandPrincipalId,
    actual: &MaterialTickReceipts,
    services: &[OrganizerServiceReport],
) {
    assert_eq!(services.len(), 4);
    for service in services {
        let source = actual
            .household_services
            .iter()
            .find(|r| {
                r.principal_id == principal
                    && r.good_id.as_bytes() == service.commodity.good_id
                    && r.unit_id.as_bytes() == service.commodity.unit_id
            })
            .expect("exact household service receipt");
        assert_eq!(
            (
                service.required,
                service.performed,
                service.satisfied,
                service.unmet
            ),
            (
                source.required_quantity,
                source.performed_quantity,
                source.satisfied_quantity,
                source.unmet_quantity
            )
        );
        let orders: BTreeSet<_> = actual
            .service_performance
            .iter()
            .filter(|r| r.good_id == source.good_id && r.buyer == AccountId::Household(principal))
            .map(|r| OutboundOrderId::Service(r.order_id))
            .collect();
        let mut settled = 0;
        let mut refunded = 0;
        for t in &actual.money_transfers {
            match t.purpose {
                MoneyTransferPurpose::DeliverySettlement(id) if orders.contains(&id) => {
                    settled += t.credit.delta.micro_units();
                }
                MoneyTransferPurpose::PurchaseRefund(id) if orders.contains(&id) => {
                    refunded += t.credit.delta.micro_units();
                }
                _ => {}
            }
        }
        assert_eq!(
            (service.settled_micros, service.refunded_micros),
            (settled, refunded)
        );
    }
}

fn check_opening(
    view: &OrganizerView,
    partners: &BTreeSet<u64>,
    config: &OrganizerConfig,
    catalog: &MaterialCatalog,
    state: &MaterialCircuitState,
) {
    let CircuitAccounting::Monetary(economy) = &state.accounting else {
        panic!("monetary opening")
    };
    let recurring = economy
        .recurring
        .as_ref()
        .expect("ordinary household opening");
    let reports = view
        .observations
        .iter()
        .filter(|row| partners.contains(&row.subject_id))
        .collect::<Vec<_>>();
    assert_eq!(
        reports.len(),
        2,
        "each captured known partner shared its opening food assessment"
    );
    assert_eq!(
        reports
            .iter()
            .map(|row| row.subject_id)
            .collect::<BTreeSet<_>>(),
        *partners
    );
    for row in reports {
        let OrganizerReport::Partner {
            facts:
                OrganizerPartnerFacts::OpeningAssessment {
                    commodity,
                    required,
                    opening_stock,
                },
            ..
        } = &row.report
        else {
            panic!("only opening food assessments")
        };
        let binding = config
            .aid_bindings
            .iter()
            .find(|b| b.partner.actor_id == row.subject_id)
            .expect("known subject");
        let principal = FinalDemandPrincipalId::from_bytes(binding.recipient_principal_id);
        let need = catalog
            .household_needs
            .iter()
            .find(|n| {
                n.principal_id == principal
                    && n.good_id.as_bytes() == commodity.good_id
                    && n.unit_id.as_bytes() == commodity.unit_id
            })
            .expect("actual captured need");
        let household = recurring
            .households
            .iter()
            .find(|h| h.principal_id == principal)
            .expect("captured household");
        let quantity = recurring
            .household_stocks
            .iter()
            .filter(|r| {
                r.principal_id == principal
                    && r.good_id == need.good_id
                    && r.unit_id == need.unit_id
            })
            .map(|r| r.quantity)
            .sum::<u64>();
        assert_eq!(
            (*required, *opening_stock),
            (
                need.required_quantity(household)
                    .expect("actual required food"),
                quantity
            )
        );
        assert_eq!((row.observed_period, row.acquired_period), (0, 0));
        assert_eq!(row.source_actor_id, row.subject_id);
        assert_eq!(row.actor_id, view.actor_id);
    }
}
