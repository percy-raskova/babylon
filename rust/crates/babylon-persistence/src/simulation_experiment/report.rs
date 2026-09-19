//! Read mechanical receipts, verify replay/accounting, and emit evaluator inputs.
use super::{
    hex, product, sum, ExperimentError, ExperimentProfile, Result, SimulationExperimentV1,
    StartingSnapshot,
};
use babylon_bsl::{identity_codec::StableBslValue, structural_verbs::CollectingSink};
use babylon_graph::{hypergraph_store::HypergraphStore, stable_element::StableElementKey};
use babylon_material_circuit::{GoodId, MaterialCircuitState, ProcessId};
use babylon_practice_contract::OrderedPracticeActionBatch;
use babylon_tick::{
    material_replay::{MaterialReplaySession, PreparedMaterialTick},
    material_world::decode_material_receipts,
    replay_session::ReplayCommitDisposition,
};
use serde::Serialize;
use std::collections::BTreeMap;

mod wiring;
pub use wiring::{ReceiptCoverage, RuleExecution, WiringManifest};

#[derive(Clone, Debug, PartialEq, Eq, Serialize)]
pub struct ExperimentMetadata {
    pub profile: String,
    pub epoch: Option<String>,
    pub horizon: u64,
    pub seed: i64,
    pub source_snapshot_sha256: Option<String>,
    pub resolved_inputs_sha256: String,
}
#[derive(Clone, Debug, PartialEq, Eq, Serialize)]
pub struct EmploymentObservation {
    pub series_id: String,
    pub date: String,
    pub jobs: u64,
    pub period: u64,
    pub world_hash: String,
}
#[derive(Clone, Debug, PartialEq, Eq, Serialize)]
pub struct FreightObservation {
    pub series_id: String,
    pub period_start: String,
    pub period_end_exclusive: String,
    pub arrived_kg: u64,
    pub period: u64,
    pub world_hash: String,
}
#[derive(Clone, Debug, PartialEq, Eq, Serialize)]
pub struct ExperimentTrajectory {
    pub schema_version: u8,
    pub experiment: ExperimentMetadata,
    pub completed_periods: u64,
    pub employment: Vec<EmploymentObservation>,
    pub freight: Vec<FreightObservation>,
    pub observed_choice_count: u64,
}
#[derive(Clone, Debug, PartialEq, Eq, Serialize)]
pub struct PeriodEvidence {
    pub period: u64,
    pub world_hash: String,
    pub tick_content_sha256: String,
    pub produced_batches: u64,
    pub dispatched_units: u64,
    pub arrived_units: u64,
    pub conserved_mass_grams: u64,
    pub considered_rules: u64,
    pub fired_rules: u64,
    pub rule_execution: Vec<RuleExecution>,
    pub receipt_coverage: ReceiptCoverage,
    pub production: Vec<ProductionEvidence>,
    pub staffing: Vec<StaffingEvidence>,
}
#[derive(Clone, Debug, PartialEq, Eq, Serialize)]
pub struct ProductionEvidence {
    pub process_id: String,
    pub process_key: String,
    pub produced_batches: u64,
}
#[derive(Clone, Debug, PartialEq, Eq, Serialize)]
pub struct StaffingEvidence {
    pub subject: String,
    pub employed: u64,
    pub reserve: u64,
}
#[derive(Debug, Serialize)]
pub struct CapturedSetup {
    pub wiring: WiringManifest,
    pub resolved_inputs: super::setup::ResolvedInputs,
    pub canonical_spec: SimulationExperimentV1,
    pub experiment_input_sha256: String,
    pub defines_sha256: String,
    pub foundation_sha256: String,
    pub content_sha256: String,
    pub rules_sha256: String,
    pub reference_sha256: String,
    pub initialization_evidence: &'static str,
    pub checkpoint_restarts: u64,
    pub final_year_active_periods: u64,
    pub conserved_mass_grams: u64,
}
#[derive(Debug)]
pub struct ExperimentRun {
    pub trajectory: ExperimentTrajectory,
    pub periods: Vec<PeriodEvidence>,
    pub captured_setup: CapturedSetup,
    pub captured_defines: Vec<u8>,
    pub foundation_bytes: Vec<u8>,
}

