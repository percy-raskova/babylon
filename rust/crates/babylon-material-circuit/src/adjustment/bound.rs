//! A bound on hiring (ADR314, A5 and A6 as measured in round nine): at the close, when a workplace plans the next
//! period, the hours it asks of people are capped at the hours it can work.
//!
//! - A maker: the labor of the batches its capacity can run, that its service inputs can feed (a stocked input
//!   already bounds the engine's own request) and that its money can pay for, wages first and service inputs after.
//! - A merchant: the handling its sale needs, and what its money pays at its wage. Its restocking is bought after
//!   its sale and is not counted against its money.
//!
//! The plan itself is not cut: planned batches, orders and prices stay. The attendance plan of the next period
//! (read by payroll) and the staffing requests (read by staffing) are capped. Nothing is kept from one close to
//! the next. Every number is whole.

use std::collections::{BTreeMap, BTreeSet};
use std::result::Result as StdResult;

use super::receipts::{HiringBoundReceipt, HiringLimit};
use crate::production::ProcessLaborRequest;
use crate::services::ServiceInputPolicy;
use crate::{
    AccountId, CircuitAccounting, GoodId, InputOutputCoefficient, MaintenanceReceipt,
    MaterialCatalog, MaterialCircuitError, MaterialCircuitState, MonetaryCircuit, ProcessId,
    RecurringEconomy, ServicePerformanceReceipt, SiteId, UnitId,
};

type Result<T> = StdResult<T, MaterialCircuitError>;

/// The bound of the next period: each production process's batches and hours, and each attendance row's cut.
#[derive(Clone, Debug, PartialEq, Eq)]
pub(crate) struct HiringBound {
    pub(crate) next_period: u64,
    pub(crate) process: BTreeMap<ProcessId, (u64, u64)>,
    pub(crate) rows: Vec<HiringBoundReceipt>,
}

impl HiringBound {
    /// The hours a production request may ask of people: its own, or the bound's where that is lower.
    pub(crate) fn capped_hours(&self, process: ProcessId, hours: u64) -> u64 {
        self.process
            .get(&process)
            .map_or(hours, |&(_, cap)| hours.min(cap))
    }
}

/// The largest `b <= most` with `spent + b x per <= cash`; all of `most` when `per == 0`; 0 when `cash < spent`.
///
/// # Errors
/// `Arithmetic` for a negative `per` or a sum that does not fit.
pub(crate) fn batches_within(most: u64, per: i128, spent: i128, cash: i128) -> Result<u64> {
    if per < 0 {
        return Err(MaterialCircuitError::Arithmetic);
    }
    if cash < spent {
        return Ok(0);
    }
    if per == 0 {
        return Ok(most);
    }
    let affordable = (cash - spent) / per;
    Ok(u64::try_from(affordable).map_or(most, |count| count.min(most)))
}

/// The processes in the order they are reckoned: every provider of a service input before its buyers, ties and
/// cycles by process id. `depends` maps each process to the processes that provide its service inputs.
pub(crate) fn provider_first(depends: &BTreeMap<ProcessId, BTreeSet<ProcessId>>) -> Vec<ProcessId> {
    let mut left: BTreeSet<ProcessId> = depends.keys().copied().collect();
    let mut order = Vec::with_capacity(left.len());
    while let Some(first) = left.iter().next().copied() {
        let ready = left.iter().copied().find(|process| {
            depends[process]
                .iter()
                .all(|provider| *provider == *process || !left.contains(provider))
        });
        let next = ready.unwrap_or(first);
        left.remove(&next);
        order.push(next);
    }
    order
}

/// What the reckoning notes about one workplace (site, labor unit).
#[derive(Default)]
struct Notes {
    asked: BTreeMap<(SiteId, UnitId), u64>,
    cut: BTreeMap<(SiteId, UnitId), u64>,
    by: BTreeMap<(SiteId, UnitId), HiringLimit>,
}

impl Notes {
    /// The last limit other than `None` in the reckoning order is the workplace's.
    fn note(&mut self, key: (SiteId, UnitId), limit: HiringLimit) {
        let entry = self.by.entry(key).or_insert(HiringLimit::None);
        if limit != HiringLimit::None {
            *entry = limit;
        }
    }

