//! Optional facts from the native reader; the supervisor alone qualifies runs.

mod advance;

mod aid;

mod read;

mod recovery;

#[path = "qualification/state.rs"]
mod state;

pub(crate) use state::NativeAudit;
#[cfg(test)]
use state::{admit_tick, publication_matches, RECORD_BYTES};
pub(super) use state::{awaiting_archive, Candidate, Configuration, Work};
use state::{elapsed, hex, write_named_record, KnownBinding, Opening, Record, Scope};

use super::PreparedObservation;
use crate::observer::{ObservationContext, Perspective};
#[cfg(test)]
use crate::observer::{ObserverSession, SessionPhase};
#[cfg(test)]
use babylon_persistence::identity::CampaignId;
#[cfg(test)]
use babylon_persistence::observer_reader::ObserverEconomySnapshot;
use babylon_persistence::observer_reader::{
    ObserverEconomyReader, ObserverMaterialCursor, ObserverVisibility,
};
use babylon_persistence::qualification_audit::policy::canonical_digest;
#[cfg(test)]
use babylon_persistence::qualification_audit::policy::FrozenPolicy;
use babylon_persistence::qualification_audit::MaterialAudit;
use std::time::Instant;

#[cfg(test)]
mod tests {
    use super::*;
    use aid::Custody;
    use babylon_kernel::clock::CampaignDuration;
    use fs::Permissions;
    use std::fs;
    use std::os::unix::fs::PermissionsExt;
    use std::path::PathBuf;
    use uuid::Uuid;

    pub(in crate::observer_io) struct Directory(pub(in crate::observer_io) PathBuf);
    impl Directory {
        pub(in crate::observer_io) fn new() -> Self {
            let path =
                std::env::temp_dir().join(format!("babylon-native-audit-{}", Uuid::new_v4()));
            fs::create_dir(&path).expect("the fixture directory is creatable");
            fs::set_permissions(&path, Permissions::from_mode(0o700))
                .expect("the fixture file mode is settable");
            Self(path)
        }
    }
    impl Drop for Directory {
        fn drop(&mut self) {
            fs::remove_dir_all(&self.0).expect("the fixture directory exists before removal");
        }
    }

    #[test]
    fn boundary_records_are_exact_atomic_and_conflicting_records_are_preserved() {
        let directory = Directory::new();
        state::write_record(&directory.0, 1, b"original\n")
            .expect("the fixture sink accepts the authored bytes");
        state::write_record(&directory.0, 1, b"original\n")
            .expect("the fixture sink accepts the authored bytes");
        assert!(state::write_record(&directory.0, 1, b"changed\n").is_err());
        assert_eq!(
            fs::read(directory.0.join("material-1.json"))
                .expect("the fixture reader returns its authored facts"),
            b"original\n"
        );
        assert_eq!(
            fs::read_dir(&directory.0)
                .expect("the fixture directory is readable")
                .count(),
            1
        );
        assert!(state::write_record(&directory.0, 2, &vec![0; RECORD_BYTES + 1]).is_err());
        assert!(!directory.0.join("material-2.json").exists());
    }

    #[test]
    fn failed_publication_and_changed_directory_publish_nothing() {
        let directory = Directory::new();
        fs::create_dir(directory.0.join("material-1.json"))
            .expect("the fixture directory is creatable");
        assert!(state::write_record(&directory.0, 1, b"facts\n").is_err());
        assert_eq!(
            fs::read_dir(&directory.0)
                .expect("the fixture directory is readable")
                .count(),
            1
        );
        fs::set_permissions(&directory.0, Permissions::from_mode(0o755))
            .expect("the fixture file mode is settable");
        assert!(state::write_record(&directory.0, 2, b"facts\n").is_err());
        assert!(!directory.0.join("material-2.json").exists());
    }

    #[test]
    fn native_boundary_continuity_refuses_missing_prefix_and_does_not_refold_refresh() {
        assert!(admit_tick(0, 1, 52).expect("the fixture admits the authored tick"));
        assert!(!admit_tick(1, 1, 52).expect("the fixture admits the authored tick"));
        assert!(admit_tick(0, 2, 52).is_err());
        assert!(admit_tick(2, 1, 52).is_err());
        assert!(admit_tick(52, 53, 52).is_err());
    }

    pub(in crate::observer_io) fn fixture(directory: &Directory) -> (NativeAudit, ObserverSession) {
        let bytes =
            include_bytes!("../../../../../contracts/national_storage_qualification_v6.json");
        let path = directory.0.join("policy.json");
        fs::write(&path, bytes).expect("the fixture sink accepts the authored bytes");
        let campaign = CampaignId::from_uuid(Uuid::from_u128(1));
        let policy =
            FrozenPolicy::open(&path, babylon_kernel::content_digest::sha256_of(bytes), 52)
                .expect("the fixture opens the authored source");
        let audit = NativeAudit {
            configuration: Configuration {
                campaign,
                policy,
                directory: directory.0.clone(),
            },
            scope: None,
            audit: None,
            custody: Custody::default(),
            boundary: None,
            recovery: None,
            advance: None,
        };
        let mut session = ObserverSession::new(campaign);
        session.connected_fixture();
        session.ready(1, Some("b".repeat(64)));
        session.foundation_digest = Some("0a".repeat(32));
        session.duration = Some(CampaignDuration::Continuous);
        (audit, session)
    }

