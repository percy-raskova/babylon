//! One full authenticated read per source boundary, shared by all audit folds.
use super::recovery::Identity;
use super::{
    Candidate, Instant, KnownBinding, ObservationContext, ObserverEconomyReader,
    ObserverMaterialCursor, ObserverVisibility, Opening, Perspective, PreparedObservation, Record,
    Work,
};
use babylon_persistence::qualification_audit::aid::MaterialWorldRegister;

impl Work {
    pub(in crate::observer_io) fn read(
        self,
        reader: ObserverEconomyReader,
        context: &ObservationContext,
        cursor: &mut Option<ObserverMaterialCursor>,
    ) -> Result<(PreparedObservation, Candidate), String> {
        self.configuration
            .policy
            .verify()
            .map_err(|e| e.to_string())?;
        if self.recovery.is_some() {
            self.reopened(reader, context, cursor)
        } else if context.tick == 0 {
            self.opening(reader, context, cursor)
        } else {
            self.boundary(reader, context, cursor)
        }
    }

    fn opening(
        mut self,
        reader: ObserverEconomyReader,
        context: &ObservationContext,
        cursor: &mut Option<ObserverMaterialCursor>,
    ) -> Result<(PreparedObservation, Candidate), String> {
        let mut candidate_cursor = cursor.clone();
        let started = Instant::now();
        let snapshot = reader
            .snapshot_with_cursor(context.campaign, 0, &mut candidate_cursor)
            .map_err(|e| e.to_string())?;
        let production_read_elapsed_ns = super::elapsed(started)?;
        let started = Instant::now();
        let policy = self
            .configuration
            .policy
            .scope(self.scope.campaign, self.scope.foundation);
        if snapshot.campaign_id != context.campaign.as_uuid().to_string()
            || snapshot.resolve_tick != 0
            || snapshot.visibility != ObserverVisibility::FullObserver
            || snapshot.foundation_digest != super::hex(&self.scope.foundation)
            || snapshot.tick_content_hash.is_some()
        {
            return Err("native aid opening identity or byte limit differs".into());
        }
        let admitted_cursor = candidate_cursor
            .as_ref()
            .ok_or("native aid authenticated opening cursor absent")?;
        let foundations = admitted_cursor
            .opening_foundations(context.campaign)
            .map_err(|e| e.to_string())?;
        if foundations.material_foundation_sha256 != self.scope.foundation {
            return Err("native opening component admission differs from its scope".into());
        }
        let geography = babylon_persistence::qualification_audit::county_roster(&snapshot)
            .map_err(|e| e.to_string())?;
        let opening = admitted_cursor
            .with_opening_register(context.campaign, |register| {
                if register.canonical_bytes().len() > policy.material_register_bytes {
                    return Err("native aid opening exceeds its register byte limit".to_string());
                }
                self.custody.open(register, &self.scope, self.duration)?;
                Ok(Opening {
                    campaign: snapshot.campaign_id.clone(),
                    foundation_sha256: snapshot.foundation_digest.clone(),
                    graph_foundation_sha256: super::hex(&foundations.graph_foundation_sha256),
                    policy_sha256: super::hex(&policy.policy),
                    material_register_sha256: super::hex(&register.digest()),
                    material_register_bytes: register.canonical_bytes().len(),
                    geography,
                })
            })
            .map_err(|e| e.to_string())??;
        // The weak opening cursor must not keep the large admission alive.
        // Only compact owned disclosures and hashes leave the borrow above.
        drop(reader);
        let binding = KnownBinding::from_snapshot(&snapshot);
        let mut record = Record {
            version: 4,
            scope: "authenticated_native_material_and_aid_facts_only",
            runtime_epoch: self.scope.epoch,
            observation_generation: context.generation,
            production_read_elapsed_ns,
            presentation_read_elapsed_ns: production_read_elapsed_ns,
            audit_elapsed_ns: super::elapsed(started)?,
            tick: 0,
            tick_content_hash: None,
            opening: Some(opening),
            facts: None,
            aid: None,
            aid_practices: self.custody.practices(),
            economic_summary: self.audit.economic_summary(),
            aid_summary: self.custody.summary(),
            trade_summary: self.audit.trade_summary(),
        };
        let full = PreparedObservation::new(snapshot);
        let evidence = full
            .evidence
            .as_ref()
            .map_err(ToString::to_string)?
            .ok_or("native opening production evidence absent")?;
        if evidence.body_bytes() > policy.production_evidence_bytes {
            return Err("native opening exceeds its production evidence byte limit".into());
        }
        let opening = record
            .opening
            .as_ref()
            .ok_or("native opening facts absent")?;
        let identity = Identity::capture(
            &full.snapshot,
            super::canonical_digest(&opening.material_register_sha256)
                .map_err(|e| e.to_string())?,
            opening.material_register_bytes,
            evidence,
            self.duration,
        )?;
        let prepared = present(full, context, &binding, &mut record)?;
        self.finish(
            context,
            cursor,
            candidate_cursor,
            prepared,
            record,
            identity,
        )
    }

