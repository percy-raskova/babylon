//! Consume selected fields of the supervisor's exact frozen policy, never defaults.

use super::Scope;
use crate::identity::CampaignId;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::fmt::Formatter;
use std::fmt::Result as FmtResult;
use std::fs::File;
use std::io::Read;
use std::path::{Path, PathBuf};

const POLICY_BYTES: u64 = 65_536;

/// Exact authored name of the national `SQLite` qualification contract.
pub const NATIONAL_SQLITE_CONTRACT: &str = "national_sqlite_qualification_v1";

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Refusal {
    Path,
    Read,
    Changed,
    Fields,
    Digest,
    Periods,
    Arithmetic,
    Samples,
    Horizon,
}
impl std::fmt::Display for Refusal {
    fn fmt(&self, f: &mut Formatter<'_>) -> FmtResult {
        write!(f, "frozen qualification policy refused: {self:?}")
    }
}
impl std::error::Error for Refusal {}

/// The supervisor still validates the complete policy. This typed subset rejects
/// duplicate consumed fields and supplies no defaults or admission decision.
#[derive(Deserialize)]
struct Consumed {
    version: u64,
    name: String,
    county_count: u64,
    qualification_ticks: u64,
    economic_renewal_window_ticks: u64,
    maximum_material_register_bytes: u64,
    maximum_production_evidence_body_bytes: u64,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct FrozenPolicy {
    path: PathBuf,
    sha256: [u8; 32],
    periods: u64,
    renewal_seed_tick: u64,
    material_register_bytes: usize,
    production_evidence_bytes: usize,
}
impl FrozenPolicy {
    /// # Errors
    /// Refuses changed/unbounded bytes, unsupported fields and a zero run horizon.
    pub fn open(path: &Path, sha256: [u8; 32], periods: u64) -> Result<Self, Refusal> {
        if periods == 0 {
            return Err(Refusal::Periods);
        }
        let policy: Consumed =
            serde_json::from_slice(&read(path, sha256)?).map_err(|_| Refusal::Fields)?;
        if policy.version != 6
            || policy.name != "national_storage_qualification_v6"
            || policy.county_count != 3_144
            || policy.qualification_ticks != 52
            || !(2..=52).contains(&policy.economic_renewal_window_ticks)
        {
            return Err(Refusal::Fields);
        }
        Ok(Self {
            path: path.to_owned(),
            sha256,
            periods,
            renewal_seed_tick: periods
                .saturating_sub(policy.economic_renewal_window_ticks)
                .max(1),
            material_register_bytes: limit(policy.maximum_material_register_bytes)?,
            production_evidence_bytes: limit(policy.maximum_production_evidence_body_bytes)?,
        })
    }

    /// # Errors
    /// Refuses replacement, corruption or unbounded bytes after capture.
    pub fn verify(&self) -> Result<(), Refusal> {
        read(&self.path, self.sha256).map(|_| ())
    }

    #[must_use]
    pub const fn periods(&self) -> u64 {
        self.periods
    }

    #[must_use]
    pub const fn scope(&self, campaign: CampaignId, foundation: [u8; 32]) -> Scope {
        Scope {
            campaign,
            foundation,
            policy: self.sha256,
            renewal_seed_tick: self.renewal_seed_tick,
            material_register_bytes: self.material_register_bytes,
            production_evidence_bytes: self.production_evidence_bytes,
        }
    }
}

fn limit(value: u64) -> Result<usize, Refusal> {
    if value == 0 || value > 1_000_000_000 {
        return Err(Refusal::Fields);
    }
    usize::try_from(value).map_err(|_| Refusal::Fields)
}

fn read(path: &Path, sha256: [u8; 32]) -> Result<Vec<u8>, Refusal> {
    if !path.is_absolute()
        || !path
            .symlink_metadata()
            .map_err(|_| Refusal::Path)?
            .is_file()
    {
        return Err(Refusal::Path);
    }
    let mut bytes = Vec::new();
    File::open(path)
        .map_err(|_| Refusal::Read)?
        .take(POLICY_BYTES + 1)
        .read_to_end(&mut bytes)
        .map_err(|_| Refusal::Read)?;
    if u64::try_from(bytes.len()).map_err(|_| Refusal::Changed)? > POLICY_BYTES
        || <[u8; 32]>::from(Sha256::digest(&bytes)) != sha256
    {
        return Err(Refusal::Changed);
    }
    Ok(bytes)
}

/// # Errors
/// Refuses a digest other than exactly 64 lowercase hexadecimal characters.
pub fn canonical_digest(value: &str) -> Result<[u8; 32], Refusal> {
    if value.len() != 64
        || !value
            .bytes()
            .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
    {
        return Err(Refusal::Digest);
    }
    let mut bytes = [0; 32];
    for (index, byte) in bytes.iter_mut().enumerate() {
        *byte = u8::from_str_radix(&value[index * 2..index * 2 + 2], 16)
            .map_err(|_| Refusal::Digest)?;
    }
    Ok(bytes)
}

/// One ordinary advance sample with its measured subphases.
#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct AdvanceSample {
    /// Completed period the sample measured.
    pub period: u64,
    /// Detached judgment (prepare) time.
    pub judgment_ns: u64,
    /// Candidate encoding and retained-byte accounting time.
    pub encoding_ns: u64,
    /// Durable `SQLite` commit time.
    pub commit_ns: u64,
    /// Required player briefing/query time after the commit.
    pub briefing_ns: u64,
    /// Total accepted-advance time, from judgment start through briefing.
    pub total_ns: u64,
    /// Stored rows or chunks the briefing visited.
    pub chunks_visited: u64,
}

