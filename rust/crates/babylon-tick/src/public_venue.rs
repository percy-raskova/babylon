//! Evidence joins for the independently published public workplace desk.
//! The caller must provide evidence from an admitted committed period.
use babylon_kernel::content_digest;
use babylon_kernel::economic_location::EconomicLocation;
use babylon_material_circuit::{
    AgencyObservationFundingReceipt, CircuitAccounting, HouseholdTimeAccounting,
    MaterialCircuitState,
};
use babylon_practice_contract::{
    CityPdCase, CityPdConfig, CityPdIntent, OrganizerChoice, OrganizerCommitment, OrganizerConfig,
    OrganizerOutcome, OrganizerPartnerResponse, OrganizerPeriodJournalEntries, OrganizerReceipt,
    OrganizerState, OrganizerTimeBindingMode, PublicVenueHistory, PublicVenuePolicy,
    PublicVenueRecord, PublicVenueRecordKind,
};
use std::collections::BTreeSet;
use std::fmt::{Display, Formatter, Result as FmtResult};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PublicVenueEvidenceError {
    InvalidPolicy,
    InvalidOrganizerEvidence,
    MissingHouseholdDebit,
    InvalidPaidEvidence,
    InvalidPublicationAccess,
}
impl Display for PublicVenueEvidenceError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FmtResult {
        write!(f, "public venue evidence: {self:?}")
    }
}
impl std::error::Error for PublicVenueEvidenceError {}

/// Publish only the minimal contact fact after the organizer and time close.
///
/// Inputs must come from the same admitted committed period, or its retained
/// authenticated evidence. This verifies their exact joins; it does not turn
/// arbitrary copied rows into evidence that a commit happened.
///
/// # Errors
/// Refuses foreign policy, absent contact, or any missing/mismatched debit.
pub fn publish_public_contact(
    policy: &PublicVenuePolicy,
    config: &OrganizerConfig,
    commitment: &OrganizerCommitment,
    organizer: &OrganizerState,
    entries: &OrganizerPeriodJournalEntries,
    closed: &MaterialCircuitState,
) -> Result<PublicVenueRecord, PublicVenueEvidenceError> {
    use PublicVenueEvidenceError::InvalidOrganizerEvidence as Invalid;
    babylon_practice_contract::validate_organizer_commitment(commitment).map_err(|_| Invalid)?;
    let command = &commitment.command;
    if command.campaign_id != config.campaign_id
        || command.actor_id != config.controlled_actor_id
        || command.authority_id != config.input_authority_id
        || command.content_digest != config.content_digest
        || command.resource_digest
            != babylon_practice_contract::organizer_resource_digest().map_err(|_| Invalid)?
        || command.choice != OrganizerChoice::Reinforce
        || commitment.resolves_period != entries.period
    {
        return Err(Invalid);
    }
    let receipt_id = babylon_practice_contract::organizer_receipt_id(
        config.campaign_id,
        config.controlled_actor_id,
        entries.period,
        commitment.commitment_id,
    )
    .map_err(|_| Invalid)?;
    if entries
        .receipts
        .iter()
        .filter(|receipt| {
            receipt.receipt_id == receipt_id
                && receipt.commitment_id == Some(commitment.commitment_id)
        })
        .count()
        != 1
    {
        return Err(Invalid);
    }
    committed_contact_record(policy, config, organizer, entries, closed, receipt_id)
}

