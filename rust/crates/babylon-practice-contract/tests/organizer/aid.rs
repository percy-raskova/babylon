use super::support;
use babylon_practice_contract::ResolvedOrganizerPeriod;
use babylon_practice_contract::{
    OrganizerAidBinding, OrganizerAidKind, OrganizerAidMaterialPostings, OrganizerAidSupport,
    OrganizerAidSupportStatus, OrganizerChoice, OrganizerCollectionFact,
    OrganizerCollectionMandate, OrganizerCollectionOutcome, OrganizerCommitment, OrganizerConfig,
    OrganizerContribution, OrganizerError, OrganizerGiftConsent, OrganizerHouseholdBinding,
    OrganizerOutcome, OrganizerParticipant, OrganizerPartner, OrganizerPartnerPolicy,
    OrganizerPartnerResponse, OrganizerPeriodTimeResources, OrganizerRefusal, OrganizerState,
    OrganizerTimeBinding, OrganizerTimeBindingMode, OrganizerTimeUse, OrganizerWorkplaceFacts,
    PracticeId, PracticeResourceAllocationMode, PracticeResourceCapacity, PracticeResourceId,
    PracticeResourceOwner, PracticeTargetTag, ORGANIZER_SCHEMA_VERSION,
};
use std::collections::BTreeSet;

fn captured() -> OrganizerConfig {
    let mut config = support::config();
    for (contributor_id, actor_id) in [(204, 105), (205, 106)] {
        config.participants.push(OrganizerParticipant {
            contributor_id,
            label: format!("Independent body {contributor_id}"),
            available_hours: 8,
            commitments: vec![OrganizerContribution { actor_id, hours: 8 }],
            concern: String::new(),
            objection: String::new(),
            review_condition: String::new(),
        });
    }
    config.time_binding = OrganizerTimeBindingMode::Household {
        bindings: config
            .participants
            .iter()
            .map(|row| OrganizerHouseholdBinding {
                contributor_id: row.contributor_id,
                principal_id: [u8::try_from(row.contributor_id)
                    .expect("the fixture value fits the target range");
                    32],
            })
            .collect(),
    };
    config.aid_bindings = [
        (OrganizerAidKind::Local, 105, 204, 51),
        (OrganizerAidKind::Remote, 106, 205, 52),
    ]
    .into_iter()
    .map(|(kind, actor, contributor, tag)| OrganizerAidBinding {
        kind,
        mandate_id: [tag; 32],
        source_hash: [tag + 10; 32],
        donor_contributor_id: 201,
        recipient_contributor_id: contributor,
        donor_principal_id: [201; 32],
        recipient_principal_id: [u8::try_from(contributor)
            .expect("the fixture value fits the target range"); 32],
        social_class_target: [tag + 20; 32],
        receiving_consent: OrganizerGiftConsent::Accept,
        partner: OrganizerPartner {
            actor_id: actor,
            authority_id: [tag; 16],
            label: format!("Aid body {actor}"),
            policy: OrganizerPartnerPolicy::Participate,
            permits_work_report: false,
            permits_maintenance_report: false,
        },
        coordination_hours: 3,
    })
    .collect();
    babylon_practice_contract::validate_organizer_config(&config)
        .expect("the authored organizer config passes validation");
    config
}
pub(crate) fn time(
    config: &OrganizerConfig,
    recipient: u64,
    available: u64,
) -> OrganizerPeriodTimeResources {
    let unit = babylon_practice_contract::organizer_time_unit_id();
    OrganizerPeriodTimeResources {
        period: 1,
        unit_id: unit,
        bindings: config
            .participants
            .iter()
            .map(|row| OrganizerTimeBinding {
                contributor_id: row.contributor_id,
                budget_id: PracticeResourceId::from_bytes(
                    [u8::try_from(row.contributor_id)
                        .expect("the fixture value fits the target range"); 32],
                ),
            })
            .collect(),
        capacities: config
            .participants
            .iter()
            .map(|row| PracticeResourceCapacity {
                owner: PracticeResourceOwner::Shared,
                resource_id: PracticeResourceId::from_bytes(
                    [u8::try_from(row.contributor_id)
                        .expect("the fixture value fits the target range"); 32],
                ),
                unit_id: unit,
                mode: PracticeResourceAllocationMode::DivisibleProRata,
                available: if row.contributor_id == recipient {
                    available
                } else {
                    row.available_hours
                },
            })
            .collect(),
    }
}

#[test]
fn gift_admission_precedes_recipient_time_and_practice_can_fail_afterward() {
    let config = captured();
    let opening = babylon_practice_contract::initial_organizer_state(&config)
        .expect("the authored config admits an opening organizer state");
    let accepted = babylon_practice_contract::admit_organizer(
        &config,
        &opening,
        &support::command(&config, &opening, OrganizerChoice::LocalAid),
    )
    .expect("the fixture admits the organizer actor");
    let gift = babylon_practice_contract::organizer_aid_commitment(&config, &opening, &accepted)
        .expect("the authored aid commitment builds");
    assert_eq!(gift.commitment.resolves_period, 1);
    assert_eq!(gift.recipient_actor_id, 105);
    let next = resolve_supported_aid(
        &config,
        &opening,
        &support::facts(1, 160),
        Some(&accepted),
        &time(&config, 204, 0),
    )
    .expect("the supported aid resolves");
    let receipt = &next
        .journal
        .aid_receipts
        .last()
        .expect("the fixture sequence is non-empty")
        .practice;
    assert_eq!(receipt.outcome, OrganizerOutcome::InsufficientTime);
    assert!(receipt.time_use.is_empty());
    assert_eq!(next.standing, opening.standing);
    assert!(next.contact_products.is_empty());
    assert_eq!(
        next.agreements,
        babylon_practice_contract::reduce_organizer_products(
            &config,
            &opening,
            &support::facts(1, 160)
        )
        .expect("the organizer products aggregate")
        .agreements
    );
    babylon_practice_contract::validate_organizer_aid_commitment(&config, &gift)
        .expect("the authored fixture satisfies the rule");
}