/// One bounded player query sample.
#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct QuerySample {
    /// Query elapsed time.
    pub elapsed_ns: u64,
    /// Stored rows the scoped query visited.
    pub rows_visited: u64,
    /// Stored chunks the scoped query visited.
    pub chunks_visited: u64,
}

/// One sampled process resident-set measurement.
#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct MemorySample {
    /// Monotonic nanoseconds since the sampled process started.
    pub elapsed_ns: u64,
    /// Sampled resident-set bytes.
    pub rss_bytes: u64,
}

/// Every sampled process resident-set measurement for one ladder rung.
#[derive(Clone, Debug, Default, Eq, PartialEq, Serialize, Deserialize)]
pub struct MemorySummary {
    /// Ordered samples taken no slower than the frozen interval.
    pub samples: Vec<MemorySample>,
}

/// Positive retained growth charged by one committed period.
#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct PeriodCharge {
    /// Completed period.
    pub period: u64,
    /// New stored bytes this commit inserted, before every deletion.
    pub stored_added_bytes: u64,
    /// New decoded canonical bytes this commit inserted.
    pub decoded_added_bytes: u64,
    /// Stored bytes rotation made unreachable; reported, never subtracted.
    pub unreachable_stored_bytes: u64,
}

impl PeriodCharge {
    /// Return the charged growth: new additions alone, never additions minus deletions.
    #[must_use]
    pub const fn charged_bytes(&self) -> u64 {
        self.stored_added_bytes
    }
}

/// One measured ladder rung input to the policy evaluator.
#[derive(Clone, Debug, Default, Eq, PartialEq, Serialize, Deserialize)]
pub struct QualificationRun {
    /// Every ordinary advance in order.
    pub advances: Vec<AdvanceSample>,
    /// Cold open to actionable player view.
    pub cold_open_ns: u64,
    /// Warm scoped query samples.
    pub warm_queries: Vec<QuerySample>,
    /// First scoped queries after the cold open.
    pub cold_queries: Vec<QuerySample>,
    /// Process resident-set samples.
    pub memory: MemorySummary,
    /// Positive growth charged by each committed period.
    pub charges: Vec<PeriodCharge>,
    /// Opening snapshot size, reported separately from period growth.
    pub opening_bytes: u64,
}

/// One closed metric the policy decided.
#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Metric {
    /// Every horizon period was reported.
    SampleCount,
    /// Every ordinary advance met the ceiling.
    Advance,
    /// Cold open met the ceiling.
    ColdOpen,
    /// Warm scoped query met the ceiling.
    WarmQuery,
    /// Cold scoped query met the ceiling.
    ColdQuery,
    /// Combined running-game memory met the ceiling.
    Memory,
    /// Memory sampling stayed inside its interval.
    MemorySampling,
    /// Every period's charged positive growth met the ceiling.
    PeriodGrowth,
    /// Every thirteen-period block met its ceiling.
    CheckpointGrowth,
    /// Every fifty-two-period block met its ceiling.
    WindowGrowth,
    /// The complete qualification horizon met its ceiling.
    TotalGrowth,
    /// Scoped reads visited no chunk.
    BoundedRead,
}

