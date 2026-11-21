//! Carrying amounts move at the corresponding physical phase, inside its atomic close.
use super::book::StockKey;
use super::prices::GoodsCostLedger;
use super::HistoricalCostBook;
use super::IncomeReceipt;
use super::IncomeStatement;
use super::Result;
use super::{CompanyBasisAsset, CompanyBasisMovement, CompanySale};
use crate::payments::AttendanceLedger;
use crate::payments::LaborUse;
use crate::AgencyAttendanceOutcome;
use crate::AgencyObservationFundingReceipt;
use crate::AidFreightLot;
use crate::AidMandate;
use crate::EquipmentWearReceipt;
use crate::GoodId;
use crate::HouseholdConsumptionReceipt;
use crate::LaborUseReceipt;
use crate::LocalTransferReceipt;
use crate::MaintenanceReceipt;
use crate::MaterialCatalog;
use crate::MoneyLocation;
use crate::MoneyTransferPurpose;
use crate::MoneyTransferReceipt;
use crate::ServicePerformanceReceipt;
use crate::{
    AccountId, CircuitAccounting, FinalDemandOrder, FreightLotId, MaterialCircuitError,
    MaterialCircuitState, MemberLaborUseReceipt, OrderId, OrderRow, OutboundOrderId, ProcessOutput,
    RoutedFreightLot, SiteId, UnitId, WageAccrualReceipt, MAX_MATERIAL_CIRCUIT_ROWS,
};
use babylon_kernel::currency::Currency;
use std::collections::BTreeMap;
use std::collections::BTreeSet;

pub(crate) struct CostClose {
    pub(super) active: Option<ActiveCosts>,
    pub(super) attendance: AttendanceLedger,
    pub(crate) wear_receipts: Vec<EquipmentWearReceipt>,
    pub(super) goods: GoodsCostLedger,
    /// Household orders whose goods are used at the purchase and never stocked: wants.
    used_at_purchase: BTreeSet<OrderId>,
}
pub(super) struct ActiveCosts {
    pub(super) company_basis: Option<Vec<CompanyBasisMovement>>,
    pub(super) book: HistoricalCostBook,
    pub(super) income: BTreeMap<AccountId, IncomeStatement>,
    pub(super) contributions: BTreeMap<AccountId, Currency>,
    pub(super) distributions: BTreeMap<AccountId, Currency>,
}

impl CostClose {
    pub(crate) fn attendance_members(&self) -> &[MemberLaborUseReceipt] {
        self.attendance.members()
    }
    /// The wages and the hours this site has funded for the period, for one kind of labor.
    ///
    /// Every member row of the site and labor unit counts, working owners included: their hours
    /// are funded and their wage is 0.
    ///
    /// # Errors
    /// `Arithmetic` on overflow.
    pub(crate) fn funded_wage(&self, site: SiteId, unit: UnitId) -> Result<(Currency, u64)> {
        let mut wages = Currency::from_micro_units(0);
        let mut hours = 0_u64;
        for row in self.attendance.of_site_unit(site, unit) {
            wages = super::add(wages, row.accrued_wages)?;
            hours = hours
                .checked_add(row.attended_hours)
                .ok_or(MaterialCircuitError::Arithmetic)?;
        }
        Ok((wages, hours))
    }
    /// Tests only: a close whose attendance holds these member rows, for what reads the funded wages.
    #[cfg(test)]
    pub(crate) fn with_members(
        state: &MaterialCircuitState,
        catalog: &MaterialCatalog,
        members: Vec<MemberLaborUseReceipt>,
    ) -> Self {
        let mut costs = Self::new(state, catalog);
        costs.attendance = AttendanceLedger::from_members(members);
        costs
    }
    pub(crate) fn new(state: &MaterialCircuitState, catalog: &MaterialCatalog) -> Self {
        let active = match &state.accounting {
            CircuitAccounting::PhysicalControl => None,
            CircuitAccounting::Monetary(economy) => Some(ActiveCosts {
                book: economy.costs.clone(),
                company_basis: (!catalog.company_payouts.is_empty()).then(Vec::new),
                contributions: BTreeMap::new(),
                distributions: BTreeMap::new(),
                income: economy
                    .costs
                    .accounts
                    .keys()
                    .map(|&id| (id, IncomeStatement::empty()))
                    .collect(),
            }),
        };
        Self {
            active,
            wear_receipts: Vec::new(),
            goods: GoodsCostLedger::default(),
            attendance: AttendanceLedger::default(),
            used_at_purchase: BTreeSet::new(),
        }
    }