// This checks joins against the original committed occurrence, but the caller
// supplies the authority that these are the authenticated original records.
fn committed_contact_record(
    policy: &PublicVenuePolicy,
    config: &OrganizerConfig,
    organizer: &OrganizerState,
    entries: &OrganizerPeriodJournalEntries,
    closed: &MaterialCircuitState,
    receipt_id: [u8; 32],
) -> Result<PublicVenueRecord, PublicVenueEvidenceError> {
    use PublicVenueEvidenceError::{InvalidOrganizerEvidence as Invalid, InvalidPolicy};
    policy.validate().map_err(|_| InvalidPolicy)?;
    babylon_practice_contract::validate_organizer_pair(config, organizer).map_err(|_| Invalid)?;
    babylon_practice_contract::validate_organizer_period_entries(config, entries)
        .map_err(|_| Invalid)?;
    if policy.campaign_id != config.campaign_id
        || policy.workplace_id != config.workplace_id
        || policy.controlled_actor_id != config.controlled_actor_id
        || policy.committee_actor_id != config.workplace_partner.actor_id
        || policy.committee_authority_id != config.workplace_partner.authority_id
        || policy.organizer_content_digest != config.content_digest
    {
        return Err(InvalidPolicy);
    }
    if organizer.period != entries.period || entries.period.checked_add(1) != Some(closed.period) {
        return Err(Invalid);
    }
    let matches: Vec<_> = entries
        .receipts
        .iter()
        .filter(|r| r.receipt_id == receipt_id)
        .collect();
    let [receipt] = matches.as_slice() else {
        return Err(Invalid);
    };
    babylon_practice_contract::validate_organizer_receipt(receipt).map_err(|_| Invalid)?;
    let commitment_id = receipt
        .commitment_id
        .filter(|id| *id != [0; 32])
        .ok_or(Invalid)?;
    let expected_id = babylon_practice_contract::organizer_receipt_id(
        config.campaign_id,
        config.controlled_actor_id,
        entries.period,
        commitment_id,
    )
    .map_err(|_| Invalid)?;
    let expected_product = babylon_practice_contract::organizer_contact_product_id(
        expected_id,
        config.controlled_actor_id,
        config.workplace_partner.actor_id,
        entries.period,
    )
    .map_err(|_| Invalid)?;
    if receipt.receipt_id != expected_id
        || receipt.actor_id != config.controlled_actor_id
        || receipt.period != entries.period
        || receipt.choice != OrganizerChoice::Reinforce
        || receipt.standing_work
        || receipt.outcome != OrganizerOutcome::ContactCompleted
        || receipt.partner_actor_id != Some(config.workplace_partner.actor_id)
        || receipt.partner_response != OrganizerPartnerResponse::Participated
        || receipt.contact_product_id != Some(expected_product)
        || receipt.hours_spent != config.contact_hours
        || organizer
            .contact_products
            .iter()
            .filter(|p| {
                p.product_id == expected_product
                    && p.receipt_id == expected_id
                    && p.actor_id == config.controlled_actor_id
                    && p.partner_actor_id == config.workplace_partner.actor_id
                    && p.produced_period == entries.period
            })
            .count()
            != 1
    {
        return Err(Invalid);
    }
    validate_contact_debits(config, organizer, entries.period, receipt, closed)?;
    PublicVenueRecord::from_policy(
        policy,
        entries.period,
        PublicVenueRecordKind::ContactCompleted {
            organizer_receipt_id: receipt.receipt_id,
            contact_product_id: expected_product,
        },
    )
    .map_err(|_| InvalidPolicy)
}

fn validate_contact_debits(
    config: &OrganizerConfig,
    organizer: &OrganizerState,
    period: u64,
    receipt: &OrganizerReceipt,
    closed: &MaterialCircuitState,
) -> Result<(), PublicVenueEvidenceError> {
    use PublicVenueEvidenceError::MissingHouseholdDebit as Debit;
    let OrganizerTimeBindingMode::Household { bindings } = &config.time_binding else {
        return Err(Debit);
    };
    let CircuitAccounting::Monetary(economy) = &closed.accounting else {
        return Err(Debit);
    };
    let HouseholdTimeAccounting::Modeled(book) = &economy.household_time else {
        return Err(Debit);
    };
    let witness = organizer.last_period_time_witness.as_ref().ok_or(Debit)?;
    if witness.period != period {
        return Err(Debit);
    }
    let mut ids = BTreeSet::new();
    let mut actor_hours = 0_u64;
    let mut partner_hours = 0_u64;
    for usage in &receipt.time_use {
        if usage.actor_id == config.controlled_actor_id {
            actor_hours = actor_hours.checked_add(usage.hours).ok_or(Debit)?;
        } else if usage.actor_id == config.workplace_partner.actor_id {
            partner_hours = partner_hours.checked_add(usage.hours).ok_or(Debit)?;
        } else {
            return Err(Debit);
        }
        let matching: Vec<_> = bindings
            .iter()
            .filter(|b| b.contributor_id == usage.contributor_id)
            .collect();
        let [binding] = matching.as_slice() else {
            return Err(Debit);
        };
        let use_id = babylon_practice_contract::household_contribution_use_id(
            &receipt.receipt_id,
            usage.actor_id,
            usage.contributor_id,
        );
        if !ids.insert(use_id)
            || witness
                .contribution_use_ids
                .iter()
                .filter(|id| **id == use_id)
                .count()
                != 1
            || book
                .contributions
                .iter()
                .filter(|row| {
                    row.period == period
                        && row.contribution.use_id == use_id
                        && row.contribution.principal_id.as_bytes() == binding.principal_id
                        && row.contribution.actor_id == usage.actor_id
                        && row.contribution.contributor_id == usage.contributor_id
                        && row.contribution.hours == usage.hours
                })
                .count()
                != 1
        {
            return Err(Debit);
        }
    }
    if actor_hours != config.contact_hours || partner_hours != config.partner_response_hours {
        return Err(Debit);
    }
    Ok(())
}

