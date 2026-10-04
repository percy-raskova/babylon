//! Indexed graph stocks and receipt joins; no staffing policy is recomputed here.
use std::collections::BTreeMap;

use babylon_bsl::{
    identity_codec::project_stored_field_value,
    types::{BslType, EnumRegistry, FieldDecl, FieldKind},
};
use babylon_graph::{stable_element::StableElementKey, stable_state::StableGraphState};
use babylon_material_circuit::{
    CircuitAccounting, EmploymentTerms, LaborCompensation, StaffingMemberId, StaffingMemberReceipt,
};
use babylon_tick::{
    material_staffing::{
        StaffingMemberNodeBinding, StaffingNodeBinding, EMPLOYED_POPULATION,
        PREVIOUS_UNRETAINED_HOURS, RESERVE_POPULATION,
    },
    material_world::{MaterialTickReceipts, MaterialWorldRegister},
};

use super::{integer, ProductionProjectionError, Result, Stocks};
use crate::{
    michigan_economy::digest_hex,
    production_observation::{
        CompletedProductionStaffingMember, ProductionLaborCompensation,
        ProductionStaffingMemberAccount, ProductionStaffingSubject,
    },
};

pub(super) struct StaffingGraph<'a> {
    scope: &'a str,
    kinds: BTreeMap<&'a str, &'a str>,
    values: BTreeMap<(&'a str, &'a str), u64>,
}
impl<'a> StaffingGraph<'a> {
    pub(super) fn new(graph: &'a StableGraphState) -> Result<Self> {
        let kinds: BTreeMap<_, _> = graph
            .rows()
            .nodes()
            .iter()
            .map(|(name, kind)| (name.as_str(), kind.as_str()))
            .collect();
        if kinds.len() != graph.rows().nodes().len() {
            return Err(ProductionProjectionError::State);
        }
        let owned = |field: &str| {
            [
                EMPLOYED_POPULATION,
                RESERVE_POPULATION,
                PREVIOUS_UNRETAINED_HOURS,
            ]
            .contains(&field)
        };
        if graph
            .rows()
            .node_currency()
            .iter()
            .any(|(_, field, _)| owned(field))
        {
            return Err(ProductionProjectionError::State);
        }
        let mut values = BTreeMap::new();
        for (name, field, bits) in graph
            .rows()
            .node_f64()
            .iter()
            .filter(|(_, field, _)| owned(field))
        {
            let value = project_stored_field_value(
                &FieldDecl {
                    ty: BslType::Int,
                    kind: FieldKind::Extensive,
                },
                Some(*bits),
                None,
                &EnumRegistry::default(),
            )
            .map_err(|_| ProductionProjectionError::State)?;
            if values
                .insert((name.as_str(), field.as_str()), integer(&value)?)
                .is_some()
            {
                return Err(ProductionProjectionError::State);
            }
        }
        Ok(Self {
            scope: graph.scenario_scope(),
            kinds,
            values,
        })
    }
    fn node(&self, key: &'a StableElementKey, kind: &str) -> Result<&'a str> {
        let StableElementKey::Node {
            scenario,
            local_name,
        } = key
        else {
            return Err(ProductionProjectionError::Content);
        };
        if scenario != self.scope || self.kinds.get(local_name.as_str()).copied() != Some(kind) {
            return Err(ProductionProjectionError::State);
        }
        Ok(local_name)
    }
    fn field(&self, name: &str, field: &str) -> Result<u64> {
        self.values
            .get(&(name, field))
            .copied()
            .ok_or(ProductionProjectionError::State)
    }
    fn member(&self, binding: &'a StaffingMemberNodeBinding) -> Result<(u64, u64)> {
        let name = self.node(binding.subject(), "SOCIAL_CLASS")?;
        let employed = self.field(name, EMPLOYED_POPULATION)?;
        let reserve = self.field(name, RESERVE_POPULATION)?;
        if employed.checked_add(reserve) != Some(binding.member().labor_force()) {
            return Err(ProductionProjectionError::State);
        }
        Ok((employed, reserve))
    }
    pub(super) fn stocks(&self, binding: &'a StaffingNodeBinding) -> Result<Stocks> {
        let name = self.node(binding.subject(), "BUSINESS")?;
        let mut stocks = Stocks {
            employed: 0,
            reserve: 0,
            previous: self.field(name, PREVIOUS_UNRETAINED_HOURS)?,
        };
        for member in binding.members() {
            let (employed, reserve) = self.member(member)?;
            stocks.employed = stocks
                .employed
                .checked_add(employed)
                .ok_or(ProductionProjectionError::Arithmetic)?;
            stocks.reserve = stocks
                .reserve
                .checked_add(reserve)
                .ok_or(ProductionProjectionError::Arithmetic)?;
        }
        if stocks.employed.checked_add(stocks.reserve) != Some(binding.pool().labor_force()) {
            return Err(ProductionProjectionError::State);
        }
        Ok(stocks)
    }
}

pub(super) struct StaffingWitnesses<'a> {
    register: &'a MaterialWorldRegister,
    receipts: BTreeMap<StaffingMemberId, &'a StaffingMemberReceipt>,
    terms: Option<BTreeMap<StaffingMemberId, &'a EmploymentTerms>>,
    hours: BTreeMap<StaffingMemberId, u64>,
    residences: BTreeMap<
        babylon_material_circuit::FinalDemandPrincipalId,
        babylon_kernel::economic_location::EconomicLocation,
    >,
}
impl<'a> StaffingWitnesses<'a> {
    pub(super) fn new(
        register: &'a MaterialWorldRegister,
        receipts: Option<&'a MaterialTickReceipts>,
    ) -> Result<Self> {
        let rows = receipts.map_or(&[][..], |r| r.staffing_members.as_slice());
        let receipt_map: BTreeMap<_, _> = rows.iter().map(|r| (r.member.member_id(), r)).collect();
        if receipt_map.len() != rows.len() {
            return Err(ProductionProjectionError::History);
        }
        let (terms, hours) = match &register.state().accounting {
            CircuitAccounting::PhysicalControl => (None, BTreeMap::new()),
            CircuitAccounting::Monetary(economy) => {
                let terms: BTreeMap<_, _> = economy
                    .employment
                    .iter()
                    .map(|r| (r.member_id, r))
                    .collect();
                let rows: Vec<_> = economy
                    .member_labor
                    .iter()
                    .filter(|r| r.period == register.state().period)
                    .collect();
                let hours: BTreeMap<_, _> = rows
                    .iter()
                    .map(|r| (r.member_id, r.available_hours))
                    .collect();
                if terms.len() != economy.employment.len() || hours.len() != rows.len() {
                    return Err(ProductionProjectionError::State);
                }
                (Some(terms), hours)
            }
        };
        Ok(Self {
            register,
            receipts: receipt_map,
            terms,
            hours,
            residences: register
                .state()
                .final_demand_principals
                .iter()
                .map(|r| (r.id, r.location))
                .collect(),
        })
    }
    pub(super) fn project_members(
        &mut self,
        pool: &'a StaffingNodeBinding,
        current: &StaffingGraph<'a>,
        prior: Option<&StaffingGraph<'a>>,
    ) -> Result<Vec<ProductionStaffingMemberAccount>> {
        pool.members()
            .iter()
            .map(|binding| self.project_member(pool, binding, current, prior))
            .collect()
    }
    fn project_member(
        &mut self,
        pool: &'a StaffingNodeBinding,
        binding: &'a StaffingMemberNodeBinding,
        current: &StaffingGraph<'a>,
        prior: Option<&StaffingGraph<'a>>,
    ) -> Result<ProductionStaffingMemberAccount> {
        let member = binding.member();
        let id = member.member_id();
        let (employed, reserve) = current.member(binding)?;
        let next_hours = employed
            .checked_mul(pool.pool().policy().hours_per_person())
            .ok_or(ProductionProjectionError::Arithmetic)?;
        let compensation = self.compensation(pool, binding, next_hours)?;
        let completed = if let Some(prior) = prior {
            let (opening_employed, opening_reserve) = prior.member(binding)?;
            let row = self
                .receipts
                .remove(&id)
                .ok_or(ProductionProjectionError::History)?;
            row.validate()
                .map_err(|_| ProductionProjectionError::History)?;
            if row.member != *member
                || row.pool_id != pool.pool().pool_id()
                || row.site_id != pool.pool().site_id()
                || row.unit_id != pool.pool().unit_id()
                || row.period != self.register.completed_tick()
                || row.hours_per_person != pool.pool().policy().hours_per_person()
                || (
                    row.opening_employed,
                    row.opening_reserve,
                    row.closing_employed,
                    row.closing_reserve,
                    row.next_opening_hours,
                ) != (
                    opening_employed,
                    opening_reserve,
                    employed,
                    reserve,
                    next_hours,
                )
            {
                return Err(ProductionProjectionError::History);
            }
            Some(CompletedProductionStaffingMember {
                period: row.period,
                opening_employed,
                opening_reserve,
                hires: row.hires,
                separations: row.separations,
            })
        } else {
            None
        };
        let StableElementKey::Node {
            scenario,
            local_name,
        } = binding.subject()
        else {
            return Err(ProductionProjectionError::Content);
        };
        Ok(ProductionStaffingMemberAccount {
            member_id: digest_hex(&id.as_bytes()),
            household_id: digest_hex(&member.household_id().as_bytes()),
            residence: member.residence(),
            subject: ProductionStaffingSubject {
                scenario: scenario.clone(),
                local_name: local_name.clone(),
            },
            labor_force: member.labor_force(),
            employed,
            reserve,
            next_opening_hours: next_hours,
            compensation,
            completed,
        })
    }
    fn compensation(
        &mut self,
        pool: &StaffingNodeBinding,
        binding: &StaffingMemberNodeBinding,
        next_hours: u64,
    ) -> Result<Option<ProductionLaborCompensation>> {
        let Some(terms) = &mut self.terms else {
            return Ok(None);
        };
        let member = binding.member();
        let row = terms
            .remove(&member.member_id())
            .ok_or(ProductionProjectionError::State)?;
        if (row.site_id, row.unit_id, row.payee)
            != (
                pool.pool().site_id(),
                pool.pool().unit_id(),
                member.household_id(),
            )
            || self.residences.get(&member.household_id()) != Some(&member.residence())
            || self.hours.remove(&member.member_id()) != Some(next_hours)
        {
            return Err(ProductionProjectionError::State);
        }
        Ok(Some(match row.compensation {
            LaborCompensation::Wage(rate) => ProductionLaborCompensation::Wage {
                hourly_micro_units: rate.micro_units(),
            },
            LaborCompensation::WorkingOwner => ProductionLaborCompensation::WorkingOwner,
            LaborCompensation::UnpaidFamily => ProductionLaborCompensation::UnpaidFamily,
        }))
    }
    pub(super) fn finish(self) -> Result<()> {
        if !self.receipts.is_empty()
            || !self.hours.is_empty()
            || self.terms.is_some_and(|r| !r.is_empty())
        {
            return Err(ProductionProjectionError::History);
        }
        Ok(())
    }
}
