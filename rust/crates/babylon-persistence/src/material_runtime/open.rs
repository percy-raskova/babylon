//! Capture one consistent Open snapshot; reconstruct only after its transaction ends.
use super::*;

struct CapturedOpen {
    tick: u64,
    marker: Option<postgres::Row>,
    checkpoint: Option<runtime_checkpoint::CapturedRuntimeCheckpoint>,
}

impl CapturedOpen {
    fn capture(
        transaction: &mut postgres::Transaction<'_>,
        campaign: CampaignId,
    ) -> Result<Self, MaterialRuntimeError> {
        let tick = read_tail_tick(transaction, campaign)?;
        let marker = if tick == 0 {
            None
        } else {
            capture_marker(
                transaction,
                StoredTickReadSource::Runtime,
                campaign,
                i64::try_from(tick).map_err(|_| MaterialRuntimeError::Bounds)?,
            )?
        };
        let checkpoint = if tick == 0 {
            None
        } else {
            Some(runtime_checkpoint::CapturedRuntimeCheckpoint::capture(
                transaction,
                campaign,
                tick,
            )?)
        };
        Ok(Self {
            tick,
            marker,
            checkpoint,
        })
    }
}

pub(super) fn restore<C>(
    config: &Config,
    campaign: CampaignId,
    capture: impl FnOnce(
        &mut postgres::Transaction<'_>,
    ) -> Result<(CapturedMaterialFoundation, C), MaterialRuntimeError>,
    admit: impl FnOnce(
        CapturedMaterialFoundation,
        C,
    ) -> Result<MaterialRuntimeFoundation, MaterialRuntimeError>,
) -> Result<DurableMaterialRuntime, MaterialRuntimeError> {
    let bounded = bounded_material_writer_config(config)?;
    let mut client = bounded.connect(NoTls)?;
    verify_runtime_schema_client(&mut client)?;
    let mut transaction = client
        .build_transaction()
        .isolation_level(postgres::IsolationLevel::RepeatableRead)
        .read_only(true)
        .start()?;
    let (captured_foundation, policy) = capture(&mut transaction)?;
    let captured = CapturedOpen::capture(&mut transaction, campaign)?;
    transaction.commit()?;
    // This is a freshness witness over actual captured components, not a
    // substitute for the complete existing foundation or checkpoint admission.
    let fingerprint = captured_foundation.capture_fingerprint()?;
    let foundation = admit(captured_foundation, policy)?;
    if foundation
        .register
        .organizer_config()
        .is_some_and(|organizer| organizer.campaign_id != *campaign.canonical_bytes())
    {
        return Err(MaterialRuntimeError::FoundationMismatch);
    }
    let digest = foundation.digest();
    let lookup = material_storage::OpeningRegister::from_opening(&foundation.register)
        .map_err(material_storage::Error::State)?;
    let initial_lookup_chain = material_storage::initial_lookup_chain(&lookup)?;
    let stored = if let Some(checkpoint) = captured.checkpoint {
        let scope = foundation
            .graph
            .stable_graph_state()
            .map_err(MaterialReplayError::Graph)?
            .scenario_scope()
            .to_owned();
        let components = MaterialComponentIdentity::from_foundation(&foundation.graph_foundation);
        Some(checkpoint.admit(
            MaterialReadAuthority::cold(&scope, digest, &components, &lookup),
            MaterialEnvelopeRead::CanonicalBytes,
        )?)
    } else {
        None
    };
    let mut session = foundation.into_session()?;
    let (tail, lookup_chain) = restore_checkpoint(&mut session, stored, initial_lookup_chain)?;
    revalidate_capture(
        &mut client,
        campaign,
        digest,
        fingerprint,
        captured.tick,
        captured.marker.as_ref(),
    )?;
    Ok(DurableMaterialRuntime {
        config: bounded,
        campaign,
        session,
        lookup,
        lookup_chain,
        tail,
        last_receipt: None,
        last_choice_receipts: Vec::new(),
    })
}

fn restore_checkpoint(
    session: &mut MaterialReplaySession<HypergraphStore>,
    stored: Option<StoredMaterialTick<'static>>,
    initial_lookup_chain: [u8; 32],
) -> Result<(Option<IdentifiedMaterialTick>, [u8; 32]), MaterialRuntimeError> {
    let Some(stored) = stored else {
        return Ok((None, initial_lookup_chain));
    };
    session.restore_full_checkpoint(
        &stored.graph,
        &stored.material,
        &stored.sections.world_register,
        stored.register.into_owned(),
    )?;
    if session.current_world_hash()? != stored.identity.result_world_hash() {
        return Err(MaterialRuntimeError::InvalidCheckpoint);
    }
    Ok((Some(stored.identity), stored.lookup_chain))
}

fn revalidate_capture(
    client: &mut postgres::Client,
    campaign: CampaignId,
    digest: [u8; 32],
    fingerprint: [u8; 32],
    tick: u64,
    original_marker: Option<&postgres::Row>,
) -> Result<(), MaterialRuntimeError> {
    let mut transaction = client
        .build_transaction()
        .isolation_level(postgres::IsolationLevel::RepeatableRead)
        .read_only(true)
        .start()?;
    if read_tail_tick(&mut transaction, campaign)? != tick {
        return Err(MaterialRuntimeError::TailConflict);
    }
    let foundation = capture_material_foundation_components(
        &mut transaction,
        campaign,
        digest,
        FoundationReadSource::Runtime,
    )?;
    let marker = if tick == 0 {
        None
    } else {
        capture_marker(
            &mut transaction,
            StoredTickReadSource::Runtime,
            campaign,
            i64::try_from(tick).map_err(|_| MaterialRuntimeError::Bounds)?,
        )?
    };
    transaction.commit()?;
    if foundation.capture_fingerprint()? != fingerprint {
        return Err(MaterialRuntimeError::FoundationMismatch);
    }
    if capture_identity::rows_digest(marker.iter())?
        != capture_identity::rows_digest(original_marker.into_iter())?
    {
        return Err(MaterialRuntimeError::TailConflict);
    }
    // A subsequent concurrent advance remains possible. Admission reserves no
    // campaign; the backend and the writer retain their expected-tail checks.
    Ok(())
}