/// A public check-in and acyclic identities of its matched material evidence.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PaidVisitPublication {
    record: PublicVenueRecord,
    visit_core_id: [u8; 32],
    shift_evidence_id: [u8; 32],
    payment_evidence_id: [u8; 32],
}

impl PaidVisitPublication {
    #[must_use]
    pub const fn record(&self) -> &PublicVenueRecord {
        &self.record
    }
    #[must_use]
    pub const fn visit_core_id(&self) -> [u8; 32] {
        self.visit_core_id
    }
    #[must_use]
    pub const fn shift_evidence_id(&self) -> [u8; 32] {
        self.shift_evidence_id
    }
    #[must_use]
    pub const fn payment_evidence_id(&self) -> [u8; 32] {
        self.payment_evidence_id
    }
}

fn field_hash(domain: &[u8], fields: &[&[u8]]) -> [u8; 32] {
    let mut bytes = domain.to_vec();
    bytes.push(0);
    for field in fields {
        bytes.extend_from_slice(field);
    }
    content_digest::sha256_of(&bytes)
}

/// Publish a check-in only from a paid, admitted original intent and case.
///
/// The caller supplies a case already authenticated against its actual source,
/// an admitted original decision and committed-period funding/receipt bytes.
/// The material decoder validates the family-37, time, wage and cash joins.
/// Identity derivation uses the matched typed fields; these are not database IDs.
///
/// # Errors
/// Refuses a foreign intent, case or policy, nonpayment, or mismatched evidence.
pub fn publish_paid_visit(
    policy: &PublicVenuePolicy,
    config: &CityPdConfig,
    intent: &CityPdIntent,
    case: &CityPdCase,
    funding: &AgencyObservationFundingReceipt,
    receipt_bytes: &[u8],
) -> Result<PaidVisitPublication, PublicVenueEvidenceError> {
    use babylon_material_circuit::{AccountId, MoneyLocation, MoneyTransferPurpose};
    use PublicVenueEvidenceError::{InvalidPaidEvidence as Invalid, InvalidPolicy};
    validate_paid_selection(policy, config, intent, case, funding)?;
    let input = &funding.input;
    let decoded =
        crate::material_world::decode_material_receipts(receipt_bytes).map_err(|_| Invalid)?;
    if decoded.resolve_tick != intent.resolve_period {
        return Err(Invalid);
    }
    let paid: Vec<_> = decoded
        .agency_paid
        .iter()
        .filter(|r| r.intent_id == intent.intent_id)
        .collect();
    let [paid] = paid.as_slice() else {
        return Err(Invalid);
    };
    if paid.shift_id != input.shift_id
        || paid.agency != input.agency
        || paid.principal_id != input.principal_id
        || paid.labor_unit_id != input.labor_unit_id
        || paid.period != input.due_period
        || paid.hours != input.hours
        || paid.wage != funding.paid
    {
        return Err(Invalid);
    }
    let wages: Vec<_> = decoded
        .wage_accruals
        .iter()
        .filter(|w| w.shift == input.shift_id)
        .collect();
    let payments: Vec<_> = decoded
        .money_transfers
        .iter()
        .filter(|t| t.purpose == MoneyTransferPurpose::WagePayment(input.shift_id))
        .collect();
    let ([wage], [payment]) = (wages.as_slice(), payments.as_slice()) else {
        return Err(Invalid);
    };
    if wage.employer != AccountId::Organization(input.agency)
        || wage.payee != AccountId::Household(input.principal_id)
        || wage.period != input.due_period
        || wage.obligated_hours != input.hours
        || wage.amount != funding.paid
        || payment.debit.location != MoneyLocation::PayrollReserve(input.shift_id)
        || payment.credit.location != MoneyLocation::Cash(AccountId::Household(input.principal_id))
        || payment.credit.delta != funding.paid
        || payment.debit.delta.micro_units().checked_neg() != Some(funding.paid.micro_units())
    {
        return Err(Invalid);
    }
    let shift_bytes = input.shift_id.as_bytes();
    let agency_bytes = input.agency.as_bytes();
    let principal_bytes = input.principal_id.as_bytes();
    let unit_bytes = input.labor_unit_id.as_bytes();
    let period_bytes = wage.period.to_be_bytes();
    let hours_bytes = wage.obligated_hours.to_be_bytes();
    let amount_bytes = wage.amount.micro_units().to_be_bytes();
    let shift_evidence_id = field_hash(
        b"babylon.public-venue.shift-evidence.v1",
        &[
            &paid.intent_id,
            &shift_bytes,
            &agency_bytes,
            &principal_bytes,
            &unit_bytes,
            &period_bytes,
            &hours_bytes,
            &amount_bytes,
        ],
    );
    let debit_bytes = payment.debit.delta.micro_units().to_be_bytes();
    let credit_bytes = payment.credit.delta.micro_units().to_be_bytes();
    let payment_evidence_id = field_hash(
        b"babylon.public-venue.payment-evidence.v1",
        &[&shift_bytes, &principal_bytes, &debit_bytes, &credit_bytes],
    );
    let visit_core_id = visit_core_identity(
        policy,
        config,
        intent,
        case,
        period_bytes,
        &shift_evidence_id,
        &payment_evidence_id,
    );
    let record = PublicVenueRecord::from_policy(
        policy,
        intent.resolve_period,
        PublicVenueRecordKind::PaidVisit { visit_core_id },
    )
    .map_err(|_| InvalidPolicy)?;
    Ok(PaidVisitPublication {
        record,
        visit_core_id,
        shift_evidence_id,
        payment_evidence_id,
    })
}