/// One metric decision with the observed and frozen values.
#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct MetricVerdict {
    /// Metric decided.
    pub metric: Metric,
    /// Whether the observed value met the frozen limit.
    pub passed: bool,
    /// Largest or most relevant observed value.
    pub observed: u64,
    /// Frozen limit, or zero for an equality/no-visit contract.
    pub limit: u64,
    /// Short machine-readable evidence note.
    pub detail: String,
}

/// Advance quantiles and exact over-limit periods.
#[derive(Clone, Debug, Default, Eq, PartialEq, Serialize, Deserialize)]
pub struct AdvanceSummary {
    /// Samples evaluated.
    pub samples: u64,
    /// Median total latency.
    pub median_ns: u64,
    /// Nearest-rank ninety-fifth percentile total latency.
    pub p95_ns: u64,
    /// Largest total latency.
    pub max_ns: u64,
    /// Summed judgment time.
    pub judgment_ns_total: u64,
    /// Summed encoding time.
    pub encoding_ns_total: u64,
    /// Summed commit time.
    pub commit_ns_total: u64,
    /// Summed briefing time.
    pub briefing_ns_total: u64,
    /// Periods whose total exceeded the ceiling.
    pub over_limit_periods: Vec<u64>,
    /// Briefing chunks visited across every sample.
    pub chunks_visited: u64,
}

/// One growth boundary decision.
#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct GrowthCheckpoint {
    /// Periods included in this block.
    pub periods: u64,
    /// Charged positive growth in the block.
    pub charged_bytes: u64,
    /// Frozen block ceiling.
    pub limit_bytes: u64,
    /// Whether the block met its ceiling.
    pub passed: bool,
}

/// Positive retained growth across the measured horizon.
#[derive(Clone, Debug, Default, Eq, PartialEq, Serialize, Deserialize)]
pub struct GrowthSummary {
    /// Periods evaluated.
    pub periods: u64,
    /// Charged positive growth over the horizon.
    pub total_charged_bytes: u64,
    /// Decoded canonical additions over the horizon.
    pub total_decoded_bytes: u64,
    /// Stored bytes rotation made unreachable over the horizon.
    pub total_unreachable_bytes: u64,
    /// Period with the largest charged growth.
    pub worst_period: u64,
    /// Largest single-period charged growth.
    pub worst_period_bytes: u64,
    /// Periods whose growth exceeded the per-period ceiling.
    pub over_limit_periods: Vec<u64>,
    /// Thirteen-period block decisions.
    pub checkpoints: Vec<GrowthCheckpoint>,
    /// Fifty-two-period block decisions.
    pub windows: Vec<GrowthCheckpoint>,
}

/// Full policy verdict for one ladder rung.
#[derive(Clone, Debug, Default, Eq, PartialEq, Serialize, Deserialize)]
pub struct Verdict {
    /// Whether every metric passed.
    pub passed: bool,
    /// Ordered metric decisions.
    pub metrics: Vec<MetricVerdict>,
    /// Advance quantiles.
    pub advances: AdvanceSummary,
    /// Positive retained growth.
    pub growth: GrowthSummary,
}

/// Exact selected fields of `contracts/national_sqlite_qualification_v1.json`.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct NationalSqlitePolicy {
    path: PathBuf,
    sha256: [u8; 32],
    memory_sample_ns: u64,
    maximum_memory_bytes: u64,
    maximum_advance_ns: u64,
    maximum_cold_open_ns: u64,
    maximum_warm_query_ns: u64,
    maximum_cold_query_ns: u64,
    maximum_period_growth: u64,
    checkpoint_periods: u64,
    maximum_checkpoint_growth: u64,
    window_periods: u64,
    maximum_window_growth: u64,
    qualification_periods: u64,
    maximum_total_growth: u64,
    minimum_p95_samples: u64,
}

#[derive(Deserialize)]
struct NationalContract {
    version: u64,
    name: String,
    evidence_class: String,
    storage_charge_method: String,
    memory_charge_method: String,
    memory_sample_interval_nanoseconds: u64,
    maximum_combined_running_game_memory_bytes: u64,
    maximum_advance_nanoseconds: u64,
    maximum_cold_open_nanoseconds: u64,
    maximum_warm_query_nanoseconds: u64,
    maximum_cold_query_nanoseconds: u64,
    maximum_charged_growth_bytes_per_period: u64,
    checkpoint_periods: u64,
    maximum_charged_growth_bytes_13_periods: u64,
    window_periods: u64,
    maximum_charged_growth_bytes_52_periods: u64,
    qualification_periods: u64,
    maximum_charged_growth_bytes_325_periods: u64,
    routine_smoke_periods: u64,
    county_count: u64,
    p95_minimum_samples: u64,
}