    /// The goods of this household order are used at the purchase, not stocked: the payment is the
    /// household's consumption expense.
    pub(crate) fn use_at_purchase(&mut self, order: OrderId) {
        self.used_at_purchase.insert(order);
    }

    pub(crate) fn take_company_basis(&mut self) -> Vec<CompanyBasisMovement> {
        self.active
            .as_mut()
            .and_then(|a| a.company_basis.take())
            .unwrap_or_default()
    }
    pub(crate) fn admit_attendance(&mut self, attendance: AttendanceLedger) {
        self.attendance = attendance;
    }

    pub(crate) fn finish_attendance(
        &mut self,
        state: &MaterialCircuitState,
    ) -> Result<(Vec<LaborUseReceipt>, Vec<MemberLaborUseReceipt>)> {
        std::mem::take(&mut self.attendance).finish(state)
    }

    pub(crate) fn input(
        &mut self,
        key: StockKey,
        available: u64,
        quantity: u64,
        destination: CompanyBasisAsset,
    ) -> Result<Currency> {
        self.active.as_mut().map_or(Ok(super::zero()), |a| {
            a.withdraw(key, available, quantity, Some(destination), None)
        })
    }

    pub(crate) fn output(
        &mut self,
        catalog: &MaterialCatalog,
        output: &ProcessOutput,
        batches: u64,
        inputs: Currency,
    ) -> Result<()> {
        if batches == 0 {
            return Ok(());
        }
        let Some(active) = &mut self.active else {
            return Ok(());
        };
        let labor_index = catalog
            .labor_coefficients
            .binary_search_by_key(&output.process_id, |r| r.process_id)
            .map_err(|_| MaterialCircuitError::ProcessInvariant)?;
        let labor = &catalog.labor_coefficients[labor_index];
        let hours = labor
            .quantity_per_batch
            .checked_mul(batches)
            .ok_or(MaterialCircuitError::Arithmetic)?;
        let wages =
            self.attendance
                .consume(output.site_id, labor.unit_id, hours, LaborUse::Production)?;
        let key = (
            AccountId::Site(output.site_id),
            output.good_id,
            output.unit_id,
        );
        let carrying = super::add(inputs, wages)?;
        active.entire(
            CompanyBasisAsset::Process(output.site_id, output.process_id),
            CompanyBasisAsset::Stock(output.site_id, output.good_id, output.unit_id),
            inputs,
        )?;
        active.book.credit_stock(key, carrying)?;
        let quantity = output
            .quantity_per_batch
            .checked_mul(batches)
            .ok_or(MaterialCircuitError::Arithmetic)?;
        self.goods.produced(
            (output.site_id, output.good_id, output.unit_id),
            quantity,
            carrying,
        )?;
        let statement = active.statement(key.0)?;
        statement.productive_labor_capitalized =
            super::add(statement.productive_labor_capitalized, wages)?;
        Ok(())
    }

