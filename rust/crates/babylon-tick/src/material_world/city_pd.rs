//! Resolver-bound private opponent state for the material register.

use babylon_graph::dossier::Dossier;
use babylon_kernel::currency::Currency;
use babylon_kernel::economic_location::EconomicLocation;
use babylon_practice_contract::CityPdCase;
use babylon_practice_contract::CityPdCaseSource;
use std::collections::BTreeSet;
use std::fmt::{Formatter, Result as FmtResult};

use babylon_graph::stable_element::{StableElementKey, StableElementResolver};
use babylon_kernel::content_digest;
use babylon_material_circuit::{
    AccountId, AgencyAttendanceOutcome, AgencyObservationFundingReceipt, CircuitAccounting,
    FinalDemandPrincipalId, MaterialCatalog, MaterialCircuitState, OrganizationAccountId,
    PublicAccountId, PublicTransferTreatment,
};
use babylon_practice_contract::{
    CityPdCaseStatus, CityPdConfig, CityPdDecision, CityPdDecisionReceipt, CityPdOutcome,
    CityPdReceipt, CITY_PD_MAX_ROWS,
};

use crate::state_opponent::{self, CityPdState};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CityPdRegisterError {
    Binding,
    Account,
    Period,
    Decision,
    History,
    Framing,
    Limit,
}

impl std::fmt::Display for CityPdRegisterError {
    fn fmt(&self, formatter: &mut Formatter<'_>) -> FmtResult {
        write!(formatter, "City PD register refused: {self:?}")
    }
}
impl std::error::Error for CityPdRegisterError {}

/// Exact private beliefs and retained evidence, never a second truth graph.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CityPdRegister {
    pub config: CityPdConfig,
    pub state: CityPdState,
    pub bindings: Vec<(u64, StableElementKey)>,
    pub attempts: Vec<CityPdAttempt>,
}

/// Original admitted decision and actual detached outcome for one visit attempt.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CityPdAttempt {
    pub decision: CityPdDecisionReceipt,
    pub funding: AgencyObservationFundingReceipt,
    pub receipt: CityPdReceipt,
}

/// Handle-free original decision evidence; never an admitted live register.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DecodedCityPdAttemptEvidence {
    pub config: CityPdConfig,
    pub cases: Vec<CityPdCase>,
    pub last_decision: CityPdDecisionReceipt,
    pub attempts: Vec<CityPdAttempt>,
}

impl CityPdRegister {
    pub(crate) fn decide_next(
        &mut self,
        catalog: &MaterialCatalog,
        material: &MaterialCircuitState,
        tick: u64,
        resolver: &StableElementResolver,
    ) -> Result<(), CityPdRegisterError> {
        let CircuitAccounting::Monetary(money) = &material.accounting else {
            return Err(CityPdRegisterError::Account);
        };
        let cash = money
            .book
            .cash(AccountId::Organization(OrganizationAccountId::from_bytes(
                self.config.agency_account_id,
            )))
            .map_err(|_| CityPdRegisterError::Account)?;
        self.state.last_decision = Some(
            state_opponent::decide_city_pd(
                &self.config,
                &self.state,
                resolver,
                &self.bindings,
                cash,
                tick,
            )
            .map_err(|_| CityPdRegisterError::Decision)?,
        );
        self.validate(catalog, material, tick, resolver)
    }

    /// Construct a real period-zero decision from the captured notice and cash.
    ///
    /// # Errors
    /// Refuses an invalid captured notice, binding, account, or decision.
    pub fn try_initial(
        config: CityPdConfig,
        case: CityPdCase,
        mut bindings: Vec<(u64, StableElementKey)>,
        catalog: &MaterialCatalog,
        material: &MaterialCircuitState,
        resolver: &StableElementResolver,
    ) -> Result<Self, CityPdRegisterError> {
        use CityPdRegisterError as E;
        if case.observed_period != 0
            || case.acquired_period != 0
            || case.status != CityPdCaseStatus::Open
            || case.source_kind != CityPdCaseSource::CapturedPublicRecord
        {
            return Err(E::History);
        }
        bindings.sort_by_key(|row| row.0);
        let resolve = |id: u64| -> Result<_, CityPdRegisterError> {
            let key = &bindings.iter().find(|row| row.0 == id).ok_or(E::Binding)?.1;
            resolver.validate_sealed_key(key).map_err(|_| E::Binding)?;
            let StableElementKey::Node { local_name, .. } = key else {
                return Err(E::Binding);
            };
            resolver
                .node_handle_by_local_name(local_name)
                .map_err(|_| E::Binding)
        };
        let mut dossier = Dossier::new(resolve(config.actor_id)?);
        dossier.resolve_node(resolve(case.subject_id)?);
        let mut state = CityPdState {
            dossier,
            cases: vec![case],
            last_decision: None,
        };
        let CircuitAccounting::Monetary(money) = &material.accounting else {
            return Err(E::Account);
        };
        let balance = money
            .book
            .cash(AccountId::Organization(OrganizationAccountId::from_bytes(
                config.agency_account_id,
            )))
            .map_err(|_| E::Account)?;
        if balance.micro_units() != 0 {
            return Err(E::Account);
        }
        state.last_decision = Some(
            state_opponent::decide_city_pd(&config, &state, resolver, &bindings, balance, 0)
                .map_err(|_| E::Decision)?,
        );
        let register = Self {
            config,
            state,
            bindings,
            attempts: vec![],
        };
        register.validate(catalog, material, 0, resolver)?;
        Ok(register)
    }

