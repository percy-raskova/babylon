use std::collections::BTreeMap;

use babylon_bsl::structural_verbs::CollectingSink;
use babylon_graph::hypergraph_store::HypergraphStore;
use babylon_kernel::content_digest::sha256_of;
use babylon_persistence::michigan_material::{MichiganDeliveryPreset, MichiganMaterialCatalog};
use babylon_persistence::simulation_experiment::SimulationExperimentV1;
use babylon_practice_contract::OrderedPracticeActionBatch;
use babylon_tick::material_replay::MaterialReplaySession;
use babylon_tick::replay_session::ReplayCommitDisposition;
use serde::Serialize;
use serde_json::{json, Value};

use super::artifacts::{contract, Result};
use super::observe::{self, PeriodRow};

pub const BASELINE: &str = include_str!("../../../../../content/scenarios/michigan/defines.toml");
pub const PERIODS: u64 = 16;
#[derive(Clone, Copy)]
pub struct CaseSpec {
    pub id: &'static str,
    pub delivery: MichiganDeliveryPreset,
    pub opening_sheet_kg: u64,
}

pub const SPECS: [CaseSpec; 4] = [
    CaseSpec {
        id: "standard-0",
        delivery: MichiganDeliveryPreset::Standard,
        opening_sheet_kg: 0,
    },
    CaseSpec {
        id: "delayed-0",
        delivery: MichiganDeliveryPreset::Delayed,
        opening_sheet_kg: 0,
    },
    CaseSpec {
        id: "standard-320",
        delivery: MichiganDeliveryPreset::Standard,
        opening_sheet_kg: 320,
    },
    CaseSpec {
        id: "delayed-320",
        delivery: MichiganDeliveryPreset::Delayed,
        opening_sheet_kg: 320,
    },
];

pub struct Case {
    pub spec: CaseSpec,
    pub catalog: MichiganMaterialCatalog,
    pub experiment: SimulationExperimentV1,
}

pub fn hex(bytes: &[u8]) -> String {
    use std::fmt::Write;
    let mut result = String::with_capacity(bytes.len() * 2);
    for byte in bytes {
        write!(result, "{byte:02x}").expect("writing to String cannot fail");
    }
    result
}

pub fn digest_json(value: &impl Serialize) -> Result<String> {
    Ok(hex(&sha256_of(&serde_json::to_vec(value)?)))
}

fn regional_parameters(catalog: &MichiganMaterialCatalog) -> Result<Value> {
    let capture: Value = serde_json::from_slice(catalog.defines_bytes())?;
    let definitions = capture
        .get("defines")
        .and_then(Value::as_object)
        .ok_or_else(|| contract("missing current captured numeric definitions"))?;
    let parameters = [
        "SCHEMA_VERSION",
        "TICK_DURATION_DAYS",
        "HORIZON_PERIODS",
        "staffing",
        "process",
        "corridor",
        "route",
        "shared_freight",
        "regional_mass",
    ]
    .into_iter()
    .map(|key| {
        definitions
            .get(key)
            .cloned()
            .map(|value| (key.to_owned(), value))
            .ok_or_else(|| contract(format!("missing regional parameter {key}")))
    })
    .collect::<Result<serde_json::Map<String, Value>>>()?;
    Ok(Value::Object(parameters))
}

