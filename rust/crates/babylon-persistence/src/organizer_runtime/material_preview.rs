//! Actor-safe material facts; no forecast of admission, delivered quantity or practice.
use crate::runtime_session::RuntimeSessionErrorCode;
use babylon_material_circuit::{
    AidTransport, CircuitAccounting, HouseholdTimeAccounting, MaterialCircuitState,
};
use babylon_practice_contract::{
    OrganizerAidKind, OrganizerAidSupport, OrganizerConfig, OrganizerGiftConsent,
    OrganizerPendingAidPractice, OrganizerReceipt, OrganizerState,
};
use serde::{Deserialize, Serialize};
type Result<T> = std::result::Result<T, RuntimeSessionErrorCode>;
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct OrganizerMaterialAidPreview {
    pub kind: OrganizerAidKind,
    pub mandate_id: [u8; 32],
    pub period: u64,
    pub donor_id: [u8; 32],
    pub recipient_id: [u8; 32],
    pub good_id: [u8; 32],
    pub unit_id: [u8; 32],
    pub donor_stock: u64,
    pub own_need: u64,
    pub grams_per_unit: u64,
    #[serde(with = "decimal_i128")]
    pub payer_cash: i128,
    pub ordinary_offer: Option<OrganizerAidOrdinaryOffer>,
    pub maximum_quantity: u64,
    #[serde(with = "decimal_i128")]
    pub gift_cash_per_unit: i128,
    pub labor_unit_id: [u8; 32],
    pub fulfillment_hours_per_unit: u64,
    pub coordination_hours: u64,
    pub receiving_consent: OrganizerGiftConsent,
    pub time: Option<OrganizerAidTime>,
    pub transport: OrganizerAidTransportPreview,
}
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct OrganizerAidOrdinaryOffer {
    pub seller_id: [u8; 32],
    #[serde(with = "decimal_i128")]
    pub unit_price: i128,
}
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct OrganizerAidTime {
    pub period: u64,
    pub labor_unit_id: [u8; 32],
    pub remaining_hours: u64,
}
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub enum OrganizerAidTransportPreview {
    Local,
    Routed {
        route_id: [u8; 32],
        from_node_id: [u8; 32],
        to_node_id: [u8; 32],
        stages: Vec<OrganizerAidRouteStage>,
    },
}
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct OrganizerAidRouteStage {
    pub stage_index: u16,
    pub from_node_id: [u8; 32],
    pub to_node_id: [u8; 32],
    pub travel_periods: u16,
    pub loss_ppm: u32,
    pub departure_period: u64,
    pub capacities: Vec<OrganizerAidCapacity>,
}
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct OrganizerAidCapacity {
    pub corridor_id: [u8; 32],
    pub remaining_grams: Option<u64>,
}
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct OrganizerAidPending {
    pub kind: OrganizerAidKind,
    pub original_commitment_id: [u8; 32],
    pub material_commitment_id: [u8; 32],
    pub mandate_id: [u8; 32],
    pub admitted_period: u64,
    pub dispatch_period: u64,
    pub good_id: [u8; 32],
    pub unit_id: [u8; 32],
}
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct OrganizerAidResolution {
    pub pending: OrganizerAidPending,
    pub support: OrganizerAidSupport,
    pub practice: OrganizerReceipt,
}
fn refused() -> RuntimeSessionErrorCode {
    RuntimeSessionErrorCode::OrganizerRefused
}
pub(super) fn pending(row: &OrganizerPendingAidPractice) -> OrganizerAidPending {
    OrganizerAidPending {
        kind: row.gift.kind,
        original_commitment_id: row.gift.commitment.commitment_id,
        material_commitment_id: row.material_commitment_id,
        mandate_id: row.gift.mandate_id,
        admitted_period: row.gift.commitment.command.expected_period,
        dispatch_period: row.dispatch_period,
        good_id: row.good_id,
        unit_id: row.unit_id,
    }
}
pub(super) fn projections(
    state: &MaterialCircuitState,
    config: &OrganizerConfig,
    period: u64,
) -> Result<Vec<OrganizerMaterialAidPreview>> {
    if period.checked_add(1) != Some(state.period) {
        return Err(refused());
    }
    if config.aid_bindings.is_empty() {
        return Ok(Vec::new());
    }
    let CircuitAccounting::Monetary(economy) = &state.accounting else {
        return Err(refused());
    };
    let recurring = economy.recurring.as_ref().ok_or_else(refused)?;
    let mut result = Vec::with_capacity(config.aid_bindings.len());
    for binding in &config.aid_bindings {
        let mandate = economy
            .aid
            .mandates
            .iter()
            .find(|m| m.id == binding.mandate_id)
            .ok_or_else(refused)?;
        if mandate.source_hash != binding.source_hash
            || mandate.donor.as_bytes() != binding.donor_principal_id
            || mandate.recipient.as_bytes() != binding.recipient_principal_id
            || mandate.donor_actor != config.controlled_actor_id
        {
            return Err(refused());
        }
        let (donor_stock, own_need) = pantry_amounts(recurring, mandate)?;
        let ordinary_offer = recurring
            .household_purchases
            .iter()
            .find(|p| {
                p.principal_id == mandate.donor
                    && p.good_id == mandate.good_id
                    && p.unit_id == mandate.unit_id
            })
            .and_then(|p| {
                recurring.offers.iter().find(|o| {
                    o.site_id == p.retailer_site_id
                        && o.good_id == mandate.good_id
                        && o.unit_id == mandate.unit_id
                })
            })
            .map(|o| OrganizerAidOrdinaryOffer {
                seller_id: o.site_id.as_bytes(),
                unit_price: o.unit_price.micro_units(),
            });
        let time = remaining_time(state, mandate.donor, mandate.labor_unit_id, period)?;
        let transport = transport(state, mandate.transport)?;
        result.push(OrganizerMaterialAidPreview {
            kind: binding.kind,
            mandate_id: mandate.id,
            period,
            donor_id: mandate.donor.as_bytes(),
            recipient_id: mandate.recipient.as_bytes(),
            good_id: mandate.good_id.as_bytes(),
            unit_id: mandate.unit_id.as_bytes(),
            donor_stock,
            own_need,
            grams_per_unit: state
                .commodities
                .iter()
                .find(|r| r.good_id == mandate.good_id && r.unit_id == mandate.unit_id)
                .ok_or_else(refused)?
                .grams_per_unit()
                .map_err(|_| refused())?,
            payer_cash: economy
                .book
                .cash(mandate.payer)
                .map_err(|_| refused())?
                .micro_units(),
            ordinary_offer,
            maximum_quantity: mandate.maximum_quantity,
            gift_cash_per_unit: mandate.cash_per_unit.micro_units(),
            labor_unit_id: mandate.labor_unit_id.as_bytes(),
            fulfillment_hours_per_unit: mandate.hours_per_unit,
            coordination_hours: binding.coordination_hours,
            receiving_consent: binding.receiving_consent,
            time,
            transport,
        });
    }
    Ok(result)
}
fn pantry_amounts(
    recurring: &babylon_material_circuit::RecurringEconomy,
    mandate: &babylon_material_circuit::AidMandate,
) -> Result<(u64, u64)> {
    let cohort = recurring
        .households
        .iter()
        .find(|r| r.principal_id == mandate.donor)
        .ok_or_else(refused)?;
    let own_need = recurring
        .household_needs
        .iter()
        .filter(|r| {
            r.principal_id == mandate.donor
                && r.good_id == mandate.good_id
                && r.unit_id == mandate.unit_id
        })
        .try_fold(0u64, |sum, r| {
            sum.checked_add(r.required_quantity(cohort).map_err(|_| refused())?)
                .ok_or_else(refused)
        })?;
    let donor_stock = recurring
        .household_stocks
        .iter()
        .filter(|r| {
            r.principal_id == mandate.donor
                && r.good_id == mandate.good_id
                && r.unit_id == mandate.unit_id
        })
        .try_fold(0u64, |sum, r| {
            sum.checked_add(r.quantity).ok_or_else(refused)
        })?;
    Ok((donor_stock, own_need))
}