    pub(crate) fn validate(
        &self,
        catalog: &MaterialCatalog,
        material: &MaterialCircuitState,
        completed_tick: u64,
        resolver: &StableElementResolver,
    ) -> Result<(), CityPdRegisterError> {
        babylon_practice_contract::validate_city_pd_config(&self.config)
            .map_err(|_| CityPdRegisterError::Binding)?;
        self.validate_bindings()?;
        let balance = self.validate_accounts(catalog, material)?;
        self.validate_decision(material, completed_tick, resolver, balance)?;
        self.validate_history(completed_tick)
    }

    fn validate_bindings(&self) -> Result<(), CityPdRegisterError> {
        use CityPdRegisterError as E;
        if self.state.cases.len() > CITY_PD_MAX_ROWS
            || self.attempts.len() > CITY_PD_MAX_ROWS
            || self.bindings.len() > CITY_PD_MAX_ROWS
        {
            return Err(E::Limit);
        }
        let mut previous = None;
        for (id, key) in &self.bindings {
            let bytes = key.canonical_bytes().map_err(|_| E::Binding)?;
            let digest = content_digest::sha256_of(&bytes);
            let derived = u64::from_be_bytes(digest[..8].try_into().map_err(|_| E::Binding)?);
            if *id != derived || previous.is_some_and(|last| last >= *id) {
                return Err(E::Binding);
            }
            previous = Some(*id);
        }
        let expected_ids: BTreeSet<_> = std::iter::once(self.config.actor_id)
            .chain(self.state.cases.iter().map(|case| case.subject_id))
            .collect();
        if self
            .bindings
            .iter()
            .map(|row| row.0)
            .collect::<BTreeSet<_>>()
            != expected_ids
        {
            return Err(E::Binding);
        }
        Ok(())
    }

    fn validate_accounts(
        &self,
        catalog: &MaterialCatalog,
        material: &MaterialCircuitState,
    ) -> Result<Currency, CityPdRegisterError> {
        use CityPdRegisterError as E;
        let principal =
            FinalDemandPrincipalId::from_bytes(self.config.investigator_household_account_id);
        let agency = OrganizationAccountId::from_bytes(self.config.agency_account_id);
        let public = PublicAccountId::from_bytes(self.config.public_account_id);
        let CircuitAccounting::Monetary(money) = &material.accounting else {
            return Err(E::Account);
        };
        let county: EconomicLocation = "county:26163".parse().map_err(|_| E::Binding)?;
        if self.config.county != *b"26163"
            || material
                .final_demand_principals
                .iter()
                .filter(|row| row.id == principal && row.location == county)
                .count()
                != 1
            || catalog
                .household_time_policy
                .iter()
                .filter(|row| {
                    row.principal_id == principal
                        && row.labor_unit_id.as_bytes() == self.config.labor_unit_id
                        && row.eligible_persons > 0
                })
                .count()
                != 1
            || money
                .financial
                .locations
                .iter()
                .filter(|row| row.account == AccountId::Public(public) && row.location == county)
                .count()
                != 1
            || money
                .financial
                .locations
                .iter()
                .filter(|row| {
                    row.account == AccountId::Organization(agency) && row.location == county
                })
                .count()
                != 1
            || money
                .financial
                .public_allocations
                .iter()
                .filter(|row| row.recipient == AccountId::Organization(agency))
                .count()
                != 1
            || money
                .financial
                .public_allocations
                .iter()
                .filter(|row| {
                    row.public_account == public
                        && row.recipient == AccountId::Organization(agency)
                        && row.treatment == PublicTransferTreatment::AgencyAppropriation
                        && row.priority == self.config.appropriation_priority
                        && row.amount_per_period.micro_units() == self.config.appropriation_micros
                })
                .count()
                != 1
        {
            return Err(E::Account);
        }
        let balance = money
            .book
            .cash(AccountId::Organization(agency))
            .map_err(|_| E::Account)?;
        money
            .book
            .cash(AccountId::Household(principal))
            .map_err(|_| E::Account)?;
        money
            .book
            .cash(AccountId::Public(public))
            .map_err(|_| E::Account)?;
        Ok(balance)
    }

