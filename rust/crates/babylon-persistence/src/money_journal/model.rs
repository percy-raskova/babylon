//! Versioned monetary evidence with explicit cash and reserve namespaces.
use crate::observer_reader::CommittedMaterialReceipts;
use crate::observer_reader::ObserverEconomyError;
use babylon_material_circuit::{
    AccountId, CashTransferPurpose, MoneyLocation, MoneyTransferPurpose, MoneyTransferReceipt,
    OutboundOrderId,
};
use serde::{Deserialize, Serialize};
use std::fmt::Formatter;
use std::fmt::Result as FmtResult;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum JournalError {
    Target,
    TargetMismatch,
    Database,
    Schema,
    Authority,
    Range,
    Projection,
    CoverageAbsent,
    SourceChanged,
    Observer(ObserverEconomyError),
}
impl std::fmt::Display for JournalError {
    fn fmt(&self, formatter: &mut Formatter<'_>) -> FmtResult {
        write!(formatter, "money journal refused: {self:?}")
    }
}
impl std::error::Error for JournalError {}

/// Every monetary purpose is separate; only delivery settlement records a sale payment.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum MoneyPurpose {
    PurchaseReservation,
    DeliverySettlement,
    PurchaseRefund,
    ShiftReservation,
    WagePayment,
    ShiftCancellation,
    Tax,
    PublicTransfer,
    HouseholdTransfer,
    OwnershipDistribution,
    CapitalContribution,
    TransportService,
    MutualAid,
}
impl MoneyPurpose {
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::PurchaseReservation => "purchase_reservation",
            Self::DeliverySettlement => "delivery_settlement",
            Self::PurchaseRefund => "purchase_refund",
            Self::ShiftReservation => "shift_reservation",
            Self::WagePayment => "wage_payment",
            Self::ShiftCancellation => "shift_cancellation",
            Self::Tax => "tax",
            Self::PublicTransfer => "public_transfer",
            Self::HouseholdTransfer => "household_transfer",
            Self::OwnershipDistribution => "ownership_distribution",
            Self::CapitalContribution => "capital_contribution",
            Self::TransportService => "transport_service",
            Self::MutualAid => "mutual_aid",
        }
    }
    pub(super) fn parse(value: &str) -> Result<Self, JournalError> {
        match value {
            "purchase_reservation" => Ok(Self::PurchaseReservation),
            "delivery_settlement" => Ok(Self::DeliverySettlement),
            "purchase_refund" => Ok(Self::PurchaseRefund),
            "shift_reservation" => Ok(Self::ShiftReservation),
            "wage_payment" => Ok(Self::WagePayment),
            "shift_cancellation" => Ok(Self::ShiftCancellation),
            "tax" => Ok(Self::Tax),
            "public_transfer" => Ok(Self::PublicTransfer),
            "household_transfer" => Ok(Self::HouseholdTransfer),
            "ownership_distribution" => Ok(Self::OwnershipDistribution),
            "capital_contribution" => Ok(Self::CapitalContribution),
            "transport_service" => Ok(Self::TransportService),
            "mutual_aid" => Ok(Self::MutualAid),
            _ => Err(JournalError::Projection),
        }
    }
}

/// Reserve identities identify financial locations, never inferred economic counterparties.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum MoneyLocationKind {
    SiteCash,
    HouseholdCash,
    OrganizationCash,
    PublicCash,
    DeliveryReserve,
    LocalFinalDemandReserve,
    ServiceReserve,
    PayrollReserve,
}
impl MoneyLocationKind {
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::SiteCash => "site_cash",
            Self::HouseholdCash => "household_cash",
            Self::OrganizationCash => "organization_cash",
            Self::PublicCash => "public_cash",
            Self::DeliveryReserve => "delivery_reserve",
            Self::LocalFinalDemandReserve => "local_final_demand_reserve",
            Self::ServiceReserve => "service_reserve",
            Self::PayrollReserve => "payroll_reserve",
        }
    }
    pub(super) fn parse(value: &str) -> Result<Self, JournalError> {
        match value {
            "site_cash" => Ok(Self::SiteCash),
            "household_cash" => Ok(Self::HouseholdCash),
            "organization_cash" => Ok(Self::OrganizationCash),
            "public_cash" => Ok(Self::PublicCash),
            "delivery_reserve" => Ok(Self::DeliveryReserve),
            "local_final_demand_reserve" => Ok(Self::LocalFinalDemandReserve),
            "service_reserve" => Ok(Self::ServiceReserve),
            "payroll_reserve" => Ok(Self::PayrollReserve),
            _ => Err(JournalError::Projection),
        }
    }
}
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct MoneyEndpoint {
    pub kind: MoneyLocationKind,
    pub id: [u8; 32],
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum MoneyReferenceKind {
    Delivery,
    LocalFinalDemand,
    Service,
    Shift,
}
impl MoneyReferenceKind {
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Delivery => "delivery",
            Self::LocalFinalDemand => "local_final_demand",
            Self::Service => "service",
            Self::Shift => "shift",
        }
    }
    pub(super) fn parse(value: &str) -> Result<Self, JournalError> {
        match value {
            "delivery" => Ok(Self::Delivery),
            "local_final_demand" => Ok(Self::LocalFinalDemand),
            "service" => Ok(Self::Service),
            "shift" => Ok(Self::Shift),
            _ => Err(JournalError::Projection),
        }
    }
}
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct MoneyReference {
    pub kind: MoneyReferenceKind,
    pub id: [u8; 32],
}

