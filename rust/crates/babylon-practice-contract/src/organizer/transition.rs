use super::aid::OrganizerAidResolutionReceipt;
use super::aid::OrganizerAidSupport;
use super::aid::OrganizerAidSupportStatus;
use super::aid::OrganizerPendingAidPractice;
use super::time_resources::OrganizerPeriodTimeResources;
use super::OrganizerChoice;
use super::OrganizerCommand;
use super::OrganizerCommitment;
use super::OrganizerConfig;
use super::OrganizerContactProduct;
use super::OrganizerError;
use super::OrganizerInquiry;
use super::OrganizerLearnedAuthority;
use super::OrganizerMaterialSupport;
use super::OrganizerObservation;
use super::OrganizerOutcome;
use super::OrganizerPartner;
use super::OrganizerPartnerPolicy;
use super::OrganizerPartnerResponse;
use super::OrganizerPauseReason;
use super::OrganizerPeriodJournalEntries;
use super::OrganizerPeriodTimeWitness;
use super::OrganizerReceipt;
use super::OrganizerRefusal;
use super::OrganizerReport;
use super::OrganizerState;
use super::OrganizerWorkplaceFacts;
use super::ResolvedOrganizerPeriod;

use std::collections::BTreeSet;

use babylon_kernel::content_digest;

use crate::CampaignId;
use crate::OrderedPracticeActionBatch;
use crate::PracticeAuthorityKind;
use crate::PracticeInputAuthorityLedger;
use crate::ResolvedPracticeBatch;
use crate::{
    ActorOrganizationId, InputAuthorityId, PracticeId, PracticeIntent, PracticeParameter,
    PracticeTargetIdentity, PracticeTargetTag, ProposalNonce, TaggedPracticeTarget,
};
use babylon_kernel::replay::ReplaySessionId;

fn target_identity(domain: &[u8], id: u64) -> [u8; 32] {
    let mut bytes = Vec::from(domain);
    bytes.extend_from_slice(&id.to_be_bytes());
    content_digest::sha256_of(&bytes)
}

/// Bind every accepted ruling to the common practice input identity, including
/// controls that spend no time and execute no contact work.
///
/// # Errors
///
/// Returns the pair faults from [`validate_organizer_pair`],
/// [`OrganizerError::InvalidCommitment`] when re-admission or the choice
/// binding refuses the commitment, and [`OrganizerError::Arithmetic`] when a
/// period or target identity cannot be represented.
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
    super::contract::validate_organizer_pair(config, state)?;
    if super::contract::admit_organizer(config, state, &commitment.command)? != *commitment {
        return Err(OrganizerError::InvalidCommitment);
    }
    intent_for_authorized_commitment(config, state.period, commitment, standing_origin)
}