    fn validate_decision(
        &self,
        material: &MaterialCircuitState,
        completed_tick: u64,
        resolver: &StableElementResolver,
        balance: Currency,
    ) -> Result<(), CityPdRegisterError> {
        use CityPdRegisterError as E;
        let decision = self.state.last_decision.as_ref().ok_or(E::Decision)?;
        if decision.period != completed_tick
            || material.period.checked_sub(1) != Some(completed_tick)
        {
            return Err(E::Period);
        }
        if state_opponent::decide_city_pd(
            &self.config,
            &self.state,
            resolver,
            &self.bindings,
            balance,
            completed_tick,
        )
        .map_err(|_| E::Decision)?
            != *decision
        {
            return Err(E::Decision);
        }
        Ok(())
    }

    fn validate_history(&self, completed_tick: u64) -> Result<(), CityPdRegisterError> {
        use CityPdRegisterError as E;
        if self
            .state
            .cases
            .windows(2)
            .any(|p| p[0].case_id >= p[1].case_id)
            || self.attempts.windows(2).any(|p| {
                (p[0].receipt.resolve_period, p[0].receipt.intent_id)
                    >= (p[1].receipt.resolve_period, p[1].receipt.intent_id)
            })
        {
            return Err(E::History);
        }
        let mut intents = BTreeSet::new();
        let mut completed = BTreeSet::new();
        for attempt in &self.attempts {
            self.validate_attempt(attempt, completed_tick, &mut intents, &mut completed)?;
        }
        if self.state.cases.iter().any(|case| {
            (case.status == CityPdCaseStatus::Closed) != completed.contains(&case.case_id)
        }) {
            return Err(E::History);
        }
        for case in &self.state.cases {
            if case.source_kind == CityPdCaseSource::ObservedOrganizerReceipt
                && self
                    .attempts
                    .iter()
                    .filter(|attempt| {
                        attempt.receipt.resolve_period == case.acquired_period
                            && attempt
                                .receipt
                                .acquired_public_fact_ids
                                .contains(&case.source_id)
                    })
                    .count()
                    != 1
            {
                return Err(E::History);
            }
        }
        Ok(())
    }

    fn validate_attempt(
        &self,
        attempt: &CityPdAttempt,
        completed_tick: u64,
        intents: &mut BTreeSet<[u8; 32]>,
        completed: &mut BTreeSet<[u8; 32]>,
    ) -> Result<(), CityPdRegisterError> {
        use CityPdRegisterError as E;
        let receipt = &attempt.receipt;
        babylon_practice_contract::validate_city_pd_decision(&attempt.decision)
            .map_err(|_| E::History)?;
        let CityPdDecision::Selected(intent) = &attempt.decision.decision else {
            return Err(E::History);
        };
        babylon_practice_contract::validate_city_pd_receipt(receipt).map_err(|_| E::History)?;
        let case = self
            .state
            .cases
            .iter()
            .find(|case| case.case_id == receipt.case_id)
            .ok_or(E::History)?;
        if receipt.campaign_id != self.config.campaign_id
            || receipt.actor_id != self.config.actor_id
            || receipt.resolve_period > completed_tick
            || receipt.resolve_period <= case.acquired_period
            || !intents.insert(receipt.intent_id)
            || intent.intent_id != receipt.intent_id
            || intent.campaign_id != self.config.campaign_id
            || intent.case_id != case.case_id
            || intent.subject_id != case.subject_id
            || intent.actor_id != self.config.actor_id
            || intent.authority_id != self.config.authority_id
            || intent.config_digest
                != babylon_practice_contract::city_pd_config_digest(&self.config)
                    .map_err(|_| E::Binding)?
            || intent.resolve_period != receipt.resolve_period
            || intent.cost_micros != self.config.visit_cost_micros
            || attempt.decision.period.checked_add(1) != Some(receipt.resolve_period)
        {
            return Err(E::History);
        }
        validate_funding(&self.config, intent, &attempt.funding, receipt)?;
        if receipt.outcome == CityPdOutcome::Completed
            && (receipt.attendance_hours != self.config.visit_hours
                || receipt.wage_micros != self.config.visit_cost_micros
                || receipt.shift_receipt_id.is_none()
                || receipt.payment_receipt_id.is_none())
        {
            return Err(E::History);
        }
        if !receipt.acquired_public_fact_ids.is_empty() && receipt.case_source_evidence_id.is_none()
        {
            return Err(E::History);
        }
        let mut pairs = Vec::new();
        for source in &receipt.acquired_public_fact_ids {
            let rows: Vec<_> = self
                .state
                .cases
                .iter()
                .filter(|case| {
                    case.source_id == *source && case.acquired_period == receipt.resolve_period
                })
                .collect();
            let [case] = rows.as_slice() else {
                return Err(E::History);
            };
            pairs.push((*source, case.case_source_witness_id.ok_or(E::History)?));
        }
        if acquired_evidence(&pairs)? != receipt.case_source_evidence_id {
            return Err(E::History);
        }
        if receipt.outcome == CityPdOutcome::Completed && !completed.insert(receipt.case_id) {
            return Err(E::History);
        }
        Ok(())
    }
}

