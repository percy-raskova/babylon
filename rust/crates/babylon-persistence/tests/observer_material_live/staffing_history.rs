//! Exact historical staffing and complete-envelope refusal in an owned clone.

use super::{
    advance_material_period, assert_known_material_absence, install_reader_role,
    provision_observer_role, CampaignId, Config, DisposableTarget, DurableMaterialRuntime,
    MichiganContentPreset, NoTls, ObserverEconomyError, ObserverEconomyReader, ObserverVisibility,
    Uuid,
};
use babylon_persistence::observer_reader::ObserverEconomySnapshot;
use babylon_persistence::observer_reader::{ProductionHistoryTarget, ProductionOutputPoint};
use postgres::{
    types::{FromSqlOwned, ToSql},
    Client,
};

struct Fixture {
    target: DisposableTarget,
    campaign: CampaignId,
    runtime: DurableMaterialRuntime,
    observer: ObserverEconomyReader,
    preview: ObserverEconomyReader,
    observer_config: Config,
    foundation_digest: [u8; 32],
}

impl Fixture {
    fn new() -> Self {
        let mut target = DisposableTarget::create();
        let campaign = CampaignId::from_uuid(Uuid::from_u128(41_101));
        let foundation = MichiganContentPreset::FourWeekDelayed
            .create_foundation(&crate::test_support::catalog())
            .unwrap();
        let foundation_digest = foundation.digest();
        let runtime = DurableMaterialRuntime::create(&target.writer, campaign, foundation).unwrap();
        install_reader_role(&target.writer).unwrap();
        provision_observer_role(&target.writer).unwrap();
        let observer_config = target.login("babylon_observer", "staffinghistory");
        let observer =
            ObserverEconomyReader::connect(&observer_config, ObserverVisibility::FullObserver)
                .unwrap();
        let preview = ObserverEconomyReader::connect(
            &target.login("babylon_reader", "staffingpreview"),
            ObserverVisibility::KnownPreview,
        )
        .unwrap();
        Self {
            target,
            campaign,
            runtime,
            observer,
            preview,
            observer_config,
            foundation_digest,
        }
    }

    fn read(&self, tick: u64) -> ObserverEconomySnapshot {
        self.observer.snapshot(self.campaign, tick).unwrap()
    }

    fn advance_to(&mut self, tick: u64) {
        while self.runtime.session().completed_tick() < tick {
            advance_material_period(&mut self.runtime);
        }
    }
}

fn history_targets(snapshot: &ObserverEconomySnapshot) -> Vec<ProductionHistoryTarget> {
    snapshot
        .production
        .as_ref()
        .unwrap()
        .sites
        .iter()
        .flat_map(|site| {
            site.processes
                .iter()
                .map(|process| ProductionHistoryTarget {
                    site_id: site.id.clone(),
                    process_id: process.id.clone(),
                    output_good_id: process.output_good_id.clone(),
                    output_unit_id: process.output_unit_id.clone(),
                })
        })
        .collect()
}

fn snapshot_point(
    snapshot: &ObserverEconomySnapshot,
    target: &ProductionHistoryTarget,
) -> ProductionOutputPoint {
    let process = snapshot
        .production
        .as_ref()
        .unwrap()
        .sites
        .iter()
        .find(|site| site.id == target.site_id)
        .unwrap()
        .processes
        .iter()
        .find(|process| {
            process.id == target.process_id
                && process.output_good_id == target.output_good_id
                && process.output_unit_id == target.output_unit_id
        })
        .unwrap();
    ProductionOutputPoint {
        period: snapshot.resolve_tick,
        planned: process
            .planned_batches
            .map(|batches| batches.checked_mul(process.output_per_batch).unwrap()),
        produced: process
            .produced_batches
            .map(|batches| batches.checked_mul(process.output_per_batch).unwrap()),
    }
}