    pub(crate) fn service_carrying(&self, key: StockKey) -> Currency {
        self.active
            .as_ref()
            .and_then(|a| a.book.stocks.get(&key).copied())
            .unwrap_or_else(super::zero)
    }
    pub(crate) fn service_handoff(
        &mut self,
        row: &ServicePerformanceReceipt,
        available: u64,
    ) -> Result<()> {
        if row.performed_quantity == 0 {
            return Ok(());
        }
        let Some(active) = &mut self.active else {
            return Err(MaterialCircuitError::MonetaryInvariant);
        };
        let owner = AccountId::Site(row.provider_site_id);
        let payment = super::amount(row.performed_quantity, row.unit_price)?;
        let order = OutboundOrderId::Service(row.order_id);
        let destination = match row.buyer {
            AccountId::Site(site) => Some(CompanyBasisAsset::Handoff(site, order)),
            _ => None,
        };
        let cost = active.withdraw(
            (owner, row.good_id, row.unit_id),
            available,
            row.performed_quantity,
            destination,
            Some(CompanySale {
                order,
                buyer: row.buyer,
                proceeds: payment,
            }),
        )?;
        active.sale(owner, payment, cost)
    }
    pub(crate) fn receive_service(&mut self, row: &ServicePerformanceReceipt) -> Result<()> {
        if row.performed_quantity == 0 {
            return Ok(());
        }
        let active = self
            .active
            .as_mut()
            .ok_or(MaterialCircuitError::MonetaryInvariant)?;
        let payment = super::amount(row.performed_quantity, row.unit_price)?;
        if let AccountId::Site(site) = row.buyer {
            active.entire(
                CompanyBasisAsset::Handoff(site, OutboundOrderId::Service(row.order_id)),
                CompanyBasisAsset::Stock(site, row.good_id, row.unit_id),
                payment,
            )?;
        }
        active
            .book
            .credit_stock((row.buyer, row.good_id, row.unit_id), payment)
    }
    pub(crate) fn consume_service(
        &mut self,
        key: StockKey,
        available: u64,
        quantity: u64,
        finite_sink: bool,
    ) -> Result<()> {
        let Some(active) = &mut self.active else {
            return Ok(());
        };
        let cost = active.withdraw(key, available, quantity, None, None)?;
        let statement = active.statement(key.0)?;
        if finite_sink {
            statement.final_demand_outlay = super::add(statement.final_demand_outlay, cost)?;
        } else {
            statement.consumption_expense = super::add(statement.consumption_expense, cost)?;
        }
        Ok(())
    }
    pub(crate) fn expire_service(&mut self, key: StockKey, quantity: u64) -> Result<()> {
        let Some(active) = &mut self.active else {
            return Ok(());
        };
        let cost = active.withdraw(key, quantity, quantity, None, None)?;
        let statement = active.statement(key.0)?;
        statement.unused_service_expense = super::add(statement.unused_service_expense, cost)?;
        Ok(())
    }
    pub(crate) fn clear_service_rows(
        &mut self,
        services: &BTreeSet<(GoodId, UnitId)>,
    ) -> Result<()> {
        let Some(active) = &mut self.active else {
            return Ok(());
        };
        for (key, cost) in &active.book.stocks {
            if services.contains(&(key.1, key.2)) && *cost != super::zero() {
                return Err(MaterialCircuitError::ValuationInvariant);
            }
        }
        active
            .book
            .stocks
            .retain(|key, _| !services.contains(&(key.1, key.2)));
        Ok(())
    }

    pub(crate) fn dispatch(
        &mut self,
        key: StockKey,
        available: u64,
        quantity: u64,
        lot: FreightLotId,
    ) -> Result<()> {
        let Some(active) = &mut self.active else {
            return Ok(());
        };
        let AccountId::Site(owner) = key.0 else {
            return Err(MaterialCircuitError::ValuationInvariant);
        };
        if active.book.freight.len() >= MAX_MATERIAL_CIRCUIT_ROWS {
            return Err(MaterialCircuitError::RowLimit);
        }
        let cost = active.withdraw(
            key,
            available,
            quantity,
            Some(CompanyBasisAsset::Freight(owner, lot)),
            None,
        )?;
        if active
            .book
            .freight
            .insert(lot, (AccountId::Site(owner), cost))
            .is_some()
        {
            return Err(MaterialCircuitError::DuplicateRow);
        }
        self.goods.released((owner, key.1, key.2), quantity, cost)
    }

