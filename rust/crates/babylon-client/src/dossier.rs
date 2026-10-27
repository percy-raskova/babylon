//! One scoped Archive observation shared by native composition and headless JSONL.

use std::io::Write;
use std::num::NonZero;

use babylon_persistence::archive_revision::{
    ArchiveAtomChange, ArchiveDossierBounds, ArchiveDossierPage, ArchiveDossierPending,
    ArchiveDossierRead, ArchiveDossierState, ArchiveDossierUnavailable, ArchiveLinkedPageState,
    ArchiveReadScope, ArchiveSearchState,
};
use babylon_persistence::identity::CampaignId;
use babylon_persistence::sqlite_store::CampaignHandle;
use babylon_persistence::sqlite_store::PlayerBody;
use babylon_persistence::sqlite_store::PlayerQuery;
use babylon_persistence::sqlite_store::PlayerScope;
use babylon_persistence::sqlite_store::SubjectKind;
use babylon_persistence::CampaignQueryReader;
use babylon_persistence::{ArchiveAtom, ArchivePageRef, ArchiveSubjectKind, SemanticArchiveReader};

use bevy::app::AppExit;
use bevy::prelude::{MessageWriter, Res, Resource};
use serde_json::{json, Value};

use crate::cli::CliCommand;
use serde_json::Number;

/// The retained page is readable while pending, but that is not verification.
#[must_use]
pub fn retained_page(read: &ArchiveDossierRead) -> Option<&ArchiveDossierPage> {
    match &read.state {
        ArchiveDossierState::Ready { page, .. }
        | ArchiveDossierState::Pending {
            page: Some(page), ..
        } => Some(page),
        ArchiveDossierState::Pending { page: None, .. } | ArchiveDossierState::Unavailable(_) => {
            None
        }
    }
}

/// Only the reader's exact selected-page result certifies this observation.
#[must_use]
pub const fn verified_tick(read: &ArchiveDossierRead) -> Option<u64> {
    match &read.state {
        ArchiveDossierState::Ready {
            verified_through_tick,
            ..
        } => Some(*verified_through_tick),
        _ => None,
    }
}

/// Static availability wording shared by the card and CLI.
#[must_use]
pub const fn availability_label(read: &ArchiveDossierRead) -> &'static str {
    match &read.state {
        ArchiveDossierState::Ready { .. } => "Verified for this viewed period",
        ArchiveDossierState::Pending { reason, .. } => pending_label(*reason),
        ArchiveDossierState::Unavailable(reason) => unavailable_label(*reason),
    }
}

pub(crate) const fn pending_label(reason: ArchiveDossierPending) -> &'static str {
    match reason {
        ArchiveDossierPending::ReceiptProcessing => "Archive is still processing this observation",
        ArchiveDossierPending::KnowledgeRefresh => {
            "Newly learned information awaits Archive publication"
        }
    }
}

pub(crate) const fn unavailable_label(reason: ArchiveDossierUnavailable) -> &'static str {
    match reason {
        ArchiveDossierUnavailable::FoundationHasNoPage => {
            "The campaign foundation has no published Archive page"
        }
        ArchiveDossierUnavailable::SubjectNotDisclosed => {
            "This subject is not disclosed in this observation"
        }
        ArchiveDossierUnavailable::PageNotMaterialized => {
            "No Archive page has been published for this subject at this period"
        }
    }
}

pub(crate) const fn link_state_label(state: ArchiveLinkedPageState) -> &'static str {
    match state {
        ArchiveLinkedPageState::Unknown => "unknown",
        ArchiveLinkedPageState::KnownUnavailable => "unavailable",
        ArchiveLinkedPageState::KnownPending => "pending",
        ArchiveLinkedPageState::KnownReady => "ready",
    }
}

/// Bind the exact installed observation, never the session's newer durable hash.
///
/// # Errors
/// Refuses a missing or noncanonical positive-tick identity, or a fabricated foundation hash.
pub fn observation_scope(
    campaign: CampaignId,
    tick: u64,
    hash: Option<&str>,
) -> Result<ArchiveReadScope, String> {
    if tick == 0 {
        return if hash.is_none() {
            Ok(ArchiveReadScope::foundation(campaign))
        } else {
            Err("Foundation cannot carry a committed tick hash".into())
        };
    }
    let hash = hash.ok_or("The installed observation has no committed identity")?;
    if hash.len() != 64
        || !hash
            .bytes()
            .all(|byte| byte.is_ascii_digit() || (b'a'..=b'f').contains(&byte))
    {
        return Err("The installed observation has a noncanonical committed identity".into());
    }
    let mut bytes = [0; 32];
    for (index, byte) in bytes.iter_mut().enumerate() {
        *byte = u8::from_str_radix(&hash[index * 2..index * 2 + 2], 16)
            .map_err(|_| "The installed observation has an invalid committed identity")?;
    }
    ArchiveReadScope::committed(campaign, tick, bytes).map_err(|error| error.to_string())
}