#[test]
#[ignore = "requires the task-owned disposable PostgreSQL harness; independent clone ownership"]
fn production_history_matches_exact_snapshots_and_survives_reopen() {
    let mut fixture = Fixture::new();
    fixture.advance_to(4);
    let snapshots: Vec<_> = (0..=4).map(|tick| fixture.read(tick)).collect();
    let targets = history_targets(&snapshots[0]);
    assert!(!targets.is_empty());
    let mut held = Vec::new();
    for target in &targets {
        let expected: Vec<_> = snapshots
            .iter()
            .map(|snapshot| snapshot_point(snapshot, target))
            .collect();
        let actual = fixture
            .observer
            .production_history(fixture.campaign, 4, target)
            .unwrap();
        assert_eq!(actual, expected);
        assert_eq!(actual[0].planned, None);
        assert_eq!(actual[0].produced, None);
        held.push(actual);
    }
    assert!(held.iter().flatten().any(|point| point.produced == Some(0)));
    assert!(held
        .iter()
        .flatten()
        .any(|point| point.produced.is_some_and(|quantity| quantity > 0)));

    fixture.advance_to(6);
    fixture.runtime = DurableMaterialRuntime::open(
        &fixture.target.writer,
        fixture.campaign,
        fixture.foundation_digest,
    )
    .unwrap();
    let reader =
        ObserverEconomyReader::connect(&fixture.observer_config, ObserverVisibility::FullObserver)
            .unwrap();
    let tail = *fixture.runtime.tail().unwrap();
    let world = fixture.runtime.session().current_world_hash().unwrap();
    for (target, expected) in targets.iter().zip(held) {
        assert_eq!(
            reader
                .production_history(fixture.campaign, 4, target)
                .unwrap(),
            expected
        );
    }
    assert_eq!(fixture.runtime.tail(), Some(&tail));
    assert_eq!(
        fixture.runtime.session().current_world_hash().unwrap(),
        world
    );
    assert_eq!(
        reader.production_history(fixture.campaign, 7, &targets[0]),
        Err(ObserverEconomyError::TickAbsent)
    );
    assert_eq!(
        reader.production_history(
            CampaignId::from_uuid(Uuid::from_u128(41_102)),
            4,
            &targets[0]
        ),
        Err(ObserverEconomyError::CampaignAbsent)
    );
    for field in 0..4 {
        let mut wrong = targets[0].clone();
        let identity = match field {
            0 => &mut wrong.site_id,
            1 => &mut wrong.process_id,
            2 => &mut wrong.output_good_id,
            _ => &mut wrong.output_unit_id,
        };
        *identity = "0".repeat(64);
        assert_eq!(
            reader.production_history(fixture.campaign, 4, &wrong),
            Err(ObserverEconomyError::ProductionHistoryUnavailable)
        );
    }
}

#[test]
#[ignore = "requires the task-owned disposable PostgreSQL harness; independent clone ownership"]
fn production_history_preview_refuses_without_target_or_campaign_disclosure() {
    let mut fixture = Fixture::new();
    fixture.advance_to(2);
    let target = history_targets(&fixture.read(0)).remove(0);
    let absent = CampaignId::from_uuid(Uuid::from_u128(41_103));
    for campaign in [fixture.campaign, absent] {
        for tick in [0, 2, u64::MAX] {
            assert_eq!(
                fixture.preview.production_history(campaign, tick, &target),
                Err(ObserverEconomyError::ProductionHistoryUnavailable)
            );
        }
    }
    assert_known_material_absence(&mut fixture.preview.snapshot(fixture.campaign, 2).unwrap());
}

#[test]
#[ignore = "requires the task-owned disposable PostgreSQL harness; independent clone ownership"]
fn production_history_authenticates_corruption_before_the_displayed_suffix() {
    let mut fixture = Fixture::new();
    fixture.advance_to(16);
    let target = history_targets(&fixture.read(0)).remove(0);
    let healthy = fixture
        .observer
        .production_history(fixture.campaign, 16, &target)
        .unwrap();
    assert_eq!(healthy.len(), 13);
    assert_eq!(healthy.first().unwrap().period, 4);
    assert_eq!(healthy.last().unwrap().period, 16);
    assert_eq!(
        healthy.last().unwrap(),
        &snapshot_point(&fixture.read(16), &target)
    );
    let mut writer = fixture.target.writer.connect(NoTls).unwrap();
    for (relation, column, predicate) in [
        ("material_tick_v3", "register_storage_bytes", "true"),
        ("material_tick_v3", "receipt_storage_bytes", "true"),
        ("material_tick_v3", "lookup_delta_bytes", "true"),
        ("material_tick_v3", "identity_bytes", "true"),
        ("tick_commit", "envelope_digest", "true"),
        ("tick_action_batch_v1", "exact_action_batch_bytes", "true"),
        (
            "checkpoint_section_v1",
            "inline_section_bytes",
            "section_tag=2",
        ),
    ] {
        let row = writer.query_one(
            &format!("SELECT ctid::text, {column} FROM babylon_state.{relation} WHERE campaign_id=$1::uuid AND resolve_tick=1 AND {predicate} ORDER BY ctid LIMIT 1"),
            &[fixture.campaign.as_uuid()],
        ).unwrap();
        let location: String = row.get(0);
        let original: Vec<u8> = row.get(1);
        let update = format!("UPDATE babylon_state.{relation} SET {column}=$1 WHERE ctid=$2::text::tid RETURNING ctid::text");
        let location: String = writer
            .query_one(&update, &[&flipped(&original), &location])
            .unwrap()
            .get(0);
        let refusal = fixture
            .observer
            .production_history(fixture.campaign, 16, &target);
        assert_eq!(
            writer
                .query(&update, &[&original, &location])
                .unwrap()
                .len(),
            1
        );
        assert_eq!(
            refusal,
            Err(ObserverEconomyError::InvalidProjection),
            "{relation}.{column}"
        );
    }
    assert_eq!(
        fixture
            .observer
            .production_history(fixture.campaign, 16, &target)
            .unwrap(),
        healthy
    );
}

