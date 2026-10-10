//! One closed, scoped protocol for the lifetime of the parent-owned pipes.

use serde::{Deserialize, Serialize};

use super::RuntimeSessionErrorCode;
pub use crate::organizer_runtime::{
    OrganizerAidCapacity, OrganizerAidOrdinaryOffer, OrganizerAidPending, OrganizerAidResolution,
    OrganizerAidRouteStage, OrganizerAidTime, OrganizerAidTransportPreview,
    OrganizerCollectionPreview, OrganizerMaterialAidPreview, OrganizerSnapshot,
};
use crate::{identity::CampaignId, michigan_material::MichiganDeliveryPreset};
pub use babylon_practice_contract::{
    OrganizerAgreement, OrganizerAidKind, OrganizerAidMaterialPostings, OrganizerAidOption,
    OrganizerAidSupportStatus, OrganizerChoice, OrganizerCollectionOutcome,
    OrganizerCollectionResolution, OrganizerCommand, OrganizerCommitment, OrganizerGiftConsent,
    OrganizerInquiry, OrganizerObservation, OrganizerOutcome, OrganizerPartnerResponse,
    OrganizerPauseReason, OrganizerPosition, OrganizerPreview, OrganizerReceipt, OrganizerRefusal,
    OrganizerReport, OrganizerStandingWork, OrganizerView,
};

pub use crate::material_runtime::MaterialAdvanceStage as RuntimeAdvanceStage;

pub const RUNTIME_SESSION_PROTOCOL_VERSION: u16 = 11;
pub const RUNTIME_SESSION_MAX_LINE_BYTES: usize = 131_072;

/// A lifecycle incarnation, distinct even when the same campaign is reopened.
#[derive(Clone, Debug, Default, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct RuntimeSessionScope {
    pub epoch: u64,
    pub campaign_id: Option<String>,
}

/// Exact acknowledged durable tail; foundation has no committed tick hash.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct RuntimeSessionTail {
    pub resolve_tick: u64,
    pub tick_content_hash: Option<String>,
}

