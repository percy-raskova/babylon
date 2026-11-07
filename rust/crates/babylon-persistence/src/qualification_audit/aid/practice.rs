use super::{postings, Refusal, Result, Terms};
use crate::observer_reader::CommittedMaterialReceipts;
use babylon_practice_contract::OrganizerAidResolutionReceipt;

use super::MaterialWorldRegister;
use babylon_material_circuit::{AidOutcome, FinalDemandPrincipalId};
use babylon_practice_contract::OrganizerReceipt;
use babylon_practice_contract::{
    OrganizerAidSupportStatus, OrganizerOutcome, OrganizerPartnerPolicy, OrganizerPartnerResponse,
    OrganizerTimeBindingMode,
};
use serde::Serialize;
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet};

#[derive(Clone, Default)]
pub(super) struct History {
    first_receipts: BTreeMap<[u8; 32], OrganizerReceipt>,
    used_or_excluded: BTreeSet<[u8; 32]>,
}

impl History {
    pub(super) fn check_close(&self, admitted: &CommittedMaterialReceipts) -> Result<()> {
        if admitted
            .household_contributions
            .iter()
            .any(|row| self.used_or_excluded.contains(&row.contribution.use_id))
        {
            return Err(Refusal::Time);
        }
        Ok(())
    }

    pub(super) fn check_pending(&self, register: &MaterialWorldRegister) -> Result<()> {
        let state = register.organizer_state().ok_or(Refusal::Capture)?;
        for pending in &state.pending_aid {
            if pending.response.as_ref()
                != self
                    .first_receipts
                    .get(&pending.gift.commitment.commitment_id)
            {
                return Err(Refusal::Practice);
            }
        }
        Ok(())
    }

    pub(super) fn response(
        &mut self,
        resolution: &OrganizerAidResolutionReceipt,
        qualifying: bool,
    ) -> Result<Option<[u8; 32]>> {
        let original = resolution.authorization.gift.commitment.commitment_id;
        let claimed = resolution.authorization.response.as_ref();
        if let Some(first) = self.first_receipts.get(&original) {
            if claimed != Some(first)
                || resolution.practice.outcome != OrganizerOutcome::AidResponseRetained
            {
                return Err(Refusal::Practice);
            }
        } else if qualifying {
            if claimed != Some(&resolution.practice)
                || resolution.practice.outcome == OrganizerOutcome::AidResponseRetained
            {
                return Err(Refusal::Practice);
            }
            self.first_receipts
                .insert(original, resolution.practice.clone());
        } else if claimed.is_some()
            || resolution.practice.outcome == OrganizerOutcome::AidResponseRetained
        {
            return Err(Refusal::Practice);
        }
        claimed
            .map(|receipt| {
                let bytes = serde_json::to_vec(receipt).map_err(|_| Refusal::Practice)?;
                Ok(Sha256::digest(bytes).into())
            })
            .transpose()
    }
}

#[derive(Serialize)]
struct Posting {
    use_id: [u8; 32],
    actor_id: u64,
    contributor_id: u64,
    hours: u64,
}

#[derive(Default)]
struct Debits {
    recipient_hours: u64,
    postings: Vec<Posting>,
    absent: Vec<[u8; 32]>,
}

