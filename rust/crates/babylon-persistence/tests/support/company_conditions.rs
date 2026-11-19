//! Source-controlled opening treatments and actual prior-choice / subsequent material observations.
use super::Physical;
use babylon_graph::hypergraph_store::HypergraphStore;
use babylon_material_circuit::{CompanyId, OrderId, SiteId};
use babylon_persistence::economic_catalog::CapturedEconomicCatalog;
use babylon_tick::material_replay::PreparedMaterialTick;
use babylon_tick::material_world::MaterialTickReceipts;
use serde_json::{json, Value};
use std::collections::{BTreeMap, BTreeSet};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(super) enum Condition {
    Ordinary,
    OnePeriod,
    NoFoundingPool,
    Shortage,
    Spare,
    Replacement,
    Delay,
}
impl Condition {
    pub(super) fn label(self) -> &'static str {
        match self {
            Self::Ordinary => "ordinary",
            Self::OnePeriod => "one_period_cash_control",
            Self::NoFoundingPool => "weak_liquidity",
            Self::Shortage => "short_inputs",
            Self::Spare => "excess_capacity",
            Self::Replacement => "replacement_pressure",
            Self::Delay => "delayed_equipment",
        }
    }
    pub(super) fn change(self, policy: &mut String) {
        let replace = |text: &mut String, before: &str, after: &str| {
            assert_eq!(
                text.matches(before).count(),
                1,
                "exact captured policy treatment"
            );
            *text = text.replacen(before, after, 1);
        };
        match self {
            Self::Ordinary => {}
            Self::OnePeriod | Self::NoFoundingPool => {
                replace(
                    policy,
                    "working_capital_periods = 2\n",
                    "working_capital_periods = 1\n",
                );
                if self == Self::NoFoundingPool {
                    // Members retain their own cash. The ordinary 10% opening pool is absent.
                    replace(
                        policy,
                        "opening_treasury_bps = 1000\n",
                        "opening_treasury_bps = 0\n",
                    );
                }
            }
            Self::Shortage => {
                replace(
                    policy,
                    "opening_input_periods = 2\n",
                    "opening_input_periods = 1\n",
                );
                replace(
                    policy,
                    "resource_reserve_output_periods = 1040\n",
                    "resource_reserve_output_periods = 1\n",
                );
            }
            Self::Spare => {
                replace(
                    policy,
                    "opening_pantry_periods = 1\n",
                    "opening_pantry_periods = 4\n",
                );
                replace(
                    policy,
                    "retailer_buffer_periods = 2\n",
                    "retailer_buffer_periods = 1\n",
                );
            }
            Self::Replacement | Self::Delay => {
                // One full period at the ordinary nameplate wears through a cohort at this fraction.
                replace(
                    policy,
                    "opening_remaining_service_bps = [2500, 5000, 7500, 10000]",
                    "opening_remaining_service_bps = [100, 100, 100, 100]",
                );
                if self == Self::Delay {
                    replace(
                        policy,
                        "installation_hours_per_unit = 32\n",
                        "installation_hours_per_unit = 32000\n",
                    );
                }
            }
        }
    }
    pub(super) fn periods(self) -> u64 {
        match self {
            Self::Ordinary | Self::OnePeriod => 3,
            _ => 5,
        }
    }
    pub(super) fn verify(self, observed: &Observed) {
        let witnessed = match self {
            // Matched cash controls can remain sufficiently liquid at the captured prices.
            Self::Ordinary | Self::OnePeriod | Self::NoFoundingPool => true,
            Self::Shortage => observed.unmet_processes > 0 && observed.households_short > 0,
            Self::Spare => observed.idle_processes > 0,
            Self::Replacement => {
                observed.replacement_requests > 0 && observed.exhausted_cohorts > 0
            }
            Self::Delay => {
                observed.unfinished_installations > 0 || observed.prior_orders_still_outstanding > 0
            }
        };
        assert!(
            witnessed,
            "{} treatment did not realize its qualification condition: {}",
            self.label(),
            observed.report()
        );
    }
}

