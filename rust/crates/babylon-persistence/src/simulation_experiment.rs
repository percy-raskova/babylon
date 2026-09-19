//! Closed diagnostic inputs captured by the authoritative material foundation.
//!
//! Observations initialize named historical profiles; held-out observations never
//! enter this module. All trajectories use the ordinary material replay session.
mod freight;
pub(crate) mod regional;
pub mod report;
pub mod setup;
#[cfg(test)]
mod tests;

use crate::material_runtime::MaterialRuntimeFoundation;
use babylon_kernel::content_digest::sha256_of;
use serde::{Deserialize, Serialize};

pub const MAX_EXPERIMENT_INPUT_BYTES: usize = 65_536;
pub const MAX_EXPERIMENT_HORIZON: u64 = 131;

#[derive(Clone, Copy, Debug, PartialEq, Eq, Deserialize, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum ExperimentProfile {
    DeliveryStock,
    Sustained,
    Depletion,
    HistoricalEmployment,
    HistoricalFreight,
}
impl ExperimentProfile {
    #[must_use]
    pub const fn id(self) -> &'static str {
        match self {
            Self::DeliveryStock => "delivery_stock",
            Self::Sustained => "sustained",
            Self::Depletion => "depletion",
            Self::HistoricalEmployment => "historical_employment",
            Self::HistoricalFreight => "historical_freight",
        }
    }
    #[must_use]
    pub const fn foundation_id(self) -> &'static str {
        match self {
            Self::DeliveryStock => "experiment-delivery-stock-v1",
            Self::Sustained => "experiment-sustained-v1",
            Self::Depletion => "experiment-depletion-v1",
            Self::HistoricalEmployment => "experiment-historical-employment-v1",
            Self::HistoricalFreight => "experiment-historical-freight-v1",
        }
    }
    pub(crate) fn from_foundation_id(id: &str) -> Option<Self> {
        [
            Self::DeliveryStock,
            Self::Sustained,
            Self::Depletion,
            Self::HistoricalEmployment,
            Self::HistoricalFreight,
        ]
        .into_iter()
        .find(|p| p.foundation_id() == id)
    }
    #[must_use]
    pub const fn horizon(self) -> u64 {
        match self {
            Self::DeliveryStock => 16,
            Self::Sustained | Self::Depletion => 130,
            Self::HistoricalEmployment => 131,
            Self::HistoricalFreight => 78,
        }
    }
}
#[derive(Clone, Debug, PartialEq, Eq, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct EmploymentStartingRow {
    pub series_id: String,
    pub jobs: u64,
}
#[derive(Clone, Debug, PartialEq, Eq, Deserialize, Serialize)]
#[serde(tag = "kind", rename_all = "snake_case", deny_unknown_fields)]
pub enum StartingSnapshot {
    Employment {
        date: String,
        series: Vec<EmploymentStartingRow>,
    },
    Freight {
        date: String,
        series_id: String,
        arrived_kg: u64,
    },
}
/// Bounded Designed interventions. Each modifies a declared input, never outcomes.
#[derive(Clone, Debug, PartialEq, Eq, Deserialize, Serialize)]
#[serde(tag = "kind", rename_all = "snake_case", deny_unknown_fields)]
pub enum ExperimentIntervention {
    RegionalDelivery { delivery: ExperimentDelivery },
    TransportCapacityPermille { permille: u16 },
    OpeningSheetStock { kilograms: u64 },
}
#[derive(Clone, Copy, Debug, PartialEq, Eq, Deserialize, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum ExperimentDelivery {
    Standard,
    Delayed,
}
#[derive(Clone, Debug, PartialEq, Eq, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct SimulationExperimentV1 {
    pub schema: String,
    pub profile: ExperimentProfile,
    pub epoch: Option<String>,
    pub horizon: u64,
    pub seed: i64,
    pub source_snapshot_sha256: Option<String>,
    pub starting_snapshot: Option<StartingSnapshot>,
    pub interventions: Vec<ExperimentIntervention>,
}
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum ExperimentError {
    Input,
    Profile,
    Horizon,
    Epoch,
    Source,
    StartingSnapshot,
    Intervention,
    Arithmetic,
    Content,
    Foundation,
    Observation,
    Conservation,
    Incomplete,
}
impl std::fmt::Display for ExperimentError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "simulation experiment refused: {self:?}")
    }
}
impl std::error::Error for ExperimentError {}
pub(crate) type Result<T> = std::result::Result<T, ExperimentError>;
pub(crate) fn product(a: u64, b: u64) -> Result<u64> {
    a.checked_mul(b).ok_or(ExperimentError::Arithmetic)
}
pub(crate) fn sum(a: u64, b: u64) -> Result<u64> {
    a.checked_add(b).ok_or(ExperimentError::Arithmetic)
}
pub(crate) fn digest_valid(s: &str) -> bool {
    s.len() == 64
        && s.bytes()
            .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
        && s.bytes().any(|b| b != b'0')
}
pub(crate) fn hex(bytes: &[u8]) -> String {
    crate::michigan_economy::digest_hex(bytes)
}

