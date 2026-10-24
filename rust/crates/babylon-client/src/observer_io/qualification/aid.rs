//! Custody of actual status, review, submission and accepted responses.
use super::{Configuration, Scope};
use crate::observer::{ObservationContext, ObserverSession};
use babylon_kernel::clock::CampaignDuration;
use babylon_persistence::observer_reader::CommittedMaterialReceipts;
use babylon_persistence::qualification_audit::aid;
use babylon_persistence::qualification_audit::aid::{
    Accepted, Audit, Boundary, MaterialWorldRegister,
};
use babylon_persistence::runtime_session::{
    OrganizerChoice, OrganizerCommand, OrganizerCommitment, OrganizerPreview, OrganizerSnapshot,
    RuntimeSessionRequest, RuntimeSessionScope,
};

use aid::Summary;
use serde::Serialize;
use serde_json::Value;

#[derive(Clone, Default)]
pub(super) struct Custody {
    audit: Audit,
    material: Option<OrganizerSnapshot>,
    status: Option<(ObservationContext, OrganizerSnapshot)>,
    review: Option<Review>,
    awaiting_status: Option<OrganizerCommitment>,
    pub(super) revision: u64,
}

#[derive(Clone, Serialize, PartialEq, Eq)]
struct Review {
    #[serde(skip_serializing)]
    context: ObservationContext,
    observation_generation: u64,
    scope: RuntimeSessionScope,
    request_id: u64,
    command: OrganizerCommand,
    admission: OrganizerPreview,
    before: OrganizerSnapshot,
}

#[derive(Serialize)]
struct Original<'a> {
    version: u8,
    scope: &'static str,
    foundation_sha256: String,
    policy_sha256: String,
    tick_content_hash: Option<String>,
    review: &'a Review,
    commitment: &'a OrganizerCommitment,
}

fn is_aid(choice: OrganizerChoice) -> bool {
    matches!(
        choice,
        OrganizerChoice::LocalAid | OrganizerChoice::RemoteAid
    )
}

#[cfg(test)]
pub(super) fn disclosed_control(session: &ObserverSession, material: OrganizerSnapshot) -> Custody {
    Custody {
        material: Some(material.clone()),
        status: Some((session.context(), material)),
        ..Custody::default()
    }
}

impl Custody {
    pub(super) fn is_open(&self) -> bool {
        self.material.is_some()
    }

    pub(super) fn recovery_status(
        &self,
        session: &ObserverSession,
    ) -> Result<OrganizerSnapshot, String> {
        let (context, actual) = self
            .status
            .as_ref()
            .ok_or("native recovery original organizer status absent")?;
        if self.review.is_some()
            || self.awaiting_status.is_some()
            || !session.accepts(context)
            || context.tick != session.durable_tick
        {
            return Err(
                "native recovery has an unresolved submission or stale organizer status".into(),
            );
        }
        matches_source(
            self.material
                .as_ref()
                .ok_or("native recovery material source absent")?,
            actual,
        )?;
        Ok(actual.clone())
    }

    pub(super) fn recovered_register(
        &self,
        register: &MaterialWorldRegister,
        duration: CampaignDuration,
    ) -> Result<(), String> {
        let actual = aid::material_disclosure(register, duration).map_err(|e| e.to_string())?;
        if self.material.as_ref() != Some(&actual) {
            return Err("native restored aid material differs from its original disclosure".into());
        }
        Ok(())
    }

    pub(super) fn open(
        &mut self,
        register: &MaterialWorldRegister,
        scope: &Scope,
        duration: CampaignDuration,
    ) -> Result<(), String> {
        if register.organizer_config().map(|c| c.campaign_id)
            != Some(*scope.campaign.canonical_bytes())
        {
            return Err("native aid opening campaign differs".into());
        }
        let material = aid::material_disclosure(register, duration).map_err(|e| e.to_string())?;
        self.audit
            .open(register, &material)
            .map_err(|e| e.to_string())?;
        self.material = Some(material);
        Ok(())
    }