#[test]
fn captured_receiving_consent_does_not_force_partner_practice() {
    let mut config = captured();
    config.aid_bindings[0].partner.policy = OrganizerPartnerPolicy::Refuse;
    let opening = babylon_practice_contract::initial_organizer_state(&config)
        .expect("the authored config admits an opening organizer state");
    let accepted = babylon_practice_contract::admit_organizer(
        &config,
        &opening,
        &support::command(&config, &opening, OrganizerChoice::LocalAid),
    )
    .expect("the fixture admits the organizer actor");
    let gift = babylon_practice_contract::organizer_aid_commitment(&config, &opening, &accepted)
        .expect("the authored aid commitment builds");
    let next = resolve_supported_aid(
        &config,
        &opening,
        &support::facts(1, 160),
        Some(&accepted),
        &time(&config, 204, 0),
    )
    .expect("the supported aid resolves");
    let receipt = &next
        .journal
        .aid_receipts
        .last()
        .expect("the fixture sequence is non-empty")
        .practice;
    assert_eq!(receipt.partner_response, OrganizerPartnerResponse::Refused);
    assert_eq!(receipt.outcome, OrganizerOutcome::AidPracticeUncompleted);
    assert_eq!(receipt.hours_spent, 3);
    assert!(receipt
        .time_use
        .iter()
        .all(|row| row.actor_id == config.controlled_actor_id));
    assert!(next.contact_products.is_empty());
    babylon_practice_contract::validate_organizer_aid_commitment(&config, &gift)
        .expect("the authored fixture satisfies the rule");
}

#[test]
fn both_actual_practices_use_mutual_aid_and_separate_authorities() {
    let config = captured();
    let opening = babylon_practice_contract::initial_organizer_state(&config)
        .expect("the authored config admits an opening organizer state");
    let accepted = babylon_practice_contract::admit_organizer(
        &config,
        &opening,
        &support::command(&config, &opening, OrganizerChoice::LocalAid),
    )
    .expect("the fixture admits the organizer actor");
    let batch = babylon_practice_contract::organizer_resolved_action_batch(
        &config,
        &opening,
        Some(&accepted),
    )
    .expect("the authored resolved batch builds");
    assert_eq!(batch.items.len(), 2);
    let mut authorities = BTreeSet::new();
    for row in &batch.items {
        assert_eq!(row.intent.practice_id, PracticeId::MutualAid);
        assert_eq!(row.intent.target.tag, PracticeTargetTag::SocialClass);
        assert_eq!(
            row.intent.target.identity.as_bytes(),
            config.aid_bindings[0].social_class_target
        );
        assert!(row.intent.parameters.is_empty());
        assert_eq!(row.intent.evidence_digests, vec![[51; 32], [61; 32]]);
        authorities.insert(row.intent.input_authority_id);
    }
    assert_eq!(authorities.len(), 2);
    let next = resolve_supported_aid(
        &config,
        &opening,
        &support::facts(1, 160),
        Some(&accepted),
        &time(&config, 204, 8),
    )
    .expect("the supported aid resolves");
    let receipt = &next
        .journal
        .aid_receipts
        .last()
        .expect("the fixture sequence is non-empty")
        .practice;
    assert_eq!(receipt.outcome, OrganizerOutcome::AidPracticeCompleted);
    assert_eq!(receipt.time_use.iter().map(|row| row.hours).sum::<u64>(), 5);
    assert!(next.contact_products.is_empty());
}

#[test]
fn pending_gift_is_exact_retry_and_refuses_conflicting_nonce_stale_or_source() {
    let config = captured();
    let opening = babylon_practice_contract::initial_organizer_state(&config)
        .expect("the authored config admits an opening organizer state");
    let command = support::command(&config, &opening, OrganizerChoice::LocalAid);
    let first =
        babylon_practice_contract::admit_organizer_aid_pending(&config, &opening, &command, None)
            .expect(
                "the fixture call `admit_organizer_aid_pending` succeeds for the authored inputs",
            );
    assert_eq!(
        babylon_practice_contract::admit_organizer_aid_pending(
            &config,
            &opening,
            &command,
            Some(&first)
        )
        .expect("the fixture call `admit_organizer_aid_pending` succeeds for the authored inputs"),
        first
    );
    let mut conflict = command.clone();
    conflict.nonce[0] ^= 1;
    assert_eq!(
        babylon_practice_contract::admit_organizer_aid_pending(
            &config,
            &opening,
            &conflict,
            Some(&first)
        ),
        Err(OrganizerError::Refused(
            OrganizerRefusal::PendingAidConflict
        ))
    );
    let mut stale = command.clone();
    stale.expected_period = 1;
    assert_eq!(
        babylon_practice_contract::admit_organizer_aid_pending(&config, &opening, &stale, None),
        Err(OrganizerError::Refused(OrganizerRefusal::StalePeriod))
    );
    let mut corrupt = first;
    corrupt.source_hash[0] ^= 1;
    assert_eq!(
        babylon_practice_contract::validate_organizer_aid_commitment(&config, &corrupt),
        Err(OrganizerError::InvalidCommitment)
    );
}