#[derive(Default)]
pub(super) struct Observed {
    unmet_processes: u64,
    households_short: u64,
    idle_processes: u64,
    exhausted_cohorts: u64,
    replacement_requests: u64,
    unaffordable_requests: u64,
    requests_requiring_parent_cash: u64,
    requests_exceeding_own_and_parent_cash: u64,
    productive_sites_available_cash_micros: i128,
    parent_available_cash_micros: i128,
    unfinished_installations: u64,
    prior_orders_still_outstanding: u64,
    prior_unshipped_units: u128,
    prior_transit_units: u128,
    committed_orders: BTreeSet<OrderId>,
}

impl Observed {
    pub(super) fn record(
        tick: &PreparedMaterialTick<HypergraphStore>,
        receipts: &MaterialTickReceipts,
        members: &BTreeMap<SiteId, CompanyId>,
        prior_orders: &BTreeSet<OrderId>,
    ) -> Self {
        let register = tick.material().register();
        let mut result = Self::default();
        let companies = register
            .company_portfolios()
            .expect("admitted observations");
        let mut site_cash = BTreeMap::new();
        for company in &companies.companies {
            result.parent_available_cash_micros += company.treasury_available.micro_units();
            for process in &company.processes {
                result.unmet_processes += u64::from(process.unmet_accepted_units > 0);
                result.idle_processes +=
                    u64::from(process.capacity_batches > process.produced_batches);
                let funds = company
                    .treasury_available
                    .checked_add(process.free_cash)
                    .expect("whole funds");
                if let Some(prior) = site_cash.insert(process.site, process.free_cash.micro_units())
                {
                    assert_eq!(
                        prior,
                        process.free_cash.micro_units(),
                        "one operating balance per site"
                    );
                }
                let requested = process
                    .replacement
                    .checked_add(process.expansion)
                    .expect("whole units");
                if requested > 0 {
                    result.unaffordable_requests += u64::from(funds < process.unit_price);
                    result.requests_requiring_parent_cash +=
                        u64::from(process.free_cash < process.unit_price);
                    let cost = i128::from(requested)
                        .checked_mul(process.unit_price.micro_units())
                        .expect("whole request cost");
                    result.requests_exceeding_own_and_parent_cash +=
                        u64::from(cost > funds.micro_units());
                }
            }
        }
        result.productive_sites_available_cash_micros = site_cash.values().sum();
        result.households_short = receipts
            .household_consumption
            .iter()
            .filter(|r| r.unmet_quantity > 0)
            .map(|r| r.principal_id)
            .collect::<BTreeSet<_>>()
            .len() as u64;
        result.exhausted_cohorts = receipts
            .equipment_wear
            .iter()
            .filter(|r| members.contains_key(&r.site_id) && r.remaining_service_batches == 0)
            .count() as u64;
        result.unfinished_installations = receipts
            .installation
            .iter()
            .filter(|r| members.contains_key(&r.site_id) && r.remaining_hours > 0)
            .count() as u64;
        for r in receipts
            .investment
            .iter()
            .filter(|r| members.contains_key(&r.site_id))
        {
            result.replacement_requests += u64::from(r.replacement_requested_units > 0);
            if r.admitted_units > 0 {
                result.committed_orders.insert(r.order_id);
            }
        }
        for order in register
            .state()
            .orders
            .iter()
            .filter(|o| prior_orders.contains(&o.order_id))
        {
            let unshipped = order
                .ordered
                .checked_sub(order.shipped)
                .expect("physical order quantities");
            let in_transit = order
                .shipped
                .checked_sub(order.delivered)
                .and_then(|v| v.checked_sub(order.lost))
                .expect("physical order quantities");
            result.prior_orders_still_outstanding += u64::from(unshipped > 0 || in_transit > 0);
            result.prior_unshipped_units += u128::from(unshipped);
            result.prior_transit_units += u128::from(in_transit);
        }
        result
    }
    pub(super) fn include(&mut self, r: &Self) {
        self.unmet_processes += r.unmet_processes;
        self.households_short += r.households_short;
        self.idle_processes += r.idle_processes;
        self.exhausted_cohorts += r.exhausted_cohorts;
        self.replacement_requests += r.replacement_requests;
        self.unaffordable_requests += r.unaffordable_requests;
        self.requests_requiring_parent_cash += r.requests_requiring_parent_cash;
        self.requests_exceeding_own_and_parent_cash += r.requests_exceeding_own_and_parent_cash;
        self.productive_sites_available_cash_micros = r.productive_sites_available_cash_micros;
        self.parent_available_cash_micros = r.parent_available_cash_micros;
        self.unfinished_installations += r.unfinished_installations;
        self.prior_orders_still_outstanding += r.prior_orders_still_outstanding;
        self.prior_unshipped_units += r.prior_unshipped_units;
        self.prior_transit_units += r.prior_transit_units;
        self.committed_orders
            .extend(r.committed_orders.iter().copied());
    }
    pub(super) fn orders(&self) -> &BTreeSet<OrderId> {
        &self.committed_orders
    }
    pub(super) fn report(&self) -> Value {
        json!({"member_processes_with_unshipped_accepted_demand":self.unmet_processes,
            "household_principals_with_unmet_goods":self.households_short,"member_processes_below_recorded_capacity":self.idle_processes,
            "exhausted_member_equipment_cohorts":self.exhausted_cohorts,"member_processes_requesting_replacement":self.replacement_requests,
            "member_process_requests_unaffordable_even_with_treasury":self.unaffordable_requests,
            "member_process_requests_unaffordable_from_site_cash_alone":self.requests_requiring_parent_cash,
            "member_process_full_requests_exceeding_site_and_parent_cash":self.requests_exceeding_own_and_parent_cash,
            "productive_sites_available_cash_micros":self.productive_sites_available_cash_micros.to_string(),
            "parent_available_cash_micros":self.parent_available_cash_micros.to_string(),
            "unfinished_member_installations":self.unfinished_installations,"admitted_member_equipment_orders":self.committed_orders.len(),
            "previously_admitted_equipment_orders_still_outstanding":self.prior_orders_still_outstanding,
            "previously_committed_equipment_units_unshipped":self.prior_unshipped_units.to_string(),
            "previously_committed_equipment_units_in_transit":self.prior_transit_units.to_string()})
    }
}

