use babylon_kernel::currency::Currency;
use babylon_kernel::economic_identity::{EconomicFunction, TradeSet};
use babylon_kernel::geography::CountyGeoid;
use std::collections::BTreeMap;
use std::fmt::{Formatter, Result as FmtResult};

use crate::national_cohorts::CohortKey;

/// Hours in a working year (the project's `HOURS_PER_YEAR`).
const HOURS_PER_YEAR: u128 = 2_080;
const MICRO: u128 = 1_000_000;

/// Whether a row's jobs and payroll were published, placed under a parent, or only partly known.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum JobsRule {
    /// Every member of the group published.
    Published,
    /// Withheld members were given a share of their parent's remainder.
    Placed,
    /// Some members stay unplaced and are left out of the totals.
    Partial,
}

/// Where a row's wage pair came from.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum WageRule {
    /// The county's own jobs and payroll.
    County,
    /// The state's published rows of the same trade and ownership.
    State,
    /// The nation's rows of the same trade and ownership.
    Nation,
    /// The nation's rows of the trade over all ownerships.
    NationAllOwnerships,
}

/// One admitted cohort group's jobs, payroll and wage pair.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct TradePayRow {
    /// The group; `function` is always `Some`.
    pub key: CohortKey,
    /// The group's jobs, published plus placed.
    pub jobs: u64,
    /// The group's annual payroll in USD, published plus placed.
    pub payroll_usd: u64,
    /// How `jobs` and `payroll_usd` were reached.
    pub jobs_rule: JobsRule,
    /// Where the wage pair came from.
    pub wage_rule: WageRule,
    /// Jobs of the wage pair.
    pub wage_jobs: u64,
    /// Annual payroll in USD of the wage pair.
    pub wage_payroll_usd: u64,
}

/// `floor(payroll x 1_000_000 / (jobs x 2_080))`, or `None` for no jobs or an overflow.
fn hourly(payroll_usd: u128, jobs: u128) -> Option<u128> {
    let denominator = jobs.checked_mul(HOURS_PER_YEAR)?;
    payroll_usd.checked_mul(MICRO)?.checked_div(denominator)
}

fn currency(micro: u128) -> Option<Currency> {
    i128::try_from(micro).ok().map(Currency::from_micro_units)
}

impl TradePayRow {
    /// `floor(wage_payroll_usd x 1_000_000 / (wage_jobs x 2_080))`, in millionths per hour.
    ///
    /// # Errors
    /// `Wage` for a pair with no jobs, no payroll, or a wage that rounds to zero.
    pub fn hourly_wage(&self) -> Result<Currency, NationalTradePayError> {
        if self.wage_jobs == 0 || self.wage_payroll_usd == 0 {
            return Err(NationalTradePayError::Wage);
        }
        hourly(
            u128::from(self.wage_payroll_usd),
            u128::from(self.wage_jobs),
        )
        .filter(|micro| *micro > 0)
        .and_then(currency)
        .ok_or(NationalTradePayError::Wage)
    }
}

/// Specific refusals; no repair, zero fill or partial capture fallback.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum NationalTradePayError {
    /// Compressed bytes, decoded bytes or rows exceed the bound.
    Bound,
    /// Compact bytes differ from the qualified table.
    ArtifactDigest,
    /// Gzip or UTF-8 is invalid, or compressed bytes trail.
    Compression,
    /// The exact header or canonical line shape differs.
    Header,
    /// A record's field count differs.
    CsvShape,
    /// A function key is unknown or outside the twelve trades.
    Function,
    /// An ownership code is unknown or an aggregate control.
    Ownership,
    /// The county identity is not exactly five ASCII digits.
    CountyIdentity,
    /// A county lies outside the domestic roster.
    UnknownCounty,
    /// An integer is noncanonical, negative or beyond the signed-64-bit bound.
    NumericValue,
    /// A rule word is unknown, or a county wage contradicts its row.
    Rule,
    /// A wage pair has no jobs or no payroll, or its hourly wage is zero.
    Wage,
    /// Rows are duplicated or not in strict `CohortKey` order.
    Order,
    /// Row count or keys differ from the admitted groups of the twelve-trade cohort table.
    Coverage,
}

impl std::fmt::Display for NationalTradePayError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FmtResult {
        write!(f, "national trade pay refused: {self:?}")
    }
}

impl std::error::Error for NationalTradePayError {}