    pub(crate) fn freight(
        &mut self,
        state: &MaterialCircuitState,
        lot: &RoutedFreightLot,
        lost_quantity: u64,
        final_arrival: bool,
    ) -> Result<()> {
        let Some(active) = &mut self.active else {
            return Ok(());
        };
        let &(owner, opening) = active
            .book
            .freight
            .get(&lot.lot_id)
            .ok_or(MaterialCircuitError::ValuationInvariant)?;
        let lost_cost = super::portion(opening, lot.quantity, lost_quantity)?;
        let remaining = lot
            .quantity
            .checked_sub(lost_quantity)
            .ok_or(MaterialCircuitError::Arithmetic)?;
        let retained = super::sub(opening, lost_cost)?;
        let source = CompanyBasisAsset::Freight(lot.source_site_id, lot.lot_id);
        active.transfer(&CompanyBasisMovement {
            source,
            destination: None,
            sale: None,
            available: lot.quantity,
            quantity: lost_quantity,
            opening,
        })?;
        let statement = active.statement(owner)?;
        statement.freight_loss_expense = super::add(statement.freight_loss_expense, lost_cost)?;
        if remaining == 0 || final_arrival {
            active.book.freight.remove(&lot.lot_id);
        } else {
            active.book.freight.insert(lot.lot_id, (owner, retained));
        }
        if final_arrival && remaining > 0 {
            let payment =
                purchase_amount(state, OutboundOrderId::Delivery(lot.order_id), remaining)?;
            if owner != AccountId::Site(lot.source_site_id) {
                return Err(MaterialCircuitError::ValuationInvariant);
            }
            active.transfer(&CompanyBasisMovement {
                source,
                destination: Some(CompanyBasisAsset::Stock(
                    lot.destination_site_id,
                    lot.good_id,
                    lot.unit_id,
                )),
                sale: Some(CompanySale {
                    order: OutboundOrderId::Delivery(lot.order_id),
                    buyer: AccountId::Site(lot.destination_site_id),
                    proceeds: payment,
                }),
                available: remaining,
                quantity: remaining,
                opening: retained,
            })?;
            active.sale(owner, payment, retained)?;
            active.book.credit_stock(
                (
                    AccountId::Site(lot.destination_site_id),
                    lot.good_id,
                    lot.unit_id,
                ),
                payment,
            )?;
        }
        Ok(())
    }

    pub(crate) fn dispatch_aid(
        &mut self,
        mandate: &AidMandate,
        available: u64,
        quantity: u64,
        lot: FreightLotId,
    ) -> Result<Currency> {
        let active = self
            .active
            .as_mut()
            .ok_or(MaterialCircuitError::ValuationInvariant)?;
        if active.book.freight.len() >= MAX_MATERIAL_CIRCUIT_ROWS {
            return Err(MaterialCircuitError::RowLimit);
        }
        if active.book.freight.contains_key(&lot) {
            return Err(MaterialCircuitError::DuplicateRow);
        }
        let owner = AccountId::Household(mandate.donor);
        let cost = active.book.take_stock(
            (owner, mandate.good_id, mandate.unit_id),
            available,
            quantity,
        )?;
        active.book.freight.insert(lot, (owner, cost));
        Ok(cost)
    }

    pub(crate) fn local_aid(
        &mut self,
        mandate: &AidMandate,
        available: u64,
        quantity: u64,
    ) -> Result<Currency> {
        let active = self
            .active
            .as_mut()
            .ok_or(MaterialCircuitError::ValuationInvariant)?;
        let carrying = active.book.take_stock(
            (
                AccountId::Household(mandate.donor),
                mandate.good_id,
                mandate.unit_id,
            ),
            available,
            quantity,
        )?;
        self.grant_aid(mandate, carrying)?;
        Ok(carrying)
    }

    pub(crate) fn cash_gift(
        &mut self,
        sender: AccountId,
        recipient: AccountId,
        cash: Currency,
    ) -> Result<()> {
        if cash.micro_units() <= 0 || sender == recipient {
            return Err(MaterialCircuitError::CollectionInvariant);
        }
        let active = self
            .active
            .as_mut()
            .ok_or(MaterialCircuitError::ValuationInvariant)?;
        let statement = active.statement(sender)?;
        statement.gift_expense = super::add(statement.gift_expense, cash)?;
        let statement = active.statement(recipient)?;
        statement.gift_income = super::add(statement.gift_income, cash)?;
        Ok(())
    }

