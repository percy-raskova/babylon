//! Bounded parent-pipe runtime control. Only empty-action next-week commits exist.

use std::io::{BufRead, Read as _, Write};

use babylon_bsl::structural_verbs::CollectingSink;
use babylon_practice_contract::ordered_action_v1::OrderedPracticeActionBatchV1;
use postgres::{Config, NoTls};
use serde::{Deserialize, Serialize};

use crate::{
    material_runtime::{DurableMaterialRuntimeV3, MaterialRuntimeErrorV3},
    michigan_content::{admit_michigan_content_v1, MichiganContentPresetV1},
    michigan_economy::digest_hex,
    michigan_material::MichiganDeliveryPresetV1,
    CampaignId, CompositeArchiveDossierProducerV1, CountyDossierProducerV1, PlaceDossierProducerV1,
    SemanticArchiveStoreV1,
};

pub const RUNTIME_SESSION_PROTOCOL_VERSION_V2: u16 = 2;
pub const RUNTIME_SESSION_MAX_LINE_BYTES_V2: usize = 4096;

/// Identity of exactly one acknowledged tail; tick zero has no commit hash.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct RuntimeSessionTailV2 {
    pub resolve_tick: u64,
    pub tick_content_hash: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case", deny_unknown_fields)]
pub enum RuntimeSessionRequestV2 {
    Advance {
        protocol_version: u16,
        campaign_id: String,
        request_id: u64,
        expected_tail: RuntimeSessionTailV2,
    },
    RefreshArchive {
        protocol_version: u16,
        campaign_id: String,
        request_id: u64,
    },
    Stop {
        protocol_version: u16,
        campaign_id: String,
        request_id: u64,
    },
}