/// One CLI invocation; live commands pin a marker once before their scoped reads.
#[derive(Resource, Clone, Debug)]
pub struct HeadlessInvocation {
    command: CliCommand,
    campaign_id: CampaignId,
}
impl HeadlessInvocation {
    /// Capture one parsed command and campaign.
    #[must_use]
    pub const fn new(command: CliCommand, campaign_id: CampaignId) -> Self {
        Self {
            command,
            campaign_id,
        }
    }
}

/// Execute a scoped command, returning a process exit code.
#[must_use]
pub fn run_headless(invocation: &HeadlessInvocation) -> u8 {
    match execute(invocation) {
        Ok(()) => 0,
        Err(message) => {
            eprintln!("babylon-client: {message}");
            2
        }
    }
}

pub(crate) fn pinned_scope(
    reader: &SemanticArchiveReader,
    campaign: CampaignId,
) -> Result<ArchiveReadScope, String> {
    reader
        .committed_tick_status(campaign)
        .map_err(|error| error.to_string())?
        .map_or_else(
            || Ok(ArchiveReadScope::foundation(campaign)),
            |status| {
                ArchiveReadScope::committed(
                    campaign,
                    status.resolve_tick(),
                    *status.tick_content_hash(),
                )
                .map_err(|error| error.to_string())
            },
        )
}

fn county_subject(geoid: &str) -> Result<ArchivePageRef, String> {
    ArchivePageRef::try_new(ArchiveSubjectKind::County, geoid.into())
        .map_err(|error| error.to_string())
}

fn execute(invocation: &HeadlessInvocation) -> Result<(), String> {
    let reader = SemanticArchiveReader::from_env().map_err(|error| error.to_string())?;
    let mut out = std::io::stdout().lock();
    if invocation.command == CliCommand::EconomyStatus {
        write_jsonl(
            &mut out,
            &crate::economy_status::read(&reader, invocation.campaign_id)?,
        )?;
    } else if invocation.command == CliCommand::TickStatus {
        write_jsonl(&mut out, &tick_status_row(&reader, invocation.campaign_id)?)?;
    } else {
        let scope = pinned_scope(&reader, invocation.campaign_id)?;
        match &invocation.command {
            CliCommand::DossierShow { geoid } => {
                let read = reader
                    .dossier_as_of(
                        &scope,
                        &county_subject(geoid)?,
                        &ArchiveDossierBounds::default(),
                    )
                    .map_err(|error| error.to_string())?;
                write_jsonl(&mut out, &dossier_json(&read))?;
            }
            CliCommand::DossierSearch { query } => write_search(&mut out, &reader, &scope, query)?,
            CliCommand::Changelog { geoid } => {
                write_changes(&mut out, &reader, &scope, &county_subject(geoid)?)?;
            }
            CliCommand::TickStatus | CliCommand::EconomyStatus => unreachable!("handled above"),
        }
    }
    out.flush().map_err(|error| error.to_string())
}

fn write_search(
    out: &mut impl Write,
    reader: &SemanticArchiveReader,
    scope: &ArchiveReadScope,
    query: &str,
) -> Result<(), String> {
    let read = reader
        .search_as_of(scope, query, 50)
        .map_err(|error| error.to_string())?;
    let (state, reason) = match read.state {
        ArchiveSearchState::Ready => ("ready", None),
        ArchiveSearchState::Pending(reason) => ("pending", Some(pending_label(reason))),
        ArchiveSearchState::Unavailable(reason) => ("unavailable", Some(unavailable_label(reason))),
    };
    write_jsonl(
        out,
        &json!({"record":"archive-search-status", "scope":scope_json(&read.scope),
        "state":state,"reason":reason,"durable_tick":read.durable_tick,"processed_tick":read.processed_tick,
        "truncated":read.truncated}),
    )?;
    for hit in read.hits {
        write_jsonl(
            out,
            &json!({"record":"search-hit","subject_kind":hit.subject.kind().as_str(),
            "geoid":hit.subject.id(),"title":hit.title,"revision_id":hex_bytes(hit.revision_id),
            "content_source":scope_json(&hit.content_source)}),
        )?;
    }
    Ok(())
}