pub fn cases() -> Result<Vec<Case>> {
    let original = MichiganMaterialCatalog::from_defines_toml(BASELINE)
        .map_err(|error| contract(format!("baseline validation: {error}")))?;
    let baseline = regional_parameters(&original)?;
    if baseline["HORIZON_PERIODS"] != PERIODS
        || baseline["process"]["panel_forming"]["OPENING_INPUT_UNITS"] != 0
        || baseline["process"]["panel_forming"]["OPENING_PLANNED_BATCHES"] != 0
        || original.processes().len() != 5
        || original.routes().len() != 3
    {
        return Err(contract(
            "embedded baseline is outside the accepted Michigan comparison",
        ));
    }
    SPECS
        .iter()
        .map(|&spec| {
            let experiment = SimulationExperimentV1::parse(&serde_json::to_vec(&json!({
                "schema": "SimulationExperimentV1", "profile": "delivery_stock",
                "epoch": null, "horizon": PERIODS, "seed": 319,
                "source_snapshot_sha256": null, "starting_snapshot": null,
                "interventions": [
                    {"kind": "regional_delivery", "delivery": match spec.delivery {
                        MichiganDeliveryPreset::Standard => "standard",
                        MichiganDeliveryPreset::Delayed => "delayed",
                        _ => return Err(contract("unadmitted causal delivery profile")),
                    }},
                    {"kind": "opening_sheet_stock", "kilograms": spec.opening_sheet_kg}
                ]
            }))?)
            .map_err(|error| contract(format!("case inputs: {error}")))?;
            let catalog = experiment
                .regional_catalog()
                .map_err(|error| contract(format!("{} validation: {error}", spec.id)))?;
            Ok(Case {
                spec,
                catalog,
                experiment,
            })
        })
        .collect()
}

pub fn experiment_identity(cases: &[Case]) -> Result<Value> {
    let rows = cases
        .iter()
        .map(|case| {
            Ok(json!({
                "case": case.spec.id,
                "preset": case.spec.delivery.id(),
                "opening_sheet_kg": case.spec.opening_sheet_kg,
                "experiment": case.experiment,
                "resolved_defines": serde_json::from_slice::<Value>(case.catalog.defines_bytes())?,
                "canonical_defines_utf8": std::str::from_utf8(case.catalog.defines_bytes())
                    .map_err(|_| contract("canonical defines are not UTF-8"))?,
                "defines_sha256": hex(&case.catalog.defines_hash())
            }))
        })
        .collect::<Result<Vec<_>>>()?;
    Ok(json!({"schema": "SimulationExperimentMatrixV1", "periods": PERIODS, "cases": rows}))
}

#[derive(Serialize)]
pub struct CaseResult {
    pub case: &'static str,
    pub foundation: Value,
    pub rows: Vec<PeriodRow>,
}

fn foundation(case: &Case) -> Result<(Value, MaterialReplaySession<HypergraphStore>)> {
    let foundation = case
        .experiment
        .create_foundation()
        .map_err(|error| contract(format!("{} foundation: {error:?}", case.spec.id)))?;
    let graph = foundation.graph_foundation();
    let seed = i64::from_be_bytes(graph.rng_seed().to_be_bytes());
    if seed != 319 || foundation.spec().horizon_ticks != PERIODS {
        return Err(contract("selected composition changed its seed or horizon"));
    }
    let identity = json!({
        "foundation_sha256": hex(&foundation.digest()),
        "material_content_sha256": hex(&foundation.spec().content_digest),
        "graph_defines_sha256": hex(&graph.content_digest().defines_hash),
        "rules_sha256": hex(&graph.content_digest().rules_hash),
        "reference_sha256": hex(graph.reference_digest().as_bytes()),
        "seed": seed,
        "opening_world_has_completed_receipt": false
    });
    let session = foundation
        .into_session()
        .map_err(|error| contract(format!("material session: {error:?}")))?;
    Ok((identity, session))
}

pub fn run_case(case: &Case, mut emit: impl FnMut(&PeriodRow) -> Result<()>) -> Result<CaseResult> {
    let (identity, mut session) = foundation(case)?;
    let period_count =
        usize::try_from(PERIODS).map_err(|_| contract("period bound exceeds platform capacity"))?;
    let mut rows = Vec::with_capacity(period_count);
    for period in 1..=PERIODS {
        let actions = OrderedPracticeActionBatch::empty(
            session.graph_session().session_identity().clone(),
            period,
        )
        .map_err(|error| contract(format!("empty actions: {error:?}")))?;
        let candidate = session
            .prepare_advance(&actions)
            .map_err(|error| contract(format!("{} period {period}: {error:?}", case.spec.id)))?;
        let report = candidate.graph_report().report();
        if !report.choice_receipts.is_empty()
            || report.per_rule_considered != [("material/period".to_owned(), 1)]
            || report.per_rule_fired != [("material/period".to_owned(), 1)]
            || report.considered != 1
            || report.fired != 1
        {
            return Err(contract(
                "expected exactly one deterministic material/period invocation",
            ));
        }
        let row = observe::period(case, session.material().state(), &candidate)?;
        session
            .commit_prepared_and_publish(&mut CollectingSink::default(), candidate, |_| {
                Ok::<_, std::convert::Infallible>(ReplayCommitDisposition::Committed)
            })
            .map_err(|error| contract(format!("local publication: {error:?}")))?;
        emit(&row)?;
        rows.push(row);
    }
    Ok(CaseResult {
        case: case.spec.id,
        foundation: identity,
        rows,
    })
}

