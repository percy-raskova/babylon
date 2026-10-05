use super::*;
use crate::economic_content::{admit_economic_content, EconomicContentError};
fn control(admission: &EconomicContentAdmission) -> &MichiganMaterialCatalog {
    match admission.view().sources {
        crate::economic_catalog::EconomicSourceView::MichiganControl { catalog, .. } => catalog,
        crate::economic_catalog::EconomicSourceView::National { .. } => {
            panic!("Michigan control required")
        }
    }
}
use babylon_kernel::clock::CampaignDuration;
fn finite(final_period: u64) -> CampaignDuration {
    CampaignDuration::Finite { final_period }
}

const REGIONAL_PRESETS: [MichiganContentPreset; 4] = [
    MichiganContentPreset::FourWeekStandard,
    MichiganContentPreset::FourWeekDelayed,
    MichiganContentPreset::SharedFreightAmple,
    MichiganContentPreset::SharedFreightConstrained,
];

#[test]
fn current_staffed_foundation_keeps_observed_cohorts_separate_from_five_designed_pools() {
    for preset in REGIONAL_PRESETS {
        let foundation = preset
            .create_foundation(&crate::test_support::catalog())
            .unwrap();
        let expected = preset.admitted(&crate::test_support::catalog()).unwrap();
        assert_eq!(
            foundation.export_canonical_bytes().unwrap(),
            expected.export_canonical_bytes().unwrap()
        );
        assert_eq!(foundation.initial_register(), expected.initial_register());
        assert_eq!(expected.duration(), finite(16));
        let source = std::str::from_utf8(
            foundation
                .graph_foundation()
                .content_bundle()
                .scenario_source_bytes(),
        )
        .unwrap();
        assert_eq!(source.matches("(node business-").count(), 1_603);
        assert_eq!(source.matches("(hyperedge sector-").count(), 19);
        assert_eq!(source.matches("(node workforce-").count(), 5);
        assert_eq!(source.matches("(deffield social-class/").count(), 2);
        assert_eq!(source.matches("(node workplace-").count(), 5);
        assert_eq!(source.matches("(deffield business/").count(), 1);
        assert!(!crate::michigan_cohorts::michigan_cohorts()
            .unwrap()
            .scenario_source()
            .contains("SOCIAL_CLASS"));
        let composition = foundation.labor();
        assert_eq!(composition.bindings().len(), 5);
        for binding in composition.bindings() {
            assert_eq!(binding.members().len(), 1);
            assert_ne!(binding.subject(), binding.members()[0].subject());
            assert_eq!(
                binding.pool().labor_force(),
                binding.members()[0].member().labor_force()
            );
        }
        assert_eq!(foundation.initial_register().state().labor.len(), 5);
        assert!(foundation
            .initial_register()
            .state()
            .labor
            .iter()
            .all(|row| row.period == 1));
        assert_eq!(foundation.initial_register().state().capacities.len(), 80);
        assert_eq!(
            MichiganContentPreset::new_campaign(preset.delivery()),
            preset
        );
    }
}

#[test]
fn unsupported_michigan_saves_are_refused_without_a_predecessor_factory() {
    for version in 1..=6 {
        for delivery in [
            "standard",
            "delayed",
            "shared-freight-ample",
            "shared-freight-constrained",
        ] {
            let id = format!("michigan-material-{delivery}-v{version}");
            assert_eq!(MichiganContentPreset::from_id(&id), None);
            assert!(matches!(
                admit_economic_content(&id, finite(16), &[0; 32], &[0; 32], 0, &[]),
                Err(EconomicContentError::UnknownPreset)
            ));
        }
    }
}