/// Check the generated physical and demand inputs, beyond their source policy declarations.
fn compare_cash_opening(captured: &CapturedEconomicCatalog) {
    let source = captured.opening();
    let finances = captured
        .national_company_finances()
        .expect("cash treatment finance");
    for condition in [Condition::Ordinary, Condition::OnePeriod] {
        let control = super::capture(None, condition).expect("independent 99-company cash control");
        let base = control.opening();
        Physical::new(base).verify(source);
        assert_eq!(base.orders, source.orders);
        assert_eq!(base.policies.offers, source.policies.offers);
        assert_eq!(base.policies.replenishment, source.policies.replenishment);
        assert_eq!(
            base.policies.household_purchases,
            source.policies.household_purchases
        );
        assert_eq!(base.policies.service_inputs, source.policies.service_inputs);
        assert_eq!(
            base.policies.service_connections,
            source.policies.service_connections
        );
        let baseline = control
            .national_company_finances()
            .expect("control finance");
        assert_eq!(baseline.members.len(), finances.members.len());
        let mut control_total = 0_i128;
        let mut treatment_total = 0_i128;
        for (original, treated) in baseline.members.iter().zip(&finances.members) {
            assert_eq!(
                (original.site, original.company, original.cash_floor),
                (treated.site, treated.company, treated.cash_floor)
            );
            assert!(original.original_cash >= treated.original_cash);
            if condition == Condition::OnePeriod {
                assert_eq!(original.original_cash, treated.original_cash);
            }
            control_total += original.original_cash.micro_units();
            treatment_total += treated.original_cash.micro_units();
        }
        let multiplier = if condition == Condition::Ordinary {
            2
        } else {
            1
        };
        assert_eq!(control_total, treatment_total * multiplier);
        assert!(baseline.treasuries.iter().any(|r| r.cash.micro_units() > 0));
    }
    assert!(finances
        .treasuries
        .iter()
        .all(|r| r.cash.micro_units() == 0));
}

