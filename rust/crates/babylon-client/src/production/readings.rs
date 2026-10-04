//! Exact textual readings from one disclosed production snapshot.

use babylon_persistence::{
    production_observation::ProductionSite, production_observation::ProductionSnapshot,
};
use std::fmt::Write as _;

use super::ProductionReadingSection;
use crate::observer_ui::grouped;
use crate::production_brief::committed_plan_status;
use crate::production_freight::format_freight_mass;

pub(super) fn describe(
    site: &ProductionSite,
    snapshot: &ProductionSnapshot,
    section: ProductionReadingSection,
) -> String {
    match section {
        ProductionReadingSection::Flow => describe_flow(site, snapshot),
        ProductionReadingSection::Freight => describe_freight(site, snapshot),
        ProductionReadingSection::Work => describe_work(site, snapshot),
        ProductionReadingSection::Sources => describe_sources(site, snapshot),
    }
}

pub(super) fn reading_headline(
    site: &ProductionSite,
    snapshot: &ProductionSnapshot,
    period: u64,
) -> String {
    let mut value = if period == 0 {
        "Foundation / Designed\n".to_owned()
    } else {
        format!("Period {period} / committed reading\n")
    };
    let mut outputs = std::collections::BTreeSet::new();
    for process in &site.processes {
        if !outputs.insert((&process.output_good_id, &process.output_unit_id)) {
            continue;
        }
        let output = snapshot.material_balance.as_ref().and_then(|balance| {
            balance.rows.iter().find(|row| {
                row.site_id == site.id
                    && row.good_id == process.output_good_id
                    && row.unit_id == process.output_unit_id
            })
        });
        if let Some(output) = output {
            writeln!(
                value,
                "{} {} produced / Derived · {}",
                grouped(output.produced),
                output.unit,
                process.output_good
            )
            .expect("String write");
        } else {
            writeln!(
                value,
                "{}: {}",
                process.output_good,
                crate::production_brief::process_plan_status(process)
            )
            .expect("String write");
        }
    }
    if site.processes.is_empty() {
        writeln!(value, "{}", committed_plan_status(site)).expect("String write");
        if let Some(account) = super::maintenance::account(snapshot, &site.id) {
            if let Some(done) = &account.completed {
                writeln!(
                    value,
                    "{} jobs completed / Derived",
                    grouped(done.completed_jobs)
                )
                .expect("String write");
            }
        }
    }
    let accounts: Vec<_> = snapshot
        .staffing_accounts
        .iter()
        .filter(|account| account.site_id == site.id)
        .collect();
    if accounts.is_empty() {
        value.push_str("Modeled workforce not disclosed");
    }
    for account in accounts {
        writeln!(
            value,
            "{} employed · {} reserve / {}",
            grouped(account.employed),
            grouped(account.reserve),
            if account.completed.is_some() {
                "Derived"
            } else {
                "Designed"
            }
        )
        .expect("String write");
    }
    value.trim_end().to_owned()
}

pub(super) fn describe_flow(site: &ProductionSite, snapshot: &ProductionSnapshot) -> String {
    let mut value = String::new();
    super::maintenance::flow(&mut value, &site.id, snapshot);
    for process in &site.processes {
        writeln!(
            value,
            "{} / {}\n{}",
            process.name,
            process.output_good,
            crate::production_brief::process_plan_status(process)
        )
        .expect("String write");
        if let (Some(done), Some(plan)) = (process.produced_batches, process.planned_batches) {
            writeln!(
                value,
                "COMMITTED PRODUCTION\n{done} of {plan} planned batches"
            )
            .expect("String write");
        }
        writeln!(
            value,
            "{} {} / batch (Designed)\nNext-period capacity: {} batches\n\nINPUTS / ON HAND",
            grouped(process.output_per_batch),
            process.output_unit,
            grouped(process.available_batches)
        )
        .expect("String write");
        for input in &process.inputs {
            writeln!(
                value,
                "{}: {} {}",
                input.good,
                input
                    .on_hand
                    .map_or_else(|| "period service; no stored stock".into(), grouped),
                input.unit
            )
            .expect("String write");
        }
        if process.inputs.is_empty() {
            value.push_str("No material inputs in this recipe.\n");
        }
        value.push('\n');
    }
    if site.processes.is_empty() {
        writeln!(value, "{}", committed_plan_status(site)).expect("String write");
    }
    for account in snapshot
        .final_demand_accounts
        .iter()
        .filter(|account| account.retailer_site_ids.contains(&site.id))
    {
        writeln!(value, "RESIDENT FINAL DEMAND / {}\n{} {} ordered · {} fulfilled · {} outstanding\nFulfillment and household consumption have separate accounts.", account.good, grouped(account.ordered), account.unit, grouped(account.fulfilled), grouped(account.outstanding)).expect("String write");
    }
    describe_households(&mut value, site, snapshot);
    describe_prices(&mut value, site, snapshot);
    describe_material_balance(&mut value, site, snapshot);
    value.push_str("\nINVENTORY\n");
    for stock in &site.inventory {
        writeln!(
            value,
            "{}: {} {}",
            stock.good,
            grouped(stock.quantity),
            stock.unit
        )
        .expect("String write");
    }
    value
}