#[test]
fn missing_or_refused_receiving_capture_is_not_fallback_authorization() {
    let config = support::config();
    let opening = babylon_practice_contract::initial_organizer_state(&config)
        .expect("the authored config admits an opening organizer state");
    assert_eq!(
        babylon_practice_contract::admit_organizer(
            &config,
            &opening,
            &support::command(&config, &opening, OrganizerChoice::LocalAid)
        ),
        Err(OrganizerError::Refused(OrganizerRefusal::AidUnavailable))
    );
    let mut config = captured();
    config.aid_bindings[0].receiving_consent = OrganizerGiftConsent::Refuse;
    let opening = babylon_practice_contract::initial_organizer_state(&config)
        .expect("the authored config admits an opening organizer state");
    assert_eq!(
        babylon_practice_contract::admit_organizer(
            &config,
            &opening,
            &support::command(&config, &opening, OrganizerChoice::LocalAid)
        ),
        Err(OrganizerError::Refused(
            OrganizerRefusal::AidReceivingRefused
        ))
    );
}

#[test]
fn later_donor_scarcity_and_wrong_authority_do_not_create_practice_time() {
    let config = captured();
    let opening = babylon_practice_contract::initial_organizer_state(&config)
        .expect("the authored config admits an opening organizer state");
    let mut cmd = support::command(&config, &opening, OrganizerChoice::LocalAid);
    cmd.authority_id = [99; 16];
    assert_eq!(
        babylon_practice_contract::admit_organizer_aid_pending(&config, &opening, &cmd, None),
        Err(OrganizerError::Refused(OrganizerRefusal::WrongAuthority))
    );
    let accepted = babylon_practice_contract::admit_organizer(
        &config,
        &opening,
        &support::command(&config, &opening, OrganizerChoice::LocalAid),
    )
    .expect("the fixture admits the organizer actor");
    let gift = babylon_practice_contract::organizer_aid_commitment(&config, &opening, &accepted)
        .expect("the authored aid commitment builds");
    let next = resolve_supported_aid(
        &config,
        &opening,
        &support::facts(1, 160),
        Some(&accepted),
        &time(&config, 201, 2),
    )
    .expect("the supported aid resolves");
    assert_eq!(
        next.journal
            .aid_receipts
            .last()
            .expect("the fixture sequence is non-empty")
            .practice
            .outcome,
        OrganizerOutcome::InsufficientTime
    );
    assert!(next
        .journal
        .aid_receipts
        .last()
        .expect("the fixture sequence is non-empty")
        .practice
        .time_use
        .is_empty());
    assert_eq!(next.standing, opening.standing);
    babylon_practice_contract::validate_organizer_aid_commitment(&config, &gift)
        .expect("the authored fixture satisfies the rule");
}

#[test]
fn aid_receipt_cannot_be_retyped_into_automatic_contact_agreement() {
    let config = captured();
    let opening = babylon_practice_contract::initial_organizer_state(&config)
        .expect("the authored config admits an opening organizer state");
    let accepted = babylon_practice_contract::admit_organizer(
        &config,
        &opening,
        &support::command(&config, &opening, OrganizerChoice::LocalAid),
    )
    .expect("the fixture admits the organizer actor");
    let next = resolve_supported_aid(
        &config,
        &opening,
        &support::facts(1, 160),
        Some(&accepted),
        &time(&config, 204, 8),
    )
    .expect("the supported aid resolves");
    let mut receipt = next
        .journal
        .aid_receipts
        .last()
        .expect("the fixture sequence is non-empty")
        .practice
        .clone();
    receipt.outcome = OrganizerOutcome::ContactCompleted;
    receipt.contact_product_id = Some([91; 32]);
    assert_eq!(
        babylon_practice_contract::validate_organizer_receipt(&receipt),
        Err(OrganizerError::InvalidState)
    );
}

fn support_for(
    config: &OrganizerConfig,
    accepted: &OrganizerCommitment,
    period: u64,
    status: OrganizerAidSupportStatus,
) -> OrganizerAidSupport {
    let row = config
        .aid_bindings
        .iter()
        .find(|row| match accepted.command.choice {
            OrganizerChoice::LocalAid => row.kind == OrganizerAidKind::Local,
            OrganizerChoice::RemoteAid => row.kind == OrganizerAidKind::Remote,
            _ => false,
        })
        .expect("the fixture holds the searched element");
    let current = period == accepted.resolves_period;
    let granted = match status {
        OrganizerAidSupportStatus::Granted {
            granted_quantity, ..
        } => granted_quantity,
        _ => 0,
    };
    let dispatched = if current {
        match status {
            OrganizerAidSupportStatus::AwaitingDelivery => 1,
            _ => granted,
        }
    } else {
        0
    };
    OrganizerAidSupport {
        original_commitment_id: accepted.commitment_id,
        material_commitment_id: [88; 32],
        mandate_id: row.mandate_id,
        source_hash: row.source_hash,
        dispatch_period: accepted.resolves_period,
        period,
        recipient_principal_id: row.recipient_principal_id,
        good_id: [81; 32],
        unit_id: [82; 32],
        material_postings: OrganizerAidMaterialPostings {
            dispatched_quantity: dispatched,
            fulfillment_hours: dispatched * 2,
            payer_cash_reserved_micros: i128::from(dispatched) * 3,
            payer_cash_granted_micros: i128::from(granted) * 3,
            payer_cash_refunded_micros: 0,
        },
        status,
    }
}
fn resolve_supported_aid(
    config: &OrganizerConfig,
    opening: &OrganizerState,
    facts: &OrganizerWorkplaceFacts,
    accepted: Option<&OrganizerCommitment>,
    resources: &OrganizerPeriodTimeResources,
) -> Result<ResolvedOrganizerPeriod, OrganizerError> {
    let support = support_for(
        config,
        accepted.expect("the fixture audit returns the accepted value"),
        facts.period,
        OrganizerAidSupportStatus::Granted {
            granted_quantity: 1,
            consumed_quantity: 1,
        },
    );
    babylon_practice_contract::resolve_organizer_period_with_time(
        config,
        opening,
        facts,
        accepted,
        resources,
        babylon_practice_contract::OrganizerMaterialSupport {
            aid: &[support],
            collection: None,
        },
    )
}