    fn ask(&mut self, key: (SiteId, UnitId), hours: u64) -> Result<()> {
        add_to(&mut self.asked, key, hours)
    }
}

fn add_to(
    rows: &mut BTreeMap<(SiteId, UnitId), u64>,
    key: (SiteId, UnitId),
    hours: u64,
) -> Result<()> {
    let row = rows.entry(key).or_insert(0);
    *row = row
        .checked_add(hours)
        .ok_or(MaterialCircuitError::Arithmetic)?;
    Ok(())
}

/// What the bound reads, fixed for one reckoning.
struct Reading<'a> {
    catalog: &'a MaterialCatalog,
    state: &'a MaterialCircuitState,
    economy: &'a MonetaryCircuit,
    recurring: &'a RecurringEconomy,
    performance: &'a [ServicePerformanceReceipt],
    wages: BTreeMap<(SiteId, UnitId), i128>,
    next_period: u64,
}

/// What one maker's request comes to.
struct Maker {
    batches: u64,
    hours: u64,
    cost: i128,
    limit: HiringLimit,
}

impl Reading<'_> {
    fn labor_per_batch(&self, process: ProcessId, unit: UnitId) -> u64 {
        self.catalog
            .labor_coefficients
            .iter()
            .filter(|row| row.process_id == process && row.unit_id == unit)
            .map(|row| row.quantity_per_batch)
            .sum()
    }

    fn price(&self, site: SiteId, good: GoodId, unit: UnitId) -> Option<i128> {
        self.recurring
            .offers
            .iter()
            .find(|row| row.site_id == site && row.good_id == good && row.unit_id == unit)
            .map(|row| row.unit_price.micro_units())
    }

    fn planned_batches(&self, process: ProcessId) -> u64 {
        self.recurring
            .production
            .iter()
            .find(|row| row.process_id == process)
            .map_or(0, |row| row.planned_batches)
    }

    fn cash(&self, site: SiteId) -> Result<i128> {
        Ok(self.economy.book.cash(AccountId::Site(site))?.micro_units())
    }

    /// The service inputs of a process at its site: each with its policy.
    fn service_inputs(
        &self,
        process: ProcessId,
        site: SiteId,
    ) -> impl Iterator<Item = (&InputOutputCoefficient, &ServiceInputPolicy)> {
        self.catalog
            .input_coefficients
            .iter()
            .filter(move |row| row.process_id == process && row.quantity_per_batch > 0)
            .filter(|row| crate::services::is_service(self.catalog, row.good_id, row.unit_id))
            .filter_map(move |row| {
                self.catalog
                    .service_inputs
                    .iter()
                    .find(|policy| {
                        policy.buyer_site_id == site
                            && policy.good_id == row.good_id
                            && policy.unit_id == row.unit_id
                    })
                    .map(|policy| (row, policy))
            })
    }

    /// The processes that provide the service inputs of each requested process.
    fn dependencies(
        &self,
        requests: &[ProcessLaborRequest],
    ) -> BTreeMap<ProcessId, BTreeSet<ProcessId>> {
        let mut depends: BTreeMap<ProcessId, BTreeSet<ProcessId>> = BTreeMap::new();
        for request in requests {
            let providers = depends.entry(request.process_id).or_default();
            for (input, policy) in self.service_inputs(request.process_id, request.site_id) {
                providers.extend(
                    self.catalog
                        .process_outputs
                        .iter()
                        .filter(|out| {
                            out.site_id == policy.provider_site_id
                                && out.good_id == input.good_id
                                && out.unit_id == input.unit_id
                        })
                        .map(|out| out.process_id),
                );
            }
        }
        depends
    }

    /// What the provider plans to make of a service for the next period: as far as its capacity runs it, and as
    /// far as its own bound works it where that is reckoned already.
    fn made(
        &self,
        provider: SiteId,
        input: &InputOutputCoefficient,
        bound: &BTreeMap<ProcessId, (u64, u64)>,
    ) -> Result<u64> {
        let mut made = 0_u64;
        for out in self.catalog.process_outputs.iter().filter(|out| {
            out.site_id == provider && out.good_id == input.good_id && out.unit_id == input.unit_id
        }) {
            let nameplate = crate::capacity::process_available(
                self.catalog,
                self.state,
                out.process_id,
                out.site_id,
                self.next_period,
            )?;
            let mut batches = self.planned_batches(out.process_id).min(nameplate);
            if let Some(&(own, _)) = bound.get(&out.process_id) {
                batches = batches.min(own);
            }
            let quantity = batches
                .checked_mul(out.quantity_per_batch)
                .ok_or(MaterialCircuitError::Arithmetic)?;
            made = made
                .checked_add(quantity)
                .ok_or(MaterialCircuitError::Arithmetic)?;
        }
        Ok(made)
    }

    /// What the provider performed in the closed period for buyers other than this site.
    fn others(&self, provider: SiteId, input: &InputOutputCoefficient, site: SiteId) -> u64 {
        self.performance
            .iter()
            .filter(|row| {
                row.provider_site_id == provider
                    && row.good_id == input.good_id
                    && row.unit_id == input.unit_id
                    && row.buyer != AccountId::Site(site)
            })
            .map(|row| row.performed_quantity)
            .fold(0_u64, u64::saturating_add)
    }

    /// One maker's request: the batches capacity, inputs and money allow, and what set the cut.
    fn maker(
        &self,
        request: &ProcessLaborRequest,
        per_batch_labor: u64,
        bound: &BTreeMap<ProcessId, (u64, u64)>,
        spent: i128,
    ) -> Result<Maker> {
        let asked = request.hours / per_batch_labor;
        let capacity = crate::capacity::process_available(
            self.catalog,
            self.state,
            request.process_id,
            request.site_id,
            self.next_period,
        )?;
        let wage = self
            .wages
            .get(&(request.site_id, request.unit_id))
            .copied()
            .unwrap_or(0);
        let mut by_inputs = u64::MAX;
        let mut per = i128::from(per_batch_labor)
            .checked_mul(wage)
            .ok_or(MaterialCircuitError::Arithmetic)?;
        for (input, policy) in self.service_inputs(request.process_id, request.site_id) {
            let provider = policy.provider_site_id;
            let for_me = self
                .made(provider, input, bound)?
                .saturating_sub(self.others(provider, input, request.site_id))
                .min(policy.quantity_per_period)
                .min(policy.maximum_purchase);
            by_inputs = by_inputs.min(for_me / input.quantity_per_batch);
            let price = self
                .price(provider, input.good_id, input.unit_id)
                .ok_or(MaterialCircuitError::PurchaseInvariant)?;
            per = i128::from(input.quantity_per_batch)
                .checked_mul(price)
                .and_then(|cost| per.checked_add(cost))
                .ok_or(MaterialCircuitError::Arithmetic)?;
        }
        let before_money = asked.min(capacity).min(by_inputs);
        let batches = batches_within(before_money, per, spent, self.cash(request.site_id)?)?;
        let hours = batches
            .checked_mul(per_batch_labor)
            .ok_or(MaterialCircuitError::Arithmetic)?
            .min(request.hours);
        let limit = if batches < before_money {
            HiringLimit::Money
        } else if before_money < asked {
            if capacity <= by_inputs {
                HiringLimit::Capacity
            } else {
                HiringLimit::Inputs
            }
        } else if hours < request.hours {
            HiringLimit::Other
        } else {
            HiringLimit::None
        };
        let cost = i128::from(batches)
            .checked_mul(per)
            .ok_or(MaterialCircuitError::Arithmetic)?;
        Ok(Maker {
            batches,
            hours,
            cost,
            limit,
        })
    }

    /// The makers, providers before their buyers. Gives what each site's requests took of its money.
    fn reckon_makers(
        &self,
        requests: &[ProcessLaborRequest],
        bound: &mut BTreeMap<ProcessId, (u64, u64)>,
        notes: &mut Notes,
    ) -> Result<BTreeMap<SiteId, i128>> {
        let mut spent: BTreeMap<SiteId, i128> = BTreeMap::new();
        for process in provider_first(&self.dependencies(requests)) {
            for request in requests.iter().filter(|row| row.process_id == process) {
                let key = (request.site_id, request.unit_id);
                notes.ask(key, request.hours)?;
                let per_batch_labor = self.labor_per_batch(process, request.unit_id);
                if per_batch_labor == 0 {
                    bound.insert(process, (u64::MAX, request.hours));
                    continue;
                }
                let before = spent.get(&request.site_id).copied().unwrap_or(0);
                let maker = self.maker(request, per_batch_labor, bound, before)?;
                let total = before
                    .checked_add(maker.cost)
                    .ok_or(MaterialCircuitError::Arithmetic)?;
                spent.insert(request.site_id, total);
                bound.insert(process, (maker.batches, maker.hours));
                add_to(&mut notes.cut, key, request.hours - maker.hours)?;
                notes.note(key, maker.limit);
            }
        }
        Ok(spent)
    }

    /// The planned attendance hours of a workplace for the next period.
    fn planned(&self, key: (SiteId, UnitId)) -> u64 {
        self.recurring
            .attendance
            .iter()
            .find(|row| (row.site_id, row.unit_id) == key && row.period == self.next_period)
            .map_or(0, |row| row.planned_hours)
    }

    /// The merchants: handling the sale needs, at what their money pays.
    fn reckon_merchants(
        &self,
        requests: &[ProcessLaborRequest],
        maintenance: Option<&MaintenanceReceipt>,
        spent: &BTreeMap<SiteId, i128>,
        notes: &mut Notes,
    ) -> Result<()> {
        let planning =
            crate::production::planning_inventory(self.catalog, self.state, self.next_period)?;
        let mut other_work: BTreeMap<(SiteId, UnitId), u64> = BTreeMap::new();
        for request in requests {
            add_to(
                &mut other_work,
                (request.site_id, request.unit_id),
                request.hours,
            )?;
        }
        for (_, site, unit, hours) in crate::equipment::work_requests(self.catalog, self.state)? {
            add_to(&mut other_work, (site, unit), hours)?;
            notes.ask((site, unit), hours)?;
        }
        if let Some(receipt) = maintenance {
            let key = (
                receipt.binding.provider_site_id,
                receipt.binding.labor_unit_id,
            );
            let hours = receipt
                .requested_jobs
                .checked_mul(receipt.binding.labor_units_per_job)
                .ok_or(MaterialCircuitError::Arithmetic)?;
            add_to(&mut other_work, key, hours)?;
            notes.ask(key, hours)?;
        }
        for merchant in &self.catalog.merchants {
            let key = (merchant.site_id, merchant.labor_unit_id);
            let handling = self
                .planned(key)
                .saturating_sub(other_work.get(&key).copied().unwrap_or(0));
            notes.ask(key, handling)?;
            let mut to_handle = 0_u64;
            for row in self
                .catalog
                .handling_coefficients
                .iter()
                .filter(|row| row.site_id == merchant.site_id)
            {
                let held = planning
                    .get(&(row.site_id, row.good_id, row.unit_id))
                    .copied()
                    .unwrap_or(0);
                to_handle = held
                    .checked_mul(row.hours_per_unit)
                    .and_then(|hours| to_handle.checked_add(hours))
                    .ok_or(MaterialCircuitError::Arithmetic)?;
            }
            let before_money = handling.min(to_handle);
            let wage = self.wages.get(&key).copied().unwrap_or(0);
            let hours = batches_within(
                before_money,
                wage,
                spent.get(&merchant.site_id).copied().unwrap_or(0),
                self.cash(merchant.site_id)?,
            )?;
            add_to(&mut notes.cut, key, handling - hours)?;
            let limit = if hours < before_money {
                HiringLimit::Money
            } else if before_money < handling {
                HiringLimit::Inputs
            } else {
                HiringLimit::None
            };
            notes.note(key, limit);
        }
        Ok(())
    }
}