fn assert_foundation(fixture: &Fixture) {
    let snapshot = fixture.read(0);
    let production = snapshot.production.as_ref().unwrap();
    let catalog = crate::test_support::catalog();
    assert_eq!(production.staffing_accounts.len(), 5);
    let mut employed = Vec::new();
    for seed in &catalog.staffing().pools {
        let account = production
            .staffing_accounts
            .iter()
            .find(|account| account.subject.local_name == seed.workplace_local_name())
            .unwrap();
        assert_eq!(account.members.len(), 1);
        let member = &account.members[0];
        assert_eq!(member.subject.local_name, seed.local_name());
        assert_eq!(member.subject.scenario, account.subject.scenario);
        assert_eq!(member.employed, seed.employed);
        assert_eq!(member.reserve, seed.reserve);
        assert_eq!(member.labor_force, seed.employed + seed.reserve);
        assert_eq!(member.next_opening_hours, seed.employed * 160);
        assert!(member.completed.is_none());
        assert_eq!(account.employed, seed.employed);
        assert_eq!(account.reserve, seed.reserve);
        assert_eq!(
            account.previous_unretained_hours,
            seed.previous_unretained_hours
        );
        assert_eq!(account.labor_force, seed.employed + seed.reserve);
        assert_eq!(account.hours_per_person, 160);
        assert_eq!(account.next_opening_period, 1);
        assert_eq!(account.next_opening_hours, seed.employed * 160);
        assert!(account.completed.is_none());
        employed.push(account.employed);
    }
    employed.sort_unstable();
    assert_eq!(employed, [1, 2, 4, 4, 20]);
    let count: i64 = fixture
        .target
        .writer
        .connect(NoTls)
        .unwrap()
        .query_one(
            "SELECT count(*) FROM babylon_state.tick_event_v2 WHERE campaign_id=$1::uuid",
            &[fixture.campaign.as_uuid()],
        )
        .unwrap()
        .get(0);
    assert_eq!(count, 0);
    assert_known_material_absence(&mut fixture.preview.snapshot(fixture.campaign, 0).unwrap());
}

#[test]
#[ignore = "requires the task-owned disposable PostgreSQL harness; independent clone ownership"]
fn held_staffing_history_survives_advance_reopen_and_does_not_mutate_authority() {
    let mut fixture = Fixture::new();
    assert_foundation(&fixture);
    fixture.advance_to(2);
    let mut held = fixture.read(2);
    let digest = held.production_evidence_digest().unwrap().unwrap();
    let accounts = &held.production.as_ref().unwrap().staffing_accounts;
    assert_eq!(accounts.len(), 5);
    assert!(accounts.iter().all(|row| row
        .completed
        .as_ref()
        .is_some_and(|period| period.period == 2)));
    fixture.advance_to(4);
    let committed = *fixture.runtime.tail().unwrap();
    let world = fixture.runtime.session().current_world_hash().unwrap();
    fixture.runtime = DurableMaterialRuntime::open(
        &fixture.target.writer,
        fixture.campaign,
        fixture.foundation_digest,
    )
    .unwrap();
    let reader =
        ObserverEconomyReader::connect(&fixture.observer_config, ObserverVisibility::FullObserver)
            .unwrap();
    for tick in [4, 0, 2, 3, 2] {
        let mut snapshot = reader.snapshot(fixture.campaign, tick).unwrap();
        assert_eq!(snapshot.resolve_tick, tick);
        assert_known_material_absence(
            &mut fixture.preview.snapshot(fixture.campaign, tick).unwrap(),
        );
        if tick == 2 {
            assert_eq!(snapshot.production_evidence_digest().unwrap(), Some(digest));
            assert_eq!(snapshot, held);
        }
        assert_eq!(fixture.runtime.session().completed_tick(), 4);
        assert_eq!(fixture.runtime.tail(), Some(&committed));
        assert_eq!(
            fixture.runtime.session().current_world_hash().unwrap(),
            world
        );
    }
    let reopened = DurableMaterialRuntime::open(
        &fixture.target.writer,
        fixture.campaign,
        fixture.foundation_digest,
    )
    .unwrap();
    assert_eq!(reopened.tail(), Some(&committed));
    assert_eq!(reopened.session().current_world_hash().unwrap(), world);
}

#[derive(Clone, Copy, Debug)]
struct Fault {
    relation: &'static str,
    column: &'static str,
    predicate: &'static str,
    tick: i64,
}