    #[test]
    fn opening_is_authenticated_before_the_first_accepted_aid_offer() {
        let directory = Directory::new();
        let (mut audit, mut session) = fixture(&directory);
        session.viewed_tick = 0;
        session.durable_tick = 0;
        session.content_hash = None;
        assert!(audit
            .begin(&session)
            .expect("the fixture begins the authored transaction")
            .is_some());
        assert!(audit.audit.is_none());
        assert_eq!(
            fs::read_dir(&directory.0)
                .expect("the fixture directory is readable")
                .count(),
            1
        );
    }

    #[test]
    fn native_reopen_requires_an_authenticated_boundary_and_an_exact_sent_request() {
        use babylon_persistence::runtime_session::{RuntimeSessionRequest, RuntimeSessionTarget};
        let directory = Directory::new();
        let (mut audit, mut session) = fixture(&directory);
        audit
            .begin(&session)
            .expect("the fixture begins the authored transaction");
        session.archive_verified_tick = session.durable_tick;
        let original_scope = session
            .runtime_scope()
            .expect("the fixture runtime scope exists")
            .clone();
        session
            .queue_campaign(RuntimeSessionTarget::Open {
                campaign_id: session.campaign.as_uuid().to_string(),
            })
            .expect("the fixture call `queue_campaign` succeeds for the authored inputs");
        let request = session
            .pending_switch_request()
            .expect("the fixture call `pending_switch_request` succeeds for the authored inputs");
        assert!(audit.stage_reopen(&session, &request).is_err());
        assert!(audit.recovery.is_none());
        let RuntimeSessionRequest::Switch { request_id, .. } = request else {
            panic!()
        };
        session.switch_sent();
        let mut new_scope = original_scope.clone();
        new_scope.epoch += 1;
        session
            .switching(request_id, &original_scope, new_scope.clone())
            .expect("the fixture call `switching` succeeds for the authored inputs");
        assert!(audit
            .switching(request_id, &original_scope, &new_scope)
            .is_err());
        assert_eq!(
            audit
                .scope
                .as_ref()
                .expect("the fixture set the optional field before this read")
                .epoch,
            original_scope.epoch
        );
        assert_eq!(
            fs::read_dir(&directory.0)
                .expect("the fixture directory is readable")
                .count(),
            1
        );
    }

    #[test]
    fn qualification_refuses_changed_policy_and_scope_before_reading() {
        let directory = Directory::new();
        let (mut audit, mut session) = fixture(&directory);
        assert!(audit
            .begin(&session)
            .expect("the fixture begins the authored transaction")
            .is_some());
        session.viewed_tick = 0;
        // Inspecting historical tick 0 at a positive durable tail does not fold.
        assert!(audit
            .begin(&session)
            .expect("the fixture begins the authored transaction")
            .is_none());
        session.viewed_tick = 1;
        session.perspective = Perspective::PlayerKnowledge;
        assert!(audit
            .begin(&session)
            .expect("the fixture begins the authored transaction")
            .is_some());
        session.perspective = Perspective::FullObserver;
        session.foundation_digest = Some("0b".repeat(32));
        assert!(audit.begin(&session).is_err());
        session.foundation_digest = Some("0a".repeat(32));
        fs::write(directory.0.join("policy.json"), b"{}")
            .expect("the fixture sink accepts the authored bytes");
        assert!(audit.begin(&session).is_err());
        assert!(audit.audit.is_none());
        assert_eq!(
            fs::read_dir(&directory.0)
                .expect("the fixture directory is readable")
                .count(),
            1
        );
    }