fn visit_core_identity(
    policy: &PublicVenuePolicy,
    config: &CityPdConfig,
    intent: &CityPdIntent,
    case: &CityPdCase,
    period: [u8; 8],
    shift: &[u8; 32],
    payment: &[u8; 32],
) -> [u8; 32] {
    field_hash(
        b"babylon.public-venue.paid-visit-core.v1",
        &[
            &config.campaign_id,
            &config.actor_id.to_be_bytes(),
            &case.case_id,
            &intent.intent_id,
            &policy.venue_id,
            &case.subject_id.to_be_bytes(),
            &period,
            shift,
            payment,
        ],
    )
}

fn validate_paid_selection(
    policy: &PublicVenuePolicy,
    config: &CityPdConfig,
    intent: &CityPdIntent,
    case: &CityPdCase,
    funding: &AgencyObservationFundingReceipt,
) -> Result<(), PublicVenueEvidenceError> {
    use babylon_material_circuit::AgencyAttendanceOutcome;
    use babylon_practice_contract::CityPdCaseStatus;
    use PublicVenueEvidenceError::{InvalidPaidEvidence as Invalid, InvalidPolicy};
    policy.validate().map_err(|_| InvalidPolicy)?;
    babylon_practice_contract::validate_city_pd_config(config).map_err(|_| Invalid)?;
    babylon_practice_contract::validate_city_pd_case(case).map_err(|_| Invalid)?;
    babylon_practice_contract::validate_city_pd_intent(intent).map_err(|_| Invalid)?;
    if policy.campaign_id != config.campaign_id
        || policy.agency_reader_actor_id != config.actor_id
        || policy.source_terms_digest != config.policy_source_digest
        || case.actor_id != config.actor_id
        || case.subject_id != policy.workplace_id
        || case.public_venue_id != policy.venue_id
        || case.county != config.county
        || case.status != CityPdCaseStatus::Open
        || case.acquired_period > intent.source_period
        || intent.campaign_id != config.campaign_id
        || intent.actor_id != config.actor_id
        || intent.authority_id != config.authority_id
        || intent.config_digest
            != babylon_practice_contract::city_pd_config_digest(config).map_err(|_| Invalid)?
        || intent.case_id != case.case_id
        || intent.subject_id != case.subject_id
        || intent.cost_micros != config.visit_cost_micros
    {
        return Err(Invalid);
    }
    let input = &funding.input;
    let county = std::str::from_utf8(&config.county).map_err(|_| Invalid)?;
    let location: EconomicLocation = format!("county:{county}").parse().map_err(|_| Invalid)?;
    let attendance = funding.attendance.as_ref().ok_or(Invalid)?;
    if funding.outcome != AgencyAttendanceOutcome::Paid
        || input.intent_id != intent.intent_id
        || input.shift_id
            != babylon_material_circuit::agency_shift_id(intent.resolve_period, intent.intent_id)
        || input.agency.as_bytes() != config.agency_account_id
        || input.principal_id.as_bytes() != config.investigator_household_account_id
        || input.labor_unit_id.as_bytes() != config.labor_unit_id
        || input.residence != location
        || input.due_period != intent.resolve_period
        || input.hours != config.visit_hours
        || input.hourly_rate.micro_units() != config.hourly_wage_micros
        || funding.requested.micro_units() != config.visit_cost_micros
        || funding.reserved != funding.requested
        || funding.paid != funding.requested
        || funding.cancelled.micro_units() != 0
        || funding.shortfall.micro_units() != 0
        || funding.attended_hours != input.hours
        || funding.shortfall_hours != 0
        || attendance.intent_id != input.intent_id
        || attendance.shift_id != input.shift_id
        || attendance.principal_id != input.principal_id
        || attendance.labor_unit_id != input.labor_unit_id
        || attendance.period != input.due_period
        || attendance.hours != input.hours
    {
        return Err(Invalid);
    }
    Ok(())
}