    pub(crate) fn grant_aid(&mut self, mandate: &AidMandate, carrying: Currency) -> Result<()> {
        let active = self
            .active
            .as_mut()
            .ok_or(MaterialCircuitError::ValuationInvariant)?;
        active.book.credit_stock(
            (
                AccountId::Household(mandate.recipient),
                mandate.good_id,
                mandate.unit_id,
            ),
            carrying,
        )?;
        let donor = active.statement(AccountId::Household(mandate.donor))?;
        donor.gift_expense = super::add(donor.gift_expense, carrying)?;
        let recipient = active.statement(AccountId::Household(mandate.recipient))?;
        recipient.gift_income = super::add(recipient.gift_income, carrying)?;
        Ok(())
    }

    pub(crate) fn aid_freight(
        &mut self,
        lot: &AidFreightLot,
        lost_quantity: u64,
        final_arrival: bool,
    ) -> Result<(Currency, Currency)> {
        let active = self
            .active
            .as_mut()
            .ok_or(MaterialCircuitError::ValuationInvariant)?;
        let &(owner, opening) = active
            .book
            .freight
            .get(&lot.lot_id)
            .ok_or(MaterialCircuitError::ValuationInvariant)?;
        if owner != AccountId::Household(lot.donor) {
            return Err(MaterialCircuitError::ValuationInvariant);
        }
        let lost_cost = super::portion(opening, lot.quantity, lost_quantity)?;
        let retained = super::sub(opening, lost_cost)?;
        let remaining = lot
            .quantity
            .checked_sub(lost_quantity)
            .ok_or(MaterialCircuitError::Arithmetic)?;
        let statement = active.statement(owner)?;
        statement.freight_loss_expense = super::add(statement.freight_loss_expense, lost_cost)?;
        if final_arrival || remaining == 0 {
            active.book.freight.remove(&lot.lot_id);
        } else {
            active.book.freight.insert(lot.lot_id, (owner, retained));
        }
        Ok((lost_cost, retained))
    }

    pub(crate) fn local_sale(
        &mut self,
        state: &MaterialCircuitState,
        order: &OrderRow,
        available: u64,
        quantity: u64,
    ) -> Result<()> {
        let Some(active) = &mut self.active else {
            return Ok(());
        };
        let owner = AccountId::Site(order.supplier_site_id);
        let id = OutboundOrderId::Delivery(order.order_id);
        let proceeds = purchase_amount(state, id, quantity)?;
        let cost = active.withdraw(
            (owner, order.good_id, order.unit_id),
            available,
            quantity,
            Some(CompanyBasisAsset::Handoff(order.buyer_site_id, id)),
            Some(CompanySale {
                order: id,
                buyer: AccountId::Site(order.buyer_site_id),
                proceeds,
            }),
        )?;
        active.sale(owner, proceeds, cost)?;
        self.goods.released(
            (order.supplier_site_id, order.good_id, order.unit_id),
            quantity,
            cost,
        )
    }

    pub(crate) fn receive_local(
        &mut self,
        state: &MaterialCircuitState,
        receipt: &LocalTransferReceipt,
    ) -> Result<()> {
        let Some(active) = &mut self.active else {
            return Ok(());
        };
        let paid = purchase_amount(
            state,
            OutboundOrderId::Delivery(receipt.order_id),
            receipt.quantity,
        )?;
        active.entire(
            CompanyBasisAsset::Handoff(
                receipt.buyer_site_id,
                OutboundOrderId::Delivery(receipt.order_id),
            ),
            CompanyBasisAsset::Stock(receipt.buyer_site_id, receipt.good_id, receipt.unit_id),
            paid,
        )?;
        active.book.credit_stock(
            (
                AccountId::Site(receipt.buyer_site_id),
                receipt.good_id,
                receipt.unit_id,
            ),
            paid,
        )
    }