fn next_resources(config: &OrganizerConfig, period: u64) -> OrganizerPeriodTimeResources {
    let mut resources = time(config, 205, 8);
    resources.period = period;
    resources
}

fn remote_pending() -> (
    OrganizerConfig,
    OrganizerCommitment,
    ResolvedOrganizerPeriod,
) {
    let config = captured();
    let opening = babylon_practice_contract::initial_organizer_state(&config)
        .expect("the authored config admits an opening organizer state");
    let accepted = babylon_practice_contract::admit_organizer(
        &config,
        &opening,
        &support::command(&config, &opening, OrganizerChoice::RemoteAid),
    )
    .expect("the fixture admits the organizer actor");
    let support = support_for(
        &config,
        &accepted,
        1,
        OrganizerAidSupportStatus::AwaitingDelivery,
    );
    let next = babylon_practice_contract::resolve_organizer_period_with_time(
        &config,
        &opening,
        &support::facts(1, 160),
        Some(&accepted),
        &next_resources(&config, 1),
        babylon_practice_contract::OrganizerMaterialSupport {
            aid: &[support],
            collection: None,
        },
    )
    .expect("the organizer period resolves with time");
    (config, accepted, next)
}

#[test]
fn remote_authorization_survives_then_attempts_after_real_grant_and_consumption() {
    let (config, accepted, pending) = remote_pending();
    assert_eq!(pending.pending_aid.len(), 1);
    assert_eq!(
        pending
            .journal
            .receipts
            .last()
            .expect("the fixture sequence is non-empty")
            .outcome,
        OrganizerOutcome::AidScheduled
    );
    assert_eq!(
        pending
            .journal
            .aid_receipts
            .last()
            .expect("the fixture sequence is non-empty")
            .practice
            .outcome,
        OrganizerOutcome::AidAwaitingSupport
    );
    assert_eq!(organizer_actual_time_uses(&pending, 1).count(), 0);
    let encoded = babylon_practice_contract::encode_organizer_state(&pending)
        .expect("the fixture value encodes to its canonical bytes");
    let restored = babylon_practice_contract::decode_organizer_state(&encoded)
        .expect("the canonical bytes decode into the declared type");
    assert_eq!(restored, pending.state);
    // A later ordinary command cannot re-admit the original stale gift.
    assert_eq!(
        babylon_practice_contract::admit_organizer(&config, &restored, &accepted.command),
        Err(OrganizerError::Refused(OrganizerRefusal::StalePeriod))
    );
    let support = support_for(
        &config,
        &accepted,
        2,
        OrganizerAidSupportStatus::Granted {
            granted_quantity: 2,
            consumed_quantity: 1,
        },
    );
    let next = babylon_practice_contract::resolve_organizer_period_with_time(
        &config,
        &restored,
        &support::facts(2, 160),
        None,
        &next_resources(&config, 2),
        babylon_practice_contract::OrganizerMaterialSupport {
            aid: &[support],
            collection: None,
        },
    )
    .expect("the organizer period resolves with time");
    assert!(next.pending_aid.is_empty());
    let row = next
        .journal
        .aid_receipts
        .last()
        .expect("the fixture sequence is non-empty");
    assert_eq!(row.authorization.gift.commitment, accepted);
    assert_eq!(row.authorization.dispatch_period, 1);
    assert_eq!(row.practice.period, 2);
    assert_eq!(row.practice.outcome, OrganizerOutcome::AidPracticeCompleted);
    assert!(row.practice.contact_product_id.is_none());
    assert!(row.practice.observation_ids.is_empty());
    assert!(
        next.journal
            .receipts
            .last()
            .expect("the fixture sequence is non-empty")
            .standing_work
    );
    let later = babylon_practice_contract::resolve_organizer_period_with_time(
        &config,
        &next,
        &support::facts(3, 160),
        None,
        &next_resources(&config, 3),
        babylon_practice_contract::OrganizerMaterialSupport {
            aid: &[],
            collection: None,
        },
    )
    .expect("the organizer period resolves with time");
    assert!(
        later.journal.aid_receipts.is_empty(),
        "a resolved aid attempt is not repeated as a new period receipt"
    );
    assert_eq!(
        organizer_actual_time_uses(&later, 3).count(),
        later
            .journal
            .receipts
            .last()
            .expect("the fixture sequence is non-empty")
            .time_use
            .len()
    );
}

#[test]
fn awaiting_surviving_freight_does_not_turn_ordinary_scarcity_into_aid_failure() {
    let (config, accepted, opening) = remote_pending();
    let support = support_for(
        &config,
        &accepted,
        2,
        OrganizerAidSupportStatus::AwaitingDelivery,
    );
    let mut resources = next_resources(&config, 2);
    for row in &mut resources.capacities {
        row.available = 0;
    }
    let next = babylon_practice_contract::resolve_organizer_period_with_time(
        &config,
        &opening,
        &support::facts(2, 160),
        None,
        &resources,
        babylon_practice_contract::OrganizerMaterialSupport {
            aid: &[support],
            collection: None,
        },
    )
    .expect("the organizer period resolves with time");
    assert_eq!(
        next.journal
            .receipts
            .last()
            .expect("the fixture sequence is non-empty")
            .outcome,
        OrganizerOutcome::InsufficientTime
    );
    assert_eq!(
        next.journal
            .aid_receipts
            .last()
            .expect("the fixture sequence is non-empty")
            .practice
            .outcome,
        OrganizerOutcome::AidAwaitingSupport
    );
    assert_eq!(next.pending_aid, opening.pending_aid);
    assert_eq!(organizer_actual_time_uses(&next, 2).count(), 0);
}

