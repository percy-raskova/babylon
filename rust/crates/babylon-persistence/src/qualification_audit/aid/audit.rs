//! Leaf implementation for the parent module; public paths stay on the parent.
use crate::runtime_session::OrganizerAidFoodPreview;

use super::practice::History;
use super::reports::RetailOpening;
use super::{postings, practice, MaterialWorldRegister, PartnerReport};

use crate::observer_reader::CommittedMaterialReceipts;
use crate::runtime_session::{OrganizerMaterialAidPreview, OrganizerSnapshot};

use babylon_material_circuit::{AidMandate, AidOutcome, AidReceipt, CircuitAccounting};

use babylon_practice_contract::{
    OrganizerAidBinding, OrganizerAidKind, OrganizerChoice, OrganizerCommitment, OrganizerConfig,
    OrganizerGiftConsent, OrganizerPreview,
};

use serde::Serialize;

use serde_json::{json, Value};

use crate::runtime_session::OrganizerAidTransportPreview;
use babylon_kernel::clock::CampaignDuration;
use babylon_material_circuit::AidTransport;
use babylon_material_circuit::MaterialCatalog;
use babylon_practice_contract::OrganizerOutcome;
use babylon_tick::material_world;
use std::collections::{BTreeMap, BTreeSet};
use std::fmt::Formatter;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Refusal {
    Admission,
    ReportAuthority,
    ReportOpening,
    ReportGrant,
    ReportRetail,
    ReportService,
    ReportSettlement,
    OriginalOffer,
    Duplicate,
    Period,
    Identity,
    Capture,
    Quantity,
    Cash,
    Income,
    Consumption,
    Time,
    Practice,
    Support,
    Overflow,
}

impl std::fmt::Display for Refusal {
    fn fmt(&self, f: &mut Formatter<'_>) -> std::fmt::Result {
        write!(f, "independent aid audit refused: {self:?}")
    }
}

impl std::error::Error for Refusal {}

pub(in crate::qualification_audit) type Result<T> = std::result::Result<T, Refusal>;

/// Real responses captured before acceptance clears the client's review.
/// Later snapshots cannot manufacture this original offer witness.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Accepted {
    pub(super) commitment: OrganizerCommitment,
    admission: OrganizerPreview,
    material: OrganizerMaterialAidPreview,
}

impl Accepted {
    /// # Errors
    /// Refuses absent/duplicate offers, crossed authority, periods or receiving refusal.
    pub fn capture(
        commitment: &OrganizerCommitment,
        admission: &OrganizerPreview,
        before: &OrganizerSnapshot,
    ) -> Result<Self> {
        babylon_practice_contract::validate_organizer_commitment(commitment)
            .map_err(|_| Refusal::Admission)?;
        let command = &commitment.command;
        let kind = kind(command.choice)?;
        if command.actor_id != before.view.actor_id
            || command.authority_id != before.view.authority_id
            || command.content_digest != before.view.content_digest
            || command.resource_digest != before.view.resource_digest
            || command.expected_period != before.view.period
            || admission.choice != command.choice
            || admission.allocation != command.allocation
            || admission.current_period != command.expected_period
            || admission.resolves_period != commitment.resolves_period
            || admission.available_hours != before.view.available_hours
            || admission.refusal.is_some()
            || admission.replaces_standing_work != before.view.standing.authorized
            || !before.duration.contains(commitment.resolves_period)
            || before.pending_aid.iter().any(|r| r.kind == kind)
        {
            return Err(Refusal::Admission);
        }
        let material = one(
            before.aid.iter().filter(|r| r.kind == kind),
            Refusal::OriginalOffer,
        )?;
        let option = one(
            before.view.aid_options.iter().filter(|r| r.kind == kind),
            Refusal::OriginalOffer,
        )?;
        let babylon_practice_contract::OrganizerAllocation::Aid {
            food_quantity,
            cash_micros,
        } = command.allocation
        else {
            return Err(Refusal::Admission);
        };
        if material.period != command.expected_period
            || food_quantity > material.maximum_quantity
            || cash_micros > material.maximum_cash_micros
            || !((food_quantity > 0 && material.receiving_consent == OrganizerGiftConsent::Accept)
                || (cash_micros > 0
                    && material.cash_receiving_consent == OrganizerGiftConsent::Accept))
            || option.receiving_consent != material.receiving_consent
            || material.coordination_hours == 0
            || option.coordination_hours != material.coordination_hours
            || admission.required_hours != material.coordination_hours
        {
            return Err(Refusal::OriginalOffer);
        }
        Ok(Self {
            commitment: commitment.clone(),
            admission: admission.clone(),
            material: material.clone(),
        })
    }
}

