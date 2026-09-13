use std::collections::{BTreeMap, BTreeSet};

use babylon_kernel::content_digest::sha256_of;

use super::contract::{committed_hours, identity, required_hours, validate_organizer_pair};
use super::*;
use crate::{
    allocate_practice_resources, derive_practice_resource_request, ActorOrganizationId,
    InputAuthorityId, PracticeId, PracticeIntent, PracticeParameter,
    PracticeResourceAllocationContract, PracticeResourceAllocationMode, PracticeResourceCapacity,
    PracticeResourceId, PracticeResourceLocator, PracticeResourceOwner,
    PracticeResourceRequirement, PracticeTargetIdentity, PracticeTargetTag, PracticeUnitId,
    ProposalNonce, TaggedPracticeTarget,
};

fn target_identity(domain: &[u8], id: u64) -> [u8; 32] {
    let mut bytes = Vec::from(domain);
    bytes.extend_from_slice(&id.to_be_bytes());
    sha256_of(&bytes)
}

/// Bind every accepted ruling to the common practice input identity, including
/// controls that spend no time and execute no contact work.
pub fn organizer_practice_intent(
    config: &OrganizerConfig,
    state: &OrganizerState,
    commitment: &OrganizerCommitment,
) -> Result<PracticeIntent, OrganizerError> {
    practice_intent_with_origin(config, state, commitment, false)
}

fn practice_intent_with_origin(
    config: &OrganizerConfig,
    state: &OrganizerState,
    commitment: &OrganizerCommitment,
    standing_origin: bool,
) -> Result<PracticeIntent, OrganizerError> {
    validate_organizer_pair(config, state)?;
    if admit_organizer(config, state, &commitment.command)? != *commitment {
        return Err(OrganizerError::InvalidCommitment);
    }
    let (practice, tag, target_id, parameters) = match commitment.command.choice {
        OrganizerChoice::Inquiry(question) => (
            PracticeId::Investigate,
            PracticeTargetTag::Facility,
            config.workplace_id,
            vec![PracticeParameter {
                key_u8: 1,
                value_kind_u8: 1,
                value_length_u16: 1,
                value_bytes: vec![match question {
                    OrganizerInquiry::WorkLost => 1,
                    OrganizerInquiry::MaintenanceReceived => 2,
                }],
            }],
        ),
        OrganizerChoice::Reinforce => (
            PracticeId::Organize,
            PracticeTargetTag::Organization,
            config.workplace_partner.actor_id,
            control_parameter(1),
        ),
        OrganizerChoice::Hold => (
            PracticeId::Organize,
            PracticeTargetTag::Organization,
            config.neighborhood_partner.actor_id,
            control_parameter(if standing_origin { 5 } else { 2 }),
        ),
        OrganizerChoice::PauseStanding => (
            PracticeId::Organize,
            PracticeTargetTag::Organization,
            config.neighborhood_partner.actor_id,
            control_parameter(3),
        ),
        OrganizerChoice::ResumeStanding => (
            PracticeId::Organize,
            PracticeTargetTag::Organization,
            config.neighborhood_partner.actor_id,
            control_parameter(4),
        ),
    };
    let value = PracticeIntent {
        schema_version: 2,
        submit_after_tick: state.period,
        resolve_tick: commitment.resolves_period,
        input_authority_id: InputAuthorityId::from_bytes(commitment.command.authority_id),
        actor_org_id: ActorOrganizationId::from_bytes(commitment.command.actor_id.to_be_bytes()),
        practice_id: practice,
        target: TaggedPracticeTarget {
            tag,
            identity: PracticeTargetIdentity::from_bytes(target_identity(
                b"babylon.organizer-target.v1",
                target_id,
            )),
        },
        proposal_nonce: ProposalNonce::from_bytes(commitment.command.nonce),
        quoted_content_digest: commitment.command.content_digest,
        quoted_resource_contract_digest: commitment.command.resource_digest,
        parameters,
        evidence_digests: vec![],
    };
    crate::validate_practice_intent(&value).map_err(|_| OrganizerError::InvalidCommitment)?;
    Ok(value)
}

