//! Explicit budget and ownership opening assumptions, separate from source class.
use super::{fund, templates, ActorContext, Builder, NationalOpeningError, Result};
use crate::national_economy::grain::NationalGrainError;
use crate::national_economy::NationalGamePolicy;
use crate::national_household_allocation::HouseholdBudgetKey;
use babylon_kernel::currency::Currency;
use babylon_kernel::economic_identity::{EconomicFunction, QcewOwnership, TradeSet};
use babylon_kernel::economic_location::{EconomicLocation, ForeignCounterpart};
use babylon_material_circuit::PublicSpendingRule;

use crate::national_economy::grain::FinancialDomainId;
use babylon_material_circuit::FinalDemandPrincipalId;
use babylon_material_circuit::{
    AccountId, CashAccount, DistributionPolicy, EquityCarryingValue, InstitutionLocation,
    OwnershipClaim, PublicAllocation, PublicBudget, PublicTransferTreatment, SiteId, TaxBasis,
    TaxPolicy,
};
use std::collections::BTreeMap;

pub(super) fn wire(builder: &mut Builder<'_>) -> Result<()> {
    fund::check_share_table(builder)?;
    let mut reserve = BTreeMap::<(FinalDemandPrincipalId, EconomicLocation), u64>::new();
    for member in builder
        .opening
        .staffing
        .iter()
        .flat_map(|pool| &pool.members)
    {
        let count = reserve
            .entry((member.member.household_id(), member.member.residence()))
            .or_default();
        *count = count
            .checked_add(member.reserve)
            .ok_or(NationalOpeningError::Arithmetic)?;
    }
    let mut budgets = BTreeMap::<FinancialDomainId, Currency>::new();
    let accounts: Vec<_> = builder
        .opening
        .households
        .iter()
        .map(|household| (household.principal_id, household.location))
        .collect();
    for (principal, location) in accounts {
        budgets.insert(
            builder.domain(AccountId::Household(principal), location)?,
            Currency::from_micro_units(0),
        );
        push_tax(
            builder,
            AccountId::Household(principal),
            location,
            TaxBasis::WageIncome,
            Currency::from_micro_units(0),
        )?;
    }
    household_support(builder, &reserve, &mut budgets)?;
    let private_owners = private_owners(builder)?;
    let actors: Vec<_> = builder.actors.values().cloned().collect();
    let mut grants = Vec::new();
    for actor in actors {
        ownership(builder, &actor, &private_owners)?;
        push_tax(
            builder,
            AccountId::Site(actor.site_id),
            actor.location,
            TaxBasis::PositiveOperatingIncome,
            payroll(builder, &actor)?,
        )?;
        if actor.function == EconomicFunction::PublicProvisioning {
            let grant = public_provider_grant(builder, &actor)?;
            if grant.micro_units() > 0 {
                grants.push((
                    builder.domain(AccountId::Site(actor.site_id), actor.location)?,
                    actor.site_id,
                    grant,
                ));
            }
        }
    }
    provider_grants(builder, &grants, &mut budgets)?;
    public_accounts(builder, budgets)?;
    Ok(())
}

/// One tax row of a payer to its part's body at the scenario's rate. Under schema 8 a domestic payer's rate
/// is split between its part's body and the national fund by the part's share (`fund::split_rate`).
fn push_tax(
    builder: &mut Builder<'_>,
    payer: AccountId,
    location: EconomicLocation,
    basis: TaxBasis,
    cash_floor: Currency,
) -> Result<()> {
    let rate_bps = match basis {
        TaxBasis::WageIncome => builder.policy.financial.wage_tax_bps,
        TaxBasis::PositiveOperatingIncome => builder.policy.financial.operating_income_tax_bps,
    };
    let domain = builder.domain(payer, location)?;
    let fund_share = match (&builder.policy.fund, location) {
        (Some(fund), EconomicLocation::County(_)) => Some(fund::fund_share(
            fund,
            &templates::part_label(domain),
            basis,
        )?),
        _ => None,
    };
    let (place_rate, fund_rate) =
        fund_share.map_or((rate_bps, 0), |share| fund::split_rate(rate_bps, share));
    let taxes = &mut builder.opening.institutions.taxes;
    taxes.push(TaxPolicy {
        payer,
        public_recipient: domain.public_account(),
        basis,
        rate_bps: place_rate,
        cash_floor,
    });
    if fund_rate > 0 {
        taxes.push(TaxPolicy {
            payer,
            public_recipient: fund::fund_account(),
            basis,
            rate_bps: fund_rate,
            cash_floor,
        });
    }
    Ok(())
}

