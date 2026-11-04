//! Reconstruct transient venue capabilities from authenticated original commits.
use std::collections::BTreeSet;

use babylon_material_circuit::AgencyAttendanceOutcome;
use babylon_practice_contract::{
    CityPdCase, CityPdConfig, CityPdDecision, CityPdIntent, PublicVenueHistory,
    PublicVenueRecordKind,
};
use babylon_tick::material_world::{
    CityPdAttempt, DecodedCityPdAttemptEvidence, MaterialWorldRegister,
};
use babylon_tick::public_venue::{self, AdmittedPublicVenueSource, PublicVenueSourceProof};
use postgres::GenericClient;

use super::runtime::CommittedVenuePeriod;
use super::{
    CampaignId, CapturedMaterialTick, MaterialReadAuthority, MaterialRuntimeError,
    StoredTickReadSource,
};
use crate::material_storage::{self, LookupAnchor};

fn invalid() -> MaterialRuntimeError {
    MaterialRuntimeError::InvalidCheckpoint
}

/// The current register supplies only period hints. Every selected original period
/// is independently authenticated against its complete envelope and marker.
pub(super) fn reconstruct_sources(
    client: &mut impl GenericClient,
    campaign: CampaignId,
    opening: &MaterialWorldRegister,
    current: &MaterialWorldRegister,
    authority: MaterialReadAuthority<'_, '_>,
    expected_chain: [u8; 32],
) -> Result<Vec<AdmittedPublicVenueSource>, MaterialRuntimeError> {
    let Some(history) = current.public_venue() else {
        return Ok(Vec::new());
    };
    let notice =
        public_venue::admit_public_venue_source(history, PublicVenueSourceProof::InitialNotice)
            .map_err(|_| invalid())?;
    let mut evidence = Reconstruction {
        opening,
        current,
        history,
        sources: vec![notice],
        verified_visits: BTreeSet::new(),
        prior: None,
    };
    let periods = referenced_periods(current, history)?;
    if periods.is_empty() {
        return Ok(evidence.sources);
    }
    let rows = super::capture_material_lookup(
        client,
        StoredTickReadSource::Runtime,
        campaign,
        current.completed_tick(),
    )?;
    let mut expected = 1_u64;
    let mut chain = material_storage::initial_lookup_chain(authority.opening)?;
    for row in rows {
        if u64::try_from(row.try_get::<_, i64>(0)?).ok() != Some(expected) {
            return Err(invalid());
        }
        let lookup = material_storage::read_period_lookup(
            authority.opening,
            expected,
            row.try_get(1)?,
            LookupAnchor::Previous(chain),
        )?;
        chain = lookup.chain;
        if periods.contains(&expected) {
            let captured = CapturedMaterialTick::capture(
                client,
                StoredTickReadSource::Runtime,
                campaign,
                expected,
            )?;
            let original = captured.admit_venue_period(campaign, expected, authority, &lookup)?;
            evidence.admit_period(original, expected)?;
        }
        expected = expected
            .checked_add(1)
            .ok_or(MaterialRuntimeError::Bounds)?;
    }
    if expected
        != current
            .completed_tick()
            .checked_add(1)
            .ok_or(MaterialRuntimeError::Bounds)?
        || chain != expected_chain
        || history
            .records
            .iter()
            .filter(|record| matches!(record.kind, PublicVenueRecordKind::PaidVisit { .. }))
            .any(|record| !evidence.verified_visits.contains(&record.source_id))
    {
        return Err(invalid());
    }
    Ok(evidence.sources)
}

fn referenced_periods(
    current: &MaterialWorldRegister,
    history: &PublicVenueHistory,
) -> Result<BTreeSet<u64>, MaterialRuntimeError> {
    let mut periods = BTreeSet::new();
    for record in &history.records {
        if matches!(
            record.kind,
            PublicVenueRecordKind::ContactCompleted { .. }
                | PublicVenueRecordKind::PaidVisit { .. }
        ) {
            if record.period == 0 || record.period > current.completed_tick() {
                return Err(invalid());
            }
            periods.insert(record.period);
        }
    }
    if let Some(pd) = current.city_pd() {
        for attempt in &pd.attempts {
            let period = attempt.receipt.resolve_period;
            if period == 0 || period > current.completed_tick() {
                return Err(invalid());
            }
            periods.insert(period);
            if period > 1 {
                periods.insert(period - 1);
            }
        }
    }
    Ok(periods)
}

struct Reconstruction<'a> {
    opening: &'a MaterialWorldRegister,
    current: &'a MaterialWorldRegister,
    history: &'a PublicVenueHistory,
    sources: Vec<AdmittedPublicVenueSource>,
    verified_visits: BTreeSet<[u8; 32]>,
    prior: Option<(u64, DecodedCityPdAttemptEvidence)>,
}

