//! County identity is common; national observations are captured source metadata.
use super::{
    read_committed_counties, CampaignId, EconomicContentAdmission, ObserverCountyEconomy,
    ObserverEconomyError, ObserverVisibility, SNAPSHOT_COLUMNS,
};
use crate::{economic_catalog::EconomicSourceView, national_counties::NationalCountyReference};
use babylon_kernel::geography::{CountyGeoid, NationalCountyRoster, NATIONAL_COUNTY_COUNT};
type Result<T> = std::result::Result<T, ObserverEconomyError>;

pub(super) fn read(
    transaction: &mut postgres::Transaction<'_>,
    campaign: CampaignId,
    tick: u64,
    visibility: ObserverVisibility,
    scope: &str,
    admission: Option<&EconomicContentAdmission>,
) -> Result<Vec<ObserverCountyEconomy>> {
    match (scope, admission.map(|a| a.view().sources)) {
        ("michigan-control", Some(EconomicSourceView::MichiganControl { counties, .. })) => {
            read_committed_counties(transaction, campaign, tick, visibility, counties.counties())
        }
        ("michigan-control", None) => {
            let reference = crate::michigan_economy::michigan_economy()
                .map_err(|_| ObserverEconomyError::Reference)?;
            read_committed_counties(
                transaction,
                campaign,
                tick,
                visibility,
                reference.counties(),
            )
        }
        ("national-counties", Some(EconomicSourceView::National { counties, .. })) => {
            national(transaction, campaign, tick, visibility, Some(counties))
        }
        ("national-counties", None) if visibility == ObserverVisibility::KnownPreview => {
            national(transaction, campaign, tick, visibility, None)
        }
        _ => Err(ObserverEconomyError::ScenarioMismatch),
    }
}
fn national(
    transaction: &mut postgres::Transaction<'_>,
    campaign: CampaignId,
    expected_tick: u64,
    visibility: ObserverVisibility,
    source: Option<&NationalCountyReference>,
) -> Result<Vec<ObserverCountyEconomy>> {
    let tick = i64::try_from(expected_tick).map_err(|_| ObserverEconomyError::TickAbsent)?;
    let view = match visibility {
        ObserverVisibility::FullObserver => "public.v_observer_county_economy_v1",
        ObserverVisibility::KnownPreview => "public.v_known_county_economy_v1",
    };
    let query = format!("SELECT {SNAPSHOT_COLUMNS} FROM {view} WHERE campaign_id=$1 AND resolve_tick=$2 ORDER BY county_geoid LIMIT 3145");
    let rows = transaction
        .query(&query, &[campaign.as_uuid(), &tick])
        .map_err(|_| ObserverEconomyError::Database)?;
    if rows.len() != NATIONAL_COUNTY_COUNT {
        return Err(ObserverEconomyError::InvalidProjection);
    }
    let mut counties = Vec::with_capacity(rows.len());
    let mut identities = Vec::with_capacity(rows.len());
    for (index, row) in rows.iter().enumerate() {
        let row_campaign: uuid::Uuid = row.try_get(0).map_err(invalid)?;
        let row_tick: i64 = row.try_get(1).map_err(invalid)?;
        let geoid: String = row.try_get(2).map_err(invalid)?;
        if &row_campaign != campaign.as_uuid() || row_tick != tick {
            return Err(ObserverEconomyError::InvalidProjection);
        }
        let identity = CountyGeoid::try_from(geoid.as_str())
            .map_err(|_| ObserverEconomyError::InvalidProjection)?;
        let mut grants = [false; 4];
        for (field, grant) in grants.iter_mut().enumerate() {
            // No national QCEW mutable graph stock exists. Publishing one here
            // would mix a current simulation quantity with a source observation.
            if row
                .try_get::<_, Option<i64>>(field + 3)
                .map_err(invalid)?
                .is_some()
            {
                return Err(ObserverEconomyError::InvalidProjection);
            }
            *grant = row.try_get(field + 7).map_err(invalid)?;
        }
        let values = if let Some(source) = source {
            let county = &source.counties()[index];
            if county.geoid() != identity {
                return Err(ObserverEconomyError::InvalidProjection);
            }
            let workplace = county.workplaces();
            [
                workplace.establishments.value(),
                workplace.jobs.value(),
                workplace.annual_payroll_usd.value(),
                workplace.mean_weekly_wage_usd.value(),
            ]
        } else {
            [None; 4]
        };
        counties.push(project(identity, visibility, values, grants)?);
        identities.push(identity);
    }
    // A known-only reader proves exact geography from the permitted rows, without
    // opening the opaque material foundation or substituting current data files.
    NationalCountyRoster::try_new(identities)
        .map_err(|_| ObserverEconomyError::InvalidProjection)?;
    Ok(counties)
}
fn invalid(_: postgres::Error) -> ObserverEconomyError {
    ObserverEconomyError::InvalidProjection
}
fn project(
    identity: CountyGeoid,
    visibility: ObserverVisibility,
    mut values: [Option<u64>; 4],
    grants: [bool; 4],
) -> Result<ObserverCountyEconomy> {
    for (value, granted) in values.iter_mut().zip(grants) {
        if visibility == ObserverVisibility::FullObserver && !granted {
            return Err(ObserverEconomyError::InvalidProjection);
        }
        if !granted {
            *value = None;
        }
    }
    Ok(ObserverCountyEconomy {
        county_geoid: identity.to_string(),
        annual_avg_estabs_count: values[0],
        annual_avg_emplvl: values[1],
        total_annual_wages: values[2],
        annual_avg_wkly_wage: values[3],
    })
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn absent_workplace_evidence_stays_absent_for_a_real_resident_county() {
        let geoid = CountyGeoid::try_from("15005").unwrap();
        let county = project(
            geoid,
            ObserverVisibility::FullObserver,
            [None; 4],
            [true; 4],
        )
        .unwrap();
        assert_eq!(county.county_geoid, "15005");
        assert_eq!(county.annual_avg_emplvl, None);
        assert_eq!(county.total_annual_wages, None);
    }
    #[test]
    fn known_preview_masks_source_fields_without_inventing_zero() {
        let county = project(
            CountyGeoid::try_from("26163").unwrap(),
            ObserverVisibility::KnownPreview,
            [Some(12), Some(44), None, Some(300)],
            [true, false, true, false],
        )
        .unwrap();
        assert_eq!(county.annual_avg_estabs_count, Some(12));
        assert_eq!(county.annual_avg_emplvl, None);
        assert_eq!(county.total_annual_wages, None);
        assert_eq!(county.annual_avg_wkly_wage, None);
    }
}