// Only constants in this test select identifiers. CTIDs identify one owned row
// across each autocommit write; RETURNING captures its changed physical location.
// Hold the reader result until the old typed value is restored, then check refusal.
fn assert_fault<T: FromSqlOwned + ToSql + Sync + PartialEq + std::fmt::Debug>(
    fixture: &Fixture,
    writer: &mut Client,
    healthy: &ObserverEconomySnapshot,
    fault: Fault,
    change: impl FnOnce(&T) -> T,
) {
    let graph_chunk = fault.relation == "graph_node_f64_v1";
    let select = if graph_chunk {
        format!(
            "SELECT location,value_bits,position FROM (SELECT c.ctid::text AS location, \
             c.campaign_id,c.resolve_tick,u.value_bits,u.position,q.value AS qname \
             FROM babylon_state.graph_node_f64_chunk_v1 c \
             JOIN babylon_state.graph_string_lookup_v1 q ON q.campaign_id=c.campaign_id AND q.string_id=c.qname_id \
             CROSS JOIN LATERAL unnest(c.value_bits) WITH ORDINALITY u(value_bits,position)) expanded \
             WHERE campaign_id=$1::uuid AND resolve_tick=$2 AND {} ORDER BY location,position LIMIT 1",
            fault.predicate,
        )
    } else {
        format!("SELECT ctid::text, {} FROM babylon_state.{} WHERE campaign_id=$1::uuid AND resolve_tick=$2 AND {} ORDER BY ctid LIMIT 1", fault.column,fault.relation,fault.predicate)
    };
    let row = writer
        .query_one(&select, &[fixture.campaign.as_uuid(), &fault.tick])
        .unwrap();
    let location: String = row.get(0);
    let original: T = row.get(1);
    let changed = change(&original);
    assert_ne!(changed, original, "{fault:?}");
    let position = if graph_chunk {
        Some(i32::try_from(row.get::<_, i64>(2)).unwrap())
    } else {
        None
    };
    let update = if graph_chunk {
        "UPDATE babylon_state.graph_node_f64_chunk_v1 SET value_bits[$3]=$1 WHERE ctid=$2::text::tid RETURNING ctid::text".to_owned()
    } else {
        format!(
            "UPDATE babylon_state.{} SET {}=$1 WHERE ctid=$2::text::tid RETURNING ctid::text",
            fault.relation, fault.column
        )
    };
    let moved = update_fault_value(writer, &update, &changed, &location, position);
    assert_eq!(moved.len(), 1, "{fault:?}");
    let location: String = moved[0].get(0);
    let refusal = fixture
        .observer
        .snapshot(fixture.campaign, healthy.resolve_tick);
    let restored = update_fault_value(writer, &update, &original, &location, position);
    assert_eq!(restored.len(), 1, "{fault:?}");
    assert_eq!(
        refusal,
        Err(ObserverEconomyError::InvalidProjection),
        "{fault:?}"
    );
    assert_eq!(
        fixture.read(healthy.resolve_tick),
        *healthy,
        "restore {fault:?}"
    );
}

// Corruption is admitted only by this disposable owner fixture. Disable the
// exact immutable-row guard within a transaction and restore its catalog state
// before the observer read; a failing mutation rolls back the trigger change.
fn update_fault_value<T: ToSql + Sync>(
    writer: &mut Client,
    sql: &str,
    value: &T,
    location: &str,
    position: Option<i32>,
) -> Vec<postgres::Row> {
    if let Some(position) = position {
        let mut tx = writer.transaction().unwrap();
        tx.batch_execute("ALTER TABLE babylon_state.graph_node_f64_chunk_v1 DISABLE TRIGGER graph_node_f64_chunk_immutable_v1").unwrap();
        let rows = tx.query(sql, &[value, &location, &position]).unwrap();
        tx.batch_execute("ALTER TABLE babylon_state.graph_node_f64_chunk_v1 ENABLE TRIGGER graph_node_f64_chunk_immutable_v1").unwrap();
        tx.commit().unwrap();
        rows
    } else {
        writer.query(sql, &[value, &location]).unwrap()
    }
}

fn flipped(bytes: &[u8]) -> Vec<u8> {
    let mut changed = bytes.to_vec();
    *changed.last_mut().unwrap() ^= 1;
    changed
}

fn assert_graph_and_state_faults(
    fixture: &Fixture,
    writer: &mut Client,
    healthy: &ObserverEconomySnapshot,
) {
    for tick in [2, 1] {
        assert_fault(
            fixture,
            writer,
            healthy,
            Fault {
                relation: "graph_node_f64_v1",
                column: "value_bits",
                predicate: "qname='social-class/employed-population'",
                tick,
            },
            |value: &i64| value ^ 1,
        );
    }
    assert_fault(
        fixture,
        writer,
        healthy,
        Fault {
            relation: "graph_node_f64_v1",
            column: "value_bits",
            predicate: "qname NOT LIKE 'social-class/%'",
            tick: 2,
        },
        |value: &i64| value ^ 1,
    );
    assert_fault(
        fixture,
        writer,
        healthy,
        Fault {
            relation: "hex_state_delta_v1",
            column: "c_bits",
            predicate: "true",
            tick: 2,
        },
        |value: &i64| value ^ 1,
    );
}