#[test]
#[ignore = "serial national gameplay treatments, two independent production seeds"]
fn national_company_conditions_require_witnessed_material_pressure_and_next_commitments() {
    let only = std::env::var("BABYLON_COMPANY_CONDITION").ok();
    let treatments = [
        Condition::Shortage,
        Condition::Spare,
        Condition::OnePeriod,
        Condition::NoFoundingPool,
        Condition::Replacement,
        Condition::Delay,
    ];
    assert!(only
        .as_ref()
        .is_none_or(|s| treatments.iter().any(|t| t.label() == s)));
    for condition in treatments {
        if only.as_ref().is_some_and(|s| s != condition.label()) {
            continue;
        }
        let captured =
            super::capture(None, condition).expect("admit changed Designed opening policy");
        if condition == Condition::NoFoundingPool {
            compare_cash_opening(&captured);
        }
        let roster = captured.national_companies().expect("retained membership");
        assert_eq!(roster.companies.len(), 99);
        let members = roster
            .members
            .iter()
            .map(|r| (r.site, r.company.id()))
            .collect();
        println!(
            "{}",
            json!({"experiment":"national_company_conditions","opening_treatment":condition.label(),"capture_sha256":babylon_tick::hex(&captured.digest()),"opening_liquidity":super::opening_liquidity(&captured)})
        );
        let first = super::run(&captured, 37, condition, 99, &members);
        let second = super::run(&captured, 319, condition, 99, &members);
        super::divergence::report(&first, &second, 99, condition.label());
    }
}

#[test]
fn contrasting_company_treatments_retain_the_same_portfolio_law_and_geographic_identity() {
    use babylon_persistence::national_economy::NationalGamePolicy;
    let source = include_str!("../../../../../content/scenarios/national/defines.toml");
    let base = NationalGamePolicy::from_captured_bytes(source.as_bytes())
        .expect("authored ordinary policy");
    let mut seen = BTreeSet::new();
    for condition in [
        Condition::Ordinary,
        Condition::OnePeriod,
        Condition::NoFoundingPool,
        Condition::Shortage,
        Condition::Spare,
        Condition::Replacement,
        Condition::Delay,
    ] {
        let mut text = source.to_owned();
        condition.change(&mut text);
        let policy = NationalGamePolicy::from_captured_bytes(text.as_bytes())
            .expect("scenario remains an admitted national policy");
        assert_eq!(
            policy.grain_identity_policy_digest,
            base.grain_identity_policy_digest
        );
        let mut expected_company = base.companies;
        if condition == Condition::NoFoundingPool {
            expected_company
                .as_mut()
                .expect("99 companies")
                .treasury_bps = 0;
        }
        assert_eq!(policy.companies, expected_company);
        assert!(seen.insert(policy.source_digest));
        match condition {
            Condition::Ordinary => assert_eq!(policy, base),
            Condition::OnePeriod | Condition::NoFoundingPool => {
                assert_eq!(policy.commodities, base.commodities);
                assert_eq!(policy.recipes, base.recipes);
                assert_eq!(policy.household_needs, base.household_needs);
                assert!(policy.working_capital_periods < base.working_capital_periods);
            }
            Condition::Shortage => assert!(
                policy.resource_reserve_output_periods < base.resource_reserve_output_periods
                    && policy.opening_input_periods < base.opening_input_periods
            ),
            Condition::Spare => assert!(
                policy.retailer_buffer_periods < base.retailer_buffer_periods
                    && policy.opening_pantry_periods > base.opening_pantry_periods
            ),
            Condition::Replacement => assert!(policy
                .equipment
                .opening_remaining_service_bps
                .iter()
                .all(|n| *n <= 100)),
            Condition::Delay => assert!(
                policy.equipment.installation_hours_per_unit
                    > base.equipment.installation_hours_per_unit
            ),
        }
    }
}