fn write_changes(
    out: &mut impl Write,
    reader: &SemanticArchiveReader,
    scope: &ArchiveReadScope,
    subject: &ArchivePageRef,
) -> Result<(), String> {
    let mut cursor = None;
    loop {
        let bounds =
            ArchiveDossierBounds::try_new(32, cursor.clone()).map_err(|error| error.to_string())?;
        let read = reader
            .dossier_as_of(scope, subject, &bounds)
            .map_err(|error| error.to_string())?;
        write_jsonl(
            out,
            &json!({"record":"archive-changes-page","scope":scope_json(&read.scope),
            "subject":read.subject,"availability":availability_label(&read),
            "coverage_from_tick":retained_page(&read).map(|page|page.changes.coverage_from_tick),
            "has_more":retained_page(&read).is_some_and(|page|page.changes.next_cursor.is_some())}),
        )?;
        let Some(page) = retained_page(&read) else {
            return Ok(());
        };
        for change in &page.changes.changes {
            write_jsonl(out, &change_json(change))?;
        }
        let Some(next) = &page.changes.next_cursor else {
            return Ok(());
        };
        if cursor.as_ref() == Some(next) {
            return Err("Archive continuation did not advance".into());
        }
        cursor = Some(next.clone());
    }
}

/// Execute the one headless invocation and request application exit.
pub fn run_headless_command(invocation: Res<HeadlessInvocation>, mut exit: MessageWriter<AppExit>) {
    let code = run_headless(&invocation);
    exit.write(match NonZero::<u8>::new(code) {
        Some(code) => AppExit::Error(code),
        None => AppExit::Success,
    });
}

pub(crate) fn scope_json(scope: &ArchiveReadScope) -> Value {
    json!({"campaign_id":scope.campaign_id().as_uuid().to_string(),"tick":scope.tick(),
        "tick_content_hash":scope.tick_content_hash().map(hex_bytes)})
}

pub(crate) fn dossier_json(read: &ArchiveDossierRead) -> Value {
    let page = retained_page(read);
    let state = match read.state {
        ArchiveDossierState::Ready { .. } => "ready",
        ArchiveDossierState::Pending { .. } => "pending",
        ArchiveDossierState::Unavailable(_) => "unavailable",
    };
    json!({"record":"county-dossier","schema_version":2,"scope":scope_json(&read.scope),"subject":read.subject,
        "geoid":read.subject.id(),"state":state,"availability":availability_label(read),
        "durable_tick":read.durable_tick,"processed_tick":read.processed_tick,"verified_tick":verified_tick(read),
        "page":page.map(|page| json!({"title":page.title,"question":page.question,
            "revision_id":hex_bytes(page.revision_id),"content_source":scope_json(&page.content_source),
            "content_sha256":hex_bytes(page.content_sha256),"effective_tick":page.effective_tick,"markdown":page.markdown,
            "citations":page.citations.iter().map(|citation|json!({"source_id":citation.source_id(),"locator":citation.locator()})).collect::<Vec<_>>(),
            "signals":page.signals.iter().map(|signal|json!({"grant_key":signal.grant_key(),"label":signal.label(),
                "value":signal.value(),"citation":{"source_id":signal.citation().source_id(),"locator":signal.citation().locator()}})).collect::<Vec<_>>(),
            "atoms":page.atoms.iter().map(atom_json).collect::<Vec<_>>(),
            "links":page.links.iter().map(|link|json!({"target":link.target,"label":link.retained_label,
                "state":link_state_label(link.target_state)})).collect::<Vec<_>>(),
            "coverage_from_tick":page.changes.coverage_from_tick,
            "changes":page.changes.changes.iter().map(change_json).collect::<Vec<_>>(),
            "has_more_changes":page.changes.next_cursor.is_some()}))})
}

pub(crate) fn change_json(change: &ArchiveAtomChange) -> Value {
    json!({"record":"changelog-row","publication_tick":change.publication_tick,"signal_key":change.signal_key,
        "before":change.before.as_ref().map(atom_json),"after":change.after.as_ref().map(atom_json)})
}

fn atom_json(atom: &ArchiveAtom) -> Value {
    json!({"signal_key":atom.signal_key(),"grant_key":atom.grant_key(),"evidence_class":atom.evidence_class().as_str(),
        "value":atom_value_json(atom.value()),"valid_tick":atom.valid_tick(),"atom_id":hex_bytes(atom.atom_id()),
        "citation":{"source_id":atom.citation().source_id(),"locator":atom.citation().locator()}})
}

