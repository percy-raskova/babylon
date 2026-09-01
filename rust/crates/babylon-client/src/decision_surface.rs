//! The PER-24 contract for every shipped Bevy decision surface.
//!
//! A surface may enter a gameplay gate only when it asks a decision
//! question and declares every input/output side of the player loop. The
//! current client is still the explicitly unfogged administrative viewer, so
//! each shipped row below carries an administrative exemption and is
//! ineligible for gameplay gates. [`DeclaredSurface`] binds rendered entities
//! back to this manifest so the production plugin composition can be checked
//! as executable code rather than inferred from documentation.

use bevy::prelude::Component;
use std::fmt;

/// Stable identifiers for the visible surfaces in the production client.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum SurfaceId {
    TitleLockup,
    StoryBanner,
    CountyMap,
    CountyLensHud,
    TickTransport,
    StatePanel,
    BeatFeed,
    TerminalLatch,
    StoryCard,
    MapAbsenceNotice,
    Countdown,
    AdminDisclosure,
    AdminInspector,
}

impl SurfaceId {
    /// Complete closed set used by the manifest-exhaustiveness sentinel.
    pub const ALL: [Self; 13] = [
        Self::TitleLockup,
        Self::StoryBanner,
        Self::CountyMap,
        Self::CountyLensHud,
        Self::TickTransport,
        Self::StatePanel,
        Self::BeatFeed,
        Self::TerminalLatch,
        Self::StoryCard,
        Self::MapAbsenceNotice,
        Self::Countdown,
        Self::AdminDisclosure,
        Self::AdminInspector,
    ];
}

impl fmt::Display for SurfaceId {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(match self {
            Self::TitleLockup => "title-lockup",
            Self::StoryBanner => "story-banner",
            Self::CountyMap => "county-map",
            Self::CountyLensHud => "county-lens-hud",
            Self::TickTransport => "tick-transport",
            Self::StatePanel => "state-panel",
            Self::BeatFeed => "beat-feed",
            Self::TerminalLatch => "terminal-latch",
            Self::StoryCard => "story-card",
            Self::MapAbsenceNotice => "map-absence-notice",
            Self::Countdown => "countdown",
            Self::AdminDisclosure => "admin-disclosure",
            Self::AdminInspector => "admin-inspector",
        })
    }
}

/// Whether a surface is player-decision gameplay, semantic reference, or an
/// administrative/debug instrument.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum DecisionSurfaceRole {
    Gameplay,
    ArchiveReference,
    AdminDebug,
}

/// One complete declaration of what a surface shows and what player loop it
/// closes.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct DecisionSurfaceContract {
    pub id: SurfaceId,
    pub role: DecisionSurfaceRole,
    pub decision_question: Option<&'static str>,
    pub visible_signals: &'static [&'static str],
    pub visible_uncertainty: &'static [&'static str],
    pub fog_requirements: &'static [&'static str],
    pub actions: &'static [&'static str],
    pub expected_receipts: &'static [&'static str],
    pub archive_subjects: &'static [&'static str],
    pub admin_debug_exempt: bool,
}

/// A structurally incomplete or contradictory decision-surface declaration.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum DecisionSurfaceContractError {
    AdminExemptionMismatch,
    MissingDecisionQuestion,
    MissingVisibleSignals,
    MissingVisibleUncertainty,
    MissingFogRequirements,
    MissingActions,
    MissingExpectedReceipts,
    MissingArchiveSubjects,
}

impl fmt::Display for DecisionSurfaceContractError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(match self {
            Self::AdminExemptionMismatch => {
                "admin_debug_exempt must be true exactly for AdminDebug surfaces"
            }
            Self::MissingDecisionQuestion => "gameplay surface has no decision question",
            Self::MissingVisibleSignals => "gameplay surface has no visible signals",
            Self::MissingVisibleUncertainty => "gameplay surface has no visible uncertainty",
            Self::MissingFogRequirements => "gameplay surface has no fog requirements",
            Self::MissingActions => "gameplay surface has no available actions",
            Self::MissingExpectedReceipts => "gameplay surface has no expected receipts",
            Self::MissingArchiveSubjects => "gameplay surface has no Archive subjects",
        })
    }
}

impl std::error::Error for DecisionSurfaceContractError {}

fn has_only_declared_entries(entries: &[&str]) -> bool {
    !entries.is_empty() && entries.iter().all(|entry| !entry.trim().is_empty())
}

