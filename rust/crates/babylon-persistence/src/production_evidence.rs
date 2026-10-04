//! V17 identity of an already-authorized production presentation.
//!
//! Scope and the complete typed DTO are serialized as canonical JSON after the
//! fixed domain/version. True multisets sort; events, geometry vertices and each
//! route's physical edge sequence retain their semantic order. Serialization
//! streams into the hash with an explicit byte ceiling. V17 also binds residence
//! kinds without inventing ordinary households for collective residents, household
//! service needs and satisfaction, installation materials and work, and per-good
//! quotes with committed direct costs. It also binds household stocks, consumption,
//! bounded order history and resident staffing.
//! Locations keep their exact county, counterpart or dependency scope.
//! Household gift inflows, outflows and shared freight reservations stay separate
//! from purchases and commercial supplier orders.

use crate::production_projection::diagnostics::{Stage, Timing};
use crate::{
    observer_reader::ObserverEconomySnapshot, observer_reader::ObserverVisibility,
    production_observation::ProductionSnapshot,
};
use serde::Serialize;
use sha2::{Digest as _, Sha256};
use std::{
    collections::BTreeSet,
    io::{self, BufWriter, Write},
};

const DOMAIN: &[u8] = b"babylon.production-observation-evidence.v17\0";
const VERSION: u32 = 17;
const MAX_ROWS: usize = 65_536;
const MAX_PHYSICAL_ROWS: usize = 1_114_112;
// Designed ceiling for the streamed national presentation body.
const MAX_EVIDENCE_BYTES: usize = 1_000_000_000;

#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub struct ProductionEvidenceDigest([u8; 32]);
impl ProductionEvidenceDigest {
    #[must_use]
    pub const fn as_bytes(&self) -> &[u8; 32] {
        &self.0
    }
    #[must_use]
    pub fn to_hex(self) -> String {
        crate::michigan_economy::digest_hex(&self.0)
    }
}

/// A malformed disclosure cannot acquire a production evidence identity.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum ProductionEvidenceError {
    InvalidIdentity,
    Bound,
    Serialization,
}
impl std::fmt::Display for ProductionEvidenceError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "production evidence refused: {self:?}")
    }
}
impl std::error::Error for ProductionEvidenceError {}

type Result<T> = std::result::Result<T, ProductionEvidenceError>;

#[derive(Serialize)]
struct EvidenceScope<'a> {
    campaign_id: &'a str,
    resolve_tick: u64,
    foundation_digest: &'a str,
    tick_content_hash: Option<&'a str>,
    envelope_digest: Option<&'a str>,
    nominal_world_hash: Option<&'a str>,
    visibility: &'static str,
    production: &'a ProductionSnapshot,
}

impl ObserverEconomySnapshot {
    /// Hash the complete role-scoped disclosure after observation authentication.
    /// `None` means no production was disclosed, including a restricted preview.
    ///
    /// Canonicalizes presentation multisets in place after all semantic validation.
    /// Validation refusal leaves the disclosure unchanged; byte-limit or serialization
    /// refusal may leave those multisets sorted. Semantic sequences keep their order.
    ///
    /// # Errors
    /// Refuses duplicate identities, malformed preview disclosure, row/byte bounds
    /// and serialization errors; failure is never reported as absent production.
    pub fn production_evidence_digest(&mut self) -> Result<Option<ProductionEvidenceDigest>> {
        let Some(source) = self.production.as_mut() else {
            return Ok(None);
        };
        if self.visibility != ObserverVisibility::FullObserver {
            return Err(ProductionEvidenceError::InvalidIdentity);
        }
        diagnostic_cardinalities(source);
        let validation_timing = Timing::start(Stage::EvidenceValidation, self.resolve_tick);
        diagnostic_validation("identities", validate_identities(source))?;
        diagnostic_validation("source_contexts", validate_source_contexts(source))?;
        diagnostic_validation(
            "maintenance",
            validate_maintenance(source, self.resolve_tick),
        )?;
        diagnostic_validation("households", validate_households(source, self.resolve_tick))?;
        diagnostic_validation(
            "household_services",
            validate_household_services(source, self.resolve_tick),
        )?;
        diagnostic_validation(
            "goods_prices",
            validate_goods_prices(source, self.resolve_tick),
        )?;
        drop(validation_timing);
        let canonical_timing = Timing::start(Stage::EvidenceCanonical, self.resolve_tick);
        canonicalize_production(source);
        let production = &*source;
        drop(canonical_timing);
        let _hash_timing = Timing::start(Stage::EvidenceHash, self.resolve_tick);
        let scope = EvidenceScope {
            campaign_id: &self.campaign_id,
            resolve_tick: self.resolve_tick,
            foundation_digest: &self.foundation_digest,
            tick_content_hash: self.tick_content_hash.as_deref(),
            envelope_digest: self.envelope_digest.as_deref(),
            nominal_world_hash: self.nominal_world_hash.as_deref(),
            visibility: "full_observer",
            production,
        };
        let mut output = EvidenceWriter {
            hash: Sha256::new(),
            remaining: MAX_EVIDENCE_BYTES,
            bound: false,
        };
        output.hash.update(DOMAIN);
        output.hash.update(VERSION.to_be_bytes());
        if encode_evidence(&mut output, &scope).is_err() {
            if output.bound {
                diagnostic_encoded_size(&scope);
            }
            return Err(if output.bound {
                ProductionEvidenceError::Bound
            } else {
                ProductionEvidenceError::Serialization
            });
        }
        Ok(Some(ProductionEvidenceDigest(
            output.hash.finalize().into(),
        )))
    }
}