#[derive(Clone, Copy)]
enum EventChunk {
    Parent,
    Field,
}
impl EventChunk {
    fn table(self) -> &'static str {
        match self {
            Self::Parent => "event_parent_chunk_v1",
            Self::Field => "event_field_chunk_v1",
        }
    }
    fn guard(self) -> &'static str {
        match self {
            Self::Parent => "event_parent_chunk_v1_immutable",
            Self::Field => "event_field_chunk_v1_immutable",
        }
    }
}
#[derive(Clone, Copy)]
enum EventLookup {
    Text,
    SharedString,
}
impl EventLookup {
    fn table(self) -> &'static str {
        match self {
            Self::Text => "event_text_lookup_v1",
            Self::SharedString => "graph_string_lookup_v1",
        }
    }
    fn id_column(self) -> &'static str {
        match self {
            Self::Text => "text_id",
            Self::SharedString => "string_id",
        }
    }
    fn insert_guard(self) -> &'static str {
        match self {
            Self::Text => "event_text_lookup_v1_insert_guard",
            Self::SharedString => "graph_string_lookup_insert_guard_v1",
        }
    }
    fn immutable_guard(self) -> &'static str {
        match self {
            Self::Text => "event_text_lookup_v1_immutable",
            Self::SharedString => "graph_string_lookup_immutable_v1",
        }
    }
}
struct EventCell {
    chunk: EventChunk,
    location: String,
    index: i32,
    column: &'static str,
}

