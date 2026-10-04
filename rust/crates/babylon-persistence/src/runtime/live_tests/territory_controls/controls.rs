//! Child of `runtime::live_tests`; never commit synthetic projection markers.
use super::{validated_base_config, validated_template_name, TestDatabase};
use crate::identity::CampaignId;
use crate::stored_tick::{CapturedMaterialRows, StoredTickReadSource};
use crate::territory_storage::{insert, seed};
use postgres::{Config, GenericClient, NoTls, Transaction};
use uuid::Uuid;
include!("values.rs");

fn disposable_config(label: &str) -> (TestDatabase, Config) {
    let base = validated_base_config();
    let database = TestDatabase::create_from_template(&base, &validated_template_name(), label);
    let config = database.config(&base);
    (database, config)
}

fn foundation(config: &Config, suffix: u128) -> CampaignId {
    let campaign = CampaignId::from_uuid(Uuid::from_u128(
        (u128::from(std::process::id()) << 64) | suffix,
    ));
    let foundation = crate::michigan_content::MichiganContentPreset::new_campaign(
        crate::michigan_material::MichiganDeliveryPreset::Standard,
    )
    .create_foundation(&crate::test_support::catalog())
    .unwrap();
    let runtime =
        crate::material_runtime::DurableMaterialRuntime::create(config, campaign, foundation)
            .unwrap();
    assert_eq!(runtime.session().completed_tick(), 0);
    campaign
}

fn marker_components(tx: &mut Transaction<'_>, campaign: CampaignId, tick: i64) {
    // Only SQL relational controls; values are deliberately not a canonical material tick.
    // No commit and no SET CONSTRAINTS ALL IMMEDIATE: target territory guard only.
    tx.execute("INSERT INTO babylon_state.material_tick_v3(campaign_id,resolve_tick,identity_bytes,register_storage_bytes,receipt_storage_bytes,lookup_delta_bytes) VALUES($1,$2,$3,$3,$3,$3)", &[campaign.as_uuid(),&tick,&&[1_u8;32][..]]).unwrap();
    tx.execute(
        "INSERT INTO babylon_state.graph_node_manifest_v1 VALUES($1,$2,0,0,0,0)",
        &[campaign.as_uuid(), &tick],
    )
    .unwrap();
    tx.execute(
        "INSERT INTO babylon_state.event_manifest_v1 VALUES($1,$2,0,0,0,0)",
        &[campaign.as_uuid(), &tick],
    )
    .unwrap();
    tx.execute("INSERT INTO babylon_state.world_register_v1(campaign_id,resolve_tick,register_name,value_tag,int_value) VALUES($1,$2,'world/completed-tick',1,$2)", &[campaign.as_uuid(),&tick]).unwrap();
}

fn marker(tx: &mut Transaction<'_>, campaign: CampaignId, tick: i64) {
    marker_components(tx, campaign, tick);
    tx.execute(
        "INSERT INTO babylon_state.tick_commit VALUES($1,$2,3,$3,$3)",
        &[campaign.as_uuid(), &tick, &&[1_u8; 32][..]],
    )
    .unwrap();
}

fn definition_count(client: &mut impl GenericClient, campaign: CampaignId) -> i64 {
    client
        .query_one(
            "SELECT count(*) FROM babylon_state.territory_definition_v1 WHERE campaign_id=$1",
            &[campaign.as_uuid()],
        )
        .unwrap()
        .try_get(0)
        .unwrap()
}

fn canonical_rows(
    tx: &mut Transaction<'_>,
    source: StoredTickReadSource,
    campaign: CampaignId,
    tick: i64,
) -> Vec<Vec<u8>> {
    CapturedMaterialRows::capture(tx, source, campaign, tick)
        .unwrap()
        .admit()
        .unwrap()
        .territories()
        .rows()
        .iter()
        .map(|row| row.canonical_bytes().to_vec())
        .collect()
}