pub(super) fn describe_freight(site: &ProductionSite, snapshot: &ProductionSnapshot) -> String {
    let mut value = String::new();
    let Ok(definitions) =
        babylon_persistence::production_observation::PhysicalRouteIndex::try_new(snapshot)
    else {
        return "Physical route details unavailable in this observation.\n".into();
    };
    let Ok(orders) =
        babylon_persistence::production_observation::FreightOrderIndex::try_new(snapshot)
    else {
        return "Freight order details unavailable in this observation.\n".into();
    };
    let accounts = crate::production_freight::shared_accounts_with_index(
        snapshot,
        Some(&site.id),
        &definitions,
    );
    if accounts.is_empty() {
        value.push_str("No shared freight pool disclosed for this subject.\n");
    }
    if accounts.len() > 3 {
        writeln!(value, "{} shared capacity accounts; showing the three with least next-opening availability.\n", accounts.len()).expect("String write");
    }
    for account in accounts.into_iter().take(3) {
        value.push_str(&crate::production_freight::account_reading_with_index(
            account,
            snapshot,
            &definitions,
            &orders,
        ));
        value.push('\n');
    }
    value.push_str("\nPHYSICAL DELIVERIES / TO DATE\n");
    for route in snapshot
        .routes
        .iter()
        .filter(|route| route.buyer_site_id == site.id || route.supplier_site_id == site.id)
    {
        let other = if route.buyer_site_id == site.id {
            &route.supplier_site_id
        } else {
            &route.buyer_site_id
        };
        let name = snapshot
            .sites
            .iter()
            .find(|site| site.id == *other)
            .map_or(other.as_str(), |site| site.name.as_str());
        let Some(physical) = definitions.get(route) else {
            continue;
        };
        writeln!(
            value,
            "{} | {}\n{} / {} {} delivered | {} unshipped\n",
            name,
            match physical.transport_kind {
                babylon_persistence::production_observation::ProductionRouteTransport::Local =>
                    "Local inter-owner transfer".into(),
                babylon_persistence::production_observation::ProductionRouteTransport::Staged =>
                    format!("{} periods travel", physical.travel_periods),
            },
            grouped(route.delivered),
            grouped(route.ordered),
            route.unit,
            route
                .ordered
                .checked_sub(route.shipped)
                .map_or_else(|| "unavailable".into(), grouped)
        )
        .expect("String write");
    }
    value.push_str("Deliveries record quantities, not payments.\n");
    value
}

pub(super) fn describe_work(site: &ProductionSite, snapshot: &ProductionSnapshot) -> String {
    let mut value = String::new();
    describe_staffing_accounts(&mut value, site, snapshot);
    describe_labor_accounts(&mut value, site, snapshot);
    super::maintenance::work(&mut value, &site.id, snapshot);
    value.push_str("\nLABOR BUDGET / DERIVED\n");
    for labor in site.processes.iter().flat_map(|process| &process.labor) {
        writeln!(
            value,
            "{} {} available | {} / batch (Designed)",
            grouped(labor.available),
            labor.unit,
            grouped(labor.quantity_per_batch)
        )
        .expect("String write");
    }
    for handling in snapshot
        .merchant_handling_accounts
        .iter()
        .filter(|account| account.site_id == site.id)
    {
        value.push_str("\nMERCHANT HANDLING\n");
        if let Some(done) = &handling.completed {
            writeln!(
                value,
                "Period {}: {} handled · {} / {} labor-hours used / needed",
                done.period,
                format_freight_mass(done.handled_grams),
                grouped(done.used_hours),
                grouped(done.needed_hours)
            )
            .expect("String write");
        } else {
            value.push_str("Foundation; no completed handling work.\n");
        }
        value.push_str("Handling moves existing goods; it does not create productive output.\n");
    }
    value.trim_start().to_owned()
}