// Only current admitted input and validate_pending may enter this canonical builder.
/// Bind one authorized commitment to its exact BSL practice intent.
///
/// # Errors
///
/// Returns [`OrganizerError::InvalidCommitment`] when the choice lacks its
/// configured binding and [`OrganizerError::InvalidState`] when a target
/// identity cannot be derived.
#[allow(
    clippy::too_many_lines,
    reason = "one exhaustive match binds every organizer choice to its exact practice intent; splitting it would scatter the exhaustive binding"
)]
pub(super) fn intent_for_authorized_commitment(
    config: &OrganizerConfig,
    submit_after_tick: u64,
    commitment: &OrganizerCommitment,
    standing_origin: bool,
) -> Result<PracticeIntent, OrganizerError> {
    let (practice, tag, target_id, parameters) = match commitment.command.choice {
        OrganizerChoice::Collect => {
            let row = config
                .collection
                .as_ref()
                .ok_or(OrganizerError::InvalidCommitment)?;
            (
                PracticeId::MutualAid,
                PracticeTargetTag::SocialClass,
                row.social_class_target,
                vec![],
            )
        }
        OrganizerChoice::LocalAid | OrganizerChoice::RemoteAid => {
            let binding = super::aid::aid_binding(config, commitment.command.choice)
                .ok_or(OrganizerError::InvalidCommitment)?;
            (
                PracticeId::MutualAid,
                PracticeTargetTag::SocialClass,
                binding.social_class_target,
                vec![],
            )
        }
        OrganizerChoice::Inquiry(question) => (
            PracticeId::Investigate,
            PracticeTargetTag::Facility,
            target_identity(b"babylon.organizer-target.v1", config.workplace_id),
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
            target_identity(
                b"babylon.organizer-target.v1",
                config.workplace_partner.actor_id,
            ),
            control_parameter(1),
        ),
        OrganizerChoice::Hold => (
            PracticeId::Organize,
            PracticeTargetTag::Organization,
            target_identity(
                b"babylon.organizer-target.v1",
                config.neighborhood_partner.actor_id,
            ),
            control_parameter(if standing_origin { 5 } else { 2 }),
        ),
        OrganizerChoice::PauseStanding => (
            PracticeId::Organize,
            PracticeTargetTag::Organization,
            target_identity(
                b"babylon.organizer-target.v1",
                config.neighborhood_partner.actor_id,
            ),
            control_parameter(3),
        ),
        OrganizerChoice::ResumeStanding => (
            PracticeId::Organize,
            PracticeTargetTag::Organization,
            target_identity(
                b"babylon.organizer-target.v1",
                config.neighborhood_partner.actor_id,
            ),
            control_parameter(4),
        ),
    };
    let value = PracticeIntent {
        schema_version: 2,
        submit_after_tick,
        resolve_tick: commitment.resolves_period,
        input_authority_id: InputAuthorityId::from_bytes(commitment.command.authority_id),
        actor_org_id: ActorOrganizationId::from_bytes(commitment.command.actor_id.to_be_bytes()),
        practice_id: practice,
        target: TaggedPracticeTarget {
            tag,
            identity: PracticeTargetIdentity::from_bytes(target_id),
        },
        proposal_nonce: ProposalNonce::from_bytes(commitment.command.nonce),
        quoted_content_digest: commitment.command.content_digest,
        quoted_resource_contract_digest: commitment.command.resource_digest,
        parameters,
        evidence_digests: if let Some(binding) =
            super::aid::aid_binding(config, commitment.command.choice)
        {
            let mut digests = vec![binding.mandate_id, binding.source_hash];
            digests.sort_unstable();
            digests.dedup();
            digests
        } else if commitment.command.choice == OrganizerChoice::Collect {
            let row = config
                .collection
                .as_ref()
                .ok_or(OrganizerError::InvalidCommitment)?;
            let mut digests = vec![row.mandate_id, row.source_hash];
            digests.sort_unstable();
            digests.dedup();
            digests
        } else {
            vec![]
        },
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
    entries: &mut OrganizerPeriodJournalEntries,
    config: &OrganizerConfig,
    observed_period: u64,
    acquired_period: u64,
    receipt_id: Option<[u8; 32]>,
    report: OrganizerReport,
) -> Result<[u8; 32], OrganizerError> {
    let observation_id = super::contract::identity(
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
    if entries
        .observations
        .iter()
        .any(|row| row.observation_id == observation_id)
        || state
            .learned_authority_index
            .iter()
            .any(|row| row.observation_id == observation_id)
    {
        return Err(OrganizerError::InvalidState);
    }
    let observation = OrganizerObservation {
        observation_id,
        actor_id: config.controlled_actor_id,
        subject_id: config.workplace_id,
        source_actor_id: config.workplace_partner.actor_id,
        observed_period,
        acquired_period,
        receipt_id,
        report: report.clone(),
    };
    entries.observations.push(observation);
    super::contract::upsert_learned_authority(
        &mut state.learned_authority_index,
        OrganizerLearnedAuthority {
            observation_id,
            receipt_id,
            subject_id: config.workplace_id,
            source_actor_id: config.workplace_partner.actor_id,
            observed_period,
            acquired_period,
            report,
        },
    );
    Ok(observation_id)
}

/// Endogenous reducer: only products in the opening committed state can renew
/// cooperation. Newly closed material facts can publish an attributed report
/// inside the same detached transaction; no report escapes a failed tick.
///
/// # Errors
///
/// Returns every [`consume_organizer_contact_products`] and
/// [`report_organizer_workplace`] fault for the supplied facts.
pub fn reduce_organizer_products(
    config: &OrganizerConfig,
    opening: &OrganizerState,
    facts: &OrganizerWorkplaceFacts,
) -> Result<ResolvedOrganizerPeriod, OrganizerError> {
    let contacts = consume_organizer_contact_products(config, opening, facts.period)?;
    report_organizer_workplace(config, opening, &contacts, facts)
}

/// Consume retained contact receipts without fabricating a report. This
/// separately testable reducer is the causal consumer of completed contact.
///
/// # Errors
///
/// Returns [`OrganizerError::PeriodMismatch`] when `resolve_period` is not the
/// opening period plus one, [`OrganizerError::InvalidState`] for a product
/// without a matching agreement, and [`OrganizerError::Arithmetic`] on an
/// overflowing renewal window.
pub fn consume_organizer_contact_products(
    config: &OrganizerConfig,
    opening: &OrganizerState,
    resolve_period: u64,
) -> Result<OrganizerState, OrganizerError> {
    super::contract::validate_organizer_pair(config, opening)?;
    if opening.period.checked_add(1) != Some(resolve_period) {
        return Err(OrganizerError::PeriodMismatch);
    }
    let mut next = opening.clone();
    let consumed: BTreeSet<_> = opening.consumed_product_ids.iter().copied().collect();
    let mut spent = BTreeSet::new();
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
        // The tombstone is the durable refusal; the creation receipt may be
        // evicted, so the consumed product never stays in live state.
        next.consumed_product_ids.push(product.product_id);
        spent.insert(product.product_id);
    }
    next.contact_products
        .retain(|product| !spent.contains(&product.product_id));
    next.consumed_product_ids.sort_unstable();
    next.consumed_product_ids.dedup();
    super::contract::validate_organizer_pair(config, &next)?;
    Ok(next)
}

/// Publish the material signal only while an actual report-sharing agreement
/// remains in force. Omitting the contact consumer cannot sustain this access.
///
/// # Errors
///
/// Returns the pair faults from [`validate_organizer_pair`],
/// [`OrganizerError::PeriodMismatch`] when any input belongs to another
/// period or workplace, and [`OrganizerError::Arithmetic`] when a report
/// bound overflows.
pub fn report_organizer_workplace(
    config: &OrganizerConfig,
    opening: &OrganizerState,
    contacts: &OrganizerState,
    facts: &OrganizerWorkplaceFacts,
) -> Result<ResolvedOrganizerPeriod, OrganizerError> {
    super::contract::validate_organizer_pair(config, opening)?;
    super::contract::validate_organizer_pair(config, contacts)?;
    if opening.period.checked_add(1) != Some(facts.period)
        || contacts.period != opening.period
        || facts.workplace_id != config.workplace_id
    {
        return Err(OrganizerError::PeriodMismatch);
    }
    let mut next = contacts.clone();
    next.period = facts.period;
    next.last_workplace_facts = Some(facts.clone());
    let mut entries = OrganizerPeriodJournalEntries::new(facts.period);
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
                    &mut entries,
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
    super::contract::validate_organizer_pair(config, &next)?;
    Ok(ResolvedOrganizerPeriod {
        state: next,
        journal: entries,
    })
}

fn routine_commitment(
    config: &OrganizerConfig,
    opening: &OrganizerState,
) -> Result<OrganizerCommitment, OrganizerError> {
    let resolves_period = opening
        .period
        .checked_add(1)
        .ok_or(OrganizerError::Arithmetic)?;
    let digest = super::contract::identity(
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
        resource_digest: super::contract::organizer_resource_digest()?,
        nonce,
        choice: OrganizerChoice::Hold,
    };
    Ok(OrganizerCommitment {
        commitment_id: super::contract::identity(b"babylon.organizer-commitment.v1", &command)?,
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
        OrganizerChoice::LocalAid | OrganizerChoice::RemoteAid => {
            super::aid::aid_binding(config, choice).map(|row| &row.partner)
        }
        OrganizerChoice::PauseStanding | OrganizerChoice::Collect => None,
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
            if super::contract::committed_hours(config, partner.actor_id)?
                >= config.partner_response_hours
            {
                OrganizerPartnerResponse::Participated
            } else {
                OrganizerPartnerResponse::UnableToParticipate
            },
        ),
    }
}

pub(super) fn response_intent(
    intent: &PracticeIntent,
    config: &OrganizerConfig,
    partner: &OrganizerPartner,
) -> Result<PracticeIntent, OrganizerError> {
    let originating_digest =
        crate::practice_intent_digest(intent).map_err(|_| OrganizerError::InvalidCommitment)?;
    let digest = super::contract::identity(
        b"babylon.organizer-response-nonce.v1",
        &(originating_digest, partner.actor_id),
    )?;
    let mut nonce = [0_u8; 16];
    nonce.copy_from_slice(&digest[..16]);
    let mut response = intent.clone();
    response.proposal_nonce = ProposalNonce::from_bytes(nonce);
    response.actor_org_id = ActorOrganizationId::from_bytes(partner.actor_id.to_be_bytes());
    response.input_authority_id = InputAuthorityId::from_bytes(partner.authority_id);
    if intent.practice_id != PracticeId::MutualAid {
        response.practice_id = PracticeId::Organize;
        response.target.tag = PracticeTargetTag::Organization;
        response.target.identity = PracticeTargetIdentity::from_bytes(target_identity(
            b"babylon.organizer-target.v1",
            config.controlled_actor_id,
        ));
        response.parameters.clear();
    }
    crate::validate_practice_intent(&response).map_err(|_| OrganizerError::InvalidCommitment)?;
    Ok(response)
}

/// Captured player/policy authority rows use the same existing identity law.
///
/// # Errors
///
/// Returns the config faults [`validate_organizer_config`] reports and
/// [`OrganizerError::InvalidConfig`] when the assembled ledger fails its own
/// identity validation.
pub fn organizer_input_authority_ledger(
    config: &OrganizerConfig,
) -> Result<PracticeInputAuthorityLedger, OrganizerError> {
    super::contract::validate_organizer_config(config)?;
    let mut rows = vec![];
    let mut actors = vec![
        (
            config.controlled_actor_id,
            config.input_authority_id,
            PracticeAuthorityKind::PlayerSeat,
        ),
        (
            config.workplace_partner.actor_id,
            config.workplace_partner.authority_id,
            PracticeAuthorityKind::DeterministicPolicy,
        ),
        (
            config.neighborhood_partner.actor_id,
            config.neighborhood_partner.authority_id,
            PracticeAuthorityKind::DeterministicPolicy,
        ),
    ];
    actors.extend(config.aid_bindings.iter().map(|row| {
        (
            row.partner.actor_id,
            row.partner.authority_id,
            PracticeAuthorityKind::DeterministicPolicy,
        )
    }));
    for (actor_id, authority_id, authority_kind) in actors {
        rows.push(crate::PracticeInputAuthority {
            schema_version: 2,
            campaign_id: CampaignId::from_bytes(config.campaign_id),
            authority_kind,
            input_authority_id: InputAuthorityId::from_bytes(authority_id),
            actor_org_id: ActorOrganizationId::from_bytes(actor_id.to_be_bytes()),
            effective_from_tick: 0,
            effective_through_tick_exclusive: u64::MAX,
            decision_content_digest: config.content_digest,
        });
    }
    rows.sort_by_key(|row| row.input_authority_id);
    let ledger = PracticeInputAuthorityLedger {
        schema_version: 2,
        rows,
    };
    crate::validate_input_authority_ledger(&ledger).map_err(|_| OrganizerError::InvalidConfig)?;
    Ok(ledger)
}

/// Bind accepted and standing work, including independent participating
/// responses, to the existing canonical admission rail.
///
/// # Errors
///
/// Returns the pair faults from [`validate_organizer_pair`], the config and
/// ledger faults of [`organizer_input_authority_ledger`], routine binding
/// faults, and [`OrganizerError::Arithmetic`] when a period or hour sum
/// overflows.
pub fn organizer_resolved_action_batch(
    config: &OrganizerConfig,
    state: &OrganizerState,
    accepted: Option<&OrganizerCommitment>,
) -> Result<ResolvedPracticeBatch, OrganizerError> {
    super::contract::validate_organizer_pair(config, state)?;
    let ledger = organizer_input_authority_ledger(config)?;
    let routine = routine_commitment(config, state)?;
    let commitment = accepted.unwrap_or(&routine);
    let mut intents = vec![];
    // Ineligible saved work pauses during resolution and submits no action.
    let cost = super::contract::required_hours(config, state, commitment.command.choice);
    if accepted.is_some()
        || (state.standing.authorized
            && cost <= super::contract::committed_hours(config, config.controlled_actor_id)?)
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
    for pending in &state.pending_aid {
        let period = state
            .period
            .checked_add(1)
            .ok_or(OrganizerError::Arithmetic)?;
        let (intent, response) = super::aid::delayed_aid_intents(config, pending, period)?;
        if let Some(partner) = partner_for_choice(config, pending.gift.commitment.command.choice) {
            if partner_response(config, partner)? == OrganizerPartnerResponse::Participated {
                intents.push(response);
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
    let batch = ResolvedPracticeBatch {
        schema_version: 2,
        campaign_id: CampaignId::from_bytes(config.campaign_id),
        resolve_tick: state
            .period
            .checked_add(1)
            .ok_or(OrganizerError::Arithmetic)?,
        authority_ledger_digest: crate::input_authority_ledger_digest(&ledger)
            .map_err(|_| OrganizerError::InvalidConfig)?,
        resource_allocation_contract_digest: super::contract::organizer_resource_digest()?,
        content_digest: config.content_digest,
        items,
    };
    crate::validate_resolved_practice_batch(&batch, &ledger)
        .map_err(|_| OrganizerError::InvalidCommitment)?;
    Ok(batch)
}

/// Project the resolved batch into the ordered replay action rail.
///
/// # Errors
///
/// Returns every [`organizer_resolved_action_batch`] fault and
/// [`OrganizerError::InvalidCommitment`] when projection refuses the batch or
/// its authority ledger.
pub fn organizer_action_batch(
    config: &OrganizerConfig,
    state: &OrganizerState,
    accepted: Option<&OrganizerCommitment>,
    session: ReplaySessionId,
) -> Result<OrderedPracticeActionBatch, OrganizerError> {
    OrderedPracticeActionBatch::project(
        session,
        &organizer_resolved_action_batch(config, state, accepted)?,
        &organizer_input_authority_ledger(config)?,
    )
    .map_err(|_| OrganizerError::InvalidCommitment)
}

fn inquiry_report(question: OrganizerInquiry, opening: &OrganizerState) -> Option<OrganizerReport> {
    let facts = opening.last_workplace_facts.as_ref()?;
    Some(match question {
        OrganizerInquiry::WorkLost => {
            let previous = opening
                .learned_authority_index
                .iter()
                .filter(|row| row.report_kind() == 1 && row.observed_period == facts.period)
                .max_by_key(|row| (row.acquired_period, row.observation_id))
                .and_then(|row| match row.report {
                    OrganizerReport::ReducedWork {
                        previous_labor_hours,
                        ..
                    } => Some(previous_labor_hours),
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
/// Explicit fixed-time control path; captured campaigns supply real budgets
/// through `resolve_organizer_practice_with_time` instead.
///
/// # Errors
///
/// Returns the pair faults from [`validate_organizer_pair`],
/// [`OrganizerError::PeriodMismatch`] when the facts belong to another period,
/// and the fixed-time resource and resolution faults of
/// [`resolve_organizer_practice_with_time`].
pub fn resolve_organizer_practice(
    config: &OrganizerConfig,
    opening: &OrganizerState,
    reduced: &OrganizerState,
    facts: &OrganizerWorkplaceFacts,
    accepted: Option<&OrganizerCommitment>,
) -> Result<ResolvedOrganizerPeriod, OrganizerError> {
    super::contract::validate_organizer_pair(config, opening)?;
    if opening.period.checked_add(1) != Some(facts.period) {
        return Err(OrganizerError::PeriodMismatch);
    }
    let resources = super::time_resources::organizer_fixed_time_resources(config, facts.period)?;
    resolve_organizer_practice_with_time(
        config,
        opening,
        reduced,
        facts,
        accepted,
        &resources,
        OrganizerMaterialSupport {
            aid: &[],
            collection: None,
        },
    )
}

/// Execute with exact supplied resolving-period budgets and independent consent.
/// Aliases share one capacity; incomplete funding spends no actual time.
/// # Errors
/// Refuses malformed bindings, units, resource scope and changed commitments.
#[allow(
    clippy::too_many_lines,
    reason = "one ordered resolution keeps the receipt, aid and witness passes in causal sequence"
)]
pub fn resolve_organizer_practice_with_time(
    config: &OrganizerConfig,
    opening: &OrganizerState,
    reduced: &OrganizerState,
    facts: &OrganizerWorkplaceFacts,
    accepted: Option<&OrganizerCommitment>,
    resources: &OrganizerPeriodTimeResources,
    material_support: OrganizerMaterialSupport<'_>,
) -> Result<ResolvedOrganizerPeriod, OrganizerError> {
    let aid_support = material_support.aid;
    let collection_fact = material_support.collection;
    super::contract::validate_organizer_pair(config, opening)?;
    super::contract::validate_organizer_pair(config, reduced)?;
    if opening.period.checked_add(1) != Some(facts.period)
        || reduced.period != facts.period
        || reduced.last_workplace_facts.as_ref() != Some(facts)
        || facts.workplace_id != config.workplace_id
    {
        return Err(OrganizerError::PeriodMismatch);
    }
    super::time_resources::validate_resources(config, facts.period, resources)?;
    if opening
        .last_period_time_witness
        .as_ref()
        .is_some_and(|witness| witness.period >= facts.period)
    {
        return Err(OrganizerError::PeriodMismatch);
    }
    let fresh_aid = accepted.filter(|row| super::aid::aid_kind(row.command.choice).is_some());
    let routine = routine_commitment(config, opening)?;
    let commitment = accepted.unwrap_or(&routine);
    if let Some(accepted) = accepted {
        if super::contract::admit_organizer(config, opening, &accepted.command)? != *accepted {
            return Err(OrganizerError::InvalidCommitment);
        }
    }
    super::aid::require_support_rows(opening, fresh_aid, facts.period, aid_support)?;
    let choice = commitment.command.choice;
    let receipt_id = super::contract::identity(
        b"babylon.organizer-receipt.v1",
        &(
            config.campaign_id,
            config.controlled_actor_id,
            facts.period,
            commitment.commitment_id,
        ),
    )?;
    let mut next = reduced.clone();
    let mut entries = OrganizerPeriodJournalEntries::new(facts.period);
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
    let required = super::contract::required_hours(config, opening, choice);
    if choice == OrganizerChoice::Collect {
        let fact = collection_fact.ok_or(OrganizerError::CollectionSupportMissing)?;
        let resolution =
            super::collection::acknowledge_collection(config, commitment, fact, &mut receipt)?;
        entries.collection_receipts.push(resolution);
    } else if collection_fact.is_some() {
        return Err(OrganizerError::CollectionSupportMismatch);
    } else if fresh_aid.is_some() {
        // The original accepted gift replaces ordinary work once, without
        // dispatch being mislabeled as performed mutual-aid practice.
        receipt.outcome = OrganizerOutcome::AidScheduled;
    } else if choice == OrganizerChoice::PauseStanding {
        next.standing.authorized = false;
        next.standing.paused_reason = Some(OrganizerPauseReason::Explicit);
        receipt.outcome = OrganizerOutcome::StandingPaused;
    } else if required > super::contract::committed_hours(config, config.controlled_actor_id)? {
        // A saved practice can lose eligibility between periods; no invented
        // resource refill or silent execution replaces missing commitments.
        if super::aid::aid_kind(choice).is_none() {
            next.standing.authorized = false;
            next.standing.paused_reason = Some(OrganizerPauseReason::InsufficientCommittedTime);
        }
        receipt.outcome = OrganizerOutcome::InsufficientTime;
    } else if required > 0 {
        execute_practice(
            config,
            opening,
            &mut next,
            commitment,
            resources,
            &mut receipt,
            accepted.is_none(),
            &mut entries,
        )?;
    }
    entries.receipts.push(receipt);
    resolve_pending_aid(
        config,
        opening,
        &mut next,
        fresh_aid,
        resources,
        aid_support,
        &mut entries,
    )?;
    set_time_witness(config, &mut next, &entries)?;
    super::contract::validate_organizer_pair(config, &next)?;
    super::contract::validate_organizer_period_entries(config, &entries)?;
    super::aid::validate_completed_aid(&next, &entries)?;
    Ok(ResolvedOrganizerPeriod {
        state: next,
        journal: entries,
    })
}

/// Record the last resolved household-hour partitions, refusing a replay.
fn set_time_witness(
    config: &OrganizerConfig,
    next: &mut OrganizerState,
    entries: &OrganizerPeriodJournalEntries,
) -> Result<(), OrganizerError> {
    if !matches!(
        config.time_binding,
        super::OrganizerTimeBindingMode::Household { .. }
    ) {
        next.last_period_time_witness = None;
        return Ok(());
    }
    let ids = super::contract::charged_time_ids(entries)
        .into_iter()
        .collect::<Vec<_>>();
    if let Some(previous) = &next.last_period_time_witness {
        if ids
            .iter()
            .any(|id| previous.contribution_use_ids.contains(id))
        {
            return Err(OrganizerError::Refused(
                OrganizerRefusal::HouseholdTimeAlreadySpent,
            ));
        }
    }
    next.last_period_time_witness = Some(OrganizerPeriodTimeWitness {
        period: entries.period,
        contribution_use_ids: ids,
    });
    Ok(())
}

#[allow(
    clippy::too_many_arguments,
    reason = "the practice executor binds one receipt to its exact state, evidence and supplied budgets"
)]
fn execute_practice(
    config: &OrganizerConfig,
    opening: &OrganizerState,
    next: &mut OrganizerState,
    commitment: &OrganizerCommitment,
    resources: &OrganizerPeriodTimeResources,
    receipt: &mut OrganizerReceipt,
    standing_origin: bool,
    entries: &mut OrganizerPeriodJournalEntries,
) -> Result<(), OrganizerError> {
    let choice = commitment.command.choice;
    let required = super::contract::required_hours(config, opening, choice);
    let period = next.period;
    let receipt_id = receipt.receipt_id;
    let partner = partner_for_choice(config, choice).ok_or(OrganizerError::InvalidCommitment)?;
    receipt.partner_actor_id = Some(partner.actor_id);
    receipt.partner_response = partner_response(config, partner)?;
    let intent = practice_intent_with_origin(config, opening, commitment, standing_origin)?;
    let Some(time_use) = super::time_resources::allocate_hours(
        config,
        &intent,
        (receipt.partner_response == OrganizerPartnerResponse::Participated).then_some(partner),
        required,
        resources,
        super::aid::aid_binding(config, choice),
    )?
    else {
        if super::aid::aid_kind(choice).is_none() {
            next.standing.authorized = false;
            next.standing.paused_reason = Some(OrganizerPauseReason::InsufficientAvailableTime);
        }
        receipt.outcome = OrganizerOutcome::InsufficientTime;
        if receipt.partner_response == OrganizerPartnerResponse::Participated {
            receipt.partner_response = OrganizerPartnerResponse::UnableToParticipate;
        }
        return Ok(());
    };
    receipt.time_use = time_use;
    if choice == OrganizerChoice::ResumeStanding {
        next.standing.authorized = true;
        next.standing.paused_reason = None;
    }
    receipt.hours_spent = required;
    match choice {
        OrganizerChoice::LocalAid | OrganizerChoice::RemoteAid => {
            return Err(OrganizerError::AidSupportMissing)
        }
        OrganizerChoice::Inquiry(question) => {
            let allowed = match question {
                OrganizerInquiry::WorkLost => partner.permits_work_report,
                OrganizerInquiry::MaintenanceReceived => partner.permits_maintenance_report,
            };
            if allowed && receipt.partner_response == OrganizerPartnerResponse::Participated {
                if let Some(report) = inquiry_report(question, opening) {
                    let id = add_observation(
                        next,
                        entries,
                        config,
                        opening.period,
                        period,
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
        OrganizerChoice::Reinforce | OrganizerChoice::Hold | OrganizerChoice::ResumeStanding => {
            if receipt.partner_response == OrganizerPartnerResponse::Participated {
                let product_id = super::contract::identity(
                    b"babylon.organizer-contact-product.v1",
                    &(
                        receipt_id,
                        config.controlled_actor_id,
                        partner.actor_id,
                        period,
                    ),
                )?;
                receipt.contact_product_id = Some(product_id);
                receipt.outcome = OrganizerOutcome::ContactCompleted;
                next.contact_products.push(OrganizerContactProduct {
                    product_id,
                    receipt_id,
                    actor_id: config.controlled_actor_id,
                    partner_actor_id: partner.actor_id,
                    produced_period: period,
                    origin_journal_seq: None,
                });
            } else {
                receipt.outcome = OrganizerOutcome::ContactUncompleted;
            }
        }
        OrganizerChoice::PauseStanding | OrganizerChoice::Collect => {
            return Err(OrganizerError::InvalidCommitment)
        }
    }
    Ok(())
}

/// Compose the two separately scheduled BSL operations for replay contracts.
///
/// # Errors
///
/// Returns every [`reduce_organizer_products`] and
/// [`resolve_organizer_practice`] fault; a reduction that fails publishes
/// nothing.
pub fn resolve_organizer_period(
    config: &OrganizerConfig,
    opening: &OrganizerState,
    facts: &OrganizerWorkplaceFacts,
    accepted: Option<&OrganizerCommitment>,
) -> Result<ResolvedOrganizerPeriod, OrganizerError> {
    let reduced = reduce_organizer_products(config, opening, facts)?;
    let mut resolved =
        resolve_organizer_practice(config, opening, &reduced.state, facts, accepted)?;
    let mut journal = reduced.journal;
    journal.extend(resolved.journal)?;
    resolved.journal = journal;
    Ok(resolved)
}

/// Resolve using exact period-specific supplied time; no absent-budget fallback.
/// # Errors
/// Refuses malformed resources, periods or commitments. Valid scarcity produces
/// an insufficient-time receipt with no actual debit or new contact product.
pub fn resolve_organizer_period_with_time(
    config: &OrganizerConfig,
    opening: &OrganizerState,
    facts: &OrganizerWorkplaceFacts,
    accepted: Option<&OrganizerCommitment>,
    resources: &OrganizerPeriodTimeResources,
    material_support: OrganizerMaterialSupport<'_>,
) -> Result<ResolvedOrganizerPeriod, OrganizerError> {
    let reduced = reduce_organizer_products(config, opening, facts)?;
    let mut resolved = resolve_organizer_practice_with_time(
        config,
        opening,
        &reduced.state,
        facts,
        accepted,
        resources,
        material_support,
    )?;
    let mut journal = reduced.journal;
    journal.extend(resolved.journal)?;
    resolved.journal = journal;
    Ok(resolved)
}

fn resolve_pending_aid(
    config: &OrganizerConfig,
    opening: &OrganizerState,
    next: &mut OrganizerState,
    fresh: Option<&OrganizerCommitment>,
    resources: &OrganizerPeriodTimeResources,
    supports: &[OrganizerAidSupport],
    entries: &mut OrganizerPeriodJournalEntries,
) -> Result<(), OrganizerError> {
    let mut pending = opening.pending_aid.clone();
    if let Some(accepted) = fresh {
        let support = supports
            .iter()
            .find(|row| row.original_commitment_id == accepted.commitment_id)
            .ok_or(OrganizerError::AidSupportMissing)?;
        pending.push(super::aid::pending_from_support(
            config, opening, accepted, support,
        )?);
    }
    pending.sort_by_key(|row| row.gift.kind);
    let mut previous = None;
    for row in &pending {
        super::aid::validate_pending(config, row)?;
        if previous == Some(row.gift.kind) {
            return Err(OrganizerError::Refused(
                OrganizerRefusal::PendingAidConflict,
            ));
        }
        previous = Some(row.gift.kind);
    }
    next.pending_aid.clear();
    let remaining_pledge =
        super::collection::remaining_collection_pledge(config, entries, next.period)?;
    let mut performed = super::aid::organizer_period_receipts(entries)
        .filter(|row| row.choice != OrganizerChoice::Collect)
        .flat_map(|row| row.time_use.iter())
        .cloned()
        .collect::<Vec<_>>();
    for authorization in pending {
        let support = supports
            .iter()
            .find(|row| row.original_commitment_id == authorization.gift.commitment.commitment_id)
            .ok_or(OrganizerError::AidSupportMissing)?;
        super::aid::validate_support(&authorization, support, next.period)?;
        let choice = authorization.gift.commitment.command.choice;
        let mut receipt = aid_attempt_receipt(&authorization, next.period)?;
        match support.status {
            OrganizerAidSupportStatus::AwaitingDelivery => {
                receipt.outcome = OrganizerOutcome::AidAwaitingSupport;
                next.pending_aid.push(authorization.clone());
            }
            OrganizerAidSupportStatus::TerminalFailure
            | OrganizerAidSupportStatus::Granted {
                consumed_quantity: 0,
                ..
            } => {}
            OrganizerAidSupportStatus::Granted { .. } => {
                let (intent, _) =
                    super::aid::delayed_aid_intents(config, &authorization, next.period)?;
                let partner =
                    partner_for_choice(config, choice).ok_or(OrganizerError::InvalidCommitment)?;
                receipt.partner_actor_id = Some(partner.actor_id);
                receipt.partner_response = partner_response(config, partner)?;
                let (remaining, supply) = super::time_resources::remaining_after_uses(
                    &remaining_pledge,
                    resources,
                    &performed,
                )?;
                let binding = super::aid::aid_binding(config, choice)
                    .ok_or(OrganizerError::AidSupportMismatch)?;
                let time_use = super::time_resources::allocate_hours(
                    &remaining,
                    &intent,
                    (receipt.partner_response == OrganizerPartnerResponse::Participated)
                        .then_some(partner),
                    binding.coordination_hours,
                    &supply,
                    Some(binding),
                )?;
                if let Some(uses) = time_use {
                    receipt.outcome =
                        if receipt.partner_response == OrganizerPartnerResponse::Participated {
                            OrganizerOutcome::AidPracticeCompleted
                        } else {
                            OrganizerOutcome::AidPracticeUncompleted
                        };
                    receipt.hours_spent = binding.coordination_hours;
                    performed.extend(uses.iter().cloned());
                    receipt.time_use = uses;
                } else {
                    receipt.outcome = OrganizerOutcome::InsufficientTime;
                    if receipt.partner_response == OrganizerPartnerResponse::Participated {
                        receipt.partner_response = OrganizerPartnerResponse::UnableToParticipate;
                    }
                }
            }
        }
        let row = OrganizerAidResolutionReceipt {
            authorization,
            support: support.clone(),
            practice: receipt,
        };
        super::aid::validate_resolution_shape(&row)?;
        entries.aid_receipts.push(row);
    }
    Ok(())
}

fn aid_attempt_receipt(
    authorization: &OrganizerPendingAidPractice,
    period: u64,
) -> Result<OrganizerReceipt, OrganizerError> {
    let choice = authorization.gift.commitment.command.choice;
    Ok(OrganizerReceipt {
        receipt_id: super::contract::identity(
            b"babylon.organizer-aid-resolution.v1",
            &(authorization.gift.commitment.commitment_id, period),
        )?,
        commitment_id: Some(authorization.gift.commitment.commitment_id),
        actor_id: authorization.gift.donor_actor_id,
        period,
        choice,
        standing_work: false,
        outcome: OrganizerOutcome::AidNotProvisioned,
        hours_spent: 0,
        partner_actor_id: None,
        partner_response: OrganizerPartnerResponse::NotRequested,
        observation_ids: vec![],
        contact_product_id: None,
        time_use: vec![],
    })
}