pub(crate) fn acquired_evidence(
    pairs: &[([u8; 32], [u8; 32])],
) -> Result<Option<[u8; 32]>, CityPdRegisterError> {
    if pairs.is_empty() {
        return Ok(None);
    }
    if pairs.len() > CITY_PD_MAX_ROWS
        || pairs.windows(2).any(|rows| rows[0].0 >= rows[1].0)
        || pairs
            .iter()
            .any(|(source, witness)| *source == [0; 32] || *witness == [0; 32])
    {
        return Err(CityPdRegisterError::History);
    }
    let mut basis = b"babylon.city-pd-acquired-source-evidence.v1\0".to_vec();
    basis.extend_from_slice(
        &u32::try_from(pairs.len())
            .map_err(|_| CityPdRegisterError::Limit)?
            .to_be_bytes(),
    );
    for (source, witness) in pairs {
        basis.extend_from_slice(source);
        basis.extend_from_slice(witness);
    }
    Ok(Some(content_digest::sha256_of(&basis)))
}

fn validate_funding(
    config: &CityPdConfig,
    intent: &babylon_practice_contract::CityPdIntent,
    funding: &AgencyObservationFundingReceipt,
    receipt: &CityPdReceipt,
) -> Result<(), CityPdRegisterError> {
    use CityPdRegisterError as E;
    let input = &funding.input;
    let county: EconomicLocation = "county:26163".parse().map_err(|_| E::Binding)?;
    if input.intent_id != intent.intent_id
        || input.shift_id
            != babylon_material_circuit::agency_shift_id(intent.resolve_period, intent.intent_id)
        || input.agency.as_bytes() != config.agency_account_id
        || input.principal_id.as_bytes() != config.investigator_household_account_id
        || input.residence != county
        || input.labor_unit_id.as_bytes() != config.labor_unit_id
        || input.due_period != intent.resolve_period
        || input.hours != config.visit_hours
        || input.hourly_rate.micro_units() != config.hourly_wage_micros
        || funding.requested.micro_units() != config.visit_cost_micros
    {
        return Err(E::History);
    }
    match funding.outcome {
        AgencyAttendanceOutcome::Paid => {
            let attendance = funding.attendance.as_ref().ok_or(E::History)?;
            if receipt.outcome != CityPdOutcome::Completed
                || funding.reserved != funding.requested
                || funding.paid != funding.requested
                || funding.cancelled.micro_units() != 0
                || funding.shortfall.micro_units() != 0
                || funding.attended_hours != input.hours
                || funding.shortfall_hours != 0
                || attendance.intent_id != input.intent_id
                || attendance.shift_id != input.shift_id
                || attendance.principal_id != input.principal_id
                || attendance.labor_unit_id != input.labor_unit_id
                || attendance.period != input.due_period
                || attendance.hours != input.hours
            {
                return Err(E::History);
            }
        }
        AgencyAttendanceOutcome::NoFunds | AgencyAttendanceOutcome::InsufficientTime => {
            if funding.paid.micro_units() != 0
                || funding.attended_hours != 0
                || funding.shortfall_hours != input.hours
                || funding.attendance.is_some()
            {
                return Err(E::History);
            }
            match funding.outcome {
                AgencyAttendanceOutcome::NoFunds
                    if receipt.outcome == CityPdOutcome::InsufficientFunds
                        && funding.reserved.micro_units() == 0
                        && funding.cancelled.micro_units() == 0
                        && funding.shortfall.micro_units() > 0
                        && funding.shortfall.micro_units() <= config.visit_cost_micros
                        && receipt.shift_receipt_id.is_none() => {}
                AgencyAttendanceOutcome::InsufficientTime
                    if receipt.outcome == CityPdOutcome::InsufficientTime
                        && funding.reserved == funding.requested
                        && funding.cancelled == funding.requested
                        && funding.shortfall.micro_units() == 0 => {}
                _ => return Err(E::History),
            }
        }
    }
    Ok(())
}

fn append(out: &mut Vec<u8>, data: &[u8]) -> Result<(), CityPdRegisterError> {
    let length = out
        .len()
        .checked_add(data.len())
        .ok_or(CityPdRegisterError::Limit)?;
    if length > super::MAX_MATERIAL_WORLD_REGISTER_BYTES {
        return Err(CityPdRegisterError::Limit);
    }
    out.try_reserve(data.len())
        .map_err(|_| CityPdRegisterError::Limit)?;
    out.extend_from_slice(data);
    Ok(())
}
fn section(out: &mut Vec<u8>, data: &[u8]) -> Result<(), CityPdRegisterError> {
    append(
        out,
        &u64::try_from(data.len())
            .map_err(|_| CityPdRegisterError::Limit)?
            .to_be_bytes(),
    )?;
    append(out, data)
}
fn count(out: &mut Vec<u8>, value: usize) -> Result<(), CityPdRegisterError> {
    if value > CITY_PD_MAX_ROWS {
        return Err(CityPdRegisterError::Limit);
    }
    append(
        out,
        &u32::try_from(value)
            .map_err(|_| CityPdRegisterError::Limit)?
            .to_be_bytes(),
    )
}

