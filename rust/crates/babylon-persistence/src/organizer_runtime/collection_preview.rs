//! Captured rule and owned account facts. Protected eligibility is judged only at close.
use super::{material_preview::decimal_i128, RuntimeSessionErrorCode};
use babylon_material_circuit::{
    AccountId, CircuitAccounting, MaterialCircuitState, OrganizationAccountId,
};
use babylon_practice_contract::{OrganizerConfig, OrganizerGiftConsent};
use serde::{Deserialize, Serialize};
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct OrganizerCollectionPreview {
    pub period: u64,
    pub mandate_id: [u8; 32],
    pub cash_consent: OrganizerGiftConsent,
    #[serde(with = "nonnegative_decimal_i128")]
    pub maximum_cash_micros: i128,
    #[serde(with = "nonnegative_decimal_i128")]
    pub protected_cash_floor_micros: i128,
    pub collection_hours: u64,
    #[serde(with = "nonnegative_decimal_i128")]
    pub organization_cash_micros: i128,
}
pub(super) fn required_nullable<'de, D, T>(d: D) -> Result<Option<T>, D::Error>
where
    D: serde::Deserializer<'de>,
    T: Deserialize<'de>,
{
    Option::deserialize(d)
}
pub(super) fn projection(
    state: &MaterialCircuitState,
    config: &OrganizerConfig,
    period: u64,
) -> Result<Option<OrganizerCollectionPreview>, RuntimeSessionErrorCode> {
    let refused = || RuntimeSessionErrorCode::OrganizerRefused;
    if period.checked_add(1) != Some(state.period) {
        return Err(refused());
    }
    let Some(m) = &config.collection else {
        return Ok(None);
    };
    if m.actor_id != config.controlled_actor_id {
        return Err(refused());
    }
    let CircuitAccounting::Monetary(economy) = &state.accounting else {
        return Err(refused());
    };
    let cash = economy
        .book
        .cash(AccountId::Organization(OrganizationAccountId::from_bytes(
            m.organization_account_id,
        )))
        .map_err(|_| refused())?
        .micro_units();
    Ok(Some(OrganizerCollectionPreview {
        period,
        mandate_id: m.mandate_id,
        cash_consent: m.cash_consent,
        maximum_cash_micros: m.maximum_cash_micros,
        protected_cash_floor_micros: m.protected_cash_floor_micros,
        collection_hours: m.collection_hours,
        organization_cash_micros: cash,
    }))
}

mod nonnegative_decimal_i128 {
    use super::decimal_i128;
    use serde::{Deserializer, Serializer};
    pub fn serialize<S: Serializer>(value: &i128, s: S) -> Result<S::Ok, S::Error> {
        if *value < 0 {
            return Err(serde::ser::Error::custom("negative collection cash"));
        }
        decimal_i128::serialize(value, s)
    }
    pub fn deserialize<'de, D: Deserializer<'de>>(d: D) -> Result<i128, D::Error> {
        let value = decimal_i128::deserialize(d)?;
        if value < 0 {
            return Err(serde::de::Error::custom("negative collection cash"));
        }
        Ok(value)
    }
}