pub(super) fn read(
    admitted: &CommittedMaterialReceipts,
    resolution: &OrganizerAidResolutionReceipt,
    terms: &Terms<'_>,
    history: &mut History,
) -> Result<Value> {
    let qualifying = validate_practice(admitted, resolution, terms)?;
    let practice = &resolution.practice;
    let debits = debits(admitted, resolution, terms)?;
    for id in debits
        .postings
        .iter()
        .map(|posting| posting.use_id)
        .chain(debits.absent.iter().copied())
    {
        if !history.used_or_excluded.insert(id) {
            return Err(Refusal::Time);
        }
    }
    let first_digest = history.response(resolution, qualifying)?;
    let food_consumed_quantity = match resolution.support.status {
        OrganizerAidSupportStatus::Granted {
            consumed_quantity, ..
        } => consumed_quantity,
        _ => 0,
    };
    let cash_received = resolution
        .support
        .material_postings
        .payer_cash_granted_micros;
    Ok(json!({
        "original_commitment": terms.accepted.commitment.commitment_id,
        "mandate": terms.mandate.id,
        "dispatch_period": terms.accepted.commitment.resolves_period,
        "period": practice.period,
        "qualifying_received_support": qualifying,
        "food_consumed": food_consumed_quantity > 0,
        "food_consumed_quantity": food_consumed_quantity,
        "food_consumption_period": (food_consumed_quantity > 0).then_some(practice.period),
        "cash_received_micros": cash_received.to_string(),
        "cash_received_period": (cash_received > 0).then_some(practice.period),
        "first_response_period": resolution.authorization.response.as_ref().map(|row| row.period),
        "partner_actor": practice.partner_actor_id,
        "partner_response": practice.partner_response,
        "outcome": practice.outcome,
        "recipient_debited_hours": debits.recipient_hours,
        "material_commitment_id": resolution.authorization.material_commitment_id,
        "practice_receipt_id": practice.receipt_id,
        "first_response_receipt_id": resolution.authorization.response.as_ref().map(|row| row.receipt_id),
        "first_response_receipt_sha256": first_digest,
        "contribution_postings": debits.postings,
        "absent_contribution_use_ids": debits.absent,
        "finite_practice_completed": practice.outcome == OrganizerOutcome::AidPracticeCompleted,
    }))
}
fn validate_practice(
    admitted: &CommittedMaterialReceipts,
    resolution: &OrganizerAidResolutionReceipt,
    terms: &Terms<'_>,
) -> Result<bool> {
    let qualifying = identity(resolution, terms, admitted.receipts.resolve_tick)?;
    requested_legs(admitted, resolution)?;
    support(admitted, resolution)?;
    let practice = &resolution.practice;
    let recipient = terms.binding.partner.actor_id;
    match practice.outcome {
        OrganizerOutcome::AidResponseRetained => {
            let original = resolution
                .authorization
                .response
                .as_ref()
                .ok_or(Refusal::Practice)?;
            if original.period >= practice.period
                || original.commitment_id != practice.commitment_id
                || practice.hours_spent != 0
                || !practice.time_use.is_empty()
                || practice.partner_actor_id.is_some()
                || practice.partner_response != OrganizerPartnerResponse::NotRequested
            {
                return Err(Refusal::Practice);
            }
        }
        OrganizerOutcome::AidAwaitingSupport | OrganizerOutcome::NoQualifyingSupport => {
            if qualifying
                || !practice.time_use.is_empty()
                || practice.partner_response != OrganizerPartnerResponse::NotRequested
                || practice.partner_actor_id.is_some()
            {
                return Err(Refusal::Practice);
            }
        }
        OrganizerOutcome::AidPracticeCompleted => {
            if !qualifying
                || practice.partner_response != OrganizerPartnerResponse::Participated
                || terms.binding.partner.policy != OrganizerPartnerPolicy::Participate
                || practice.partner_actor_id != Some(recipient)
                || practice.hours_spent != terms.binding.coordination_hours
            {
                return Err(Refusal::Practice);
            }
        }
        OrganizerOutcome::InsufficientTime => {
            if !practice.time_use.is_empty()
                || practice.partner_response == OrganizerPartnerResponse::Participated
            {
                return Err(Refusal::Practice);
            }
        }
        OrganizerOutcome::AidPracticeUncompleted => {
            if practice.partner_response == OrganizerPartnerResponse::Participated
                || practice.time_use.iter().any(|u| u.actor_id == recipient)
            {
                return Err(Refusal::Practice);
            }
        }
        _ => return Err(Refusal::Practice),
    }
    if qualifying
        && practice.outcome != OrganizerOutcome::AidResponseRetained
        && practice.partner_actor_id != Some(recipient)
    {
        return Err(Refusal::Practice);
    }
    Ok(qualifying)
}