fn control_parameter(value: u8) -> Vec<PracticeParameter> {
    vec![PracticeParameter {
        key_u8: 2,
        value_kind_u8: 1,
        value_length_u16: 1,
        value_bytes: vec![value],
    }]
}

fn has_agreement(
    state: &OrganizerState,
    actor_id: u64,
    partner_actor_id: u64,
    period: u64,
) -> bool {
    state.agreements.iter().any(|row| {
        row.actor_id == actor_id
            && row.partner_actor_id == partner_actor_id
            && row.valid_from_period <= period
            && period <= row.valid_through_period
    })
}

fn add_observation(
    state: &mut OrganizerState,
    config: &OrganizerConfig,
    observed_period: u64,
    acquired_period: u64,
    receipt_id: Option<[u8; 32]>,
    report: OrganizerReport,
) -> Result<[u8; 32], OrganizerError> {
    let observation_id = identity(
        b"babylon.organizer-observation.v1",
        &(
            config.controlled_actor_id,
            config.workplace_id,
            config.workplace_partner.actor_id,
            observed_period,
            acquired_period,
            receipt_id,
            &report,
        ),
    )?;
    if state
        .observations
        .iter()
        .any(|row| row.observation_id == observation_id)
    {
        return Err(OrganizerError::InvalidState);
    }
    state.observations.push(OrganizerObservation {
        observation_id,
        actor_id: config.controlled_actor_id,
        subject_id: config.workplace_id,
        source_actor_id: config.workplace_partner.actor_id,
        observed_period,
        acquired_period,
        receipt_id,
        report,
    });
    Ok(observation_id)
}

/// Endogenous reducer: only products in the opening committed state can renew
/// cooperation. Newly closed material facts can publish an attributed report
/// inside the same detached transaction; no report escapes a failed tick.
pub fn reduce_organizer_products(
    config: &OrganizerConfig,
    opening: &OrganizerState,
    facts: &OrganizerWorkplaceFacts,
) -> Result<OrganizerState, OrganizerError> {
    let contacts = consume_organizer_contact_products(config, opening, facts.period)?;
    report_organizer_workplace(config, opening, &contacts, facts)
}

/// Consume retained contact receipts without fabricating a report. This
/// separately testable reducer is the causal consumer of completed contact.
pub fn consume_organizer_contact_products(
    config: &OrganizerConfig,
    opening: &OrganizerState,
    resolve_period: u64,
) -> Result<OrganizerState, OrganizerError> {
    validate_organizer_pair(config, opening)?;
    if opening.period.checked_add(1) != Some(resolve_period) {
        return Err(OrganizerError::PeriodMismatch);
    }
    let mut next = opening.clone();
    let consumed: BTreeSet<_> = opening.consumed_product_ids.iter().copied().collect();
    for product in &opening.contact_products {
        if consumed.contains(&product.product_id) {
            continue;
        }
        if product.produced_period >= resolve_period {
            return Err(OrganizerError::InvalidState);
        }
        let from = product
            .produced_period
            .checked_add(1)
            .ok_or(OrganizerError::Arithmetic)?;
        let through = product
            .produced_period
            .checked_add(config.contact_renewal_periods)
            .ok_or(OrganizerError::Arithmetic)?;
        let agreement = next
            .agreements
            .iter_mut()
            .find(|row| {
                row.actor_id == product.actor_id && row.partner_actor_id == product.partner_actor_id
            })
            .ok_or(OrganizerError::InvalidState)?;
        if through > agreement.valid_through_period {
            // A lapsed agreement can be renewed through an existing relationship.
            if agreement
                .valid_through_period
                .checked_add(1)
                .is_none_or(|end| end < from)
            {
                agreement.valid_from_period = from;
            }
            agreement.valid_through_period = through;
            agreement.source_product_id = Some(product.product_id);
        }
        next.consumed_product_ids.push(product.product_id);
    }
    validate_organizer_pair(config, &next)?;
    Ok(next)
}