/// Original evidence supplied by the committed-period owner, not a public claim.
#[derive(Clone, Copy)]
pub enum PublicVenueSourceProof<'a> {
    InitialNotice,
    Contact {
        config: &'a OrganizerConfig,
        commitment: &'a OrganizerCommitment,
        organizer: &'a OrganizerState,
        entries: &'a OrganizerPeriodJournalEntries,
        closed: &'a MaterialCircuitState,
    },
    /// Original committed contact: the host must authenticate the original
    /// envelope, marker and foundation before supplying these exact records.
    CommittedContact {
        config: &'a OrganizerConfig,
        organizer: &'a OrganizerState,
        entries: &'a OrganizerPeriodJournalEntries,
        closed: &'a MaterialCircuitState,
        record: &'a PublicVenueRecord,
    },
}
/// Verified source token. Only reconstruction from original proof can make one.
/// The host publishes tokens only with the corresponding committed history.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AdmittedPublicVenueSource {
    record: PublicVenueRecord,
}
impl AdmittedPublicVenueSource {
    #[must_use]
    pub const fn record(&self) -> &PublicVenueRecord {
        &self.record
    }
}
/// Reconstruct an opaque source token from committed original period evidence.
///
/// The caller must authenticate the original committed envelope, marker and
/// foundation; these joins alone cannot establish durable authority. The cold
/// `CommittedContact` proof does not re-admit or reconstruct a private command.
///
/// # Errors
/// Refuses a foreign policy, missing publication, or mismatched original proof.
pub fn admit_public_venue_source(
    history: &PublicVenueHistory,
    proof: PublicVenueSourceProof<'_>,
) -> Result<AdmittedPublicVenueSource, PublicVenueEvidenceError> {
    use PublicVenueEvidenceError::{InvalidPolicy, InvalidPublicationAccess as Invalid};
    history.validate().map_err(|_| InvalidPolicy)?;
    let policy = &history.policy;
    let record = match proof {
        PublicVenueSourceProof::InitialNotice => {
            babylon_practice_contract::initial_public_venue_notice(policy)
                .map_err(|_| InvalidPolicy)?
        }
        PublicVenueSourceProof::Contact {
            config,
            commitment,
            organizer,
            entries,
            closed,
        } => publish_public_contact(policy, config, commitment, organizer, entries, closed)?,
        PublicVenueSourceProof::CommittedContact {
            config,
            organizer,
            entries,
            closed,
            record,
        } => {
            let PublicVenueRecordKind::ContactCompleted {
                organizer_receipt_id,
                ..
            } = &record.kind
            else {
                return Err(Invalid);
            };
            let reconstructed = committed_contact_record(
                policy,
                config,
                organizer,
                entries,
                closed,
                *organizer_receipt_id,
            )?;
            if reconstructed != *record {
                return Err(Invalid);
            }
            reconstructed
        }
    };
    if history
        .records
        .iter()
        .filter(|published| **published == record)
        .count()
        != 1
    {
        return Err(Invalid);
    }
    Ok(AdmittedPublicVenueSource { record })
}
/// A public source read during an actually paid visit.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PublicVenueAcquisition {
    pub record: PublicVenueRecord,
    pub witness_id: [u8; 32],
}
/// Read admitted, earlier publications during an authenticated paid visit.
///
/// Tokens come from the original committed-period proof and must be published
/// atomically with the corresponding history. No same-period ordering is inferred.
///
/// # Errors
/// Refuses wrong reader, foreign venue, missing publication, duplicates or bounds.
pub fn read_public_venue_sources(
    history: &PublicVenueHistory,
    reader_actor_id: u64,
    visit: &PaidVisitPublication,
    tokens: &[AdmittedPublicVenueSource],
) -> Result<Vec<PublicVenueAcquisition>, PublicVenueEvidenceError> {
    use PublicVenueEvidenceError::{InvalidPolicy, InvalidPublicationAccess as Invalid};
    history.validate().map_err(|_| InvalidPolicy)?;
    let policy = &history.policy;
    visit.record.validate(policy).map_err(|_| InvalidPolicy)?;
    if reader_actor_id != policy.agency_reader_actor_id
        || tokens.len() > babylon_practice_contract::PUBLIC_VENUE_MAX_RECORDS
    {
        return Err(Invalid);
    }
    let mut ids = BTreeSet::new();
    let mut sources = Vec::new();
    for token in tokens {
        let record = &token.record;
        record.validate(policy).map_err(|_| InvalidPolicy)?;
        if !history.records.contains(record) || !ids.insert(record.source_id) {
            return Err(Invalid);
        }
        if record.period >= visit.record.period {
            continue;
        }
        let witness_id = field_hash(
            b"babylon.public-venue.acquisition.v1",
            &[
                &visit.visit_core_id,
                &record.source_id,
                &visit.record.period.to_be_bytes(),
                &reader_actor_id.to_be_bytes(),
            ],
        );
        sources.push(PublicVenueAcquisition {
            record: record.clone(),
            witness_id,
        });
    }
    sources.sort_unstable_by_key(|row| row.record.source_id);
    Ok(sources)
}