impl NationalSqlitePolicy {
    /// Open the exact authored qualification contract and freeze its selected fields.
    ///
    /// # Errors
    /// Refuses changed bytes, an absent file, a zero or inconsistent limit, or a
    /// contract name/version/method outside this exact format.
    pub fn open(path: &Path, sha256: [u8; 32]) -> Result<Self, Refusal> {
        let contract: NationalContract =
            serde_json::from_slice(&read(path, sha256)?).map_err(|_| Refusal::Fields)?;
        if contract.version != 1
            || contract.name != NATIONAL_SQLITE_CONTRACT
            || contract.evidence_class != "Designed"
            || contract.storage_charge_method != "positive_growth_by_component_and_boundary_v1"
            || contract.memory_charge_method != "sampled_process_rss_upper_bound_v1"
            || contract.routine_smoke_periods != 2
            || contract.county_count != 3_144
            || contract.p95_minimum_samples < 2
            || contract.checkpoint_periods != 13
            || contract.window_periods != 52
            || contract.qualification_periods != 325
            || contract.memory_sample_interval_nanoseconds == 0
            || contract.maximum_combined_running_game_memory_bytes == 0
            || contract.maximum_advance_nanoseconds == 0
            || contract.maximum_cold_open_nanoseconds == 0
            || contract.maximum_warm_query_nanoseconds == 0
            || contract.maximum_cold_query_nanoseconds == 0
            || contract.maximum_charged_growth_bytes_per_period == 0
        {
            return Err(Refusal::Fields);
        }
        let per_period = contract.maximum_charged_growth_bytes_per_period;
        let scaled = |periods: u64, limit: u64| -> Result<u64, Refusal> {
            per_period
                .checked_mul(periods)
                .filter(|value| *value == limit)
                .ok_or(Refusal::Fields)
        };
        scaled(
            contract.checkpoint_periods,
            contract.maximum_charged_growth_bytes_13_periods,
        )?;
        scaled(
            contract.window_periods,
            contract.maximum_charged_growth_bytes_52_periods,
        )?;
        scaled(
            contract.qualification_periods,
            contract.maximum_charged_growth_bytes_325_periods,
        )?;
        Ok(Self {
            path: path.to_owned(),
            sha256,
            memory_sample_ns: contract.memory_sample_interval_nanoseconds,
            maximum_memory_bytes: contract.maximum_combined_running_game_memory_bytes,
            maximum_advance_ns: contract.maximum_advance_nanoseconds,
            maximum_cold_open_ns: contract.maximum_cold_open_nanoseconds,
            maximum_warm_query_ns: contract.maximum_warm_query_nanoseconds,
            maximum_cold_query_ns: contract.maximum_cold_query_nanoseconds,
            maximum_period_growth: per_period,
            checkpoint_periods: contract.checkpoint_periods,
            maximum_checkpoint_growth: contract.maximum_charged_growth_bytes_13_periods,
            window_periods: contract.window_periods,
            maximum_window_growth: contract.maximum_charged_growth_bytes_52_periods,
            qualification_periods: contract.qualification_periods,
            maximum_total_growth: contract.maximum_charged_growth_bytes_325_periods,
            minimum_p95_samples: contract.p95_minimum_samples,
        })
    }

    /// Return the exact frozen contract digest.
    #[must_use]
    pub const fn sha256(&self) -> [u8; 32] {
        self.sha256
    }

    /// Return the frozen memory sampling interval.
    #[must_use]
    pub const fn memory_sample_ns(&self) -> u64 {
        self.memory_sample_ns
    }

    /// Return the frozen ordinary-advance ceiling.
    #[must_use]
    pub const fn maximum_advance_ns(&self) -> u64 {
        self.maximum_advance_ns
    }

    /// Return the frozen minimum sample count for an empirical p95 claim.
    #[must_use]
    pub const fn minimum_p95_samples(&self) -> u64 {
        self.minimum_p95_samples
    }

    /// Return the frozen combined running-game memory ceiling.
    #[must_use]
    pub const fn maximum_memory_bytes(&self) -> u64 {
        self.maximum_memory_bytes
    }

    /// Return the frozen cold-open ceiling.
    #[must_use]
    pub const fn maximum_cold_open_ns(&self) -> u64 {
        self.maximum_cold_open_ns
    }