#[test]
fn unshipped_or_granted_unconsumed_support_never_completes_and_retires_once() {
    for status in [
        OrganizerAidSupportStatus::TerminalFailure,
        OrganizerAidSupportStatus::Granted {
            granted_quantity: 2,
            consumed_quantity: 0,
        },
    ] {
        let config = captured();
        let opening = babylon_practice_contract::initial_organizer_state(&config)
            .expect("the authored config admits an opening organizer state");
        let accepted = babylon_practice_contract::admit_organizer(
            &config,
            &opening,
            &support::command(&config, &opening, OrganizerChoice::LocalAid),
        )
        .expect("the fixture admits the organizer actor");
        let support = support_for(&config, &accepted, 1, status);
        let next = babylon_practice_contract::resolve_organizer_period_with_time(
            &config,
            &opening,
            &support::facts(1, 160),
            Some(&accepted),
            &next_resources(&config, 1),
            babylon_practice_contract::OrganizerMaterialSupport {
                aid: &[support],
                collection: None,
            },
        )
        .expect("the organizer period resolves with time");
        assert!(next.pending_aid.is_empty());
        assert_eq!(
            next.journal
                .aid_receipts
                .last()
                .expect("the fixture sequence is non-empty")
                .practice
                .outcome,
            OrganizerOutcome::AidNotProvisioned
        );
        assert_eq!(organizer_actual_time_uses(&next, 1).count(), 0);
        assert_eq!(
            next.agreements,
            babylon_practice_contract::reduce_organizer_products(
                &config,
                &opening,
                &support::facts(1, 160)
            )
            .expect("the organizer products aggregate")
            .agreements
        );
    }
}

#[test]
fn missing_foreign_duplicate_future_and_changed_support_fail_without_mutating_opening() {
    let (config, accepted, opening) = remote_pending();
    let before = opening.clone();
    let valid = support_for(
        &config,
        &accepted,
        2,
        OrganizerAidSupportStatus::Granted {
            granted_quantity: 1,
            consumed_quantity: 1,
        },
    );
    assert_eq!(
        babylon_practice_contract::resolve_organizer_period_with_time(
            &config,
            &opening,
            &support::facts(2, 160),
            None,
            &next_resources(&config, 2),
            babylon_practice_contract::OrganizerMaterialSupport {
                aid: &[],
                collection: None,
            }
        ),
        Err(OrganizerError::AidSupportMissing)
    );
    for invalid in 0..5 {
        let mut row = valid.clone();
        match invalid {
            0 => row.source_hash[0] ^= 1,
            1 => row.material_commitment_id[0] ^= 1,
            2 => row.good_id[0] ^= 1,
            3 => row.period = 3,
            _ => row.recipient_principal_id[0] ^= 1,
        }
        assert_eq!(
            babylon_practice_contract::resolve_organizer_period_with_time(
                &config,
                &opening,
                &support::facts(2, 160),
                None,
                &next_resources(&config, 2),
                babylon_practice_contract::OrganizerMaterialSupport {
                    aid: &[row],
                    collection: None,
                }
            ),
            Err(OrganizerError::AidSupportMismatch)
        );
    }
    assert_eq!(
        babylon_practice_contract::resolve_organizer_period_with_time(
            &config,
            &opening,
            &support::facts(2, 160),
            None,
            &next_resources(&config, 2),
            babylon_practice_contract::OrganizerMaterialSupport {
                aid: &[valid.clone(), valid],
                collection: None,
            }
        ),
        Err(OrganizerError::AidSupportMissing)
    );
    assert_eq!(opening, before);
}

#[test]
fn delayed_partner_authority_tamper_and_third_pending_slot_refuse() {
    let (config, _accepted, opening) = remote_pending();
    let mut altered = opening.state.clone();
    altered.pending_aid[0].partner_authorization.authority_id = [99; 16];
    assert!(babylon_practice_contract::validate_organizer_pair(&config, &altered).is_err());
    let mut oversized = opening.state.clone();
    oversized.pending_aid = vec![opening.pending_aid[0].clone(); 3];
    assert_eq!(
        babylon_practice_contract::validate_organizer_state(&oversized),
        Err(OrganizerError::SizeLimit)
    );
    let fresh = support::command(&config, &opening, OrganizerChoice::RemoteAid);
    assert_eq!(
        babylon_practice_contract::admit_organizer(&config, &opening, &fresh),
        Err(OrganizerError::Refused(
            OrganizerRefusal::PendingAidConflict
        ))
    );
    let batch = babylon_practice_contract::organizer_resolved_action_batch(&config, &opening, None)
        .expect("the authored resolved batch builds");
    let delayed = batch
        .items
        .iter()
        .filter(|row| row.intent.practice_id == PracticeId::MutualAid)
        .collect::<Vec<_>>();
    assert_eq!(delayed.len(), 2);
    for row in &delayed {
        assert_eq!(row.intent.resolve_tick, 2);
        assert!(row
            .intent
            .evidence_digests
            .contains(&opening.pending_aid[0].gift.commitment.commitment_id));
        assert!(row
            .intent
            .evidence_digests
            .contains(&opening.pending_aid[0].material_commitment_id));
    }
    assert_ne!(
        delayed[0].intent.input_authority_id,
        delayed[1].intent.input_authority_id
    );
}