pub(crate) fn encode(
    register: Option<&CityPdRegister>,
    catalog: &MaterialCatalog,
    material: &MaterialCircuitState,
    tick: u64,
    resolver: Option<&StableElementResolver>,
) -> Result<Vec<u8>, CityPdRegisterError> {
    let Some(register) = register else {
        return Ok(vec![0]);
    };
    let resolver = resolver.ok_or(CityPdRegisterError::Binding)?;
    register.validate(catalog, material, tick, resolver)?;
    let mut output = vec![1];
    section(
        &mut output,
        &babylon_practice_contract::encode_city_pd_config(&register.config)
            .map_err(|_| CityPdRegisterError::Framing)?,
    )?;
    count(&mut output, register.bindings.len())?;
    for (id, key) in &register.bindings {
        append(&mut output, &id.to_be_bytes())?;
        section(
            &mut output,
            &key.canonical_bytes()
                .map_err(|_| CityPdRegisterError::Binding)?,
        )?;
    }
    count(&mut output, register.state.cases.len())?;
    for case in &register.state.cases {
        section(
            &mut output,
            &babylon_practice_contract::encode_city_pd_case(case)
                .map_err(|_| CityPdRegisterError::Framing)?,
        )?;
    }
    section(
        &mut output,
        &register
            .state
            .dossier
            .encode_canonical(resolver)
            .map_err(|_| CityPdRegisterError::Binding)?,
    )?;
    section(
        &mut output,
        &babylon_practice_contract::encode_city_pd_decision(
            register
                .state
                .last_decision
                .as_ref()
                .ok_or(CityPdRegisterError::Decision)?,
        )
        .map_err(|_| CityPdRegisterError::Decision)?,
    )?;
    count(&mut output, register.attempts.len())?;
    for attempt in &register.attempts {
        section(
            &mut output,
            &babylon_practice_contract::encode_city_pd_decision(&attempt.decision)
                .map_err(|_| CityPdRegisterError::History)?,
        )?;
        section(&mut output, &encode_funding(&attempt.funding)?)?;
        section(
            &mut output,
            &babylon_practice_contract::encode_city_pd_receipt(&attempt.receipt)
                .map_err(|_| CityPdRegisterError::History)?,
        )?;
    }
    Ok(output)
}

struct Cursor<'a> {
    bytes: &'a [u8],
    position: usize,
}
impl<'a> Cursor<'a> {
    fn take(&mut self, length: usize) -> Result<&'a [u8], CityPdRegisterError> {
        let end = self
            .position
            .checked_add(length)
            .ok_or(CityPdRegisterError::Limit)?;
        let value = self
            .bytes
            .get(self.position..end)
            .ok_or(CityPdRegisterError::Framing)?;
        self.position = end;
        Ok(value)
    }
    fn array<const N: usize>(&mut self) -> Result<[u8; N], CityPdRegisterError> {
        self.take(N)?
            .try_into()
            .map_err(|_| CityPdRegisterError::Framing)
    }
    fn section(&mut self) -> Result<&'a [u8], CityPdRegisterError> {
        let length = usize::try_from(u64::from_be_bytes(self.array()?))
            .map_err(|_| CityPdRegisterError::Limit)?;
        self.take(length)
    }
    fn count(&mut self) -> Result<usize, CityPdRegisterError> {
        let value = usize::try_from(u32::from_be_bytes(self.array()?))
            .map_err(|_| CityPdRegisterError::Limit)?;
        if value > CITY_PD_MAX_ROWS {
            return Err(CityPdRegisterError::Limit);
        }
        Ok(value)
    }
}

pub(crate) fn decode(
    bytes: &[u8],
    catalog: &MaterialCatalog,
    material: &MaterialCircuitState,
    tick: u64,
    resolver: Option<&StableElementResolver>,
) -> Result<Option<CityPdRegister>, CityPdRegisterError> {
    if bytes.len() > super::MAX_MATERIAL_WORLD_REGISTER_BYTES {
        return Err(CityPdRegisterError::Limit);
    }
    if bytes == [0] {
        return Ok(None);
    }
    let resolver = resolver.ok_or(CityPdRegisterError::Binding)?;
    let mut cursor = Cursor { bytes, position: 0 };
    if cursor.array::<1>()? != [1] {
        return Err(CityPdRegisterError::Framing);
    }
    let config = babylon_practice_contract::decode_city_pd_config(cursor.section()?)
        .map_err(|_| CityPdRegisterError::Framing)?;
    let mut bindings = Vec::new();
    for _ in 0..cursor.count()? {
        let id = u64::from_be_bytes(cursor.array()?);
        let key = StableElementKey::from_canonical_bytes(cursor.section()?)
            .map_err(|_| CityPdRegisterError::Binding)?;
        bindings.push((id, key));
    }
    let mut cases = Vec::new();
    for _ in 0..cursor.count()? {
        cases.push(
            babylon_practice_contract::decode_city_pd_case(cursor.section()?)
                .map_err(|_| CityPdRegisterError::Framing)?,
        );
    }
    let dossier = Dossier::decode_canonical(cursor.section()?, resolver)
        .map_err(|_| CityPdRegisterError::Binding)?;
    let decision = babylon_practice_contract::decode_city_pd_decision(cursor.section()?)
        .map_err(|_| CityPdRegisterError::Decision)?;
    let mut attempts = Vec::new();
    for _ in 0..cursor.count()? {
        let decision = babylon_practice_contract::decode_city_pd_decision(cursor.section()?)
            .map_err(|_| CityPdRegisterError::History)?;
        let funding = decode_funding(cursor.section()?)?;
        let receipt = babylon_practice_contract::decode_city_pd_receipt(cursor.section()?)
            .map_err(|_| CityPdRegisterError::History)?;
        attempts.push(CityPdAttempt {
            decision,
            funding,
            receipt,
        });
    }
    if cursor.position != bytes.len() {
        return Err(CityPdRegisterError::Framing);
    }
    let result = CityPdRegister {
        config,
        state: CityPdState {
            dossier,
            cases,
            last_decision: Some(decision),
        },
        bindings,
        attempts,
    };
    if encode(Some(&result), catalog, material, tick, Some(resolver))? != bytes {
        return Err(CityPdRegisterError::Framing);
    }
    Ok(Some(result))
}

