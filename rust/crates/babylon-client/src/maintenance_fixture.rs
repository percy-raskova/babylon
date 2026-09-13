//! Test data enters through the same strict serialized observer disclosure.
use babylon_persistence::production_observation::ProductionSnapshot;
use serde_json::{json, Value};

pub(crate) fn maintenance(mut value: Value, period: u64, jobs: Option<u64>) -> Value {
    let process = value["sites"][0]["processes"][0].clone();
    let consumer = value["sites"][0]["id"].clone();
    let provider = "9".repeat(64);
    value["sites"].as_array_mut().unwrap().push(json!({
        "id": provider, "county_geoid": "26163", "name": "Wayne maintenance",
        "industry_code": "811310", "observed_employment": null, "role": "Maintenance",
        "sector_code": "81", "processes": [], "inventory": []
    }));
    value["labor_accounts"].as_array_mut().unwrap().push(json!({
        "site_id": provider, "unit_id": "8".repeat(64), "unit": "labor-hours",
        "next_opening_period": period + 1, "next_opening_available": 40,
        "completed": jobs.map(|n| json!({
            "period": period, "opening": n * 10, "planned": 0, "used": n * 10,
            "unused": 0, "handling_needed": 0, "handling_used": 0,
            "maintenance_needed": 40, "maintenance_used": n * 10
        }))
    }));
    value["maintenance_account"] = json!({
        "provider_site_id": provider, "consumer_site_id": consumer,
        "consumer_process_id": process["id"], "spare_good_id": process["output_good_id"],
        "spare_unit_id": process["output_unit_id"], "spare_good": process["output_good"],
        "spare_unit": process["output_unit"], "labor_unit_id": "8".repeat(64), "labor_unit": "labor-hours",
        "output_good_id": process["output_good_id"], "output_unit_id": process["output_unit_id"],
        "output_good": process["output_good"], "output_unit": process["output_unit"],
        "output_per_batch": process["output_per_batch"], "spare_units_per_job": 2,
        "labor_units_per_job": 10, "enabled_batches_per_job": 2, "maximum_jobs_per_period": 4,
        "next_service_period": period + 1, "next_service_batches": jobs.map_or(4, |n| n * 2),
        "completed": jobs.map(|n| json!({
            "period": period, "opening_service_batches": 6, "consumed_service_batches": 4,
            "expired_service_batches": 2, "prospective_batches": 8, "requested_jobs": 4,
            "opening_spare_parts": 8, "arrived_spare_parts": 0, "available_spare_parts": 8,
            "available_labor_hours": n * 10, "completed_jobs": n, "consumed_spare_parts": n * 2,
            "consumed_labor_hours": n * 10
        }))
    });
    value
}

pub(crate) fn snapshot(
    source: &ProductionSnapshot,
    period: u64,
    jobs: Option<u64>,
) -> ProductionSnapshot {
    serde_json::from_value(maintenance(
        serde_json::to_value(source).unwrap(),
        period,
        jobs,
    ))
    .expect("the current observer disclosure must admit one maintenance account")
}