impl RuntimeSessionRequestV2 {
    fn header(&self) -> (u16, &str, u64) {
        match self {
            Self::Advance {
                protocol_version,
                campaign_id,
                request_id,
                ..
            }
            | Self::RefreshArchive {
                protocol_version,
                campaign_id,
                request_id,
            }
            | Self::Stop {
                protocol_version,
                campaign_id,
                request_id,
            } => (*protocol_version, campaign_id, *request_id),
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum RuntimeSessionErrorCodeV2 {
    InvalidRequest,
    UnsupportedVersion,
    CampaignMismatch,
    StaleExpectedTail,
    CommitRefused,
    ArchiveRefused,
    StorageRefused,
    StorageBusy,
    StorageCanceled,
    ScenarioMismatch,
    PipeFailure,
    HorizonComplete,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case", deny_unknown_fields)]
pub enum RuntimeSessionResponseV2 {
    Ready {
        protocol_version: u16,
        campaign_id: String,
        foundation_digest: String,
        tail: RuntimeSessionTailV2,
    },
    Committed {
        request_id: u64,
        campaign_id: String,
        tail: RuntimeSessionTailV2,
    },
    ArchiveProgress {
        request_id: Option<u64>,
        campaign_id: String,
        durable_tick: u64,
        verified_tick: u64,
        retention_ready: bool,
    },
    Error {
        request_id: Option<u64>,
        code: RuntimeSessionErrorCodeV2,
        tail: RuntimeSessionTailV2,
    },
    Stopped {
        request_id: u64,
    },
}

impl std::fmt::Display for RuntimeSessionErrorCodeV2 {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "runtime session refused: {self:?}")
    }
}
impl std::error::Error for RuntimeSessionErrorCodeV2 {}

#[derive(Clone, Copy)]
struct ArchiveMaintenanceProgress {
    verified_tick: u64,
    retention_ready: bool,
}

trait SessionBackend {
    fn tail(&self) -> RuntimeSessionTailV2;
    fn advance(
        &mut self,
        expected: &RuntimeSessionTailV2,
    ) -> Result<RuntimeSessionTailV2, RuntimeSessionErrorCodeV2>;
    fn sweep(&mut self) -> Result<ArchiveMaintenanceProgress, RuntimeSessionErrorCodeV2>;
}

struct DurableBackend {
    config: Config,
    campaign: CampaignId,
    runtime: DurableMaterialRuntimeV3,
    tail: RuntimeSessionTailV2,
}
impl SessionBackend for DurableBackend {
    fn tail(&self) -> RuntimeSessionTailV2 {
        self.tail.clone()
    }
    fn advance(
        &mut self,
        expected: &RuntimeSessionTailV2,
    ) -> Result<RuntimeSessionTailV2, RuntimeSessionErrorCodeV2> {
        if expected != &self.tail || durable_tail(&self.config, self.campaign)? != self.tail {
            return Err(RuntimeSessionErrorCodeV2::StaleExpectedTail);
        }
        let tick = self
            .tail
            .resolve_tick
            .checked_add(1)
            .ok_or(RuntimeSessionErrorCodeV2::CommitRefused)?;
        let actions = OrderedPracticeActionBatchV1::empty(
            self.runtime
                .session()
                .graph_session()
                .session_identity()
                .clone(),
            tick,
        )
        .map_err(|_| RuntimeSessionErrorCodeV2::CommitRefused)?;
        let receipt = self
            .runtime
            .advance_and_commit(&mut CollectingSink::default(), &actions)
            .map_err(|error| match error {
                MaterialRuntimeErrorV3::Replay(
                    babylon_tick::material_replay::MaterialReplayErrorV3::Horizon,
                ) => RuntimeSessionErrorCodeV2::HorizonComplete,
                MaterialRuntimeErrorV3::DatabaseLockRefused(_) => {
                    RuntimeSessionErrorCodeV2::StorageBusy
                }
                MaterialRuntimeErrorV3::DatabaseStatementCanceled(_) => {
                    RuntimeSessionErrorCodeV2::StorageCanceled
                }
                _ => RuntimeSessionErrorCodeV2::CommitRefused,
            })?;
        self.tail = RuntimeSessionTailV2 {
            resolve_tick: receipt.resolve_tick(),
            tick_content_hash: Some(digest_hex(receipt.tick_content_hash().as_bytes())),
        };
        Ok(self.tail.clone())
    }
    fn sweep(&mut self) -> Result<ArchiveMaintenanceProgress, RuntimeSessionErrorCodeV2> {
        let county = CountyDossierProducerV1::try_new(&self.config)
            .map_err(|_| RuntimeSessionErrorCodeV2::ArchiveRefused)?;
        let place = PlaceDossierProducerV1::try_new(&self.config)
            .map_err(|_| RuntimeSessionErrorCodeV2::ArchiveRefused)?;
        let producer =
            CompositeArchiveDossierProducerV1::new(vec![Box::new(county), Box::new(place)]);
        let report = crate::ArchiveWorkerV1::new(&self.config)
            .sweep_once(self.campaign, &producer)
            .map_err(|_| RuntimeSessionErrorCodeV2::ArchiveRefused)?;
        Ok(ArchiveMaintenanceProgress {
            verified_tick: report.verified_tick(),
            retention_ready: report.retention_ready(),
        })
    }
}

fn durable_tail(
    config: &Config,
    campaign: CampaignId,
) -> Result<RuntimeSessionTailV2, RuntimeSessionErrorCodeV2> {
    let bounded = crate::material_runtime::bounded_material_writer_config_v3(config)
        .map_err(|_| RuntimeSessionErrorCodeV2::StorageRefused)?;
    let mut client = bounded
        .connect(NoTls)
        .map_err(|_| RuntimeSessionErrorCodeV2::StorageRefused)?;
    let row = client.query_opt("SELECT resolve_tick, tick_content_hash FROM babylon_state.tick_commit WHERE campaign_id = $1 ORDER BY resolve_tick DESC LIMIT 1", &[campaign.as_uuid()]).map_err(|_| RuntimeSessionErrorCodeV2::StorageRefused)?;
    match row {
        None => Ok(RuntimeSessionTailV2 {
            resolve_tick: 0,
            tick_content_hash: None,
        }),
        Some(row) => {
            let tick: i64 = row
                .try_get(0)
                .map_err(|_| RuntimeSessionErrorCodeV2::StorageRefused)?;
            let hash: Vec<u8> = row
                .try_get(1)
                .map_err(|_| RuntimeSessionErrorCodeV2::StorageRefused)?;
            if tick <= 0 || hash.len() != 32 {
                return Err(RuntimeSessionErrorCodeV2::StorageRefused);
            }
            Ok(RuntimeSessionTailV2 {
                resolve_tick: u64::try_from(tick)
                    .map_err(|_| RuntimeSessionErrorCodeV2::StorageRefused)?,
                tick_content_hash: Some(digest_hex(&hash)),
            })
        }
    }
}

fn emit(
    output: &mut impl Write,
    response: &RuntimeSessionResponseV2,
) -> Result<(), RuntimeSessionErrorCodeV2> {
    let mut bytes =
        serde_json::to_vec(response).map_err(|_| RuntimeSessionErrorCodeV2::PipeFailure)?;
    if bytes.len() >= RUNTIME_SESSION_MAX_LINE_BYTES_V2 {
        return Err(RuntimeSessionErrorCodeV2::PipeFailure);
    }
    bytes.push(b'\n');
    output
        .write_all(&bytes)
        .and_then(|()| output.flush())
        .map_err(|_| RuntimeSessionErrorCodeV2::PipeFailure)
}

fn serve_session(
    input: &mut impl BufRead,
    output: &mut impl Write,
    backend: &mut impl SessionBackend,
    campaign: &str,
    foundation_digest: String,
) -> Result<(), RuntimeSessionErrorCodeV2> {
    emit(
        output,
        &RuntimeSessionResponseV2::Ready {
            protocol_version: RUNTIME_SESSION_PROTOCOL_VERSION_V2,
            campaign_id: campaign.to_owned(),
            foundation_digest,
            tail: backend.tail(),
        },
    )?;
    loop {
        let mut line = Vec::new();
        let size = (&mut *input)
            .take((RUNTIME_SESSION_MAX_LINE_BYTES_V2 + 1) as u64)
            .read_until(b'\n', &mut line)
            .map_err(|_| RuntimeSessionErrorCodeV2::PipeFailure)?;
        if size == 0 {
            return Ok(());
        }
        if size > RUNTIME_SESSION_MAX_LINE_BYTES_V2 || !line.ends_with(b"\n") {
            emit(
                output,
                &RuntimeSessionResponseV2::Error {
                    request_id: None,
                    code: RuntimeSessionErrorCodeV2::InvalidRequest,
                    tail: backend.tail(),
                },
            )?;
            return Err(RuntimeSessionErrorCodeV2::InvalidRequest);
        }
        let Ok(request) = serde_json::from_slice::<RuntimeSessionRequestV2>(&line) else {
            emit(
                output,
                &RuntimeSessionResponseV2::Error {
                    request_id: None,
                    code: RuntimeSessionErrorCodeV2::InvalidRequest,
                    tail: backend.tail(),
                },
            )?;
            continue;
        };
        let (version, selected_campaign, request_id) = request.header();
        let refusal = if version != RUNTIME_SESSION_PROTOCOL_VERSION_V2 {
            Some(RuntimeSessionErrorCodeV2::UnsupportedVersion)
        } else if selected_campaign != campaign {
            Some(RuntimeSessionErrorCodeV2::CampaignMismatch)
        } else {
            None
        };
        if let Some(code) = refusal {
            emit(
                output,
                &RuntimeSessionResponseV2::Error {
                    request_id: Some(request_id),
                    code,
                    tail: backend.tail(),
                },
            )?;
            continue;
        }
        match request {
            RuntimeSessionRequestV2::Stop { .. } => {
                emit(output, &RuntimeSessionResponseV2::Stopped { request_id })?;
                return Ok(());
            }
            RuntimeSessionRequestV2::Advance { expected_tail, .. } => {
                match backend.advance(&expected_tail) {
                    Ok(tail) => emit(
                        output,
                        &RuntimeSessionResponseV2::Committed {
                            request_id,
                            campaign_id: campaign.to_owned(),
                            tail,
                        },
                    )?,
                    Err(code) => {
                        emit(
                            output,
                            &RuntimeSessionResponseV2::Error {
                                request_id: Some(request_id),
                                code,
                                tail: backend.tail(),
                            },
                        )?;
                        continue;
                    }
                }
                // Ack is flushed before one bounded sweep. A dead parent cannot
                // request a further tick; a committed in-flight tick stays durable.
                emit_archive_progress(output, backend, campaign, Some(request_id))?;
            }
            RuntimeSessionRequestV2::RefreshArchive { .. } => {
                emit_archive_progress(output, backend, campaign, Some(request_id))?;
            }
        }
    }
}

fn emit_archive_progress(
    output: &mut impl Write,
    backend: &mut impl SessionBackend,
    campaign: &str,
    request_id: Option<u64>,
) -> Result<(), RuntimeSessionErrorCodeV2> {
    let response = match backend.sweep() {
        Ok(progress) => RuntimeSessionResponseV2::ArchiveProgress {
            request_id,
            campaign_id: campaign.to_owned(),
            durable_tick: backend.tail().resolve_tick,
            verified_tick: progress.verified_tick,
            retention_ready: progress.retention_ready,
        },
        Err(code) => RuntimeSessionResponseV2::Error {
            request_id,
            code,
            tail: backend.tail(),
        },
    };
    emit(output, &response)
}

/// Run the parent-owned control protocol over explicit bounded byte streams.
/// # Errors
/// Refuses foundations outside the closed, versioned Michigan content catalog,
/// runtime failures, invalid framing, or a closed response pipe.
pub fn run_runtime_session_v2(
    config: &Config,
    campaign: CampaignId,
    requested_preset: Option<MichiganDeliveryPresetV1>,
    input: &mut impl BufRead,
    output: &mut impl Write,
) -> Result<(), RuntimeSessionErrorCodeV2> {
    let bounded = crate::material_runtime::bounded_material_writer_config_v3(config)
        .map_err(|_| RuntimeSessionErrorCodeV2::StorageRefused)?;
    crate::material_runtime::install_material_runtime_schema_v3(config)
        .map_err(|_| RuntimeSessionErrorCodeV2::StorageRefused)?;
    SemanticArchiveStoreV1::new(config)
        .install_schema()
        .map_err(|_| RuntimeSessionErrorCodeV2::StorageRefused)?;
    crate::install_reader_role_v1(config).map_err(|_| RuntimeSessionErrorCodeV2::StorageRefused)?;
    crate::install_observer_economy_schema_v1(config)
        .map_err(|_| RuntimeSessionErrorCodeV2::StorageRefused)?;
    let mut client = bounded
        .connect(NoTls)
        .map_err(|_| RuntimeSessionErrorCodeV2::StorageRefused)?;
    let (preset, exists) = runtime_content(&mut client, campaign, requested_preset)?;
    let admitted = preset
        .admitted()
        .map_err(|_| RuntimeSessionErrorCodeV2::ScenarioMismatch)?;
    let foundation_digest = digest_hex(&admitted.digest());
    let runtime = if exists {
        DurableMaterialRuntimeV3::open(config, campaign, admitted.digest())
    } else {
        let foundation = preset
            .create_foundation()
            .map_err(|_| RuntimeSessionErrorCodeV2::ScenarioMismatch)?;
        DurableMaterialRuntimeV3::create(config, campaign, foundation)
    }
    .map_err(|error| match error {
        MaterialRuntimeErrorV3::LegacyCampaign | MaterialRuntimeErrorV3::FoundationMismatch => {
            RuntimeSessionErrorCodeV2::ScenarioMismatch
        }
        _ => RuntimeSessionErrorCodeV2::StorageRefused,
    })?;
    let tail = durable_tail(config, campaign)?;
    if runtime.session().completed_tick() != tail.resolve_tick {
        return Err(RuntimeSessionErrorCodeV2::StorageRefused);
    }
    let mut backend = DurableBackend {
        config: config.clone(),
        campaign,
        runtime,
        tail,
    };
    serve_session(
        input,
        output,
        &mut backend,
        &campaign.as_uuid().to_string(),
        foundation_digest,
    )
}

// This single row read selects a version, never substitutes stored self-hashes
// for the independently admitted expected identity passed to runtime reopen.
fn runtime_content(
    client: &mut impl postgres::GenericClient,
    campaign: CampaignId,
    requested: Option<MichiganDeliveryPresetV1>,
) -> Result<(MichiganContentPresetV1, bool), RuntimeSessionErrorCodeV2> {
    let row = client.query_opt("SELECT f.preset_id,f.horizon_ticks,f.content_sha256,f.foundation_sha256,g.foundation_sha256,pg_catalog.sha256(pg_catalog.convert_to(g.scenario_source,'UTF8')) FROM babylon_state.material_campaign_foundation_v2 f JOIN babylon_state.campaign_foundation g USING(campaign_id) WHERE campaign_id=$1::uuid", &[campaign.as_uuid()])
        .map_err(|_| RuntimeSessionErrorCodeV2::StorageRefused)?;
    let Some(row) = row else {
        return Ok((select_content_preset(None, requested)?, false));
    };
    let id: String = row
        .try_get(0)
        .map_err(|_| RuntimeSessionErrorCodeV2::StorageRefused)?;
    let horizon: i64 = row
        .try_get(1)
        .map_err(|_| RuntimeSessionErrorCodeV2::StorageRefused)?;
    let content: Vec<u8> = row
        .try_get(2)
        .map_err(|_| RuntimeSessionErrorCodeV2::StorageRefused)?;
    let foundation: Vec<u8> = row
        .try_get(3)
        .map_err(|_| RuntimeSessionErrorCodeV2::StorageRefused)?;
    let graph: Vec<u8> = row
        .try_get(4)
        .map_err(|_| RuntimeSessionErrorCodeV2::StorageRefused)?;
    let scenario: Vec<u8> = row
        .try_get(5)
        .map_err(|_| RuntimeSessionErrorCodeV2::StorageRefused)?;
    let admitted = admit_michigan_content_v1(&id, horizon, &content, &foundation, 0)
        .map_err(|_| RuntimeSessionErrorCodeV2::ScenarioMismatch)?;
    admitted
        .validate_graph(&graph, &scenario)
        .map_err(|_| RuntimeSessionErrorCodeV2::ScenarioMismatch)?;
    Ok((
        select_content_preset(Some(admitted.preset()), requested)?,
        true,
    ))
}

fn select_content_preset(
    stored: Option<MichiganContentPresetV1>,
    requested: Option<MichiganDeliveryPresetV1>,
) -> Result<MichiganContentPresetV1, RuntimeSessionErrorCodeV2> {
    if let Some(stored) = stored {
        if requested.is_some_and(|delivery| delivery != stored.delivery()) {
            return Err(RuntimeSessionErrorCodeV2::ScenarioMismatch);
        }
        Ok(stored)
    } else {
        Ok(MichiganContentPresetV1::new_campaign(
            requested.unwrap_or(MichiganDeliveryPresetV1::Standard),
        ))
    }
}

/// Bind the session protocol to the inherited standard streams.
/// # Errors
/// See [`run_runtime_session_v2`].
pub fn run_runtime_session_stdio_v2(
    config: &Config,
    campaign: CampaignId,
    requested_preset: Option<MichiganDeliveryPresetV1>,
) -> Result<(), RuntimeSessionErrorCodeV2> {
    run_runtime_session_v2(
        config,
        campaign,
        requested_preset,
        &mut std::io::stdin().lock(),
        &mut std::io::stdout().lock(),
    )
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn resume_keeps_stored_revision_and_new_campaigns_choose_cohorts() {
        for stored in crate::michigan_content::MICHIGAN_CONTENT_PRESETS_V1 {
            assert_eq!(select_content_preset(Some(stored), None), Ok(stored));
            assert_eq!(
                select_content_preset(Some(stored), Some(stored.delivery())),
                Ok(stored)
            );
            let other = match stored.delivery() {
                MichiganDeliveryPresetV1::Standard => MichiganDeliveryPresetV1::Delayed,
                MichiganDeliveryPresetV1::Delayed => MichiganDeliveryPresetV1::Standard,
            };
            assert_eq!(
                select_content_preset(Some(stored), Some(other)),
                Err(RuntimeSessionErrorCodeV2::ScenarioMismatch)
            );
        }
        assert_eq!(
            select_content_preset(None, None),
            Ok(MichiganContentPresetV1::BundlesStandardV3)
        );
        assert_eq!(
            select_content_preset(None, Some(MichiganDeliveryPresetV1::Delayed)),
            Ok(MichiganContentPresetV1::BundlesDelayedV3)
        );
    }

    #[derive(Default)]
    struct Backend {
        tick: u64,
        fail_commit: bool,
        sweeps: usize,
    }
    impl SessionBackend for Backend {
        fn tail(&self) -> RuntimeSessionTailV2 {
            RuntimeSessionTailV2 {
                resolve_tick: self.tick,
                tick_content_hash: (self.tick > 0).then(|| format!("{:064x}", self.tick)),
            }
        }
        fn advance(
            &mut self,
            expected: &RuntimeSessionTailV2,
        ) -> Result<RuntimeSessionTailV2, RuntimeSessionErrorCodeV2> {
            if expected != &self.tail() {
                return Err(RuntimeSessionErrorCodeV2::StaleExpectedTail);
            }
            if self.fail_commit {
                return Err(RuntimeSessionErrorCodeV2::CommitRefused);
            }
            self.tick += 1;
            Ok(self.tail())
        }
        fn sweep(&mut self) -> Result<ArchiveMaintenanceProgress, RuntimeSessionErrorCodeV2> {
            self.sweeps += 1;
            Ok(ArchiveMaintenanceProgress {
                verified_tick: self.tick,
                retention_ready: true,
            })
        }
    }
    fn advance() -> RuntimeSessionRequestV2 {
        RuntimeSessionRequestV2::Advance {
            protocol_version: RUNTIME_SESSION_PROTOCOL_VERSION_V2,
            campaign_id: "campaign".to_owned(),
            request_id: 1,
            expected_tail: RuntimeSessionTailV2 {
                resolve_tick: 0,
                tick_content_hash: None,
            },
        }
    }
    fn wire(request: &RuntimeSessionRequestV2) -> Vec<u8> {
        let mut line = serde_json::to_vec(request).unwrap();
        line.push(b'\n');
        line
    }
    fn responses(output: &[u8]) -> Vec<RuntimeSessionResponseV2> {
        output
            .split(|byte| *byte == b'\n')
            .filter(|line| !line.is_empty())
            .map(|line| serde_json::from_slice(line).unwrap())
            .collect()
    }
    #[test]
    fn acknowledgement_follows_commit_and_precedes_archive_progress() {
        let mut backend = Backend::default();
        let mut output = Vec::new();
        serve_session(
            &mut std::io::Cursor::new(wire(&advance())),
            &mut output,
            &mut backend,
            "campaign",
            "digest".into(),
        )
        .unwrap();
        let rows = responses(&output);
        assert!(matches!(rows[0], RuntimeSessionResponseV2::Ready { .. }));
        assert!(matches!(
            rows[1],
            RuntimeSessionResponseV2::Committed { .. }
        ));
        assert!(matches!(
            rows[2],
            RuntimeSessionResponseV2::ArchiveProgress { .. }
        ));
        assert_eq!(backend.tick, 1);
    }

    #[test]
    fn queued_stop_finishes_current_commit_and_prevents_any_later_advance() {
        let mut backend = Backend::default();
        let mut output = Vec::new();
        let mut input = wire(&advance());
        input.extend(wire(&RuntimeSessionRequestV2::Stop {
            protocol_version: RUNTIME_SESSION_PROTOCOL_VERSION_V2,
            campaign_id: "campaign".into(),
            request_id: 0,
        }));
        input.extend(wire(&advance()));
        serve_session(
            &mut std::io::Cursor::new(input),
            &mut output,
            &mut backend,
            "campaign",
            "digest".into(),
        )
        .unwrap();
        let rows = responses(&output);
        assert_eq!(rows.len(), 4);
        assert!(matches!(
            rows[1],
            RuntimeSessionResponseV2::Committed { .. }
        ));
        assert!(matches!(
            rows[2],
            RuntimeSessionResponseV2::ArchiveProgress { .. }
        ));
        assert!(matches!(
            rows[3],
            RuntimeSessionResponseV2::Stopped { request_id: 0 }
        ));
        assert_eq!(backend.tick, 1);
        assert_eq!(backend.sweeps, 1);
    }
    #[test]
    fn failed_commit_has_no_acknowledgement_or_archive_sweep() {
        let mut backend = Backend {
            fail_commit: true,
            ..Backend::default()
        };
        let mut output = Vec::new();
        serve_session(
            &mut std::io::Cursor::new(wire(&advance())),
            &mut output,
            &mut backend,
            "campaign",
            "digest".into(),
        )
        .unwrap();
        assert!(matches!(
            responses(&output)[1],
            RuntimeSessionResponseV2::Error {
                code: RuntimeSessionErrorCodeV2::CommitRefused,
                ..
            }
        ));
        assert_eq!((backend.tick, backend.sweeps), (0, 0));
    }
    #[test]
    fn duplicate_stale_command_advances_only_once_and_eof_does_not_tick() {
        let mut commands = wire(&advance());
        commands.extend(wire(&advance()));
        let mut backend = Backend::default();
        let mut output = Vec::new();
        serve_session(
            &mut std::io::Cursor::new(commands),
            &mut output,
            &mut backend,
            "campaign",
            "digest".into(),
        )
        .unwrap();
        assert_eq!(backend.tick, 1);
        assert!(matches!(
            responses(&output)[3],
            RuntimeSessionResponseV2::Error {
                code: RuntimeSessionErrorCodeV2::StaleExpectedTail,
                ..
            }
        ));
    }
    #[test]
    fn extra_actions_and_unknown_version_cannot_reach_commit() {
        assert!(serde_json::from_str::<RuntimeSessionRequestV2>(r#"{"type":"advance","protocol_version":2,"campaign_id":"campaign","request_id":1,"expected_tail":{"resolve_tick":0,"tick_content_hash":null},"actions":[1]}"#).is_err());
        for rejected_version in [1, 3] {
            let mut request = advance();
            if let RuntimeSessionRequestV2::Advance {
                protocol_version, ..
            } = &mut request
            {
                *protocol_version = rejected_version;
            }
            let mut backend = Backend::default();
            let mut output = Vec::new();
            serve_session(
                &mut std::io::Cursor::new(wire(&request)),
                &mut output,
                &mut backend,
                "campaign",
                "digest".into(),
            )
            .unwrap();
            assert_eq!(backend.tick, 0);
            let rows = responses(&output);
            assert!(matches!(
                rows[0],
                RuntimeSessionResponseV2::Ready {
                    protocol_version: 2,
                    ..
                }
            ));
            assert!(matches!(
                rows[1],
                RuntimeSessionResponseV2::Error {
                    code: RuntimeSessionErrorCodeV2::UnsupportedVersion,
                    ..
                }
            ));
        }
        assert!(serde_json::from_str::<RuntimeSessionResponseV2>(r#"{"type":"archive_progress","request_id":0,"campaign_id":"campaign","durable_tick":1,"verified_tick":1}"#).is_err());
    }
    #[test]
    fn oversized_line_is_refused_before_parsing() {
        let mut backend = Backend::default();
        let mut output = Vec::new();
        assert_eq!(
            serve_session(
                &mut std::io::Cursor::new(vec![b' '; RUNTIME_SESSION_MAX_LINE_BYTES_V2 + 1]),
                &mut output,
                &mut backend,
                "campaign",
                "digest".into()
            ),
            Err(RuntimeSessionErrorCodeV2::InvalidRequest)
        );
        assert_eq!(backend.tick, 0);
    }
}
