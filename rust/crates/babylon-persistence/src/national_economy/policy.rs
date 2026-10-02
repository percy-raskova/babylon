//! Explicit native quantities and Designed opening policies; no equilibrium solver.

mod admission;
use babylon_kernel::{
    currency::Currency, economic_identity::EconomicFunction, economic_location::ForeignCounterpart,
};
use babylon_material_circuit::{CommodityKind, GoodId, HouseholdNeedBasis, UnitId};
use std::collections::BTreeMap;

/// One current policy decoded from captured bytes, independent of source paths.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct NationalGamePolicy {
    pub period_days: u64,
    pub work_hours_per_person: u64,
    pub default_wage: Currency,
    pub opening_pantry_periods: u64,
    pub opening_input_periods: u64,
    pub working_capital_periods: u64,
    pub retailer_buffer_periods: u64,
    pub resource_reserve_output_periods: u64,
    pub handling_hours_per_unit: u64,
    pub missing_peer_weight_per_establishment: u64,
    pub household_enterprise_function: EconomicFunction,
    pub financial: GameFinancialPolicy,
    pub equipment: GameEquipmentPolicy,
    pub commodities: BTreeMap<String, GameCommodity>,
    pub recipes: BTreeMap<EconomicFunction, GameRecipe>,
    pub household_needs: Vec<GameNeed>,
    pub counterparts: BTreeMap<ForeignCounterpart, GameProfile>,
    pub dependency: GameDependencyProfile,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GameCommodity {
    pub good_id: GoodId,
    pub unit_id: UnitId,
    pub label: String,
    pub unit_label: String,
    pub kind: CommodityKind,
    pub price: Option<GamePrice>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GamePrice {
    pub opening: Currency,
    pub minimum: Currency,
    pub maximum: Currency,
    pub step: Currency,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GameRecipe {
    pub output: String,
    pub output_units_per_batch: u64,
    pub labor_hours_per_batch: u64,
    pub inputs: BTreeMap<String, u64>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GameNeed {
    pub key: String,
    pub basis: HouseholdNeedBasis,
    pub units_per_basis: u64,
}

/// Statistical source population is not itself a labor-force observation.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GameProfile {
    pub participation_bps: u16,
    pub opening_employment_bps: u16,
    pub persons_per_household: u64,
    pub wage_per_hour: Currency,
    pub price_scale_bps: u16,
    /// `EconomicFunction` source-key order, independent of ownership or class.
    pub function_weights_bps: [u16; 10],
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GameDependencyProfile {
    pub profile: GameProfile,
    pub missing_population_game_persons: u64,
}

/// Designed rates and budget commitments; payments still require actual funds.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GameFinancialPolicy {
    pub wage_tax_bps: u16,
    pub operating_income_tax_bps: u16,
    pub private_distribution_bps: u16,
    pub reserve_food_support_periods: u64,
    pub cross_border_ownership_bps: u16,
}

/// Finite productive use and installation requirements, independent of the horizon.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GameEquipmentPolicy {
    pub batches_per_unit_per_period: u64,
    pub service_batches_per_unit: u64,
    pub installation_hours_per_unit: u64,
    pub installation_inputs: BTreeMap<String, u64>,
    pub installation_workforce_hours_bps: u16,
    pub expansion_earnings_fraction_bps: u16,
    pub opening_remaining_service_bps: [u16; 4],
}

/// Disjoint fixed person pools; no jobs are converted into additional people.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct ResidentOpeningCounts {
    pub persons: u64,
    pub households: u64,
    pub employed: u64,
    pub reserve: u64,
    pub inactive: u64,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum NationalGamePolicyError {
    Syntax,
    Bounds,
    Evidence,
    Shape,
    Commodity(String),
    Recipe(String),
    HouseholdNeed(String),
    Profile(String),
    Location,
    Arithmetic,
}
impl std::fmt::Display for NationalGamePolicyError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "national game policy refused: {self:?}")
    }
}
impl std::error::Error for NationalGamePolicyError {}