    pub(crate) fn retail(
        &mut self,
        state: &MaterialCircuitState,
        order: &FinalDemandOrder,
        available: u64,
        quantity: u64,
    ) -> Result<()> {
        let Some(active) = &mut self.active else {
            return Ok(());
        };
        let seller = AccountId::Site(order.retailer_site_id);
        let buyer = AccountId::Household(order.demand_principal_id);
        let payment = purchase_amount(
            state,
            OutboundOrderId::LocalFinalDemand(order.order_id),
            quantity,
        )?;
        let cost = active.withdraw(
            (seller, order.good_id, order.unit_id),
            available,
            quantity,
            None,
            Some(CompanySale {
                order: OutboundOrderId::LocalFinalDemand(order.order_id),
                buyer,
                proceeds: payment,
            }),
        )?;
        active.sale(seller, payment, cost)?;
        self.goods.released(
            (order.retailer_site_id, order.good_id, order.unit_id),
            quantity,
            cost,
        )?;
        let key = (buyer, order.good_id, order.unit_id);
        if self.used_at_purchase.contains(&order.order_id) {
            let statement = active.statement(buyer)?;
            statement.consumption_expense = super::add(statement.consumption_expense, payment)?;
        } else if active.book.stocks.contains_key(&key) {
            active.book.credit_stock(key, payment)?;
        } else {
            let statement = active.statement(buyer)?;
            statement.final_demand_outlay = super::add(statement.final_demand_outlay, payment)?;
        }
        Ok(())
    }

    pub(crate) fn consume(&mut self, receipt: &HouseholdConsumptionReceipt) -> Result<()> {
        let Some(active) = &mut self.active else {
            return Ok(());
        };
        let owner = AccountId::Household(receipt.principal_id);
        let cost = active.book.take_stock(
            (owner, receipt.good_id, receipt.unit_id),
            receipt.available_quantity,
            receipt.consumed_quantity,
        )?;
        let statement = active.statement(owner)?;
        statement.consumption_expense = super::add(statement.consumption_expense, cost)?;
        Ok(())
    }

    pub(crate) fn handling(
        &mut self,
        key: (SiteId, GoodId, UnitId),
        unit: UnitId,
        quantity: u64,
        hours: u64,
    ) -> Result<()> {
        let site = key.0;
        let Some(active) = &mut self.active else {
            return Ok(());
        };
        let wages = self
            .attendance
            .consume(site, unit, hours, LaborUse::Handling)?;
        let statement = active.statement(AccountId::Site(site))?;
        statement.handling_expense = super::add(statement.handling_expense, wages)?;
        self.goods.handled(key, quantity, wages)
    }

    pub(crate) fn maintenance(
        &mut self,
        _state: &MaterialCircuitState,
        receipt: &MaintenanceReceipt,
    ) -> Result<()> {
        let Some(active) = &mut self.active else {
            return Ok(());
        };
        let binding = &receipt.binding;
        let owner = AccountId::Site(binding.provider_site_id);
        let materials = active.withdraw(
            (owner, binding.spare_good_id, binding.spare_unit_id),
            receipt.available_spare_parts,
            receipt.consumed_spare_parts,
            None,
            None,
        )?;
        let wages = self.attendance.consume(
            binding.provider_site_id,
            binding.labor_unit_id,
            receipt.consumed_labor_hours,
            LaborUse::Maintenance,
        )?;
        let statement = active.statement(owner)?;
        statement.maintenance_material_expense =
            super::add(statement.maintenance_material_expense, materials)?;
        statement.maintenance_labor_expense =
            super::add(statement.maintenance_labor_expense, wages)?;
        Ok(())
    }