pub(crate) fn atom_value_json(value: &babylon_persistence::ArchiveAtomValue) -> Value {
    match value {
        babylon_persistence::ArchiveAtomValue::Text(text) => Value::String(text.clone()),
        babylon_persistence::ArchiveAtomValue::F64(number) => {
            Number::from_f64(*number).map_or(Value::Null, Value::Number)
        }
        babylon_persistence::ArchiveAtomValue::U64(number) => Value::from(*number),
        babylon_persistence::ArchiveAtomValue::Bool(flag) => Value::from(*flag),
    }
}

pub(crate) fn hex_bytes(bytes: [u8; 32]) -> String {
    let mut rendered = String::with_capacity(64);
    for byte in bytes {
        use std::fmt::Write as _;
        let _ = write!(rendered, "{byte:02x}");
    }
    rendered
}

fn write_jsonl(out: &mut impl Write, value: &Value) -> Result<(), String> {
    writeln!(out, "{value}").map_err(|error| error.to_string())
}

/// Run one scoped headless command against an in-process campaign owner.
///
/// This is the local-campaign read surface: it answers the same headless
/// commands the Archive reader answers, but every answer is a closed
/// [`PlayerQuery`] inside one [`PlayerScope`] served from bounded rows. It never
/// opens a second writer, so the process that owns the campaign stays the only
/// one that can mutate it.
///
/// No shipped path calls this yet: the binary's headless system still runs
/// `run_headless` against the Archive reader, and a separate client process
/// cannot legitimately open a campaign file. `SqliteCampaignStore::open`
/// requires the caller's `BuildIdentity` (no producer exists before the runtime
/// cutover) and the campaign lock admits a single owner. Wiring a `CliCommand`
/// variant through this surface is therefore deferred to the runtime
/// composition root in Task 13/14; until then only the client unit tests in this
/// module exercise it.
#[must_use]
pub fn run_scoped_headless(
    invocation: &HeadlessInvocation,
    handle: &CampaignHandle,
    player_id: [u8; 8],
) -> u8 {
    match execute_scoped(invocation, handle, player_id) {
        Ok(()) => 0,
        Err(message) => {
            eprintln!("babylon-client: {message}");
            2
        }
    }
}

fn execute_scoped(
    invocation: &HeadlessInvocation,
    handle: &CampaignHandle,
    player_id: [u8; 8],
) -> Result<(), String> {
    let reader = CampaignQueryReader::new(handle);
    let scope = reader
        .current_scope(player_id)
        .map_err(|error| error.to_string())?;
    let mut out = std::io::stdout().lock();
    let row = match &invocation.command {
        CliCommand::DossierShow { geoid } => scoped_dossier_row(reader, scope, geoid)?,
        CliCommand::Changelog { geoid } => scoped_changelog_row(reader, scope, geoid)?,
        CliCommand::EconomyStatus => scoped_map_row(reader, scope)?,
        CliCommand::TickStatus => scoped_tick_row(reader, scope)?,
        CliCommand::DossierSearch { .. } => {
            return Err("search is not served by the local campaign query surface".into());
        }
    };
    write_jsonl(&mut out, &row)?;
    out.flush().map_err(|error| error.to_string())
}

/// Render one earned county dossier from the scoped query surface.
fn scoped_dossier_row(
    reader: CampaignQueryReader<'_>,
    scope: PlayerScope,
    geoid: &str,
) -> Result<Value, String> {
    let subject_id = county_subject_id(geoid)?;
    let result = reader
        .query(
            scope,
            PlayerQuery::EarnedDossier {
                subject_kind: SubjectKind::County,
                subject_id,
                as_of_period: scope.as_of_period(),
            },
        )
        .map_err(|error| error.to_string())?;
    let PlayerBody::EarnedDossier(dossier) = &result.body else {
        return Err("the campaign answered a different dossier projection".into());
    };
    Ok(json!({
        "record": "county-dossier",
        "schema_version": 2,
        "source": "local-campaign",
        "geoid": geoid,
        "state": "ready",
        "committed_period": result.committed_period,
        "as_of_period": result.as_of_period,
        "knowledge_seq": dossier.journal_seq,
        "published_period": dossier.period,
        "payload_sha256": hex_of(&dossier.payload),
        "payload_utf8": std::str::from_utf8(&dossier.payload).ok(),
        "rows_visited": result.cost.rows_visited(),
    }))
}

