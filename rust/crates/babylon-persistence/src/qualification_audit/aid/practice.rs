use super::{add, cash, one, postings, Refusal, Result, Terms};
use crate::{observer_reader::CommittedMaterialReceipts, runtime_session::OrganizerAidResolution};
use babylon_material_circuit::{AidOutcome, FinalDemandPrincipalId};
use babylon_practice_contract::{
    OrganizerAidSupportStatus, OrganizerOutcome, OrganizerPartnerPolicy, OrganizerPartnerResponse,
    OrganizerTimeBindingMode,
};
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::collections::BTreeSet;

pub(super) fn read(
    admitted: &CommittedMaterialReceipts,
    resolution: &OrganizerAidResolution,
    terms: &Terms<'_>,
) -> Result<Value> {
    let consumed = identity(resolution, terms, admitted.receipts.resolve_tick)?;
    support(admitted, resolution)?;
    let practice = &resolution.practice;
    let recipient = terms.binding.partner.actor_id;
    match practice.outcome {
        OrganizerOutcome::AidAwaitingSupport | OrganizerOutcome::AidNotProvisioned => {
            if consumed
                || !practice.time_use.is_empty()
                || practice.partner_response != OrganizerPartnerResponse::NotRequested
                || practice.partner_actor_id.is_some()
            {
                return Err(Refusal::Practice);
            }
        }
        OrganizerOutcome::AidPracticeCompleted => {
            if !consumed
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
    if consumed && practice.partner_actor_id != Some(recipient) {
        return Err(Refusal::Practice);
    }
    let recipient_hours = debits(admitted, resolution, terms)?;
    Ok(
        json!({"original_commitment":terms.accepted.commitment.commitment_id,"mandate":terms.mandate.id,"dispatch_period":terms.accepted.commitment.resolves_period,"period":practice.period,"consumed_support":consumed,"partner_actor":practice.partner_actor_id,"partner_response":practice.partner_response,"outcome":practice.outcome,"recipient_debited_hours":recipient_hours,"finite_practice_completed":practice.outcome==OrganizerOutcome::AidPracticeCompleted}),
    )
}
fn identity(resolution: &OrganizerAidResolution, terms: &Terms<'_>, tick: u64) -> Result<bool> {
    let accepted = &terms.accepted.commitment;
    let p = &resolution.pending;
    let s = &resolution.support;
    let r = &resolution.practice;
    let material =
        babylon_material_circuit::aid_commitment_id(terms.mandate.id, accepted.resolves_period)
            .as_bytes();
    if p.original_commitment_id != accepted.commitment_id
        || p.mandate_id != terms.mandate.id
        || p.kind != terms.binding.kind
        || p.admitted_period != accepted.command.expected_period
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
    Ok(
        matches!(s.status, OrganizerAidSupportStatus::Granted { consumed_quantity, .. } if consumed_quantity > 0),
    )
}
fn support(
    admitted: &CommittedMaterialReceipts,
    resolution: &OrganizerAidResolution,
) -> Result<()> {
    let s = &resolution.support;
    let mut granted = 0;
    let mut dispatched = 0;
    let mut hours = 0;
    let mut reserved_cash = 0;
    let mut granted_cash = 0;
    let mut refunded_cash = 0;
    for r in admitted
        .receipts
        .aid
        .iter()
        .filter(|r| r.commitment_id.as_bytes() == s.material_commitment_id)
    {
        if r.outcome == AidOutcome::Granted {
            add(&mut granted, r.quantity)?;
            cash(&mut granted_cash, r.cash_amount.micro_units())?;
        }
        if r.period == r.dispatch_period
            && matches!(
                r.outcome,
                AidOutcome::Dispatched | AidOutcome::Granted | AidOutcome::Unshipped
            )
        {
            cash(&mut reserved_cash, r.cash_amount.micro_units())?;
        }
        if matches!(r.outcome, AidOutcome::Lost | AidOutcome::Unshipped) {
            cash(&mut refunded_cash, r.cash_amount.micro_units())?;
        }
        if r.outcome == AidOutcome::Dispatched
            || (r.outcome == AidOutcome::Granted && r.period == r.dispatch_period)
        {
            add(&mut dispatched, r.quantity)?;
            add(&mut hours, r.contribution_hours)?;
        }
    }
    let p = &s.material_postings;
    if (
        p.dispatched_quantity,
        p.fulfillment_hours,
        p.payer_cash_reserved_micros,
        p.payer_cash_granted_micros,
        p.payer_cash_refunded_micros,
    ) != (
        dispatched,
        hours,
        reserved_cash,
        granted_cash,
        refunded_cash,
    ) {
        return Err(Refusal::Support);
    }
    if let OrganizerAidSupportStatus::Granted {
        granted_quantity,
        consumed_quantity,
    } = s.status
    {
        let c = one(
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
            || c.consumed_quantity != consumed_quantity
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
fn debits(
    admitted: &CommittedMaterialReceipts,
    resolution: &OrganizerAidResolution,
    terms: &Terms<'_>,
) -> Result<u64> {
    let practice = &resolution.practice;
    let donor = terms.mandate.donor_actor;
    let recipient = terms.binding.partner.actor_id;
    let OrganizerTimeBindingMode::Household { bindings } = &terms.config.time_binding else {
        return Err(Refusal::Time);
    };
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
            if recorded != declared || declared > 1 {
                return Err(Refusal::Time);
            }
        }
    }
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
        let binding = one(
            bindings
                .iter()
                .filter(|b| b.contributor_id == usage.contributor_id),
            Refusal::Time,
        )?;
        let participant = one(
            terms
                .config
                .participants
                .iter()
                .filter(|p| p.contributor_id == usage.contributor_id),
            Refusal::Time,
        )?;
        let promise = one(
            participant
                .commitments
                .iter()
                .filter(|p| p.actor_id == usage.actor_id),
            Refusal::Time,
        )?;
        if usage.hours > promise.hours {
            return Err(Refusal::Time);
        }
        let debit = one(
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
        postings::remaining(
            &admitted.receipts.household_time,
            &admitted.household_contributions,
            FinalDemandPrincipalId::from_bytes(binding.principal_id),
            practice.period,
            terms.mandate.labor_unit_id.as_bytes(),
        )?;
        if usage.actor_id == recipient {
            add(&mut recipient_hours, usage.hours)?;
        } else {
            add(&mut donor_hours, usage.hours)?;
        }
    }
    if donor_hours != practice.hours_spent
        || (practice.outcome == OrganizerOutcome::AidPracticeCompleted
            && recipient_hours != terms.config.partner_response_hours)
        || (practice.outcome != OrganizerOutcome::AidPracticeCompleted && recipient_hours != 0)
    {
        return Err(Refusal::Time);
    }
    Ok(recipient_hours)
}