#[test]
#[ignore = "requires task-owned disposable PostgreSQL current schema"]
fn live_territory_definitions_reuse_exact_fields_and_preserve_history() {
    let (database, config) = disposable_config("territoryexact");
    let campaign = foundation(&config, 0x40_7e11);
    let mut client = config.connect(NoTls).unwrap();
    let original = rows(false);
    let expected: Vec<_> = original
        .iter()
        .map(|r| r.canonical_bytes().to_vec())
        .collect();
    let changed = rows(true);
    let changed_expected: Vec<_> = changed
        .iter()
        .map(|r| r.canonical_bytes().to_vec())
        .collect();
    assert_ne!(
        expected, changed_expected,
        "a changed canonical value must not alias"
    );
    let before = definition_count(&mut client, campaign);
    let mut tx = client.transaction().unwrap();
    seed(&mut tx, campaign, &original).unwrap();
    assert_eq!(definition_count(&mut tx, campaign), before + 2);
    // The existing BSL canonical encoder identifies both signs of real zero.
    // Verify that equivalence without changing its governed numeric semantics.
    let mut equivalent = rows(false);
    let fields = equivalent[1]
        .ordered_fields()
        .iter()
        .map(|(name, value)| {
            (
                name.clone(),
                if name == "05-real" {
                    StableBslValue::RealBits(0.0_f64.to_bits())
                } else {
                    value.clone()
                },
            )
        })
        .collect();
    equivalent[1] =
        TerritoryStateRow::try_new(equivalent[1].territory_id().clone(), fields).unwrap();
    assert_eq!(
        original[1].canonical_bytes(),
        equivalent[1].canonical_bytes()
    );
    let signed_zero: i64 = tx.query_one(
        "SELECT f.real_bits FROM babylon_state.territory_definition_field_v1 f JOIN babylon_state.territory_definition_v1 d USING(campaign_id,definition_id) WHERE d.campaign_id=$1 AND d.canonical_sha256=$2 AND f.field_name='05-real'",
        &[campaign.as_uuid(), &&babylon_kernel::content_digest::sha256_of(original[1].canonical_bytes())[..]],
    ).unwrap().get(0);
    assert_eq!(
        signed_zero,
        i64::from_be_bytes((-0.0_f64).to_bits().to_be_bytes())
    );
    for (tick, fields) in [(1_i64, &original), (2, &equivalent)] {
        insert(&mut tx, campaign, tick, fields).unwrap();
        marker(&mut tx, campaign, tick);
        assert_eq!(
            definition_count(&mut tx, campaign),
            before + 2,
            "unchanged definition reused at tick {tick}"
        );
    }
    insert(&mut tx, campaign, 3, &changed).unwrap();
    marker(&mut tx, campaign, 3);
    assert_eq!(
        definition_count(&mut tx, campaign),
        before + 3,
        "only changed typed row creates definition; empty row reused"
    );
    for (tick, expected) in [(1, &expected), (2, &expected), (3, &changed_expected)] {
        assert_eq!(
            &canonical_rows(&mut tx, StoredTickReadSource::Runtime, campaign, tick),
            expected
        );
        assert_eq!(
            &canonical_rows(&mut tx, StoredTickReadSource::FullObserver, campaign, tick),
            expected
        );
    }
    insert(&mut tx, campaign, 4, &[]).unwrap();
    marker(&mut tx, campaign, 4);
    assert!(canonical_rows(&mut tx, StoredTickReadSource::Runtime, campaign, 4).is_empty());
    assert!(canonical_rows(&mut tx, StoredTickReadSource::FullObserver, campaign, 4).is_empty());
    assert_eq!(tx.query_one("SELECT territory_count FROM babylon_state.territory_tick_manifest_v1 WHERE campaign_id=$1 AND resolve_tick=4", &[campaign.as_uuid()]).unwrap().try_get::<_,i64>(0).unwrap(), 0);
    tx.batch_execute("SET CONSTRAINTS babylon_state.territory_definition_complete_v1 IMMEDIATE")
        .unwrap();
    assert_header_corruption_refused(&mut tx, campaign, &original, &changed);
    tx.rollback().unwrap();
    assert_eq!(definition_count(&mut client, campaign), before);
    assert_eq!(
        client
            .query_one(
                "SELECT count(*) FROM babylon_state.tick_commit WHERE campaign_id=$1",
                &[campaign.as_uuid()]
            )
            .unwrap()
            .try_get::<_, i64>(0)
            .unwrap(),
        0
    );
    drop(client);
    database.cleanup();
}

include!("faults.rs");

include!("header_controls.rs");