fn duration(periods: &[u64]) -> Value {
    let mut longest = 0;
    let mut current = 0;
    let mut previous = None;
    for &period in periods {
        current = if previous == Some(period - 1) {
            current + 1
        } else {
            1
        };
        longest = longest.max(current);
        previous = Some(period);
    }
    json!({"periods": periods, "total_periods": periods.len(), "longest_consecutive_periods": longest})
}

fn milestone(result: &CaseResult, key: &str, target: u64) -> Option<u64> {
    let mut cumulative = 0;
    for row in &result.rows {
        for process in &row.processes {
            if process.process == key {
                cumulative += process
                    .completed_receipt
                    .as_ref()
                    .map_or(0, |receipt| receipt.produced_output_units);
            }
        }
        if cumulative >= target {
            return Some(row.period);
        }
    }
    None
}

fn comparison(results: &[CaseResult], left: usize, right: usize, label: &str) -> Value {
    let delta = |key, target| {
        let a = i64::try_from(milestone(&results[left], key, target)?).ok()?;
        let b = i64::try_from(milestone(&results[right], key, target)?).ok()?;
        Some(b - a)
    };
    json!({"comparison": label, "reference": results[left].case, "changed": results[right].case,
        "first_subassembly_period_difference": delta("subassembly-making", 1),
        "completion_30_period_difference": delta("subassembly-making", 30)})
}

pub fn summarize(results: &[CaseResult]) -> Result<Value> {
    let period_count =
        usize::try_from(PERIODS).map_err(|_| contract("period bound exceeds platform capacity"))?;
    if results.len() != 4
        || results
            .iter()
            .zip(SPECS)
            .any(|(result, spec)| result.case != spec.id || result.rows.len() != period_count)
    {
        return Err(contract(
            "summary requires the exact complete four-case matrix",
        ));
    }
    let control = results
        .first()
        .ok_or_else(|| contract("missing baseline control"))?;
    let mut cases = Vec::new();
    for result in results {
        for (a, b) in control.rows.iter().zip(&result.rows) {
            if a.food_evidence() != b.food_evidence() {
                return Err(contract(format!(
                    "food control diverged in {} period {}",
                    result.case, b.period
                )));
            }
        }
        let mut bounds: BTreeMap<String, BTreeMap<String, Vec<u64>>> = BTreeMap::new();
        for row in &result.rows {
            for process in &row.processes {
                if let Some(next) = &process.next_opening {
                    for bound in &next.limiting_bounds {
                        bounds
                            .entry(process.process.clone())
                            .or_default()
                            .entry((*bound).to_string())
                            .or_default()
                            .push(next.period);
                    }
                }
            }
        }
        let last = result
            .rows
            .last()
            .ok_or_else(|| contract("missing final period"))?;
        let durations: BTreeMap<_, _> = bounds
            .iter()
            .map(|(process, constraints)| {
                (
                    process,
                    constraints
                        .iter()
                        .map(|(bound, periods)| (bound, duration(periods)))
                        .collect::<BTreeMap<_, _>>(),
                )
            })
            .collect();
        let cumulative: BTreeMap<_, _> = last
            .processes
            .iter()
            .map(|process| {
                let produced: u64 = result
                    .rows
                    .iter()
                    .flat_map(|row| row.processes.iter())
                    .filter(|row| row.process == process.process)
                    .map(|row| {
                        row.completed_receipt
                            .as_ref()
                            .map_or(0, |receipt| receipt.produced_output_units)
                    })
                    .sum();
                (&process.process, produced)
            })
            .collect();
        let staffing: Vec<_> = result.rows.iter().flat_map(|row| row.processes.iter()
            .filter(|process| process.staffing.hires > 0 || process.staffing.separations > 0)
            .map(move |process| json!({"period": row.period, "process": process.process,
                "employed": process.staffing.closing_employed, "reserve": process.staffing.closing_reserve,
                "hires": process.staffing.hires, "separations": process.staffing.separations}))).collect();
        cases.push(json!({"case": result.case, "foundation": result.foundation,
            "first_panel_output_period": milestone(result, "panel-forming", 1),
            "first_subassembly_output_period": milestone(result, "subassembly-making", 1),
            "reaches_30_subassemblies_period": milestone(result, "subassembly-making", 30),
            "final_subassemblies": last.output("subassembly-making"),
            "final_packaged_meal_kg": last.output("meal-packaging"),
            "final_unsold_panels": last.output("panel-forming"),
            "cumulative_output_by_process": cumulative,
            "constraint_durations_including_ties": durations,
            "staffing_movements": staffing,
            "period_evidence_sha256": digest_json(&result.rows)?}));
    }
    Ok(
        json!({"schema": "MichiganDeliveryStockSummaryV1", "food_control_equal": true,
        "interpretation": "Added 320 kg is a Designed initial endowment. Finite orders cap terminal output; no equal-resource or fun claim.",
        "comparisons": [comparison(results, 0, 1, "delivery_without_buffer"), comparison(results, 2, 3, "delivery_with_buffer"),
            comparison(results, 0, 2, "stock_with_standard_delivery"), comparison(results, 1, 3, "stock_with_delayed_delivery")],
        "cases": cases}),
    )
}

