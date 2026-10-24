//! Leaf implementation for the parent module; public paths stay on the parent.

use super::{economic, production_renewal, trade};

use crate::identity::CampaignId;
use crate::observer_reader::CommittedMaterialObservation;
use crate::production_observation::ProductionSnapshot;

use babylon_kernel::economic_location::EconomicLocation;

use babylon_tick::material_replay::IdentifiedMaterialTick;
use babylon_tick::material_world::MaterialWorldRegister;

use serde::Serialize;

use serde_json::Value;

use sha2::{Digest, Sha256};

use crate::observer_reader::ObserverEconomySnapshot;
use babylon_tick::material_world;
use economic::Boundary;
use economic::Summary;
use production_renewal::Evidence;
use std::cmp::Ordering;
use std::collections::BTreeSet;
use std::fmt::Formatter;
use std::fmt::Result as FmtResult;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Refusal {
    Scope,
    Period,
    Identity,
    Geography,
    Production,
    RegisterLimit,
    EvidenceLimit,
    Economic(economic::Refusal),
    Trade(trade::Refusal),
    Renewal(production_renewal::Refusal),
}

impl std::fmt::Display for Refusal {
    fn fmt(&self, f: &mut Formatter<'_>) -> FmtResult {
        write!(f, "read-only qualification audit refused: {self:?}")
    }
}

impl std::error::Error for Refusal {}

/// Exact run inputs supplied by the supervisor from its frozen policy.
#[derive(Clone, Copy)]
pub struct Scope {
    pub campaign: CampaignId,
    pub foundation: [u8; 32],
    pub policy: [u8; 32],
    pub renewal_seed_tick: u64,
    pub material_register_bytes: usize,
    pub production_evidence_bytes: usize,
}

/// Bind a fold to the exact authenticated receipt that supplied its inputs.
#[derive(Serialize)]
pub struct ReceiptFacts<T> {
    pub tick_content_hash: String,
    pub canonical_receipt_sha256: String,
    #[serde(flatten)]
    pub audit: T,
}

impl<T> ReceiptFacts<T> {
    pub(super) fn new(audit: T, identity: &IdentifiedMaterialTick) -> Self {
        Self {
            tick_content_hash: hex(identity.tick_content_hash().as_bytes()),
            canonical_receipt_sha256: hex(&identity.receipt_digest()),
            audit,
        }
    }
}

/// Renewal retains its seed, while the current receipt authenticates its end.
#[derive(Serialize)]
pub struct RenewalFacts {
    pub through_tick_content_hash: String,
    pub canonical_receipt_sha256: String,
    #[serde(flatten)]
    pub audit: Evidence,
}

impl RenewalFacts {
    pub(super) fn new(audit: Evidence, identity: &IdentifiedMaterialTick) -> Self {
        Self {
            through_tick_content_hash: hex(identity.tick_content_hash().as_bytes()),
            canonical_receipt_sha256: hex(&identity.receipt_digest()),
            audit,
        }
    }
}

/// Facts, not an admission result. Aid, Archive, storage, recovery and timing
/// remain independently required by the sole qualification evaluator.
#[derive(Serialize)]
pub struct BoundaryFacts {
    pub version: u8,
    pub campaign: String,
    pub foundation_sha256: String,
    pub policy_sha256: String,
    pub tick: u64,
    pub tick_content_hash: String,
    pub envelope_digest: String,
    pub canonical_receipt_sha256: String,
    pub nominal_world_hash: String,
    pub material_register_sha256: String,
    pub material_register_bytes: usize,
    pub production_evidence_sha256: String,
    pub production_evidence_body_bytes: u64,
    pub county_roster_sha256: String,
    pub economic: ReceiptFacts<Boundary>,
    pub trade: ReceiptFacts<Value>,
    pub production_renewal: Option<RenewalFacts>,
}

