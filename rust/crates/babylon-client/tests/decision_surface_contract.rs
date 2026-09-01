//! PER-24: the shipped Bevy viewer must enumerate every visible surface and
//! keep administrative exemptions outside every gameplay gate.

use babylon_client::decision_surface::{
    contract_for, DecisionSurfaceContract, DecisionSurfaceRole, DeclaredSurface, SurfaceId,
    SHIPPED_SURFACE_MANIFEST,
};
use bevy::asset::AssetPlugin;
use bevy::image::ImagePlugin;
use bevy::prelude::*;
use bevy::render::texture::TexturePlugin;
use std::collections::HashSet;

fn shipped_app() -> App {
    let mut app = App::new();
    app.add_plugins((
        MinimalPlugins,
        AssetPlugin::default(),
        ImagePlugin::default(),
        TexturePlugin,
    ));
    app.add_plugins((
        babylon_client::visual_assets::VisualAssetsPlugin,
        babylon_client::visual_assets::VisualPresentationPlugin,
    ));
    app.add_plugins(babylon_client::map::MapPlugin);
    app.add_plugins(babylon_client::loop_ui::TickLoopPlugin);
    app.insert_resource(babylon_client::story::SelectedStory(
        babylon_client::story::counties(),
    ));
    app.finish();
    app.update(); // Startup.
    app.world_mut()
        .resource_mut::<babylon_client::map::SelectedCounty>()
        .0 = Some(0);
    app.update(); // Exercise the selection-outline spawn path too.
    app
}

#[test]
fn manifest_is_unique_exhaustive_and_valid() {
    let ids: HashSet<_> = SHIPPED_SURFACE_MANIFEST
        .iter()
        .map(|contract| contract.id)
        .collect();

    assert_eq!(
        ids.len(),
        SHIPPED_SURFACE_MANIFEST.len(),
        "a shipped surface may have exactly one authoritative contract"
    );
    assert_eq!(
        ids,
        SurfaceId::ALL.into_iter().collect(),
        "every shipped surface id must have one manifest row"
    );

    for contract in SHIPPED_SURFACE_MANIFEST {
        contract
            .validate()
            .unwrap_or_else(|error| panic!("{} has an invalid contract: {error}", contract.id));
        assert_eq!(
            contract_for(contract.id),
            contract,
            "manifest lookup must resolve the authoritative row"
        );
    }
}

#[test]
fn gameplay_contract_requires_every_decision_field() {
    const PRESENT: &[&str] = &["declared"];
    let complete = DecisionSurfaceContract {
        id: SurfaceId::CountyMap,
        role: DecisionSurfaceRole::Gameplay,
        decision_question: Some("What should I do here next week?"),
        visible_signals: PRESENT,
        visible_uncertainty: PRESENT,
        fog_requirements: PRESENT,
        actions: PRESENT,
        expected_receipts: PRESENT,
        archive_subjects: PRESENT,
        admin_debug_exempt: false,
    };
    assert!(complete.validate().is_ok());
    assert!(complete.satisfies_gameplay_gate());

    let omissions = [
        DecisionSurfaceContract {
            decision_question: None,
            ..complete
        },
        DecisionSurfaceContract {
            visible_signals: &[],
            ..complete
        },
        DecisionSurfaceContract {
            visible_uncertainty: &[],
            ..complete
        },
        DecisionSurfaceContract {
            fog_requirements: &[],
            ..complete
        },
        DecisionSurfaceContract {
            actions: &[],
            ..complete
        },
        DecisionSurfaceContract {
            expected_receipts: &[],
            ..complete
        },
        DecisionSurfaceContract {
            archive_subjects: &[],
            ..complete
        },
    ];

    for omitted in omissions {
        assert!(omitted.validate().is_err());
        assert!(!omitted.satisfies_gameplay_gate());
    }
}

#[test]
fn admin_exemptions_never_satisfy_gameplay_gates() {
    const PRESENT: &[&str] = &["declared"];
    let exempt_gameplay = DecisionSurfaceContract {
        id: SurfaceId::CountyMap,
        role: DecisionSurfaceRole::Gameplay,
        decision_question: Some("Looks complete, but is exempt"),
        visible_signals: PRESENT,
        visible_uncertainty: PRESENT,
        fog_requirements: PRESENT,
        actions: PRESENT,
        expected_receipts: PRESENT,
        archive_subjects: PRESENT,
        admin_debug_exempt: true,
    };
    assert!(exempt_gameplay.validate().is_err());
    assert!(!exempt_gameplay.satisfies_gameplay_gate());

    let disguised_admin = DecisionSurfaceContract {
        id: SurfaceId::CountyMap,
        role: DecisionSurfaceRole::AdminDebug,
        decision_question: Some("Looks complete, but is administrative"),
        visible_signals: PRESENT,
        visible_uncertainty: PRESENT,
        fog_requirements: PRESENT,
        actions: PRESENT,
        expected_receipts: PRESENT,
        archive_subjects: PRESENT,
        admin_debug_exempt: true,
    };

    assert!(disguised_admin.validate().is_ok());
    assert!(!disguised_admin.satisfies_gameplay_gate());
    for contract in SHIPPED_SURFACE_MANIFEST {
        if contract.admin_debug_exempt {
            assert!(!contract.satisfies_gameplay_gate(), "{}", contract.id);
        }
    }
}

#[test]
fn every_shipped_visual_entity_declares_a_manifest_surface() {
    let mut app = shipped_app();
    let world = app.world_mut();

    let declared_ids: HashSet<_> = world
        .query::<&DeclaredSurface>()
        .iter(world)
        .map(|declared| declared.id)
        .collect();
    assert_eq!(
        declared_ids,
        SurfaceId::ALL.into_iter().collect(),
        "the production plugin composition must instantiate every manifest surface"
    );

    let mut text_query = world.query::<(Entity, &Text, Option<&DeclaredSurface>)>();
    for (entity, _, declared) in text_query.iter(world) {
        let declared = declared.unwrap_or_else(|| {
            panic!("shipped Text entity {entity:?} has no DecisionSurfaceContract declaration")
        });
        assert!(contract_for(declared.id).validate().is_ok());
    }

    let mut image_query = world.query::<(Entity, &ImageNode, Option<&DeclaredSurface>)>();
    for (entity, _, declared) in image_query.iter(world) {
        let declared = declared.unwrap_or_else(|| {
            panic!("shipped ImageNode entity {entity:?} has no DecisionSurfaceContract declaration")
        });
        assert!(contract_for(declared.id).validate().is_ok());
    }

    let mut map_query = world.query::<(Entity, &Mesh2d, Option<&DeclaredSurface>)>();
    for (entity, _, declared) in map_query.iter(world) {
        let declared = declared.unwrap_or_else(|| {
            panic!(
                "shipped county-map entity {entity:?} has no DecisionSurfaceContract declaration"
            )
        });
        assert_eq!(declared.id, SurfaceId::CountyMap);
    }
}

#[test]
fn current_client_cannot_claim_a_gameplay_gate() {
    assert!(
        SHIPPED_SURFACE_MANIFEST
            .iter()
            .all(|contract| !contract.satisfies_gameplay_gate()),
        "the current Bevy client is an administrative viewer with no player action"
    );
}
