//! One initialization compiler. It creates current engine rows; it does not
//! adjudicate a period or retain another mutable state owner.
use super::{CatalogAccounting, CatalogCapacity, EconomicCatalogError, EconomicOpening};
use babylon_material_circuit::{
    decode_material_circuit_state, encode_material_circuit_state, AccountId, AttendancePlan,
    BacklogRow, CapacityRow, CapacitySupply, CashAccount, CircuitAccounting, CorridorCapacity,
    FinalDemandPrincipal, FinancialInstitutions, HistoricalCostBook, HouseholdCohort,
    HouseholdNeed, HouseholdStock, InputOutputCoefficient, InventoryRow, LaborCapacityRow,
    LaborCoefficient, MaintenanceService, MaterialCircuitState, MemberLaborCapacityRow,
    MerchantHandling, MerchantHandlingCoefficient, MonetaryBook, MonetaryCircuit, ProcessOutput,
    ProductionCommitment, ProductionDemandPolicy, RecurringEconomy, RollingCapacitySupply,
    SiteLogisticsNode, StockCarryingValue,
};
use babylon_tick::material_staffing::{
    StaffingComposition, StaffingMemberNodeBinding, StaffingNodeBinding,
};
use std::collections::{BTreeMap, BTreeSet};
type Result<T> = std::result::Result<T, EconomicCatalogError>;

/// Ephemeral checked output. The foundation keeps one canonical material register.
pub struct CompiledEconomicOpening {
    pub state: MaterialCircuitState,
    pub staffing: StaffingComposition,
}
impl EconomicOpening {
    /// Compile exact input rows through the sole current material admission codec.
    /// # Errors
    /// Refuses ambiguous identities, inconsistent principals, overflow or an
    /// engine invariant. Monetary opening orders require a separate funded import.
    pub fn compile(&self) -> Result<CompiledEconomicOpening> {
        let mut state = empty_state();
        state.commodities.clone_from(&self.commodities);
        append_sites(self, &mut state)?;
        append_households(self, &mut state)?;
        append_logistics(self, &mut state)?;
        let (staffing, member_labor) = append_staffing(self, &mut state)?;
        state.accounting = compile_accounting(self, &state, member_labor)?;
        let state = decode_material_circuit_state(&encode_material_circuit_state(&state)?)?;
        Ok(CompiledEconomicOpening { state, staffing })
    }
}

