//! Actor-safe material facts; no forecast of admission, delivered quantity or practice.
use crate::runtime_session::RuntimeSessionErrorCode;
use babylon_material_circuit::CapacitySupply;
use babylon_material_circuit::CorridorId;
use babylon_material_circuit::FinalDemandPrincipalId;
use babylon_material_circuit::MonetaryError;
use babylon_material_circuit::RecurringEconomy;
use babylon_material_circuit::UnitId;
use babylon_material_circuit::{AccountId, AidMandate, MaterialCircuitError};
use babylon_material_circuit::{
    AidTransport, CircuitAccounting, HouseholdTimeAccounting, MaterialCatalog, MaterialCircuitState,
};
use babylon_practice_contract::OrganizerAidCashStatus;
use babylon_practice_contract::OrganizerAidMaterialPostings;
use babylon_practice_contract::OrganizerAidSupportStatus;
use babylon_practice_contract::OrganizerAllocation;
use babylon_practice_contract::{
    OrganizerAidKind, OrganizerAidSupport, OrganizerConfig, OrganizerGiftConsent,
    OrganizerPendingAidPractice, OrganizerPeriodJournalEntries, OrganizerReceipt,
};
use babylon_practice_contract::{OrganizerChoice, OrganizerCommand};
use serde::{Deserialize, Serialize};
type Result<T> = std::result::Result<T, RuntimeSessionErrorCode>;
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct OrganizerMaterialAidPreview {
    pub kind: OrganizerAidKind,
    pub mandate_id: [u8; 32],
    pub period: u64,
    pub donor_id: [u8; 32],
    pub recipient_actor_id: u64,
    pub good_id: [u8; 32],
    pub unit_id: [u8; 32],
    #[serde(deserialize_with = "required_food")]
    pub food: Option<OrganizerAidFoodPreview>,
    pub funding: OrganizerAidFunding,
    pub maximum_quantity: u64,
    #[serde(with = "decimal_i128")]
    pub maximum_cash_micros: i128,
    pub initial_food_quantity: u64,
    #[serde(with = "decimal_i128")]
    pub initial_cash_micros: i128,
    pub cash_receiving_consent: OrganizerGiftConsent,
    pub coordination_hours: u64,
    pub receiving_consent: OrganizerGiftConsent,
}

/// Authority to attempt a cash gift and, for a controlled treasury, read its balance.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case", deny_unknown_fields)]
pub enum OrganizerAidFunding {
    Unavailable,
    Mandated,
    Organization {
        #[serde(with = "decimal_i128")]
        cash_micros: i128,
    },
}

impl OrganizerAidFunding {
    /// Whether the original can attempt a positive cash gift.
    #[must_use]
    pub fn available(self) -> bool {
        !matches!(self, Self::Unavailable)
    }
}

/// Available physical food facts. Absence on the parent means that leg is unwired.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct OrganizerAidFoodPreview {
    pub donor_stock: u64,
    pub own_need: u64,
    pub grams_per_unit: u64,
    pub ordinary_offer: Option<OrganizerAidOrdinaryOffer>,
    pub labor_unit_id: [u8; 32],
    pub fulfillment_hours_per_unit: u64,
    pub time: Option<OrganizerAidTime>,
    pub transport: OrganizerAidTransportPreview,
}

fn required_food<'de, D: serde::Deserializer<'de>>(
    deserializer: D,
) -> std::result::Result<Option<OrganizerAidFoodPreview>, D::Error> {
    Option::<OrganizerAidFoodPreview>::deserialize(deserializer)
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
/// Food movements observable by the sender under its practice receipt.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case", deny_unknown_fields)]
pub enum OrganizerFoodDelivery {
    NotRequested,
    AwaitingDelivery,
    ReceivingRefused,
    TerminalFailure,
    Granted { granted_quantity: u64 },
}

impl From<OrganizerAidSupportStatus> for OrganizerFoodDelivery {
    fn from(status: OrganizerAidSupportStatus) -> Self {
        match status {
            OrganizerAidSupportStatus::NotRequested => Self::NotRequested,
            OrganizerAidSupportStatus::AwaitingDelivery => Self::AwaitingDelivery,
            OrganizerAidSupportStatus::ReceivingRefused => Self::ReceivingRefused,
            OrganizerAidSupportStatus::TerminalFailure => Self::TerminalFailure,
            OrganizerAidSupportStatus::Granted {
                granted_quantity, ..
            } => Self::Granted { granted_quantity },
        }
    }
}

/// The sender can follow its own original commitment, transfers and delivery dates.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct OrganizerAidTransfer {
    pub original_commitment_id: [u8; 32],
    pub material_commitment_id: [u8; 32],
    pub mandate_id: [u8; 32],
    pub dispatch_period: u64,
    pub period: u64,
    pub good_id: [u8; 32],
    pub unit_id: [u8; 32],
    pub status: OrganizerFoodDelivery,
    pub cash_status: OrganizerAidCashStatus,
    pub material_postings: OrganizerAidMaterialPostings,
}