fn event_fixture_lock(tx: &mut postgres::Transaction<'_>, campaign: CampaignId) {
    tx.query_one("SELECT pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended('babylon.graph-lookup.v1:'||$1::uuid::text,0))",&[campaign.as_uuid()]).unwrap();
    tx.query_one("SELECT pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended('babylon.event-marker.v1:'||$1::uuid::text||':2',0))",&[campaign.as_uuid()]).unwrap();
}
fn fixture_guard(tx: &mut postgres::Transaction<'_>, table: &str, guard: &str, enabled: bool) {
    // Identifiers come only from the closed enums and fixed fixture guards.
    let state:String=tx.query_one("SELECT tgenabled::text FROM pg_catalog.pg_trigger WHERE tgrelid=$1::text::regclass AND tgname=$2",&[&format!("babylon_state.{table}"),&guard]).unwrap().get(0);
    assert_eq!(state, if enabled { "D" } else { "O" });
    if enabled {
        // A temporary lookup insert queues its deferred marker foreign key.
        // Drain that valid reference before restoring the fixture guard.
        tx.batch_execute("SET CONSTRAINTS ALL IMMEDIATE").unwrap();
    }
    tx.batch_execute(&format!(
        "ALTER TABLE babylon_state.{table} {} TRIGGER {guard}",
        if enabled { "ENABLE" } else { "DISABLE" }
    ))
    .unwrap();
}
fn set_event_cell<T: ToSql + Sync>(
    tx: &mut postgres::Transaction<'_>,
    cell: &EventCell,
    value: &T,
) -> String {
    fixture_guard(tx, cell.chunk.table(), cell.chunk.guard(), false);
    let sql = format!(
        "UPDATE babylon_state.{} SET {}[$3]=$1 WHERE ctid=$2::text::tid RETURNING ctid::text",
        cell.chunk.table(),
        cell.column
    );
    let rows = tx
        .query(&sql, &[value, &cell.location, &cell.index])
        .unwrap();
    assert_eq!(rows.len(), 1);
    let moved = rows[0].get(0);
    fixture_guard(tx, cell.chunk.table(), cell.chunk.guard(), true);
    moved
}
fn read_event_field_cell(
    writer: &mut Client,
    campaign: CampaignId,
    name: &str,
    column: &'static str,
) -> (EventCell, postgres::Row) {
    assert!(matches!(column, "int_values" | "key_ids"));
    let sql=format!("SELECT c.ctid::text,p::integer,c.{column}[p],c.value_tag FROM babylon_state.event_field_chunk_v1 c CROSS JOIN LATERAL generate_subscripts(c.event_ordinals,1) AS idx(p) JOIN babylon_state.event_text_lookup_v1 n ON n.campaign_id=c.campaign_id AND n.text_id=c.name_ids[p] WHERE c.campaign_id=$1::uuid AND c.resolve_tick=2 AND n.value=$2 ORDER BY c.chunk,p LIMIT 1");
    let row = writer
        .query_one(&sql, &[campaign.as_uuid(), &name])
        .unwrap();
    let cell = EventCell {
        chunk: EventChunk::Field,
        location: row.get(0),
        index: row.get(1),
        column,
    };
    (cell, row)
}
fn assert_event_integer_fault(
    fixture: &Fixture,
    writer: &mut Client,
    healthy: &ObserverEconomySnapshot,
) {
    let (mut cell, row) =
        read_event_field_cell(writer, fixture.campaign, "retained-hours", "int_values");
    let original: i64 = row.get(2);
    let changed = original.checked_add(1).unwrap();
    let mut tx = writer.transaction().unwrap();
    event_fixture_lock(&mut tx, fixture.campaign);
    cell.location = set_event_cell(&mut tx, &cell, &changed);
    tx.commit().unwrap();
    let refusal = fixture
        .observer
        .snapshot(fixture.campaign, healthy.resolve_tick);
    let mut tx = writer.transaction().unwrap();
    event_fixture_lock(&mut tx, fixture.campaign);
    let _ = set_event_cell(&mut tx, &cell, &original);
    tx.commit().unwrap();
    assert_eq!(refusal, Err(ObserverEconomyError::InvalidProjection));
    assert_eq!(fixture.read(healthy.resolve_tick), *healthy);
}
fn lookup_head(
    writer: &mut impl postgres::GenericClient,
    campaign: CampaignId,
    lookup: EventLookup,
) -> (i64, i64) {
    let sql = format!(
        "SELECT count(*),coalesce(max({}),-1) FROM babylon_state.{} WHERE campaign_id=$1::uuid",
        lookup.id_column(),
        lookup.table()
    );
    let row = writer.query_one(&sql, &[campaign.as_uuid()]).unwrap();
    (row.get(0), row.get(1))
}
// Temporary foreign identity is test-owned, appended only while its exact guard
// is disabled in this transaction. It changes one cell, never a shared lookup.
fn append_foreign_lookup<T: ToSql + Sync>(
    tx: &mut postgres::Transaction<'_>,
    campaign: CampaignId,
    lookup: EventLookup,
    value: &T,
    id: i64,
) {
    let duplicate = tx
        .query_one(
            &format!(
                "SELECT count(*) FROM babylon_state.{} WHERE campaign_id=$1::uuid AND value=$2",
                lookup.table()
            ),
            &[campaign.as_uuid(), value],
        )
        .unwrap()
        .get::<_, i64>(0);
    assert_eq!(duplicate, 0, "foreign fixture identity must be distinct");
    let guard = lookup.insert_guard();
    fixture_guard(tx, lookup.table(), guard, false);
    let changed=tx.execute(&format!("INSERT INTO babylon_state.{}(campaign_id,{},first_tick,value) VALUES($1::uuid,$2,2,$3)",lookup.table(),lookup.id_column()),&[campaign.as_uuid(),&id,value]).unwrap();
    assert_eq!(changed, 1);
    fixture_guard(tx, lookup.table(), guard, true);
}
fn remove_foreign_lookup<T: ToSql + Sync>(
    tx: &mut postgres::Transaction<'_>,
    campaign: CampaignId,
    lookup: EventLookup,
    value: &T,
    id: i64,
) {
    let guard = lookup.immutable_guard();
    fixture_guard(tx, lookup.table(), guard, false);
    let changed=tx.execute(&format!("DELETE FROM babylon_state.{} WHERE campaign_id=$1::uuid AND {}=$2 AND first_tick=2 AND value=$3",lookup.table(),lookup.id_column()),&[campaign.as_uuid(),&id,value]).unwrap();
    assert_eq!(changed, 1);
    fixture_guard(tx, lookup.table(), guard, true);
}
fn assert_event_lookup_fault<T: ToSql + Sync>(
    fixture: &Fixture,
    writer: &mut Client,
    healthy: &ObserverEconomySnapshot,
    mut cell: EventCell,
    lookup: EventLookup,
    original: i64,
    foreign: &T,
) {
    let before = lookup_head(writer, fixture.campaign, lookup);
    assert_eq!(before.1.checked_add(1), Some(before.0));
    let foreign_id = before.0;
    let mut tx = writer.transaction().unwrap();
    event_fixture_lock(&mut tx, fixture.campaign);
    append_foreign_lookup(&mut tx, fixture.campaign, lookup, foreign, foreign_id);
    cell.location = set_event_cell(&mut tx, &cell, &foreign_id);
    tx.commit().unwrap();
    // All trigger enable states are restored before the reader's schema census.
    let refusal = fixture
        .observer
        .snapshot(fixture.campaign, healthy.resolve_tick);
    let mut tx = writer.transaction().unwrap();
    event_fixture_lock(&mut tx, fixture.campaign);
    let _ = set_event_cell(&mut tx, &cell, &original);
    remove_foreign_lookup(&mut tx, fixture.campaign, lookup, foreign, foreign_id);
    tx.commit().unwrap();
    assert_eq!(lookup_head(writer, fixture.campaign, lookup), before);
    assert_eq!(refusal, Err(ObserverEconomyError::InvalidProjection));
    assert_eq!(fixture.read(healthy.resolve_tick), *healthy);
}
fn assert_event_subject_fault(
    fixture: &Fixture,
    writer: &mut Client,
    healthy: &ObserverEconomySnapshot,
) {
    let (cell, row) = read_event_field_cell(writer, fixture.campaign, "subject", "key_ids");
    let original: i64 = row.get(2);
    assert_eq!(row.get::<_, i16>(3), 7, "native staffing subject is a Node");
    let name:String=writer.query_one("SELECT value FROM babylon_state.graph_string_lookup_v1 WHERE campaign_id=$1::uuid AND string_id=$2",&[fixture.campaign.as_uuid(),&original]).unwrap().get(0);
    let foreign = format!("{name}-foreign");
    assert_ne!(foreign, name);
    assert_event_lookup_fault(
        fixture,
        writer,
        healthy,
        cell,
        EventLookup::SharedString,
        original,
        &foreign,
    );
}
fn assert_event_rule_fault(
    fixture: &Fixture,
    writer: &mut Client,
    healthy: &ObserverEconomySnapshot,
) {
    let row=writer.query_one("SELECT c.ctid::text,p::integer,c.rule_ids[p],r.value FROM babylon_state.event_parent_chunk_v1 c CROSS JOIN LATERAL generate_subscripts(c.event_ordinals,1) AS idx(p) JOIN babylon_state.event_text_lookup_v1 t ON t.campaign_id=c.campaign_id AND t.text_id=c.type_ids[p] JOIN babylon_state.event_text_lookup_v1 r ON r.campaign_id=c.campaign_id AND r.text_id=c.rule_ids[p] WHERE c.campaign_id=$1::uuid AND c.resolve_tick=2 AND t.value='WORKFORCE_STAFFING' ORDER BY c.chunk,p LIMIT 1",&[fixture.campaign.as_uuid()]).unwrap();
    let cell = EventCell {
        chunk: EventChunk::Parent,
        location: row.get(0),
        index: row.get(1),
        column: "rule_ids",
    };
    let original: i64 = row.get(2);
    let name: String = row.get(3);
    let foreign = format!("{name}-foreign");
    assert_event_lookup_fault(
        fixture,
        writer,
        healthy,
        cell,
        EventLookup::Text,
        original,
        &foreign,
    );
}
fn assert_event_faults(fixture: &Fixture, writer: &mut Client, healthy: &ObserverEconomySnapshot) {
    assert_event_integer_fault(fixture, writer, healthy);
    assert_event_subject_fault(fixture, writer, healthy);
    assert_event_rule_fault(fixture, writer, healthy);
    swap_event_fields(writer, fixture.campaign);
    let refusal = fixture.observer.snapshot(fixture.campaign, 2);
    swap_event_fields(writer, fixture.campaign);
    assert_eq!(refusal, Err(ObserverEconomyError::InvalidProjection));
    assert_eq!(fixture.read(2), *healthy);
}
fn swap_event_fields(writer: &mut Client, campaign: CampaignId) {
    let mut tx = writer.transaction().unwrap();
    event_fixture_lock(&mut tx, campaign);
    let ordinal:i64=tx.query_one("SELECT ordinal FROM babylon_state.tick_event_v2 WHERE campaign_id=$1::uuid AND resolve_tick=2 AND event_type='WORKFORCE_STAFFING' ORDER BY ordinal LIMIT 1",&[campaign.as_uuid()]).unwrap().get(0);
    let highest:i64=tx.query_one("SELECT max(position) FROM babylon_state.tick_event_field_v2 WHERE campaign_id=$1::uuid AND resolve_tick=2 AND ordinal=$2",&[campaign.as_uuid(),&ordinal]).unwrap().get(0);
    let spare = highest.checked_add(1).unwrap();
    assert!(spare <= i64::from(u32::MAX));
    fixture_guard(
        &mut tx,
        "event_field_chunk_v1",
        "event_field_chunk_v1_immutable",
        false,
    );
    for (from, to) in [(11_i64, spare), (12, 11), (spare, 12)] {
        let row=tx.query_one("SELECT c.ctid::text,p::integer FROM babylon_state.event_field_chunk_v1 c CROSS JOIN LATERAL generate_subscripts(c.event_ordinals,1) AS idx(p) WHERE c.campaign_id=$1::uuid AND c.resolve_tick=2 AND c.event_ordinals[p]=$2 AND c.positions[p]=$3 ORDER BY c.chunk,p LIMIT 1",&[campaign.as_uuid(),&ordinal,&from]).unwrap();
        let location: String = row.get(0);
        let index: i32 = row.get(1);
        assert_eq!(tx.execute("UPDATE babylon_state.event_field_chunk_v1 SET positions[$3]=$4 WHERE ctid=$1::text::tid AND campaign_id=$2::uuid",&[&location,campaign.as_uuid(),&index,&to]).unwrap(),1);
    }
    fixture_guard(
        &mut tx,
        "event_field_chunk_v1",
        "event_field_chunk_v1_immutable",
        true,
    );
    tx.commit().unwrap();
}