// Coalesce the serializer's small fragments without changing their byte order.
// The final flush is part of admission: buffered suffixes must reach the bounded
// hash writer before any evidence digest can be returned.
fn encode_evidence(output: &mut EvidenceWriter, value: &impl Serialize) -> serde_json::Result<()> {
    let mut buffered = BufWriter::with_capacity(65_536, output);
    serde_json::to_writer(&mut buffered, value)?;
    buffered.flush().map_err(serde_json::Error::io)
}

fn diagnostic_cardinalities(rows: &ProductionSnapshot) {
    if std::env::var("BABYLON_TIMINGS").as_deref() != Ok("1") {
        return;
    }
    for (collection, count) in [
        ("sites", rows.sites.len()),
        ("routes", rows.routes.len()),
        ("physical_routes", rows.physical_routes.len()),
        (
            "freight_order_definitions",
            rows.freight_order_definitions.len(),
        ),
        ("freight", rows.freight.len()),
        ("labor_accounts", rows.labor_accounts.len()),
        ("staffing_accounts", rows.staffing_accounts.len()),
        (
            "freight_capacity_accounts",
            rows.freight_capacity_accounts.len(),
        ),
        (
            "merchant_handling_accounts",
            rows.merchant_handling_accounts.len(),
        ),
        ("final_demand_accounts", rows.final_demand_accounts.len()),
        ("household_accounts", rows.household_accounts.len()),
        (
            "household_service_accounts",
            rows.household_service_accounts.len(),
        ),
        ("goods_price_accounts", rows.goods_price_accounts.len()),
        ("observed_contexts", rows.observed_contexts.len()),
        (
            "national_observed_contexts",
            rows.national_observed_contexts.len(),
        ),
        ("process_attributions", rows.process_attributions.len()),
        ("physical_edges", rows.physical_edges.len()),
        ("events", rows.events.len()),
        ("provenance", rows.provenance.len()),
        (
            "site_processes_max",
            rows.sites
                .iter()
                .map(|r| r.processes.len())
                .max()
                .unwrap_or(0),
        ),
        (
            "site_inventory_max",
            rows.sites
                .iter()
                .map(|r| r.inventory.len())
                .max()
                .unwrap_or(0),
        ),
        (
            "route_stages_max",
            rows.physical_routes
                .iter()
                .map(|r| r.stages.len())
                .max()
                .unwrap_or(0),
        ),
        (
            "route_physical_edges_max",
            rows.physical_routes
                .iter()
                .map(|r| r.physical_edge_ids.len())
                .max()
                .unwrap_or(0),
        ),
    ] {
        eprintln!("production_evidence_cardinality collection={collection} count={count}");
    }
    let members = rows
        .staffing_accounts
        .iter()
        .try_fold(0_u128, |sum, r| sum.checked_add(r.members.len() as u128));
    match members {
        Some(count) => eprintln!(
            "production_evidence_cardinality collection=staffing_members_total count={count}"
        ),
        None => eprintln!(
            "production_evidence_cardinality collection=staffing_members_total count_overflow=true"
        ),
    }
}

/// Measure only a byte-bound refusal, without allocating serialized evidence.
fn diagnostic_encoded_size(scope: &EvidenceScope<'_>) {
    if std::env::var("BABYLON_TIMINGS").as_deref() != Ok("1") {
        return;
    }
    let started = std::time::Instant::now();
    let mut output = CountingEvidenceWriter {
        hash: Sha256::new(),
        body_bytes: 0,
    };
    output.hash.update(DOMAIN);
    output.hash.update(VERSION.to_be_bytes());
    if serde_json::to_writer(&mut output, scope).is_err() {
        eprintln!("production_evidence_encoded_size version={VERSION} status=counting_refused");
        return;
    }
    let Some(total_bytes) = output
        .body_bytes
        .checked_add(DOMAIN.len())
        .and_then(|length| length.checked_add(std::mem::size_of::<u32>()))
    else {
        eprintln!("production_evidence_encoded_size version={VERSION} status=length_overflow");
        return;
    };
    let body_bytes = output.body_bytes;
    if diagnostic_field_sizes(scope, body_bytes).is_err() {
        eprintln!("production_evidence_field_bytes status=counting_refused");
    }
    let framed_digest: [u8; 32] = output.hash.finalize().into();
    let framed_sha256 = crate::michigan_economy::digest_hex(&framed_digest);
    let elapsed_ns = started.elapsed().as_nanos();
    eprintln!(
        "production_evidence_encoded_size version={VERSION} status=measured_refusal body_bytes={body_bytes} framed_total_bytes={total_bytes} body_limit_bytes={MAX_EVIDENCE_BYTES} framed_sha256={framed_sha256} elapsed_ns={elapsed_ns}"
    );
}