fn describe_sources(site: &ProductionSite, snapshot: &ProductionSnapshot) -> String {
    let mut value = format!(
        "WORKPLACE / {}\n{} · {:?}\n",
        site.location,
        site.industry_code.as_deref().unwrap_or(&site.function),
        site.roles
    );
    for process in &site.processes {
        writeln!(
            value,
            "\nRECIPE / DESIGNED / {}\n{} {} / batch",
            process.name,
            grouped(process.output_per_batch),
            process.output_unit
        )
        .expect("String write");
        for input in &process.inputs {
            writeln!(
                value,
                "{}: {} {} / batch",
                input.good,
                grouped(input.quantity_per_batch),
                input.unit
            )
            .expect("String write");
        }
    }
    if let Some(jobs) = site.observed_employment {
        writeln!(value, "\nINDUSTRY EMPLOYMENT / OBSERVED 2024\n{} annual-average jobs (QCEW; separate from modeled people and hours)", grouped(jobs)).expect("String write");
    }
    super::maintenance::sources(&mut value, &site.id, snapshot);
    describe_sector_context(&mut value, site, snapshot);
    writeln!(
        value,
        "\nCAPTURED AUTHORITY\n{}",
        snapshot.content_authority_sha256
    )
    .expect("String write");
    if let Some(source) = &snapshot.road_source {
        writeln!(
            value,
            "Road extract: {}\nReplication: {}\nRouting profile: {}\nGraph: {}",
            source.pbf_url,
            source.replication_timestamp,
            source.routing_profile_version,
            source.graph_sha256
        )
        .expect("String write");
        value.push_str("Road data © OpenStreetMap contributors, available under the Open Database License (ODbL).\nhttps://www.openstreetmap.org/copyright\n");
    }
    value.push_str("\nSCENE KEY\nEqual-height structures identify county cohorts; height and spacing carry no quantity or geography. Arrows point from disclosed suppliers to buyers. Cyan links enter the selection; copper links leave it. Gold elevated links show maintenance service from provider to consumer, separate from the reverse parts shipment. Packets are actual in-transit lots at static schematic positions.\n");
    value
}

pub(super) fn describe_material_balance(
    value: &mut String,
    site: &ProductionSite,
    snapshot: &ProductionSnapshot,
) {
    let Some(balance) = &snapshot.material_balance else {
        value.push_str("\nNo completed stock-movement account at this point.\n");
        return;
    };
    let mut rows = balance
        .rows
        .iter()
        .filter(|row| row.site_id == site.id)
        .peekable();
    if rows.peek().is_none() {
        value.push_str("\nNo stock-movement account disclosed for this subject.\n");
        return;
    }
    writeln!(value, "\nSTOCK MOVEMENT / PERIOD {}", balance.period).expect("String write");
    for row in rows {
        if row.installation_consumed != 0
            || row.maintenance_consumed != 0
            || super::maintenance::account(snapshot, &site.id).is_some_and(|account| {
                account.provider_site_id == site.id
                    && account.spare_good_id == row.good_id
                    && account.spare_unit_id == row.unit_id
            })
        {
            writeln!(value, "{} / {}\nOpened {} + arrived {} + received locally {} + produced {}\n= production consumed {} + maintenance consumed {} + installation consumed {} + dispatched {} + transferred locally {} + final demand {} + closed {}", row.good, row.unit, grouped(row.opening), grouped(row.arrivals), grouped(row.local_received), grouped(row.produced), grouped(row.consumed), grouped(row.maintenance_consumed), grouped(row.installation_consumed), grouped(row.dispatched), grouped(row.local_transferred), grouped(row.final_demand_fulfilled), grouped(row.closing)).expect("String write");
            continue;
        }
        if row.local_received != 0 || row.local_transferred != 0 || row.final_demand_fulfilled != 0
        {
            writeln!(value, "{} / {}\nOpened {} + arrived {} + received locally {} + produced {}\n= consumed {} + dispatched {} + transferred locally {} + final demand {} + closed {}", row.good, row.unit, grouped(row.opening), grouped(row.arrivals), grouped(row.local_received), grouped(row.produced), grouped(row.consumed), grouped(row.dispatched), grouped(row.local_transferred), grouped(row.final_demand_fulfilled), grouped(row.closing)).expect("String write");
            continue;
        }
        writeln!(
            value,
            "{} / {}\nOpened {} + arrived {} + produced {}\n= consumed {} + dispatched {} + closed {}",
            row.good,
            row.unit,
            grouped(row.opening),
            grouped(row.arrivals),
            grouped(row.produced),
            grouped(row.consumed),
            grouped(row.dispatched),
            grouped(row.closing),
        )
        .expect("String write");
    }
}