/// Reckon the bound and lower the next period's attendance plans by it.
///
/// # Errors
/// `Arithmetic` for sums that do not fit; `PurchaseInvariant` for a service input whose provider posts no price;
/// the circuit's own refusals of capacity and inventory reads.
pub(crate) fn bound_hiring(
    catalog: &MaterialCatalog,
    state: &mut MaterialCircuitState,
    performance: &[ServicePerformanceReceipt],
    maintenance: Option<&MaintenanceReceipt>,
    next_period: u64,
) -> Result<HiringBound> {
    let mut bound = HiringBound {
        next_period,
        process: BTreeMap::new(),
        rows: Vec::new(),
    };
    let notes = {
        let CircuitAccounting::Monetary(economy) = &state.accounting else {
            return Ok(bound);
        };
        let Some(recurring) = economy.recurring.as_ref() else {
            return Ok(bound);
        };
        let reading = Reading {
            catalog,
            state,
            economy,
            recurring,
            performance,
            wages: crate::recurring::spare_money::wages(economy),
            next_period,
        };
        let requests =
            crate::production::derive_shared_labor_requests(catalog, state, next_period)?;
        let mut notes = Notes::default();
        let spent = reading.reckon_makers(&requests, &mut bound.process, &mut notes)?;
        reading.reckon_merchants(&requests, maintenance, &spent, &mut notes)?;
        notes
    };
    let CircuitAccounting::Monetary(economy) = &mut state.accounting else {
        return Ok(bound);
    };
    let recurring = economy
        .recurring
        .as_mut()
        .ok_or(MaterialCircuitError::MonetaryInvariant)?;
    for row in recurring
        .attendance
        .iter_mut()
        .filter(|row| row.period == next_period)
    {
        let key = (row.site_id, row.unit_id);
        let lost = notes.cut.get(&key).copied().unwrap_or(0);
        let asked_hours = notes.asked.get(&key).copied().unwrap_or(row.planned_hours);
        row.planned_hours = row.planned_hours.saturating_sub(lost);
        let limit = if lost > 0 {
            notes.by.get(&key).copied().unwrap_or(HiringLimit::Other)
        } else {
            HiringLimit::None
        };
        bound.rows.push(HiringBoundReceipt {
            period: next_period,
            site_id: row.site_id,
            unit_id: row.unit_id,
            asked_hours,
            bound_hours: asked_hours.saturating_sub(lost),
            limit,
        });
    }
    Ok(bound)
}