    /// Return the frozen warm scoped-query ceiling.
    #[must_use]
    pub const fn maximum_warm_query_ns(&self) -> u64 {
        self.maximum_warm_query_ns
    }

    /// Return the frozen cold scoped-query ceiling.
    #[must_use]
    pub const fn maximum_cold_query_ns(&self) -> u64 {
        self.maximum_cold_query_ns
    }

    /// Return the frozen per-period charged growth ceiling.
    #[must_use]
    pub const fn maximum_period_growth(&self) -> u64 {
        self.maximum_period_growth
    }

    /// Return the frozen thirteen-period block size.
    #[must_use]
    pub const fn checkpoint_periods(&self) -> u64 {
        self.checkpoint_periods
    }

    /// Return the frozen thirteen-period charged growth ceiling.
    #[must_use]
    pub const fn maximum_checkpoint_growth(&self) -> u64 {
        self.maximum_checkpoint_growth
    }

    /// Return the frozen fifty-two-period block size.
    #[must_use]
    pub const fn window_periods(&self) -> u64 {
        self.window_periods
    }

    /// Return the frozen fifty-two-period charged growth ceiling.
    #[must_use]
    pub const fn maximum_window_growth(&self) -> u64 {
        self.maximum_window_growth
    }

    /// Return the frozen complete qualification horizon.
    #[must_use]
    pub const fn qualification_periods(&self) -> u64 {
        self.qualification_periods
    }

    /// Return the frozen complete-horizon charged growth ceiling.
    #[must_use]
    pub const fn maximum_total_growth(&self) -> u64 {
        self.maximum_total_growth
    }