fn describe_sector_context(
    value: &mut String,
    site: &ProductionSite,
    snapshot: &ProductionSnapshot,
) {
    describe_national_context(value, site, snapshot);
    let subjects: std::collections::BTreeSet<_> = snapshot
        .process_attributions
        .iter()
        .filter(|link| link.site_id == site.id)
        .map(|link| &link.cohort_subject)
        .collect();
    for context in snapshot.observed_contexts.iter().filter(|context| {
        site.is_in_county(&context.county_geoid)
            && (subjects.contains(&context.subject)
                || (site.roles.contains(
                    &babylon_persistence::production_observation::ProductionSiteRole::Maintenance,
                ) && site.sector_code.as_deref() == Some(context.sector_code.as_str())))
    }) {
        writeln!(
            value,
            "\nSECTOR CONTEXT / OBSERVED {}\n{} | NAICS {}\n{} establishments",
            context.vintage,
            context.sector_title,
            context.sector_code,
            grouped(context.annual_avg_estabs_count),
        )
        .expect("String write");
        for (metric, prefix, suffix, undisclosed) in [
            (
                context.annual_avg_emplvl,
                "",
                " annual-average jobs",
                "Annual-average jobs: not disclosed",
            ),
            (
                context.total_annual_wages,
                "USD ",
                " annual payroll",
                "Annual payroll: not disclosed",
            ),
            (
                context.annual_avg_wkly_wage,
                "USD ",
                " mean weekly wage",
                "Mean weekly wage: not disclosed",
            ),
        ] {
            match metric {
                Some(metric) => writeln!(value, "{prefix}{}{suffix}", grouped(metric)),
                None => writeln!(value, "{undisclosed}"),
            }
            .expect("String write");
        }
        let shared_ids: std::collections::BTreeSet<_> = snapshot
            .process_attributions
            .iter()
            .filter(|link| link.cohort_subject == context.subject)
            .map(|link| link.site_id.as_str())
            .collect();
        let mut names: Vec<_> = snapshot
            .sites
            .iter()
            .filter(|other| shared_ids.contains(other.id.as_str()))
            .map(|other| other.name.as_str())
            .collect();
        names.sort_unstable();
        writeln!(
            value,
            "Modeled processes sharing this context: {}\nThis county-sector total does not assign workers to a process.\nSource: BLS QCEW / {}\n{}",
            names.join("; "),
            context.source_file,
            context.source_url,
        )
        .expect("String write");
    }
}

fn describe_national_context(
    value: &mut String,
    site: &ProductionSite,
    snapshot: &ProductionSnapshot,
) {
    for row in snapshot
        .national_observed_contexts
        .iter()
        .filter(|r| r.site_id == site.id)
    {
        writeln!(
            value,
            "\nWORKPLACE SOURCE / OBSERVED {}\nCounty {} · {} · ownership {}",
            row.vintage, row.county_geoid, row.function, row.ownership
        )
        .expect("String write");
        for (label, cell) in [
            ("Establishments", &row.establishments),
            ("Annual-average jobs", &row.annual_average_jobs),
            ("Annual payroll USD", &row.annual_payroll_usd),
        ] {
            if cell.missing_members == 0 {
                writeln!(value, "{label}: {}", grouped(cell.known_subtotal)).expect("String write");
            } else {
                writeln!(
                    value,
                    "{label}: {} known subtotal; {} source cells not disclosed",
                    grouped(cell.known_subtotal),
                    cell.missing_members
                )
                .expect("String write");
            }
        }
        writeln!(value,"Source jobs do not assign people to this workplace. Technical function mapping is Designed.\nSource sha256:{}\nMapping sha256:{}",row.artifact_sha256,row.function_mapping_sha256).expect("String write");
    }
}