fn encode_funding(value: &AgencyObservationFundingReceipt) -> Result<Vec<u8>, CityPdRegisterError> {
    let input = &value.input;
    let mut out = Vec::new();
    for row in [
        input.intent_id,
        input.shift_id.as_bytes(),
        input.agency.as_bytes(),
        input.principal_id.as_bytes(),
    ] {
        append(&mut out, &row)?;
    }
    append(&mut out, &input.residence.canonical_bytes())?;
    append(&mut out, &input.labor_unit_id.as_bytes())?;
    append(&mut out, &input.due_period.to_be_bytes())?;
    append(&mut out, &input.hours.to_be_bytes())?;
    append(&mut out, &input.hourly_rate.micro_units().to_be_bytes())?;
    append(
        &mut out,
        &[match value.outcome {
            AgencyAttendanceOutcome::NoFunds => 1,
            AgencyAttendanceOutcome::InsufficientTime => 2,
            AgencyAttendanceOutcome::Paid => 3,
        }],
    )?;
    for amount in [
        value.requested,
        value.reserved,
        value.paid,
        value.cancelled,
        value.shortfall,
    ] {
        append(&mut out, &amount.micro_units().to_be_bytes())?;
    }
    append(&mut out, &value.attended_hours.to_be_bytes())?;
    append(&mut out, &value.shortfall_hours.to_be_bytes())?;
    if let Some(attendance) = &value.attendance {
        append(&mut out, &[1])?;
        for row in [
            attendance.intent_id,
            attendance.shift_id.as_bytes(),
            attendance.principal_id.as_bytes(),
            attendance.labor_unit_id.as_bytes(),
        ] {
            append(&mut out, &row)?;
        }
        append(&mut out, &attendance.period.to_be_bytes())?;
        append(&mut out, &attendance.hours.to_be_bytes())?;
    } else {
        append(&mut out, &[0])?;
    }
    Ok(out)
}

fn decode_funding(bytes: &[u8]) -> Result<AgencyObservationFundingReceipt, CityPdRegisterError> {
    use babylon_material_circuit::{AgencyAttendanceInput, CityPdAttendance, ShiftId, UnitId};
    use Currency;
    let mut cursor = Cursor { bytes, position: 0 };
    let input = AgencyAttendanceInput {
        intent_id: cursor.array()?,
        shift_id: ShiftId::from_bytes(cursor.array()?),
        agency: OrganizationAccountId::from_bytes(cursor.array()?),
        principal_id: FinalDemandPrincipalId::from_bytes(cursor.array()?),
        residence: EconomicLocation::from_canonical_bytes(cursor.array()?)
            .map_err(|_| CityPdRegisterError::Framing)?,
        labor_unit_id: UnitId::from_bytes(cursor.array()?),
        due_period: u64::from_be_bytes(cursor.array()?),
        hours: u64::from_be_bytes(cursor.array()?),
        hourly_rate: Currency::from_micro_units(i128::from_be_bytes(cursor.array()?)),
    };
    let outcome = match cursor.array::<1>()? {
        [1] => AgencyAttendanceOutcome::NoFunds,
        [2] => AgencyAttendanceOutcome::InsufficientTime,
        [3] => AgencyAttendanceOutcome::Paid,
        _ => return Err(CityPdRegisterError::Framing),
    };
    let requested = Currency::from_micro_units(i128::from_be_bytes(cursor.array()?));
    let reserved = Currency::from_micro_units(i128::from_be_bytes(cursor.array()?));
    let paid = Currency::from_micro_units(i128::from_be_bytes(cursor.array()?));
    let cancelled = Currency::from_micro_units(i128::from_be_bytes(cursor.array()?));
    let shortfall = Currency::from_micro_units(i128::from_be_bytes(cursor.array()?));
    let attended_hours = u64::from_be_bytes(cursor.array()?);
    let shortfall_hours = u64::from_be_bytes(cursor.array()?);
    let attendance = match cursor.array::<1>()? {
        [0] => None,
        [1] => Some(CityPdAttendance {
            intent_id: cursor.array()?,
            shift_id: ShiftId::from_bytes(cursor.array()?),
            principal_id: FinalDemandPrincipalId::from_bytes(cursor.array()?),
            labor_unit_id: UnitId::from_bytes(cursor.array()?),
            period: u64::from_be_bytes(cursor.array()?),
            hours: u64::from_be_bytes(cursor.array()?),
        }),
        _ => return Err(CityPdRegisterError::Framing),
    };
    if cursor.position != bytes.len() {
        return Err(CityPdRegisterError::Framing);
    }
    let value = AgencyObservationFundingReceipt {
        input,
        outcome,
        requested,
        reserved,
        paid,
        cancelled,
        shortfall,
        attended_hours,
        shortfall_hours,
        attendance,
    };
    if encode_funding(&value)? != bytes {
        return Err(CityPdRegisterError::Framing);
    }
    Ok(value)
}