/// Publish the material signal only while an actual report-sharing agreement
/// remains in force. Omitting the contact consumer cannot sustain this access.
pub fn report_organizer_workplace(
    config: &OrganizerConfig,
    opening: &OrganizerState,
    contacts: &OrganizerState,
    facts: &OrganizerWorkplaceFacts,
) -> Result<OrganizerState, OrganizerError> {
    validate_organizer_pair(config, opening)?;
    validate_organizer_pair(config, contacts)?;
    if opening.period.checked_add(1) != Some(facts.period)
        || contacts.period != opening.period
        || facts.workplace_id != config.workplace_id
    {
        return Err(OrganizerError::PeriodMismatch);
    }
    let mut next = contacts.clone();
    next.period = facts.period;
    next.last_workplace_facts = Some(facts.clone());
    if config.workplace_partner.permits_work_report
        && config.workplace_partner.policy == OrganizerPartnerPolicy::Participate
        && has_agreement(
            &next,
            config.controlled_actor_id,
            config.workplace_partner.actor_id,
            facts.period,
        )
    {
        if let Some(previous) = &opening.last_workplace_facts {
            if facts.performed_labor_hours < previous.performed_labor_hours {
                add_observation(
                    &mut next,
                    config,
                    facts.period,
                    facts.period,
                    None,
                    OrganizerReport::ReducedWork {
                        previous_labor_hours: previous.performed_labor_hours,
                        performed_labor_hours: facts.performed_labor_hours,
                    },
                )?;
            }
        }
    }
    validate_organizer_pair(config, &next)?;
    Ok(next)
}

fn routine_commitment(
    config: &OrganizerConfig,
    opening: &OrganizerState,
) -> Result<OrganizerCommitment, OrganizerError> {
    let resolves_period = opening
        .period
        .checked_add(1)
        .ok_or(OrganizerError::Arithmetic)?;
    let digest = identity(
        b"babylon.organizer-routine-nonce.v1",
        &(
            config.campaign_id,
            config.controlled_actor_id,
            resolves_period,
        ),
    )?;
    let mut nonce = [0; 16];
    nonce.copy_from_slice(&digest[..16]);
    let command = OrganizerCommand {
        campaign_id: config.campaign_id,
        actor_id: config.controlled_actor_id,
        authority_id: config.input_authority_id,
        expected_period: opening.period,
        content_digest: config.content_digest,
        resource_digest: organizer_resource_digest()?,
        nonce,
        choice: OrganizerChoice::Hold,
    };
    Ok(OrganizerCommitment {
        commitment_id: identity(b"babylon.organizer-commitment.v1", &command)?,
        command,
        resolves_period,
    })
}

fn partner_for_choice(
    config: &OrganizerConfig,
    choice: OrganizerChoice,
) -> Option<&OrganizerPartner> {
    match choice {
        OrganizerChoice::Inquiry(_) | OrganizerChoice::Reinforce => Some(&config.workplace_partner),
        OrganizerChoice::Hold | OrganizerChoice::ResumeStanding => {
            Some(&config.neighborhood_partner)
        }
        OrganizerChoice::PauseStanding => None,
    }
}

fn partner_response(
    config: &OrganizerConfig,
    partner: &OrganizerPartner,
) -> Result<OrganizerPartnerResponse, OrganizerError> {
    match partner.policy {
        OrganizerPartnerPolicy::Refuse => Ok(OrganizerPartnerResponse::Refused),
        OrganizerPartnerPolicy::NoResponse => Ok(OrganizerPartnerResponse::NoResponse),
        OrganizerPartnerPolicy::Participate => Ok(
            if committed_hours(config, partner.actor_id)? >= config.partner_response_hours {
                OrganizerPartnerResponse::Participated
            } else {
                OrganizerPartnerResponse::UnableToParticipate
            },
        ),
    }
}