fn month_days(year: u64, month: u64) -> u64 {
    match month {
        1 | 3 | 5 | 7 | 8 | 10 | 12 => 31,
        4 | 6 | 9 | 11 => 30,
        2 => {
            if year.is_multiple_of(400) || (year.is_multiple_of(4) && !year.is_multiple_of(100)) {
                29
            } else {
                28
            }
        }
        _ => 0,
    }
}

/// Gregorian reporting date. The material engine still advances exactly 28 days.
/// # Errors
/// Refuses malformed dates, unsupported years or arithmetic overflow.
pub fn date_after(epoch: &str, days: u64) -> Result<String> {
    let fields = epoch
        .split('-')
        .map(str::parse::<u64>)
        .collect::<std::result::Result<Vec<_>, _>>()
        .map_err(|_| ExperimentError::Epoch)?;
    let [mut year, mut month, mut day]: [u64; 3] = fields
        .as_slice()
        .try_into()
        .map_err(|_| ExperimentError::Epoch)?;
    if !(1900..=2200).contains(&year) || day == 0 || day > month_days(year, month) || days > 10_000
    {
        return Err(ExperimentError::Epoch);
    }
    for _ in 0..days {
        day += 1;
        if day > month_days(year, month) {
            day = 1;
            month += 1;
            if month == 13 {
                month = 1;
                year += 1;
            }
        }
    }
    Ok(format!("{year:04}-{month:02}-{day:02}"))
}
fn total(mut values: impl Iterator<Item = u64>) -> Result<u64> {
    values.try_fold(0, sum)
}
fn mass(state: &MaterialCircuitState) -> Result<u64> {
    let coefficients: BTreeMap<_, _> = state
        .freight_mass_coefficients
        .iter()
        .map(|r| ((r.good_id, r.unit_id), r.grams_per_unit))
        .collect();
    state
        .inventory
        .iter()
        .map(|r| (r.good_id, r.unit_id, r.quantity))
        .chain(
            state
                .freight
                .iter()
                .map(|r| (r.good_id, r.unit_id, r.quantity)),
        )
        .try_fold(0, |n, (good, unit, quantity)| {
            sum(
                n,
                product(
                    quantity,
                    *coefficients
                        .get(&(good, unit))
                        .ok_or(ExperimentError::Conservation)?,
                )?,
            )
        })
}
fn staffing(candidate: &PreparedMaterialTick<HypergraphStore>) -> Result<Vec<StaffingEvidence>> {
    let mut rows = Vec::new();
    for event in candidate
        .graph_report()
        .successful_event_batch()
        .events()
        .iter()
        .filter(|e| e.event_type() == "WORKFORCE_STAFFING")
    {
        let field = |name: &str| {
            event
                .fields()
                .iter()
                .find(|(k, _)| k == name)
                .map(|(_, v)| v)
        };
        let Some(StableBslValue::Node(StableElementKey::Node { local_name, .. })) =
            field("subject")
        else {
            return Err(ExperimentError::Observation);
        };
        let number = |key| match field(key) {
            Some(StableBslValue::Int(v)) => {
                u64::try_from(*v).map_err(|_| ExperimentError::Observation)
            }
            _ => Err(ExperimentError::Observation),
        };
        rows.push(StaffingEvidence {
            subject: local_name.clone(),
            employed: number("closing-employed")?,
            reserve: number("closing-reserve")?,
        });
    }
    rows.sort_by(|a, b| a.subject.cmp(&b.subject));
    Ok(rows)
}
fn observations(
    spec: &SimulationExperimentV1,
    candidate: &PreparedMaterialTick<HypergraphStore>,
    trajectory: &mut ExperimentTrajectory,
    evidence: &PeriodEvidence,
) -> Result<()> {
    let period = candidate.identity().resolve_tick();
    if spec.profile == ExperimentProfile::HistoricalEmployment {
        let date = date_after(
            spec.epoch.as_deref().ok_or(ExperimentError::Epoch)?,
            product(period, 28)?,
        )?;
        for (subject, series) in [
            ("workforce-sheet-rolling", "26163/331"),
            ("workforce-panel-forming", "26099/332"),
            ("workforce-subassembly-making", "26163/3363"),
            ("workforce-meal-milling", "26161/311"),
            ("workforce-meal-packaging", "26125/311"),
        ] {
            let row = evidence
                .staffing
                .iter()
                .find(|r| r.subject == subject)
                .ok_or(ExperimentError::Observation)?;
            trajectory.employment.push(EmploymentObservation {
                series_id: series.to_owned(),
                date: date.clone(),
                jobs: row.employed,
                period,
                world_hash: evidence.world_hash.clone(),
            });
        }
    } else if spec.profile == ExperimentProfile::HistoricalFreight {
        let receipts = decode_material_receipts(candidate.material().receipt_bytes())
            .map_err(|_| ExperimentError::Observation)?;
        // The admitted profile contains exactly one HS72 inbound order. No
        // domestic route, destination county or substitute commodity is scored.
        let arrived_kg = total(receipts.arrivals.iter().map(|r| r.quantity))?;
        let epoch = spec.epoch.as_deref().ok_or(ExperimentError::Epoch)?;
        trajectory.freight.push(FreightObservation {
            series_id: "detroit_canada_truck_import_hs72".to_owned(),
            period_start: date_after(epoch, product(period - 1, 28)?)?,
            period_end_exclusive: date_after(epoch, product(period, 28)?)?,
            arrived_kg,
            period,
            world_hash: evidence.world_hash.clone(),
        });
    }
    Ok(())
}
fn prepare(
    session: &MaterialReplaySession<HypergraphStore>,
) -> Result<PreparedMaterialTick<HypergraphStore>> {
    let actions = OrderedPracticeActionBatch::empty(
        session.graph_session().session_identity().clone(),
        session.completed_tick() + 1,
    )
    .map_err(|_| ExperimentError::Foundation)?;
    session
        .prepare_advance(&actions)
        .map_err(|_| ExperimentError::Foundation)
}
fn publish(
    session: &mut MaterialReplaySession<HypergraphStore>,
    candidate: PreparedMaterialTick<HypergraphStore>,
) -> Result<()> {
    session
        .commit_prepared_and_publish(&mut CollectingSink::default(), candidate, |_| {
            Ok::<_, std::convert::Infallible>(ReplayCommitDisposition::Committed)
        })
        .map(|_| ())
        .map_err(|_| ExperimentError::Foundation)
}
fn initial_report(
    spec: &SimulationExperimentV1,
    foundation: &crate::material_runtime::MaterialRuntimeFoundation,
    session: &MaterialReplaySession<HypergraphStore>,
    initial_mass: u64,
) -> Result<(CapturedSetup, ExperimentTrajectory)> {
    let graph = foundation.graph_foundation();
    let setup = CapturedSetup {
        wiring: wiring::capture(foundation)?,
        resolved_inputs: super::setup::capture(spec, graph)?,
        canonical_spec: spec.clone(),
        experiment_input_sha256: hex(&spec.sha256()?),
        defines_sha256: hex(&graph.content_digest().defines_hash),
        foundation_sha256: hex(&foundation.digest()),
        content_sha256: hex(&foundation.spec().content_digest),
        rules_sha256: hex(&graph.content_digest().rules_hash),
        reference_sha256: hex(graph.reference_digest().as_bytes()),
        initialization_evidence: if spec.starting_snapshot.is_some() {
            "Observed starting snapshot; Derived capacities; Designed hours, recipes, reserves, inventories, orders and travel"
        } else {
            "Designed diagnostic content"
        },
        checkpoint_restarts: 0,
        final_year_active_periods: 0,
        conserved_mass_grams: initial_mass,
    };
    let mut trajectory = ExperimentTrajectory {
        schema_version: 1,
        experiment: ExperimentMetadata {
            profile: spec.profile.id().to_owned(),
            epoch: spec.epoch.clone(),
            horizon: spec.horizon,
            seed: spec.seed,
            source_snapshot_sha256: spec.source_snapshot_sha256.clone(),
            resolved_inputs_sha256: setup.defines_sha256.clone(),
        },
        completed_periods: 0,
        employment: Vec::new(),
        freight: Vec::new(),
        observed_choice_count: 0,
    };
    if let Some(StartingSnapshot::Employment { date, series }) = &spec.starting_snapshot {
        for row in series {
            trajectory.employment.push(EmploymentObservation {
                series_id: row.series_id.clone(),
                date: date.clone(),
                jobs: row.jobs,
                period: 0,
                world_hash: hex(&session
                    .current_world_hash()
                    .map_err(|_| ExperimentError::Foundation)?),
            });
        }
    }
    Ok((setup, trajectory))
}

