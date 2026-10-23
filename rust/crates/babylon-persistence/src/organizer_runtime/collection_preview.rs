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
    pub actor_id: u64,
    pub contributor_id: u64,
    pub contributor_label: String,
    pub source_hash: [u8; 32],
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
    let participant = config
        .participants
        .iter()
        .find(|participant| participant.contributor_id == m.contributor_id)
        .ok_or_else(refused)?;
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
        actor_id: m.actor_id,
        contributor_id: m.contributor_id,
        contributor_label: participant.label.clone(),
        source_hash: m.source_hash,
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

#[cfg(test)]
mod tests {
    use super::*;
    use crate::organizer_aid_fixture as fixture;
    use babylon_practice_contract::{validate_organizer_config, OrganizerCollectionMandate};

    #[test]
    fn collection_terms_project_captured_contributor_and_source_at_committed_period() {
        let session = fixture::authored_session(
            crate::michigan_dynamic_hex_foundation().unwrap(),
            fixture::config(),
            false,
            false,
        );
        let CircuitAccounting::Monetary(economy) = &session.material().state().accounting else {
            panic!("monetary captured fixture");
        };
        let labor_unit_id = economy.aid.mandates[0].labor_unit_id.as_bytes();
        let mut config = session.material().organizer_config().unwrap().clone();
        let binding = &config.aid_bindings[0];
        config.collection = Some(OrganizerCollectionMandate {
            mandate_id: [8; 32],
            source_hash: [9; 32],
            actor_id: config.controlled_actor_id,
            contributor_id: binding.donor_contributor_id,
            household_principal_id: binding.donor_principal_id,
            organization_account_id: [96; 32],
            social_class_target: binding.social_class_target,
            labor_unit_id,
            cash_consent: OrganizerGiftConsent::Accept,
            maximum_cash_micros: 400_000,
            protected_cash_floor_micros: 0,
            collection_hours: 2,
        });
        validate_organizer_config(&config).unwrap();
        let state = session.material().state();
        let terms = projection(state, &config, 0).unwrap().unwrap();
        assert_eq!(terms.actor_id, config.controlled_actor_id);
        assert_eq!(terms.contributor_id, 201);
        assert_eq!(terms.contributor_label, "Fixture participant 201");
        assert_eq!(terms.source_hash, [9; 32]);
        assert_eq!(terms.period, 0);
        assert_eq!(
            projection(state, &config, 1),
            Err(RuntimeSessionErrorCode::OrganizerRefused)
        );
        config.collection.as_mut().unwrap().actor_id += 1;
        assert_eq!(
            projection(state, &config, 0),
            Err(RuntimeSessionErrorCode::OrganizerRefused)
        );
        config.collection.as_mut().unwrap().actor_id -= 1;
        config
            .participants
            .retain(|participant| participant.contributor_id != 201);
        assert_eq!(
            projection(state, &config, 0),
            Err(RuntimeSessionErrorCode::OrganizerRefused)
        );
    }
}