/// Closed wire selection of captured campaigns and explicit Michigan controls.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum RuntimeSessionPreset {
    #[serde(rename = "national-world")]
    NationalWorld,
    #[serde(rename = "organize-in-wayne")]
    OrganizeInWayne,
    Standard,
    Delayed,
    #[serde(rename = "shared-freight-ample")]
    SharedFreightAmple,
    #[serde(rename = "shared-freight-constrained")]
    SharedFreightConstrained,
    #[serde(rename = "statewide-baseline")]
    StatewideBaseline,
    #[serde(rename = "statewide-freight-constraint")]
    StatewideFreightConstraint,
    #[serde(rename = "statewide-packaging-shortage")]
    StatewidePackagingShortage,
    #[serde(rename = "statewide-both")]
    StatewideBoth,
    #[serde(rename = "statewide-maintenance-baseline")]
    StatewideMaintenanceBaseline,
    #[serde(rename = "statewide-maintenance-labor-shortage")]
    StatewideMaintenanceLaborShortage,
    #[serde(rename = "statewide-maintenance-parts-shortage")]
    StatewideMaintenancePartsShortage,
    #[serde(rename = "statewide-maintenance-both")]
    StatewideMaintenanceBoth,
}
impl RuntimeSessionPreset {
    pub(super) const fn delivery(self) -> Option<MichiganDeliveryPreset> {
        Some(match self {
            Self::NationalWorld => return None,
            Self::OrganizeInWayne => MichiganDeliveryPreset::OrganizeInWayne,
            Self::Standard => MichiganDeliveryPreset::Standard,
            Self::Delayed => MichiganDeliveryPreset::Delayed,
            Self::SharedFreightAmple => MichiganDeliveryPreset::SharedFreightAmple,
            Self::SharedFreightConstrained => MichiganDeliveryPreset::SharedFreightConstrained,
            Self::StatewideBaseline => MichiganDeliveryPreset::StatewideBaseline,
            Self::StatewideFreightConstraint => MichiganDeliveryPreset::StatewideFreightConstraint,
            Self::StatewidePackagingShortage => MichiganDeliveryPreset::StatewidePackagingShortage,
            Self::StatewideBoth => MichiganDeliveryPreset::StatewideBoth,
            Self::StatewideMaintenanceBaseline => {
                MichiganDeliveryPreset::StatewideMaintenanceBaseline
            }
            Self::StatewideMaintenanceLaborShortage => {
                MichiganDeliveryPreset::StatewideMaintenanceLaborShortage
            }
            Self::StatewideMaintenancePartsShortage => {
                MichiganDeliveryPreset::StatewideMaintenancePartsShortage
            }
            Self::StatewideMaintenanceBoth => MichiganDeliveryPreset::StatewideMaintenanceBoth,
        })
    }
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case", deny_unknown_fields)]
pub enum RuntimeSessionTarget {
    New {
        campaign_id: String,
        preset: RuntimeSessionPreset,
    },
    Open {
        campaign_id: String,
    },
}
impl RuntimeSessionTarget {
    pub(super) fn campaign(&self) -> Result<CampaignId, RuntimeSessionErrorCode> {
        let (Self::New { campaign_id, .. } | Self::Open { campaign_id }) = self;
        let id = uuid::Uuid::parse_str(campaign_id)
            .map_err(|_| RuntimeSessionErrorCode::InvalidRequest)?;
        if id.is_nil() || id.to_string() != *campaign_id {
            return Err(RuntimeSessionErrorCode::InvalidRequest);
        }
        Ok(CampaignId::from_uuid(id))
    }
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case", deny_unknown_fields)]
pub enum RuntimeSessionRequest {
    Switch {
        protocol_version: u16,
        request_id: u64,
        scope: RuntimeSessionScope,
        target: RuntimeSessionTarget,
    },
    PreviewOrganizer {
        protocol_version: u16,
        request_id: u64,
        scope: RuntimeSessionScope,
        command: OrganizerCommand,
    },
    SubmitOrganizer {
        protocol_version: u16,
        request_id: u64,
        scope: RuntimeSessionScope,
        command: OrganizerCommand,
    },
    ConfigureOrganizerStanding {
        protocol_version: u16,
        request_id: u64,
        scope: RuntimeSessionScope,
        command: OrganizerCommand,
    },
    OrganizerStatus {
        protocol_version: u16,
        request_id: u64,
        scope: RuntimeSessionScope,
    },
    Advance {
        protocol_version: u16,
        request_id: u64,
        scope: RuntimeSessionScope,
        expected_tail: RuntimeSessionTail,
    },
    RefreshArchive {
        protocol_version: u16,
        request_id: u64,
        scope: RuntimeSessionScope,
    },
    Stop {
        protocol_version: u16,
        request_id: u64,
        scope: RuntimeSessionScope,
    },
}
impl RuntimeSessionRequest {
    pub(super) const fn header(&self) -> (u16, u64, &RuntimeSessionScope) {
        match self {
            Self::PreviewOrganizer {
                protocol_version,
                request_id,
                scope,
                ..
            }
            | Self::SubmitOrganizer {
                protocol_version,
                request_id,
                scope,
                ..
            }
            | Self::ConfigureOrganizerStanding {
                protocol_version,
                request_id,
                scope,
                ..
            }
            | Self::OrganizerStatus {
                protocol_version,
                request_id,
                scope,
            }
            | Self::Switch {
                protocol_version,
                request_id,
                scope,
                ..
            }
            | Self::Advance {
                protocol_version,
                request_id,
                scope,
                ..
            }
            | Self::RefreshArchive {
                protocol_version,
                request_id,
                scope,
            }
            | Self::Stop {
                protocol_version,
                request_id,
                scope,
            } => (*protocol_version, *request_id, scope),
        }
    }
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case", deny_unknown_fields)]
pub enum RuntimeSessionResponse {
    Hello {
        protocol_version: u16,
        scope: RuntimeSessionScope,
    },
    Switching {
        request_id: u64,
        previous_scope: RuntimeSessionScope,
        scope: RuntimeSessionScope,
    },
    Ready {
        request_id: u64,
        scope: RuntimeSessionScope,
        foundation_digest: String,
        duration: babylon_kernel::clock::CampaignDuration,
        organizer: bool,
        tail: RuntimeSessionTail,
    },
    OrganizerPreview {
        request_id: u64,
        scope: RuntimeSessionScope,
        preview: OrganizerPreview,
    },
    OrganizerAccepted {
        request_id: u64,
        scope: RuntimeSessionScope,
        commitment: OrganizerCommitment,
    },
    OrganizerStatus {
        request_id: u64,
        scope: RuntimeSessionScope,
        snapshot: Box<OrganizerSnapshot>,
    },
    AdvanceProgress {
        request_id: u64,
        scope: RuntimeSessionScope,
        resolve_tick: u64,
        stage: RuntimeAdvanceStage,
    },
    Committed {
        request_id: u64,
        scope: RuntimeSessionScope,
        tail: RuntimeSessionTail,
    },
    ArchiveProgress {
        request_id: Option<u64>,
        scope: RuntimeSessionScope,
        durable_tick: u64,
        verified_tick: u64,
    },
    Error {
        request_id: Option<u64>,
        scope: RuntimeSessionScope,
        code: RuntimeSessionErrorCode,
        tail: Option<RuntimeSessionTail>,
    },
    Stopped {
        request_id: u64,
        scope: RuntimeSessionScope,
    },
}

#[cfg(test)]
mod selection_tests {
    use super::*;