/// The debit is exactly minus `amount_micros`, the credit exactly plus it.
/// A decimal string preserves i128 values in JSON consumers and SQL adapters.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct MoneyMovement {
    pub ordinal: u64,
    pub purpose: MoneyPurpose,
    pub reference: Option<MoneyReference>,
    pub debit: MoneyEndpoint,
    pub credit: MoneyEndpoint,
    pub amount_micros: String,
}

/// Exact SQL SUM across purpose totals; the sum can exceed i128 even when each transfer fits.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct MoneyTotal {
    pub purpose: MoneyPurpose,
    pub movement_count: u64,
    pub amount_micros: String,
}
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct PublishReport {
    pub period: u64,
    pub movement_count: u64,
    pub changed: bool,
}

fn order_reference(order: OutboundOrderId) -> MoneyReference {
    let (kind, id) = match order {
        OutboundOrderId::Delivery(id) => (MoneyReferenceKind::Delivery, id.as_bytes()),
        OutboundOrderId::LocalFinalDemand(id) => {
            (MoneyReferenceKind::LocalFinalDemand, id.as_bytes())
        }
        OutboundOrderId::Service(id) => (MoneyReferenceKind::Service, id.as_bytes()),
    };
    MoneyReference { kind, id }
}
fn endpoint(location: MoneyLocation) -> MoneyEndpoint {
    use MoneyLocationKind as K;
    let (kind, id) = match location {
        MoneyLocation::Cash(account) => match account {
            AccountId::Site(id) => (K::SiteCash, id.as_bytes()),
            AccountId::Household(id) => (K::HouseholdCash, id.as_bytes()),
            AccountId::Organization(id) => (K::OrganizationCash, id.as_bytes()),
            AccountId::Public(id) => (K::PublicCash, id.as_bytes()),
        },
        MoneyLocation::PurchaseReserve(order) => match order {
            OutboundOrderId::Delivery(id) => (K::DeliveryReserve, id.as_bytes()),
            OutboundOrderId::LocalFinalDemand(id) => (K::LocalFinalDemandReserve, id.as_bytes()),
            OutboundOrderId::Service(id) => (K::ServiceReserve, id.as_bytes()),
        },
        MoneyLocation::PayrollReserve(id) => (K::PayrollReserve, id.as_bytes()),
    };
    MoneyEndpoint { kind, id }
}
fn purpose(value: MoneyTransferPurpose) -> (MoneyPurpose, Option<MoneyReference>) {
    use MoneyPurpose as P;
    match value {
        MoneyTransferPurpose::PurchaseReservation(id) => {
            (P::PurchaseReservation, Some(order_reference(id)))
        }
        MoneyTransferPurpose::DeliverySettlement(id) => {
            (P::DeliverySettlement, Some(order_reference(id)))
        }
        MoneyTransferPurpose::PurchaseRefund(id) => (P::PurchaseRefund, Some(order_reference(id))),
        MoneyTransferPurpose::ShiftReservation(id) => (
            P::ShiftReservation,
            Some(MoneyReference {
                kind: MoneyReferenceKind::Shift,
                id: id.as_bytes(),
            }),
        ),
        MoneyTransferPurpose::WagePayment(id) => (
            P::WagePayment,
            Some(MoneyReference {
                kind: MoneyReferenceKind::Shift,
                id: id.as_bytes(),
            }),
        ),
        MoneyTransferPurpose::ShiftCancellation(id) => (
            P::ShiftCancellation,
            Some(MoneyReference {
                kind: MoneyReferenceKind::Shift,
                id: id.as_bytes(),
            }),
        ),
        MoneyTransferPurpose::Cash(value) => (
            match value {
                CashTransferPurpose::Tax => P::Tax,
                CashTransferPurpose::PublicTransfer => P::PublicTransfer,
                CashTransferPurpose::HouseholdTransfer => P::HouseholdTransfer,
                CashTransferPurpose::OwnershipDistribution => P::OwnershipDistribution,
                CashTransferPurpose::CapitalContribution => P::CapitalContribution,
                CashTransferPurpose::TransportService => P::TransportService,
                CashTransferPurpose::MutualAid => P::MutualAid,
            },
            None,
        ),
    }
}

/// Derive narrow facts in source receipt order; no party or sale is inferred from a reserve.
/// # Errors
/// Refuses inconsistent period identity, unbalanced postings or an unrepresentable ordinal.
pub fn derive_movements(
    source: &CommittedMaterialReceipts,
) -> Result<Vec<MoneyMovement>, JournalError> {
    if source.identity.resolve_tick() != source.receipts.resolve_tick {
        return Err(JournalError::SourceChanged);
    }
    movements(&source.receipts.money_transfers)
}
pub(super) fn movements(rows: &[MoneyTransferReceipt]) -> Result<Vec<MoneyMovement>, JournalError> {
    let mut result = Vec::with_capacity(rows.len());
    for (ordinal, row) in rows.iter().enumerate() {
        let amount = row.credit.delta.micro_units();
        if amount <= 0 || row.debit.delta.micro_units().checked_add(amount) != Some(0) {
            return Err(JournalError::Projection);
        }
        let (purpose, reference) = purpose(row.purpose);
        result.push(MoneyMovement {
            ordinal: u64::try_from(ordinal).map_err(|_| JournalError::Range)?,
            purpose,
            reference,
            debit: endpoint(row.debit.location),
            credit: endpoint(row.credit.location),
            amount_micros: amount.to_string(),
        });
    }
    Ok(result)
}
