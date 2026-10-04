//! Bounded qualification output from the same authenticated native economic reader.
use babylon_kernel::economic_location::EconomicLocation;
use babylon_persistence::{
    identity::CampaignId,
    national_counties::national_county_reference,
    observer_reader::{ObserverEconomyReader, ObserverEconomySnapshot, ObserverVisibility},
    CommittedTickStatus, SemanticArchiveReader,
};
use serde_json::{json, Value};
use std::{collections::BTreeSet, time::Instant};

pub(crate) fn read(reader: &SemanticArchiveReader, campaign: CampaignId) -> Result<Value, String> {
    let start = Instant::now();
    let tail = reader
        .committed_tick_status(campaign)
        .map_err(|e| e.to_string())?;
    let period = tail.as_ref().map_or(0, CommittedTickStatus::resolve_tick);
    let mut snapshot = ObserverEconomyReader::from_observer_env()
        .map_err(|e| e.to_string())?
        .snapshot(campaign, period)
        .map_err(|e| e.to_string())?;
    let hash = tail
        .as_ref()
        .map(|row| crate::dossier::hex_bytes(*row.tick_content_hash()));
    if snapshot.campaign_id != campaign.as_uuid().to_string()
        || snapshot.resolve_tick != period
        || snapshot.tick_content_hash != hash
    {
        return Err("Economic snapshot differs from its requested committed identity".into());
    }
    let mut summary = summarize(&snapshot)?;
    let production = snapshot
        .production
        .as_ref()
        .ok_or("Economic projection absent")?;
    let counts = (
        production.sites.len(),
        production.household_accounts.len(),
        production.household_service_accounts.len(),
    );
    let evidence = snapshot
        .production_evidence_digest()
        .map_err(|error| {
            format!(
                "{error}; sites={}, household goods={}, household services={}",
                counts.0, counts.1, counts.2
            )
        })?
        .ok_or("Economic projection has no display evidence")?;
    summary["production_evidence_sha256"] = evidence.to_hex().into();
    summary["read_elapsed_us"] = u64::try_from(start.elapsed().as_micros())
        .map_err(|_| "Economic read duration exceeds its reporting range")?
        .into();
    Ok(summary)
}

fn summarize(snapshot: &ObserverEconomySnapshot) -> Result<Value, String> {
    if snapshot.visibility != ObserverVisibility::FullObserver {
        return Err("Economic qualification requires the full-observer capability".into());
    }
    let production = snapshot
        .production
        .as_ref()
        .ok_or("Economic snapshot has no material projection")?;
    let counties: BTreeSet<_> = snapshot
        .counties
        .iter()
        .map(|row| row.county_geoid.as_str())
        .collect();
    if counties.len() != snapshot.counties.len() {
        return Err("Economic snapshot contains duplicate county identities".into());
    }
    let pinned: BTreeSet<_> = national_county_reference()
        .map_err(|e| e.to_string())?
        .counties()
        .iter()
        .map(|county| county.geoid().to_string())
        .collect();
    let exact_national_roster = counties
        .iter()
        .copied()
        .eq(pinned.iter().map(String::as_str));
    // Count captured budget principals, including collective residence; never
    // treat this as an observed count of households or individual people.
    let households: BTreeSet<_> = production
        .household_accounts
        .iter()
        .map(|a| a.demand_principal_id.as_str())
        .chain(
            production
                .household_service_accounts
                .iter()
                .map(|a| a.demand_principal_id.as_str()),
        )
        .collect();
    let locations: BTreeSet<_> = production
        .household_accounts
        .iter()
        .map(|a| a.location)
        .chain(
            production
                .household_service_accounts
                .iter()
                .map(|a| a.location),
        )
        .collect();
    let resident_counties: BTreeSet<_> = locations
        .iter()
        .filter_map(|location| match location {
            EconomicLocation::County(county) => Some(county.geoid().to_string()),
            _ => None,
        })
        .collect();
    Ok(json!({
        "record": "economy-status", "schema_version": 2,
        "campaign_id": snapshot.campaign_id, "resolve_tick": snapshot.resolve_tick,
        "foundation_digest": snapshot.foundation_digest,
        "tick_content_hash": snapshot.tick_content_hash,
        "nominal_world_hash": snapshot.nominal_world_hash,
        "envelope_digest": snapshot.envelope_digest,
        "visibility": snapshot.visibility, "duration": production.duration,
        "county_count": counties.len(), "exact_national_roster": exact_national_roster,
        "domestic_household_locations": resident_counties.len(),
        "households_cover_national_roster": resident_counties == pinned,
        "external_household_locations": locations.len() - resident_counties.len(),
        "household_cohorts": households.len(), "sites": production.sites.len(),
        "household_goods_accounts": production.household_accounts.len(),
        "household_service_accounts": production.household_service_accounts.len(),
        "completed_household_goods_accounts": production.household_accounts.iter().filter(|a| a.completed.is_some()).count(),
        "completed_household_service_accounts": production.household_service_accounts.iter().filter(|a| a.completed.is_some()).count(),
        "completed_material_balance": production.material_balance.is_some(),
        "price_accounts": production.goods_price_accounts.len(),
    }))
}

#[cfg(test)]
mod tests {
    use super::*;
    use babylon_persistence::observer_reader::ObserverCountyEconomy;
    #[test]
    fn county_scope_is_checked_by_identity_not_only_the_3144_count() {
        let state =
            crate::observer::ObserverSession::new(CampaignId::from_uuid(uuid::Uuid::from_u128(7)));
        let mut snapshot = crate::observer_io::tests::snapshot_with_event(&state, "delivery", 1);
        snapshot.counties = national_county_reference()
            .unwrap()
            .counties()
            .iter()
            .map(|county| ObserverCountyEconomy {
                county_geoid: county.geoid().to_string(),
                annual_avg_estabs_count: None,
                annual_avg_emplvl: None,
                total_annual_wages: None,
                annual_avg_wkly_wage: None,
            })
            .collect();
        let report = summarize(&snapshot).unwrap();
        assert_eq!(report["county_count"], 3144);
        assert_eq!(report["exact_national_roster"], true);
        let first_county = snapshot.counties[0].county_geoid.clone();
        snapshot.counties[0].county_geoid = "72001".into();
        assert_eq!(
            summarize(&snapshot).unwrap()["exact_national_roster"],
            false
        );
        snapshot.counties[0].county_geoid = snapshot.counties[1].county_geoid.clone();
        assert!(summarize(&snapshot).is_err());
        snapshot.counties[0].county_geoid = first_county;
        snapshot.visibility = ObserverVisibility::KnownPreview;
        assert!(summarize(&snapshot).is_err());
    }
}