/// Each funded public provider's grant, from its part's own body at priority 0; where the scenario has a
/// place grant for the part, the fund pays the provider its part of the row and the body pays that much less.
fn provider_grants(
    builder: &mut Builder<'_>,
    grants: &[(FinancialDomainId, SiteId, Currency)],
    budgets: &mut BTreeMap<FinancialDomainId, Currency>,
) -> Result<()> {
    let from_fund = fund::place_grant_parts(builder, grants)?;
    for (domain, site, grant) in grants {
        let part = from_fund
            .get(site)
            .copied()
            .unwrap_or_else(|| Currency::from_micro_units(0));
        if part.micro_units() > 0 {
            builder
                .opening
                .institutions
                .public_allocations
                .push(PublicAllocation {
                    public_account: fund::fund_account(),
                    recipient: AccountId::Site(*site),
                    treatment: PublicTransferTreatment::ProviderOperatingGrant,
                    priority: fund::PLACE_GRANT_PRIORITY,
                    amount_per_period: part,
                });
        }
        let own = Currency::from_micro_units(
            grant
                .micro_units()
                .checked_sub(part.micro_units())
                .ok_or(NationalOpeningError::Arithmetic)?,
        );
        if own.micro_units() > 0 {
            builder
                .opening
                .institutions
                .public_allocations
                .push(PublicAllocation {
                    public_account: domain.public_account(),
                    recipient: AccountId::Site(*site),
                    treatment: PublicTransferTreatment::ProviderOperatingGrant,
                    priority: 0,
                    amount_per_period: own,
                });
            add_budget(budgets, *domain, own)?;
        }
    }
    Ok(())
}

fn public_accounts(
    builder: &mut Builder<'_>,
    budgets: BTreeMap<FinancialDomainId, Currency>,
) -> Result<()> {
    for (domain, period_cap) in budgets {
        let account = domain.public_account();
        let location = domain.location;
        builder.opening.institutional_cash.push(CashAccount {
            id: AccountId::Public(account),
            cash: super::amount(builder.policy.working_capital_periods, period_cap)?,
        });
        builder
            .opening
            .institutions
            .locations
            .push(InstitutionLocation {
                account: AccountId::Public(account),
                location,
            });
        builder
            .opening
            .institutions
            .public_budgets
            .push(PublicBudget {
                public_account: account,
                period_cap,
                cash_floor: Currency::from_micro_units(0),
                rule: PublicSpendingRule::CappedInOrder,
            });
    }
    Ok(())
}

fn household_support(
    builder: &mut Builder<'_>,
    reserves: &BTreeMap<(FinalDemandPrincipalId, EconomicLocation), u64>,
    budgets: &mut BTreeMap<FinancialDomainId, Currency>,
) -> Result<()> {
    let policy = &builder.policy.financial;
    if policy.reserve_food_support_periods == 0 {
        return Ok(());
    }
    for ((principal, location), persons) in reserves {
        let scale = scale(builder, *location)?;
        let unit_price = support_unit_price(builder.policy, scale)?;
        let support = super::amount(*persons, unit_price)?;
        if support.micro_units() == 0 {
            continue;
        }
        builder
            .opening
            .institutions
            .public_allocations
            .push(PublicAllocation {
                public_account: builder
                    .domain(AccountId::Household(*principal), *location)?
                    .public_account(),
                recipient: AccountId::Household(*principal),
                treatment: PublicTransferTreatment::HouseholdIncomeSupport,
                priority: 1,
                amount_per_period: support,
            });
        add_budget(
            budgets,
            builder.domain(AccountId::Household(*principal), *location)?,
            support,
        )?;
    }
    Ok(())
}

/// What the county's household support pays for one job-seeking person for one period: the food
/// price at the given scale times the periods of food the policy supports. Under schema 8 a period of
/// food is the food need's units a person (one period of one person's food need); before, one unit. A
/// county's scale is 10,000 basis points.
pub(in crate::national_economy) fn support_unit_price(
    policy: &NationalGamePolicy,
    scale_bps: u16,
) -> Result<Currency> {
    let food = policy
        .commodities
        .get("food")
        .and_then(|commodity| commodity.price.as_ref())
        .ok_or(NationalOpeningError::Policy)?;
    let price = food
        .scaled(scale_bps)
        .map_err(|_| NationalOpeningError::Arithmetic)?
        .opening;
    let units = if policy.fund.is_some() {
        policy
            .household_needs
            .iter()
            .find(|need| need.key == "food")
            .ok_or(NationalOpeningError::Policy)?
            .units_per_basis
    } else {
        1
    };
    super::amount(
        super::quantity(policy.financial.reserve_food_support_periods, units)?,
        price,
    )
}

/// The support unit of a domestic county.
pub(in crate::national_economy) fn county_support_unit_price(
    policy: &NationalGamePolicy,
) -> Result<Currency> {
    support_unit_price(policy, COUNTY_PRICE_SCALE_BPS)
}

/// A county's prices are the policy's own: no scale.
const COUNTY_PRICE_SCALE_BPS: u16 = 10_000;