    #[test]
    fn publication_requires_installed_generation_campaign_epoch_and_identity() {
        let directory = Directory::new();
        let (mut audit, mut session) = fixture(&directory);
        audit
            .begin(&session)
            .expect("the fixture begins the authored transaction");
        let scope = audit
            .scope
            .as_ref()
            .expect("the fixture set the optional field before this read");
        let context = session.context();
        let hash = "b".repeat(64);
        assert!(!publication_matches(
            &session,
            scope,
            &context,
            1,
            Some(&hash)
        ));
        assert!(session.installed(&context));
        assert!(publication_matches(
            &session,
            scope,
            &context,
            1,
            Some(&hash)
        ));
        assert!(!publication_matches(
            &session,
            scope,
            &context,
            2,
            Some(&hash)
        ));
        assert!(!publication_matches(
            &session,
            scope,
            &context,
            1,
            Some(&"c".repeat(64))
        ));
        let mut wrong_scope = scope.clone();
        wrong_scope.epoch += 1;
        assert!(!publication_matches(
            &session,
            &wrong_scope,
            &context,
            1,
            Some(&hash)
        ));
        wrong_scope = scope.clone();
        wrong_scope.campaign = CampaignId::from_uuid(Uuid::from_u128(2));
        assert!(!publication_matches(
            &session,
            &wrong_scope,
            &context,
            1,
            Some(&hash)
        ));
        session.foundation_digest = Some("0b".repeat(32));
        assert!(!publication_matches(
            &session,
            scope,
            &context,
            1,
            Some(&hash)
        ));
        session.foundation_digest = Some("0a".repeat(32));
        session.generation += 1;
        assert!(!publication_matches(
            &session,
            scope,
            &context,
            1,
            Some(&hash)
        ));
        assert_eq!(
            fs::read_dir(&directory.0)
                .expect("the fixture directory is readable")
                .count(),
            1
        );
    }

    #[test]
    fn native_wayne_knowledge_view_keeps_its_visibility_during_private_audit() {
        let directory = Directory::new();
        let (mut audit, mut session) = fixture(&directory);
        session.perspective = Perspective::PlayerKnowledge;
        assert!(audit
            .begin(&session)
            .expect("the fixture begins the authored transaction")
            .is_some());
        assert_eq!(session.perspective, Perspective::PlayerKnowledge);
        assert!(audit.audit.is_none());
    }

    #[test]
    fn large_qualified_reads_wait_for_the_current_archive_acknowledgement() {
        let directory = Directory::new();
        let (_, mut session) = fixture(&directory);
        assert!(awaiting_archive(&session, true));
        assert!(!awaiting_archive(&session, false));
        session.archive_verified_tick = 1;
        assert!(!awaiting_archive(&session, true));
        session.archive_verified_tick = 0;
        session.viewed_tick = 0;
        assert!(!awaiting_archive(&session, true));
    }

    #[test]
    fn player_disclosure_binds_private_identity_without_exposing_material_facts() {
        let binding = KnownBinding {
            campaign: Uuid::from_u128(1).to_string(),
            tick: 1,
            foundation: "a".repeat(64),
            hash: Some("b".repeat(64)),
            envelope: Some("c".repeat(64)),
        };
        let mut snapshot = ObserverEconomySnapshot {
            campaign_id: binding.campaign.clone(),
            resolve_tick: 1,
            foundation_digest: binding.foundation.clone(),
            tick_content_hash: binding.hash.clone(),
            envelope_digest: binding.envelope.clone(),
            nominal_world_hash: None,
            visibility: ObserverVisibility::KnownPreview,
            counties: vec![],
            production: None,
        };
        assert!(binding.agrees(&snapshot));
        snapshot.envelope_digest = Some("d".repeat(64));
        assert!(!binding.agrees(&snapshot));
        snapshot.envelope_digest = binding.envelope.clone();
        snapshot.nominal_world_hash = Some("e".repeat(64));
        assert!(!binding.agrees(&snapshot));
        snapshot.nominal_world_hash = None;
        snapshot.visibility = ObserverVisibility::FullObserver;
        assert!(!binding.agrees(&snapshot));
    }

    #[test]
    fn stale_qualified_read_drains_before_another_reconstruction_can_start() {
        use super::super::{ObservationCache, ObservationRead, PendingObservation};
        use crate::observer_ui::ObserverFrame;
        use bevy::prelude::{App, MinimalPlugins};
        use bevy::tasks::AsyncComputeTaskPool;

        let directory = Directory::new();
        let (audit, mut session) = fixture(&directory);
        session.archive_verified_tick = 1;
        let stale = session.context();
        session.generation += 1;
        let mut app = App::new();
        app.add_plugins(MinimalPlugins)
            .insert_resource(session)
            .insert_resource(audit)
            .init_resource::<ObservationCache>()
            .init_resource::<ObserverFrame>()
            .add_systems(
                bevy::prelude::Update,
                super::super::runtime::start_observation,
            );
        let task = AsyncComputeTaskPool::get()
            .spawn(async { bevy::tasks::futures_lite::future::pending::<ObservationRead>().await });
        app.insert_resource(PendingObservation(Some((stale.clone(), task))));
        for _ in 0..2 {
            app.update();
        }
        assert_eq!(
            app.world()
                .resource::<PendingObservation>()
                .0
                .as_ref()
                .expect("the fixture set the optional field before this read")
                .0,
            stale
        );
        assert_eq!(
            app.world().resource::<ObserverSession>().phase,
            SessionPhase::Loading
        );
        assert_eq!(
            fs::read_dir(&directory.0)
                .expect("the fixture directory is readable")
                .count(),
            1
        );
    }
}
