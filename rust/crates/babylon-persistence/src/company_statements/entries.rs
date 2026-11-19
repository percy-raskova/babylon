//! Immediate source identities for eliminations and realization on an outside disposition.
use crate::money_journal::MoneyEndpoint;
use crate::qualification_audit::trade;
use babylon_kernel::currency::Currency;
use babylon_material_circuit::AccountId;
use serde::{Deserialize, Serialize};

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum CompanyEntryKind {
    InternalSale,
    ExternalSale,
    Expense,
    Contribution,
    Dividend,
}
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct CompanyEntry {
    pub family: u8,
    pub ordinal: u64,
    pub kind: CompanyEntryKind,
    pub from_kind: String,
    pub from_id: String,
    pub to_kind: Option<String>,
    pub to_id: Option<String>,
    pub amount_micros: String,
    pub legal_cost_micros: String,
    pub group_cost_micros: String,
    pub margin_created_micros: String,
    pub margin_realized_micros: String,
}
impl CompanyEntry {
    pub(super) fn new(
        family: u8,
        ordinal: usize,
        kind: CompanyEntryKind,
        from: AccountId,
        to: Option<AccountId>,
        amount: Currency,
    ) -> Self {
        let source = MoneyEndpoint::from(from);
        let destination = to.map(MoneyEndpoint::from);
        Self {
            family,
            ordinal: ordinal as u64,
            kind,
            from_kind: source.kind.as_str().to_owned(),
            from_id: trade::hex(&source.id),
            to_kind: destination.as_ref().map(|v| v.kind.as_str().to_owned()),
            to_id: destination.map(|v| trade::hex(&v.id)),
            amount_micros: amount.micro_units().to_string(),
            legal_cost_micros: "0".into(),
            group_cost_micros: "0".into(),
            margin_created_micros: "0".into(),
            margin_realized_micros: "0".into(),
        }
    }
}