/// Qualify the bounded causal comparison before a report can declare completion.
pub fn qualify(results: &[CaseResult], summary: &Value) -> Result<()> {
    for (index, (first, complete, metal, panels)) in [
        (5, 6, 600, 0),
        (7, 8, 600, 0),
        (4, 5, 920, 32),
        (4, 7, 920, 32),
    ]
    .into_iter()
    .enumerate()
    {
        let value = &summary["cases"][index];
        if value["first_panel_output_period"] != [3, 5, 2, 2][index]
            || value["first_subassembly_output_period"] != first
            || value["reaches_30_subassemblies_period"] != complete
            || value["final_subassemblies"] != 30
            || value["final_packaged_meal_kg"] != 200
            || value["final_unsold_panels"] != panels
            || results[index]
                .rows
                .iter()
                .any(|row| row.metal_input_equivalent_kg != metal || row.food_kg != 200)
            || results[index].rows[15].routes.iter().any(|row| {
                !row.in_transit.is_empty()
                    || row.cumulative_delivered != row.ordered
                    || row.cumulative_lost != 0
            })
        {
            return Err(contract(format!(
                "causal qualification failed for {}",
                results[index].case
            )));
        }
    }
    let process = |case: usize, period: usize, key: &str| {
        results[case].rows[period - 1]
            .processes
            .iter()
            .find(|p| p.process == key)
            .ok_or_else(|| contract("qualification process missing"))
    };
    let arriving = process(0, 2, "panel-forming")?;
    if arriving.completed_receipt.is_some()
        || arriving.closing_input != 320
        || arriving
            .next_opening
            .as_ref()
            .map(|row| row.planned_batches)
            != Some(32)
        || process(2, 1, "panel-forming")?.completed_receipt.is_some()
        || process(1, 2, "panel-forming")?.staffing.separations != 4
        || process(3, 3, "panel-forming")?.staffing.separations != 4
        || process(3, 3, "subassembly-making")?.staffing.hires != 4
        || process(3, 5, "subassembly-making")?.staffing.separations != 4
        || process(3, 6, "subassembly-making")?.staffing.hires != 4
    {
        return Err(contract("causal timing or staffing qualification failed"));
    }
    Ok(())
}