impl From<&OrganizerAidSupport> for OrganizerAidTransfer {
    fn from(row: &OrganizerAidSupport) -> Self {
        Self {
            original_commitment_id: row.original_commitment_id,
            material_commitment_id: row.material_commitment_id,
            mandate_id: row.mandate_id,
            dispatch_period: row.dispatch_period,
            period: row.period,
            good_id: row.good_id,
            unit_id: row.unit_id,
            status: row.status.into(),
            cash_status: row.cash_status,
            material_postings: row.material_postings.clone(),
        }
    }
}

fn owned_practice(receipt: &OrganizerReceipt) -> OrganizerReceipt {
    let mut disclosed = receipt.clone();
    disclosed
        .time_use
        .retain(|row| row.actor_id == receipt.actor_id);
    disclosed
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
    pub allocation: OrganizerAllocation,
    pub dispatch_support: OrganizerAidTransfer,
    pub response: Option<OrganizerReceipt>,
    pub lost_quantity: u64,
}
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct OrganizerAidResolution {
    pub pending: OrganizerAidPending,
    pub support: OrganizerAidTransfer,
    pub practice: OrganizerReceipt,
}
fn refused() -> RuntimeSessionErrorCode {
    RuntimeSessionErrorCode::OrganizerRefused
}
pub(super) fn pending(row: &OrganizerPendingAidPractice) -> OrganizerAidPending {
    OrganizerAidPending {
        allocation: row.gift.commitment.command.allocation,
        dispatch_support: (&row.dispatch_support).into(),
        response: row.response.as_ref().map(owned_practice),
        lost_quantity: row.lost_quantity,
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
    catalog: &MaterialCatalog,
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
        let mandate = catalog
            .aid_mandates
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
        let food = food_projection(catalog, state, recurring, mandate, period)?;
        let controlled = config.collection.as_ref().is_some_and(|collection| {
            collection.actor_id == config.controlled_actor_id
                && matches!(mandate.payer, AccountId::Organization(id) if id.as_bytes() == collection.organization_account_id)
        });
        let funding = match economy.book.cash(mandate.payer) {
            Ok(cash) if controlled => OrganizerAidFunding::Organization {
                cash_micros: cash.micro_units(),
            },
            Ok(_) => OrganizerAidFunding::Mandated,
            Err(MonetaryError::UnknownAccount) => OrganizerAidFunding::Unavailable,
            Err(_) => return Err(refused()),
        };
        result.push(OrganizerMaterialAidPreview {
            kind: binding.kind,
            mandate_id: mandate.id,
            period,
            donor_id: mandate.donor.as_bytes(),
            recipient_actor_id: binding.partner.actor_id,
            good_id: mandate.good_id.as_bytes(),
            unit_id: mandate.unit_id.as_bytes(),
            food,
            funding,
            maximum_quantity: mandate.maximum_quantity,
            maximum_cash_micros: mandate.maximum_cash.micro_units(),
            initial_food_quantity: mandate.initial_quantity,
            initial_cash_micros: mandate.initial_cash.micro_units(),
            cash_receiving_consent: binding.cash_receiving_consent,
            coordination_hours: binding.coordination_hours,
            receiving_consent: binding.receiving_consent,
        });
    }
    Ok(result)
}
pub(crate) fn validate_selected(
    catalog: &MaterialCatalog,
    state: &MaterialCircuitState,
    config: &OrganizerConfig,
    period: u64,
    command: &OrganizerCommand,
) -> Result<()> {
    let OrganizerAllocation::Aid {
        food_quantity,
        cash_micros,
    } = command.allocation
    else {
        return Ok(());
    };
    let kind = match command.choice {
        OrganizerChoice::LocalAid => OrganizerAidKind::Local,
        OrganizerChoice::RemoteAid => OrganizerAidKind::Remote,
        _ => return Err(refused()),
    };
    let offers = projections(catalog, state, config, period)?;
    let offer = offers
        .iter()
        .find(|row| row.kind == kind)
        .ok_or_else(refused)?;
    if (food_quantity > 0 && offer.food.is_none())
        || (cash_micros > 0 && !offer.funding.available())
    {
        return Err(refused());
    }
    Ok(())
}

