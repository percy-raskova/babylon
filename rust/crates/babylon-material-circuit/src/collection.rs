//! Bounded voluntary household cash after reproduction/taxes, before distributions.
use crate::{
    AccountId, AidReceipt, CapitalContributionReceipt, CashTransferPurpose, CircuitAccounting,
    CommodityKind, FinalDemandPrincipalId, FinancialInstitutions, HouseholdConsumptionReceipt,
    HouseholdContributionUse, HouseholdServiceReceipt, HouseholdTimeReceipt, MaterialCircuitError,
    MaterialCircuitState, MoneyLocation, MoneyTransferPurpose, MoneyTransferReceipt,
    OrganizationAccountId, TaxReceipt, UnitId,
};
use babylon_kernel::{content_digest::sha256_of, currency::Currency};
type Result<T> = std::result::Result<T, MaterialCircuitError>;
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CollectionResolveInput {
    pub original_commitment_id: [u8; 32],
    pub command_nonce: [u8; 16],
    pub admitted_period: u64,
    pub resolve_period: u64,
    pub mandate_id: [u8; 32],
    pub source_hash: [u8; 32],
    pub actor_id: u64,
    pub contributor_id: u64,
    pub donor: FinalDemandPrincipalId,
    pub recipient: OrganizationAccountId,
    pub labor_unit_id: UnitId,
    pub cash_consent: bool,
    pub requested: Currency,
    pub protected_cash_floor: Currency,
    pub collection_hours: u64,
    pub pledged_hours: u64,
}
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[repr(u8)]
pub enum CollectionOutcome {
    Collected = 1,
    CashConsentRefused = 2,
    ProtectedConsumptionUnmet = 3,
    ProtectedServiceUnmet = 4,
    ProtectedClosingStockUnmet = 5,
    DuePaymentUnmet = 6,
    InsufficientCash = 7,
    InsufficientContributionTime = 8,
}
impl TryFrom<u8> for CollectionOutcome {
    type Error = MaterialCircuitError;
    fn try_from(tag: u8) -> Result<Self> {
        match tag {
            1 => Ok(Self::Collected),
            2 => Ok(Self::CashConsentRefused),
            3 => Ok(Self::ProtectedConsumptionUnmet),
            4 => Ok(Self::ProtectedServiceUnmet),
            5 => Ok(Self::ProtectedClosingStockUnmet),
            6 => Ok(Self::DuePaymentUnmet),
            7 => Ok(Self::InsufficientCash),
            8 => Ok(Self::InsufficientContributionTime),
            _ => Err(MaterialCircuitError::CollectionInvariant),
        }
    }
}
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CollectionReceipt {
    pub period: u64,
    pub admitted_period: u64,
    pub original_commitment_id: [u8; 32],
    pub command_nonce: [u8; 16],
    pub mandate_id: [u8; 32],
    pub source_hash: [u8; 32],
    pub actor_id: u64,
    pub contributor_id: u64,
    pub donor: FinalDemandPrincipalId,
    pub recipient: OrganizationAccountId,
    pub labor_unit_id: UnitId,
    pub requested: Currency,
    pub collected: Currency,
    pub performed_hours: u64,
    pub outcome: CollectionOutcome,
    pub transfer_ordinal: Option<u32>,
    pub contribution_use_id: [u8; 32],
}
/// Exact deterministic use identity; not a second hour allocator.
#[must_use]
pub fn collection_contribution_id(
    original: [u8; 32],
    mandate: [u8; 32],
    period: u64,
    actor: u64,
    contributor: u64,
    donor: FinalDemandPrincipalId,
    unit: UnitId,
) -> [u8; 32] {
    let mut bytes = b"babylon.collection-household-contribution.v1\0".to_vec();
    bytes.extend_from_slice(&original);
    bytes.extend_from_slice(&mandate);
    for value in [period, actor, contributor] {
        bytes.extend_from_slice(&value.to_be_bytes());
    }
    bytes.extend_from_slice(&donor.as_bytes());
    bytes.extend_from_slice(&unit.as_bytes());
    sha256_of(&bytes)
}
impl CollectionReceipt {
    /// Check complete actual/refusal identity; authority joins belong to the host.
    /// # Errors
    /// Refuses malformed periods, quantities, references and fabricated refusal work.
    pub fn validate(&self) -> Result<()> {
        let paid = self.outcome == CollectionOutcome::Collected;
        if self.period == 0
            || self.admitted_period.checked_add(1) != Some(self.period)
            || [
                self.original_commitment_id,
                self.mandate_id,
                self.source_hash,
                self.donor.as_bytes(),
                self.recipient.as_bytes(),
                self.labor_unit_id.as_bytes(),
            ]
            .contains(&[0; 32])
            || self.actor_id == 0
            || self.contributor_id == 0
            || self.requested.micro_units() <= 0
            || (paid
                && (self.collected != self.requested
                    || self.performed_hours == 0
                    || self.transfer_ordinal.is_none()
                    || self.transfer_ordinal == Some(u32::MAX)
                    || self.contribution_use_id
                        != collection_contribution_id(
                            self.original_commitment_id,
                            self.mandate_id,
                            self.period,
                            self.actor_id,
                            self.contributor_id,
                            self.donor,
                            self.labor_unit_id,
                        )))
            || (!paid
                && (self.collected.micro_units() != 0
                    || self.performed_hours != 0
                    || self.transfer_ordinal.is_some()
                    || self.contribution_use_id != [0; 32]))
        {
            return Err(MaterialCircuitError::CollectionInvariant);
        }
        Ok(())
    }
    /// Borrow the exact shared use already consumed by material close.
    #[must_use]
    pub fn contribution_use(&self) -> Option<HouseholdContributionUse> {
        (self.outcome == CollectionOutcome::Collected).then_some(HouseholdContributionUse {
            use_id: self.contribution_use_id,
            principal_id: self.donor,
            actor_id: self.actor_id,
            contributor_id: self.contributor_id,
            hours: self.performed_hours,
        })
    }
}
#[derive(Clone, Copy)]
pub(crate) struct CollectionEvidence<'a> {
    pub consumption: &'a [HouseholdConsumptionReceipt],
    pub services: &'a [HouseholdServiceReceipt],
    pub time: &'a [HouseholdTimeReceipt],
    pub taxes: &'a [TaxReceipt],
    pub contributions: &'a [CapitalContributionReceipt],
    pub aid: &'a [AidReceipt],
}
fn one<'a, T: 'a>(mut rows: impl Iterator<Item = &'a T>) -> Result<&'a T> {
    let row = rows
        .next()
        .ok_or(MaterialCircuitError::CollectionInvariant)?;
    if rows.next().is_some() {
        return Err(MaterialCircuitError::CollectionInvariant);
    }
    Ok(row)
}
fn protected(
    state: &MaterialCircuitState,
    input: &CollectionResolveInput,
    facts: &CollectionEvidence<'_>,
) -> Result<Option<CollectionOutcome>> {
    let CircuitAccounting::Monetary(e) = &state.accounting else {
        return Err(MaterialCircuitError::CollectionInvariant);
    };
    let recurring = e
        .recurring
        .as_ref()
        .ok_or(MaterialCircuitError::CollectionInvariant)?;
    let household = one(recurring
        .households
        .iter()
        .filter(|row| row.principal_id == input.donor))?;
    let mut outcome = None;
    let mut has_needs = false;
    for need in recurring
        .household_needs
        .iter()
        .filter(|row| row.principal_id == input.donor)
    {
        has_needs = true;
        let required = need.required_quantity(household)?;
        let commodity = one(state
            .commodities
            .iter()
            .filter(|row| row.good_id == need.good_id && row.unit_id == need.unit_id))?;
        match commodity.kind {
            CommodityKind::Storable { .. } => {
                let row = one(facts.consumption.iter().filter(|row| {
                    row.principal_id == input.donor
                        && row.good_id == need.good_id
                        && row.unit_id == need.unit_id
                }))?;
                if row.period != state.period
                    || row.required_quantity != required
                    || row.consumed_quantity.checked_add(row.unmet_quantity) != Some(required)
                {
                    return Err(MaterialCircuitError::CollectionInvariant);
                }
                if row.unmet_quantity > 0 {
                    outcome.get_or_insert(CollectionOutcome::ProtectedConsumptionUnmet);
                }
                let policy = one(recurring.household_purchases.iter().filter(|row| {
                    row.principal_id == input.donor
                        && row.good_id == need.good_id
                        && row.unit_id == need.unit_id
                }))?;
                let stock = one(recurring.household_stocks.iter().filter(|row| {
                    row.principal_id == input.donor
                        && row.good_id == need.good_id
                        && row.unit_id == need.unit_id
                }))?;
                if stock.quantity != row.closing_quantity {
                    return Err(MaterialCircuitError::CollectionInvariant);
                }
                if stock.quantity < policy.target_closing_stock {
                    outcome.get_or_insert(CollectionOutcome::ProtectedClosingStockUnmet);
                }
            }
            CommodityKind::PeriodService { .. } => {
                let row = one(facts.services.iter().filter(|row| {
                    row.principal_id == input.donor
                        && row.good_id == need.good_id
                        && row.unit_id == need.unit_id
                }))?;
                if row.period != state.period
                    || row.required_quantity != required
                    || row.satisfied_quantity.checked_add(row.unmet_quantity) != Some(required)
                {
                    return Err(MaterialCircuitError::CollectionInvariant);
                }
                if row.unmet_quantity > 0 {
                    outcome.get_or_insert(CollectionOutcome::ProtectedServiceUnmet);
                }
            }
        }
    }
    if !has_needs {
        return Err(MaterialCircuitError::CollectionInvariant);
    }
    protected_payments(
        &e.financial,
        AccountId::Household(input.donor),
        state.period,
        facts,
        &mut outcome,
    )?;
    Ok(outcome)
}

fn protected_payments(
    financial: &FinancialInstitutions,
    donor: AccountId,
    period: u64,
    facts: &CollectionEvidence<'_>,
    outcome: &mut Option<CollectionOutcome>,
) -> Result<()> {
    // Missing/duplicate/wrong-period tax evidence is corruption, not permission.
    for policy in financial.taxes.iter().filter(|row| row.payer == donor) {
        let tax = one(facts.taxes.iter().filter(|row| {
            row.payer == donor
                && row.public_recipient == policy.public_recipient
                && row.basis == policy.basis
        }))?;
        if tax.period != period || tax.rate_bps != policy.rate_bps {
            return Err(MaterialCircuitError::CollectionInvariant);
        }
        if tax.uncollected.micro_units() != 0 {
            outcome.get_or_insert(CollectionOutcome::DuePaymentUnmet);
        }
    }
    for row in facts
        .contributions
        .iter()
        .filter(|row| row.contributor == donor)
    {
        if row.period != period {
            return Err(MaterialCircuitError::CollectionInvariant);
        }
        if row.unfunded.micro_units() != 0 {
            outcome.get_or_insert(CollectionOutcome::DuePaymentUnmet);
        }
    }
    Ok(())
}

fn input_valid(state: &MaterialCircuitState, input: &CollectionResolveInput) -> Result<()> {
    if input.resolve_period != state.period
        || input.admitted_period.checked_add(1) != Some(input.resolve_period)
        || input.requested.micro_units() <= 0
        || input.protected_cash_floor.micro_units() < 0
        || input.collection_hours == 0
        || input.actor_id == 0
        || input.contributor_id == 0
        || [
            input.original_commitment_id,
            input.mandate_id,
            input.source_hash,
            input.donor.as_bytes(),
            input.recipient.as_bytes(),
            input.labor_unit_id.as_bytes(),
        ]
        .contains(&[0; 32])
    {
        return Err(MaterialCircuitError::CollectionInvariant);
    }
    let CircuitAccounting::Monetary(e) = &state.accounting else {
        return Err(MaterialCircuitError::CollectionInvariant);
    };
    if e.aid.mandates.iter().any(|row| row.id == input.mandate_id)
        || !e.aid.mandates.iter().any(|row| {
            row.donor == input.donor
                && row.donor_actor == input.actor_id
                && row.donor_contributor_id == input.contributor_id
                && row.labor_unit_id == input.labor_unit_id
                && row.payer == AccountId::Organization(input.recipient)
        })
    {
        return Err(MaterialCircuitError::CollectionInvariant);
    }
    e.book.cash(AccountId::Household(input.donor))?;
    e.book.cash(AccountId::Organization(input.recipient))?;
    Ok(())
}
fn incoming_gifts(money: &[MoneyTransferReceipt], donor: FinalDemandPrincipalId) -> Result<i128> {
    money
        .iter()
        .filter(|row| {
            matches!(
                row.purpose,
                MoneyTransferPurpose::Cash(CashTransferPurpose::MutualAid)
                    | MoneyTransferPurpose::AidGrant(_)
            ) && row.credit.location == MoneyLocation::Cash(AccountId::Household(donor))
        })
        .try_fold(0_i128, |sum, row| {
            sum.checked_add(row.credit.delta.micro_units())
                .ok_or(MaterialCircuitError::Arithmetic)
        })
}
fn frozen_outcomes(
    inputs: &[CollectionResolveInput],
    state: &MaterialCircuitState,
    money: &[MoneyTransferReceipt],
    facts: &CollectionEvidence<'_>,
) -> Result<Vec<Option<CollectionOutcome>>> {
    // Freeze eligibility before any collection and ownership payout. Even an
    // identical credit later in the tick cannot change this source snapshot.
    let mut frozen = Vec::with_capacity(inputs.len());
    let aid_uses = crate::aid::contribution_uses(state, facts.aid)?;
    for input in inputs {
        input_valid(state, input)?;
        let CircuitAccounting::Monetary(e) = &state.accounting else {
            return Err(MaterialCircuitError::CollectionInvariant);
        };
        let cash = e
            .book
            .cash(AccountId::Household(input.donor))?
            .micro_units()
            .checked_sub(incoming_gifts(money, input.donor)?)
            .and_then(|value| value.checked_sub(input.protected_cash_floor.micro_units()))
            .ok_or(MaterialCircuitError::Arithmetic)?;
        let time = one(facts
            .time
            .iter()
            .filter(|row| row.principal_id == input.donor))?;
        time.validate()?;
        if time.period != state.period || time.labor_unit_id != input.labor_unit_id {
            return Err(MaterialCircuitError::CollectionInvariant);
        }
        let spent = aid_uses
            .iter()
            .filter(|row| row.principal_id == input.donor)
            .try_fold(0_u64, |sum, row| {
                sum.checked_add(row.hours)
                    .ok_or(MaterialCircuitError::Arithmetic)
            })?;
        let residual = time
            .contribution_available_hours
            .checked_sub(spent)
            .ok_or(MaterialCircuitError::HouseholdTimeInvariant)?;
        let outcome = if !input.cash_consent {
            Some(CollectionOutcome::CashConsentRefused)
        } else if let Some(reason) = protected(state, input, facts)? {
            Some(reason)
        } else if cash < input.requested.micro_units() {
            Some(CollectionOutcome::InsufficientCash)
        } else if residual < input.collection_hours || input.pledged_hours < input.collection_hours
        {
            Some(CollectionOutcome::InsufficientContributionTime)
        } else {
            None
        };
        frozen.push(outcome);
    }
    Ok(frozen)
}

pub(crate) fn close(
    inputs: &[CollectionResolveInput],
    state: &mut MaterialCircuitState,
    costs: &mut crate::valuation::CostClose,
    money: &mut Vec<MoneyTransferReceipt>,
    facts: CollectionEvidence<'_>,
) -> Result<Vec<CollectionReceipt>> {
    if inputs.len() > 1 {
        return Err(MaterialCircuitError::RowLimit);
    }
    if inputs.is_empty() {
        return Ok(Vec::new());
    }
    let frozen = frozen_outcomes(inputs, state, money, &facts)?;
    let mut result = Vec::with_capacity(inputs.len());
    for (input, outcome) in inputs.iter().zip(frozen) {
        let mut row = CollectionReceipt {
            period: state.period,
            admitted_period: input.admitted_period,
            original_commitment_id: input.original_commitment_id,
            command_nonce: input.command_nonce,
            mandate_id: input.mandate_id,
            source_hash: input.source_hash,
            actor_id: input.actor_id,
            contributor_id: input.contributor_id,
            donor: input.donor,
            recipient: input.recipient,
            labor_unit_id: input.labor_unit_id,
            requested: input.requested,
            collected: Currency::from_micro_units(0),
            performed_hours: 0,
            outcome: outcome.unwrap_or(CollectionOutcome::Collected),
            transfer_ordinal: None,
            contribution_use_id: [0; 32],
        };
        if outcome.is_none() {
            let ordinal = u32::try_from(money.len()).map_err(|_| MaterialCircuitError::RowLimit)?;
            if ordinal == u32::MAX {
                return Err(MaterialCircuitError::RowLimit);
            }
            let CircuitAccounting::Monetary(e) = &mut state.accounting else {
                return Err(MaterialCircuitError::CollectionInvariant);
            };
            money.push(e.book.transfer_cash(
                AccountId::Household(input.donor),
                AccountId::Organization(input.recipient),
                input.requested,
                CashTransferPurpose::MutualAid,
            )?);
            costs.cash_gift(
                AccountId::Household(input.donor),
                AccountId::Organization(input.recipient),
                input.requested,
            )?;
            row.collected = input.requested;
            row.performed_hours = input.collection_hours;
            row.transfer_ordinal = Some(ordinal);
            row.contribution_use_id = collection_contribution_id(
                input.original_commitment_id,
                input.mandate_id,
                state.period,
                input.actor_id,
                input.contributor_id,
                input.donor,
                input.labor_unit_id,
            );
        }
        row.validate()?;
        result.push(row);
    }
    Ok(result)
}