#[cfg(test)]
mod tests {
    use super::{batches_within, provider_first};
    use crate::ProcessId;
    use std::collections::{BTreeMap, BTreeSet};

    #[test]
    fn the_opening_is_not_cut() {
        assert_eq!(batches_within(120, 10_000_000, 0, 1_200_000_000), Ok(120));
        assert_eq!(batches_within(4, 220_000_000, 0, 880_000_000), Ok(4));
        assert_eq!(batches_within(40, 22_000_000, 0, 880_000_000), Ok(40));
    }

    #[test]
    fn money_cuts_by_whole_batches() {
        assert_eq!(batches_within(40, 22_000_000, 0, 879_999_999), Ok(39));
    }

    #[test]
    fn money_spent_by_an_earlier_request_counts() {
        assert_eq!(
            batches_within(10, 10_000_000, 95_000_000, 100_000_000),
            Ok(0)
        );
    }

    #[test]
    fn a_free_batch_is_not_cut() {
        assert_eq!(batches_within(7, 0, 0, 0), Ok(7));
    }

    #[test]
    fn providers_come_before_their_buyers() {
        let low = ProcessId::from_bytes([1; 32]);
        let mid = ProcessId::from_bytes([2; 32]);
        let high = ProcessId::from_bytes([3; 32]);
        // `low` buys from `high`; `mid` buys from nobody. Process id order alone would reckon `low` first.
        let depends = BTreeMap::from([
            (low, BTreeSet::from([high])),
            (mid, BTreeSet::new()),
            (high, BTreeSet::new()),
        ]);
        assert_eq!(provider_first(&depends), vec![mid, high, low]);
        // A cycle falls back to process id order.
        let cycle = BTreeMap::from([(low, BTreeSet::from([high])), (high, BTreeSet::from([low]))]);
        assert_eq!(provider_first(&cycle), vec![low, high]);
    }
}