pub(in crate::qualification_audit) fn kind(choice: OrganizerChoice) -> Result<OrganizerAidKind> {
    match choice {
        OrganizerChoice::LocalAid => Ok(OrganizerAidKind::Local),
        OrganizerChoice::RemoteAid => Ok(OrganizerAidKind::Remote),
        _ => Err(Refusal::Admission),
    }
}

pub(in crate::qualification_audit) fn one<T>(
    mut rows: impl Iterator<Item = T>,
    refusal: Refusal,
) -> Result<T> {
    let row = rows.next().ok_or(refusal)?;
    if rows.next().is_some() {
        return Err(refusal);
    }
    Ok(row)
}

pub(in crate::qualification_audit) fn add(a: &mut u64, b: u64) -> Result<()> {
    *a = a.checked_add(b).ok_or(Refusal::Overflow)?;
    Ok(())
}

pub(in crate::qualification_audit) fn cash(a: &mut i128, b: i128) -> Result<()> {
    *a = a.checked_add(b).ok_or(Refusal::Overflow)?;
    Ok(())
}

pub(in crate::qualification_audit) struct Terms<'a> {
    pub(in crate::qualification_audit) accepted: &'a Accepted,
    pub(in crate::qualification_audit) mandate: &'a AidMandate,
    pub(in crate::qualification_audit) binding: &'a OrganizerAidBinding,
    pub(in crate::qualification_audit) config: &'a OrganizerConfig,
}

pub(in crate::qualification_audit) fn terms<'a>(
    accepted: &'a Accepted,
    config: &'a OrganizerConfig,
    mandates: &'a [AidMandate],
) -> Result<Terms<'a>> {
    let command = &accepted.commitment.command;
    let p = &accepted.material;
    let binding = one(
        config.aid_bindings.iter().filter(|r| r.kind == p.kind),
        Refusal::Capture,
    )?;
    let mandate = one(
        mandates.iter().filter(|r| r.id == p.mandate_id),
        Refusal::Capture,
    )?;
    if command.campaign_id != config.campaign_id
        || command.actor_id != config.controlled_actor_id
        || command.authority_id != config.input_authority_id
        || command.content_digest != config.content_digest
        || command.resource_digest
            != babylon_practice_contract::organizer_resource_digest()
                .map_err(|_| Refusal::Capture)?
        || binding.mandate_id != mandate.id
        || binding.source_hash != mandate.source_hash
        || binding.donor_contributor_id != mandate.donor_contributor_id
        || binding.donor_principal_id != mandate.donor.as_bytes()
        || binding.recipient_principal_id != mandate.recipient.as_bytes()
        || mandate.donor_actor != command.actor_id
        || mandate.recipient_actor != binding.partner.actor_id
        || binding.receiving_consent != p.receiving_consent
        || binding.cash_receiving_consent != p.cash_receiving_consent
        || p.initial_food_quantity != mandate.initial_quantity
        || p.initial_cash_micros != mandate.initial_cash.micro_units()
        || p.donor_id != mandate.donor.as_bytes()
        || p.recipient_actor_id != mandate.recipient_actor
        || p.good_id != mandate.good_id.as_bytes()
        || p.unit_id != mandate.unit_id.as_bytes()
        || p.maximum_cash_micros != mandate.maximum_cash.micro_units()
        || p.maximum_quantity != mandate.maximum_quantity
        || p.coordination_hours != binding.coordination_hours
    {
        return Err(Refusal::Capture);
    }
    let babylon_practice_contract::OrganizerAllocation::Aid {
        food_quantity,
        cash_micros,
    } = command.allocation
    else {
        return Err(Refusal::Capture);
    };
    if (food_quantity > 0 && p.food.is_none()) || (cash_micros > 0 && !p.funding.available()) {
        return Err(Refusal::Capture);
    }
    if let Some(food) = &p.food {
        validate_food_capture(food, mandate)?;
    }
    Ok(Terms {
        accepted,
        mandate,
        binding,
        config,
    })
}

fn validate_food_capture(food: &OrganizerAidFoodPreview, mandate: &AidMandate) -> Result<()> {
    if food.labor_unit_id != mandate.labor_unit_id.as_bytes()
        || food.fulfillment_hours_per_unit != mandate.hours_per_unit
    {
        return Err(Refusal::Capture);
    }
    let route_matches = match (&food.transport, mandate.transport) {
        (OrganizerAidTransportPreview::Local, AidTransport::Local) => true,
        (
            OrganizerAidTransportPreview::Routed {
                route_id,
                from_node_id,
                to_node_id,
                ..
            },
            AidTransport::Routed {
                route_id: route,
                from_node_id: from,
                to_node_id: to,
            },
        ) => {
            *route_id == route.as_bytes()
                && *from_node_id == from.as_bytes()
                && *to_node_id == to.as_bytes()
        }
        _ => false,
    };
    if !route_matches {
        return Err(Refusal::Capture);
    }
    Ok(())
}