pub(crate) fn decode_attempt_evidence(
    bytes: &[u8],
) -> Result<Option<DecodedCityPdAttemptEvidence>, CityPdRegisterError> {
    if bytes == [0] {
        return Ok(None);
    }
    let mut cursor = Cursor { bytes, position: 0 };
    if cursor.array::<1>()? != [1] {
        return Err(CityPdRegisterError::Framing);
    }
    let config = babylon_practice_contract::decode_city_pd_config(cursor.section()?)
        .map_err(|_| CityPdRegisterError::Framing)?;
    let mut prior_id = None;
    for _ in 0..cursor.count()? {
        let id = u64::from_be_bytes(cursor.array()?);
        let key = StableElementKey::from_canonical_bytes(cursor.section()?)
            .map_err(|_| CityPdRegisterError::Binding)?;
        let digest = content_digest::sha256_of(
            &key.canonical_bytes()
                .map_err(|_| CityPdRegisterError::Binding)?,
        );
        if id
            != u64::from_be_bytes(
                digest[..8]
                    .try_into()
                    .map_err(|_| CityPdRegisterError::Binding)?,
            )
            || prior_id.is_some_and(|prior| prior >= id)
        {
            return Err(CityPdRegisterError::Binding);
        }
        prior_id = Some(id);
    }
    let mut prior_case = None;
    let mut cases = Vec::new();
    for _ in 0..cursor.count()? {
        let case = babylon_practice_contract::decode_city_pd_case(cursor.section()?)
            .map_err(|_| CityPdRegisterError::History)?;
        if prior_case.is_some_and(|prior| prior >= case.case_id) {
            return Err(CityPdRegisterError::History);
        }
        prior_case = Some(case.case_id);
        cases.push(case);
    }
    // The original dossier frame remains opaque; it is not reconstructed into
    // handles or adopted by this purpose-specific historical view.
    let _dossier = cursor.section()?;
    let last_decision = babylon_practice_contract::decode_city_pd_decision(cursor.section()?)
        .map_err(|_| CityPdRegisterError::Decision)?;
    let mut attempts = Vec::new();
    for _ in 0..cursor.count()? {
        let decision = babylon_practice_contract::decode_city_pd_decision(cursor.section()?)
            .map_err(|_| CityPdRegisterError::History)?;
        let funding = decode_funding(cursor.section()?)?;
        let receipt = babylon_practice_contract::decode_city_pd_receipt(cursor.section()?)
            .map_err(|_| CityPdRegisterError::History)?;
        let CityPdDecision::Selected(intent) = &decision.decision else {
            return Err(CityPdRegisterError::History);
        };
        if intent.intent_id != receipt.intent_id
            || intent.actor_id != config.actor_id
            || intent.authority_id != config.authority_id
            || intent.campaign_id != config.campaign_id
            || intent.resolve_period != receipt.resolve_period
        {
            return Err(CityPdRegisterError::History);
        }
        validate_funding(&config, intent, &funding, &receipt)?;
        attempts.push(CityPdAttempt {
            decision,
            funding,
            receipt,
        });
    }
    if cursor.position != bytes.len()
        || attempts.windows(2).any(|rows| {
            (rows[0].receipt.resolve_period, rows[0].receipt.intent_id)
                >= (rows[1].receipt.resolve_period, rows[1].receipt.intent_id)
        })
    {
        return Err(CityPdRegisterError::Framing);
    }
    Ok(Some(DecodedCityPdAttemptEvidence {
        config,
        cases,
        last_decision,
        attempts,
    }))
}

#[cfg(test)]
mod tests {
    use super::*;
    use babylon_material_circuit::{AgencyAttendanceInput, CityPdAttendance, UnitId};
    use babylon_practice_contract::{CityPdIntent, CITY_PD_SCHEMA_VERSION};
    use Currency;