    pub(crate) fn payroll(
        &mut self,
        state: &MaterialCircuitState,
        labor: &[MemberLaborUseReceipt],
        accruals: &[WageAccrualReceipt],
        agency: Option<&AgencyObservationFundingReceipt>,
        transfers: &[MoneyTransferReceipt],
    ) -> Result<()> {
        let Some(active) = &mut self.active else {
            return Ok(());
        };
        let mut wages = BTreeMap::new();
        for row in accruals {
            if row.period != state.period {
                return Err(MaterialCircuitError::ValuationInvariant);
            }
            let total = wages.entry(row.employer).or_insert_with(super::zero);
            *total = super::add(*total, row.amount)?;
            let statement = active.statement(row.payee)?;
            statement.wage_income = super::add(statement.wage_income, row.amount)?;
        }
        if let Some(receipt) = agency {
            let input = &receipt.input;
            let matching: Vec<_> = accruals
                .iter()
                .filter(|row| row.shift == input.shift_id)
                .collect();
            let payments: Vec<_> = transfers
                .iter()
                .filter(|row| row.purpose == MoneyTransferPurpose::WagePayment(input.shift_id))
                .collect();
            if receipt.outcome == AgencyAttendanceOutcome::Paid {
                if matching.len() != 1
                    || payments.len() != 1
                    || matching[0].employer != AccountId::Organization(input.agency)
                    || matching[0].payee != AccountId::Household(input.principal_id)
                    || matching[0].period != input.due_period
                    || matching[0].obligated_hours != input.hours
                    || matching[0].amount != receipt.paid
                    || receipt.paid != receipt.reserved
                    || payments[0].debit.location != MoneyLocation::PayrollReserve(input.shift_id)
                    || payments[0].credit.location
                        != MoneyLocation::Cash(AccountId::Household(input.principal_id))
                    || payments[0].credit.delta != receipt.paid
                    || receipt.attended_hours != input.hours
                    || receipt.attendance.is_none()
                {
                    return Err(MaterialCircuitError::ValuationInvariant);
                }
                let statement = active.statement(AccountId::Organization(input.agency))?;
                statement.agency_observation_labor_expense =
                    super::add(statement.agency_observation_labor_expense, receipt.paid)?;
            } else if !matching.is_empty()
                || !payments.is_empty()
                || receipt.attended_hours != 0
                || receipt.attendance.is_some()
            {
                return Err(MaterialCircuitError::ValuationInvariant);
            }
        }
        for row in labor {
            row.validate()?;
            let idle = row.idle_wages;
            let statement = active.statement(AccountId::Site(row.site_id))?;
            statement.idle_labor_expense = super::add(statement.idle_labor_expense, idle)?;
        }
        for (account, statement) in &active.income {
            let classified = super::add(
                super::add(
                    statement.productive_labor_capitalized,
                    statement.idle_labor_expense,
                )?,
                super::add(
                    statement.handling_expense,
                    statement.maintenance_labor_expense,
                )?,
            )?;
            if super::add(
                super::add(classified, statement.installation_labor_capitalized)?,
                statement.agency_observation_labor_expense,
            )? != wages.get(account).copied().unwrap_or_else(super::zero)
            {
                return Err(MaterialCircuitError::ValuationInvariant);
            }
        }
        Ok(())
    }

    pub(crate) fn finish(
        self,
        catalog: &MaterialCatalog,
        state: &mut MaterialCircuitState,
    ) -> Result<Vec<IncomeReceipt>> {
        let Some(mut active) = self.active else {
            return Ok(vec![]);
        };
        let mut receipts = Vec::with_capacity(active.income.len());
        for (account, statement) in active.income {
            let row = active
                .book
                .accounts
                .get_mut(&account)
                .ok_or(MaterialCircuitError::ValuationInvariant)?;
            let net_income = statement.net_income()?;
            let contributions_received = active
                .contributions
                .get(&account)
                .copied()
                .unwrap_or_else(super::zero);
            let distributions_paid = active
                .distributions
                .get(&account)
                .copied()
                .unwrap_or_else(super::zero);
            let closing_contributed_capital =
                super::add(row.contributed_capital, contributions_received)?;
            let closing = super::sub(
                super::add(row.retained_earnings, net_income)?,
                distributions_paid,
            )?;
            receipts.push(IncomeReceipt {
                account,
                period: state.period,
                opening_capital: row.opening_capital,
                opening_retained_earnings: row.retained_earnings,
                opening_contributed_capital: row.contributed_capital,
                contributions_received,
                closing_contributed_capital,
                distributions_paid,
                statement,
                net_income,
                closing_retained_earnings: closing,
            });
            row.retained_earnings = closing;
            row.contributed_capital = closing_contributed_capital;
        }
        let CircuitAccounting::Monetary(economy) = &mut state.accounting else {
            return Err(MaterialCircuitError::ValuationInvariant);
        };
        economy.costs = active.book;
        super::validation::validate(catalog, state)?;
        Ok(receipts)
    }
}