#[test]
fn later_ordinary_work_precedes_aid_and_cannot_double_spend_actual_supply() {
    let (config, accepted, opening) = remote_pending();
    let mut resources = next_resources(&config, 2);
    let donor = resources
        .bindings
        .iter()
        .find(|row| row.contributor_id == 201)
        .expect("the fixture holds the searched element")
        .budget_id;
    resources
        .capacities
        .iter_mut()
        .find(|row| row.resource_id == donor)
        .expect("the fixture holds the searched element")
        .available = 10;
    let support = support_for(
        &config,
        &accepted,
        2,
        OrganizerAidSupportStatus::Granted {
            granted_quantity: 2,
            consumed_quantity: 1,
        },
    );
    let next = babylon_practice_contract::resolve_organizer_period_with_time(
        &config,
        &opening,
        &support::facts(2, 160),
        None,
        &resources,
        babylon_practice_contract::OrganizerMaterialSupport {
            aid: &[support],
            collection: None,
        },
    )
    .expect("the organizer period resolves with time");
    assert_eq!(
        next.journal
            .receipts
            .last()
            .expect("the fixture sequence is non-empty")
            .hours_spent,
        config.contact_hours
    );
    assert_eq!(
        next.journal
            .aid_receipts
            .last()
            .expect("the fixture sequence is non-empty")
            .practice
            .outcome,
        OrganizerOutcome::InsufficientTime
    );
    assert!(next.pending_aid.is_empty());
    assert_eq!(
        organizer_actual_time_uses(&next, 2)
            .filter(|row| row.contributor_id == 201)
            .map(|row| row.hours)
            .sum::<u64>(),
        config.contact_hours
    );
}

#[test]
fn independently_refused_delayed_practice_keeps_valid_grant_and_consumption_evidence() {
    let mut config = captured();
    config.aid_bindings[1].partner.policy = OrganizerPartnerPolicy::Refuse;
    let opening = babylon_practice_contract::initial_organizer_state(&config)
        .expect("the authored config admits an opening organizer state");
    let accepted = babylon_practice_contract::admit_organizer(
        &config,
        &opening,
        &support::command(&config, &opening, OrganizerChoice::RemoteAid),
    )
    .expect("the fixture admits the organizer actor");
    let wait = support_for(
        &config,
        &accepted,
        1,
        OrganizerAidSupportStatus::AwaitingDelivery,
    );
    let dispatched = babylon_practice_contract::resolve_organizer_period_with_time(
        &config,
        &opening,
        &support::facts(1, 160),
        Some(&accepted),
        &next_resources(&config, 1),
        babylon_practice_contract::OrganizerMaterialSupport {
            aid: &[wait],
            collection: None,
        },
    )
    .expect("the organizer period resolves with time");
    let granted = support_for(
        &config,
        &accepted,
        2,
        OrganizerAidSupportStatus::Granted {
            granted_quantity: 2,
            consumed_quantity: 1,
        },
    );
    let next = babylon_practice_contract::resolve_organizer_period_with_time(
        &config,
        &dispatched,
        &support::facts(2, 160),
        None,
        &next_resources(&config, 2),
        babylon_practice_contract::OrganizerMaterialSupport {
            aid: std::slice::from_ref(&granted),
            collection: None,
        },
    )
    .expect("the organizer period resolves with time");
    let row = next
        .journal
        .aid_receipts
        .last()
        .expect("the fixture sequence is non-empty");
    assert_eq!(row.support, granted);
    assert_eq!(
        row.practice.outcome,
        OrganizerOutcome::AidPracticeUncompleted
    );
    assert_eq!(
        row.practice.partner_response,
        OrganizerPartnerResponse::Refused
    );
    assert!(!row
        .practice
        .time_use
        .iter()
        .any(|use_row| use_row.actor_id == 106));
    assert!(row.practice.contact_product_id.is_none());
    assert!(next.pending_aid.is_empty());
}

#[test]
fn product_reduction_can_carry_pending_authorization_but_cannot_be_saved_before_resolution() {
    let (config, _accepted, opening) = remote_pending();
    let reduced = babylon_practice_contract::reduce_organizer_products(
        &config,
        &opening,
        &support::facts(2, 160),
    )
    .expect("the organizer products aggregate");
    assert_eq!(reduced.pending_aid, opening.pending_aid);
    assert_eq!(
        babylon_practice_contract::validate_organizer_journal(
            &config,
            &reduced,
            &support::journal_of(&reduced.journal),
        ),
        Err(OrganizerError::InvalidState)
    );
}

fn organizer_actual_time_uses(
    period_state: &ResolvedOrganizerPeriod,
    _period: u64,
) -> impl Iterator<Item = &OrganizerTimeUse> {
    babylon_practice_contract::organizer_period_receipts(&period_state.journal)
        .flat_map(|row| row.time_use.iter())
}

#[test]
fn pending_original_date_and_nonce_cannot_be_rewritten_as_current_admission() {
    let (config, accepted, opening) = remote_pending();
    let before = opening.clone();
    for changed in 0..3 {
        let mut forged = opening.state.clone();
        let original = &mut forged.pending_aid[0].gift.commitment;
        match changed {
            0 => original.command.expected_period = opening.period,
            1 => original.command.nonce[0] ^= 1,
            _ => original.commitment_id[0] ^= 1,
        }
        assert!(
            babylon_practice_contract::organizer_resolved_action_batch(&config, &forged, None)
                .is_err()
        );
        assert!(babylon_practice_contract::encode_organizer_state(&forged).is_err());
    }
    assert_eq!(opening, before);
    assert_eq!(opening.pending_aid[0].gift.commitment, accepted);
}