pub(in crate::qualification_audit) type Totals = BTreeMap<[u8; 32], (u64, i128, i128)>;

#[derive(Default, Clone)]
pub struct Audit {
    period: u64,
    retail_opening: RetailOpening,
    commands: BTreeMap<[u8; 32], Accepted>,
    dispatched: Totals,
    settled: Totals,
    facts: Vec<Value>,
    pub(super) completed_practices: BTreeSet<[u8; 32]>,
    terminal_practices: BTreeSet<[u8; 32]>,
    practice_history: History,
    completed_kinds: BTreeSet<OrganizerAidKind>,
    pub(super) opening: Option<([u8; 16], OrganizerSnapshot)>,
    campaign: Option<[u8; 16]>,
}

#[derive(Debug, Clone, Serialize)]
pub struct Boundary {
    pub version: u8,
    pub period: u64,
    pub tick_content_hash: String,
    pub canonical_receipt_sha256: String,
    pub selected_aid: Vec<Value>,
    pub independent_practices: Vec<Value>,
    pub partner_reports: Vec<PartnerReport>,
}

/// A compact comparison disclosure from a register already authenticated by the
/// full observer. This is not an original protocol offer or command witness.
/// # Errors
/// Refuses unavailable organizer state or an invalid captured campaign duration.
pub fn material_disclosure(
    catalog: &MaterialCatalog,
    register: &MaterialWorldRegister,
    duration: CampaignDuration,
) -> Result<OrganizerSnapshot> {
    if !duration.contains(register.completed_tick()) {
        return Err(Refusal::Period);
    }
    crate::organizer_runtime::captured_organizer_snapshot(catalog, register, None, duration)
        .map_err(|_| Refusal::Capture)
}

impl Audit {
    /// Capture the original public offer from a complete observer's authenticated
    /// register. The caller must bind that register to its campaign/foundation.
    /// # Errors
    /// Refuses a different period or disclosure, including dynamic stock, cash,
    /// ordinary prices, route stages, capacities and remaining household time.
    pub fn open(
        &mut self,
        catalog: &MaterialCatalog,
        register: &MaterialWorldRegister,
        snapshot: &OrganizerSnapshot,
    ) -> Result<()> {
        if register.catalog_digest() != catalog.catalog_digest() {
            return Err(Refusal::Identity);
        }
        if register.completed_tick() != self.period {
            return Err(Refusal::Period);
        }
        if !crate::organizer_runtime::aid_snapshot_matches(catalog, register, snapshot)
            .map_err(|_| Refusal::Identity)?
        {
            return Err(Refusal::Identity);
        }
        let campaign = register
            .organizer_config()
            .ok_or(Refusal::Capture)?
            .campaign_id;
        if self.campaign.is_some_and(|bound| bound != campaign)
            || self
                .opening
                .as_ref()
                .is_some_and(|(_, before)| before.view.period == self.period && before != snapshot)
        {
            return Err(Refusal::Identity);
        }
        let retail_opening = RetailOpening::capture(register)?;
        self.retail_opening = retail_opening;
        self.campaign = Some(campaign);
        self.opening = Some((campaign, snapshot.clone()));
        Ok(())
    }
    /// # Errors
    /// Refuses a missing audited prefix, changed retries or conflicting period rulings.
    pub fn accept(&mut self, accepted: Accepted) -> Result<()> {
        if let Some(prior) = self.commands.get(&accepted.commitment.commitment_id) {
            return if *prior == accepted {
                Ok(())
            } else {
                Err(Refusal::Duplicate)
            };
        }
        if accepted.commitment.command.expected_period != self.period {
            return Err(Refusal::Period);
        }
        let (campaign, opening) = self.opening.as_ref().ok_or(Refusal::OriginalOffer)?;
        if accepted.commitment.command.campaign_id != *campaign
            || Accepted::capture(&accepted.commitment, &accepted.admission, opening)? != accepted
        {
            return Err(Refusal::OriginalOffer);
        }
        if self
            .commands
            .values()
            .any(|r| r.commitment.resolves_period == accepted.commitment.resolves_period)
        {
            return Err(Refusal::Duplicate);
        }
        self.commands
            .insert(accepted.commitment.commitment_id, accepted);
        Ok(())
    }