type PrivateOwners = BTreeMap<FinancialDomainId, Vec<(FinalDemandPrincipalId, u64)>>;

fn ownership(
    builder: &mut Builder<'_>,
    actor: &ActorContext,
    private_owners: &PrivateOwners,
) -> Result<()> {
    let is_public = actor
        .source_ownership
        .is_some_and(|owner| owner != QcewOwnership::Private)
        || (actor.source_ownership.is_none()
            && actor.function == EconomicFunction::PublicProvisioning);
    let remote = foreign_claim(builder.policy.trades, actor);
    let remote_share = if remote.is_some() {
        u64::from(builder.policy.financial.cross_border_ownership_bps)
    } else {
        0
    };
    if remote_share < 10_000 {
        if is_public {
            claim(
                builder,
                actor,
                AccountId::Public(
                    builder
                        .domain(AccountId::Site(actor.site_id), actor.location)?
                        .public_account(),
                ),
                10_000 - remote_share,
            );
        } else {
            private_claims(
                builder,
                actor,
                builder.domain(AccountId::Site(actor.site_id), actor.location)?,
                10_000 - remote_share,
                private_owners,
            )?;
        }
    }
    if remote_share > 0 {
        private_claims(
            builder,
            actor,
            FinancialDomainId::detailed(remote.ok_or(NationalOpeningError::Policy)?),
            remote_share,
            private_owners,
        )?;
    }
    let cash_floor = payroll(builder, actor)?;
    let site = builder
        .sites
        .get(&actor.site_id)
        .and_then(|i| builder.opening.sites.get(*i))
        .ok_or(NationalOpeningError::Identity)?;
    let period_cap = super::amount(1, site.opening_cash)?;
    builder
        .opening
        .institutions
        .distributions
        .push(DistributionPolicy {
            issuer_site_id: actor.site_id,
            earnings_fraction_bps: if is_public {
                10_000
            } else {
                builder.policy.financial.private_distribution_bps
            },
            period_cap,
            cash_floor,
        });
    Ok(())
}
fn claim(builder: &mut Builder<'_>, actor: &ActorContext, beneficiary: AccountId, shares: u64) {
    builder.opening.institutions.ownership.push(OwnershipClaim {
        issuer_site_id: actor.site_id,
        beneficiary,
        shares,
    });
    // Zero is an explicit opening historical basis, not a market valuation of ownership.
    builder.opening.equity.push(EquityCarryingValue {
        owner: beneficiary,
        issuer_site_id: actor.site_id,
        amount: Currency::from_micro_units(0),
    });
}

/// The trade whose private plants in Wayne carry Japan's claim, and whose plants in Canada carry Wayne's.
pub(super) const fn claimed_plants(trades: TradeSet) -> EconomicFunction {
    match trades {
        TradeSet::Ten => EconomicFunction::CapitalGoods,
        TradeSet::Twelve => EconomicFunction::ConsumerGoods,
    }
}

/// Two explicitly Designed reciprocal claims make location and remittance distinct.
fn foreign_claim(trades: TradeSet, actor: &ActorContext) -> Option<EconomicLocation> {
    let plants = claimed_plants(trades);
    if matches!(actor.location, EconomicLocation::County(county) if county.geoid().as_bytes() == *b"26163")
        && actor.function == plants
        && actor.source_ownership == Some(QcewOwnership::Private)
    {
        return Some(EconomicLocation::Foreign(ForeignCounterpart::Japan));
    }
    if actor.location == EconomicLocation::Foreign(ForeignCounterpart::Canada)
        && actor.function == plants
    {
        return "county:26163".parse().ok();
    }
    None
}

fn private_owners(builder: &Builder<'_>) -> Result<PrivateOwners> {
    let mut by_location = PrivateOwners::new();
    for row in &builder.opening.households {
        let key = builder
            .household_keys
            .get(&row.principal_id)
            .ok_or(NationalOpeningError::Identity)?;
        if key.owner_exposure() || *key == HouseholdBudgetKey::PooledExternal {
            by_location
                .entry(builder.domain(AccountId::Household(row.principal_id), row.location)?)
                .or_default()
                .push((row.principal_id, row.households));
        }
    }
    for recipients in by_location.values_mut() {
        recipients.sort_unstable_by_key(|row| row.0);
    }
    Ok(by_location)
}

fn private_claims(
    builder: &mut Builder<'_>,
    actor: &ActorContext,
    location: FinancialDomainId,
    total_shares: u64,
    private_owners: &PrivateOwners,
) -> Result<()> {
    let recipients = private_owners
        .get(&location)
        .ok_or(NationalOpeningError::Grain(
            NationalGrainError::MissingOwnerBudget(location),
        ))?;
    let weights: Vec<_> = recipients.iter().map(|row| row.1).collect();
    let shares = crate::national_resident_allocation::apportion(total_shares, &weights)
        .map_err(NationalOpeningError::Workforce)?;
    for ((principal, _), shares) in recipients.iter().copied().zip(shares) {
        if shares > 0 {
            claim(builder, actor, AccountId::Household(principal), shares);
        }
    }
    Ok(())
}