fn diagnostic_field_sizes(scope: &EvidenceScope<'_>, expected_body: usize) -> io::Result<()> {
    let production_fields = diagnostic_production_fields(scope.production)?;
    let scope_fields = [
        ("campaign_id", diagnostic_value_bytes(&scope.campaign_id)?),
        ("resolve_tick", diagnostic_value_bytes(&scope.resolve_tick)?),
        (
            "foundation_digest",
            diagnostic_value_bytes(&scope.foundation_digest)?,
        ),
        (
            "tick_content_hash",
            diagnostic_value_bytes(&scope.tick_content_hash)?,
        ),
        (
            "envelope_digest",
            diagnostic_value_bytes(&scope.envelope_digest)?,
        ),
        (
            "nominal_world_hash",
            diagnostic_value_bytes(&scope.nominal_world_hash)?,
        ),
        ("visibility", diagnostic_value_bytes(&scope.visibility)?),
    ];
    let mut production_bytes = 2_usize;
    let mut production_values = 0_usize;
    for (index, (name, bytes)) in production_fields.iter().enumerate() {
        production_bytes = diagnostic_add_field(production_bytes, name, *bytes, index > 0)?;
        production_values = production_values
            .checked_add(*bytes)
            .ok_or_else(|| io::Error::other("evidence diagnostic length overflow"))?;
        let family = index + 1;
        eprintln!("production_evidence_field_bytes family={family} bytes={bytes}");
    }
    let mut body_bytes = 2_usize;
    let mut scope_values = 0_usize;
    for (index, (name, bytes)) in scope_fields.iter().enumerate() {
        body_bytes = diagnostic_add_field(body_bytes, name, *bytes, index > 0)?;
        scope_values = scope_values
            .checked_add(*bytes)
            .ok_or_else(|| io::Error::other("evidence diagnostic length overflow"))?;
        let family = production_fields.len() + index + 1;
        eprintln!("production_evidence_field_bytes family={family} bytes={bytes}");
    }
    body_bytes = diagnostic_add_field(body_bytes, "production", production_bytes, true)?;
    let production_framing = production_bytes - production_values;
    let scope_framing = body_bytes - production_bytes - scope_values;
    eprintln!("production_evidence_field_framing production_bytes={production_framing} scope_bytes={scope_framing}");
    let equal = body_bytes == expected_body;
    eprintln!("production_evidence_field_total production_bytes={production_bytes} body_bytes={body_bytes} expected_body_bytes={expected_body} exact={equal}");
    if !equal {
        return Err(io::Error::other(
            "evidence diagnostic fields do not reconcile",
        ));
    }
    Ok(())
}