fn identity(
    resolution: &OrganizerAidResolutionReceipt,
    terms: &Terms<'_>,
    tick: u64,
) -> Result<bool> {
    let accepted = &terms.accepted.commitment;
    let p = &resolution.authorization;
    let s = &resolution.support;
    let r = &resolution.practice;
    let material =
        babylon_material_circuit::aid_commitment_id(terms.mandate.id, accepted.resolves_period)
            .as_bytes();
    if p.gift.commitment != *accepted
        || p.gift.mandate_id != terms.mandate.id
        || p.gift.kind != terms.binding.kind
        || p.dispatch_period != accepted.resolves_period
        || p.material_commitment_id != material
        || p.good_id != terms.mandate.good_id.as_bytes()
        || p.unit_id != terms.mandate.unit_id.as_bytes()
        || s.original_commitment_id != accepted.commitment_id
        || s.material_commitment_id != material
        || s.mandate_id != terms.mandate.id
        || s.source_hash != terms.mandate.source_hash
        || s.dispatch_period != accepted.resolves_period
        || s.period != tick
        || s.recipient_principal_id != terms.mandate.recipient.as_bytes()
        || s.good_id != terms.mandate.good_id.as_bytes()
        || s.unit_id != terms.mandate.unit_id.as_bytes()
        || r.commitment_id != Some(accepted.commitment_id)
        || r.period != tick
        || r.choice != accepted.command.choice
        || r.actor_id != accepted.command.actor_id
        || r.contact_product_id.is_some()
    {
        return Err(Refusal::Identity);
    }
    Ok(s.material_postings.payer_cash_granted_micros > 0
        || matches!(s.status, OrganizerAidSupportStatus::Granted { consumed_quantity, .. } if consumed_quantity > 0))
}
fn requested_legs(
    admitted: &CommittedMaterialReceipts,
    resolution: &OrganizerAidResolutionReceipt,
) -> Result<()> {
    use babylon_practice_contract::OrganizerAllocation;
    let pending = &resolution.authorization;
    let OrganizerAllocation::Aid {
        food_quantity,
        cash_micros,
    } = pending.gift.commitment.command.allocation
    else {
        return Err(Refusal::Support);
    };
    let rows: Vec<_> = admitted
        .receipts
        .aid
        .iter()
        .filter(|row| row.commitment_id.as_bytes() == pending.material_commitment_id)
        .collect();
    let current = pending.dispatch_period == admitted.receipts.resolve_tick;
    let requests: Vec<_> = rows
        .iter()
        .filter(|row| row.outcome == AidOutcome::Requested)
        .collect();
    let cash: Vec<_> = rows
        .iter()
        .filter(|row| row.outcome == AidOutcome::CashRequested)
        .collect();
    if requests.len() != usize::from(current && food_quantity > 0)
        || requests
            .first()
            .is_some_and(|row| row.quantity != food_quantity)
        || cash.len() != usize::from(current && cash_micros > 0)
        || cash
            .first()
            .is_some_and(|row| row.cash_amount.micro_units() != cash_micros)
    {
        return Err(Refusal::Support);
    }
    if current {
        let mut ended = 0;
        let mut cash_results = 0;
        for row in rows {
            match row.outcome {
                AidOutcome::Dispatched
                | AidOutcome::Granted
                | AidOutcome::Unshipped
                | AidOutcome::FoodReceivingRefused => super::add(&mut ended, row.quantity)?,
                AidOutcome::CashGranted
                | AidOutcome::CashUnfunded
                | AidOutcome::CashReceivingRefused => cash_results += 1,
                AidOutcome::Requested | AidOutcome::CashRequested | AidOutcome::Lost => {}
            }
        }
        if ended != food_quantity || cash_results != usize::from(cash_micros > 0) {
            return Err(Refusal::Support);
        }
    }
    Ok(())
}
fn support(
    admitted: &CommittedMaterialReceipts,
    resolution: &OrganizerAidResolutionReceipt,
) -> Result<()> {
    let s = &resolution.support;
    let mut granted = 0;
    let mut dispatched = 0;
    let mut hours = 0;
    let mut granted_cash = 0;
    let mut lost = 0;
    for r in admitted
        .receipts
        .aid
        .iter()
        .filter(|r| r.commitment_id.as_bytes() == s.material_commitment_id)
    {
        if r.outcome == AidOutcome::Granted {
            super::add(&mut granted, r.quantity)?;
        }
        if r.outcome == AidOutcome::CashGranted {
            super::cash(&mut granted_cash, r.cash_amount.micro_units())?;
        }
        if r.outcome == AidOutcome::Lost {
            super::add(&mut lost, r.quantity)?;
        }
        if r.outcome == AidOutcome::Dispatched
            || (r.outcome == AidOutcome::Granted && r.period == r.dispatch_period)
        {
            super::add(&mut dispatched, r.quantity)?;
            super::add(&mut hours, r.contribution_hours)?;
        }
    }
    let p = &s.material_postings;
    if (
        p.dispatched_quantity,
        p.fulfillment_hours,
        p.payer_cash_granted_micros,
        p.lost_quantity,
    ) != (dispatched, hours, granted_cash, lost)
    {
        return Err(Refusal::Support);
    }
    if let OrganizerAidSupportStatus::Granted {
        granted_quantity,
        consumed_quantity,
        household_consumed_quantity,
    } = s.status
    {
        let c = super::one(
            admitted.receipts.household_consumption.iter().filter(|c| {
                c.principal_id.as_bytes() == s.recipient_principal_id
                    && c.good_id.as_bytes() == s.good_id
                    && c.unit_id.as_bytes() == s.unit_id
            }),
            Refusal::Consumption,
        )?;
        if granted == 0
            || granted != granted_quantity
            || c.period != s.period
            || c.consumed_quantity != household_consumed_quantity
            || consumed_quantity > granted_quantity
            || consumed_quantity > household_consumed_quantity
        {
            return Err(Refusal::Support);
        }
    } else if granted != 0 {
        return Err(Refusal::Support);
    }
    Ok(())
}
fn use_id(receipt: [u8; 32], actor: u64, contributor: u64) -> [u8; 32] {
    let mut hash = Sha256::new();
    hash.update(b"babylon.organizer-household-contribution.v1\0");
    hash.update(receipt);
    hash.update(actor.to_be_bytes());
    hash.update(contributor.to_be_bytes());
    hash.finalize().into()
}
fn absent_use_ids(
    admitted: &CommittedMaterialReceipts,
    practice: &OrganizerReceipt,
    terms: &Terms<'_>,
) -> Result<Vec<[u8; 32]>> {
    let mut absent = Vec::new();
    let donor = terms.mandate.donor_actor;
    let recipient = terms.binding.partner.actor_id;
    // Reconcile all configured aliases, including aliases which declared no use.
    for participant in &terms.config.participants {
        for actor in [donor, recipient] {
            let id = use_id(practice.receipt_id, actor, participant.contributor_id);
            let declared = practice
                .time_use
                .iter()
                .filter(|r| r.actor_id == actor && r.contributor_id == participant.contributor_id)
                .count();
            let recorded = admitted
                .household_contributions
                .iter()
                .filter(|r| r.contribution.use_id == id)
                .count();
            if declared == 0 {
                absent.push(id);
            }
            if recorded != declared || declared > 1 {
                return Err(Refusal::Time);
            }
        }
    }
    absent.sort_unstable();
    Ok(absent)
}