// A valid canonical body and matching reference digest still cannot replace
// an authenticated historical section under its unchanged manifest/envelope.
fn assert_valid_checkpoint_body_fault(
    fixture: &Fixture,
    writer: &mut Client,
    healthy: &ObserverEconomySnapshot,
) {
    let manifest = babylon_tick::replay_identity::world_register_manifest().unwrap();
    let replacement =
        babylon_tick::replay_identity::encode_world_register_set(&manifest, 3).unwrap();
    assert_eq!(replacement.completed_tick(), 3);
    let original = writer.query_one(
        "SELECT inline_section_bytes,decoded_length,decoded_sha256 FROM babylon_state.checkpoint_section_v1 WHERE campaign_id=$1::uuid AND resolve_tick=2 AND section_tag=2 AND ordinal=0",
        &[fixture.campaign.as_uuid()],
    ).unwrap();
    let bytes: Vec<u8> = original.get(0);
    let length: i64 = original.get(1);
    let digest: Vec<u8> = original.get(2);
    let expected = babylon_tick::replay_identity::encode_world_register_set(&manifest, 2).unwrap();
    assert_eq!(bytes, expected.canonical_bytes());
    assert_eq!(digest, expected.digest());
    assert_ne!(bytes, replacement.canonical_bytes());
    let authority = |client: &mut Client| {
        let row = client.query_one(
            "SELECT c.manifest_bytes,m.envelope_digest FROM babylon_state.checkpoint_manifest c JOIN babylon_state.tick_commit m USING(campaign_id,resolve_tick) WHERE c.campaign_id=$1::uuid AND c.resolve_tick=2",
            &[fixture.campaign.as_uuid()],
        ).unwrap();
        (row.get::<_, Vec<u8>>(0), row.get::<_, Vec<u8>>(1))
    };
    let before = authority(writer);
    let update = "UPDATE babylon_state.checkpoint_section_v1 SET inline_section_bytes=$2,decoded_length=$3,decoded_sha256=$4 WHERE campaign_id=$1::uuid AND resolve_tick=2 AND section_tag=2 AND ordinal=0";
    let changed = replacement.canonical_bytes().to_vec();
    let changed_length = i64::try_from(changed.len()).unwrap();
    let changed_digest = replacement.digest().to_vec();
    assert_eq!(
        writer
            .execute(
                update,
                &[
                    fixture.campaign.as_uuid(),
                    &changed,
                    &changed_length,
                    &changed_digest
                ]
            )
            .unwrap(),
        1
    );
    assert_eq!(authority(writer), before);
    let refusal = fixture
        .observer
        .snapshot(fixture.campaign, healthy.resolve_tick);
    assert_eq!(
        writer
            .execute(
                update,
                &[fixture.campaign.as_uuid(), &bytes, &length, &digest]
            )
            .unwrap(),
        1
    );
    assert_eq!(authority(writer), before);
    assert_eq!(refusal, Err(ObserverEconomyError::InvalidProjection));
    assert_eq!(fixture.read(healthy.resolve_tick), *healthy);
}