/// Read the actual published paid check-in for the authorized player actor.
/// This proves access to a publication, not presence at the visit.
///
/// # Errors
/// Refuses foreign or malformed public history or visit.
pub fn read_public_visit(
    history: &PublicVenueHistory,
    reader_actor_id: u64,
    visit: &PaidVisitPublication,
) -> Result<Option<[u8; 32]>, PublicVenueEvidenceError> {
    history
        .validate()
        .map_err(|_| PublicVenueEvidenceError::InvalidPolicy)?;
    visit
        .record
        .validate(&history.policy)
        .map_err(|_| PublicVenueEvidenceError::InvalidPolicy)?;
    if reader_actor_id != history.policy.player_reader_actor_id
        || !history.records.contains(&visit.record)
    {
        return Ok(None);
    }
    Ok(Some(public_visit_access_identity(
        visit.visit_core_id,
        visit.record.source_id,
        reader_actor_id,
    )))
}

/// Compute the access identity for a public check-in and reader.
/// This pure identity alone does not prove occurrence or lawful access.
#[must_use]
pub fn public_visit_access_identity(
    visit_core_id: [u8; 32],
    source_id: [u8; 32],
    reader_actor_id: u64,
) -> [u8; 32] {
    field_hash(
        b"babylon.public-venue.player-access.v1",
        &[&visit_core_id, &source_id, &reader_actor_id.to_be_bytes()],
    )
}