impl Reconstruction<'_> {
    fn admit_period(
        &mut self,
        original: CommittedVenuePeriod,
        period: u64,
    ) -> Result<(), MaterialRuntimeError> {
        self.admit_contacts(&original, period)?;
        self.validate_attempts(&original, period)?;
        self.prior = original.city_pd.map(|pd| (period, pd));
        Ok(())
    }

    fn admit_contacts(
        &mut self,
        original: &CommittedVenuePeriod,
        period: u64,
    ) -> Result<(), MaterialRuntimeError> {
        let original_history = original
            .material_organizer
            .public_venue
            .as_ref()
            .ok_or_else(invalid)?;
        if original_history
            .records
            .iter()
            .any(|record| !self.history.records.contains(record))
        {
            return Err(invalid());
        }
        for record in self.history.records.iter().filter(|record| {
            record.period == period
                && matches!(record.kind, PublicVenueRecordKind::ContactCompleted { .. })
        }) {
            if !original_history.records.contains(record) {
                return Err(invalid());
            }
            let (config, organizer, journal) = original
                .material_organizer
                .organizer
                .as_ref()
                .ok_or_else(invalid)?;
            let entries = journal
                .periods
                .iter()
                .find(|entries| entries.period == period)
                .ok_or_else(invalid)?;
            let token = public_venue::admit_public_venue_source(
                self.history,
                PublicVenueSourceProof::CommittedContact {
                    config,
                    organizer,
                    entries,
                    closed: &original.material_organizer.material,
                    record,
                },
            )
            .map_err(|_| invalid())?;
            self.sources.push(token);
        }
        if original_history
            .records
            .iter()
            .filter(|record| {
                matches!(
                    record.kind,
                    PublicVenueRecordKind::AuthoredInitialNotice
                        | PublicVenueRecordKind::ContactCompleted { .. }
                )
            })
            .count()
            != self.sources.len()
            || self
                .sources
                .iter()
                .any(|source| !original_history.records.contains(source.record()))
        {
            return Err(invalid());
        }
        Ok(())
    }

    fn validate_attempts(
        &mut self,
        original: &CommittedVenuePeriod,
        period: u64,
    ) -> Result<(), MaterialRuntimeError> {
        let Some(pd) = self.current.city_pd() else {
            return Ok(());
        };
        for attempt in pd
            .attempts
            .iter()
            .filter(|attempt| attempt.receipt.resolve_period == period)
        {
            let old = original.city_pd.as_ref().ok_or_else(invalid)?;
            if old
                .attempts
                .iter()
                .filter(|candidate| *candidate == attempt)
                .count()
                != 1
            {
                return Err(invalid());
            }
            let (decision, cases) = if period == 1 {
                let pd = self.opening.city_pd().ok_or_else(invalid)?;
                (
                    pd.state.last_decision.as_ref().ok_or_else(invalid)?,
                    &pd.state.cases,
                )
            } else {
                let (_, pd) = self
                    .prior
                    .as_ref()
                    .filter(|(previous, _)| *previous == period - 1)
                    .ok_or_else(invalid)?;
                (&pd.last_decision, &pd.cases)
            };
            if decision != &attempt.decision {
                return Err(invalid());
            }
            let CityPdDecision::Selected(intent) = &decision.decision else {
                return Err(invalid());
            };
            if !cases.iter().any(|case| case.case_id == intent.case_id) {
                return Err(invalid());
            }
            if attempt.funding.outcome == AgencyAttendanceOutcome::Paid {
                let source = validate_paid(
                    self.history,
                    original,
                    cases,
                    intent,
                    attempt,
                    &pd.config,
                    &self.sources,
                )?;
                if !self.verified_visits.insert(source) {
                    return Err(invalid());
                }
            } else {
                babylon_tick::material_world::validate_committed_nonpaid(
                    &attempt.funding,
                    &original.receipt_bytes,
                )
                .map_err(|_| invalid())?;
            }
        }
        Ok(())
    }
}

fn validate_paid(
    history: &PublicVenueHistory,
    original: &CommittedVenuePeriod,
    cases: &[CityPdCase],
    intent: &CityPdIntent,
    attempt: &CityPdAttempt,
    config: &CityPdConfig,
    sources: &[AdmittedPublicVenueSource],
) -> Result<[u8; 32], MaterialRuntimeError> {
    let old = original.city_pd.as_ref().ok_or_else(invalid)?;
    let original_history = original
        .material_organizer
        .public_venue
        .as_ref()
        .ok_or_else(invalid)?;
    let case = cases
        .iter()
        .find(|case| case.case_id == intent.case_id)
        .ok_or_else(invalid)?;
    let paid = public_venue::publish_paid_visit(
        &history.policy,
        config,
        intent,
        case,
        &attempt.funding,
        &original.receipt_bytes,
    )
    .map_err(|_| invalid())?;
    if !original_history.records.contains(paid.record())
        || attempt.receipt.shift_receipt_id != Some(paid.shift_evidence_id())
        || attempt.receipt.payment_receipt_id != Some(paid.payment_evidence_id())
        || attempt.receipt.player_witness_evidence_id
            != public_venue::read_public_visit(
                original_history,
                history.policy.controlled_actor_id,
                &paid,
            )
            .map_err(|_| invalid())?
        || !history.records.contains(paid.record())
    {
        return Err(invalid());
    }
    let acquired =
        public_venue::read_public_venue_sources(original_history, config.actor_id, &paid, sources)
            .map_err(|_| invalid())?;
    let newly: Vec<_> = acquired
        .iter()
        .filter(|source| {
            !cases
                .iter()
                .any(|case| case.source_id == source.record.source_id)
        })
        .collect();
    let ids: Vec<_> = newly.iter().map(|source| source.record.source_id).collect();
    if ids != attempt.receipt.acquired_public_fact_ids {
        return Err(invalid());
    }
    for source in newly {
        if !old.cases.iter().any(|case| {
            case.source_id == source.record.source_id
                && case.case_source_witness_id == Some(source.witness_id)
        }) {
            return Err(invalid());
        }
    }
    Ok(paid.record().source_id)
}