fn food_projection(
    catalog: &MaterialCatalog,
    state: &MaterialCircuitState,
    recurring: &RecurringEconomy,
    mandate: &AidMandate,
    period: u64,
) -> Result<Option<OrganizerAidFoodPreview>> {
    let Some(commodity) = catalog
        .commodities
        .iter()
        .find(|row| row.good_id == mandate.good_id && row.unit_id == mandate.unit_id)
    else {
        return Ok(None);
    };
    match babylon_material_circuit::validate_aid_food_wiring(catalog, state, mandate) {
        Ok(()) => {}
        Err(MaterialCircuitError::AidAuthority) => return Ok(None),
        Err(_) => return Err(refused()),
    }
    let (donor_stock, own_need) = pantry_amounts(catalog, recurring, mandate)?;
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
    let transport = transport(catalog, state, mandate.transport)?;
    Ok(Some(OrganizerAidFoodPreview {
        donor_stock,
        own_need,
        grams_per_unit: commodity.grams_per_unit().map_err(|_| refused())?,
        ordinary_offer,
        labor_unit_id: mandate.labor_unit_id.as_bytes(),
        fulfillment_hours_per_unit: mandate.hours_per_unit,
        time,
        transport,
    }))
}

fn pantry_amounts(
    catalog: &MaterialCatalog,
    recurring: &RecurringEconomy,
    mandate: &AidMandate,
) -> Result<(u64, u64)> {
    let cohort = recurring
        .households
        .iter()
        .find(|r| r.principal_id == mandate.donor)
        .ok_or_else(refused)?;
    let own_need = catalog
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
    principal: FinalDemandPrincipalId,
    unit: UnitId,
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
    catalog: &MaterialCatalog,
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
    for row in catalog
        .route_stages
        .iter()
        .filter(|r| r.route_id == route_id)
    {
        let capacities = state
            .route_stage_capacities
            .iter()
            .filter(|r| r.route_id == route_id && r.stage_index == row.stage_index)
            .map(|m| {
                Ok(OrganizerAidCapacity {
                    corridor_id: m.corridor_id.as_bytes(),
                    remaining_grams: remaining_capacity(catalog, state, m.corridor_id, departure)?,
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
pub(super) fn resolutions(entries: &OrganizerPeriodJournalEntries) -> Vec<OrganizerAidResolution> {
    entries
        .aid_receipts
        .iter()
        .filter(|r| r.practice.period == entries.period)
        .map(|r| OrganizerAidResolution {
            pending: pending(&r.authorization),
            support: (&r.support).into(),
            practice: owned_practice(&r.practice),
        })
        .collect()
}

fn remaining_capacity(
    catalog: &MaterialCatalog,
    state: &MaterialCircuitState,
    id: CorridorId,
    period: u64,
) -> Result<Option<u64>> {
    if let Some(row) = state
        .corridor_capacities
        .iter()
        .find(|r| r.corridor_id == id && r.period == period)
    {
        return Ok(Some(row.available_grams));
    }
    match &catalog.capacity_policy {
        CapacitySupply::FiniteSchedule => Ok(Some(0)),
        CapacitySupply::Rolling(supply) => {
            let Some(row) = supply.shared.iter().find(|r| r.corridor_id == id) else {
                return Ok(None);
            };
            let reserved = state
                .capacity_reservations
                .future
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
    use fmt::Formatter;
    use serde::{de, Deserializer, Serializer};
    use std::fmt;

    pub fn serialize<S: Serializer>(value: &i128, serializer: S) -> Result<S::Ok, S::Error> {
        serializer.serialize_str(&value.to_string())
    }

    pub fn deserialize<'de, D: Deserializer<'de>>(deserializer: D) -> Result<i128, D::Error> {
        struct Decimal;
        impl de::Visitor<'_> for Decimal {
            type Value = i128;
            fn expecting(&self, formatter: &mut Formatter<'_>) -> fmt::Result {
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
