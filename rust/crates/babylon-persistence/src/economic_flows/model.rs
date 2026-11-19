//! Financial reporting identities bound to a material campaign foundation.
use crate::money_journal::MoneyEndpoint;
use crate::national_economy::companies::CompanyKey;
use crate::observer_reader::CommittedMaterialReceipts;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum EconomicFlowError {
    MonetaryBookMismatch,
    UnknownCashAccount,
    AccountGeographyMismatch,
    UnknownOrderPrincipal,
    UnknownShiftPrincipal,
    ConflictingPrincipal,
    InvalidPosting,
    ReceiptOrdinal,
}

pub(super) type FlowResult<T> = Result<T, EconomicFlowError>;

/// Original signed decimal degrees from the captured TIGER county record.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct CountyInternalPoint {
    pub longitude: String,
    pub latitude: String,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct FlowAccount {
    /// Controlling company of an admitted whole site or its own treasury.
    pub company: Option<CompanyKey>,
    pub account: MoneyEndpoint,
    /// The operating county, foreign counterpart or dependency, including a representative hub.
    pub location: Option<String>,
    /// Captured national representative membership, independently of the hub's county.
    pub catchment: Option<String>,
    /// Modeled operating function of a site. Other principals have no site function.
    pub industry: Option<String>,
    /// A county map anchor, never a surveyed site position.
    pub county_internal_point: Option<CountyInternalPoint>,
}

/// The ordinal joins the purpose and amount in this period's original custody movement.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Settlement {
    pub ordinal: u64,
    pub payer: MoneyEndpoint,
    pub recipient: MoneyEndpoint,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct EconomicPaymentPeriod {
    pub source: CommittedMaterialReceipts,
    pub accounts: Vec<FlowAccount>,
    pub settlements: Vec<Settlement>,
}