    /// Evaluate one measured rung against every frozen metric.
    ///
    /// # Errors
    /// Refuses a zero horizon, missing/extra samples, non-contiguous periods or
    /// arithmetic overflow. It does not refuse a measured target failure; that is
    /// a verdict, not an evaluator error.
    #[allow(
        clippy::too_many_lines,
        reason = "`evaluate` keeps one ordered metric decision table beside its frozen limits"
    )]
    pub fn evaluate(&self, run: &QualificationRun, horizon: u64) -> Result<Verdict, Refusal> {
        if horizon == 0 || horizon > self.qualification_periods {
            return Err(Refusal::Horizon);
        }
        let sample_count = u64::try_from(run.advances.len()).map_err(|_| Refusal::Samples)?;
        let charge_count = u64::try_from(run.charges.len()).map_err(|_| Refusal::Samples)?;
        if sample_count != horizon || charge_count != horizon {
            return Err(Refusal::Samples);
        }
        verify_periods(&run.advances, |sample| sample.period, horizon)?;
        verify_periods(&run.charges, |charge| charge.period, horizon)?;

        let advances = summarize_advances(&run.advances, self.maximum_advance_ns)?;
        let growth = self.summarize_growth(run, horizon)?;
        let memory_peak = run
            .memory
            .samples
            .iter()
            .map(|sample| sample.rss_bytes)
            .max()
            .unwrap_or(0);
        let memory_gap = maximum_gap(&run.memory.samples)?;
        let warm = query_summary(&run.warm_queries)?;
        let cold = query_summary(&run.cold_queries)?;
        let chunks_visited = advances
            .chunks_visited
            .checked_add(warm.chunks_visited)
            .and_then(|value| value.checked_add(cold.chunks_visited))
            .ok_or(Refusal::Arithmetic)?;

        let mut metrics = Vec::with_capacity(12);
        metrics.push(metric(
            Metric::SampleCount,
            sample_count == horizon && charge_count == horizon,
            sample_count,
            horizon,
            "advance and charge records equal the requested horizon",
        ));
        let advance_over = !advances.over_limit_periods.is_empty();
        metrics.push(metric(
            Metric::Advance,
            !advance_over,
            advances.max_ns,
            self.maximum_advance_ns,
            &quantile_detail(&advances, advances.over_limit_periods.len()),
        ));
        metrics.push(metric(
            Metric::ColdOpen,
            run.cold_open_ns > 0 && run.cold_open_ns <= self.maximum_cold_open_ns,
            run.cold_open_ns,
            self.maximum_cold_open_ns,
            "cold open to scoped player view",
        ));
        metrics.push(metric(
            Metric::WarmQuery,
            !run.warm_queries.is_empty() && warm.max_ns <= self.maximum_warm_query_ns,
            warm.max_ns,
            self.maximum_warm_query_ns,
            &format!(
                "samples={} median_ns={} p95_ns={}",
                warm.samples, warm.median_ns, warm.p95_ns
            ),
        ));
        metrics.push(metric(
            Metric::ColdQuery,
            !run.cold_queries.is_empty() && cold.max_ns <= self.maximum_cold_query_ns,
            cold.max_ns,
            self.maximum_cold_query_ns,
            &format!("samples={} max_ns={}", cold.samples, cold.max_ns),
        ));
        metrics.push(metric(
            Metric::Memory,
            !run.memory.samples.is_empty() && memory_peak <= self.maximum_memory_bytes,
            memory_peak,
            self.maximum_memory_bytes,
            &format!("samples={}", run.memory.samples.len()),
        ));
        metrics.push(metric(
            Metric::MemorySampling,
            !run.memory.samples.is_empty() && memory_gap <= self.memory_sample_ns,
            memory_gap,
            self.memory_sample_ns,
            "maximum sampled interval",
        ));
        metrics.push(metric(
            Metric::PeriodGrowth,
            growth.over_limit_periods.is_empty(),
            growth.worst_period_bytes,
            self.maximum_period_growth,
            &format!(
                "worst_period={} over_period_periods={}",
                growth.worst_period,
                growth.over_limit_periods.len()
            ),
        ));
        let checkpoint_failed = growth
            .checkpoints
            .iter()
            .any(|checkpoint| !checkpoint.passed);
        let checkpoint_max = growth
            .checkpoints
            .iter()
            .map(|checkpoint| checkpoint.charged_bytes)
            .max()
            .unwrap_or(0);
        metrics.push(metric(
            Metric::CheckpointGrowth,
            !checkpoint_failed,
            checkpoint_max,
            self.maximum_checkpoint_growth,
            &format!("blocks={}", growth.checkpoints.len()),
        ));
        let window_failed = growth.windows.iter().any(|window| !window.passed);
        let window_max = growth
            .windows
            .iter()
            .map(|window| window.charged_bytes)
            .max()
            .unwrap_or(0);
        metrics.push(metric(
            Metric::WindowGrowth,
            !window_failed,
            window_max,
            self.maximum_window_growth,
            &format!("blocks={}", growth.windows.len()),
        ));
        if horizon == self.qualification_periods {
            metrics.push(metric(
                Metric::TotalGrowth,
                growth.total_charged_bytes <= self.maximum_total_growth,
                growth.total_charged_bytes,
                self.maximum_total_growth,
                "complete qualification horizon",
            ));
        }
        metrics.push(metric(
            Metric::BoundedRead,
            chunks_visited == 0,
            chunks_visited,
            0,
            "scoped reads and briefings visit no state chunk",
        ));
        let passed = metrics.iter().all(|decision| decision.passed);
        Ok(Verdict {
            passed,
            metrics,
            advances,
            growth,
        })
    }

    fn summarize_growth(
        &self,
        run: &QualificationRun,
        horizon: u64,
    ) -> Result<GrowthSummary, Refusal> {
        let mut total_charged = 0_u64;
        let mut total_decoded = 0_u64;
        let mut total_unreachable = 0_u64;
        let mut worst_period = 0_u64;
        let mut worst_bytes = 0_u64;
        let mut over_limit = Vec::new();
        for charge in &run.charges {
            total_charged = total_charged
                .checked_add(charge.charged_bytes())
                .ok_or(Refusal::Arithmetic)?;
            total_decoded = total_decoded
                .checked_add(charge.decoded_added_bytes)
                .ok_or(Refusal::Arithmetic)?;
            total_unreachable = total_unreachable
                .checked_add(charge.unreachable_stored_bytes)
                .ok_or(Refusal::Arithmetic)?;
            if charge.charged_bytes() > worst_bytes {
                worst_bytes = charge.charged_bytes();
                worst_period = charge.period;
            }
            if charge.charged_bytes() > self.maximum_period_growth {
                over_limit.push(charge.period);
            }
        }
        let checkpoints = Self::blocks(
            &run.charges,
            self.checkpoint_periods,
            self.maximum_checkpoint_growth,
        )?;
        let windows = Self::blocks(
            &run.charges,
            self.window_periods,
            self.maximum_window_growth,
        )?;
        Ok(GrowthSummary {
            periods: horizon,
            total_charged_bytes: total_charged,
            total_decoded_bytes: total_decoded,
            total_unreachable_bytes: total_unreachable,
            worst_period,
            worst_period_bytes: worst_bytes,
            over_limit_periods: over_limit,
            checkpoints,
            windows,
        })
    }

    fn blocks(
        charges: &[PeriodCharge],
        periods: u64,
        limit: u64,
    ) -> Result<Vec<GrowthCheckpoint>, Refusal> {
        let window_len = usize::try_from(periods).map_err(|_| Refusal::Arithmetic)?;
        let mut decisions = Vec::new();
        for chunk in charges.chunks_exact(window_len) {
            let block_total = chunk.iter().try_fold(0_u64, |total, charge| {
                total
                    .checked_add(charge.charged_bytes())
                    .ok_or(Refusal::Arithmetic)
            })?;
            decisions.push(GrowthCheckpoint {
                periods,
                charged_bytes: block_total,
                limit_bytes: limit,
                passed: block_total <= limit,
            });
        }
        Ok(decisions)
    }
}