    /// # Errors
    /// Refuses crossed committed identities, unjoined postings or unauthorized time.
    /// Every refusal leaves the complete fold unchanged.
    pub fn read(
        &mut self,
        catalog: &MaterialCatalog,
        admitted: &CommittedMaterialReceipts,
        register: &MaterialWorldRegister,
        after: &OrganizerSnapshot,
    ) -> Result<Boundary> {
        let tick = admitted.receipts.resolve_tick;
        if self.period.checked_add(1) != Some(tick) {
            return Err(Refusal::Period);
        }
        if admitted.identity.resolve_tick() != tick
            || register.completed_tick() != tick
            || material_world::nominal_material_world_hash(
                admitted.identity.graph_world_after(),
                register,
            ) != admitted.identity.result_world_hash()
        {
            return Err(Refusal::Identity);
        }
        let config = register.organizer_config().ok_or(Refusal::Capture)?;
        if self.campaign != Some(config.campaign_id)
            || config.campaign_id != *admitted.campaign_id.canonical_bytes()
            || !crate::organizer_runtime::aid_snapshot_matches(catalog, register, after)
                .map_err(|_| Refusal::Identity)?
        {
            return Err(Refusal::Identity);
        }
        let CircuitAccounting::Monetary(_) = &register.state().accounting else {
            return Err(Refusal::Capture);
        };
        let mut candidate = self.clone();
        candidate.practice_history.check_close(admitted)?;
        postings::check_period(&admitted.receipts)?;
        let mut selected_aid = Vec::new();
        for row in &admitted.receipts.aid {
            let accepted = one(
                self.commands.values().filter(|a| {
                    a.material.mandate_id == row.mandate_id
                        && a.commitment.resolves_period == row.dispatch_period
                }),
                Refusal::OriginalOffer,
            )?;
            let terms = terms(accepted, config, &catalog.aid_mandates)?;
            let uses_time = check_material(row, &terms, tick)?;
            candidate.track(row, uses_time, terms.mandate.maximum_quantity)?;
            let remaining = postings::check_time(admitted, row, &terms, after)?;
            selected_aid.push(json!({"original_commitment":accepted.commitment.commitment_id,"mandate":row.mandate_id,"dispatch_period":row.dispatch_period,"outcome":format!("{:?}",row.outcome),"quantity":row.quantity,"cash_micros":row.cash_amount.micro_units().to_string(),"carrying_micros":row.carrying_amount.micro_units().to_string(),"fulfillment_hours":row.contribution_hours,"remaining_shared_hours":remaining}));
        }
        let mut independent_practices = Vec::new();
        let mut seen = BTreeSet::new();
        let entries = register
            .organizer_journal()
            .and_then(|journal| journal.latest())
            .ok_or(Refusal::Capture)?;
        if entries.period != tick {
            return Err(Refusal::Period);
        }
        for resolution in &entries.aid_receipts {
            let original = resolution.authorization.gift.commitment.commitment_id;
            if !seen.insert(original) {
                return Err(Refusal::Duplicate);
            }
            let accepted = self.commands.get(&original).ok_or(Refusal::OriginalOffer)?;
            let terms = terms(accepted, config, &catalog.aid_mandates)?;
            let fact = practice::read(
                admitted,
                resolution,
                &terms,
                &mut candidate.practice_history,
            )?;
            if !matches!(
                resolution.practice.outcome,
                OrganizerOutcome::AidAwaitingSupport | OrganizerOutcome::AidResponseRetained
            ) && !candidate.terminal_practices.insert(original)
            {
                return Err(Refusal::Duplicate);
            }
            if resolution.practice.outcome == OrganizerOutcome::AidPracticeCompleted {
                candidate.completed_practices.insert(original);
                candidate.completed_kinds.insert(accepted.material.kind);
            }
            independent_practices.push(fact);
        }
        candidate.practice_history.check_pending(register)?;
        let fact = Boundary {
            version: 3,
            partner_reports: super::reports::closed(
                catalog,
                register,
                admitted,
                &self.retail_opening,
            )?,
            period: tick,
            tick_content_hash: super::super::hex(admitted.identity.tick_content_hash().as_bytes()),
            canonical_receipt_sha256: super::super::hex(&admitted.identity.receipt_digest()),
            selected_aid,
            independent_practices,
        };
        candidate
            .facts
            .push(serde_json::to_value(&fact).map_err(|_| Refusal::Identity)?);
        candidate.period = tick;
        candidate.open(catalog, register, after)?;
        *self = candidate;
        Ok(fact)
    }

