//! Packed membership must preserve exact restricted SQL disclosure and replay.
use super::*;

#[test]
#[ignore = "requires the task-owned disposable PostgreSQL runtime and committed ticks"]
fn live_packed_membership_rejects_invalid_arrays_and_unresolved_references() {
    let mut phase = std::time::Instant::now();
    let target = LiveWorkerTarget::create("packedmembers", 0x34321, 1);
    record_phase("fixture", &mut phase);
    let report = ArchiveWorker::new(&target.config)
        .sweep_once(target.campaign_id, &StubPageProducer)
        .expect("one complete authenticated publication");
    assert_eq!(report.verified_tick(), 1);
    record_phase("publication", &mut phase);
    with_reader(&target.config, |reader| {
        record_phase("confined_reader", &mut phase);
        let mut client = target.config.connect(NoTls).unwrap();
        let retired: bool = client
            .query_one(
                "SELECT to_regclass('babylon_meta.archive_revision_atom_v2') IS NULL \
             AND to_regclass('babylon_meta.archive_revision_grant_v2') IS NULL",
                &[],
            )
            .unwrap()
            .get(0);
        assert!(
            retired,
            "packed pages retire the duplicated association tables"
        );

        assert_invalid_arrays_rejected(&mut client, target.campaign_id);

        let healthy = disclosed_count(&mut client, &target);
        assert_eq!(
            healthy,
            (1, 1),
            "healthy publication has body and candidate identity"
        );
        for assignment in [
            "atom_ids[1]=decode(repeat('a1',32),'hex')",
            "grant_provenance_refs[1]=babylon_meta.archive_provenance_intern_v1(campaign_id,'changed-frozen-provenance','changed')",
            "grant_ticks[1]=source_tick+1",
        ] {
            let mut transaction = client.transaction().unwrap();
            transaction.execute(
            &format!("UPDATE babylon_meta.archive_page_revision_v2 SET {assignment} WHERE campaign_id=$1"),
            &[target.campaign_id.as_uuid()],
        ).unwrap();
            // Direct SQL must withhold the body while retaining an identifiable
            // corrupt candidate. Rust post-fetch checks cannot provide this proof.
            assert_eq!(
                disclosed_count(&mut transaction, &target),
                (0, 1),
                "{assignment}"
            );
            transaction.rollback().unwrap();
        }
        for mutation in [
        "UPDATE babylon_meta.archive_atom_v1 SET subject_id='99999' \
         WHERE atom_id=(SELECT atom_ids[1] FROM babylon_meta.archive_page_revision_v2 WHERE campaign_id=$1)",
        "UPDATE babylon_meta.archive_atom_v1 SET valid_tick=valid_tick+1 \
         WHERE atom_id=(SELECT atom_ids[1] FROM babylon_meta.archive_page_revision_v2 WHERE campaign_id=$1)",
    ] {
        let mut transaction = client.transaction().unwrap();
        assert_eq!(transaction.execute(mutation, &[target.campaign_id.as_uuid()]).unwrap(), 1);
        assert_eq!(disclosed_count(&mut transaction, &target), (0, 1), "{mutation}");
        transaction.rollback().unwrap();
    }
        assert_eq!(disclosed_count(&mut client, &target), healthy);
        record_phase("array_and_reference_faults", &mut phase);
        drop(client);
        let scope = scope_at(&target.config, target.campaign_id, 1);
        let dossier = reader
            .dossier_as_of(
                &scope,
                &stub_subject_spec(1).page_ref,
                &ArchiveDossierBounds::default(),
            )
            .expect("restored complete publication remains readable");
        assert!(matches!(dossier.state, ArchiveDossierState::Ready { .. }));
        record_phase("restored_dossier", &mut phase);
    });
    assert_eq!(
        receipt_consumption_count(&target.config, target.campaign_id),
        1
    );
    target.finish();
    record_phase("cleanup", &mut phase);
}

fn assert_invalid_arrays_rejected(client: &mut postgres::Client, campaign: CampaignId) {
    for assignment in [
        "atom_ids=array_fill(NULL::bytea,ARRAY[atom_count])",
        "atom_ids=array_fill(atom_ids[1],ARRAY[atom_count],ARRAY[0])",
        "atom_ids=ARRAY[atom_ids]",
        "atom_ids=ARRAY[atom_ids[1],atom_ids[1]],atom_count=2",
        "grant_subject_kinds=array_fill(NULL::text,ARRAY[grant_count])",
        "grant_keys=grant_keys[1:grant_count-1]",
        "grant_subject_kinds[1]='concept'",
        "grant_ticks[1]=-1",
        "grant_provenance_refs=array_fill(NULL::integer,ARRAY[grant_count])",
        "grant_provenance_refs=array_fill(grant_provenance_refs[1],ARRAY[grant_count],ARRAY[0])",
        "grant_provenance_refs=ARRAY[grant_provenance_refs]",
        "grant_provenance_refs[1]=0",
        "grant_subject_kinds=array_append(grant_subject_kinds,grant_subject_kinds[1]), \
     grant_subject_ids=array_append(grant_subject_ids,grant_subject_ids[1]), \
     grant_keys=array_append(grant_keys,grant_keys[1]), \
     grant_ticks=array_append(grant_ticks,grant_ticks[1]), \
     grant_provenance_refs=array_append(grant_provenance_refs,grant_provenance_refs[1]),grant_count=grant_count+1",
    ] {
        let mut transaction = client.transaction().unwrap();
        let failure = transaction
        .execute(
            &format!("UPDATE babylon_meta.archive_page_revision_v2 SET {assignment} WHERE campaign_id=$1"),
            &[campaign.as_uuid()],
        )
        .expect_err("invalid arrays cannot enter a retained publication");
        assert_eq!(
            failure.code(),
            Some(&postgres::error::SqlState::CHECK_VIOLATION),
            "{assignment}"
        );
        transaction.rollback().unwrap();
    }
}

fn record_phase(label: &str, started: &mut std::time::Instant) {
    eprintln!(
        "packed_membership_stage phase={label} elapsed_ns={}",
        started.elapsed().as_nanos()
    );
    *started = std::time::Instant::now();
}

fn disclosed_count(
    client: &mut impl postgres::GenericClient,
    target: &LiveWorkerTarget,
) -> (i64, i64) {
    client.batch_execute("SET ROLE babylon_reader").unwrap();
    let row = client.query_one(
        "SELECT (SELECT count(*) FROM public.v_archive_revision_known_v2 WHERE campaign_id=$1), \
         (SELECT count(*) FROM public.v_archive_revision_index_v2 WHERE campaign_id=$1)",
        &[target.campaign_id.as_uuid()],
    ).unwrap();
    client.batch_execute("RESET ROLE").unwrap();
    (row.get(0), row.get(1))
}