fn diagnostic_production_fields(
    production: &ProductionSnapshot,
) -> io::Result<[(&'static str, usize); 25]> {
    Ok([
        (
            "scenario_label",
            diagnostic_value_bytes(&production.scenario_label)?,
        ),
        ("duration", diagnostic_value_bytes(&production.duration)?),
        (
            "content_authority_sha256",
            diagnostic_value_bytes(&production.content_authority_sha256)?,
        ),
        (
            "physical_edges",
            diagnostic_value_bytes(&production.physical_edges)?,
        ),
        (
            "road_source",
            diagnostic_value_bytes(&production.road_source)?,
        ),
        ("sites", diagnostic_value_bytes(&production.sites)?),
        ("routes", diagnostic_value_bytes(&production.routes)?),
        (
            "physical_routes",
            diagnostic_value_bytes(&production.physical_routes)?,
        ),
        ("freight", diagnostic_value_bytes(&production.freight)?),
        (
            "freight_capacity_accounts",
            diagnostic_value_bytes(&production.freight_capacity_accounts)?,
        ),
        (
            "freight_order_definitions",
            diagnostic_value_bytes(&production.freight_order_definitions)?,
        ),
        ("events", diagnostic_value_bytes(&production.events)?),
        (
            "merchant_handling_accounts",
            diagnostic_value_bytes(&production.merchant_handling_accounts)?,
        ),
        (
            "final_demand_accounts",
            diagnostic_value_bytes(&production.final_demand_accounts)?,
        ),
        (
            "household_accounts",
            diagnostic_value_bytes(&production.household_accounts)?,
        ),
        (
            "household_service_accounts",
            diagnostic_value_bytes(&production.household_service_accounts)?,
        ),
        (
            "goods_price_accounts",
            diagnostic_value_bytes(&production.goods_price_accounts)?,
        ),
        (
            "maintenance_account",
            diagnostic_value_bytes(&production.maintenance_account)?,
        ),
        (
            "labor_accounts",
            diagnostic_value_bytes(&production.labor_accounts)?,
        ),
        (
            "staffing_accounts",
            diagnostic_value_bytes(&production.staffing_accounts)?,
        ),
        (
            "material_balance",
            diagnostic_value_bytes(&production.material_balance)?,
        ),
        (
            "observed_contexts",
            diagnostic_value_bytes(&production.observed_contexts)?,
        ),
        (
            "national_observed_contexts",
            diagnostic_value_bytes(&production.national_observed_contexts)?,
        ),
        (
            "process_attributions",
            diagnostic_value_bytes(&production.process_attributions)?,
        ),
        (
            "provenance",
            diagnostic_value_bytes(&production.provenance)?,
        ),
    ])
}

fn diagnostic_add_field(total: usize, name: &str, bytes: usize, comma: bool) -> io::Result<usize> {
    total
        .checked_add(name.len())
        .and_then(|n| n.checked_add(3 + usize::from(comma)))
        .and_then(|n| n.checked_add(bytes))
        .ok_or_else(|| io::Error::other("evidence diagnostic length overflow"))
}

fn diagnostic_value_bytes(value: &impl Serialize) -> io::Result<usize> {
    let mut output = EvidenceByteCounter { bytes: 0 };
    serde_json::to_writer(&mut output, value).map_err(io::Error::other)?;
    Ok(output.bytes)
}

struct EvidenceByteCounter {
    bytes: usize,
}
impl Write for EvidenceByteCounter {
    fn write(&mut self, bytes: &[u8]) -> io::Result<usize> {
        self.bytes = self
            .bytes
            .checked_add(bytes.len())
            .ok_or_else(|| io::Error::other("evidence diagnostic length overflow"))?;
        Ok(bytes.len())
    }
    fn flush(&mut self) -> io::Result<()> {
        Ok(())
    }
}

struct CountingEvidenceWriter {
    hash: Sha256,
    body_bytes: usize,
}
impl Write for CountingEvidenceWriter {
    fn write(&mut self, bytes: &[u8]) -> io::Result<usize> {
        self.body_bytes = self.body_bytes.checked_add(bytes.len()).ok_or_else(|| {
            io::Error::new(
                io::ErrorKind::InvalidData,
                "evidence diagnostic length overflow",
            )
        })?;
        self.hash.update(bytes);
        Ok(bytes.len())
    }
    fn flush(&mut self) -> io::Result<()> {
        Ok(())
    }
}

struct EvidenceWriter {
    hash: Sha256,
    remaining: usize,
    bound: bool,
}
impl Write for EvidenceWriter {
    fn write(&mut self, bytes: &[u8]) -> io::Result<usize> {
        if bytes.len() > self.remaining {
            self.bound = true;
            bound(
                BoundReason::EncodedBytes,
                (MAX_EVIDENCE_BYTES - self.remaining) as u128 + bytes.len() as u128,
                MAX_EVIDENCE_BYTES,
            );
            return Err(io::Error::new(
                io::ErrorKind::InvalidData,
                "production evidence byte bound",
            ));
        }
        self.remaining -= bytes.len();
        self.hash.update(bytes);
        Ok(bytes.len())
    }
    fn flush(&mut self) -> io::Result<()> {
        Ok(())
    }
}

// Closed bound labels only; never log identities or disclosed values.
#[derive(Debug, Clone, Copy)]
enum BoundReason {
    Sites,
    Routes,
    PhysicalRoutes,
    Freight,
    LaborAccounts,
    StaffingAccounts,
    FreightCapacityAccounts,
    MerchantHandlingAccounts,
    FinalDemandAccounts,
    HouseholdAccounts,
    HouseholdServiceAccounts,
    GoodsPriceAccounts,
    ObservedContexts,
    NationalObservedContexts,
    ProcessAttributions,
    PhysicalEdges,
    Events,
    SiteProcesses,
    SiteInventory,
    RoutePhysicalEdges,
    RouteStages,
    StaffingMembers,
    StaffingMemberSum,
    ObservedMemberSum,
    EncodedBytes,
}

fn bound(reason: BoundReason, observed: u128, limit: usize) -> ProductionEvidenceError {
    if std::env::var("BABYLON_TIMINGS").as_deref() == Ok("1") {
        eprintln!("production_evidence_bound reason={reason:?} observed={observed} limit={limit}");
    }
    ProductionEvidenceError::Bound
}

fn check_bound(reason: BoundReason, observed: usize, limit: usize) -> Result<()> {
    if observed > limit {
        return Err(bound(reason, observed as u128, limit));
    }
    Ok(())
}

fn diagnostic_validation_refusal(check: &'static str, family: &'static str) {
    if std::env::var("BABYLON_TIMINGS").as_deref() == Ok("1") {
        eprintln!("production_evidence_refused check={check} family={family}");
    }
}

fn diagnostic_validation(label: &'static str, result: Result<()>) -> Result<()> {
    if result.is_err() {
        diagnostic_validation_refusal("validation", label);
    }
    result
}

fn unique<T: Ord>(label: &'static str, rows: impl IntoIterator<Item = T>) -> Result<()> {
    let mut ids = BTreeSet::new();
    for id in rows {
        if !ids.insert(id) {
            diagnostic_validation_refusal("unique", label);
            return Err(ProductionEvidenceError::InvalidIdentity);
        }
    }
    Ok(())
}

fn validate_source_contexts(rows: &ProductionSnapshot) -> Result<()> {
    let sites: std::collections::BTreeMap<_, _> =
        rows.sites.iter().map(|r| (r.id.as_str(), r)).collect();
    for site in &rows.sites {
        if site.roles.is_empty() {
            return Err(ProductionEvidenceError::InvalidIdentity);
        }
        unique("site_roles", &site.roles)?;
    }
    for row in &rows.national_observed_contexts {
        let site = sites
            .get(row.site_id.as_str())
            .ok_or(ProductionEvidenceError::InvalidIdentity)?;
        if !site.is_in_county(&row.county_geoid)
            || site.function != row.function
            || row.evidence_class != crate::ArchiveEvidenceClass::Observed
        {
            return Err(ProductionEvidenceError::InvalidIdentity);
        }
        let mut member_count = None;
        for cell in [
            &row.establishments,
            &row.annual_average_jobs,
            &row.annual_payroll_usd,
        ] {
            let count = cell
                .published_members
                .checked_add(cell.missing_members)
                .ok_or_else(|| {
                    bound(
                        BoundReason::ObservedMemberSum,
                        cell.published_members as u128 + cell.missing_members as u128,
                        usize::MAX,
                    )
                })?;
            if count == 0 || member_count.is_some_and(|n| n != count) {
                return Err(ProductionEvidenceError::InvalidIdentity);
            }
            member_count = Some(count);
        }
        if site.observed_employment
            != (row.annual_average_jobs.missing_members == 0)
                .then_some(row.annual_average_jobs.known_subtotal)
        {
            return Err(ProductionEvidenceError::InvalidIdentity);
        }
    }
    Ok(())
}

fn validate_member_identities(rows: &ProductionSnapshot) -> Result<()> {
    let member_count = rows.staffing_accounts.iter().try_fold(0_usize, |n, row| {
        n.checked_add(row.members.len()).ok_or_else(|| {
            bound(
                BoundReason::StaffingMemberSum,
                n as u128 + row.members.len() as u128,
                usize::MAX,
            )
        })
    })?;
    check_bound(
        BoundReason::StaffingMembers,
        member_count,
        babylon_material_circuit::MAX_STAFFING_MEMBERS,
    )?;
    unique(
        "staffing_member_ids",
        rows.staffing_accounts
            .iter()
            .flat_map(|row| row.members.iter().map(|member| &member.member_id)),
    )?;
    Ok(())
}

fn validate_collection_bounds(rows: &ProductionSnapshot) -> Result<()> {
    for (reason, count) in [
        (BoundReason::Sites, rows.sites.len()),
        (BoundReason::Routes, rows.routes.len()),
        (BoundReason::PhysicalRoutes, rows.physical_routes.len()),
        (BoundReason::Freight, rows.freight.len()),
        (BoundReason::LaborAccounts, rows.labor_accounts.len()),
        (BoundReason::StaffingAccounts, rows.staffing_accounts.len()),
        (
            BoundReason::FreightCapacityAccounts,
            rows.freight_capacity_accounts.len(),
        ),
        (
            BoundReason::MerchantHandlingAccounts,
            rows.merchant_handling_accounts.len(),
        ),
        (
            BoundReason::FinalDemandAccounts,
            rows.final_demand_accounts.len(),
        ),
        (
            BoundReason::HouseholdAccounts,
            rows.household_accounts.len(),
        ),
        (
            BoundReason::HouseholdServiceAccounts,
            rows.household_service_accounts.len(),
        ),
        (
            BoundReason::GoodsPriceAccounts,
            rows.goods_price_accounts.len(),
        ),
        (BoundReason::ObservedContexts, rows.observed_contexts.len()),
        (
            BoundReason::NationalObservedContexts,
            rows.national_observed_contexts.len(),
        ),
        (
            BoundReason::ProcessAttributions,
            rows.process_attributions.len(),
        ),
    ] {
        let maximum = match reason {
            BoundReason::Routes | BoundReason::PhysicalRoutes => {
                babylon_material_circuit::MAX_SUPPLIER_ROUTES
            }
            _ => MAX_ROWS,
        };
        check_bound(reason, count, maximum)?;
    }
    check_bound(
        BoundReason::PhysicalEdges,
        rows.physical_edges.len(),
        MAX_PHYSICAL_ROWS,
    )?;
    check_bound(BoundReason::Events, rows.events.len(), MAX_PHYSICAL_ROWS)?;
    Ok(())
}

fn validate_identities(rows: &ProductionSnapshot) -> Result<()> {
    validate_collection_bounds(rows)?;
    unique("site_ids", rows.sites.iter().map(|row| &row.id))?;
    unique(
        "process_ids",
        rows.sites
            .iter()
            .flat_map(|row| row.processes.iter().map(|row| &row.id)),
    )?;
    validate_route_identities(rows)?;
    unique(
        "national_observed_site_ids",
        rows.national_observed_contexts
            .iter()
            .map(|row| &row.site_id),
    )?;
    unique("freight_ids", rows.freight.iter().map(|row| &row.id))?;
    unique("event_ids", rows.events.iter().map(|row| &row.id))?;
    unique(
        "physical_edge_ids",
        rows.physical_edges.iter().map(|row| &row.id),
    )?;
    unique(
        "labor_site_unit",
        rows.labor_accounts
            .iter()
            .map(|row| (&row.site_id, &row.unit_id)),
    )?;
    validate_member_identities(rows)?;
    unique(
        "staffing_pool_ids",
        rows.staffing_accounts.iter().map(|row| &row.pool_id),
    )?;
    unique(
        "staffing_site_unit",
        rows.staffing_accounts
            .iter()
            .map(|row| (&row.site_id, &row.unit_id)),
    )?;
    unique(
        "freight_corridor_ids",
        rows.freight_capacity_accounts
            .iter()
            .map(|row| &row.corridor_id),
    )?;
    unique(
        "merchant_site_ids",
        rows.merchant_handling_accounts
            .iter()
            .map(|row| &row.site_id),
    )?;
    unique(
        "final_demand_principal_good_unit",
        rows.final_demand_accounts
            .iter()
            .map(|row| (&row.demand_principal_id, &row.good_id, &row.unit_id)),
    )?;
    unique(
        "household_principal_good_unit",
        rows.household_accounts
            .iter()
            .map(|row| (&row.demand_principal_id, &row.good_id, &row.unit_id)),
    )?;
    for site in &rows.sites {
        check_bound(BoundReason::SiteProcesses, site.processes.len(), MAX_ROWS)?;
        check_bound(BoundReason::SiteInventory, site.inventory.len(), MAX_ROWS)?;
        unique(
            "site_inventory_good_unit",
            site.inventory
                .iter()
                .map(|row| (&row.good_id, &row.unit_id)),
        )?;
        for process in &site.processes {
            unique(
                "process_input_good_unit",
                process
                    .inputs
                    .iter()
                    .map(|row| (&row.good_id, &row.unit_id)),
            )?;
        }
    }
    for route in &rows.physical_routes {
        check_bound(
            BoundReason::RoutePhysicalEdges,
            route.physical_edge_ids.len(),
            MAX_PHYSICAL_ROWS,
        )?;
        check_bound(BoundReason::RouteStages, route.stages.len(), 16)?;
        unique(
            "route_stage_indices",
            route.stages.iter().map(|row| row.stage_index),
        )?;
        for stage in &route.stages {
            unique("stage_capacity_ids", &stage.capacity_ids)?;
        }
    }
    validate_account_rows(rows)
}

fn validate_route_identities(rows: &ProductionSnapshot) -> Result<()> {
    unique("route_ids", rows.routes.iter().map(|row| &row.id))?;
    unique(
        "physical_route_ids",
        rows.physical_routes.iter().map(|row| &row.id),
    )?;
    crate::production_observation::PhysicalRouteIndex::try_new(rows).map_err(
        |error| match error {
            crate::production_observation::PhysicalRouteError::Bound => {
                ProductionEvidenceError::Bound
            }
            _ => ProductionEvidenceError::InvalidIdentity,
        },
    )?;
    Ok(())
}

fn validate_account_rows(rows: &ProductionSnapshot) -> Result<()> {
    crate::production_observation::FreightOrderIndex::try_new(rows).map_err(|error| {
        if error == crate::production_observation::FreightOrderError::Bound {
            ProductionEvidenceError::Bound
        } else {
            ProductionEvidenceError::InvalidIdentity
        }
    })?;
    for account in &rows.freight_capacity_accounts {
        unique("capacity_route_ids", &account.route_ids)?;
        unique("capacity_merchant_site_ids", &account.merchant_site_ids)?;
        if let Some(completed) = &account.completed {
            unique(
                "capacity_reservation_periods",
                completed
                    .reservations
                    .iter()
                    .map(|row| row.reservation_period),
            )?;
            for row in &completed.reservations {
                unique(
                    "capacity_support_commitment_ids",
                    row.support_orders.iter().map(|row| &row.commitment_id),
                )?;
            }
        }
    }
    for account in &rows.merchant_handling_accounts {
        unique(
            "merchant_coefficient_good_unit",
            account
                .coefficients
                .iter()
                .map(|row| (&row.good_id, &row.unit_id)),
        )?;
        if let Some(completed) = &account.completed {
            unique(
                "merchant_order_kind_id",
                completed.orders.iter().map(|row| (row.kind, &row.order_id)),
            )?;
        }
    }
    for account in &rows.final_demand_accounts {
        unique("final_demand_retailer_site_ids", &account.retailer_site_ids)?;
        unique(
            "final_demand_order_ids",
            account.orders.iter().map(|row| &row.order_id),
        )?;
    }
    if let Some(balance) = &rows.material_balance {
        unique(
            "balance_site_good_unit",
            balance
                .rows
                .iter()
                .map(|row| (&row.site_id, &row.good_id, &row.unit_id)),
        )?;
    }
    Ok(())
}

fn validate_households(rows: &ProductionSnapshot, period: u64) -> Result<()> {
    for row in &rows.household_accounts {
        if !row
            .kind
            .admits_counts(row.person_count, row.household_count)
            || row.required_per_period == 0
        {
            return Err(ProductionEvidenceError::InvalidIdentity);
        }
        match (&row.completed, period) {
            (None, 0) => {}
            (Some(done), period)
                if period > 0
                    && done.period == period
                    && done.required == row.required_per_period
                    && done.closing_stock == row.stock_on_hand
                    && u128::from(done.opening_stock)
                        + u128::from(done.received)
                        + u128::from(done.support_granted)
                        == u128::from(done.consumed)
                            + u128::from(done.closing_stock)
                            + u128::from(done.support_dispatched)
                    && done.consumed.checked_add(done.unmet) == Some(done.required)
                    && done.fulfilled.checked_add(done.expired) == Some(done.admitted)
                    && done.fulfilled <= done.received
                    && done.admitted <= done.requested
                    && done.requested <= done.desired => {}
            _ => return Err(ProductionEvidenceError::InvalidIdentity),
        }
    }
    Ok(())
}

fn validate_household_services(rows: &ProductionSnapshot, period: u64) -> Result<()> {
    unique(
        "household_service_principal_good_unit",
        rows.household_service_accounts
            .iter()
            .map(|r| (&r.demand_principal_id, &r.good_id, &r.unit_id)),
    )?;
    for row in &rows.household_service_accounts {
        unique("household_service_provider_ids", &row.provider_site_ids)?;
        if !row
            .kind
            .admits_counts(row.person_count, row.household_count)
            || row.required_per_period == 0
        {
            return Err(ProductionEvidenceError::InvalidIdentity);
        }
        match (&row.completed, period) {
            (None, 0) => {}
            (Some(done), period)
                if period > 0
                    && done.period == period
                    && done.required == row.required_per_period
                    && done.satisfied == done.required.min(done.performed)
                    && done.satisfied.checked_add(done.unmet) == Some(done.required)
                    && done.satisfied.checked_add(done.unused) == Some(done.performed)
                    && done.performed.checked_add(done.expired) == Some(done.admitted)
                    && done.admitted <= done.requested => {}
            _ => return Err(ProductionEvidenceError::InvalidIdentity),
        }
    }
    Ok(())
}

fn validate_goods_prices(rows: &ProductionSnapshot, period: u64) -> Result<()> {
    unique(
        "price_site_good_unit",
        rows.goods_price_accounts
            .iter()
            .map(|r| (&r.site_id, &r.good_id, &r.unit_id)),
    )?;
    for row in &rows.goods_price_accounts {
        if row.current_price_micro <= 0 {
            return Err(ProductionEvidenceError::InvalidIdentity);
        }
        match (&row.completed, period) {
            (None, 0) => {}
            (Some(done), period) if period > 0 && done.valid(period, row.current_price_micro) => {}
            _ => return Err(ProductionEvidenceError::InvalidIdentity),
        }
    }
    Ok(())
}

fn validate_maintenance(rows: &ProductionSnapshot, period: u64) -> Result<()> {
    use crate::production_observation::ProductionSiteRole;
    let Some(account) = &rows.maintenance_account else {
        if rows
            .sites
            .iter()
            .any(|site| site.roles.contains(&ProductionSiteRole::Maintenance))
        {
            return Err(ProductionEvidenceError::InvalidIdentity);
        }
        return Ok(());
    };
    let provider = rows
        .sites
        .iter()
        .find(|site| site.id == account.provider_site_id);
    let consumer = rows
        .sites
        .iter()
        .find(|site| site.id == account.consumer_site_id);
    let process = consumer.and_then(|site| {
        site.processes
            .iter()
            .find(|process| process.id == account.consumer_process_id)
    });
    if !provider.is_some_and(|site| {
        site.roles.contains(&ProductionSiteRole::Maintenance) && site.processes.is_empty()
    }) || rows
        .sites
        .iter()
        .filter(|site| site.roles.contains(&ProductionSiteRole::Maintenance))
        .count()
        != 1
        || account.provider_site_id == account.consumer_site_id
        || !process.is_some_and(|process| {
            process.output_good_id == account.output_good_id
                && process.output_unit_id == account.output_unit_id
                && process.output_per_batch == account.output_per_batch
        })
        || account.spare_good_id != account.output_good_id
        || account.spare_unit_id != account.output_unit_id
        || !rows.labor_accounts.iter().any(|labor| {
            labor.site_id == account.provider_site_id && labor.unit_id == account.labor_unit_id
        })
        || account.spare_units_per_job == 0
        || account.labor_units_per_job == 0
        || account.enabled_batches_per_job == 0
        || account.output_per_batch == 0
        || period.checked_add(1) != Some(account.next_service_period)
        || account
            .next_service_batches
            .checked_mul(account.output_per_batch)
            .is_none()
    {
        return Err(ProductionEvidenceError::InvalidIdentity);
    }
    let Some(done) = &account.completed else {
        return if period == 0 {
            Ok(())
        } else {
            Err(ProductionEvidenceError::InvalidIdentity)
        };
    };
    let requested = done.prospective_batches / account.enabled_batches_per_job
        + u64::from(
            !done
                .prospective_batches
                .is_multiple_of(account.enabled_batches_per_job),
        );
    let feasible = requested
        .min(account.maximum_jobs_per_period)
        .min(done.available_spare_parts / account.spare_units_per_job)
        .min(done.available_labor_hours / account.labor_units_per_job);
    if period == 0
        || done.period != period
        || done.requested_jobs != requested
        || done.completed_jobs != feasible
        || done
            .opening_spare_parts
            .checked_add(done.arrived_spare_parts)
            != Some(done.available_spare_parts)
        || done
            .consumed_service_batches
            .checked_add(done.expired_service_batches)
            != Some(done.opening_service_batches)
        || done.completed_jobs.checked_mul(account.spare_units_per_job)
            != Some(done.consumed_spare_parts)
        || done.completed_jobs.checked_mul(account.labor_units_per_job)
            != Some(done.consumed_labor_hours)
        || done
            .completed_jobs
            .checked_mul(account.enabled_batches_per_job)
            != Some(account.next_service_batches)
    {
        return Err(ProductionEvidenceError::InvalidIdentity);
    }
    Ok(())
}

fn canonicalize_production(rows: &mut ProductionSnapshot) {
    rows.freight_order_definitions.sort_unstable();
    for site in &mut rows.sites {
        site.roles.sort_unstable();
        site.inventory.sort_unstable();
        for process in &mut site.processes {
            for input in &mut process.inputs {
                input.supplier_site_ids.sort_unstable();
            }
            process.inputs.sort_unstable();
            process.labor.sort_unstable();
        }
        site.processes.sort_unstable();
    }
    rows.sites.sort_unstable();
    rows.labor_accounts.sort_unstable();
    for pool in &mut rows.staffing_accounts {
        pool.members.sort_unstable();
    }
    rows.staffing_accounts.sort_unstable();
    if let Some(balance) = &mut rows.material_balance {
        balance.rows.sort_unstable();
    }
    rows.observed_contexts.sort_unstable();
    rows.national_observed_contexts.sort_unstable();
    rows.process_attributions.sort_unstable();
    rows.physical_edges.sort_unstable();
    for route in &mut rows.physical_routes {
        for stage in &mut route.stages {
            stage.capacity_ids.sort_unstable();
        }
        route.stages.sort_unstable();
    }
    rows.physical_routes.sort_unstable();
    rows.routes.sort_unstable();
    for account in &mut rows.freight_capacity_accounts {
        account.route_ids.sort_unstable();
        account.merchant_site_ids.sort_unstable();
        if let Some(completed) = &mut account.completed {
            for reservation in &mut completed.reservations {
                reservation.orders.sort_unstable();
                reservation.support_orders.sort_unstable();
            }
            completed.reservations.sort_unstable();
        }
    }
    rows.freight_capacity_accounts.sort_unstable();
    for account in &mut rows.merchant_handling_accounts {
        account.coefficients.sort_unstable();
        if let Some(completed) = &mut account.completed {
            completed.orders.sort_unstable();
        }
    }
    rows.merchant_handling_accounts.sort_unstable();
    for account in &mut rows.final_demand_accounts {
        account.orders.sort_unstable();
        account.retailer_site_ids.sort_unstable();
    }
    rows.final_demand_accounts.sort_unstable();
    rows.household_accounts.sort_unstable();
    for row in &mut rows.household_service_accounts {
        row.provider_site_ids.sort_unstable();
    }
    rows.household_service_accounts.sort_unstable();
    rows.goods_price_accounts.sort_unstable();
    rows.freight.sort_unstable();
    for event in &mut rows.events {
        event.subject_site_ids.sort_unstable();
    }
    rows.provenance.sort_unstable();
}

#[cfg(test)]
mod tests;