#[test]
fn admission_refuses_mixed_headers_graphs_and_unadmitted_versions() {
    for preset in REGIONAL_PRESETS {
        let expected = preset.admitted(&crate::test_support::catalog()).unwrap();
        let reopened = admit_economic_content(
            preset.id(),
            finite(16),
            &expected.content_digest(),
            &expected.digest(),
            16,
            &expected.export_canonical_bytes().unwrap(),
        )
        .unwrap();
        assert_eq!(
            reopened.export_canonical_bytes().unwrap(),
            expected.export_canonical_bytes().unwrap()
        );
        for tick in [0, 16] {
            assert!(expected
                .validate_header(
                    finite(16),
                    &expected.content_digest(),
                    &expected.digest(),
                    tick
                )
                .is_ok());
        }
        for horizon in [0, 15, 17, u64::MAX] {
            assert_eq!(
                expected.validate_header(
                    finite(horizon),
                    &expected.content_digest(),
                    &expected.digest(),
                    0
                ),
                Err(EconomicContentError::Identity)
            );
        }
        assert_eq!(
            expected.validate_header(
                finite(16),
                &expected.content_digest(),
                &expected.digest(),
                17
            ),
            Err(EconomicContentError::Identity)
        );
        for other in REGIONAL_PRESETS {
            if other == preset {
                continue;
            }
            let mixed = other.admitted(&crate::test_support::catalog()).unwrap();
            assert!(admit_economic_content(
                preset.id(),
                finite(16),
                &mixed.content_digest(),
                &mixed.digest(),
                0,
                &expected.export_canonical_bytes().unwrap()
            )
            .is_err());
            if expected.graph_digest != mixed.graph_digest {
                assert!(expected
                    .validate_graph(&mixed.graph_digest, &expected.source_digest)
                    .is_err());
            }
            if expected.source_digest != mixed.source_digest {
                assert!(expected
                    .validate_graph(&expected.graph_digest, &mixed.source_digest)
                    .is_err());
            }
        }
        assert!(admit_economic_content(
            "michigan-material-standard-v8",
            finite(16),
            &expected.content_digest(),
            &expected.digest(),
            0,
            &expected.export_canonical_bytes().unwrap()
        )
        .is_err());
        assert!(admit_economic_content(
            preset.id(),
            finite(16),
            &expected.content_digest()[..31],
            &expected.digest(),
            0,
            &expected.export_canonical_bytes().unwrap()
        )
        .is_err());
        assert!(admit_economic_content(
            preset.id(),
            finite(16),
            &expected.content_digest(),
            &expected.digest()[..31],
            0,
            &expected.export_canonical_bytes().unwrap()
        )
        .is_err());
    }
}

#[test]
fn edited_parameters_change_new_foundations_but_stored_campaign_keeps_its_own_values() {
    let catalog = crate::test_support::catalog();
    let preset = MichiganContentPreset::FourWeekStandard;
    let original = preset.admitted(&catalog).unwrap();
    let source = include_str!(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../../../content/scenarios/michigan/defines.toml"
    ));
    let edited = MichiganMaterialCatalog::from_defines_toml(
        &source
            .replace(
                "WORK_HOURS_PER_PERSON_WEEK = 40",
                "WORK_HOURS_PER_PERSON_WEEK = 45",
            )
            .replace("OPENING_INPUT_UNITS = 600", "OPENING_INPUT_UNITS = 700")
            .replace(
                "DURATION = { kind = \"continuous\" }",
                "DURATION = { kind = \"finite\", final_period = 8 }",
            ),
    )
    .unwrap();
    let next = preset.admitted(&edited).unwrap();
    assert_ne!(original.digest(), next.digest());
    assert_eq!(next.duration(), finite(8));
    assert!(next
        .validate_header(finite(8), &next.content_digest(), &next.digest(), 8)
        .is_ok());
    assert!(next
        .validate_header(finite(8), &next.content_digest(), &next.digest(), 9)
        .is_err());
    assert_eq!(edited.staffing().hours_per_worker_period, 180);
    assert_eq!(
        next.initial_register()
            .state()
            .labor
            .iter()
            .find(|row| {
                row.site_id
                    == edited
                        .processes()
                        .iter()
                        .find(|process| process.key == "sheet-rolling")
                        .unwrap()
                        .site_id()
            })
            .unwrap()
            .available,
        3600
    );
    let reopened = admit_economic_content(
        preset.id(),
        finite(16),
        &original.content_digest(),
        &original.digest(),
        0,
        &original.export_canonical_bytes().unwrap(),
    )
    .unwrap();
    assert_eq!(control(&reopened).staffing().hours_per_worker_period, 160);
    assert_eq!(reopened.view().opening, original.view().opening);
    assert_eq!(reopened.initial_register(), original.initial_register());
    assert!(admit_economic_content(
        preset.id(),
        finite(16),
        &next.content_digest(),
        &next.digest(),
        0,
        &original.export_canonical_bytes().unwrap()
    )
    .is_err());
    let mut corrupted = original.export_canonical_bytes().unwrap();
    let end = corrupted.len() - 1;
    corrupted[end] ^= 1;
    assert!(admit_economic_content(
        preset.id(),
        finite(16),
        &original.content_digest(),
        &original.digest(),
        0,
        &corrupted
    )
    .is_err());
    for length in [0, 32, original.canonical_len().unwrap() - 1] {
        assert!(admit_economic_content(
            preset.id(),
            finite(16),
            &original.content_digest(),
            &original.digest(),
            0,
            &original.export_canonical_bytes().unwrap()[..length]
        )
        .is_err());
    }
}