impl SimulationExperimentV1 {
    /// Decode closed, bounded inputs and reject unsupported profile combinations.
    /// # Errors
    /// Refuses unknown fields, noninteger values, invalid source identities and domains.
    pub fn parse(bytes: &[u8]) -> Result<Self> {
        if bytes.len() > MAX_EXPERIMENT_INPUT_BYTES {
            return Err(ExperimentError::Input);
        }
        let mut value: Self = serde_json::from_slice(bytes).map_err(|_| ExperimentError::Input)?;
        if let Some(StartingSnapshot::Employment { series, .. }) = &mut value.starting_snapshot {
            series.sort_by(|a, b| a.series_id.cmp(&b.series_id));
        }
        value.interventions.sort_by_key(|i| match i {
            ExperimentIntervention::RegionalDelivery { .. } => 0,
            ExperimentIntervention::TransportCapacityPermille { .. } => 1,
            ExperimentIntervention::OpeningSheetStock { .. } => 2,
        });
        value.validate()?;
        Ok(value)
    }
    /// # Errors
    /// Refuses changed schema, unsupported dates/horizons, or inadmissible interventions.
    pub fn validate(&self) -> Result<()> {
        if self.schema != "SimulationExperimentV1" {
            return Err(ExperimentError::Input);
        }
        if self.horizon != self.profile.horizon() {
            return Err(ExperimentError::Horizon);
        }
        match self.profile {
            ExperimentProfile::DeliveryStock
            | ExperimentProfile::Sustained
            | ExperimentProfile::Depletion => {
                if self.epoch.is_some()
                    || self.source_snapshot_sha256.is_some()
                    || self.starting_snapshot.is_some()
                {
                    return Err(ExperimentError::Source);
                }
            }
            ExperimentProfile::HistoricalEmployment => {
                if self.epoch.as_deref() != Some("2010-01-01") {
                    return Err(ExperimentError::Epoch);
                }
                let Some(StartingSnapshot::Employment { date, series }) = &self.starting_snapshot
                else {
                    return Err(ExperimentError::StartingSnapshot);
                };
                let mut keys = series
                    .iter()
                    .map(|r| r.series_id.as_str())
                    .collect::<Vec<_>>();
                keys.sort_unstable();
                if date != "2010-01-01"
                    || keys
                        != [
                            "26099/332",
                            "26125/311",
                            "26161/311",
                            "26163/331",
                            "26163/3363",
                        ]
                    || series.iter().any(|r| r.jobs == 0 || r.jobs > 1_000_000)
                {
                    return Err(ExperimentError::StartingSnapshot);
                }
            }
            ExperimentProfile::HistoricalFreight => {
                if self.epoch.as_deref() != Some("2019-02-01") {
                    return Err(ExperimentError::Epoch);
                }
                let Some(StartingSnapshot::Freight {
                    date,
                    series_id,
                    arrived_kg,
                }) = &self.starting_snapshot
                else {
                    return Err(ExperimentError::StartingSnapshot);
                };
                if date != "2019-01-01"
                    || series_id != "detroit_canada_truck_import_hs72"
                    || *arrived_kg == 0
                    || *arrived_kg > 1_000_000_000_000
                {
                    return Err(ExperimentError::StartingSnapshot);
                }
            }
        }
        if matches!(
            self.profile,
            ExperimentProfile::HistoricalEmployment | ExperimentProfile::HistoricalFreight
        ) && !self
            .source_snapshot_sha256
            .as_deref()
            .is_some_and(digest_valid)
        {
            return Err(ExperimentError::Source);
        }
        self.validate_interventions()
    }
    fn validate_interventions(&self) -> Result<()> {
        let mut transport = false;
        let mut stock = false;
        let mut delivery = false;
        for i in &self.interventions {
            match i {
                ExperimentIntervention::RegionalDelivery { .. } => {
                    if delivery || self.profile != ExperimentProfile::DeliveryStock {
                        return Err(ExperimentError::Intervention);
                    }
                    delivery = true;
                }
                ExperimentIntervention::TransportCapacityPermille { permille } => {
                    if transport
                        || !(250..=2000).contains(permille)
                        || self.profile == ExperimentProfile::Depletion
                    {
                        return Err(ExperimentError::Intervention);
                    }
                    transport = true;
                }
                ExperimentIntervention::OpeningSheetStock { kilograms } => {
                    if stock
                        || *kilograms > 1_000_000
                        || !matches!(
                            self.profile,
                            ExperimentProfile::Sustained | ExperimentProfile::DeliveryStock
                        )
                    {
                        return Err(ExperimentError::Intervention);
                    }
                    stock = true;
                }
            }
        }
        Ok(())
    }
    /// Canonical JSON used inside the foundation, independent of input whitespace.
    /// # Errors
    /// Refuses invalid experiment values.
    pub fn canonical_bytes(&self) -> Result<Vec<u8>> {
        self.validate()?;
        serde_json::to_vec(self).map_err(|_| ExperimentError::Input)
    }
    /// # Errors
    /// Refuses invalid experiment values.
    pub fn sha256(&self) -> Result<[u8; 32]> {
        Ok(sha256_of(&self.canonical_bytes()?))
    }
    /// Construct the ordinary authoritative material foundation from captured inputs.
    /// # Errors
    /// Refuses invalid content, arithmetic overflow and material/graph composition failures.
    pub fn create_foundation(&self) -> Result<MaterialRuntimeFoundation> {
        self.validate()?;
        if self.profile == ExperimentProfile::HistoricalFreight {
            return freight::foundation(self);
        }
        let catalog = regional::catalog(self)?;
        crate::sector_bundle::foundation::create_bundle_foundation(
            self.profile.foundation_id(),
            crate::michigan_material::MichiganDeliveryPreset::Standard,
            &catalog,
        )
        .map_err(|_| ExperimentError::Foundation)
    }
    /// Resolved regional rows for evidence readers. No second transition authority.
    /// # Errors
    /// Refuses the foreign freight profile and invalid captured inputs.
    pub fn regional_catalog(&self) -> Result<crate::michigan_material::MichiganMaterialCatalog> {
        regional::catalog(self)
    }
    pub(crate) fn transport_permille(&self) -> u64 {
        self.interventions
            .iter()
            .find_map(|i| match i {
                ExperimentIntervention::TransportCapacityPermille { permille } => {
                    Some(u64::from(*permille))
                }
                _ => None,
            })
            .unwrap_or(1000)
    }
}
pub(crate) fn validate_freight_authority(
    graph: &crate::CampaignFoundation,
    register: &babylon_tick::material_world::MaterialWorldRegister,
    spec: &crate::material_runtime::MaterialFoundationSpec,
) -> Result<babylon_tick::material_staffing::StaffingComposition> {
    freight::validate_authority(graph, register, spec)
}