fn debits(
    admitted: &CommittedMaterialReceipts,
    resolution: &OrganizerAidResolutionReceipt,
    terms: &Terms<'_>,
) -> Result<Debits> {
    let mut evidence = Debits {
        absent: absent_use_ids(admitted, &resolution.practice, terms)?,
        ..Debits::default()
    };
    let practice = &resolution.practice;
    let donor = terms.mandate.donor_actor;
    let recipient = terms.binding.partner.actor_id;
    let OrganizerTimeBindingMode::Household { bindings } = &terms.config.time_binding else {
        return Err(Refusal::Time);
    };
    let mut donor_hours = 0;
    let mut recipient_hours = 0;
    let mut seen = BTreeSet::new();
    for usage in &practice.time_use {
        if usage.hours == 0
            || !seen.insert((usage.actor_id, usage.contributor_id))
            || ![donor, recipient].contains(&usage.actor_id)
            || usage.contributor_id
                != if usage.actor_id == donor {
                    terms.binding.donor_contributor_id
                } else {
                    terms.binding.recipient_contributor_id
                }
        {
            return Err(Refusal::Time);
        }
        let binding = super::one(
            bindings
                .iter()
                .filter(|b| b.contributor_id == usage.contributor_id),
            Refusal::Time,
        )?;
        let participant = super::one(
            terms
                .config
                .participants
                .iter()
                .filter(|p| p.contributor_id == usage.contributor_id),
            Refusal::Time,
        )?;
        let promise = super::one(
            participant
                .commitments
                .iter()
                .filter(|p| p.actor_id == usage.actor_id),
            Refusal::Time,
        )?;
        if usage.hours > promise.hours {
            return Err(Refusal::Time);
        }
        let debit = super::one(
            admitted.household_contributions.iter().filter(|d| {
                d.contribution.use_id
                    == use_id(practice.receipt_id, usage.actor_id, usage.contributor_id)
            }),
            Refusal::Time,
        )?;
        if debit.period != practice.period
            || debit.contribution.principal_id.as_bytes() != binding.principal_id
            || debit.contribution.actor_id != usage.actor_id
            || debit.contribution.contributor_id != usage.contributor_id
            || debit.contribution.hours != usage.hours
        {
            return Err(Refusal::Time);
        }
        evidence.postings.push(Posting {
            use_id: debit.contribution.use_id,
            actor_id: debit.contribution.actor_id,
            contributor_id: debit.contribution.contributor_id,
            hours: debit.contribution.hours,
        });
        postings::remaining(
            &admitted.receipts.household_time,
            &admitted.household_contributions,
            FinalDemandPrincipalId::from_bytes(binding.principal_id),
            practice.period,
            terms.mandate.labor_unit_id.as_bytes(),
        )?;
        if usage.actor_id == recipient {
            super::add(&mut recipient_hours, usage.hours)?;
        } else {
            super::add(&mut donor_hours, usage.hours)?;
        }
    }
    if donor_hours != practice.hours_spent
        || (practice.outcome == OrganizerOutcome::AidPracticeCompleted
            && recipient_hours != terms.config.partner_response_hours)
        || (practice.outcome != OrganizerOutcome::AidPracticeCompleted && recipient_hours != 0)
    {
        return Err(Refusal::Time);
    }
    evidence.recipient_hours = recipient_hours;
    evidence.postings.sort_by_key(|row| row.use_id);
    Ok(evidence)
}
