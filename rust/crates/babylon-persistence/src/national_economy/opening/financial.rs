//! Explicit budget and ownership opening assumptions, separate from source class.
use super::{amount, quantity, sum_amount, ActorContext, Builder, NationalOpeningError, Result};
use crate::national_household_allocation::HouseholdBudgetKey;
use babylon_kernel::{
    content_digest::sha256_of,
    currency::Currency,
    economic_identity::{EconomicFunction, QcewOwnership},
    economic_location::{EconomicLocation, ForeignCounterpart},
};
use babylon_material_circuit::{
    AccountId, CashAccount, DistributionPolicy, EquityCarryingValue, InstitutionLocation,
    OwnershipClaim, PublicAccountId, PublicAllocation, PublicBudget, PublicTransferTreatment,
    TaxBasis, TaxPolicy,
};
use std::collections::BTreeMap;

pub(super) fn wire(builder: &mut Builder<'_>) -> Result<()> {
    let mut reserve = BTreeMap::<
        (
            babylon_material_circuit::FinalDemandPrincipalId,
            EconomicLocation,
        ),
        u64,
    >::new();
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
    let mut budgets = BTreeMap::<EconomicLocation, Currency>::new();
    for household in &builder.opening.households {
        budgets.insert(household.location, Currency::from_micro_units(0));
        builder.opening.institutions.taxes.push(TaxPolicy {
            payer: AccountId::Household(household.principal_id),
            public_recipient: public(household.location),
            basis: TaxBasis::WageIncome,
            rate_bps: builder.policy.financial.wage_tax_bps,
            cash_floor: Currency::from_micro_units(0),
        });
    }
    household_support(builder, &reserve, &mut budgets)?;
    let private_owners = private_owners(builder)?;
    let actors: Vec<_> = builder.actors.values().cloned().collect();
    for actor in actors {
        ownership(builder, &actor, &private_owners)?;
        builder.opening.institutions.taxes.push(TaxPolicy {
            payer: AccountId::Site(actor.site_id),
            public_recipient: public(actor.location),
            basis: TaxBasis::PositiveOperatingIncome,
            rate_bps: builder.policy.financial.operating_income_tax_bps,
            cash_floor: payroll(builder, &actor)?,
        });
        if actor.function == EconomicFunction::PublicProvisioning {
            let grant = public_provider_grant(builder, &actor)?;
            if grant.micro_units() > 0 {
                builder
                    .opening
                    .institutions
                    .public_allocations
                    .push(PublicAllocation {
                        public_account: public(actor.location),
                        recipient: AccountId::Site(actor.site_id),
                        treatment: PublicTransferTreatment::ProviderOperatingGrant,
                        priority: 0,
                        amount_per_period: grant,
                    });
                add_budget(&mut budgets, actor.location, grant)?;
            }
        }
    }
    for (location, period_cap) in budgets {
        let account = public(location);
        builder.opening.institutional_cash.push(CashAccount {
            id: AccountId::Public(account),
            cash: amount(builder.policy.working_capital_periods, period_cap)?,
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
            });
    }
    Ok(())
}

fn household_support(
    builder: &mut Builder<'_>,
    reserves: &BTreeMap<
        (
            babylon_material_circuit::FinalDemandPrincipalId,
            EconomicLocation,
        ),
        u64,
    >,
    budgets: &mut BTreeMap<EconomicLocation, Currency>,
) -> Result<()> {
    let policy = &builder.policy.financial;
    if policy.reserve_food_support_periods == 0 {
        return Ok(());
    }
    let food = builder
        .commodity("food")?
        .price
        .as_ref()
        .ok_or(NationalOpeningError::Policy)?
        .clone();
    for ((principal, location), persons) in reserves {
        let scale = scale(builder, *location)?;
        let unit_price = food
            .scaled(scale)
            .map_err(|_| NationalOpeningError::Arithmetic)?
            .opening;
        let support = amount(
            quantity(*persons, policy.reserve_food_support_periods)?,
            unit_price,
        )?;
        if support.micro_units() == 0 {
            continue;
        }
        builder
            .opening
            .institutions
            .public_allocations
            .push(PublicAllocation {
                public_account: public(*location),
                recipient: AccountId::Household(*principal),
                treatment: PublicTransferTreatment::HouseholdIncomeSupport,
                priority: 1,
                amount_per_period: support,
            });
        add_budget(budgets, *location, support)?;
    }
    Ok(())
}

type PrivateOwners =
    BTreeMap<EconomicLocation, Vec<(babylon_material_circuit::FinalDemandPrincipalId, u64)>>;

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
    let remote = foreign_claim(actor);
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
                AccountId::Public(public(actor.location)),
                10_000 - remote_share,
            );
        } else {
            private_claims(
                builder,
                actor,
                actor.location,
                10_000 - remote_share,
                private_owners,
            )?;
        }
    }
    if remote_share > 0 {
        private_claims(
            builder,
            actor,
            remote.ok_or(NationalOpeningError::Policy)?,
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
    let period_cap = amount(1, site.opening_cash)?;
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

/// Two explicitly Designed reciprocal claims make location and remittance distinct.
fn foreign_claim(actor: &ActorContext) -> Option<EconomicLocation> {
    if matches!(actor.location, EconomicLocation::County(county) if county.geoid().as_bytes() == *b"26163")
        && actor.function == EconomicFunction::CapitalGoods
        && actor.source_ownership == Some(QcewOwnership::Private)
    {
        return Some(EconomicLocation::Foreign(ForeignCounterpart::Japan));
    }
    if actor.location == EconomicLocation::Foreign(ForeignCounterpart::Canada)
        && actor.function == EconomicFunction::CapitalGoods
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
                .entry(row.location)
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
    location: EconomicLocation,
    total_shares: u64,
    private_owners: &PrivateOwners,
) -> Result<()> {
    let recipients = private_owners
        .get(&location)
        .ok_or(NationalOpeningError::Identity)?;
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
    let mut cost = payroll(builder, actor)?;
    for (key, coefficient) in &recipe.inputs {
        let good = builder.commodity(key)?;
        let price = good
            .price
            .as_ref()
            .ok_or(NationalOpeningError::Policy)?
            .scaled(actor.price_scale_bps)
            .map_err(|_| NationalOpeningError::Arithmetic)?
            .opening;
        cost = sum_amount(
            cost,
            amount(quantity(actor.planned_batches, *coefficient)?, price)?,
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
    let receipts = amount(
        quantity(actor.planned_batches, recipe.output_units_per_batch)?,
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
    amount(
        quantity(actor.employee_persons, builder.policy.work_hours_per_person)?,
        actor.wage,
    )
}
fn scale(builder: &Builder<'_>, location: EconomicLocation) -> Result<u16> {
    match location {
        EconomicLocation::County(_) => Ok(10_000),
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
    budgets: &mut BTreeMap<EconomicLocation, Currency>,
    location: EconomicLocation,
    amount: Currency,
) -> Result<()> {
    let value = budgets
        .get_mut(&location)
        .ok_or(NationalOpeningError::Identity)?;
    *value = sum_amount(*value, amount)?;
    Ok(())
}
fn public(location: EconomicLocation) -> PublicAccountId {
    let mut bytes = b"NationalPublicProvisioningV1\0".to_vec();
    bytes.extend_from_slice(&location.canonical_bytes());
    PublicAccountId::from_bytes(sha256_of(&bytes))
}