impl DecisionSurfaceContract {
    /// Checks the structural requirements of the declared role.
    ///
    /// Administrative and Archive/reference surfaces may describe signals,
    /// but only gameplay surfaces must close every part of the player decision
    /// loop. The exemption flag is deliberately redundant with the role: that
    /// makes an exemption explicit in every manifest row and lets validation
    /// reject contradictory declarations.
    ///
    /// # Errors
    ///
    /// Returns the first missing gameplay field or an exemption/role
    /// contradiction.
    pub fn validate(&self) -> Result<(), DecisionSurfaceContractError> {
        if self.admin_debug_exempt != (self.role == DecisionSurfaceRole::AdminDebug) {
            return Err(DecisionSurfaceContractError::AdminExemptionMismatch);
        }
        if self.role != DecisionSurfaceRole::Gameplay {
            return Ok(());
        }
        if self
            .decision_question
            .is_none_or(|question| question.trim().is_empty())
        {
            return Err(DecisionSurfaceContractError::MissingDecisionQuestion);
        }
        if !has_only_declared_entries(self.visible_signals) {
            return Err(DecisionSurfaceContractError::MissingVisibleSignals);
        }
        if !has_only_declared_entries(self.visible_uncertainty) {
            return Err(DecisionSurfaceContractError::MissingVisibleUncertainty);
        }
        if !has_only_declared_entries(self.fog_requirements) {
            return Err(DecisionSurfaceContractError::MissingFogRequirements);
        }
        if !has_only_declared_entries(self.actions) {
            return Err(DecisionSurfaceContractError::MissingActions);
        }
        if !has_only_declared_entries(self.expected_receipts) {
            return Err(DecisionSurfaceContractError::MissingExpectedReceipts);
        }
        if !has_only_declared_entries(self.archive_subjects) {
            return Err(DecisionSurfaceContractError::MissingArchiveSubjects);
        }
        Ok(())
    }

    /// Returns true only for a valid, non-exempt gameplay declaration.
    #[must_use]
    pub fn satisfies_gameplay_gate(&self) -> bool {
        self.role == DecisionSurfaceRole::Gameplay
            && !self.admin_debug_exempt
            && self.validate().is_ok()
    }
}

/// ECS marker connecting a rendered entity to its manifest row.
#[derive(Component, Debug, Clone, Copy, PartialEq, Eq)]
pub struct DeclaredSurface {
    pub id: SurfaceId,
}

impl DeclaredSurface {
    #[must_use]
    pub const fn new(id: SurfaceId) -> Self {
        Self { id }
    }
}

const NONE: &[&str] = &[];
const UNFOGGED_ADMIN: &[&str] = &["unfogged material truth; no player knowledge state"];

const fn admin_surface(
    id: SurfaceId,
    visible_signals: &'static [&'static str],
    visible_uncertainty: &'static [&'static str],
) -> DecisionSurfaceContract {
    DecisionSurfaceContract {
        id,
        role: DecisionSurfaceRole::AdminDebug,
        decision_question: None,
        visible_signals,
        visible_uncertainty,
        fog_requirements: UNFOGGED_ADMIN,
        actions: NONE,
        expected_receipts: NONE,
        archive_subjects: NONE,
        admin_debug_exempt: true,
    }
}

/// Authoritative inventory of the surfaces composed by `main.rs`.
///
/// Every row is administrative today because the client has no player action
/// and renders an always-visible `ADMIN · MATERIAL TRUTH · UNFOGGED` banner.
/// The manifest makes that limitation executable: rich visual output cannot
/// become gameplay evidence merely by existing.
pub const SHIPPED_SURFACE_MANIFEST: &[DecisionSurfaceContract] = &[
    admin_surface(SurfaceId::TitleLockup, &["application identity"], NONE),
    admin_surface(SurfaceId::StoryBanner, &["selected story identity"], NONE),
    admin_surface(
        SurfaceId::CountyMap,
        &["unfogged county lens values", "county boundaries"],
        &["absent lens values are visibly distinct from zero"],
    ),
    admin_surface(
        SurfaceId::CountyLensHud,
        &["selected county", "active lens value and source"],
        &["absence banner for unavailable readings"],
    ),
    admin_surface(
        SurfaceId::TickTransport,
        &["tick", "nominal world hash", "viewer playback state"],
        NONE,
    ),
    admin_surface(
        SurfaceId::StatePanel,
        &["selected node engine fields"],
        &["missing fields render as absent"],
    ),
    admin_surface(
        SurfaceId::BeatFeed,
        &["engine events", "severity", "tick"],
        &["bounded feed history"],
    ),
    admin_surface(
        SurfaceId::TerminalLatch,
        &["terminal-decision event payload"],
        &["uncomputed outcomes remain explicitly absent"],
    ),
    admin_surface(
        SurfaceId::StoryCard,
        &["story premise", "story catalog", "viewer controls"],
        &["open-ended stories show unknown beat totals"],
    ),
    admin_surface(
        SurfaceId::MapAbsenceNotice,
        &["declared territorial-substrate absence"],
        NONE,
    ),
    admin_surface(
        SurfaceId::Countdown,
        &["engine-derived phase countdown"],
        &["unlatched countdowns remain absent"],
    ),
    admin_surface(
        SurfaceId::AdminDisclosure,
        &[
            "administrative viewer status",
            "unfogged material-truth status",
        ],
        NONE,
    ),
    admin_surface(
        SurfaceId::AdminInspector,
        &[
            "raw selected-node attributes",
            "per-rule tick report after a completed viewer tick",
            "tick report \u{2014} not yet run",
            "roster \u{2014} no county selected",
        ],
        &["pre-tick and roster-selection status are explicit"],
    ),
];

/// Resolves one surface id to its sole manifest declaration.
///
/// # Panics
///
/// Panics when `id` is absent. The manifest exhaustiveness test proves that
/// every closed [`SurfaceId`] variant resolves in the shipped build.
#[must_use]
pub fn contract_for(id: SurfaceId) -> &'static DecisionSurfaceContract {
    SHIPPED_SURFACE_MANIFEST
        .iter()
        .find(|contract| contract.id == id)
        .unwrap_or_else(|| panic!("surface {id} has no manifest contract"))
}