    fn paid_fixture() -> (
        CityPdConfig,
        CityPdIntent,
        AgencyObservationFundingReceipt,
        CityPdReceipt,
    ) {
        let config = CityPdConfig {
            schema_version: CITY_PD_SCHEMA_VERSION,
            campaign_id: [1; 16],
            actor_id: 1,
            authority_id: [2; 16],
            county: *b"26163",
            public_account_id: [3; 32],
            agency_account_id: [4; 32],
            investigator_household_account_id: [5; 32],
            investigator_entitlement_id: [6; 32],
            labor_unit_id: [7; 32],
            visit_hours: 1,
            hourly_wage_micros: 24_000_000,
            visit_cost_micros: 24_000_000,
            appropriation_micros: 24_000_000,
            appropriation_priority: 0,
            content_digest: [8; 32],
            policy_source_digest: [9; 32],
        };
        let intent = CityPdIntent {
            intent_id: [10; 32],
            schema_version: CITY_PD_SCHEMA_VERSION,
            campaign_id: config.campaign_id,
            actor_id: config.actor_id,
            authority_id: config.authority_id,
            config_digest: [11; 32],
            decision_basis_digest: [12; 32],
            case_id: [13; 32],
            subject_id: 14,
            source_period: 1,
            resolve_period: 2,
            cost_micros: config.visit_cost_micros,
        };
        let input = AgencyAttendanceInput {
            intent_id: intent.intent_id,
            shift_id: babylon_material_circuit::agency_shift_id(2, intent.intent_id),
            agency: OrganizationAccountId::from_bytes(config.agency_account_id),
            principal_id: FinalDemandPrincipalId::from_bytes(
                config.investigator_household_account_id,
            ),
            residence: "county:26163".parse().expect("Wayne county"),
            labor_unit_id: UnitId::from_bytes(config.labor_unit_id),
            due_period: 2,
            hours: 1,
            hourly_rate: Currency::from_micro_units(24_000_000),
        };
        let amount = Currency::from_micro_units(24_000_000);
        let funding = AgencyObservationFundingReceipt {
            attendance: Some(CityPdAttendance {
                intent_id: input.intent_id,
                shift_id: input.shift_id,
                principal_id: input.principal_id,
                labor_unit_id: input.labor_unit_id,
                period: 2,
                hours: 1,
            }),
            input,
            outcome: AgencyAttendanceOutcome::Paid,
            requested: amount,
            reserved: amount,
            paid: amount,
            cancelled: Currency::from_micro_units(0),
            shortfall: Currency::from_micro_units(0),
            attended_hours: 1,
            shortfall_hours: 0,
        };
        let receipt = CityPdReceipt {
            receipt_id: [15; 32],
            campaign_id: config.campaign_id,
            actor_id: config.actor_id,
            case_id: intent.case_id,
            intent_id: intent.intent_id,
            resolve_period: 2,
            outcome: CityPdOutcome::Completed,
            attendance_hours: 1,
            wage_micros: 24_000_000,
            shift_receipt_id: Some([16; 32]),
            payment_receipt_id: Some([17; 32]),
            acquired_public_fact_ids: vec![],
            case_source_evidence_id: None,
            player_witness_evidence_id: None,
        };
        (config, intent, funding, receipt)
    }

    #[test]
    fn paid_visit_completes_without_public_facts_or_player_witness() {
        let (config, intent, mut funding, receipt) = paid_fixture();
        let amount = funding.requested;
        assert!(validate_funding(&config, &intent, &funding, &receipt).is_ok());
        for outcome in [
            AgencyAttendanceOutcome::NoFunds,
            AgencyAttendanceOutcome::InsufficientTime,
        ] {
            funding.outcome = outcome;
            funding.paid = Currency::from_micro_units(0);
            funding.attendance = None;
            funding.attended_hours = 0;
            funding.shortfall_hours = 1;
            match outcome {
                AgencyAttendanceOutcome::NoFunds => {
                    funding.reserved = Currency::from_micro_units(0);
                    funding.cancelled = Currency::from_micro_units(0);
                    funding.shortfall = amount;
                }
                AgencyAttendanceOutcome::InsufficientTime => {
                    funding.reserved = amount;
                    funding.cancelled = amount;
                    funding.shortfall = Currency::from_micro_units(0);
                }
                AgencyAttendanceOutcome::Paid => unreachable!("test covers only unpaid outcomes"),
            }
            let mut refusal = receipt.clone();
            refusal.outcome = match outcome {
                AgencyAttendanceOutcome::NoFunds => CityPdOutcome::InsufficientFunds,
                AgencyAttendanceOutcome::InsufficientTime => CityPdOutcome::InsufficientTime,
                AgencyAttendanceOutcome::Paid => unreachable!("test covers only unpaid outcomes"),
            };
            refusal.attendance_hours = 0;
            refusal.wage_micros = 0;
            refusal.shift_receipt_id = None;
            refusal.payment_receipt_id = None;
            assert!(validate_funding(&config, &intent, &funding, &refusal).is_ok());
            assert!(validate_funding(&config, &intent, &funding, &receipt).is_err());
        }
    }
}