fn empty_state() -> MaterialCircuitState {
    MaterialCircuitState {
        capacity_supply: CapacitySupply::FiniteSchedule,
        period: 1,
        site_logistics_nodes: vec![],
        process_outputs: vec![],
        input_coefficients: vec![],
        labor_coefficients: vec![],
        service_connections: vec![],
        service_orders: vec![],
        commodities: vec![],
        supplier_routes: vec![],
        route_stages: vec![],
        route_stage_capacities: vec![],
        inventory: vec![],
        orders: vec![],
        backlog: vec![],
        freight: vec![],
        corridor_capacities: vec![],
        capacities: vec![],
        labor: vec![],
        production_commitments: vec![],
        merchants: vec![],
        handling_coefficients: vec![],
        final_demand_principals: vec![],
        final_demand_orders: vec![],
        accounting: CircuitAccounting::PhysicalControl,
        maintenance_binding: None,
        maintenance_service: None,
    }
}
fn append_sites(opening: &EconomicOpening, state: &mut MaterialCircuitState) -> Result<()> {
    let recipes: BTreeMap<_, _> = opening.recipes.iter().map(|r| (r.id, r)).collect();
    if recipes.len() != opening.recipes.len() {
        return Err(EconomicCatalogError::Opening("duplicate recipe"));
    }
    let mut subjects = BTreeSet::new();
    for site in &opening.sites {
        site.subject
            .canonical_bytes()
            .map_err(|_| EconomicCatalogError::Identity)?;
        if !subjects.insert(&site.subject) || site.label.is_empty() {
            return Err(EconomicCatalogError::Opening("site identity"));
        }
        state.site_logistics_nodes.push(SiteLogisticsNode {
            site_id: site.site_id,
            node_id: site.logistics_node_id,
        });
        for stock in &site.opening_stock {
            state.inventory.push(InventoryRow {
                site_id: site.site_id,
                good_id: stock.amount.good_id,
                unit_id: stock.amount.unit_id,
                quantity: stock.amount.quantity,
            });
        }
        for process in &site.processes {
            let recipe = recipes
                .get(&process.recipe)
                .ok_or(EconomicCatalogError::Opening("absent recipe"))?;
            state.process_outputs.push(ProcessOutput {
                process_id: process.process_id,
                site_id: site.site_id,
                good_id: recipe.output.good_id,
                unit_id: recipe.output.unit_id,
                quantity_per_batch: recipe.output.quantity,
            });
            state
                .input_coefficients
                .extend(recipe.inputs.iter().map(|input| InputOutputCoefficient {
                    process_id: process.process_id,
                    good_id: input.good_id,
                    unit_id: input.unit_id,
                    quantity_per_batch: input.quantity,
                }));
            if let Some(labor) = &recipe.labor {
                state.labor_coefficients.push(LaborCoefficient {
                    process_id: process.process_id,
                    unit_id: labor.unit_id,
                    quantity_per_batch: labor.hours_per_batch,
                });
            }
            if process.planned_batches > 0 {
                state.production_commitments.push(ProductionCommitment {
                    process_id: process.process_id,
                    site_id: site.site_id,
                    period: 1,
                    planned_batches: process.planned_batches,
                });
            }
        }
        if let Some(merchant) = &site.merchant {
            state.merchants.push(MerchantHandling {
                site_id: site.site_id,
                location: site.location,
                role: merchant.role,
                capacity_id: merchant.capacity_id,
                labor_unit_id: merchant.labor_unit_id,
            });
            state
                .handling_coefficients
                .extend(
                    merchant
                        .handling
                        .iter()
                        .map(|row| MerchantHandlingCoefficient {
                            site_id: site.site_id,
                            good_id: row.good_id,
                            unit_id: row.unit_id,
                            hours_per_unit: row.hours_per_unit,
                        }),
                );
        }
    }
    Ok(())
}
fn append_households(opening: &EconomicOpening, state: &mut MaterialCircuitState) -> Result<()> {
    state
        .final_demand_principals
        .clone_from(&opening.orders.principals);
    for household in &opening.households {
        household
            .subject
            .canonical_bytes()
            .map_err(|_| EconomicCatalogError::Identity)?;
        state.final_demand_principals.push(FinalDemandPrincipal {
            id: household.principal_id,
            location: household.location,
        });
    }
    state
        .final_demand_orders
        .clone_from(&opening.orders.final_demand);
    state.orders.clone_from(&opening.orders.goods);
    if state
        .orders
        .iter()
        .any(|r| r.shipped != 0 || r.lost != 0 || r.delivered != 0 || r.realized != 0)
        || state.final_demand_orders.iter().any(|r| r.fulfilled != 0)
    {
        return Err(EconomicCatalogError::Opening("non-opening order counters"));
    }
    state.backlog = state
        .orders
        .iter()
        .map(|r| BacklogRow {
            order_id: r.order_id,
            quantity: r.ordered,
        })
        .collect();
    Ok(())
}
fn append_logistics(opening: &EconomicOpening, state: &mut MaterialCircuitState) -> Result<()> {
    state
        .supplier_routes
        .clone_from(&opening.logistics.supplier_routes);
    state
        .route_stages
        .clone_from(&opening.logistics.route_stages);
    state
        .route_stage_capacities
        .clone_from(&opening.logistics.memberships);
    state
        .service_connections
        .clone_from(&opening.policies.service_connections);
    match &opening.capacity {
        CatalogCapacity::Finite { process, freight } => {
            state.capacities.clone_from(process);
            state.corridor_capacities.clone_from(freight);
        }
        CatalogCapacity::Rolling(processes) => {
            let installed = processes.capacities(1)?;
            state.capacities = installed
                .iter()
                .map(|r| CapacityRow {
                    process_id: r.process_id,
                    site_id: r.site_id,
                    period: 1,
                    available_batches: r.batches_per_period,
                })
                .collect();
            state.corridor_capacities = opening
                .logistics
                .shared_capacity
                .iter()
                .map(|r| CorridorCapacity {
                    corridor_id: r.corridor_id,
                    period: 1,
                    available_grams: r.grams_per_period,
                })
                .collect();
            state.capacity_supply = CapacitySupply::Rolling(Box::new(RollingCapacitySupply {
                processes: processes.clone(),
                shared: opening.logistics.shared_capacity.clone(),
                future_reservations: vec![],
            }));
        }
    }

    if let Some(maintenance) = &opening.maintenance {
        state.maintenance_binding = Some(maintenance.binding.clone());
        state.maintenance_service = Some(MaintenanceService {
            period: 1,
            available_batches: maintenance.opening_enabled_batches,
        });
    }
    Ok(())
}
fn append_staffing(
    opening: &EconomicOpening,
    state: &mut MaterialCircuitState,
) -> Result<(StaffingComposition, Vec<MemberLaborCapacityRow>)> {
    let sites: BTreeMap<_, _> = opening
        .sites
        .iter()
        .map(|site| (site.site_id, site))
        .collect();
    let mut bindings = Vec::new();
    let mut hours = Vec::new();
    for seed in &opening.staffing {
        if sites
            .get(&seed.pool.site_id())
            .is_none_or(|site| site.subject != seed.workplace)
        {
            return Err(EconomicCatalogError::Opening("staffing workplace"));
        }
        let mut total = 0_u64;
        let mut members = Vec::new();
        for seed_member in &seed.members {
            if seed_member.employed.checked_add(seed_member.reserve)
                != Some(seed_member.member.labor_force())
            {
                return Err(EconomicCatalogError::Opening("member opening counts"));
            }
            let available = seed_member
                .employed
                .checked_mul(seed.pool.policy().hours_per_person())
                .ok_or(EconomicCatalogError::Arithmetic)?;
            total = total
                .checked_add(available)
                .ok_or(EconomicCatalogError::Arithmetic)?;
            hours.push(MemberLaborCapacityRow {
                member_id: seed_member.member.member_id(),
                period: 1,
                available_hours: available,
            });
            members.push(
                StaffingMemberNodeBinding::try_new(
                    seed_member.subject.clone(),
                    seed_member.member.clone(),
                )
                .map_err(EconomicCatalogError::Staffing)?,
            );
        }
        state.labor.push(LaborCapacityRow {
            site_id: seed.pool.site_id(),
            unit_id: seed.pool.unit_id(),
            period: 1,
            available: total,
        });
        bindings.push(
            StaffingNodeBinding::try_new(seed.workplace.clone(), seed.pool.clone(), members)
                .map_err(EconomicCatalogError::Staffing)?,
        );
    }
    let composition =
        StaffingComposition::try_new(bindings).map_err(EconomicCatalogError::Staffing)?;
    Ok((composition, hours))
}
fn compile_accounting(
    opening: &EconomicOpening,
    state: &MaterialCircuitState,
    member_labor: Vec<MemberLaborCapacityRow>,
) -> Result<CircuitAccounting> {
    match opening.accounting {
        CatalogAccounting::PhysicalControl => {
            if !opening.households.is_empty()
                || !opening.employment.is_empty()
                || !opening.institutional_cash.is_empty()
                || !opening.equity.is_empty()
                || !opening.equipment.is_empty()
                || opening.institutions != FinancialInstitutions::empty()
                || !opening.policies.offers.is_empty()
                || !opening.policies.replenishment.is_empty()
                || !opening.policies.household_purchases.is_empty()
                || !opening.policies.service_inputs.is_empty()
                || opening.sites.iter().any(|s| {
                    s.opening_cash.micro_units() != 0
                        || s.opening_stock
                            .iter()
                            .any(|v| v.total_cost.micro_units() != 0)
                })
            {
                return Err(EconomicCatalogError::Opening("money in physical control"));
            }
            Ok(CircuitAccounting::PhysicalControl)
        }
        CatalogAccounting::Monetary => {
            if !state.orders.is_empty() || !state.final_demand_orders.is_empty() {
                return Err(EconomicCatalogError::Opening(
                    "unfunded monetary opening orders",
                ));
            }
            let (book, costs) = opening_books(opening)?;
            let recurring = recurring(opening, state)?;
            Ok(CircuitAccounting::Monetary(Box::new(MonetaryCircuit {
                financial: opening.institutions.clone(),
                costs,
                recurring: Some(Box::new(recurring)),
                book,
                employment: opening.employment.clone(),
                member_labor,
            })))
        }
    }
}
fn opening_books(opening: &EconomicOpening) -> Result<(MonetaryBook, HistoricalCostBook)> {
    if opening
        .institutional_cash
        .iter()
        .any(|r| !matches!(r.id, AccountId::Organization(_) | AccountId::Public(_)))
    {
        return Err(EconomicCatalogError::Opening(
            "institutional cash namespace",
        ));
    }
    let mut cash = opening.institutional_cash.clone();
    let mut stocks = Vec::new();
    for (owner, balance, inventory) in opening
        .sites
        .iter()
        .map(|s| (AccountId::Site(s.site_id), s.opening_cash, &s.opening_stock))
        .chain(opening.households.iter().map(|h| {
            (
                AccountId::Household(h.principal_id),
                h.opening_cash,
                &h.opening_stock,
            )
        }))
    {
        cash.push(CashAccount {
            id: owner,
            cash: balance,
        });
        stocks.extend(inventory.iter().map(|s| StockCarryingValue {
            owner,
            good_id: s.amount.good_id,
            unit_id: s.amount.unit_id,
            amount: s.total_cost,
        }));
    }
    let book = MonetaryBook::open(cash).map_err(|e| EconomicCatalogError::Circuit(e.into()))?;
    let costs = HistoricalCostBook::open(
        &book,
        stocks,
        vec![],
        opening.equity.clone(),
        opening.equipment.clone(),
    )?;
    Ok((book, costs))
}
fn recurring(opening: &EconomicOpening, state: &MaterialCircuitState) -> Result<RecurringEconomy> {
    let templates: BTreeMap<_, _> = opening
        .household_templates
        .iter()
        .map(|r| (r.id, r))
        .collect();
    if templates.len() != opening.household_templates.len() {
        return Err(EconomicCatalogError::Opening("household template identity"));
    }
    let mut households = Vec::new();
    let mut household_stocks = Vec::new();
    let mut household_needs = Vec::new();
    for h in &opening.households {
        let template = templates
            .get(&h.template)
            .ok_or(EconomicCatalogError::Opening("absent household template"))?;
        households.push(HouseholdCohort {
            kind: h.kind,
            principal_id: h.principal_id,
            persons: h.persons,
            households: h.households,
        });
        household_stocks.extend(h.opening_stock.iter().map(|s| HouseholdStock {
            principal_id: h.principal_id,
            good_id: s.amount.good_id,
            unit_id: s.amount.unit_id,
            quantity: s.amount.quantity,
        }));
        household_needs.extend(template.needs.iter().map(|n| HouseholdNeed {
            principal_id: h.principal_id,
            good_id: n.good_id,
            unit_id: n.unit_id,
            basis: n.basis,
            units_per_basis: n.units_per_basis,
        }));
    }
    Ok(RecurringEconomy {
        service_inputs: opening.policies.service_inputs.clone(),
        households,
        household_stocks,
        household_needs,
        household_purchases: opening.policies.household_purchases.clone(),
        offers: opening.policies.offers.clone(),
        replenishment: opening.policies.replenishment.clone(),
        production: opening
            .sites
            .iter()
            .flat_map(|s| {
                s.processes.iter().map(|p| ProductionDemandPolicy {
                    process_id: p.process_id,
                    site_id: s.site_id,
                    output_buffer: p.output_buffer,
                    planned_batches: p.planned_batches,
                })
            })
            .collect(),
        attendance: state
            .labor
            .iter()
            .map(|r| AttendancePlan {
                site_id: r.site_id,
                unit_id: r.unit_id,
                period: 1,
                planned_hours: r.available,
            })
            .collect(),
        last_household_admission_period: 0,
        last_household_consumption_period: 0,
    })
}
