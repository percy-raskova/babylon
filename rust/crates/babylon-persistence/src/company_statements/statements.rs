//! Legal and consolidated period statements. Currency values serialize as exact decimal micro-units.
use super::{CompanyBalance, CompanyEntry};
use babylon_kernel::currency::Currency;
use serde::de::Error;
use serde::{Deserialize, Deserializer, Serialize, Serializer};
pub(super) fn from_decimal<'de, D: Deserializer<'de>>(d: D) -> Result<Currency, D::Error> {
    let text = String::deserialize(d)?;
    let value = text.parse::<i128>().map_err(D::Error::custom)?;
    if value.to_string() != text {
        return Err(D::Error::custom("noncanonical micro-units"));
    }
    Ok(Currency::from_micro_units(value))
}
fn decimal<S: Serializer>(v: &Currency, s: S) -> Result<S::Ok, S::Error> {
    s.serialize_str(&v.micro_units().to_string())
}
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct CompanyIncome {
    #[serde(serialize_with = "decimal", deserialize_with = "from_decimal")]
    pub sales: Currency,
    #[serde(serialize_with = "decimal", deserialize_with = "from_decimal")]
    pub cost_of_goods_sold: Currency,
    #[serde(serialize_with = "decimal", deserialize_with = "from_decimal")]
    pub operating_expenses: Currency,
    #[serde(serialize_with = "decimal", deserialize_with = "from_decimal")]
    pub taxes: Currency,
    #[serde(serialize_with = "decimal", deserialize_with = "from_decimal")]
    pub other_income: Currency,
    #[serde(serialize_with = "decimal", deserialize_with = "from_decimal")]
    pub other_expenses: Currency,
    #[serde(serialize_with = "decimal", deserialize_with = "from_decimal")]
    pub profit: Currency,
    #[serde(serialize_with = "decimal", deserialize_with = "from_decimal")]
    pub distributions: Currency,
    #[serde(serialize_with = "decimal", deserialize_with = "from_decimal")]
    pub contributions: Currency,
}
impl Default for CompanyIncome {
    fn default() -> Self {
        let zero = Currency::from_micro_units(0);
        Self {
            sales: zero,
            cost_of_goods_sold: zero,
            operating_expenses: zero,
            taxes: zero,
            other_income: zero,
            other_expenses: zero,
            profit: zero,
            distributions: zero,
            contributions: zero,
        }
    }
}
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct CompanyCashFlow {
    #[serde(serialize_with = "decimal", deserialize_with = "from_decimal")]
    pub operating: Currency,
    #[serde(serialize_with = "decimal", deserialize_with = "from_decimal")]
    pub investing: Currency,
    #[serde(serialize_with = "decimal", deserialize_with = "from_decimal")]
    pub financing: Currency,
    #[serde(serialize_with = "decimal", deserialize_with = "from_decimal")]
    pub reserve_reclassification: Currency,
}
impl Default for CompanyCashFlow {
    fn default() -> Self {
        let zero = Currency::from_micro_units(0);
        Self {
            operating: zero,
            investing: zero,
            financing: zero,
            reserve_reclassification: zero,
        }
    }
}
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct CompanyEliminations {
    #[serde(serialize_with = "decimal", deserialize_with = "from_decimal")]
    pub opening_investments: Currency,
    #[serde(serialize_with = "decimal", deserialize_with = "from_decimal")]
    pub closing_investments: Currency,
    #[serde(serialize_with = "decimal", deserialize_with = "from_decimal")]
    pub opening_intercompany_claims: Currency,
    #[serde(serialize_with = "decimal", deserialize_with = "from_decimal")]
    pub closing_intercompany_claims: Currency,
    #[serde(serialize_with = "decimal", deserialize_with = "from_decimal")]
    pub distributions: Currency,
    #[serde(serialize_with = "decimal", deserialize_with = "from_decimal")]
    pub contributions: Currency,
    #[serde(serialize_with = "decimal", deserialize_with = "from_decimal")]
    pub sales: Currency,
    #[serde(serialize_with = "decimal", deserialize_with = "from_decimal")]
    pub seller_cost: Currency,
    #[serde(serialize_with = "decimal", deserialize_with = "from_decimal")]
    pub margin_created: Currency,
    #[serde(serialize_with = "decimal", deserialize_with = "from_decimal")]
    pub margin_realized: Currency,
    #[serde(serialize_with = "decimal", deserialize_with = "from_decimal")]
    pub opening_unrealized_margin: Currency,
    #[serde(serialize_with = "decimal", deserialize_with = "from_decimal")]
    pub closing_unrealized_margin: Currency,
}
impl Default for CompanyEliminations {
    fn default() -> Self {
        let zero = Currency::from_micro_units(0);
        Self {
            opening_investments: zero,
            closing_investments: zero,
            opening_intercompany_claims: zero,
            closing_intercompany_claims: zero,
            distributions: zero,
            contributions: zero,
            sales: zero,
            seller_cost: zero,
            margin_created: zero,
            margin_realized: zero,
            opening_unrealized_margin: zero,
            closing_unrealized_margin: zero,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct CompanyBookPeriod {
    pub opening: CompanyBalance,
    pub closing: CompanyBalance,
    pub income: CompanyIncome,
    pub cash_flow: CompanyCashFlow,
}
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct CompanyPeriod {
    pub company: String,
    pub parent: CompanyBookPeriod,
    pub subsidiaries: CompanyBookPeriod,
    pub consolidated: CompanyBookPeriod,
    pub eliminations: CompanyEliminations,
    pub entries: Vec<CompanyEntry>,
}
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct CompanyPeriodReport {
    pub version: u32,
    pub campaign: String,
    pub resolve_tick: u64,
    pub foundation_sha256: String,
    pub tick_content_hash: String,
    pub receipt_sha256: String,
    pub currency_unit: String,
    pub companies: Vec<CompanyPeriod>,
}