/// Payroll and jobs summed over some rows.
#[derive(Clone, Copy, Default)]
struct Sum {
    payroll_usd: u128,
    jobs: u128,
}

impl Sum {
    fn add(&mut self, row: &TradePayRow) {
        self.payroll_usd += u128::from(row.payroll_usd);
        self.jobs += u128::from(row.jobs);
    }
    /// The figure, or `None` for a sum that holds no jobs.
    fn wage(self) -> Option<Currency> {
        if self.jobs == 0 {
            return None;
        }
        hourly(self.payroll_usd, self.jobs).and_then(currency)
    }
}

/// Every admitted group's pay, sorted by key, with the averages computed once.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct NationalTradePayReference {
    rows: Box<[TradePayRow]>,
    counties: BTreeMap<CountyGeoid, Currency>,
    states: BTreeMap<[u8; 2], Currency>,
    nation: Currency,
    trades: BTreeMap<EconomicFunction, Currency>,
    sha256: [u8; 32],
}

impl NationalTradePayReference {
    /// Build the averages over rows already checked and sorted.
    pub(super) fn from_rows(rows: Vec<TradePayRow>, sha256: [u8; 32]) -> Self {
        let mut by_county: BTreeMap<CountyGeoid, Sum> = BTreeMap::new();
        let mut by_state: BTreeMap<[u8; 2], Sum> = BTreeMap::new();
        let mut by_trade: BTreeMap<EconomicFunction, Sum> = BTreeMap::new();
        let mut all = Sum::default();
        for row in &rows {
            by_county.entry(row.key.county).or_default().add(row);
            by_state
                .entry(row.key.county.state_fips())
                .or_default()
                .add(row);
            if let Some(function) = row.key.function {
                by_trade.entry(function).or_default().add(row);
            }
            all.add(row);
        }
        let nation = all.wage().unwrap_or_else(|| Currency::from_micro_units(0));
        Self {
            counties: by_county
                .into_iter()
                .filter_map(|(key, sum)| sum.wage().map(|wage| (key, wage)))
                .collect(),
            states: by_state
                .into_iter()
                .filter_map(|(key, sum)| sum.wage().map(|wage| (key, wage)))
                .collect(),
            trades: by_trade
                .into_iter()
                .filter_map(|(key, sum)| sum.wage().map(|wage| (key, wage)))
                .collect(),
            nation,
            rows: rows.into_boxed_slice(),
            sha256,
        }
    }

    /// Every row, sorted by key.
    #[must_use]
    pub fn rows(&self) -> &[TradePayRow] {
        &self.rows
    }

    /// Exact row lookup.
    #[must_use]
    pub fn row(&self, key: CohortKey) -> Option<&TradePayRow> {
        self.rows
            .binary_search_by_key(&key, |row| row.key)
            .ok()
            .map(|index| &self.rows[index])
    }

    /// A county's own rows, in key order; empty for a county with no cohort group.
    #[must_use]
    pub fn county_rows(&self, county: CountyGeoid) -> &[TradePayRow] {
        let start = self.rows.partition_point(|row| row.key.county < county);
        let end = self.rows.partition_point(|row| row.key.county <= county);
        &self.rows[start..end]
    }

    /// All of a county's rows, all trades and ownerships:
    /// `sum(payroll_usd) x 1_000_000 / (sum(jobs) x 2_080)`. A county whose rows hold no jobs takes
    /// its state's figure over all its counties, then the nation's.
    #[must_use]
    pub fn county_average(&self, county: CountyGeoid) -> Currency {
        self.counties
            .get(&county)
            .or_else(|| self.states.get(&county.state_fips()))
            .copied()
            .unwrap_or(self.nation)
    }

    /// The same sum over every row of the trade, all counties and ownerships. A trade with no
    /// jobs anywhere takes the nation's figure over all rows.
    #[must_use]
    pub fn national_wage(&self, function: EconomicFunction) -> Currency {
        self.trades.get(&function).copied().unwrap_or(self.nation)
    }

    /// SHA-256 of the exact compact gzip bytes captured here.
    #[must_use]
    pub const fn artifact_sha256(&self) -> [u8; 32] {
        self.sha256
    }

    /// The trades the rows are checked against.
    #[must_use]
    pub const fn trades(&self) -> TradeSet {
        TradeSet::Twelve
    }
}