fn response_intent(
    intent: &PracticeIntent,
    config: &OrganizerConfig,
    partner: &OrganizerPartner,
) -> Result<PracticeIntent, OrganizerError> {
    let originating_digest =
        crate::practice_intent_digest(intent).map_err(|_| OrganizerError::InvalidCommitment)?;
    let digest = identity(
        b"babylon.organizer-response-nonce.v1",
        &(originating_digest, partner.actor_id),
    )?;
    let mut nonce = [0_u8; 16];
    nonce.copy_from_slice(&digest[..16]);
    let mut response = intent.clone();
    response.proposal_nonce = ProposalNonce::from_bytes(nonce);
    response.actor_org_id = ActorOrganizationId::from_bytes(partner.actor_id.to_be_bytes());
    response.input_authority_id = InputAuthorityId::from_bytes(partner.authority_id);
    response.practice_id = PracticeId::Organize;
    response.target.tag = PracticeTargetTag::Organization;
    response.target.identity = PracticeTargetIdentity::from_bytes(target_identity(
        b"babylon.organizer-target.v1",
        config.controlled_actor_id,
    ));
    response.parameters.clear();
    Ok(response)
}

/// Captured player/policy authority rows use the same existing identity law.
pub fn organizer_input_authority_ledger(
    config: &OrganizerConfig,
) -> Result<crate::PracticeInputAuthorityLedger, OrganizerError> {
    validate_organizer_config(config)?;
    let mut rows = vec![];
    for (actor_id, authority_id, authority_kind) in [
        (
            config.controlled_actor_id,
            config.input_authority_id,
            crate::PracticeAuthorityKind::PlayerSeat,
        ),
        (
            config.workplace_partner.actor_id,
            config.workplace_partner.authority_id,
            crate::PracticeAuthorityKind::DeterministicPolicy,
        ),
        (
            config.neighborhood_partner.actor_id,
            config.neighborhood_partner.authority_id,
            crate::PracticeAuthorityKind::DeterministicPolicy,
        ),
    ] {
        rows.push(crate::PracticeInputAuthority {
            schema_version: 2,
            campaign_id: crate::CampaignId::from_bytes(config.campaign_id),
            authority_kind,
            input_authority_id: InputAuthorityId::from_bytes(authority_id),
            actor_org_id: ActorOrganizationId::from_bytes(actor_id.to_be_bytes()),
            effective_from_tick: 0,
            effective_through_tick_exclusive: u64::MAX,
            decision_content_digest: config.content_digest,
        });
    }
    rows.sort_by_key(|row| row.input_authority_id);
    let ledger = crate::PracticeInputAuthorityLedger {
        schema_version: 2,
        rows,
    };
    crate::validate_input_authority_ledger(&ledger).map_err(|_| OrganizerError::InvalidConfig)?;
    Ok(ledger)
}

