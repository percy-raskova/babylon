//! PostgreSQL numeric inputs retain all integer currency micros and rational share weights.
use crate::money_journal::statement_storage;
use crate::money_journal::MoneyEndpoint;
use crate::national_economy::companies::{
    BeneficiaryClaim, CompanyBand, CompanyMember, CompanyPopulation, CompanyTreasury,
    MemberFunding, OriginalClaim,
};
use serde::Serialize;
#[derive(Serialize)]
pub(super) struct Parent {
    company_id: String,
    industry_key: &'static str,
    label: String,
    band: &'static str,
    division: Option<u8>,
    employed: u64,
    sites: u64,
    opening_cash_micros: String,
    subsidiary_capital_micros: String,
    original_capital_micros: String,
    common_denominator: String,
    total_weight: String,
}
impl Parent {
    pub(super) fn new(r: &CompanyPopulation, t: &CompanyTreasury) -> Self {
        let (band, division) = match r.key.band {
            CompanyBand::FirstNational => ("first_national", None),
            CompanyBand::SecondNational => ("second_national", None),
            CompanyBand::Regional(d) => ("regional", Some(d as u8)),
        };
        Self {
            company_id: statement_storage::bytea(&t.company.as_bytes()),
            industry_key: r.key.function.source_key(),
            label: r.key.label(),
            band,
            division,
            employed: r.employed,
            sites: r.sites,
            opening_cash_micros: t.cash.micro_units().to_string(),
            subsidiary_capital_micros: t.subsidiary_capital.micro_units().to_string(),
            original_capital_micros: t.original_capital.micro_units().to_string(),
            common_denominator: t.common_denominator.to_string(),
            total_weight: t.total_weight.to_string(),
        }
    }
}
#[derive(Serialize)]
pub(super) struct Member {
    company_id: String,
    site_id: String,
    county_geoid: String,
    opening_employed: u64,
    original_cash_micros: String,
    cash_floor_micros: String,
    swept_micros: String,
    remaining_cash_micros: String,
    original_capital_micros: String,
    remaining_capital_micros: String,
}
impl Member {
    pub(super) fn new(r: &CompanyMember, f: &MemberFunding) -> Self {
        Self {
            company_id: statement_storage::bytea(&f.company.as_bytes()),
            site_id: statement_storage::bytea(&r.site.as_bytes()),
            county_geoid: r.county.to_string(),
            opening_employed: r.employed,
            original_cash_micros: f.original_cash.micro_units().to_string(),
            cash_floor_micros: f.cash_floor.micro_units().to_string(),
            swept_micros: f.swept.micro_units().to_string(),
            remaining_cash_micros: f.remaining_cash.micro_units().to_string(),
            original_capital_micros: f.original_capital.micro_units().to_string(),
            remaining_capital_micros: f.remaining_capital.micro_units().to_string(),
        }
    }
}
#[derive(Serialize)]
pub(super) struct Claim {
    company_id: String,
    beneficiary_kind: &'static str,
    beneficiary_id: String,
    weight: String,
}
impl From<&BeneficiaryClaim> for Claim {
    fn from(r: &BeneficiaryClaim) -> Self {
        let owner = MoneyEndpoint::from(r.beneficiary);
        Self {
            company_id: statement_storage::bytea(&r.company.as_bytes()),
            beneficiary_kind: owner.kind.as_str(),
            beneficiary_id: statement_storage::bytea(&owner.id),
            weight: r.weight.to_string(),
        }
    }
}
#[derive(Serialize)]
pub(super) struct Source {
    company_id: String,
    site_id: String,
    beneficiary_kind: &'static str,
    beneficiary_id: String,
    original_shares: u64,
    site_total_shares: u64,
    capital_micros: String,
    original_carrying_micros: String,
}
impl From<&OriginalClaim> for Source {
    fn from(r: &OriginalClaim) -> Self {
        let owner = MoneyEndpoint::from(r.beneficiary);
        Self {
            company_id: statement_storage::bytea(&r.company.as_bytes()),
            site_id: statement_storage::bytea(&r.site.as_bytes()),
            beneficiary_kind: owner.kind.as_str(),
            beneficiary_id: statement_storage::bytea(&owner.id),
            original_shares: r.original_shares,
            site_total_shares: r.site_total_shares,
            capital_micros: r.capital.micro_units().to_string(),
            original_carrying_micros: r.original_carrying_value.micro_units().to_string(),
        }
    }
}