fn assert_commit_faults(fixture: &Fixture, writer: &mut Client, healthy: &ObserverEconomySnapshot) {
    for (relation, column, predicate) in [
        (
            "checkpoint_section_v1",
            "inline_section_bytes",
            "section_tag=2",
        ),
        ("checkpoint_manifest", "manifest_bytes", "true"),
        ("tick_action_batch_v1", "exact_action_batch_bytes", "true"),
        ("archive_dirty_receipt_v1", "tick_content_hash", "true"),
        ("tick_commit", "envelope_digest", "true"),
    ] {
        assert_fault(
            fixture,
            writer,
            healthy,
            Fault {
                relation,
                column,
                predicate,
                tick: 2,
            },
            |bytes: &Vec<u8>| flipped(bytes),
        );
    }
}

#[test]
#[ignore = "requires the task-owned disposable PostgreSQL harness; independent clone ownership"]
fn complete_marker_authentication_refuses_independent_staffing_and_auxiliary_row_corruption() {
    let mut fixture = Fixture::new();
    fixture.advance_to(4);
    let healthy = fixture.read(2);
    let tail = *fixture.runtime.tail().unwrap();
    let world = fixture.runtime.session().current_world_hash().unwrap();
    let mut writer = fixture.target.writer.connect(NoTls).unwrap();
    assert_graph_and_state_faults(&fixture, &mut writer, &healthy);
    assert_event_faults(&fixture, &mut writer, &healthy);
    assert_commit_faults(&fixture, &mut writer, &healthy);
    assert_valid_checkpoint_body_fault(&fixture, &mut writer, &healthy);
    assert_known_material_absence(&mut fixture.preview.snapshot(fixture.campaign, 2).unwrap());
    assert_eq!(fixture.runtime.tail(), Some(&tail));
    assert_eq!(
        fixture.runtime.session().current_world_hash().unwrap(),
        world
    );
    let reopened = DurableMaterialRuntime::open(
        &fixture.target.writer,
        fixture.campaign,
        fixture.foundation_digest,
    )
    .unwrap();
    assert_eq!(reopened.tail(), Some(&tail));
    assert_eq!(reopened.session().current_world_hash().unwrap(), world);
}