fn describe_staffing_accounts(
    value: &mut String,
    site: &ProductionSite,
    snapshot: &ProductionSnapshot,
) {
    let mut disclosed = false;
    for account in snapshot
        .staffing_accounts
        .iter()
        .filter(|account| account.site_id == site.id)
    {
        disclosed = true;
        value.push_str(if account.completed.is_some() {
            "\nMODELED WORKFORCE / DERIVED\n"
        } else {
            "\nMODELED WORKFORCE / DESIGNED\n"
        });
        writeln!(
            value,
            "{} employed + {} reserve = {} people\n{} hours per person / period (Designed)",
            grouped(account.employed),
            grouped(account.reserve),
            grouped(account.labor_force),
            grouped(account.hours_per_person),
        )
        .expect("String write");
        if let Some(completed) = &account.completed {
            writeln!(
                value,
                "\nSTAFFING / PERIOD {}\nOpening: {} employed, {} reserve\nWork activations: {} | releases: {} | target: {} employed\nWork request: {} hours | prior period: {} hours\nOne-period retention: {} hours\n",
                completed.period,
                grouped(completed.opening_employed),
                grouped(completed.opening_reserve),
                grouped(completed.hires),
                grouped(completed.separations),
                grouped(completed.target_employed),
                grouped(completed.current_unretained_hours),
                grouped(completed.previous_unretained_hours),
                grouped(completed.retained_hours),
            )
            .expect("String write");
        } else {
            value.push_str("Opening workforce; no completed staffing period.\n");
        }
    }
    if disclosed {
        value.push_str("Observed QCEW jobs are separate; these accounts record no payments.\n");
    } else {
        value.push_str("\nMODELED WORKFORCE\nNo workforce account disclosed for this subject.\n");
    }
}

fn describe_labor_accounts(
    value: &mut String,
    site: &ProductionSite,
    snapshot: &ProductionSnapshot,
) {
    for account in snapshot
        .labor_accounts
        .iter()
        .filter(|account| account.site_id == site.id)
    {
        if let Some(completed) = &account.completed {
            writeln!(
                value,
                "\nCOMMITTED WORK TIME / PERIOD {} / DERIVED\n{} used + {} unused = {} available\nProduction planned: {} {}",
                completed.period,
                grouped(completed.used),
                grouped(completed.unused),
                grouped(completed.opening),
                grouped(completed.planned),
                account.unit,
            )
            .expect("String write");
            if site.roles.iter().any(|r| {
                matches!(
                    r,
                    babylon_persistence::production_observation::ProductionSiteRole::Wholesale
                        | babylon_persistence::production_observation::ProductionSiteRole::Retail
                )
            }) || completed.handling_needed != 0
                || completed.handling_used != 0
            {
                writeln!(
                    value,
                    "Handling: {} needed · {} used {}",
                    grouped(completed.handling_needed),
                    grouped(completed.handling_used),
                    account.unit
                )
                .expect("String write");
            }
            if completed.maintenance_needed != 0
                || completed.maintenance_used != 0
                || site.roles.contains(
                    &babylon_persistence::production_observation::ProductionSiteRole::Maintenance,
                )
            {
                writeln!(
                    value,
                    "Maintenance: {} needed · {} used {}",
                    grouped(completed.maintenance_needed),
                    grouped(completed.maintenance_used),
                    account.unit
                )
                .expect("String write");
            }
            if completed.installation_needed != 0 || completed.installation_used != 0 {
                writeln!(
                    value,
                    "Installation: {} awaiting work · {} used {}",
                    grouped(completed.installation_needed),
                    grouped(completed.installation_used),
                    account.unit
                )
                .expect("String write");
            }
            value.push_str("Time accounts do not measure job losses.\n");
        }
        writeln!(
            value,
            "Next opening (period {}): {} {} (Derived)",
            account.next_opening_period,
            grouped(account.next_opening_available),
            account.unit,
        )
        .expect("String write");
    }
}

