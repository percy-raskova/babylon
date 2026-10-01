//! Carrying amounts move at the corresponding physical phase, inside its atomic close.
use super::book::StockKey;
use super::{
    add, amount, portion, sub, zero, HistoricalCostBook, IncomeReceipt, IncomeStatement, Result,
};
use crate::{
    AccountId, CircuitAccounting, FinalDemandOrder, FreightLotId, LaborUseReceipt,
    MaterialCircuitError, MaterialCircuitState, OrderRow, OutboundOrderId, ProcessOutput,
    RoutedFreightLot, SiteId, UnitId, WageAccrualReceipt, MAX_MATERIAL_CIRCUIT_ROWS,
};
use babylon_kernel::currency::Currency;
use std::collections::BTreeMap;

pub(crate) struct CostClose {
    active: Option<ActiveCosts>,
}
struct ActiveCosts {
    book: HistoricalCostBook,
    income: BTreeMap<AccountId, IncomeStatement>,
}

impl CostClose {
    pub(crate) fn new(state: &MaterialCircuitState) -> Self {
        let active = match &state.accounting {
            CircuitAccounting::PhysicalControl => None,
            CircuitAccounting::Monetary(economy) => Some(ActiveCosts {
                book: economy.costs.clone(),
                income: economy
                    .costs
                    .accounts
                    .keys()
                    .map(|&id| (id, IncomeStatement::empty()))
                    .collect(),
            }),
        };
        Self { active }
    }

    pub(crate) fn input(
        &mut self,
        key: StockKey,
        available: u64,
        quantity: u64,
    ) -> Result<Currency> {
        self.active
            .as_mut()
            .map_or(Ok(zero()), |a| a.book.take_stock(key, available, quantity))
    }

    pub(crate) fn output(
        &mut self,
        state: &MaterialCircuitState,
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
        let labor_index = state
            .labor_coefficients
            .binary_search_by_key(&output.process_id, |r| r.process_id)
            .map_err(|_| MaterialCircuitError::ProcessInvariant)?;
        let labor = &state.labor_coefficients[labor_index];
        let hours = labor
            .quantity_per_batch
            .checked_mul(batches)
            .ok_or(MaterialCircuitError::Arithmetic)?;
        let wages = wage_cost(state, output.site_id, labor.unit_id, hours)?;
        let key = (
            AccountId::Site(output.site_id),
            output.good_id,
            output.unit_id,
        );
        active.book.credit_stock(key, add(inputs, wages)?)?;
        let statement = active.statement(key.0)?;
        statement.productive_labor_capitalized =
            add(statement.productive_labor_capitalized, wages)?;
        Ok(())
    }

