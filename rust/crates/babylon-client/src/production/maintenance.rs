//! Read one disclosed maintenance account without forecasting production.
use crate::observer_ui::grouped;
use babylon_persistence::production_observation::{
    ProductionMaintenanceAccount, ProductionSiteRole, ProductionSnapshot,
};
use std::fmt::Write as _;

pub(crate) fn account<'a>(
    snapshot: &'a ProductionSnapshot,
    site: &str,
) -> Option<&'a ProductionMaintenanceAccount> {
    let account = snapshot.maintenance_account.as_ref()?;
    if site != account.provider_site_id && site != account.consumer_site_id {
        return None;
    }
    snapshot.sites.iter().find(|site| {
        site.id == account.provider_site_id && site.role == ProductionSiteRole::Maintenance
    })?;
    snapshot
        .sites
        .iter()
        .find(|site| site.id == account.consumer_site_id)?
        .processes
        .iter()
        .find(|process| {
            process.id == account.consumer_process_id
                && process.output_good_id == account.output_good_id
                && process.output_unit_id == account.output_unit_id
                && process.output_per_batch == account.output_per_batch
        })?;
    Some(account)
}

pub(crate) fn next_output(account: &ProductionMaintenanceAccount) -> Option<u64> {
    account
        .next_service_batches
        .checked_mul(account.output_per_batch)
}

pub(super) fn flow(value: &mut String, site: &str, snapshot: &ProductionSnapshot) {
    let Some(account) = account(snapshot, site) else {
        return;
    };
    let name = |id: &str| {
        snapshot
            .sites
            .iter()
            .find(|site| site.id == id)
            .map_or("undisclosed", |site| site.name.as_str())
    };
    writeln!(
        value,
        "MAINTENANCE SERVICE\n{} → {}",
        name(&account.provider_site_id),
        name(&account.consumer_site_id)
    )
    .expect("String write");
    if let Some(done) = &account.completed {
        writeln!(value, "Period {}: {} / {} jobs completed / requested\nParts: {} opened + {} arrived = {} {} available\nUsed: {} {} parts + {} labor-hours\n{} consumed + {} expired = {} opening batches",
            done.period, grouped(done.completed_jobs), grouped(done.requested_jobs), grouped(done.opening_spare_parts),
            grouped(done.arrived_spare_parts), grouped(done.available_spare_parts), account.spare_unit,
            grouped(done.consumed_spare_parts), account.spare_unit, grouped(done.consumed_labor_hours),
            grouped(done.consumed_service_batches), grouped(done.expired_service_batches), grouped(done.opening_service_batches)).expect("String write");
        writeln!(
            value,
            "Next work request: {} material-feasible batches",
            grouped(done.prospective_batches)
        )
        .expect("String write");
        writeln!(
            value,
            "Job limits: parts {} · labor {} · Designed maximum {}",
            limit(done.available_spare_parts, account.spare_units_per_job),
            limit(done.available_labor_hours, account.labor_units_per_job),
            grouped(account.maximum_jobs_per_period)
        )
        .expect("String write");
    } else {
        value.push_str("Foundation; no completed maintenance receipt.\n");
    }
    writeln!(value, "Service for period {}: {} batches / up to {} {}\nActual output needs the following production receipt.\nUnused service expires; service is not stock or a parts shipment.\n",
        account.next_service_period, grouped(account.next_service_batches), next_output(account).map_or_else(|| "unavailable".into(),grouped), account.output_unit).expect("String write");
}

fn limit(available: u64, coefficient: u64) -> String {
    available
        .checked_div(coefficient)
        .map_or_else(|| "unavailable".into(), grouped)
}

pub(super) fn work(value: &mut String, site: &str, snapshot: &ProductionSnapshot) {
    let Some(account) = account(snapshot, site) else {
        return;
    };
    if site != account.provider_site_id {
        return;
    }
    value.push_str("\nMAINTENANCE WORK\n");
    if let Some(done) = &account.completed {
        writeln!(
            value,
            "Maintenance: {} used / {} requested labor-hours",
            grouped(done.consumed_labor_hours),
            done.requested_jobs
                .checked_mul(account.labor_units_per_job)
                .map_or_else(|| "unavailable".into(), grouped)
        )
        .expect("String write");
    } else {
        value.push_str("Foundation; no completed maintenance receipt.\n");
    }
    value.push_str("Service jobs use parts and hours. These are separate from production and merchant handling.\n");
}

