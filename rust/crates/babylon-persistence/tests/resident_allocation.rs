//! Source-controlled persons reach sparse graph seed partitions, never inferred jobs.
use babylon_persistence::{
    national_cohorts::national_cohort_reference,
    national_counties::national_county_reference,
    national_economy::{NationalGamePolicy, ResidentWorkplaceSource},
    national_resident_allocation::{allocate_home_county, ResidentAttendanceMode},
    national_resident_workforce::national_resident_workforce_reference,
};

#[test]
fn home_county_allocation_conserves_all_resident_controls_and_keeps_source_zero_pools() {
    let counties = national_county_reference().unwrap();
    let cohorts = national_cohort_reference().unwrap();
    let classes = national_resident_workforce_reference().unwrap();
    let policy = NationalGamePolicy::parse(include_str!(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../../../content/scenarios/national/defines.toml"
    )))
    .unwrap();
    let allocation = allocate_home_county(counties, cohorts, classes, &policy).unwrap();
    assert_eq!(allocation.counties.len(), 3144);
    assert_eq!(allocation.workplaces.len(), 60454);
    assert_eq!(
        allocation
            .workplaces
            .iter()
            .map(|r| r.members.len())
            .sum::<usize>(),
        62745
    );
    assert_eq!(
        allocation
            .workplaces
            .iter()
            .filter(|r| matches!(r.target.source, ResidentWorkplaceSource::Qcew(_)))
            .count(),
        57238
    );
    assert_eq!(
        allocation
            .workplaces
            .iter()
            .filter(|r| r.members.is_empty())
            .count(),
        351
    );
    assert_eq!(
        allocation.counties.iter().map(|r| r.employed).sum::<u64>(),
        161_297_155
    );
    assert_eq!(
        allocation.counties.iter().map(|r| r.reserve).sum::<u64>(),
        8_902_365
    );
    for row in &allocation.workplaces {
        for m in &row.members {
            assert_eq!(m.seed.member.residence(), row.target.location);
            assert_eq!(
                m.seed.employed + m.seed.reserve,
                m.seed.member.labor_force()
            );
            if m.mode != ResidentAttendanceMode::Employee {
                assert_eq!(m.seed.reserve, 0);
            }
            let babylon_graph::stable_element::StableElementKey::Node { local_name, .. } =
                &m.seed.subject
            else {
                panic!("member must be node")
            };
            assert_eq!(local_name.len(), 59);
            assert!(m.seed.subject.canonical_bytes().is_ok());
        }
    }
}

#[test]
fn kalawao_employees_have_explicit_fallbacks_and_owner_activity_is_not_a_missing_job_residual() {
    let allocation = allocate_home_county(
        national_county_reference().unwrap(),
        national_cohort_reference().unwrap(),
        national_resident_workforce_reference().unwrap(),
        &NationalGamePolicy::parse(include_str!(concat!(
            env!("CARGO_MANIFEST_DIR"),
            "/../../../content/scenarios/national/defines.toml"
        )))
        .unwrap(),
    )
    .unwrap();
    let county = "15005".parse().unwrap();
    let rows:Vec<_>=allocation.workplaces.iter().filter(|r|matches!(r.target.location,babylon_kernel::economic_location::EconomicLocation::County(c) if c.geoid()==county)).collect();
    assert_eq!(rows.len(), 4);
    assert_eq!(
        rows.iter()
            .filter(|r| matches!(
                r.target.source,
                ResidentWorkplaceSource::ResidentEmployerFallback
            ))
            .count(),
        3
    );
    let enterprise = rows
        .iter()
        .find(|r| {
            matches!(
                r.target.source,
                ResidentWorkplaceSource::HouseholdEnterprise
            )
        })
        .unwrap();
    assert_eq!(enterprise.members.len(), 1);
    assert_eq!(
        enterprise.members[0].mode,
        ResidentAttendanceMode::WorkingOwner
    );
    assert_eq!(enterprise.members[0].seed.employed, 3);
    assert_eq!(
        rows.iter()
            .flat_map(|r| &r.members)
            .map(|m| m.seed.employed)
            .sum::<u64>(),
        49
    );
}

#[test]
fn suppressed_jobs_remain_absent_when_peer_weights_place_resident_people() {
    let cohorts = national_cohort_reference().unwrap();
    let policy = NationalGamePolicy::parse(include_str!(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../../../content/scenarios/national/defines.toml"
    )))
    .unwrap();
    let allocation = allocate_home_county(
        national_county_reference().unwrap(),
        cohorts,
        national_resident_workforce_reference().unwrap(),
        &policy,
    )
    .unwrap();
    assert_eq!(
        allocation.function_mapping_sha256,
        cohorts.function_mapping_sha256()
    );
    let mut suppressed_groups = 0;
    for assigned in &allocation.workplaces {
        let ResidentWorkplaceSource::Qcew(key) = assigned.target.source else {
            continue;
        };
        let source = cohorts.group(key).unwrap();
        let weight = assigned.weight.as_ref().unwrap();
        assert_eq!(weight.published_jobs, source.jobs().known_subtotal());
        assert_eq!(
            weight.source_jobs_complete,
            source.jobs().complete_total().is_some()
        );
        if !weight.source_jobs_complete {
            suppressed_groups += 1;
        }
        for imputed in &weight.imputed {
            let original = source
                .members()
                .iter()
                .find(|r| r.naics_code == imputed.naics_code)
                .unwrap();
            assert_eq!(original.annual_average_jobs, None);
            assert_eq!(
                original.annual_average_establishments,
                imputed.establishments
            );
            assert_eq!(original.annual_payroll_usd, None);
        }
    }
    assert!(suppressed_groups > 0);
}