fn public_provider_grant(builder: &Builder<'_>, actor: &ActorContext) -> Result<Currency> {
    let recipe = builder
        .policy
        .recipes
        .get(&actor.function)
        .ok_or(NationalOpeningError::Policy)?;
    let mut cost = super::sum_amount(
        payroll(builder, actor)?,
        super::equipment::wear_per_period(builder, actor)?,
    )?;
    for (key, coefficient) in &recipe.inputs {
        let good = builder.commodity(key)?;
        let price = good
            .price
            .as_ref()
            .ok_or(NationalOpeningError::Policy)?
            .scaled(actor.price_scale_bps)
            .map_err(|_| NationalOpeningError::Arithmetic)?
            .opening;
        cost = super::sum_amount(
            cost,
            super::amount(super::quantity(actor.planned_batches, *coefficient)?, price)?,
        )?;
    }
    let output = builder.commodity(&recipe.output)?;
    let fee = output
        .price
        .as_ref()
        .ok_or(NationalOpeningError::Policy)?
        .scaled(actor.price_scale_bps)
        .map_err(|_| NationalOpeningError::Arithmetic)?
        .opening;
    let receipts = super::amount(
        super::quantity(actor.planned_batches, recipe.output_units_per_batch)?,
        fee,
    )?;
    Ok(Currency::from_micro_units(
        cost.micro_units()
            .checked_sub(receipts.micro_units())
            .ok_or(NationalOpeningError::Arithmetic)?
            .max(0),
    ))
}
fn payroll(builder: &Builder<'_>, actor: &ActorContext) -> Result<Currency> {
    super::amount(
        super::quantity(actor.employee_persons, builder.policy.work_hours_per_person)?,
        actor.wage,
    )
}
fn scale(builder: &Builder<'_>, location: EconomicLocation) -> Result<u16> {
    match location {
        EconomicLocation::County(_) => Ok(COUNTY_PRICE_SCALE_BPS),
        EconomicLocation::Foreign(counterpart) => builder
            .policy
            .counterparts
            .get(&counterpart)
            .map(|p| p.price_scale_bps)
            .ok_or(NationalOpeningError::Policy),
        EconomicLocation::Dependency(_) => Ok(builder.policy.dependency.profile.price_scale_bps),
    }
}
fn add_budget(
    budgets: &mut BTreeMap<FinancialDomainId, Currency>,
    location: FinancialDomainId,
    amount: Currency,
) -> Result<()> {
    let value = budgets
        .get_mut(&location)
        .ok_or(NationalOpeningError::Identity)?;
    *value = super::sum_amount(*value, amount)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::{claimed_plants, county_support_unit_price};
    use crate::national_economy::NationalGamePolicy;
    use babylon_kernel::economic_identity::{EconomicFunction, TradeSet};

    #[test]
    fn the_car_plants_carry_the_claims() {
        assert_eq!(
            claimed_plants(TradeSet::Ten),
            EconomicFunction::CapitalGoods
        );
        assert_eq!(
            claimed_plants(TradeSet::Twelve),
            EconomicFunction::ConsumerGoods
        );
    }

    const FIXTURE: &str =
        include_str!("../../../tests/fixtures/national_twelve_trades.defines.toml");
    const SHIPPED: &str = include_str!("../../../../../../content/scenarios/national/defines.toml");

    #[test]
    fn the_support_unit_is_a_period_of_the_food_need() {
        let food = "good = \"food\"\nbasis = \"persons\"\nunits_per_basis = ";
        let price = |text: &str| {
            let policy = NationalGamePolicy::parse(text).expect("the text admits");
            let unit = county_support_unit_price(&policy).expect("a unit");
            let periods = policy.financial.reserve_food_support_periods;
            let opening = policy.commodities["food"]
                .price
                .as_ref()
                .expect("a price")
                .opening;
            (unit.micro_units(), periods, opening.micro_units())
        };
        let (unit, periods, opening) = price(FIXTURE);
        assert_eq!(unit, i128::from(periods) * opening);
        let two = FIXTURE.replacen(&format!("{food}1"), &format!("{food}2"), 1);
        assert_ne!(two, FIXTURE);
        let (unit, periods, opening) = price(&two);
        assert_eq!(unit, 2 * i128::from(periods) * opening);
        // Schema 7 and earlier keep one unit of food.
        let (unit, periods, opening) = price(SHIPPED);
        assert_eq!(unit, i128::from(periods) * opening);
    }
}