struct Queries {
    samples: usize,
    median_ns: u64,
    p95_ns: u64,
    max_ns: u64,
    chunks_visited: u64,
}

fn query_summary(samples: &[QuerySample]) -> Result<Queries, Refusal> {
    let mut times = Vec::with_capacity(samples.len());
    let mut chunks = 0_u64;
    for sample in samples {
        times.push(sample.elapsed_ns);
        chunks = chunks
            .checked_add(sample.chunks_visited)
            .ok_or(Refusal::Arithmetic)?;
    }
    times.sort_unstable();
    if times.is_empty() {
        return Ok(Queries {
            samples: 0,
            median_ns: 0,
            p95_ns: 0,
            max_ns: 0,
            chunks_visited: chunks,
        });
    }
    Ok(Queries {
        samples: times.len(),
        median_ns: percentile(&times, 1, 2)?,
        p95_ns: percentile(&times, 95, 100)?,
        max_ns: times.last().copied().unwrap_or(0),
        chunks_visited: chunks,
    })
}

fn summarize_advances(samples: &[AdvanceSample], limit: u64) -> Result<AdvanceSummary, Refusal> {
    let mut totals = Vec::with_capacity(samples.len());
    let mut judgment = 0_u64;
    let mut encoding = 0_u64;
    let mut commit = 0_u64;
    let mut briefing = 0_u64;
    let mut chunks = 0_u64;
    let mut over_limit = Vec::new();
    for sample in samples {
        if sample.total_ns
            < sample
                .judgment_ns
                .checked_add(sample.encoding_ns)
                .and_then(|value| value.checked_add(sample.commit_ns))
                .and_then(|value| value.checked_add(sample.briefing_ns))
                .ok_or(Refusal::Arithmetic)?
        {
            return Err(Refusal::Arithmetic);
        }
        totals.push(sample.total_ns);
        judgment = judgment
            .checked_add(sample.judgment_ns)
            .ok_or(Refusal::Arithmetic)?;
        encoding = encoding
            .checked_add(sample.encoding_ns)
            .ok_or(Refusal::Arithmetic)?;
        commit = commit
            .checked_add(sample.commit_ns)
            .ok_or(Refusal::Arithmetic)?;
        briefing = briefing
            .checked_add(sample.briefing_ns)
            .ok_or(Refusal::Arithmetic)?;
        chunks = chunks
            .checked_add(sample.chunks_visited)
            .ok_or(Refusal::Arithmetic)?;
        if sample.total_ns > limit {
            over_limit.push(sample.period);
        }
    }
    totals.sort_unstable();
    Ok(AdvanceSummary {
        samples: u64::try_from(totals.len()).map_err(|_| Refusal::Arithmetic)?,
        median_ns: percentile(&totals, 1, 2)?,
        p95_ns: percentile(&totals, 95, 100)?,
        max_ns: totals.last().copied().unwrap_or(0),
        judgment_ns_total: judgment,
        encoding_ns_total: encoding,
        commit_ns_total: commit,
        briefing_ns_total: briefing,
        over_limit_periods: over_limit,
        chunks_visited: chunks,
    })
}

fn percentile(sorted: &[u64], numerator: u64, denominator: u64) -> Result<u64, Refusal> {
    if sorted.is_empty() || denominator == 0 || numerator > denominator {
        return Err(Refusal::Samples);
    }
    let count = u64::try_from(sorted.len()).map_err(|_| Refusal::Arithmetic)?;
    let scaled = count
        .checked_mul(numerator)
        .ok_or(Refusal::Arithmetic)?
        .checked_add(denominator - 1)
        .ok_or(Refusal::Arithmetic)?;
    let rank = scaled / denominator;
    let index = usize::try_from(rank.saturating_sub(1)).map_err(|_| Refusal::Arithmetic)?;
    sorted.get(index).copied().ok_or(Refusal::Samples)
}