#[test]
fn cutting_real_support_with_unrelated_free_time_blocks_delayed_completion() {
    let (config, accepted, opening) = remote_pending();
    for status in [
        OrganizerAidSupportStatus::TerminalFailure,
        OrganizerAidSupportStatus::Granted {
            granted_quantity: 2,
            consumed_quantity: 0,
        },
    ] {
        let support = support_for(&config, &accepted, 2, status);
        let next = babylon_practice_contract::resolve_organizer_period_with_time(
            &config,
            &opening,
            &support::facts(2, 160),
            None,
            &next_resources(&config, 2),
            babylon_practice_contract::OrganizerMaterialSupport {
                aid: &[support],
                collection: None,
            },
        )
        .expect("the organizer period resolves with time");
        let row = next
            .journal
            .aid_receipts
            .last()
            .expect("the fixture sequence is non-empty");
        assert_eq!(row.practice.outcome, OrganizerOutcome::AidNotProvisioned);
        assert!(row.practice.time_use.is_empty());
        assert!(next.pending_aid.is_empty());
        // Ordinary authorized standing work still ran; it is not aid completion.
        assert!(
            next.journal
                .receipts
                .last()
                .expect("the fixture sequence is non-empty")
                .standing_work
        );
    }
}

#[test]
fn current_aid_support_requires_actual_postings_and_exact_decimal_money() {
    let (_, _, pending) = remote_pending();
    let mut entries = serde_json::to_value(&pending.journal).expect("the value serializes to JSON");
    entries["aid_receipts"][0]["support"]
        .as_object_mut()
        .expect("the JSON fixture field is an object")
        .remove("material_postings");
    assert!(
        serde_json::from_value::<babylon_practice_contract::OrganizerPeriodJournalEntries>(entries)
            .is_err()
    );

    let mut support = serde_json::to_value(&pending.journal.aid_receipts[0].support)
        .expect("the value serializes to JSON");
    support["material_postings"] = serde_json::json!({
        "dispatched_quantity": 1,
        "fulfillment_hours": 2,
        "payer_cash_reserved_micros": "9007199254740993",
        "payer_cash_granted_micros": "0",
        "payer_cash_refunded_micros": "0"
    });
    let decoded: OrganizerAidSupport =
        serde_json::from_value(support.clone()).expect("the JSON value matches the declared type");
    assert_eq!(
        serde_json::to_value(decoded).expect("the value serializes to JSON"),
        support
    );
    for invalid in [
        serde_json::json!(0),
        serde_json::json!("-1"),
        serde_json::json!("-0"),
        serde_json::json!("+0"),
        serde_json::json!("01"),
        serde_json::json!("1.0"),
        serde_json::json!("170141183460469231731687303715884105728"),
    ] {
        let mut malformed = support.clone();
        malformed["material_postings"]["payer_cash_reserved_micros"] = invalid;
        assert!(serde_json::from_value::<OrganizerAidSupport>(malformed).is_err());
    }
}

#[test]
fn later_support_cannot_repeat_dispatch_postings_or_foreign_actor_authority() {
    let (config, accepted, opening) = remote_pending();
    let valid = support_for(
        &config,
        &accepted,
        2,
        OrganizerAidSupportStatus::Granted {
            granted_quantity: 1,
            consumed_quantity: 1,
        },
    );
    for (field, value) in [
        ("dispatched_quantity", serde_json::json!(1)),
        ("fulfillment_hours", serde_json::json!(1)),
        ("payer_cash_reserved_micros", serde_json::json!("3")),
    ] {
        let mut row = serde_json::to_value(&valid).expect("the value serializes to JSON");
        row["material_postings"][field] = value;
        let row: OrganizerAidSupport =
            serde_json::from_value(row).expect("the JSON value matches the declared type");
        assert_eq!(
            babylon_practice_contract::resolve_organizer_period_with_time(
                &config,
                &opening,
                &support::facts(2, 160),
                None,
                &next_resources(&config, 2),
                babylon_practice_contract::OrganizerMaterialSupport {
                    aid: &[row],
                    collection: None,
                }
            ),
            Err(OrganizerError::AidSupportMismatch)
        );
    }
    let mut foreign = opening.state.clone();
    foreign.pending_aid[0].gift.donor_actor_id = config.aid_bindings[0].partner.actor_id;
    assert!(babylon_practice_contract::validate_organizer_pair(&config, &foreign).is_err());
    assert_eq!(opening.pending_aid[0].gift.commitment, accepted);
}

#[test]
fn current_organizer_refuses_prior_schema_even_without_aid() {
    assert_eq!(ORGANIZER_SCHEMA_VERSION, 8);
    let mut prior = support::config();
    prior.schema_version = 6;
    assert_eq!(
        babylon_practice_contract::validate_organizer_config(&prior),
        Err(OrganizerError::UnsupportedSchema)
    );
    let mut config_bytes = b"babylon.organizer-config.v6\0".to_vec();
    config_bytes.extend_from_slice(
        &serde_json::to_vec(&prior).expect("the value serializes to canonical JSON bytes"),
    );
    assert!(babylon_practice_contract::decode_organizer_config(&config_bytes).is_err());
    let mut state = babylon_practice_contract::initial_organizer_state(&support::config())
        .expect("the authored config admits an opening organizer state");
    state.schema_version = 6;
    let mut state_bytes = b"babylon.organizer-state.v4\0".to_vec();
    state_bytes.extend_from_slice(
        &serde_json::to_vec(&state).expect("the value serializes to canonical JSON bytes"),
    );
    assert!(babylon_practice_contract::decode_organizer_state(&state_bytes).is_err());
}