    pub(crate) fn service_carrying(&self, key: StockKey) -> Currency {
        self.active
            .as_ref()
            .and_then(|a| a.book.stocks.get(&key).copied())
            .unwrap_or_else(zero)
    }
    pub(crate) fn service_handoff(
        &mut self,
        row: &crate::ServicePerformanceReceipt,
        available: u64,
    ) -> Result<()> {
        if row.performed_quantity == 0 {
            return Ok(());
        }
        let Some(active) = &mut self.active else {
            return Err(MaterialCircuitError::MonetaryInvariant);
        };
        let owner = AccountId::Site(row.provider_site_id);
        let cost = active.book.take_stock(
            (owner, row.good_id, row.unit_id),
            available,
            row.performed_quantity,
        )?;
        let payment = amount(row.performed_quantity, row.unit_price)?;
        active.sale(owner, payment, cost)
    }
    pub(crate) fn receive_service(&mut self, row: &crate::ServicePerformanceReceipt) -> Result<()> {
        if row.performed_quantity == 0 {
            return Ok(());
        }
        let active = self
            .active
            .as_mut()
            .ok_or(MaterialCircuitError::MonetaryInvariant)?;
        active.book.credit_stock(
            (row.buyer, row.good_id, row.unit_id),
            amount(row.performed_quantity, row.unit_price)?,
        )
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
        let cost = active.book.take_stock(key, available, quantity)?;
        let statement = active.statement(key.0)?;
        if finite_sink {
            statement.final_demand_outlay = add(statement.final_demand_outlay, cost)?;
        } else {
            statement.consumption_expense = add(statement.consumption_expense, cost)?;
        }
        Ok(())
    }
    pub(crate) fn expire_service(&mut self, key: StockKey, quantity: u64) -> Result<()> {
        let Some(active) = &mut self.active else {
            return Ok(());
        };
        let cost = active.book.take_stock(key, quantity, quantity)?;
        let statement = active.statement(key.0)?;
        statement.unused_service_expense = add(statement.unused_service_expense, cost)?;
        Ok(())
    }
    pub(crate) fn clear_service_rows(
        &mut self,
        services: &std::collections::BTreeSet<(crate::GoodId, UnitId)>,
    ) -> Result<()> {
        let Some(active) = &mut self.active else {
            return Ok(());
        };
        for (key, cost) in &active.book.stocks {
            if services.contains(&(key.1, key.2)) && *cost != zero() {
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
        let cost = active.book.take_stock(key, available, quantity)?;
        if active.book.freight.insert(lot, (owner, cost)).is_some() {
            return Err(MaterialCircuitError::DuplicateRow);
        }
        Ok(())
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
        let lost_cost = portion(opening, lot.quantity, lost_quantity)?;
        let remaining = lot
            .quantity
            .checked_sub(lost_quantity)
            .ok_or(MaterialCircuitError::Arithmetic)?;
        let retained = sub(opening, lost_cost)?;
        let statement = active.statement(AccountId::Site(owner))?;
        statement.freight_loss_expense = add(statement.freight_loss_expense, lost_cost)?;
        if remaining == 0 || final_arrival {
            active.book.freight.remove(&lot.lot_id);
        } else {
            active.book.freight.insert(lot.lot_id, (owner, retained));
        }
        if final_arrival && remaining > 0 {
            let payment =
                purchase_amount(state, OutboundOrderId::Delivery(lot.order_id), remaining)?;
            active.sale(AccountId::Site(owner), payment, retained)?;
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
        let cost =
            active
                .book
                .take_stock((owner, order.good_id, order.unit_id), available, quantity)?;
        active.sale(
            owner,
            purchase_amount(state, OutboundOrderId::Delivery(order.order_id), quantity)?,
            cost,
        )
    }

    pub(crate) fn receive_local(
        &mut self,
        state: &MaterialCircuitState,
        receipt: &crate::LocalTransferReceipt,
    ) -> Result<()> {
        let Some(active) = &mut self.active else {
            return Ok(());
        };
        let paid = purchase_amount(
            state,
            OutboundOrderId::Delivery(receipt.order_id),
            receipt.quantity,
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
        let cost =
            active
                .book
                .take_stock((seller, order.good_id, order.unit_id), available, quantity)?;
        let payment = purchase_amount(
            state,
            OutboundOrderId::LocalFinalDemand(order.order_id),
            quantity,
        )?;
        active.sale(seller, payment, cost)?;
        let buyer = AccountId::Household(order.demand_principal_id);
        let key = (buyer, order.good_id, order.unit_id);
        if active.book.stocks.contains_key(&key) {
            active.book.credit_stock(key, payment)?;
        } else {
            let statement = active.statement(buyer)?;
            statement.final_demand_outlay = add(statement.final_demand_outlay, payment)?;
        }
        Ok(())
    }

    pub(crate) fn consume(&mut self, receipt: &crate::HouseholdConsumptionReceipt) -> Result<()> {
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
        statement.consumption_expense = add(statement.consumption_expense, cost)?;
        Ok(())
    }

    pub(crate) fn handling(
        &mut self,
        state: &MaterialCircuitState,
        site: SiteId,
        unit: UnitId,
        hours: u64,
    ) -> Result<()> {
        let Some(active) = &mut self.active else {
            return Ok(());
        };
        let wages = wage_cost(state, site, unit, hours)?;
        let statement = active.statement(AccountId::Site(site))?;
        statement.handling_expense = add(statement.handling_expense, wages)?;
        Ok(())
    }

    pub(crate) fn maintenance(
        &mut self,
        state: &MaterialCircuitState,
        receipt: &crate::MaintenanceReceipt,
    ) -> Result<()> {
        let Some(active) = &mut self.active else {
            return Ok(());
        };
        let binding = &receipt.binding;
        let owner = AccountId::Site(binding.provider_site_id);
        let materials = active.book.take_stock(
            (owner, binding.spare_good_id, binding.spare_unit_id),
            receipt.available_spare_parts,
            receipt.consumed_spare_parts,
        )?;
        let wages = wage_cost(
            state,
            binding.provider_site_id,
            binding.labor_unit_id,
            receipt.consumed_labor_hours,
        )?;
        let statement = active.statement(owner)?;
        statement.maintenance_material_expense =
            add(statement.maintenance_material_expense, materials)?;
        statement.maintenance_labor_expense = add(statement.maintenance_labor_expense, wages)?;
        Ok(())
    }

    pub(crate) fn payroll(
        &mut self,
        state: &MaterialCircuitState,
        labor: &[LaborUseReceipt],
        accruals: &[WageAccrualReceipt],
    ) -> Result<()> {
        let Some(active) = &mut self.active else {
            return Ok(());
        };
        let mut wages = BTreeMap::new();
        for row in accruals {
            if row.period != state.period {
                return Err(MaterialCircuitError::ValuationInvariant);
            }
            let total = wages.entry(row.employer).or_insert_with(zero);
            *total = add(*total, row.amount)?;
            let statement = active.statement(row.payee)?;
            statement.wage_income = add(statement.wage_income, row.amount)?;
        }
        for row in labor {
            let idle = wage_cost(state, row.site_id, row.unit_id, row.paid_idle_hours)?;
            let statement = active.statement(AccountId::Site(row.site_id))?;
            statement.idle_labor_expense = add(statement.idle_labor_expense, idle)?;
        }
        for (account, statement) in &active.income {
            let classified = add(
                add(
                    statement.productive_labor_capitalized,
                    statement.idle_labor_expense,
                )?,
                add(
                    statement.handling_expense,
                    statement.maintenance_labor_expense,
                )?,
            )?;
            if classified != wages.get(account).copied().unwrap_or_else(zero) {
                return Err(MaterialCircuitError::ValuationInvariant);
            }
        }
        Ok(())
    }

    pub(crate) fn finish(self, state: &mut MaterialCircuitState) -> Result<Vec<IncomeReceipt>> {
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
            let closing = add(row.retained_earnings, net_income)?;
            receipts.push(IncomeReceipt {
                account,
                period: state.period,
                opening_capital: row.opening_capital,
                opening_retained_earnings: row.retained_earnings,
                statement,
                net_income,
                closing_retained_earnings: closing,
            });
            row.retained_earnings = closing;
        }
        let CircuitAccounting::Monetary(economy) = &mut state.accounting else {
            return Err(MaterialCircuitError::ValuationInvariant);
        };
        economy.costs = active.book;
        super::validation::validate(state)?;
        Ok(receipts)
    }
}

impl ActiveCosts {
    fn statement(&mut self, account: AccountId) -> Result<&mut IncomeStatement> {
        self.income
            .get_mut(&account)
            .ok_or(MaterialCircuitError::ValuationInvariant)
    }
    fn sale(&mut self, account: AccountId, revenue: Currency, cost: Currency) -> Result<()> {
        let statement = self.statement(account)?;
        statement.sales = add(statement.sales, revenue)?;
        statement.cost_of_goods_sold = add(statement.cost_of_goods_sold, cost)?;
        Ok(())
    }
}

fn wage_cost(
    state: &MaterialCircuitState,
    site: SiteId,
    unit: UnitId,
    hours: u64,
) -> Result<Currency> {
    let CircuitAccounting::Monetary(economy) = &state.accounting else {
        return Ok(zero());
    };
    let index = economy
        .employment
        .binary_search_by_key(&(site, unit), |r| (r.site_id, r.unit_id))
        .map_err(|_| MaterialCircuitError::PayrollInvariant)?;
    let terms = &economy.employment[index];
    amount(hours, terms.hourly_rate)
}
fn purchase_amount(
    state: &MaterialCircuitState,
    order: OutboundOrderId,
    quantity: u64,
) -> Result<Currency> {
    let CircuitAccounting::Monetary(economy) = &state.accounting else {
        return Ok(zero());
    };
    amount(quantity, economy.book.purchase(order)?.unit_price)
}