fn remaining_time(
    state: &MaterialCircuitState,
    principal: babylon_material_circuit::FinalDemandPrincipalId,
    unit: babylon_material_circuit::UnitId,
    period: u64,
) -> Result<Option<OrganizerAidTime>> {
    if period == 0 {
        return Ok(None);
    }
    let CircuitAccounting::Monetary(economy) = &state.accounting else {
        return Err(refused());
    };
    let HouseholdTimeAccounting::Modeled(book) = &economy.household_time else {
        return Err(refused());
    };
    let row = book
        .receipts
        .iter()
        .find(|r| r.principal_id == principal)
        .ok_or_else(refused)?;
    if row.period != period || row.labor_unit_id != unit {
        return Err(refused());
    }
    let spent = book
        .contributions
        .iter()
        .filter(|r| r.contribution.principal_id == principal)
        .try_fold(0u64, |sum, r| {
            if r.period != period {
                return Err(refused());
            }
            sum.checked_add(r.contribution.hours).ok_or_else(refused)
        })?;
    Ok(Some(OrganizerAidTime {
        period,
        labor_unit_id: unit.as_bytes(),
        remaining_hours: row
            .contribution_available_hours
            .checked_sub(spent)
            .ok_or_else(refused)?,
    }))
}
fn transport(
    state: &MaterialCircuitState,
    value: AidTransport,
) -> Result<OrganizerAidTransportPreview> {
    let AidTransport::Routed {
        route_id,
        from_node_id,
        to_node_id,
    } = value
    else {
        return Ok(OrganizerAidTransportPreview::Local);
    };
    let mut departure = state.period;
    let mut stages = Vec::new();
    for row in state.route_stages.iter().filter(|r| r.route_id == route_id) {
        let capacities = state
            .route_stage_capacities
            .iter()
            .filter(|r| r.route_id == route_id && r.stage_index == row.stage_index)
            .map(|m| {
                Ok(OrganizerAidCapacity {
                    corridor_id: m.corridor_id.as_bytes(),
                    remaining_grams: remaining_capacity(state, m.corridor_id, departure)?,
                })
            })
            .collect::<Result<Vec<_>>>()?;
        stages.push(OrganizerAidRouteStage {
            stage_index: row.stage_index,
            from_node_id: row.from_node_id.as_bytes(),
            to_node_id: row.to_node_id.as_bytes(),
            travel_periods: row.travel_periods,
            loss_ppm: row.loss_ppm,
            departure_period: departure,
            capacities,
        });
        departure = departure
            .checked_add(u64::from(row.travel_periods))
            .ok_or_else(refused)?;
    }
    if stages.is_empty() {
        return Err(refused());
    }
    Ok(OrganizerAidTransportPreview::Routed {
        route_id: route_id.as_bytes(),
        from_node_id: from_node_id.as_bytes(),
        to_node_id: to_node_id.as_bytes(),
        stages,
    })
}
pub(super) fn resolutions(state: &OrganizerState) -> Vec<OrganizerAidResolution> {
    state
        .aid_receipts
        .iter()
        .filter(|r| r.practice.period == state.period)
        .map(|r| OrganizerAidResolution {
            pending: pending(&r.authorization),
            support: r.support.clone(),
            practice: r.practice.clone(),
        })
        .collect()
}