impl ActiveCosts {
    pub(super) fn statement(&mut self, account: AccountId) -> Result<&mut IncomeStatement> {
        self.income
            .get_mut(&account)
            .ok_or(MaterialCircuitError::ValuationInvariant)
    }
    fn sale(&mut self, account: AccountId, revenue: Currency, cost: Currency) -> Result<()> {
        let statement = self.statement(account)?;
        statement.sales = super::add(statement.sales, revenue)?;
        statement.cost_of_goods_sold = super::add(statement.cost_of_goods_sold, cost)?;
        Ok(())
    }
}

fn purchase_amount(
    state: &MaterialCircuitState,
    order: OutboundOrderId,
    quantity: u64,
) -> Result<Currency> {
    let CircuitAccounting::Monetary(economy) = &state.accounting else {
        return Ok(super::zero());
    };
    super::amount(quantity, economy.book.purchase(order)?.unit_price)
}

#[cfg(test)]
mod funded_wage_tests {
    use super::*;
    use crate::{FinalDemandPrincipalId, LaborCompensation, StaffingMemberId};

    fn row(
        member: u8,
        site: u8,
        compensation: LaborCompensation,
        hours: u64,
    ) -> MemberLaborUseReceipt {
        let wages =
            Currency::from_micro_units(compensation.wage_rate().micro_units() * i128::from(hours));
        MemberLaborUseReceipt {
            member_id: StaffingMemberId::from_bytes([member; 32]),
            site_id: SiteId::from_bytes([site; 32]),
            unit_id: UnitId::from_bytes([2; 32]),
            payee: FinalDemandPrincipalId::from_bytes([member; 32]),
            compensation,
            period: 1,
            available_hours: hours,
            planned_hours: hours,
            unplanned_hours: 0,
            attended_hours: hours,
            unattended_hours: 0,
            production_hours: hours,
            handling_hours: 0,
            maintenance_hours: 0,
            installation_hours: 0,
            idle_hours: 0,
            accrued_wages: wages,
            production_wages: wages,
            handling_wages: Currency::from_micro_units(0),
            maintenance_wages: Currency::from_micro_units(0),
            installation_wages: Currency::from_micro_units(0),
            idle_wages: Currency::from_micro_units(0),
        }
    }

    #[test]
    fn a_working_owners_hours_count_and_their_wage_is_nothing() {
        let costs = CostClose {
            active: None,
            attendance: AttendanceLedger::from_members(vec![
                row(
                    1,
                    7,
                    LaborCompensation::Wage(Currency::from_micro_units(20_000_000)),
                    10,
                ),
                row(2, 7, LaborCompensation::WorkingOwner, 10),
                row(
                    3,
                    8,
                    LaborCompensation::Wage(Currency::from_micro_units(99_000_000)),
                    5,
                ),
            ]),
            wear_receipts: Vec::new(),
            goods: GoodsCostLedger::default(),
            used_at_purchase: BTreeSet::new(),
        };
        let (wages, hours) = costs
            .funded_wage(SiteId::from_bytes([7; 32]), UnitId::from_bytes([2; 32]))
            .expect("the rows add");
        assert_eq!((wages.micro_units(), hours), (200_000_000, 20));
        let none = costs
            .funded_wage(SiteId::from_bytes([9; 32]), UnitId::from_bytes([2; 32]))
            .expect("no rows add to nothing");
        assert_eq!((none.0.micro_units(), none.1), (0, 0));
    }
}
