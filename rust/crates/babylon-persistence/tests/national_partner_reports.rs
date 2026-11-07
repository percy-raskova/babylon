//! Disclosed partner knowledge in an ordinary national campaign.
use babylon_kernel::replay::{ReplaySeed, ReplaySessionId};
use babylon_material_circuit::AccountId;
use babylon_material_circuit::MaterialCatalog;
use babylon_material_circuit::MaterialCircuitState;
use babylon_material_circuit::{
    CircuitAccounting, FinalDemandPrincipalId, HouseholdTimeAccounting, HouseholdTimeBook,
};
use babylon_material_circuit::{MoneyTransferPurpose, OutboundOrderId};
use babylon_persistence::economic_catalog::{self, CapturedEconomicCatalog};
use babylon_persistence::identity::CampaignId;
use babylon_persistence::qualification_audit::aid;
use babylon_practice_contract::OrganizerConfig;
use babylon_practice_contract::OrganizerView;
use babylon_practice_contract::{OrganizerPartnerFacts, OrganizerReport, OrganizerServiceReport};
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
    let reports: Vec<_> = end
        .view
        .observations
        .iter()
        .filter(|r| r.observed_period == 1 && partners.contains(&r.subject_id))
        .collect();
    assert_eq!(reports.len(), 6);
    let CircuitAccounting::Monetary(economy) = &committed.state().accounting else {
        panic!("modeled cash")
    };
    let HouseholdTimeAccounting::Modeled(book) = &economy.household_time else {
        panic!("modeled household hours")
    };
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
        let principal = babylon_material_circuit::FinalDemandPrincipalId::from_bytes(
            binding.recipient_principal_id,
        );
        let OrganizerReport::Partner { facts, .. } = &row.report else {
            panic!("partner report")
        };
        check_completed(principal, &actual, book, facts);
    }
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