    fn track(&mut self, row: &AidReceipt, dispatched: bool, maximum: u64) -> Result<()> {
        let key = row.commitment_id.as_bytes();
        if dispatched {
            total(self.dispatched.entry(key).or_default(), row)?;
            if self.dispatched[&key].0 > maximum {
                return Err(Refusal::Quantity);
            }
        }
        if matches!(row.outcome, AidOutcome::Granted | AidOutcome::Lost) {
            total(self.settled.entry(key).or_default(), row)?;
        }
        if let Some(&(q, c, v)) = self.settled.get(&key) {
            let &(dq, dc, dv) = self.dispatched.get(&key).ok_or(Refusal::Quantity)?;
            if q > dq || c > dc || v > dv || (q == dq && (c, v) != (dc, dv)) {
                return Err(Refusal::Quantity);
            }
        }
        Ok(())
    }
    #[must_use]
    pub fn summary(&self) -> Summary {
        let status = if self.period > 0 {
            "passed"
        } else {
            "incomplete"
        };
        Summary {
            cash_and_in_kind_postings: status,
            accepted_original_commands: self.commands.len(),
            time_partition_and_residual_bound: status,
            exact_final_contribution_debit_ledger: status,
        }
    }
    #[must_use]
    pub fn report(&self) -> Value {
        let summary = self.summary();
        json!({"cash_and_in_kind_postings":summary.cash_and_in_kind_postings,"accepted_original_commands":summary.accepted_original_commands,"time_partition_and_residual_bound":summary.time_partition_and_residual_bound,"exact_final_contribution_debit_ledger":summary.exact_final_contribution_debit_ledger,"periods":self.facts})
    }
    #[must_use]
    pub fn practice_report(&self) -> Value {
        json!({"status":if self.completed_kinds.contains(&OrganizerAidKind::Local)&&self.completed_kinds.contains(&OrganizerAidKind::Remote){"passed"}else{"incomplete"},"completed_original_commands":self.completed_practices,"terminal_original_commands":self.terminal_practices,"basis":"actual_qualifying_support_independent_partner_response_and_authenticated_finite_debits"})
    }
}

/// Summary of the same checked posting audit, without repeated prior periods.
#[derive(Debug, Serialize)]
pub struct Summary {
    pub cash_and_in_kind_postings: &'static str,
    pub accepted_original_commands: usize,
    pub time_partition_and_residual_bound: &'static str,
    pub exact_final_contribution_debit_ledger: &'static str,
}

pub(in crate::qualification_audit) fn total(
    entry: &mut (u64, i128, i128),
    row: &AidReceipt,
) -> Result<()> {
    add(&mut entry.0, row.quantity)?;
    cash(&mut entry.1, row.cash_amount.micro_units())?;
    cash(&mut entry.2, row.carrying_amount.micro_units())
}

pub(in crate::qualification_audit) fn check_material(
    row: &AidReceipt,
    terms: &Terms<'_>,
    tick: u64,
) -> Result<bool> {
    let m = terms.mandate;
    let babylon_practice_contract::OrganizerAllocation::Aid {
        food_quantity,
        cash_micros,
    } = terms.accepted.commitment.command.allocation
    else {
        return Err(Refusal::Admission);
    };
    if row.quantity > food_quantity
        || row.cash_amount.micro_units() > cash_micros
        || (row.outcome == AidOutcome::Requested && row.quantity != food_quantity)
        || (row.outcome == AidOutcome::CashRequested
            && row.cash_amount.micro_units() != cash_micros)
    {
        return Err(Refusal::Quantity);
    }
    if row.commitment_id
        != babylon_material_circuit::aid_commitment_id(
            m.id,
            terms.accepted.commitment.resolves_period,
        )
        || row.donor != m.donor
        || row.recipient != m.recipient
        || row.good_id != m.good_id
        || row.unit_id != m.unit_id
        || row.payer != m.payer
        || row.period != tick
        || row.quantity > m.maximum_quantity
    {
        return Err(Refusal::Capture);
    }
    let uses_time = row.outcome == AidOutcome::Dispatched
        || (row.outcome == AidOutcome::Granted && row.dispatch_period == tick);
    row.validate_against(m).map_err(|_| Refusal::Capture)?;
    let expected_hours = row
        .quantity
        .checked_mul(m.hours_per_unit)
        .ok_or(Refusal::Overflow)?;
    if row.contribution_hours != if uses_time { expected_hours } else { 0 } {
        return Err(Refusal::Time);
    }
    Ok(uses_time)
}