fn period_evidence(
    candidate: &PreparedMaterialTick<HypergraphStore>,
    initial_mass: u64,
    process_keys: &BTreeMap<ProcessId, String>,
    wiring: &WiringManifest,
) -> Result<PeriodEvidence> {
    let receipts = decode_material_receipts(candidate.material().receipt_bytes())
        .map_err(|_| ExperimentError::Observation)?;
    if receipts.resolve_tick != candidate.identity().resolve_tick() {
        return Err(ExperimentError::Observation);
    }
    let conserved = mass(candidate.material().register().state())?;
    if conserved != initial_mass {
        return Err(ExperimentError::Conservation);
    }
    let report = candidate.graph_report().report();
    let staffing = staffing(candidate)?;
    let (receipt_coverage, rule_execution) = wiring::verify(wiring, report, &receipts, &staffing)?;
    let evidence = PeriodEvidence {
        period: candidate.identity().resolve_tick(),
        world_hash: hex(&candidate.identity().result_world_hash()),
        tick_content_sha256: hex(candidate.identity().tick_content_hash().as_bytes()),
        produced_batches: total(receipts.production.iter().map(|r| r.produced_batches))?,
        dispatched_units: total(receipts.dispatches.iter().map(|r| r.quantity))?,
        arrived_units: total(receipts.arrivals.iter().map(|r| r.quantity))?,
        conserved_mass_grams: conserved,
        considered_rules: u64::try_from(report.considered)
            .map_err(|_| ExperimentError::Arithmetic)?,
        fired_rules: u64::try_from(report.fired).map_err(|_| ExperimentError::Arithmetic)?,
        rule_execution,
        receipt_coverage,
        production: receipts
            .production
            .iter()
            .map(|r| {
                Ok(ProductionEvidence {
                    process_id: hex(&r.process_id.as_bytes()),
                    process_key: process_keys
                        .get(&r.process_id)
                        .ok_or(ExperimentError::Observation)?
                        .clone(),
                    produced_batches: r.produced_batches,
                })
            })
            .collect::<Result<Vec<_>>>()?,
        staffing,
    };
    Ok(evidence)
}

