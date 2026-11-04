//! Resolve the saved agency intent against the detached material close.

use crate::public_venue::AdmittedPublicVenueSource;
use crate::public_venue::PublicVenueAcquisition;
use babylon_graph::stable_element::StableElementResolver;
use babylon_material_circuit::{
    AgencyAttendanceOutcome, AgencyObservationFundingReceipt, MaterialCatalog,
};
use babylon_practice_contract::{
    CityPdCase, CityPdCaseSource, CityPdCaseStatus, CityPdConfig, CityPdDecision, CityPdIntent,
    CityPdOutcome, CityPdReceipt, PublicVenueRecordKind,
};

use super::{CityPdAttempt, CityPdRegister, MaterialWorldError, PreparedMaterialWorld};

pub(crate) fn resolve(
    candidate: &mut PreparedMaterialWorld,
    catalog: &MaterialCatalog,
    resolver: &StableElementResolver,
    opening_sources: &[AdmittedPublicVenueSource],
) -> Result<(), MaterialWorldError> {
    let mut pd = candidate
        .city_pd_opening()
        .cloned()
        .ok_or(MaterialWorldError::Wire)?;
    let decision = pd
        .state
        .last_decision
        .clone()
        .ok_or(MaterialWorldError::Wire)?;
    let attendance = candidate.agency_attendance().to_vec();
    let mut venue = candidate
        .register()
        .public_venue()
        .cloned()
        .ok_or(MaterialWorldError::Wire)?;
    match &decision.decision {
        CityPdDecision::NoCases | CityPdDecision::NoFunds { .. } => {
            if !attendance.is_empty() {
                return Err(MaterialWorldError::Wire);
            }
        }
        CityPdDecision::Selected(intent) => {
            let [funding] = attendance.as_slice() else {
                return Err(MaterialWorldError::Wire);
            };
            let index = pd
                .state
                .cases
                .iter()
                .position(|case| case.case_id == intent.case_id)
                .ok_or(MaterialWorldError::Wire)?;
            let original_case = pd.state.cases[index].clone();
            if original_case.status != CityPdCaseStatus::Open
                || intent.resolve_period != candidate.register().completed_tick()
            {
                return Err(MaterialWorldError::Wire);
            }
            let mut receipt = new_receipt(&pd.config, intent, funding);
            if funding.outcome == AgencyAttendanceOutcome::Paid {
                let published = crate::public_venue::publish_paid_visit(
                    &venue.policy,
                    &pd.config,
                    intent,
                    &original_case,
                    funding,
                    candidate.receipt_bytes(),
                )
                .map_err(|_| MaterialWorldError::Wire)?;
                venue.records.push(published.record().clone());
                venue.records.sort_by_key(|row| (row.period, row.source_id));
                venue.validate().map_err(|_| MaterialWorldError::Wire)?;
                receipt.shift_receipt_id = Some(published.shift_evidence_id());
                receipt.payment_receipt_id = Some(published.payment_evidence_id());
                receipt.player_witness_evidence_id = crate::public_venue::read_public_visit(
                    &venue,
                    candidate
                        .register()
                        .organizer_config()
                        .ok_or(MaterialWorldError::Wire)?
                        .controlled_actor_id,
                    &published,
                )
                .map_err(|_| MaterialWorldError::Wire)?;
                let sources = crate::public_venue::read_public_venue_sources(
                    &venue,
                    pd.config.actor_id,
                    &published,
                    opening_sources,
                )
                .map_err(|_| MaterialWorldError::Wire)?;
                record_acquisitions(&mut pd, &mut receipt, sources, intent.resolve_period)?;
                pd.state.cases[index].status = CityPdCaseStatus::Closed;
                pd.state.cases.sort_by_key(|case| case.case_id);
                candidate.set_public_venue(catalog, venue, resolver)?;
            }
            let receipt = babylon_practice_contract::finalize_city_pd_receipt(receipt)
                .map_err(|_| MaterialWorldError::Wire)?;
            pd.attempts.push(CityPdAttempt {
                decision: decision.clone(),
                funding: funding.clone(),
                receipt,
            });
        }
    }
    pd.decide_next(
        catalog,
        candidate.register().state(),
        candidate.register().completed_tick(),
        resolver,
    )?;
    candidate.set_city_pd(catalog, pd, resolver)
}

fn new_receipt(
    config: &CityPdConfig,
    intent: &CityPdIntent,
    funding: &AgencyObservationFundingReceipt,
) -> CityPdReceipt {
    CityPdReceipt {
        receipt_id: [0; 32],
        campaign_id: config.campaign_id,
        actor_id: config.actor_id,
        case_id: intent.case_id,
        intent_id: intent.intent_id,
        resolve_period: intent.resolve_period,
        outcome: match funding.outcome {
            AgencyAttendanceOutcome::Paid => CityPdOutcome::Completed,
            AgencyAttendanceOutcome::NoFunds => CityPdOutcome::InsufficientFunds,
            AgencyAttendanceOutcome::InsufficientTime => CityPdOutcome::InsufficientTime,
        },
        attendance_hours: funding.attended_hours,
        wage_micros: funding.paid.micro_units(),
        shift_receipt_id: None,
        payment_receipt_id: None,
        acquired_public_fact_ids: Vec::new(),
        case_source_evidence_id: None,
        player_witness_evidence_id: None,
    }
}

fn record_acquisitions(
    pd: &mut CityPdRegister,
    receipt: &mut CityPdReceipt,
    sources: Vec<PublicVenueAcquisition>,
    period: u64,
) -> Result<(), MaterialWorldError> {
    let mut acquired = Vec::new();
    for source in sources {
        if pd
            .state
            .cases
            .iter()
            .any(|case| case.source_id == source.record.source_id)
        {
            continue;
        }
        let PublicVenueRecordKind::ContactCompleted {
            organizer_receipt_id,
            ..
        } = source.record.kind
        else {
            return Err(MaterialWorldError::Wire);
        };
        let mut case = CityPdCase {
            case_id: [0; 32],
            actor_id: pd.config.actor_id,
            subject_id: source.record.workplace_id,
            county: pd.config.county,
            public_venue_id: source.record.venue_id,
            source_id: source.record.source_id,
            source_kind: CityPdCaseSource::ObservedOrganizerReceipt,
            source_receipt_id: Some(organizer_receipt_id),
            case_source_witness_id: Some(source.witness_id),
            observed_period: source.record.period,
            acquired_period: period,
            status: CityPdCaseStatus::Open,
        };
        case.case_id = babylon_practice_contract::city_pd_case_id(&case)
            .map_err(|_| MaterialWorldError::Wire)?;
        acquired.push((case.source_id, source.witness_id));
        pd.state.cases.push(case);
    }
    acquired.sort_unstable();
    if acquired.windows(2).any(|pair| pair[0].0 >= pair[1].0) {
        return Err(MaterialWorldError::Wire);
    }
    if !acquired.is_empty() {
        receipt
            .acquired_public_fact_ids
            .extend(acquired.iter().map(|(source, _)| *source));
        receipt.case_source_evidence_id = super::city_pd::acquired_evidence(&acquired)?;
    }
    Ok(())
}