pub(super) fn sources(value: &mut String, site: &str, snapshot: &ProductionSnapshot) {
    let Some(account) = account(snapshot, site) else {
        return;
    };
    writeln!(value, "\nMAINTENANCE COEFFICIENTS\n{} {} parts + {} labor-hours per job / Designed\n{} enabled batches per job · maximum {} jobs per period / Designed\nBinding: provider {}\nConsumer {} / process {}\nParts {} / unit {}\nLabor unit {}\nOutput {} / unit {}",
        grouped(account.spare_units_per_job), account.spare_unit, grouped(account.labor_units_per_job),
        grouped(account.enabled_batches_per_job), grouped(account.maximum_jobs_per_period), account.provider_site_id,
        account.consumer_site_id, account.consumer_process_id, account.spare_good_id, account.spare_unit_id,
        account.labor_unit_id, account.output_good_id, account.output_unit_id).expect("String write");
}

pub(crate) fn compatible(
    a: &ProductionMaintenanceAccount,
    b: &ProductionMaintenanceAccount,
) -> bool {
    a.provider_site_id == b.provider_site_id
        && a.consumer_site_id == b.consumer_site_id
        && a.consumer_process_id == b.consumer_process_id
        && a.spare_good_id == b.spare_good_id
        && a.spare_unit_id == b.spare_unit_id
        && a.labor_unit_id == b.labor_unit_id
        && a.output_good_id == b.output_good_id
        && a.output_unit_id == b.output_unit_id
        && a.output_per_batch == b.output_per_batch
        && a.spare_units_per_job == b.spare_units_per_job
        && a.labor_units_per_job == b.labor_units_per_job
        && a.enabled_batches_per_job == b.enabled_batches_per_job
        && a.maximum_jobs_per_period == b.maximum_jobs_per_period
}

pub(crate) fn comparison(
    value: &mut String,
    site: &str,
    current: &ProductionSnapshot,
    compared: &ProductionSnapshot,
    period: u64,
) {
    let Some(a) = account(current, site) else {
        return;
    };
    let Some(b) = account(compared, site)
        .filter(|b| compatible(a, b) && a.next_service_period == b.next_service_period)
    else {
        value.push_str("Compatible maintenance account unavailable.\n");
        return;
    };
    if period.checked_add(1) != Some(a.next_service_period) {
        value.push_str("Matching completed maintenance receipts unavailable.\n");
        return;
    }
    value.push_str("MAINTENANCE SERVICE\n");
    match (&a.completed, &b.completed) {
        (Some(x), Some(y)) if x.period == period && y.period == period => {
            writeln!(value, "CURRENT  {} / {} jobs completed / requested\nCOMPARED  {} / {} jobs completed / requested\nParts available: {} / {} {} · used {} / {}\nLabor available: {} / {} hours · used {} / {}\nExpired service: {} / {} batches\nConsumed service: {} / {} batches",
                grouped(x.completed_jobs), grouped(x.requested_jobs), grouped(y.completed_jobs), grouped(y.requested_jobs),
                grouped(x.available_spare_parts), grouped(y.available_spare_parts), a.spare_unit, grouped(x.consumed_spare_parts), grouped(y.consumed_spare_parts),
                grouped(x.available_labor_hours), grouped(y.available_labor_hours), grouped(x.consumed_labor_hours), grouped(y.consumed_labor_hours),
                grouped(x.expired_service_batches), grouped(y.expired_service_batches), grouped(x.consumed_service_batches), grouped(y.consumed_service_batches)).expect("String write");
            writeln!(value, "Parts opened: {} / {} · arrived {} / {} {}\nProspective work: {} / {} material-feasible batches",
                grouped(x.opening_spare_parts), grouped(y.opening_spare_parts), grouped(x.arrived_spare_parts), grouped(y.arrived_spare_parts), a.spare_unit,
                grouped(x.prospective_batches), grouped(y.prospective_batches)).expect("String write");
        }
        (None, None) if period == 0 => {
            value.push_str("Foundation; no completed maintenance receipt.\n");
        }
        _ => {
            value.push_str("Matching completed maintenance receipts unavailable.\n");
            return;
        }
    }
    writeln!(value, "Period {} service: {} / {} batches · up to {} / {} {}\nDesigned per job: {} {} parts, {} labor-hours, {} enabled batches; maximum {} jobs.\nActual output needs the following production receipt.",
        a.next_service_period, grouped(a.next_service_batches), grouped(b.next_service_batches),
        next_output(a).map_or_else(|| "unavailable".into(),grouped), next_output(b).map_or_else(|| "unavailable".into(),grouped), a.output_unit,
        grouped(a.spare_units_per_job), a.spare_unit, grouped(a.labor_units_per_job), grouped(a.enabled_batches_per_job), grouped(a.maximum_jobs_per_period)).expect("String write");
}