    #[test]
    fn national_selection_has_no_michigan_fallback_or_open_override() {
        let preset: RuntimeSessionPreset = serde_json::from_str("\"national-world\"").unwrap();
        assert_eq!(preset, RuntimeSessionPreset::NationalWorld);
        assert_eq!(preset.delivery(), None);
        assert_eq!(
            RuntimeSessionPreset::Standard.delivery(),
            Some(MichiganDeliveryPreset::Standard)
        );
        for selection in [
            "national",
            "National-world",
            "national_world",
            "national-world ",
        ] {
            assert!(
                serde_json::from_value::<RuntimeSessionPreset>(serde_json::json!(selection))
                    .is_err()
            );
        }
        assert!(serde_json::from_value::<RuntimeSessionTarget>(serde_json::json!({
            "type": "open", "campaign_id": uuid::Uuid::from_u128(7).to_string(), "preset": "national-world"
        })).is_err());
    }
}

#[test]
fn advance_progress_current_wire_is_closed_and_versioned() {
    assert_eq!(RUNTIME_SESSION_PROTOCOL_VERSION, 11);
    let valid = r#"{"type":"advance_progress","request_id":2,"scope":{"epoch":1,"campaign_id":"00000000-0000-0000-0000-000000000001"},"resolve_tick":1,"stage":"preparing_commitments"}"#;
    let response: RuntimeSessionResponse =
        serde_json::from_str(valid).expect("current actual progress wire");
    assert_eq!(
        serde_json::to_value(response).unwrap(),
        serde_json::from_str::<serde_json::Value>(valid).unwrap()
    );
    assert!(serde_json::from_str::<RuntimeSessionResponse>(
        &valid.replace("preparing_commitments", "invented_stage")
    )
    .is_err());
    assert!(serde_json::from_str::<RuntimeSessionResponse>(
        &valid.replace(r#""resolve_tick":1"#, r#""resolve_tick":1,"percent":50"#)
    )
    .is_err());
}

#[cfg(test)]
#[path = "money_wire_tests.rs"]
mod money_wire_tests;