#[test]
fn stored_shared_freight_capacities_reconstruct_without_current_default_substitution() {
    let source = include_str!(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../../../content/scenarios/michigan/defines.toml"
    ));
    let defaults = crate::test_support::catalog();
    let authored = MichiganMaterialCatalog::from_defines_toml(
        &source
            .replace(
                "DURATION = { kind = \"continuous\" }",
                "DURATION = { kind = \"finite\", final_period = 16 }",
            )
            .replace("AMPLE_UNITS_PER_WEEK = 200", "AMPLE_UNITS_PER_WEEK = 201")
            .replace(
                "CONSTRAINED_UNITS_PER_WEEK = 40",
                "CONSTRAINED_UNITS_PER_WEEK = 41",
            ),
    )
    .unwrap();
    for (preset, capacity) in [
        (MichiganContentPreset::SharedFreightAmple, 804),
        (MichiganContentPreset::SharedFreightConstrained, 164),
    ] {
        let original = preset.admitted(&authored).unwrap();
        let default_campaign = preset.admitted(&defaults).unwrap();
        assert_ne!(original.digest(), default_campaign.digest());
        let reopened = admit_economic_content(
            preset.id(),
            finite(16),
            &original.content_digest(),
            &original.digest(),
            0,
            &original.export_canonical_bytes().unwrap(),
        )
        .unwrap();
        assert_eq!(reopened.view().opening, original.view().opening);
        assert_ne!(
            reopened.view().source_digest,
            default_campaign.view().source_digest
        );
        assert_eq!(reopened.initial_register(), original.initial_register());
        assert_eq!(
            reopened.export_canonical_bytes().unwrap(),
            original.export_canonical_bytes().unwrap()
        );
        let sheet = control(&reopened)
            .routes()
            .iter()
            .find(|route| route.key == "sheet-transfer")
            .unwrap();
        let crate::michigan_material::MichiganMaterialPath::Routed { capacity_keys, .. } =
            &sheet.path
        else {
            panic!("regional transfer requires freight");
        };
        assert_eq!(capacity_keys.len(), 1);
        let shared = control(&reopened)
            .corridors()
            .iter()
            .find(|row| row.key == capacity_keys[0])
            .unwrap();
        assert_eq!(shared.capacity_grams_per_period, capacity * 1000);
        let capacities: Vec<_> = reopened
            .initial_register()
            .state()
            .corridor_capacities
            .iter()
            .filter(|row| row.corridor_id == shared.id())
            .collect();
        assert_eq!(capacities.len(), 16);
        assert!(capacities
            .iter()
            .all(|row| row.available_grams == capacity * 1000));
        assert!(admit_economic_content(
            preset.id(),
            finite(16),
            &default_campaign.content_digest(),
            &default_campaign.digest(),
            0,
            &original.export_canonical_bytes().unwrap(),
        )
        .is_err());
    }
}

#[test]
fn statewide_presets_refuse_an_unqualified_regional_catalog() {
    let catalog = crate::test_support::catalog();
    for preset in MICHIGAN_CONTENT_PRESETS
        .into_iter()
        .filter(|preset| !REGIONAL_PRESETS.contains(preset))
    {
        assert!(preset.create_foundation(&catalog).is_err());
        assert!(preset.admitted(&catalog).is_err());
    }
}

#[test]
fn continuous_campaign_admits_explicit_duration_without_a_numeric_stop() {
    let source = include_str!("../../../../../content/scenarios/michigan/defines.toml");
    let catalog = MichiganMaterialCatalog::from_defines_toml(source)
        .expect("explicit continuous duration must be admitted independently of a finite experiment horizon");
    assert_eq!(catalog.duration(), CampaignDuration::Continuous);
    let foundation = MichiganContentPreset::FourWeekStandard
        .create_foundation(&catalog)
        .unwrap();
    assert!(matches!(
        foundation.initial_register().state().capacity_supply,
        babylon_material_circuit::CapacitySupply::Rolling(_)
    ));
    assert!(foundation
        .initial_register()
        .state()
        .capacities
        .iter()
        .all(|row| row.period == 1));
    let expected = MichiganContentPreset::FourWeekStandard
        .admitted(&catalog)
        .unwrap();
    assert!(expected
        .validate_header(
            CampaignDuration::Continuous,
            &expected.content_digest(),
            &expected.digest(),
            80
        )
        .is_ok());
    assert!(expected
        .validate_header(
            finite(16),
            &expected.content_digest(),
            &expected.digest(),
            0
        )
        .is_err());
}