    pub(super) fn status(
        &mut self,
        session: &ObserverSession,
        snapshot: OrganizerSnapshot,
    ) -> Result<(), String> {
        if snapshot.view.period != session.durable_tick {
            return Err("native aid status differs from authenticated material disclosure".into());
        }
        if self.awaiting_status.as_ref().is_some_and(|accepted| {
            snapshot.view.period == accepted.command.expected_period
                && snapshot.pending.as_ref() != Some(accepted)
        }) {
            return Err(
                "native organizer status lost its actual accepted pending commitment".into(),
            );
        }
        if let Some(source) = self
            .material
            .as_ref()
            .filter(|s| s.view.period == snapshot.view.period)
        {
            matches_source(source, &snapshot)?;
        }
        self.status = Some((session.context(), snapshot));
        self.awaiting_status = None;
        Ok(())
    }

    /// Install only computed material/fold state. A status or submission received
    /// during the asynchronous read remains owned by the ordinary control path.
    pub(super) fn install(&mut self, candidate: Self) -> Result<(), String> {
        if self.revision != candidate.revision {
            return Err("native aid acceptance changed during boundary reconstruction".into());
        }
        let source = candidate
            .material
            .as_ref()
            .ok_or("native aid material source absent")?;
        if let Some((_, status)) = self
            .status
            .as_ref()
            .filter(|(_, s)| s.view.period == source.view.period)
        {
            matches_source(source, status)?;
        }
        self.status = self
            .status
            .take()
            .filter(|(_, s)| s.view.period == source.view.period);
        self.audit = candidate.audit;
        self.material = candidate.material;
        Ok(())
    }

    pub(super) fn stage(
        &mut self,
        session: &ObserverSession,
        request: &RuntimeSessionRequest,
        preview: Option<&OrganizerPreview>,
    ) -> Result<(), String> {
        let RuntimeSessionRequest::SubmitOrganizer {
            scope,
            request_id,
            command,
            ..
        } = request
        else {
            return Ok(());
        };
        if !is_aid(command.choice) {
            return Ok(());
        }
        let (context, before) = self
            .status
            .as_ref()
            .ok_or("native aid original status absent")?;
        matches_source(
            self.material
                .as_ref()
                .ok_or("native aid original opening absent")?,
            before,
        )?;
        if !session.accepts(context)
            || context.tick != session.durable_tick
            || session.runtime_scope() != Some(scope)
            || before.pending.is_some()
            || command.expected_period != before.view.period
        {
            return Err("native aid original review context differs".into());
        }
        let review = Review {
            context: context.clone(),
            observation_generation: context.generation,
            scope: scope.clone(),
            request_id: *request_id,
            command: command.clone(),
            admission: preview
                .cloned()
                .ok_or("native aid original preview absent")?,
            before: before.clone(),
        };
        if self.review.as_ref().is_some_and(|prior| *prior != review) {
            return Err("native aid already owns a different submitted review".into());
        }
        self.review = Some(review);
        Ok(())
    }

    pub(super) fn accepted(
        &mut self,
        configuration: &Configuration,
        scope: &Scope,
        session: &ObserverSession,
        request_id: u64,
        commitment: &OrganizerCommitment,
    ) -> Result<(), String> {
        let (context, status) = self
            .status
            .as_ref()
            .ok_or("native accepted organizer original status absent")?;
        if !session.accepts(context) || status.view.period != commitment.command.expected_period {
            return Err("native accepted organizer source context differs".into());
        }
        if !is_aid(commitment.command.choice) {
            self.awaiting_status = Some(commitment.clone());
            return Ok(());
        }
        let review = self
            .review
            .as_ref()
            .ok_or("native aid submitted review absent")?;
        if review.request_id != request_id
            || review.command != commitment.command
            || session.runtime_scope() != Some(&review.scope)
            || review.context.campaign != scope.campaign
            || session.durable_tick != review.context.tick
        {
            return Err("native aid acceptance differs from its original submission".into());
        }
        let mut candidate = self.audit.clone();
        candidate
            .accept(
                Accepted::capture(commitment, &review.admission, &review.before)
                    .map_err(|e| e.to_string())?,
            )
            .map_err(|e| e.to_string())?;
        let revision = self
            .revision
            .checked_add(1)
            .ok_or("native aid revision overflow")?;
        configuration.policy.verify().map_err(|e| e.to_string())?;
        let policy = configuration.policy.scope(scope.campaign, scope.foundation);
        let original = Original {
            version: 1,
            scope: "actual_native_aid_acceptance_witness_only",
            foundation_sha256: super::hex(&scope.foundation),
            policy_sha256: super::hex(&policy.policy),
            tick_content_hash: session.content_hash.clone(),
            review,
            commitment,
        };
        let mut bytes =
            serde_json::to_vec(&original).map_err(|_| "native aid witness encoding failed")?;
        bytes.push(b'\n');
        super::write_named_record(
            &configuration.directory,
            &format!("aid-{}", super::hex(&commitment.commitment_id)),
            &bytes,
        )?;
        self.audit = candidate;
        self.revision = revision;
        self.awaiting_status = Some(commitment.clone());
        self.review = None;
        Ok(())
    }