fn maximum_gap(samples: &[MemorySample]) -> Result<u64, Refusal> {
    let mut gap = 0_u64;
    let mut previous = None;
    for sample in samples {
        if let Some(prior) = previous {
            let delta = sample
                .elapsed_ns
                .checked_sub(prior)
                .ok_or(Refusal::Samples)?;
            gap = gap.max(delta);
        }
        previous = Some(sample.elapsed_ns);
    }
    Ok(gap)
}

fn verify_periods<T>(items: &[T], period: impl Fn(&T) -> u64, horizon: u64) -> Result<(), Refusal> {
    for (index, item) in items.iter().enumerate() {
        let expected = u64::try_from(index).map_err(|_| Refusal::Arithmetic)? + 1;
        if period(item) != expected || expected > horizon {
            return Err(Refusal::Samples);
        }
    }
    Ok(())
}

fn metric(metric: Metric, passed: bool, observed: u64, limit: u64, detail: &str) -> MetricVerdict {
    MetricVerdict {
        metric,
        passed,
        observed,
        limit,
        detail: detail.to_owned(),
    }
}

fn quantile_detail(summary: &AdvanceSummary, over_periods: usize) -> String {
    format!(
        "samples={} median_ns={} p95_ns={} max_ns={} over_periods={over_periods}",
        summary.samples, summary.median_ns, summary.p95_ns, summary.max_ns
    )
}

#[cfg(test)]
mod tests {
    use super::*;
    use sha2::{Digest, Sha256};
    use std::fs;
    use std::path::PathBuf;
    use uuid::Uuid;

    struct Fixture(PathBuf);
    impl Fixture {
        fn new() -> Self {
            use std::sync::atomic::{AtomicU64, Ordering};
            static NEXT: AtomicU64 = AtomicU64::new(0);
            let path = std::env::temp_dir().join(format!(
                "babylon-audit-policy-{}.json",
                format_args!(
                    "{}-{}",
                    std::process::id(),
                    NEXT.fetch_add(1, Ordering::Relaxed)
                )
            ));
            fs::write(
                &path,
                include_bytes!("../../../../../contracts/national_storage_qualification_v6.json"),
            )
            .expect("the fixture sink accepts the authored bytes");
            Self(path)
        }
        fn digest(&self) -> [u8; 32] {
            Sha256::digest(
                fs::read(&self.0).expect("the fixture reader returns its authored facts"),
            )
            .into()
        }
    }
    impl Drop for Fixture {
        fn drop(&mut self) {
            fs::remove_file(&self.0).expect("the fixture file exists before removal");
        }
    }

    #[test]
    fn frozen_fields_and_renewal_seed_are_shared_without_defaults() {
        let file = Fixture::new();
        let policy = FrozenPolicy::open(&file.0, file.digest(), 52)
            .expect("the fixture opens the authored source");
        let scope = policy.scope(
            crate::identity::CampaignId::from_uuid(Uuid::from_u128(1)),
            [7; 32],
        );
        assert_eq!(scope.renewal_seed_tick, 39);
        assert_eq!(scope.material_register_bytes, 1_000_000_000);
        assert_eq!(scope.production_evidence_bytes, 1_000_000_000);
        assert_eq!(scope.policy, file.digest());
        assert!(policy.verify().is_ok());
        fs::write(&file.0, b"{}").expect("the fixture sink accepts the authored bytes");
        assert_eq!(policy.verify(), Err(Refusal::Changed));
    }

    #[test]
    fn unsupported_missing_and_duplicated_consumed_fields_refuse() {
        let file = Fixture::new();
        for replacement in [
            b"{}".as_slice(),
            b"{\"version\":5}",
            b"{\"version\":6,\"version\":6}",
        ] {
            fs::write(&file.0, replacement).expect("the fixture sink accepts the authored bytes");
            assert!(FrozenPolicy::open(&file.0, file.digest(), 2).is_err());
        }
        assert!(canonical_digest(&"A".repeat(64)).is_err());
        assert!(canonical_digest(&"a".repeat(63)).is_err());
        assert_eq!(
            canonical_digest(&"ab".repeat(32))
                .expect("the fixture call `canonical_digest` succeeds for the authored inputs"),
            [0xab; 32]
        );
    }
}
