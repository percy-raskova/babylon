//! Scope is exercised through the scene system with real committed atlas geometry.
use super::*;
use babylon_kernel::geography::{CountyGeoid, NationalCountyRoster};
use babylon_persistence::identity::CampaignId;
use babylon_persistence::observer_reader::{
    ObserverCountyEconomy, ObserverEconomySnapshot, ObserverVisibility,
};

fn atlas() -> CountyAtlas {
    CountyAtlas::parse(include_bytes!(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../../../assets/map/county_atlas.bin"
    )))
    .unwrap()
}
fn domestic_counties() -> Vec<String> {
    let atlas = atlas();
    let counties: Vec<_> = (0..atlas.len())
        .map(|i| atlas.county(i).unwrap().fips)
        .filter(|fips| !fips.starts_with("72"))
        .map(|fips| CountyGeoid::try_from(fips).unwrap())
        .collect();
    NationalCountyRoster::try_new(counties.clone()).unwrap();
    counties
        .into_iter()
        .map(|county| county.to_string())
        .collect()
}
fn observation(campaign: CampaignId, counties: Vec<String>) -> ObserverFrame {
    ObserverFrame(
        Some(ObserverEconomySnapshot {
            campaign_id: campaign.as_uuid().to_string(),
            resolve_tick: 0,
            foundation_digest: "f".repeat(64),
            tick_content_hash: None,
            nominal_world_hash: None,
            envelope_digest: None,
            visibility: ObserverVisibility::FullObserver,
            production: None,
            counties: counties
                .into_iter()
                .map(|county_geoid| ObserverCountyEconomy {
                    county_geoid,
                    annual_avg_estabs_count: None,
                    annual_avg_emplvl: None,
                    total_annual_wages: None,
                    annual_avg_wkly_wage: None,
                })
                .collect(),
        }),
        None,
    )
}
fn scene(counties: Vec<String>) -> App {
    let campaign = CampaignId::from_uuid(uuid::Uuid::nil());
    let mut session = ObserverSession::new(campaign);
    session.foundation_digest = Some("f".repeat(64));
    session.ready(0, None);
    let mut app = App::new();
    app.add_plugins((
        MinimalPlugins,
        bevy::asset::AssetPlugin::default(),
        crate::map::MapPlugin,
    ))
    .init_asset::<StandardMaterial>()
    .insert_resource(session)
    .insert_resource(observation(campaign, counties))
    .add_systems(
        Update,
        setup_map
            .after(crate::map::MapScopeSet)
            .before(ObserverSet::Paint),
    );
    app.update();
    app
}
fn slabs(app: &mut App) -> std::collections::BTreeMap<String, Entity> {
    let world = app.world_mut();
    world
        .query::<(Entity, &CountySlab)>()
        .iter(world)
        .map(|(entity, slab)| (slab.fips.clone(), entity))
        .collect()
}
#[test]
fn national_scene_uses_all_admitted_counties_without_dependency_substitution() {
    let counties = domestic_counties();
    let mut app = scene(counties.clone());
    let rendered = slabs(&mut app);
    assert_eq!(rendered.len(), 3144);
    assert_eq!(rendered.keys().cloned().collect::<Vec<_>>(), counties);
    assert!(rendered.contains_key("02013"));
    assert!(rendered.contains_key("15005"));
    assert!(!rendered.keys().any(|county| county.starts_with("72")));
}
#[test]
fn loading_same_campaign_preserves_meshes_but_switch_clears_stale_counties() {
    let counties = domestic_counties()
        .into_iter()
        .filter(|fips| fips.starts_with("26"))
        .collect();
    let mut app = scene(counties);
    let original = slabs(&mut app);
    assert_eq!(original.len(), 83);
    app.world_mut().resource_mut::<ObserverFrame>().0 = None;
    app.update();
    assert_eq!(slabs(&mut app), original);
    app.world_mut().resource_mut::<ObserverSession>().campaign =
        CampaignId::from_uuid(uuid::Uuid::from_u128(1));
    app.update();
    assert!(slabs(&mut app).is_empty());
}

#[test]
fn campaign_switch_installs_known_geography_and_preserves_admitted_wayne_selection() {
    let mut app = scene(vec!["26163".into()]);
    let wayne = app
        .world()
        .resource::<CountyAtlas>()
        .index_of_fips("26163")
        .unwrap();
    assert_eq!(app.world().resource::<SelectedCounty>().0, Some(wayne));
    app.world_mut().resource_mut::<HoveredCounty>().0 = Some(wayne);
    let campaign = CampaignId::from_uuid(uuid::Uuid::from_u128(2));
    {
        let mut session = app.world_mut().resource_mut::<ObserverSession>();
        session.campaign = campaign;
        session.perspective = crate::observer::Perspective::PlayerKnowledge;
    }
    let mut frame = observation(
        campaign,
        vec!["02013".into(), "15005".into(), "26163".into()],
    );
    frame.0.as_mut().unwrap().visibility = ObserverVisibility::KnownPreview;
    *app.world_mut().resource_mut::<ObserverFrame>() = frame;
    app.update();
    assert_eq!(
        slabs(&mut app).keys().cloned().collect::<Vec<_>>(),
        ["02013", "15005", "26163"]
    );
    assert_eq!(app.world().resource::<SelectedCounty>().0, Some(wayne));
    assert_eq!(app.world().resource::<HoveredCounty>().0, None);
    let world = app.world_mut();
    assert_eq!(
        world
            .query::<&Text>()
            .iter(world)
            .filter(|text| text.0.contains("relocated inset"))
            .count(),
        2
    );
}

#[test]
fn changed_geography_in_one_foundation_refuses_and_removes_the_old_scene() {
    let mut app = scene(vec!["26163".into()]);
    {
        let mut frame = app.world_mut().resource_mut::<ObserverFrame>();
        let counties = &mut frame.0.as_mut().unwrap().counties;
        let mut addition = counties[0].clone();
        addition.county_geoid = "26165".into();
        counties.push(addition);
    }
    app.update();
    assert_eq!(
        app.world().resource::<ObserverSession>().phase,
        crate::observer::SessionPhase::Failed
    );
    assert!(slabs(&mut app).is_empty());
    assert_eq!(app.world().resource::<SelectedCounty>().0, None);
    assert!(app
        .world()
        .resource::<ObserverSession>()
        .error
        .as_deref()
        .unwrap()
        .contains("ChangedGeography"));
    app.update();
    assert!(slabs(&mut app).is_empty());
}