/// Bind accepted and standing work, including independent participating
/// responses, to the existing canonical admission rail.
pub fn organizer_resolved_action_batch(
    config: &OrganizerConfig,
    state: &OrganizerState,
    accepted: Option<&OrganizerCommitment>,
) -> Result<crate::ResolvedPracticeBatch, OrganizerError> {
    validate_organizer_pair(config, state)?;
    let ledger = organizer_input_authority_ledger(config)?;
    let routine = routine_commitment(config, state)?;
    let commitment = accepted.unwrap_or(&routine);
    let mut intents = vec![];
    // Ineligible saved work pauses during resolution and submits no action.
    let cost = required_hours(config, state, commitment.command.choice);
    if accepted.is_some()
        || (state.standing.authorized
            && cost <= committed_hours(config, config.controlled_actor_id)?)
    {
        let intent = practice_intent_with_origin(config, state, commitment, accepted.is_none())?;
        if cost > 0 {
            if let Some(partner) = partner_for_choice(config, commitment.command.choice) {
                if partner_response(config, partner)? == OrganizerPartnerResponse::Participated {
                    intents.push(response_intent(&intent, config, partner)?);
                }
            }
        }
        intents.push(intent);
    }
    intents.sort_by_key(crate::practice_proposal_key);
    let items = intents
        .into_iter()
        .map(|intent| {
            let authority = ledger
                .rows
                .iter()
                .find(|row| row.input_authority_id == intent.input_authority_id)
                .ok_or(OrganizerError::InvalidConfig)?
                .clone();
            Ok(crate::ResolvedPracticeBatchItem { authority, intent })
        })
        .collect::<Result<Vec<_>, OrganizerError>>()?;
    let batch = crate::ResolvedPracticeBatch {
        schema_version: 2,
        campaign_id: crate::CampaignId::from_bytes(config.campaign_id),
        resolve_tick: state
            .period
            .checked_add(1)
            .ok_or(OrganizerError::Arithmetic)?,
        authority_ledger_digest: crate::input_authority_ledger_digest(&ledger)
            .map_err(|_| OrganizerError::InvalidConfig)?,
        resource_allocation_contract_digest: organizer_resource_digest()?,
        content_digest: config.content_digest,
        items,
    };
    crate::validate_resolved_practice_batch(&batch, &ledger)
        .map_err(|_| OrganizerError::InvalidCommitment)?;
    Ok(batch)
}

pub fn organizer_action_batch(
    config: &OrganizerConfig,
    state: &OrganizerState,
    accepted: Option<&OrganizerCommitment>,
    session: babylon_kernel::replay::ReplaySessionId,
) -> Result<crate::OrderedPracticeActionBatch, OrganizerError> {
    crate::OrderedPracticeActionBatch::project(
        session,
        &organizer_resolved_action_batch(config, state, accepted)?,
        &organizer_input_authority_ledger(config)?,
    )
    .map_err(|_| OrganizerError::InvalidCommitment)
}

fn allocate_hours(
    config: &OrganizerConfig,
    intent: &PracticeIntent,
    partner: Option<&OrganizerPartner>,
    own_hours: u64,
) -> Result<Vec<OrganizerTimeUse>, OrganizerError> {
    let contract = PracticeResourceAllocationContract::conservation_first();
    let unit_id = PracticeUnitId::from_bytes(sha256_of(b"babylon.organizer-whole-hour.v1"));
    let mut capacities = vec![];
    let mut contributor_by_resource = BTreeMap::new();
    for participant in &config.participants {
        let resource_id = PracticeResourceId::from_bytes(target_identity(
            b"babylon.organizer-contributor.v1",
            participant.contributor_id,
        ));
        contributor_by_resource.insert(resource_id, participant.contributor_id);
        capacities.push(PracticeResourceCapacity {
            owner: PracticeResourceOwner::Shared,
            resource_id,
            unit_id,
            mode: PracticeResourceAllocationMode::DivisibleProRata,
            available: participant.available_hours,
        });
    }
    let mut actors = vec![(intent.clone(), own_hours)];
    if let Some(partner) = partner {
        actors.push((
            response_intent(intent, config, partner)?,
            config.partner_response_hours,
        ));
    }
    let mut requests = vec![];
    for (actor_intent, cost) in actors {
        let actor_id = u64::from_be_bytes(actor_intent.actor_org_id.to_bytes());
        let mut remaining = cost;
        for participant in &config.participants {
            let offered = participant
                .commitments
                .iter()
                .find(|row| row.actor_id == actor_id)
                .map_or(0, |row| row.hours);
            let quantity = remaining.min(offered);
            if quantity == 0 {
                continue;
            }
            remaining = remaining
                .checked_sub(quantity)
                .ok_or(OrganizerError::Arithmetic)?;
            requests.push(
                derive_practice_resource_request(
                    &contract,
                    &actor_intent,
                    &PracticeResourceRequirement {
                        practice_id: actor_intent.practice_id,
                        locator: PracticeResourceLocator::Shared,
                        resource_id: PracticeResourceId::from_bytes(target_identity(
                            b"babylon.organizer-contributor.v1",
                            participant.contributor_id,
                        )),
                        unit_id,
                        quantity,
                    },
                )
                .map_err(|_| OrganizerError::ResourceAllocation)?,
            );
        }
        if remaining != 0 {
            return Err(OrganizerError::ResourceAllocation);
        }
    }
    let allocation = allocate_practice_resources(&contract, &requests, &capacities)
        .map_err(|_| OrganizerError::ResourceAllocation)?;
    let mut time_use = vec![];
    for row in allocation.allocations() {
        if row.allocated() != row.requested() {
            return Err(OrganizerError::ResourceAllocation);
        }
        time_use.push(OrganizerTimeUse {
            contributor_id: *contributor_by_resource
                .get(&row.request().resource_id())
                .ok_or(OrganizerError::ResourceAllocation)?,
            actor_id: u64::from_be_bytes(row.request().proposal_key().actor_org_id.to_bytes()),
            hours: row.allocated(),
        });
    }
    time_use.sort_by_key(|row| (row.contributor_id, row.actor_id));
    Ok(time_use)
}