#[derive(Clone)]
pub struct MaterialAudit {
    scope: Scope,
    period: u64,
    economic: economic::Audit,
    trade: trade::Audit,
    renewal: Option<production_renewal::Audit>,
}

impl MaterialAudit {
    #[must_use]
    pub const fn completed_tick(&self) -> u64 {
        self.period
    }

    /// # Errors
    /// Refuses nil scope, a zero seed or a read limit beyond runtime hard bounds.
    pub fn new(scope: Scope) -> Result<Self, Refusal> {
        if scope.campaign.as_uuid().is_nil()
            || scope.foundation == [0; 32]
            || scope.policy == [0; 32]
            || scope.renewal_seed_tick == 0
            || scope.material_register_bytes == 0
            || scope.material_register_bytes > 1_000_000_000
            || scope.production_evidence_bytes == 0
            || scope.production_evidence_bytes > 1_000_000_000
        {
            return Err(Refusal::Scope);
        }
        Ok(Self {
            scope,
            period: 0,
            economic: economic::Audit::default(),
            trade: trade::Audit::default(),
            renewal: None,
        })
    }

    /// # Errors
    /// Refuses mismatched identities, incomplete national coverage, budget
    /// overruns or invalid joins. A refusal leaves every fold unchanged.
    pub fn read(
        &mut self,
        observation: &CommittedMaterialObservation,
        register: &MaterialWorldRegister,
    ) -> Result<BoundaryFacts, Refusal> {
        let identity = &observation.accounting.identity;
        let tick = identity.resolve_tick();
        if self.period.checked_add(1) != Some(tick) {
            return Err(Refusal::Period);
        }
        let snapshot = &observation.snapshot;
        let hash = hex(identity.tick_content_hash().as_bytes());
        let world = hex(&identity.result_world_hash());
        if observation.accounting.campaign_id != self.scope.campaign
            || snapshot.campaign_id != self.scope.campaign.as_uuid().to_string()
            || snapshot.resolve_tick != tick
            || identity.foundation_digest() != self.scope.foundation
            || snapshot.foundation_digest != hex(&self.scope.foundation)
            || snapshot.tick_content_hash.as_deref() != Some(hash.as_str())
            || snapshot.nominal_world_hash.as_deref() != Some(world.as_str())
            || observation.accounting.receipts.resolve_tick != tick
            || register.completed_tick() != tick
            || material_world::nominal_material_world_hash(identity.graph_world_after(), register)
                != identity.result_world_hash()
        {
            return Err(Refusal::Identity);
        }
        let envelope = snapshot.envelope_digest.clone().ok_or(Refusal::Identity)?;
        if envelope.len() != 64
            || !envelope
                .bytes()
                .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
        {
            return Err(Refusal::Identity);
        }
        if observation.accounting.material_register_bytes != register.canonical_bytes().len()
            || register.canonical_bytes().len() > self.scope.material_register_bytes
        {
            return Err(Refusal::RegisterLimit);
        }
        let body_bytes = observation.production_evidence.body_bytes();
        if body_bytes > self.scope.production_evidence_bytes {
            return Err(Refusal::EvidenceLimit);
        }
        let county_roster_sha256 = county_roster(snapshot)?.county_roster_sha256;
        let production = snapshot.production.as_ref().ok_or(Refusal::Production)?;
        validate_production(production)?;
        let mut candidate = self.clone();
        let economic = candidate
            .economic
            .read(&observation.accounting.receipts)
            .map_err(Refusal::Economic)?;
        let trade = candidate
            .trade
            .read(&observation.accounting.receipts, &production.sites)
            .map_err(Refusal::Trade)?;
        let production_renewal = match tick.cmp(&self.scope.renewal_seed_tick) {
            Ordering::Less => None,
            Ordering::Equal => {
                let audit =
                    production_renewal::Audit::seed(register.state(), tick, register.digest())
                        .map_err(Refusal::Renewal)?;
                let evidence = audit.evidence().map_err(Refusal::Renewal)?;
                candidate.renewal = Some(audit);
                Some(evidence)
            }
            Ordering::Greater => Some(
                candidate
                    .renewal
                    .as_mut()
                    .ok_or(Refusal::Identity)?
                    .read(&observation.accounting.receipts)
                    .map_err(Refusal::Renewal)?,
            ),
        };
        let facts = BoundaryFacts {
            version: 1,
            campaign: snapshot.campaign_id.clone(),
            foundation_sha256: snapshot.foundation_digest.clone(),
            policy_sha256: hex(&self.scope.policy),
            tick,
            tick_content_hash: hash,
            envelope_digest: envelope,
            canonical_receipt_sha256: hex(&identity.receipt_digest()),
            nominal_world_hash: world,
            material_register_sha256: hex(&register.digest()),
            material_register_bytes: register.canonical_bytes().len(),
            production_evidence_sha256: observation.production_evidence.to_hex(),
            production_evidence_body_bytes: u64::try_from(body_bytes)
                .map_err(|_| Refusal::EvidenceLimit)?,
            county_roster_sha256,
            economic: ReceiptFacts::new(economic, identity),
            trade: ReceiptFacts::new(trade, identity),
            production_renewal: production_renewal.map(|e| RenewalFacts::new(e, identity)),
        };
        candidate.period = tick;
        *self = candidate;
        Ok(facts)
    }

