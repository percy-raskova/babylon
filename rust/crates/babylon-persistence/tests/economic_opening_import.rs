//! Michigan controls enter the same initialization shape as national campaigns.
use babylon_kernel::currency::Currency;
use babylon_persistence::economic_catalog;
use babylon_persistence::economic_catalog::CatalogAccounting;
use babylon_persistence::michigan_material::{MichiganDeliveryPreset, MichiganMaterialCatalog};

#[test]
fn control_import_preserves_exact_goods_orders_and_staffing() {
    let text = include_str!("../../../../content/scenarios/michigan/defines.toml");
    for preset in [
        MichiganDeliveryPreset::Standard,
        MichiganDeliveryPreset::Delayed,
        MichiganDeliveryPreset::SharedFreightAmple,
        MichiganDeliveryPreset::SharedFreightConstrained,
    ] {
        let catalog = MichiganMaterialCatalog::from_defines_toml(text)
            .expect("the authored input admits the derived value")
            .with_preset(preset)
            .expect("the fixture builder accepts the authored options");
        let opening = economic_catalog::import_michigan_opening(&catalog)
            .expect("the fixture call `import_michigan_opening` succeeds for the authored inputs");
        assert_eq!(opening.accounting, CatalogAccounting::PhysicalControl);
        assert!(opening.households.is_empty());
        assert!(opening.employment.is_empty());
        let compiled = opening.compile().expect("the authored scenario compiles");
        assert_eq!(
            compiled.catalog.process_outputs.len(),
            catalog.processes().len()
        );
        assert_eq!(
            compiled.catalog.supplier_routes.len(),
            catalog.routes().len()
        );
        assert_eq!(compiled.state.orders.len(), catalog.routes().len());
        assert_eq!(
            compiled.staffing.bindings().len(),
            catalog.staffing().pools.len()
        );
        let mut mixed = opening.clone();
        mixed.sites[0].opening_cash = Currency::from_micro_units(1);
        assert!(
            mixed.compile().is_err(),
            "physical controls cannot hide money"
        );
        let mut forged = opening;
        forged.staffing[0].members[0].employed += 1;
        assert!(
            forged.compile().is_err(),
            "the single member population principal must reconcile"
        );
    }
}

#[test]
fn source_only_control_capture_round_trips_without_a_derived_material_blob() {
    use babylon_persistence::economic_catalog::{CapturedEconomicCatalog, SourceArtifactKind};
    use babylon_persistence::{FoundationContentBundle, FoundationContentKind};
    let control = MichiganMaterialCatalog::from_defines_toml(include_str!(
        "../../../../content/scenarios/michigan/defines.toml"
    ))
    .expect("the authored input admits the derived value");
    let captured = CapturedEconomicCatalog::from_michigan(&control)
        .expect("the Michigan fixture content loads");
    let detail = captured
        .source(SourceArtifactKind::MichiganSpatialProducts)
        .expect("the fixture call `source` succeeds for the authored inputs");
    assert_eq!(detail.len(), 2_325_740);
    assert!(captured
        .source(SourceArtifactKind::MichiganDynamicHexes)
        .is_some());
    let raw = captured.canonical_bytes().to_vec();
    let digest = captured.digest();
    let reopened = CapturedEconomicCatalog::decode(&raw, digest)
        .expect("the committed canonical bytes decode");
    assert_eq!(reopened.opening(), captured.opening());
    let babylon_persistence::economic_catalog::EconomicSourceView::MichiganControl {
        catalog, ..
    } = reopened.view().sources
    else {
        panic!("captured Michigan control source required");
    };
    let recaptured = CapturedEconomicCatalog::from_michigan(catalog)
        .expect("the Michigan fixture content loads");
    assert_eq!(recaptured.canonical_bytes(), raw);

    assert_eq!(
        reopened.source(SourceArtifactKind::MichiganDefines),
        Some(include_bytes!("../../../../content/scenarios/michigan/defines.toml").as_slice())
    );
    let bundle = FoundationContentBundle::from_economic_catalog(reopened)
        .expect("the authored input admits the derived value");
    assert_eq!(bundle.kind(), FoundationContentKind::EconomicCatalog);
    assert_eq!(bundle.reference_digest().as_bytes(), &digest);
    assert_eq!(
        FoundationContentBundle::decode(bundle.canonical_bytes())
            .expect("the committed canonical bytes decode"),
        bundle
    );
    let mut unknown = raw;
    unknown[0] ^= 1;
    assert!(CapturedEconomicCatalog::decode(&unknown, digest).is_err());
}

#[test]
fn captured_control_restarts_and_advances_through_the_same_three_period_circuit() {
    use babylon_bsl::structural_verbs::CollectingSink;
    use babylon_kernel::replay::{ReplaySeed, ReplaySessionId};
    use babylon_persistence::economic_catalog::CapturedEconomicCatalog;
    use babylon_persistence::material_runtime::MaterialRuntimeFoundation;

    use babylon_practice_contract::OrderedPracticeActionBatch;
    use babylon_tick::replay_session::ReplayCommitDisposition;
    let control = MichiganMaterialCatalog::from_defines_toml(include_str!(
        "../../../../content/scenarios/michigan/defines.toml"
    ))
    .expect("the authored input admits the derived value");
    let original = CapturedEconomicCatalog::from_michigan(&control)
        .expect("the Michigan fixture content loads")
        .create_foundation(
            ReplaySessionId::try_from("captured-control")
                .expect("the fixture value fits the target range"),
            ReplaySeed::new(319),
        )
        .expect("the authored catalog builds the foundation");
    let restored = MaterialRuntimeFoundation::decode(
        &original
            .export_canonical_bytes()
            .expect("the content exports its canonical bytes"),
        original.digest(),
    )
    .expect("the committed canonical bytes decode");
    assert_eq!(
        original
            .export_canonical_bytes()
            .expect("the content exports its canonical bytes"),
        restored
            .export_canonical_bytes()
            .expect("the content exports its canonical bytes")
    );
    let mut direct = original
        .into_session()
        .expect("the fixture opens a session");
    let mut restart = restored
        .into_session()
        .expect("the fixture opens a session");
    for period in 1..=3 {
        let actions = OrderedPracticeActionBatch::empty(
            direct.graph_session().session_identity().clone(),
            period,
        )
        .expect("the empty authored batch constructs");
        let left = direct
            .prepare_advance(&actions)
            .expect("the session prepares the authored advance");
        let right = restart
            .prepare_advance(&actions)
            .expect("the session prepares the authored advance");
        assert_eq!(left.identity(), right.identity());
        assert_eq!(
            left.material().register().canonical_bytes(),
            right.material().register().canonical_bytes()
        );
        assert_eq!(
            left.material().receipt_bytes(),
            right.material().receipt_bytes()
        );
        direct
            .commit_prepared_and_publish(&mut CollectingSink::default(), left, |_, _| {
                Ok::<_, ()>(ReplayCommitDisposition::Committed)
            })
            .expect("the prepared period commits");
        restart
            .commit_prepared_and_publish(&mut CollectingSink::default(), right, |_, _| {
                Ok::<_, ()>(ReplayCommitDisposition::Committed)
            })
            .expect("the prepared period commits");
    }
}