    fn boundary(
        mut self,
        reader: ObserverEconomyReader,
        context: &ObservationContext,
        cursor: &mut Option<ObserverMaterialCursor>,
    ) -> Result<(PreparedObservation, Candidate), String> {
        let mut candidate_cursor = cursor.clone();
        let started = Instant::now();
        let observation = reader
            .committed_material_observation_with_cursor(
                context.campaign,
                context.tick,
                &mut candidate_cursor,
            )
            .map_err(|e| e.to_string())?;
        drop(reader);
        let production_read_elapsed_ns = super::elapsed(started)?;
        let started = Instant::now();
        let register = candidate_cursor
            .as_ref()
            .and_then(ObserverMaterialCursor::current_register)
            .ok_or("native audit authenticated register absent")?;
        let facts = self
            .audit
            .read(&observation, register)
            .map_err(|e| e.to_string())?;
        let aid = self
            .custody
            .read(&observation.accounting, register, self.duration)?;
        let binding = KnownBinding::from_facts(&facts);
        let identity = Identity::capture(
            &observation.snapshot,
            register.digest(),
            register.canonical_bytes().len(),
            observation.production_evidence,
            self.duration,
        )?;
        let mut record = Record {
            version: 4,
            scope: "authenticated_native_material_and_aid_facts_only",
            runtime_epoch: self.scope.epoch,
            observation_generation: context.generation,
            production_read_elapsed_ns,
            presentation_read_elapsed_ns: production_read_elapsed_ns,
            audit_elapsed_ns: super::elapsed(started)?,
            tick: facts.tick,
            tick_content_hash: Some(facts.tick_content_hash.clone()),
            opening: None,
            facts: Some(facts),
            aid: Some(aid),
            aid_practices: self.custody.practices(),
            economic_summary: self.audit.economic_summary(),
            aid_summary: self.custody.summary(),
            trade_summary: self.audit.trade_summary(),
        };
        // Retain only the projection needed by the selected presentation. The
        // receipt owner is released before the small separately authorized read.
        let prepared = PreparedObservation {
            snapshot: observation.snapshot,
            evidence: Ok(Some(observation.production_evidence)),
        };
        drop(observation.accounting);
        let prepared = present(prepared, context, &binding, &mut record)?;
        self.finish(
            context,
            cursor,
            candidate_cursor,
            prepared,
            record,
            identity,
        )
    }