fn inquiry_report(question: OrganizerInquiry, opening: &OrganizerState) -> Option<OrganizerReport> {
    let facts = opening.last_workplace_facts.as_ref()?;
    Some(match question {
        OrganizerInquiry::WorkLost => {
            let previous = opening
                .observations
                .iter()
                .rev()
                .find_map(|row| match row.report {
                    OrganizerReport::ReducedWork {
                        previous_labor_hours,
                        ..
                    } if row.observed_period == facts.period => Some(previous_labor_hours),
                    _ => None,
                });
            OrganizerReport::Work {
                performed_labor_hours: facts.performed_labor_hours,
                output_kg: facts.output_kg,
                previous_labor_hours: previous,
                previous_output_kg: None,
            }
        }
        OrganizerInquiry::MaintenanceReceived => OrganizerReport::Maintenance {
            enabled_batches: facts.maintenance_enabled_batches,
            consumed_batches: facts.maintenance_consumed_batches,
            expired_batches: facts.maintenance_expired_batches,
        },
    })
}

/// Execute one admitted ruling or the saved routine after the product reducer.
/// The accepted commitment remains an input; it is never mutated on failure.
pub fn resolve_organizer_practice(
    config: &OrganizerConfig,
    opening: &OrganizerState,
    reduced: &OrganizerState,
    facts: &OrganizerWorkplaceFacts,
    accepted: Option<&OrganizerCommitment>,
) -> Result<OrganizerState, OrganizerError> {
    validate_organizer_pair(config, opening)?;
    validate_organizer_pair(config, reduced)?;
    if opening.period.checked_add(1) != Some(facts.period)
        || reduced.period != facts.period
        || reduced.last_workplace_facts.as_ref() != Some(facts)
        || facts.workplace_id != config.workplace_id
    {
        return Err(OrganizerError::PeriodMismatch);
    }
    let routine = routine_commitment(config, opening)?;
    let commitment = accepted.unwrap_or(&routine);
    if let Some(accepted) = accepted {
        if admit_organizer(config, opening, &accepted.command)? != *accepted {
            return Err(OrganizerError::InvalidCommitment);
        }
    }
    let choice = commitment.command.choice;
    let receipt_id = identity(
        b"babylon.organizer-receipt.v1",
        &(
            config.campaign_id,
            config.controlled_actor_id,
            facts.period,
            commitment.commitment_id,
        ),
    )?;
    let mut next = reduced.clone();
    let mut receipt = OrganizerReceipt {
        receipt_id,
        commitment_id: accepted.map(|row| row.commitment_id),
        actor_id: config.controlled_actor_id,
        period: facts.period,
        choice,
        standing_work: accepted.is_none()
            || matches!(
                choice,
                OrganizerChoice::Hold | OrganizerChoice::ResumeStanding
            ),
        outcome: OrganizerOutcome::NoAuthorizedPractice,
        hours_spent: 0,
        partner_actor_id: None,
        partner_response: OrganizerPartnerResponse::NotRequested,
        observation_ids: vec![],
        contact_product_id: None,
        time_use: vec![],
    };
    let required = required_hours(config, opening, choice);
    if choice == OrganizerChoice::PauseStanding {
        next.standing.authorized = false;
        next.standing.paused_reason = Some(OrganizerPauseReason::Explicit);
        receipt.outcome = OrganizerOutcome::StandingPaused;
    } else if required > committed_hours(config, config.controlled_actor_id)? {
        // A saved practice can lose eligibility between periods; no invented
        // resource refill or silent execution replaces missing commitments.
        next.standing.authorized = false;
        next.standing.paused_reason = Some(OrganizerPauseReason::InsufficientCommittedTime);
        receipt.outcome = OrganizerOutcome::InsufficientTime;
    } else if required > 0 {
        if choice == OrganizerChoice::ResumeStanding {
            next.standing.authorized = true;
            next.standing.paused_reason = None;
        }
        let partner =
            partner_for_choice(config, choice).ok_or(OrganizerError::InvalidCommitment)?;
        receipt.partner_actor_id = Some(partner.actor_id);
        receipt.partner_response = partner_response(config, partner)?;
        let intent = practice_intent_with_origin(config, opening, commitment, accepted.is_none())?;
        receipt.time_use = allocate_hours(
            config,
            &intent,
            (receipt.partner_response == OrganizerPartnerResponse::Participated).then_some(partner),
            required,
        )?;
        receipt.hours_spent = required;
        match choice {
            OrganizerChoice::Inquiry(question) => {
                let allowed = match question {
                    OrganizerInquiry::WorkLost => partner.permits_work_report,
                    OrganizerInquiry::MaintenanceReceived => partner.permits_maintenance_report,
                };
                if allowed && receipt.partner_response == OrganizerPartnerResponse::Participated {
                    if let Some(report) = inquiry_report(question, opening) {
                        let id = add_observation(
                            &mut next,
                            config,
                            opening.period,
                            facts.period,
                            Some(receipt_id),
                            report,
                        )?;
                        receipt.observation_ids.push(id);
                        receipt.outcome = OrganizerOutcome::EvidenceObtained;
                    } else {
                        receipt.outcome = OrganizerOutcome::EvidenceWithheld;
                    }
                } else {
                    receipt.outcome = OrganizerOutcome::EvidenceWithheld;
                }
            }
            OrganizerChoice::Reinforce
            | OrganizerChoice::Hold
            | OrganizerChoice::ResumeStanding => {
                if receipt.partner_response == OrganizerPartnerResponse::Participated {
                    let product_id = identity(
                        b"babylon.organizer-contact-product.v1",
                        &(
                            receipt_id,
                            config.controlled_actor_id,
                            partner.actor_id,
                            facts.period,
                        ),
                    )?;
                    receipt.contact_product_id = Some(product_id);
                    receipt.outcome = OrganizerOutcome::ContactCompleted;
                    next.contact_products.push(OrganizerContactProduct {
                        product_id,
                        receipt_id,
                        actor_id: config.controlled_actor_id,
                        partner_actor_id: partner.actor_id,
                        produced_period: facts.period,
                    });
                } else {
                    receipt.outcome = OrganizerOutcome::ContactUncompleted;
                }
            }
            OrganizerChoice::PauseStanding => return Err(OrganizerError::InvalidCommitment),
        }
    }
    next.receipts.push(receipt);
    validate_organizer_pair(config, &next)?;
    Ok(next)
}

/// Compose the two separately scheduled BSL operations for replay contracts.
pub fn resolve_organizer_period(
    config: &OrganizerConfig,
    opening: &OrganizerState,
    facts: &OrganizerWorkplaceFacts,
    accepted: Option<&OrganizerCommitment>,
) -> Result<OrganizerState, OrganizerError> {
    let reduced = reduce_organizer_products(config, opening, facts)?;
    resolve_organizer_practice(config, opening, &reduced, facts, accepted)
}