    #[must_use]
    pub fn economic_summary(&self) -> Summary {
        self.economic.summary()
    }

    #[must_use]
    pub fn trade_summary(&self) -> Value {
        self.trade.report()
    }
}

/// Compact national geography from the already authenticated observer read.
#[derive(Debug, Serialize)]
pub struct CountyRoster {
    pub county_geoids: Vec<String>,
    pub county_roster_sha256: String,
}

/// # Errors
/// Refuses missing, duplicated or substituted counties against the exact
/// national reference. The caller must authenticate the snapshot's source.
pub fn county_roster(snapshot: &ObserverEconomySnapshot) -> Result<CountyRoster, Refusal> {
    let counties: BTreeSet<_> = snapshot
        .counties
        .iter()
        .map(|c| c.county_geoid.clone())
        .collect();
    let reference =
        crate::national_counties::national_county_reference().map_err(|_| Refusal::Geography)?;
    let expected: BTreeSet<_> = reference
        .counties()
        .iter()
        .map(|c| c.geoid().to_string())
        .collect();
    if snapshot.counties.len() != 3_144 || counties != expected {
        return Err(Refusal::Geography);
    }
    let county_geoids: Vec<_> = counties.into_iter().collect();
    let bytes = serde_json::to_vec(&county_geoids).map_err(|_| Refusal::Geography)?;
    Ok(CountyRoster {
        county_geoids,
        county_roster_sha256: hex(&Sha256::digest(bytes)),
    })
}

pub(crate) fn validate_production(production: &ProductionSnapshot) -> Result<(), Refusal> {
    let mut foreign = BTreeSet::new();
    let mut dependencies = BTreeSet::new();
    for site in &production.sites {
        match site.location {
            EconomicLocation::Foreign(id) => {
                foreign.insert(id);
            }
            EconomicLocation::Dependency(id) => {
                dependencies.insert(id);
            }
            EconomicLocation::County(_) => {}
        }
    }
    if production.household_accounts.is_empty()
        || production.material_balance.is_none()
        || foreign.len() != 12
        || dependencies.len() != 6
    {
        return Err(Refusal::Production);
    }
    Ok(())
}

pub(crate) fn hex(bytes: &[u8]) -> String {
    use std::fmt::Write;
    let mut result = String::with_capacity(bytes.len().saturating_mul(2));
    for byte in bytes {
        write!(&mut result, "{byte:02x}").expect("writing to String cannot fail");
    }
    result
}