impl NationalGamePolicy {
    /// Decode the singular captured policy; never reads a current filesystem path.
    /// # Errors
    /// Refuses unsupported versions, missing declarations, ambiguous units and overflow.
    pub fn from_captured_bytes(bytes: &[u8]) -> Result<Self, NationalGamePolicyError> {
        if bytes.len() > 65_536 {
            return Err(NationalGamePolicyError::Bounds);
        }
        Self::parse(std::str::from_utf8(bytes).map_err(|_| NationalGamePolicyError::Syntax)?)
    }

    /// Decode authoring text using the same strict admission as saved captures.
    /// # Errors
    /// Refuses unknown fields, invalid prices, false evidence and unsupported service dependencies.
    pub fn parse(source: &str) -> Result<Self, NationalGamePolicyError> {
        admission::parse(source)
    }
}

impl GameProfile {
    /// Allocate this explicitly Designed fixed workforce within the supplied persons.
    /// # Errors
    /// Refuses a zero population or unrepresentable current-period person-hours.
    pub fn opening_counts(
        &self,
        persons: u64,
    ) -> Result<ResidentOpeningCounts, NationalGamePolicyError> {
        if persons == 0
            || self.persons_per_household == 0
            || !(1..=10_000).contains(&self.participation_bps)
            || self.opening_employment_bps > 10_000
        {
            return Err(NationalGamePolicyError::Profile(
                "invalid resident or workforce control".to_owned(),
            ));
        }
        let force =
            u64::try_from(u128::from(persons) * u128::from(self.participation_bps) / 10_000)
                .map_err(|_| NationalGamePolicyError::Arithmetic)?;
        let employed =
            u64::try_from(u128::from(force) * u128::from(self.opening_employment_bps) / 10_000)
                .map_err(|_| NationalGamePolicyError::Arithmetic)?;
        // A future compiler cannot accept a population whose largest allowed
        // 28-day work schedule could overflow its u64 labor-time accounts.
        force
            .checked_mul(28 * 24)
            .ok_or(NationalGamePolicyError::Arithmetic)?;
        Ok(ResidentOpeningCounts {
            persons,
            households: persons.div_ceil(self.persons_per_household),
            employed,
            reserve: force
                .checked_sub(employed)
                .ok_or(NationalGamePolicyError::Arithmetic)?,
            inactive: persons
                .checked_sub(force)
                .ok_or(NationalGamePolicyError::Arithmetic)?,
        })
    }
}

impl GamePrice {
    /// Apply a captured common-currency price scale, rounded to exact micro-units.
    /// This changes an opening offer, not an exchange rate or a population source.
    /// # Errors
    /// Refuses zero scale, invalid prices or arithmetic overflow.
    pub fn scaled(&self, scale_bps: u16) -> Result<Self, NationalGamePolicyError> {
        let scale = |price: Currency| {
            let product = price
                .micro_units()
                .checked_mul(i128::from(scale_bps))
                .ok_or(NationalGamePolicyError::Arithmetic)?;
            let micros = babylon_kernel::currency::round_half_even_div(product, 10_000);
            if micros <= 0 {
                return Err(NationalGamePolicyError::Profile(
                    "invalid price scale".to_owned(),
                ));
            }
            Ok(Currency::from_micro_units(micros))
        };
        if scale_bps == 0
            || self.minimum.micro_units() <= 0
            || self.step.micro_units() <= 0
            || self.minimum > self.opening
            || self.opening > self.maximum
        {
            return Err(NationalGamePolicyError::Profile(
                "invalid price scale".to_owned(),
            ));
        }
        Ok(Self {
            opening: scale(self.opening)?,
            minimum: scale(self.minimum)?,
            maximum: scale(self.maximum)?,
            step: scale(self.step)?,
        })
    }
}