/// Render the bounded history feed of one earned county.
fn scoped_changelog_row(
    reader: CampaignQueryReader<'_>,
    scope: PlayerScope,
    geoid: &str,
) -> Result<Value, String> {
    let subject_id = county_subject_id(geoid)?;
    let page = reader
        .history(scope, None, 0)
        .map_err(|error| error.to_string())?;
    let named = reader
        .query(
            scope,
            PlayerQuery::KnownRelationship {
                subject_kind: SubjectKind::County,
                subject_id,
            },
        )
        .map_err(|error| error.to_string())?;
    let PlayerBody::Relationship(relationship) = &named.body else {
        return Err("the campaign answered a different relationship projection".into());
    };
    Ok(json!({
        "record": "archive-changes-page",
        "schema_version": 1,
        "source": "local-campaign",
        "geoid": geoid,
        "committed_period": page.committed_period,
        "as_of_period": page.as_of_period,
        "relations": relationship.records.iter().map(|record| json!({
            "journal_seq": record.journal_seq,
            "kind": format!("{:?}", record.kind),
            "period": record.period,
            "resolved_period": record.resolved_period,
        })).collect::<Vec<_>>(),
        "truncated": relationship.truncated,
        "history_entries": page.entries.len(),
        "has_more": page.next.is_some(),
        "rows_visited": page.cost.rows_visited(),
    }))
}

/// Render the scoped subject census of one campaign.
fn scoped_map_row(reader: CampaignQueryReader<'_>, scope: PlayerScope) -> Result<Value, String> {
    let result = reader
        .query(scope, PlayerQuery::MapSummary)
        .map_err(|error| error.to_string())?;
    let PlayerBody::MapSummary(summary) = &result.body else {
        return Err("the campaign answered a different map projection".into());
    };
    Ok(json!({
        "record": "economy-status",
        "schema_version": 2,
        "source": "local-campaign",
        "committed_period": result.committed_period,
        "as_of_period": result.as_of_period,
        "knowledge_seq": result.knowledge_seq,
        "world_hash": hex_bytes(result.world_hash),
        "known_subjects": summary.known_subjects.iter().map(|count| json!({
            "subject_kind": format!("{:?}", count.kind),
            "count": count.count,
        })).collect::<Vec<_>>(),
        "rows_visited": result.cost.rows_visited(),
    }))
}

/// Render the committed identity of one campaign.
fn scoped_tick_row(reader: CampaignQueryReader<'_>, scope: PlayerScope) -> Result<Value, String> {
    let result = reader
        .query(scope, PlayerQuery::MapSummary)
        .map_err(|error| error.to_string())?;
    let PlayerBody::MapSummary(_) = &result.body else {
        return Err("the campaign answered a different map projection".into());
    };
    Ok(json!({
        "record": "tick-status",
        "source": "local-campaign",
        "durable_tick": result.committed_period,
        "campaign_id": reader.campaign_id().as_uuid().to_string(),
        "world_hash": hex_bytes(result.world_hash),
        "knowledge_seq": result.knowledge_seq,
    }))
}

/// Return one five-digit county GEOID as its canonical subject bytes.
fn county_subject_id(geoid: &str) -> Result<Vec<u8>, String> {
    let bytes = geoid.as_bytes();
    if bytes.len() != 5 || !bytes.iter().all(u8::is_ascii_digit) {
        return Err(format!("`{geoid}` is not a five-digit county GEOID"));
    }
    Ok(bytes.to_vec())
}

fn hex_of(bytes: &[u8]) -> String {
    let mut rendered = String::with_capacity(bytes.len() * 2);
    for byte in bytes {
        use std::fmt::Write as _;
        let _ = write!(rendered, "{byte:02x}");
    }
    rendered
}

