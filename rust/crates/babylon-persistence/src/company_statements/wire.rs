//! Exact decimal micro-units and stable catalog identities on the public read boundary.
use super::{CompanyBalance, CompanyOpening, CompanyOpeningReport, EliminatedMember};
use crate::michigan_economy;
use crate::national_economy::companies::CompanyBand;
use serde::{Serialize, Serializer};
use serde_json::json;

impl Serialize for CompanyBalance {
    fn serialize<S: Serializer>(&self, serializer: S) -> Result<S::Ok, S::Error> {
        json!({
            "cash": self.cash.micro_units().to_string(),
            "reserves": self.reserves.micro_units().to_string(),
            "receivables": self.receivables.micro_units().to_string(),
            "inventory": self.inventory.micro_units().to_string(),
            "freight": self.freight.micro_units().to_string(),
            "equipment": self.equipment.micro_units().to_string(),
            "investments": self.investments.micro_units().to_string(),
            "assets": self.assets.micro_units().to_string(),
            "liabilities": self.liabilities.micro_units().to_string(),
            "equity": self.equity.micro_units().to_string(),
            "retained_earnings": self.retained_earnings.micro_units().to_string(),
        })
        .serialize(serializer)
    }
}
impl Serialize for EliminatedMember {
    fn serialize<S: Serializer>(&self, serializer: S) -> Result<S::Ok, S::Error> {
        json!({
            "site": michigan_economy::digest_hex(&self.site.as_bytes()),
            "cash": self.cash.micro_units().to_string(),
            "eliminated_investment": self.investment.micro_units().to_string(),
        })
        .serialize(serializer)
    }
}
impl Serialize for CompanyOpening {
    fn serialize<S: Serializer>(&self, serializer: S) -> Result<S::Ok, S::Error> {
        let (band, division) = match self.key.band {
            CompanyBand::FirstNational => ("first_national", None),
            CompanyBand::SecondNational => ("second_national", None),
            CompanyBand::Regional(d) => ("regional", Some(d as u8)),
        };
        json!({
            "company": michigan_economy::digest_hex(&self.company.as_bytes()),
            "function": self.key.function.source_key(),
            "band": band,
            "census_division": division,
            "parent": self.parent,
            "subsidiaries": self.subsidiaries,
            "eliminated_member_investment": self.eliminated_member_investment.micro_units().to_string(),
            "consolidated": self.consolidated,
            "members": self.members,
        })
        .serialize(serializer)
    }
}
impl Serialize for CompanyOpeningReport {
    fn serialize<S: Serializer>(&self, serializer: S) -> Result<S::Ok, S::Error> {
        json!({
            "version": 1,
            "campaign": self.campaign.as_uuid().to_string(),
            "foundation_sha256": michigan_economy::digest_hex(&self.foundation),
            "resolve_tick": 0,
            "currency_unit": "micro",
            "companies": self.companies,
        })
        .serialize(serializer)
    }
}