fn qualify_activity(
    profile: ExperimentProfile,
    setup: &CapturedSetup,
    periods: &[PeriodEvidence],
) -> Result<()> {
    if profile == ExperimentProfile::Sustained && setup.final_year_active_periods != 13 {
        return Err(ExperimentError::Incomplete);
    }
    if profile == ExperimentProfile::Depletion
        && periods
            .iter()
            .rev()
            .take(13)
            .any(|r| r.produced_batches != 0 || r.dispatched_units != 0)
    {
        return Err(ExperimentError::Incomplete);
    }
    Ok(())
}

/// Execute and qualify a profile with yearly checkpoint reconstruction in parallel
/// with its uninterrupted replay. A differing tick or failed account is an error.
/// # Errors
/// Refuses incomplete execution, changed identities, accounting faults or missing receipts.
pub fn run(spec: &SimulationExperimentV1) -> Result<ExperimentRun> {
    let foundation = spec.create_foundation()?;
    let initial_mass = mass(foundation.initial_register().state())?;
    let mut session = foundation
        .reconstruct_captured()
        .map_err(|_| ExperimentError::Foundation)?
        .into_session()
        .map_err(|_| ExperimentError::Foundation)?;
    let mut restarted = foundation
        .reconstruct_captured()
        .map_err(|_| ExperimentError::Foundation)?
        .into_session()
        .map_err(|_| ExperimentError::Foundation)?;
    let graph = foundation.graph_foundation();
    let process_keys: BTreeMap<_, _> = if spec.profile == ExperimentProfile::HistoricalFreight {
        BTreeMap::new()
    } else {
        crate::sector_bundle::foundation::decode_stored_bundle_defines(
            graph.content_bundle().defines_bytes(),
            graph.content_digest().defines_hash,
        )
        .map_err(|_| ExperimentError::Content)?
        .catalog()
        .processes()
        .iter()
        .map(|p| (p.id(), p.key.clone()))
        .collect()
    };
    let (mut setup, mut trajectory) = initial_report(spec, &foundation, &session, initial_mass)?;
    let mut periods = Vec::new();
    for period in 1..=spec.horizon {
        let candidate = prepare(&session)?;
        let replayed = prepare(&restarted)?;
        if candidate.identity() != replayed.identity()
            || candidate.material().register().canonical_bytes()
                != replayed.material().register().canonical_bytes()
        {
            return Err(ExperimentError::Foundation);
        }
        let evidence = period_evidence(&candidate, initial_mass, &process_keys, &setup.wiring)?;
        let report = candidate.graph_report().report();
        trajectory.observed_choice_count = sum(
            trajectory.observed_choice_count,
            u64::try_from(report.choice_receipts.len()).map_err(|_| ExperimentError::Arithmetic)?,
        )?;
        observations(spec, &candidate, &mut trajectory, &evidence)?;
        if period > spec.horizon - 13
            && evidence.produced_batches > 0
            && evidence.dispatched_units > 0
        {
            setup.final_year_active_periods += 1;
        }
        let replacement = if period.is_multiple_of(13) || period == spec.horizon {
            let mut restored = foundation
                .reconstruct_captured()
                .map_err(|_| ExperimentError::Foundation)?
                .into_session()
                .map_err(|_| ExperimentError::Foundation)?;
            restored
                .restore_full_checkpoint(
                    replayed.graph_report().result_stable_graph(),
                    replayed.graph_report().material_state_rows(),
                    replayed.graph_report().result_registers().canonical_bytes(),
                    replayed.material().register().canonical_bytes(),
                )
                .map_err(|_| ExperimentError::Foundation)?;
            Some(restored)
        } else {
            None
        };
        publish(&mut session, candidate)?;
        publish(&mut restarted, replayed)?;
        if let Some(restored) = replacement {
            restarted = restored;
            if restarted
                .current_world_hash()
                .map_err(|_| ExperimentError::Foundation)?
                != session
                    .current_world_hash()
                    .map_err(|_| ExperimentError::Foundation)?
            {
                return Err(ExperimentError::Foundation);
            }
            setup.checkpoint_restarts += 1;
        }
        trajectory.completed_periods = period;
        periods.push(evidence);
    }
    qualify_activity(spec.profile, &setup, &periods)?;
    if prepare(&session).is_ok() {
        return Err(ExperimentError::Horizon);
    }
    Ok(ExperimentRun {
        trajectory,
        periods,
        captured_setup: setup,
        captured_defines: graph.content_bundle().defines_bytes().to_vec(),
        foundation_bytes: foundation.canonical_bytes().to_vec(),
    })
}
/// Inventory-boundary identity useful to inspectors; this is not a domestic good.
#[must_use]
pub fn historical_freight_good() -> GoodId {
    super::freight::good_id()
}