    fn reopened(
        self,
        reader: ObserverEconomyReader,
        context: &ObservationContext,
        cursor: &mut Option<ObserverMaterialCursor>,
    ) -> Result<(PreparedObservation, Candidate), String> {
        let mut candidate_cursor = cursor.clone();
        let started = Instant::now();
        let snapshot = reader
            .snapshot_with_cursor(context.campaign, context.tick, &mut candidate_cursor)
            .map_err(|e| e.to_string())?;
        let production_read_elapsed_ns = super::elapsed(started)?;
        let started = Instant::now();
        let policy = self
            .configuration
            .policy
            .scope(self.scope.campaign, self.scope.foundation);
        let binding = KnownBinding::from_snapshot(&snapshot);
        let full = PreparedObservation::new(snapshot);
        let evidence = full
            .evidence
            .as_ref()
            .map_err(ToString::to_string)?
            .ok_or("native restored production evidence absent")?;
        if evidence.body_bytes() > policy.production_evidence_bytes {
            return Err("native restored production evidence exceeds its byte limit".into());
        }
        let observe = |register: &MaterialWorldRegister| {
            if register.canonical_bytes().len() > policy.material_register_bytes {
                return Err("native restored register exceeds its byte limit".to_string());
            }
            self.custody.recovered_register(register, self.duration)?;
            Identity::capture(
                &full.snapshot,
                register.digest(),
                register.canonical_bytes().len(),
                evidence,
                self.duration,
            )
        };
        let cursor_owner = candidate_cursor
            .as_ref()
            .ok_or("native restored material cursor absent")?;
        let identity = if context.tick == 0 {
            cursor_owner
                .with_opening_register(context.campaign, observe)
                .map_err(|e| e.to_string())??
        } else {
            observe(
                cursor_owner
                    .current_register()
                    .ok_or("native restored register absent")?,
            )?
        };
        self.recovery
            .as_ref()
            .ok_or("native recovery source absent")?
            .verify_identity(&identity)?;
        drop(reader);
        let mut record = Record {
            version: 4,
            scope: "authenticated_native_material_and_aid_facts_only",
            runtime_epoch: self.scope.epoch,
            observation_generation: context.generation,
            production_read_elapsed_ns,
            presentation_read_elapsed_ns: production_read_elapsed_ns,
            audit_elapsed_ns: super::elapsed(started)?,
            tick: context.tick,
            tick_content_hash: full.snapshot.tick_content_hash.clone(),
            opening: None,
            facts: None,
            aid: None,
            aid_practices: self.custody.practices(),
            economic_summary: self.audit.economic_summary(),
            aid_summary: self.custody.summary(),
            trade_summary: self.audit.trade_summary(),
        };
        let prepared = present(full, context, &binding, &mut record)?;
        self.finish(
            context,
            cursor,
            candidate_cursor,
            prepared,
            record,
            identity,
        )
    }

    #[allow(clippy::too_many_arguments)] // One candidate binds presentation and exact private identity.
    fn finish(
        self,
        context: &ObservationContext,
        cursor: &mut Option<ObserverMaterialCursor>,
        candidate_cursor: Option<ObserverMaterialCursor>,
        prepared: PreparedObservation,
        record: Record,
        identity: Identity,
    ) -> Result<(PreparedObservation, Candidate), String> {
        self.configuration
            .policy
            .verify()
            .map_err(|e| e.to_string())?;
        *cursor = candidate_cursor;
        Ok((
            prepared,
            Candidate {
                scope: self.scope,
                context: context.clone(),
                audit: self.audit,
                custody: self.custody,
                record,
                identity,
                recovery: self.recovery,
            },
        ))
    }
}

fn present(
    prepared: PreparedObservation,
    context: &ObservationContext,
    binding: &KnownBinding,
    record: &mut Record,
) -> Result<PreparedObservation, String> {
    if context.perspective == Perspective::FullObserver {
        return Ok(prepared);
    }
    drop(prepared);
    let started = Instant::now();
    let snapshot = ObserverEconomyReader::from_known_env()
        .and_then(|reader| reader.snapshot(context.campaign, context.tick))
        .map_err(|e| e.to_string())?;
    if !binding.agrees(&snapshot) {
        return Err("native player disclosure differs from private audit identity".into());
    }
    record.presentation_read_elapsed_ns = super::elapsed(started)?;
    Ok(PreparedObservation::new(snapshot))
}
