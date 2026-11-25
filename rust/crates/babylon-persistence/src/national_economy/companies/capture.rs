//! Bind eligible whole opening workplaces to captured employment and fixed site geography.
use super::assign::{self, Site};
use super::model::{CompanyCapture, CompanyCaptureError, EmploymentTargets};
use crate::national_economy::grain::ResidentWorkplaceSourceKind;
use crate::national_economy::{ResidentWorkplaceSource, ResidentWorkplaceTarget};
use crate::national_resident_allocation::AssignedResidentWorkplace;
use babylon_kernel::economic_identity::{EconomicFunction, QcewOwnership, TradeSet};
use babylon_kernel::economic_location::EconomicLocation;
use babylon_kernel::geography::CountyGeoid;
use std::collections::BTreeMap;

pub(super) fn eligible_county(
    target: &ResidentWorkplaceTarget,
) -> Result<Option<CountyGeoid>, CompanyCaptureError> {
    let EconomicLocation::County(location) = target.location else {
        return Ok(None);
    };
    let county = location.geoid();
    let (ownership, function) = match &target.source {
        ResidentWorkplaceSource::Qcew(key) => {
            if key.county != county {
                return Err(CompanyCaptureError::InvalidSource(target.site_id));
            }
            (key.ownership, key.function)
        }
        ResidentWorkplaceSource::Representative(key) => {
            if key.source_kind != ResidentWorkplaceSourceKind::Qcew {
                return Ok(None);
            }
            (key.ownership, Some(key.function))
        }
        ResidentWorkplaceSource::HouseholdEnterprise
        | ResidentWorkplaceSource::ResidentEmployerFallback => return Ok(None),
    };
    if ownership != target.ownership || function != Some(target.function) {
        return Err(CompanyCaptureError::InvalidSource(target.site_id));
    }
    Ok((ownership == QcewOwnership::Private
        && target.function != EconomicFunction::PublicProvisioning)
        .then_some(county))
}

/// Construct the captured foundation's membership only after workplace coarsening is complete.
pub(in crate::national_economy) fn from_workplaces(
    trades: TradeSet,
    workplaces: &[AssignedResidentWorkplace],
    targets: EmploymentTargets,
) -> Result<CompanyCapture, CompanyCaptureError> {
    let mut by_function = BTreeMap::<EconomicFunction, Vec<Site>>::new();
    for workplace in workplaces {
        let target = &workplace.target;
        let Some(county) = eligible_county(target)? else {
            continue;
        };
        let employed = workplace.members.iter().try_fold(0_u64, |sum, member| {
            sum.checked_add(member.seed.employed)
                .ok_or(CompanyCaptureError::Arithmetic)
        })?;
        by_function.entry(target.function).or_default().push(Site {
            id: target.site_id,
            function: target.function,
            county,
            employed,
        });
    }
    let mut capture = CompanyCapture {
        targets,
        companies: vec![],
        members: vec![],
        cells: vec![],
    };
    for function in trades
        .functions()
        .iter()
        .copied()
        .filter(|f| *f != EconomicFunction::PublicProvisioning)
    {
        let sites = by_function.remove(&function).unwrap_or_default();
        let mut grouping = assign::for_function(function, &sites, targets)?;
        capture.companies.append(&mut grouping.companies);
        capture.members.append(&mut grouping.members);
        capture.cells.append(&mut grouping.cells);
    }
    capture.members.sort_unstable_by_key(|m| m.site);
    if let Some(rows) = capture
        .members
        .windows(2)
        .find(|pair| pair[0].site == pair[1].site)
    {
        return Err(CompanyCaptureError::DuplicateSite(rows[0].site));
    }
    Ok(capture)
}
