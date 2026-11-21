//! What each account wanted and bought in each tier, and the standard those records give.

use crate::{
    FinalDemandPrincipalId, GoodId, HouseholdConsumptionReceipt, HouseholdServiceReceipt,
    MaterialCircuitError, OrderId, SiteId, UnitId, WantTier,
};
use babylon_kernel::content_digest;
use babylon_kernel::currency::Currency;

/// Exact identity of a household's want of one product in one tier in one period.
#[must_use]
pub fn recurring_household_want_order_id(
    period: u64,
    key: (FinalDemandPrincipalId, GoodId, UnitId),
    tier: WantTier,
) -> OrderId {
    let mut bytes = b"babylon.recurring-household-want-order.v1\0".to_vec();
    bytes.extend_from_slice(&period.to_be_bytes());
    bytes.extend_from_slice(&key.0.as_bytes());
    bytes.extend_from_slice(&key.1.as_bytes());
    bytes.extend_from_slice(&key.2.as_bytes());
    bytes.push(tier as u8);
    OrderId::from_bytes(content_digest::sha256_of(&bytes))
}

/// Exact identity of a household's want of one service in one tier in one period.
#[must_use]
pub fn recurring_service_want_order_id(
    period: u64,
    principal: FinalDemandPrincipalId,
    provider: SiteId,
    good: GoodId,
    unit: UnitId,
    tier: WantTier,
) -> OrderId {
    let mut bytes = b"babylon.recurring-service-want-order.v1\0".to_vec();
    bytes.extend_from_slice(&period.to_be_bytes());
    bytes.extend_from_slice(&principal.as_bytes());
    bytes.extend_from_slice(&provider.as_bytes());
    bytes.extend_from_slice(&good.as_bytes());
    bytes.extend_from_slice(&unit.as_bytes());
    bytes.push(tier as u8);
    OrderId::from_bytes(content_digest::sha256_of(&bytes))
}

/// One account, tier and product this period. `posted_price` values the tier; `unit_price` is the
/// market's.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct HouseholdWantReceipt {
    pub period: u64,
    pub principal_id: FinalDemandPrincipalId,
    pub tier: WantTier,
    pub seller_site_id: SiteId,
    pub good_id: GoodId,
    pub unit_id: UnitId,
    pub order_id: OrderId,
    pub wanted_quantity: u64,
    pub bought_quantity: u64,
    pub posted_price: Currency,
    pub unit_price: Currency,
}

impl HouseholdWantReceipt {
    /// # Errors
    /// `MarketClearingInvariant` for a period of zero, more bought than wanted, a posted price that
    /// is not positive, or a market price below the posted one.
    pub fn validate(&self) -> Result<(), MaterialCircuitError> {
        if self.period == 0
            || self.bought_quantity > self.wanted_quantity
            || self.posted_price.micro_units() <= 0
            || self.unit_price < self.posted_price
        {
            return Err(MaterialCircuitError::MarketClearingInvariant);
        }
        Ok(())
    }
}

/// One account and tier this period, at posted prices.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct HouseholdTierReceipt {
    pub period: u64,
    pub principal_id: FinalDemandPrincipalId,
    pub tier: WantTier,
    pub wanted_value: Currency,
    pub bought_value: Currency,
}

impl HouseholdTierReceipt {
    /// # Errors
    /// `MarketClearingInvariant` for a period of zero, a negative value, or more bought than wanted.
    pub fn validate(&self) -> Result<(), MaterialCircuitError> {
        if self.period == 0
            || self.wanted_value.micro_units() < 0
            || self.bought_value.micro_units() < 0
            || self.bought_value > self.wanted_value
        {
            return Err(MaterialCircuitError::MarketClearingInvariant);
        }
        Ok(())
    }
}

/// `quantity x price`, exactly.
pub(super) fn value(quantity: u64, price: Currency) -> Result<i128, MaterialCircuitError> {
    i128::from(quantity)
        .checked_mul(price.micro_units())
        .ok_or(MaterialCircuitError::Arithmetic)
}

/// Each row is valid, and each tier row equals the sums of its account's want rows at posted prices.
///
/// # Errors
/// `MarketClearingInvariant`, or `Arithmetic` for a sum outside `i128`.
pub(super) fn validate_records(
    wants: &[HouseholdWantReceipt],
    tiers: &[HouseholdTierReceipt],
) -> Result<(), MaterialCircuitError> {
    for row in wants {
        row.validate()?;
    }
    for row in tiers {
        row.validate()?;
        let (mut wanted, mut bought) = (0_i128, 0_i128);
        for want in wants
            .iter()
            .filter(|w| w.principal_id == row.principal_id && w.tier == row.tier)
        {
            wanted = wanted
                .checked_add(value(want.wanted_quantity, want.posted_price)?)
                .ok_or(MaterialCircuitError::Arithmetic)?;
            bought = bought
                .checked_add(value(want.bought_quantity, want.posted_price)?)
                .ok_or(MaterialCircuitError::Arithmetic)?;
        }
        if wanted != row.wanted_value.micro_units() || bought != row.bought_value.micro_units() {
            return Err(MaterialCircuitError::MarketClearingInvariant);
        }
    }
    Ok(())
}

/// How well an account lived this period, read from its records.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
#[repr(u8)]
pub enum HouseholdStandard {
    GoingWithout = 1,
    GettingBy = 2,
    Comfortable = 3,
    Affluent = 4,
}

/// Going without when a need of the account went unmet; else getting by when it did not buy all its
/// comforts; else comfortable when it did not buy all its luxuries; else affluent.
///
/// # Errors
/// `MarketClearingInvariant` when a tier row of the account is missing or appears twice.
pub fn household_standard(
    principal: FinalDemandPrincipalId,
    consumption: &[HouseholdConsumptionReceipt],
    services: &[HouseholdServiceReceipt],
    tiers: &[HouseholdTierReceipt],
) -> Result<HouseholdStandard, MaterialCircuitError> {
    let one = |tier: WantTier| {
        let mut rows = tiers
            .iter()
            .filter(|row| row.principal_id == principal && row.tier == tier);
        match (rows.next(), rows.next()) {
            (Some(row), None) => Ok(row),
            _ => Err(MaterialCircuitError::MarketClearingInvariant),
        }
    };
    let comfort = one(WantTier::Comfort)?;
    let luxury = one(WantTier::Luxury)?;
    let unmet = consumption
        .iter()
        .any(|row| row.principal_id == principal && row.unmet_quantity > 0)
        || services
            .iter()
            .any(|row| row.principal_id == principal && row.unmet_quantity > 0);
    Ok(if unmet {
        HouseholdStandard::GoingWithout
    } else if comfort.bought_value < comfort.wanted_value {
        HouseholdStandard::GettingBy
    } else if luxury.bought_value < luxury.wanted_value {
        HouseholdStandard::Comfortable
    } else {
        HouseholdStandard::Affluent
    })
}