fn remaining_capacity(
    state: &MaterialCircuitState,
    id: babylon_material_circuit::CorridorId,
    period: u64,
) -> Result<Option<u64>> {
    if let Some(row) = state
        .corridor_capacities
        .iter()
        .find(|r| r.corridor_id == id && r.period == period)
    {
        return Ok(Some(row.available_grams));
    }
    match &state.capacity_supply {
        babylon_material_circuit::CapacitySupply::FiniteSchedule => Ok(Some(0)),
        babylon_material_circuit::CapacitySupply::Rolling(supply) => {
            let Some(row) = supply.shared.iter().find(|r| r.corridor_id == id) else {
                return Ok(None);
            };
            let reserved = supply
                .future_reservations
                .iter()
                .filter(|r| r.corridor_id == id && r.departure_period == period)
                .try_fold(0u64, |sum, r| {
                    sum.checked_add(r.reserved_grams).ok_or_else(refused)
                })?;
            Ok(Some(net_capacity(row.grams_per_period, reserved)?))
        }
    }
}
fn net_capacity(supply: u64, reserved: u64) -> Result<u64> {
    supply.checked_sub(reserved).ok_or_else(refused)
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn shared_capacity_is_not_nameplate_and_overdraw_is_not_zero() {
        assert_eq!(net_capacity(100, 37), Ok(63));
        assert_eq!(net_capacity(100, 100), Ok(0));
        assert_eq!(
            net_capacity(100, 101),
            Err(RuntimeSessionErrorCode::OrganizerRefused)
        );
    }
}

#[cfg(test)]
#[path = "material_preview_tests.rs"]
mod projection_tests;

/// Decimal text avoids Serde's internally tagged Content i128 limitation.
/// This runtime-only representation never changes canonical engine accounting.
pub(super) mod decimal_i128 {
    use serde::{de, Deserializer, Serializer};
    use std::fmt;

    pub fn serialize<S: Serializer>(value: &i128, serializer: S) -> Result<S::Ok, S::Error> {
        serializer.serialize_str(&value.to_string())
    }

    pub fn deserialize<'de, D: Deserializer<'de>>(deserializer: D) -> Result<i128, D::Error> {
        struct Decimal;
        impl de::Visitor<'_> for Decimal {
            type Value = i128;
            fn expecting(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
                formatter.write_str("canonical signed i128 decimal string")
            }
            fn visit_str<E: de::Error>(self, value: &str) -> Result<i128, E> {
                if value.len() > 40 {
                    return Err(E::custom("i128 decimal length exceeds bound"));
                }
                let number = value
                    .parse::<i128>()
                    .map_err(|_| E::custom("invalid or overflowing i128 decimal"))?;
                if number.to_string() != value {
                    return Err(E::custom("noncanonical i128 decimal"));
                }
                Ok(number)
            }
        }
        deserializer.deserialize_str(Decimal)
    }
}