#[test]
#[allow(
    clippy::too_many_lines,
    reason = "one scenario asserts the whole capture-to-resolution chain; splitting it would duplicate the fixture setup"
)]
fn collection_ack_does_not_recharge_material_time_before_delayed_aid() {
    let mut config = captured();
    config.collection = Some(OrganizerCollectionMandate {
        mandate_id: [93; 32],
        source_hash: [94; 32],
        actor_id: 101,
        contributor_id: 201,
        household_principal_id: [201; 32],
        organization_account_id: [96; 32],
        social_class_target: [98; 32],
        labor_unit_id: babylon_practice_contract::organizer_time_unit_id().as_bytes(),
        cash_consent: OrganizerGiftConsent::Accept,
        maximum_cash_micros: 2,
        protected_cash_floor_micros: 0,
        collection_hours: 2,
    });
    let first = babylon_practice_contract::initial_organizer_state(&config)
        .expect("the authored config admits an opening organizer state");
    let gift = babylon_practice_contract::admit_organizer(
        &config,
        &first,
        &support::command(&config, &first, OrganizerChoice::RemoteAid),
    )
    .expect("the fixture admits the organizer actor");
    let waiting = support_for(
        &config,
        &gift,
        1,
        OrganizerAidSupportStatus::AwaitingDelivery,
    );
    let pending = babylon_practice_contract::resolve_organizer_period_with_time(
        &config,
        &first,
        &support::facts(1, 160),
        Some(&gift),
        &next_resources(&config, 1),
        babylon_practice_contract::OrganizerMaterialSupport {
            aid: &[waiting],
            collection: None,
        },
    )
    .expect("the organizer period resolves with time");
    let accepted = babylon_practice_contract::admit_organizer(
        &config,
        &pending,
        &support::command(&config, &pending, OrganizerChoice::Collect),
    )
    .expect("the fixture admits the organizer actor");
    let grant = support_for(
        &config,
        &gift,
        2,
        OrganizerAidSupportStatus::Granted {
            granted_quantity: 2,
            consumed_quantity: 1,
        },
    );
    // Three hours are supplied AFTER material consumed two collection hours.
    // Double-debiting those two makes real three-hour later coordination fail.
    let mut resources = next_resources(&config, 2);
    resources
        .capacities
        .iter_mut()
        .find(|row| row.resource_id.as_bytes() == [201; 32])
        .expect("the fixture holds the searched element")
        .available = 3;
    let mut bytes = b"babylon.collection-household-contribution.v1\0".to_vec();
    bytes.extend_from_slice(&accepted.commitment_id);
    bytes.extend_from_slice(&[93; 32]);
    for value in [2_u64, 101, 201] {
        bytes.extend_from_slice(&value.to_be_bytes());
    }
    bytes.extend_from_slice(&[201; 32]);
    bytes.extend_from_slice(&babylon_practice_contract::organizer_time_unit_id().as_bytes());
    let fact = OrganizerCollectionFact {
        period: 2,
        admitted_period: 1,
        original_commitment_id: accepted.commitment_id,
        command_nonce: accepted.command.nonce,
        mandate_id: [93; 32],
        source_hash: [94; 32],
        actor_id: 101,
        contributor_id: 201,
        household_principal_id: [201; 32],
        organization_account_id: [96; 32],
        labor_unit_id: babylon_practice_contract::organizer_time_unit_id().as_bytes(),
        requested_cash_micros: 2,
        collected_cash_micros: 2,
        performed_hours: 2,
        outcome: OrganizerCollectionOutcome::Collected,
        transfer_ordinal: Some(0),
        contribution_use_id: babylon_kernel::content_digest::sha256_of(&bytes),
    };
    let next = babylon_practice_contract::resolve_organizer_period_with_time(
        &config,
        &pending,
        &support::facts(2, 160),
        Some(&accepted),
        &resources,
        babylon_practice_contract::OrganizerMaterialSupport {
            aid: std::slice::from_ref(&grant),
            collection: Some(&fact),
        },
    )
    .expect("the organizer period resolves with time");
    assert_eq!(next.journal.collection_receipts.len(), 1);
    assert_eq!(next.journal.collection_receipts[0].commitment, accepted);
    assert_eq!(
        next.journal
            .aid_receipts
            .last()
            .expect("the fixture sequence is non-empty")
            .practice
            .outcome,
        OrganizerOutcome::AidPracticeCompleted
    );
    assert_eq!(
        next.journal
            .aid_receipts
            .last()
            .expect("the fixture sequence is non-empty")
            .practice
            .hours_spent,
        3
    );
    assert_eq!(next.journal.collection_receipts[0].practice.hours_spent, 2);
    assert_eq!(next.agreements, pending.agreements);
    for field in [0_u8, 1, 2, 3] {
        let mut changed = fact.clone();
        match field {
            0 => changed.original_commitment_id = [3; 32],
            1 => changed.command_nonce = [9; 16],
            2 => changed.contribution_use_id = [4; 32],
            _ => changed.actor_id = 102,
        }
        assert!(
            babylon_practice_contract::resolve_organizer_period_with_time(
                &config,
                &pending,
                &support::facts(2, 160),
                Some(&accepted),
                &resources,
                babylon_practice_contract::OrganizerMaterialSupport {
                    aid: std::slice::from_ref(&grant),
                    collection: Some(&changed),
                }
            )
            .is_err()
        );
    }
    assert_eq!(pending.pending_aid.len(), 1);
}