fn describe_households(value: &mut String, site: &ProductionSite, snapshot: &ProductionSnapshot) {
    for row in snapshot
        .household_accounts
        .iter()
        .filter(|r| r.retailer_site_id == site.id)
    {
        writeln!(
            value,
            "HOUSEHOLD GOODS / {} / {}\n{} households · {} persons · {} {} needed each period",
            row.location,
            row.good,
            grouped(row.household_count),
            grouped(row.person_count),
            grouped(row.required_per_period),
            row.unit
        )
        .expect("String write");
        if let Some(done) = &row.completed {
            writeln!(
                value,
                "{} purchased · {} support received · {} support sent · {} consumed · {} unmet · {} in pantry",
                grouped(done.received),
                grouped(done.support_granted),
                grouped(done.support_dispatched),
                grouped(done.consumed),
                grouped(done.unmet),
                grouped(done.closing_stock)
            )
            .expect("String write");
        }
    }
    for row in snapshot
        .household_service_accounts
        .iter()
        .filter(|r| r.provider_site_ids.contains(&site.id))
    {
        writeln!(
            value,
            "HOUSEHOLD SERVICE / {} / {}\n{} households · {} persons · {} {} needed each period",
            row.location,
            row.good,
            grouped(row.household_count),
            grouped(row.person_count),
            grouped(row.required_per_period),
            row.unit
        )
        .expect("String write");
        if let Some(done) = &row.completed {
            writeln!(
                value,
                "{} requested · {} funded · {} performed · {} need satisfied · {} unmet",
                grouped(done.requested),
                grouped(done.admitted),
                grouped(done.performed),
                grouped(done.satisfied),
                grouped(done.unmet)
            )
            .expect("String write");
        } else {
            value.push_str("Foundation; no completed service period.\n");
        }
    }
}

fn describe_prices(value: &mut String, site: &ProductionSite, snapshot: &ProductionSnapshot) {
    use babylon_persistence::{GoodsPriceBasis, GoodsPriceReason};
    for row in snapshot
        .goods_price_accounts
        .iter()
        .filter(|r| r.site_id == site.id)
    {
        writeln!(
            value,
            "\nQUOTE / {}\n{} micro-currency per {}",
            row.good, row.current_price_micro, row.unit
        )
        .expect("String write");
        if let Some(done) = &row.completed {
            let reason = match done.reason {
                GoodsPriceReason::Fixed => "Fixed quote",
                GoodsPriceReason::Hold => "Quote held",
                GoodsPriceReason::UnservedDemand => "Unserved demand",
                GoodsPriceReason::ExcessStock => "Excess stock",
                GoodsPriceReason::CostPressure => "Direct cost pressure",
            };
            writeln!(
                value,
                "{reason}: {} → {}\n{} unserved · {} closing stock",
                done.old_price_micro,
                done.next_price_micro,
                grouped(done.unserved_quantity),
                grouped(done.closing_stock)
            )
            .expect("String write");
            match done.cost_basis {
                GoodsPriceBasis::Unavailable => {
                    value.push_str("No current production or stock-release cost observation.\n");
                }
                basis => {
                    let basis = if basis == GoodsPriceBasis::Produced {
                        "produced"
                    } else {
                        "released from seller stock"
                    };
                    writeln!(value,"{} {} {basis} · {} carrying + {} handling wages (micro-currency)\nCommitted direct cost per unit: {}",grouped(done.basis_quantity),row.unit,done.carrying_cost_micro,done.handling_wages_micro,done.unit_cost_micro.expect("validated price evidence")).expect("String write");
                }
            }
        }
    }
}

#[cfg(test)]
mod aid_reading_tests {
    use super::*;
    #[test]
    fn household_reading_separates_purchases_and_both_gift_directions() {
        let mut snapshot = crate::production_freight::tests::aid_fixture();
        snapshot.household_accounts[0].completed =
            Some(babylon_persistence::CompletedHouseholdBalance {
                period: 1,
                opening_stock: 5,
                received: 3,
                support_granted: 2,
                support_dispatched: 4,
                required: 4,
                consumed: 4,
                unmet: 0,
                closing_stock: 2,
                desired: 3,
                requested: 3,
                admitted: 3,
                fulfilled: 3,
                expired: 0,
            });
        let site = snapshot.sites.iter().find(|s| s.id == "panels").unwrap();
        let mut text = String::new();
        describe_households(&mut text, site, &snapshot);
        assert!(text.contains("3 purchased · 2 support received · 4 support sent · 4 consumed · 0 unmet · 2 in pantry"));
        assert!(text.contains("4 households · 4 persons"));
    }
}