fn tick_status_row(
    reader: &SemanticArchiveReader,
    campaign_id: CampaignId,
) -> Result<Value, String> {
    let status = reader
        .committed_tick_status(campaign_id)
        .map_err(|error| error.to_string())?;
    let processed_tick = reader
        .archive_verification_status(campaign_id)
        .map_err(|error| error.to_string())?
        .map(|status| status.processed_tick());
    Ok(match status {
        Some(status) => json!({
            "record": "tick-status",
            "campaign_id": status.campaign_id().as_uuid().to_string(),
            "durable_tick": status.resolve_tick(),
            "processed_tick": processed_tick,
            "envelope_layout_version": status.envelope_layout_version(),
            "tick_content_hash": hex_bytes(*status.tick_content_hash()),
            "envelope_digest": hex_bytes(*status.envelope_digest()),
        }),
        None => json!({
            "record": "tick-status",
            "campaign_id": campaign_id.as_uuid().to_string(),
            "durable_tick": Value::Null,
            "processed_tick": Value::Null,
            "envelope_layout_version": Value::Null,
            "tick_content_hash": Value::Null,
            "envelope_digest": Value::Null,
        }),
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use babylon_persistence::archive_revision::ArchiveChangePage;
    use babylon_persistence::{
        ArchiveAtomSubject, ArchiveAtomSubjectKind, ArchiveAtomValue, ArchiveCitation,
        ArchiveEvidenceClass, ArchiveSignal,
    };
    use uuid::Uuid;

    fn read(state: ArchiveDossierState) -> ArchiveDossierRead {
        let campaign = CampaignId::from_uuid(Uuid::nil());
        ArchiveDossierRead {
            scope: ArchiveReadScope::committed(campaign, 3, [0xab; 32])
                .expect("the fixture observation carries the committed value"),
            subject: county_subject("26163")
                .expect("the fixture call `county_subject` succeeds for the authored inputs"),
            durable_tick: 8,
            processed_tick: 8,
            state,
        }
    }
    fn page() -> ArchiveDossierPage {
        let campaign = CampaignId::from_uuid(Uuid::nil());
        let citation =
            ArchiveCitation::try_new("original-source".into(), "original/locator".into())
                .expect("the authored fixture satisfies the constructor invariants");
        ArchiveDossierPage {
            revision_id: [1; 32],
            effective_tick: 2,
            content_source: ArchiveReadScope::committed(campaign, 1, [0xaa; 32])
                .expect("the fixture observation carries the committed value"),
            title: "Retained title".into(),
            question: "Original question?".into(),
            signals: vec![ArchiveSignal::try_new(
                "observed-key".into(),
                "Original label".into(),
                "Original display value".into(),
                citation.clone(),
            )
            .expect("the authored fixture satisfies the constructor invariants")],
            markdown: "Original narrative bytes".into(),
            content_sha256: [2; 32],
            citations: vec![citation],
            atoms: vec![],
            links: vec![],
            changes: ArchiveChangePage {
                coverage_from_tick: 2,
                changes: vec![],
                next_cursor: None,
            },
        }
    }
    #[test]
    fn pending_retained_content_never_inherits_global_progress_verification() {
        let read = read(ArchiveDossierState::Pending {
            page: Some(page()),
            reason: ArchiveDossierPending::KnowledgeRefresh,
        });
        assert!(retained_page(&read).is_some());
        assert_eq!(verified_tick(&read), None);
        let json = dossier_json(&read);
        assert_eq!(json["state"], "pending");
        assert!(json["verified_tick"].is_null());
        assert_eq!(json["processed_tick"], 8);
        assert_eq!(json["scope"]["tick"], 3);
        assert_eq!(json["page"]["content_source"]["tick"], 1);
        assert_eq!(json["page"]["question"], "Original question?");
        assert_eq!(json["page"]["signals"][0]["label"], "Original label");
        assert_eq!(json["page"]["markdown"], "Original narrative bytes");
    }
    #[test]
    fn ready_uses_exact_selected_page_verification_and_absence_stays_typed() {
        let ready = read(ArchiveDossierState::Ready {
            page: page(),
            verified_through_tick: 3,
        });
        assert_eq!(verified_tick(&ready), Some(3));
        for reason in [
            ArchiveDossierUnavailable::FoundationHasNoPage,
            ArchiveDossierUnavailable::SubjectNotDisclosed,
            ArchiveDossierUnavailable::PageNotMaterialized,
        ] {
            let read = read(ArchiveDossierState::Unavailable(reason));
            assert!(retained_page(&read).is_none());
            assert_eq!(verified_tick(&read), None);
            let json = dossier_json(&read);
            assert_eq!(json["state"], "unavailable");
            assert!(json["page"].is_null());
            assert_eq!(json["availability"], unavailable_label(reason));
        }
    }
    #[test]
    fn exact_scope_requires_the_selected_hash_and_cannot_fabricate_foundation() {
        let campaign = CampaignId::from_uuid(Uuid::nil());
        assert!(observation_scope(campaign, 0, None)
            .expect("the fixture call `observation_scope` succeeds for the authored inputs")
            .tick_content_hash()
            .is_none());
        assert!(observation_scope(campaign, 0, Some(&"a".repeat(64))).is_err());
        for hash in [
            None,
            Some("bad"),
            Some("AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"),
        ] {
            assert!(observation_scope(campaign, 1, hash).is_err());
        }
        assert_eq!(
            observation_scope(campaign, 3, Some(&"ab".repeat(32)))
                .expect("the fixture call `observation_scope` succeeds for the authored inputs")
                .tick_content_hash(),
            Some([0xab; 32])
        );
    }
    #[test]
    fn removal_and_numeric_zero_have_different_json_evidence() {
        let atom = ArchiveAtom::try_new(
            CampaignId::from_uuid(Uuid::nil()),
            ArchiveAtomSubject::try_new(ArchiveAtomSubjectKind::County, "26163".into())
                .expect("the authored fixture satisfies the constructor invariants"),
            "jobs".into(),
            "jobs".into(),
            ArchiveEvidenceClass::Observed,
            &ArchiveAtomValue::U64(0),
            ArchiveCitation::try_new("source".into(), "locator".into())
                .expect("the authored fixture satisfies the constructor invariants"),
            2,
        )
        .expect("the authored fixture satisfies the constructor invariants");
        let mut change = ArchiveAtomChange {
            publication_tick: 3,
            signal_key: "jobs".into(),
            before: None,
            after: Some(atom.clone()),
        };
        assert_eq!(change_json(&change)["after"]["value"], 0);
        change.before = Some(atom);
        change.after = None;
        let json = change_json(&change);
        assert!(json["after"].is_null());
        assert_eq!(json["before"]["valid_tick"], 2);
        assert_eq!(json["publication_tick"], 3);
    }
}

#[cfg(test)]
mod scoped_campaign {
    use super::*;
    use babylon_kernel::content_digest;
    use babylon_persistence::sqlite_store::AdmittedContent;
    use babylon_persistence::sqlite_store::AdmittedContentEntry;
    use babylon_persistence::sqlite_store::AdmittedOpening;
    use babylon_persistence::sqlite_store::BuildIdentity;
    use babylon_persistence::sqlite_store::ChunkSection;
    use babylon_persistence::sqlite_store::ContentEntryKind;
    use babylon_persistence::sqlite_store::DossierCompletion;
    use babylon_persistence::sqlite_store::DossierRequest;
    use babylon_persistence::sqlite_store::JournalKind;
    use babylon_persistence::sqlite_store::PreparedJournalRecord;
    use babylon_persistence::sqlite_store::PreparedKnowledgeGrant;
    use babylon_persistence::sqlite_store::PreparedPeriod;
    use babylon_persistence::sqlite_store::PreparedSubject;
    use babylon_persistence::sqlite_store::SqliteCampaignStore;
    use babylon_persistence::sqlite_store::StateChunk;
    use std::fs;
    use std::path::Path;
    use std::path::PathBuf;
    use std::time::SystemTime;
    use std::time::UNIX_EPOCH;
    use uuid::Uuid;

    const PLAYER: [u8; 8] = 42_u64.to_be_bytes();

    struct TempRoot(PathBuf);

    impl TempRoot {
        fn new() -> Self {
            let nanos = SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .expect("the test clock is after the epoch")
                .as_nanos();
            let path = std::env::temp_dir().join(format!(
                "babylon-client-scoped-{}-{nanos}",
                std::process::id()
            ));
            fs::create_dir_all(&path).expect("the temporary campaign root is creatable");
            Self(path)
        }

        fn path(&self, name: &str) -> PathBuf {
            self.0.join(name)
        }
    }

    impl Drop for TempRoot {
        fn drop(&mut self) {
            let result = fs::remove_dir_all(&self.0);
            assert!(
                result.is_ok(),
                "the temporary campaign root must be removable"
            );
        }
    }

    fn county() -> PreparedSubject {
        PreparedSubject {
            kind: SubjectKind::County,
            id: b"26163".to_vec(),
        }
    }

    fn scoped_campaign(database: &Path) -> CampaignHandle {
        let mut handle = SqliteCampaignStore::create(
            database,
            AdmittedContent {
                campaign_id: CampaignId::from_uuid(Uuid::from_u128(0x5150)),
                build: BuildIdentity::from_hash([7; 32]),
                entries: vec![AdmittedContentEntry {
                    kind: ContentEntryKind::CapturedSource,
                    key: b"rules.bsl".to_vec(),
                    ordinal: 0,
                    bytes: b"captured source rules".to_vec(),
                }],
            },
            AdmittedOpening {
                world_hash: [0; 32],
                state_hash: content_digest::sha256_of(b"register"),
                chunks: vec![StateChunk {
                    section: ChunkSection::WorldRegisters,
                    ordinal: 0,
                    bytes: b"register".to_vec(),
                }],
            },
        )
        .expect("the scoped campaign is created once");
        let period = handle.current().period + 1;
        handle
            .commit(PreparedPeriod {
                period,
                expected_world_hash: handle.current().world_hash,
                world_hash: content_digest::sha256_of(b"world-1"),
                state_hash: content_digest::sha256_of(b"register"),
                chunks: vec![StateChunk {
                    section: ChunkSection::WorldRegisters,
                    ordinal: 0,
                    bytes: b"register".to_vec(),
                }],
                journal: vec![PreparedJournalRecord {
                    kind: JournalKind::PlayerReceipt,
                    subject: Some(county()),
                    record_key: None,
                    payload: b"county-receipt-1".to_vec(),
                    resolves_prior_subject: false,
                }],
                knowledge: vec![PreparedKnowledgeGrant {
                    player_id: PLAYER,
                    subject: county(),
                    grant_key: 1,
                    payload: b"wayne-wage-fact".to_vec(),
                }],
                detail: Vec::new(),
                tick_identity: None,
            })
            .expect("the scoped period commits");
        handle
    }

    fn publish_dossier(handle: &mut CampaignHandle) {
        let tails = handle.durable_tails().expect("the durable tails read");
        let receipt = handle
            .enqueue_archive_dossier(
                DossierRequest::new(1, PLAYER, county(), 1, tails.knowledge_hash())
                    .expect("the request is inside its published bounds"),
            )
            .expect("the earned dossier is queued");
        handle
            .complete_archive_dossier(
                DossierCompletion::new(
                    1,
                    PLAYER,
                    county(),
                    1,
                    tails.knowledge_hash(),
                    receipt.service_seq,
                    b"county-dossier-v1".to_vec(),
                )
                .expect("the completion is inside its published bounds"),
            )
            .expect("the earned dossier publishes");
    }

    #[test]
    fn scoped_headless_rows_render_only_earned_facts_from_bounded_rows() {
        let root = TempRoot::new();
        let database = root.path("campaign.sqlite3");
        let mut handle = scoped_campaign(&database);
        publish_dossier(&mut handle);

        let reader = CampaignQueryReader::new(&handle);
        let scope = reader
            .current_scope(PLAYER)
            .expect("the current scope binds to the durable tails");

        let dossier =
            scoped_dossier_row(reader, scope, "26163").expect("the county dossier renders");
        assert_eq!(dossier["record"], "county-dossier");
        assert_eq!(dossier["state"], "ready");
        assert_eq!(dossier["payload_utf8"], "county-dossier-v1");
        assert!(
            dossier["rows_visited"]
                .as_u64()
                .is_some_and(|rows| rows <= 4),
            "the dossier row decodes a bounded row set, saw {}",
            dossier["rows_visited"]
        );
        assert_eq!(dossier["committed_period"], 1);

        let map = scoped_map_row(reader, scope).expect("the scoped census renders");
        assert_eq!(map["known_subjects"][0]["subject_kind"], "County");
        assert_eq!(map["known_subjects"][0]["count"], 1);

        let changelog =
            scoped_changelog_row(reader, scope, "26163").expect("the earned county feed renders");
        assert_eq!(changelog["geoid"], "26163");
        assert!(
            changelog["relations"]
                .as_array()
                .is_some_and(|relations| !relations.is_empty()),
            "the granted subject names at least one journal record"
        );

        let tick = scoped_tick_row(reader, scope).expect("the committed identity renders");
        assert_eq!(tick["durable_tick"], 1);
        assert_eq!(
            tick["campaign_id"],
            CampaignId::from_uuid(Uuid::from_u128(0x5150))
                .as_uuid()
                .to_string()
        );
    }

    #[test]
    fn scoped_headless_rows_hide_a_dossier_before_its_journal_prefix() {
        let root = TempRoot::new();
        let database = root.path("campaign.sqlite3");
        let mut handle = scoped_campaign(&database);
        let tails_before = handle.durable_tails().expect("the durable tails read");
        publish_dossier(&mut handle);

        let reader = CampaignQueryReader::new(&handle);
        let earlier = PlayerScope::new(
            PLAYER,
            1,
            tails_before.knowledge_seq(),
            tails_before.journal_seq(),
        );
        let refused = scoped_dossier_row(reader, earlier, "26163");
        assert!(
            refused.is_err(),
            "a dossier published after the scope's journal prefix stays hidden"
        );

        let unknown = scoped_dossier_row(reader, earlier, "99999");
        assert!(unknown.is_err(), "an unearned county has no row");
        assert!(scoped_dossier_row(reader, earlier, "2616").is_err());
    }
}