    pub(super) fn read(
        &mut self,
        admitted: &CommittedMaterialReceipts,
        register: &MaterialWorldRegister,
        duration: CampaignDuration,
    ) -> Result<Boundary, String> {
        let after = aid::material_disclosure(register, duration).map_err(|e| e.to_string())?;
        let fact = self
            .audit
            .read(admitted, register, &after)
            .map_err(|e| e.to_string())?;
        self.material = Some(after);
        self.status = None;
        Ok(fact)
    }

    pub(super) fn practices(&self) -> Value {
        self.audit.practice_report()
    }

    pub(super) fn summary(&self) -> Summary {
        self.audit.summary()
    }

    pub(super) fn refused(&mut self, scope: &RuntimeSessionScope, request_id: u64) {
        if self
            .review
            .as_ref()
            .is_some_and(|review| review.request_id == request_id && review.scope == *scope)
        {
            self.review = None;
        }
    }
}

fn matches_source(source: &OrganizerSnapshot, snapshot: &OrganizerSnapshot) -> Result<(), String> {
    let mut committed = snapshot.clone();
    // Mutable pending protocol commands have separate original response custody.
    committed.pending = None;
    if committed != *source {
        return Err("native aid status differs from authenticated material disclosure".into());
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use babylon_persistence::identity::CampaignId;
    use babylon_persistence::runtime_session::OrganizerAidKind;
    use uuid::Uuid;

    fn fixture() -> (
        Custody,
        ObserverSession,
        OrganizerSnapshot,
        RuntimeSessionRequest,
        OrganizerPreview,
    ) {
        let snapshot: OrganizerSnapshot = serde_json::from_str(include_str!(
            "../../../../babylon-persistence/tests/fixtures/national_organizer_opening_v11.json"
        ))
        .expect("the authored JSON matches the declared schema");
        let mut session = ObserverSession::new(CampaignId::from_uuid(Uuid::from_u128(1)));
        session.connected_fixture();
        session.ready(0, None);
        session.duration = Some(snapshot.duration);
        let command = OrganizerCommand {
            campaign_id: *session.campaign.canonical_bytes(),
            actor_id: snapshot.view.actor_id,
            authority_id: snapshot.view.authority_id,
            expected_period: 0,
            content_digest: snapshot.view.content_digest,
            resource_digest: snapshot.view.resource_digest,
            nonce: [11; 16],
            choice: OrganizerChoice::LocalAid,
        };
        let preview = OrganizerPreview {
            choice: OrganizerChoice::LocalAid,
            current_period: 0,
            resolves_period: 1,
            available_hours: snapshot.view.available_hours,
            required_hours: snapshot
                .aid
                .iter()
                .find(|r| r.kind == OrganizerAidKind::Local)
                .expect("the fixture holds the searched element")
                .coordination_hours,
            replaces_standing_work: snapshot.view.standing.authorized,
            refusal: None,
            observations: vec![],
        };
        let request = RuntimeSessionRequest::SubmitOrganizer {
            protocol_version:
                babylon_persistence::runtime_session::RUNTIME_SESSION_PROTOCOL_VERSION,
            scope: session
                .runtime_scope()
                .expect("the fixture runtime scope exists")
                .clone(),
            request_id: 7,
            command,
        };
        (Custody::default(), session, snapshot, request, preview)
    }

    #[test]
    fn status_arriving_during_opening_survives_the_asynchronous_material_install() {
        let (mut custody, session, snapshot, request, preview) = fixture();
        custody
            .status(&session, snapshot.clone())
            .expect("the fixture command reports its status");
        assert!(custody.stage(&session, &request, Some(&preview)).is_err());
        let candidate = Custody {
            material: Some(snapshot.clone()),
            ..Custody::default()
        };
        custody
            .install(candidate)
            .expect("the fixture call `install` succeeds for the authored inputs");
        assert_eq!(
            custody
                .status
                .as_ref()
                .expect("the fixture set the optional field before this read")
                .1,
            snapshot
        );
        custody
            .stage(&session, &request, Some(&preview))
            .expect("the fixture call `stage` succeeds for the authored inputs");
        assert!(custody.review.is_some());
    }

    #[test]
    fn exact_submission_retry_preserves_the_original_status_and_review() {
        let (mut custody, session, snapshot, request, preview) = fixture();
        custody.material = Some(snapshot.clone());
        custody
            .status(&session, snapshot)
            .expect("the fixture command reports its status");
        custody
            .stage(&session, &request, Some(&preview))
            .expect("the fixture call `stage` succeeds for the authored inputs");
        let original = custody.review.clone().expect("the fixture value clones");
        custody
            .stage(&session, &request, Some(&preview))
            .expect("the fixture call `stage` succeeds for the authored inputs");
        let mut changed = preview;
        changed.available_hours += 1;
        assert!(custody.stage(&session, &request, Some(&changed)).is_err());
        assert!(custody.stage(&session, &request, None).is_err());
        assert!(
            custody
                .review
                .as_ref()
                .expect("the fixture set the optional field before this read")
                == &original
        );
    }

    #[test]
    fn changed_offer_or_observation_cannot_replace_the_original_source() {
        let (mut custody, mut session, snapshot, request, preview) = fixture();
        custody.material = Some(snapshot.clone());
        custody
            .status(&session, snapshot.clone())
            .expect("the fixture command reports its status");
        let mut changed = snapshot;
        changed.aid[0].payer_cash += 1;
        assert!(custody.status(&session, changed).is_err());
        session.generation += 1;
        assert!(custody.stage(&session, &request, Some(&preview)).is_err());
        assert!(custody.review.is_none());
    }

    #[test]
    fn late_candidate_cannot_erase_an_acceptance_or_its_submitted_review() {
        let (mut custody, session, snapshot, request, preview) = fixture();
        custody.material = Some(snapshot.clone());
        custody
            .status(&session, snapshot)
            .expect("the fixture command reports its status");
        custody
            .stage(&session, &request, Some(&preview))
            .expect("the fixture call `stage` succeeds for the authored inputs");
        let original = custody.review.clone();
        let mut candidate = custody.clone();
        candidate.status = None;
        candidate.review = None;
        custody
            .install(candidate.clone())
            .expect("the fixture call `install` succeeds for the authored inputs");
        assert!(custody.review == original);
        custody.revision = 1;
        assert!(custody.install(candidate).is_err());
        assert_eq!(custody.revision, 1);
        assert!(custody.review == original);
    }

    #[test]
    fn acknowledged_refusal_releases_only_its_own_review_for_a_fresh_submission() {
        let (mut custody, session, snapshot, mut request, preview) = fixture();
        custody.material = Some(snapshot.clone());
        custody
            .status(&session, snapshot)
            .expect("the fixture command reports its status");
        custody
            .stage(&session, &request, Some(&preview))
            .expect("the fixture call `stage` succeeds for the authored inputs");
        let scope = session
            .runtime_scope()
            .expect("the fixture runtime scope exists");
        custody.refused(scope, 99);
        assert!(custody.review.is_some());
        let mut crossed = scope.clone();
        crossed.epoch += 1;
        custody.refused(&crossed, 7);
        assert!(custody.review.is_some());
        custody.refused(scope, 7);
        assert!(custody.review.is_none());
        let RuntimeSessionRequest::SubmitOrganizer {
            request_id,
            command,
            ..
        } = &mut request
        else {
            panic!("submit fixture")
        };
        *request_id = 8;
        command.nonce = [12; 16];
        custody
            .stage(&session, &request, Some(&preview))
            .expect("the fixture call `stage` succeeds for the authored inputs");
        assert_eq!(
            custody
                .review
                .as_ref()
                .expect("the fixture set the optional field before this read")
                .request_id,
            8
        );
    }
}
