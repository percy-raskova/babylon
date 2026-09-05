//! PER-23 Slice 3 headless dossier execution (ADR249 R9-R11): the
//! [`HeadlessInvocation`] resource, one Startup system that runs exactly
//! one fog-safe reader command, and the JSONL serializers that keep
//! stdout machine-readable while every log line stays on stderr.
//!
//! The client serializes persistence types into [`serde_json::Value`]
//! manually — persistence types intentionally carry no `Serialize`
//! derives (Slice 2 decision 4), so the JSONL shape is a client-owned
//! contract, one field per line, decided here and nowhere else.

use std::io::Write;
use std::num::NonZero;

use babylon_persistence::{
    ArchiveAtomSubjectKindV1, ArchiveAtomSubjectV1, ArchiveAtomV1, ArchiveSubjectKindV1,
    CampaignId, SemanticArchiveReaderV1,
};
use bevy::app::AppExit;
use bevy::prelude::{MessageWriter, Res, Resource};
use serde_json::{json, Value};

use crate::cli::CliCommand;

/// How honestly current the dossier card's Archive knowledge is, against
/// the durable committed tick.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum ArchiveFreshness {
    /// No tick committed yet: nothing is durable, the card is all fog.
    NoCommittedTick,
    /// Ticks committed but the page is absent or verified behind the
    /// durable tail: the card answers an older week.
    ArchivePending,
    /// Page content or the contiguous processed watermark reaches the durable tail.
    ArchiveCurrent,
}

impl ArchiveFreshness {
    /// Stable JSONL spelling.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::NoCommittedTick => "no-committed-tick",
            Self::ArchivePending => "archive-pending",
            Self::ArchiveCurrent => "archive-current",
        }
    }
}

/// One row of a county's supersession feed: two consecutive visible atoms
/// of one signal key whose atom identity changed (ADR249 R9). The initial
/// appearance of a signal carries `from_* = None`.
#[derive(Clone, Debug, PartialEq)]
pub struct ChangelogRow {
    /// The stable signal key both atoms answer to.
    pub signal_key: String,
    /// The earlier atom's valid tick, or `None` on first appearance.
    pub from_tick: Option<u64>,
    /// The later atom's valid tick.
    pub to_tick: u64,
    /// The earlier atom's identity, or `None` on first appearance.
    pub from_atom_id: Option<[u8; 32]>,
    /// The later atom's identity.
    pub to_atom_id: [u8; 32],
    /// The earlier atom's JSON value, or `None` on first appearance.
    pub from_value: Option<Value>,
    /// The later atom's JSON value.
    pub to_value: Value,
}

/// One resolved place name on the dossier card: a link atom's target geoid
/// and the title the acknowledged Archive resolves it to, or `None` when
/// the place page stays below the fog.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct PlaceName {
    /// Seven-digit place GEOID.
    pub geoid: String,
    /// The acknowledged place title, or `None` when no known page matches.
    pub name: Option<String>,
}

/// The parsed headless invocation: exactly one command against one
/// campaign, inserted as a resource before `Startup`.
#[derive(Resource, Clone, Debug)]
pub struct HeadlessInvocation {
    command: CliCommand,
    campaign_id: CampaignId,
}

impl HeadlessInvocation {
    /// Construct one invocation from the parsed CLI request.
    #[must_use]
    pub const fn new(command: CliCommand, campaign_id: CampaignId) -> Self {
        Self {
            command,
            campaign_id,
        }
    }
}

/// Build the reader pair and run exactly one command, writing JSONL rows
/// to stdout. Returns the process exit code: 0 on success, 2 on a loud
/// refusal (already rendered to stderr).
///
/// # Errors
/// Refuses a missing or malformed `BABYLON_READER_DSN`, a reader census
/// failure, or any database read failure, each with the reader's own
/// display text.
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

fn execute(invocation: &HeadlessInvocation) -> Result<(), String> {
    let reader = SemanticArchiveReaderV1::from_env().map_err(|error| error.to_string())?;
    let mut out = std::io::stdout().lock();
    match &invocation.command {
        CliCommand::TickStatus => {
            let row = tick_status_row(&reader, invocation.campaign_id)?;
            write_jsonl(&mut out, &row)?;
        }
        CliCommand::DossierShow { geoid } => {
            let row = county_dossier_card(&reader, invocation.campaign_id, geoid)?;
            write_jsonl(&mut out, &row)?;
        }
        CliCommand::DossierSearch { query } => {
            let processed_tick = reader
                .archive_verification_status(invocation.campaign_id)
                .map_err(|error| error.to_string())?
                .map(|status| status.processed_tick());
            for hit in reader
                .search_known(invocation.campaign_id, query, 50)
                .map_err(|error| error.to_string())?
            {
                write_jsonl(
                    &mut out,
                    &json!({
                        "record": "search-hit",
                        "subject_kind": hit.page_ref().kind().as_str(),
                        "geoid": hit.page_ref().id(),
                        "title": hit.title(),
                        "content_tick": hit.verified_tick(),
                        "processed_tick": processed_tick,
                        "verified_tick": effective_verification_tick(Some(hit.verified_tick()), processed_tick),
                        "atom_count": hit.atoms().len(),
                    }),
                )?;
            }
        }
        CliCommand::Changelog { geoid } => {
            let history = subject_history(&reader, invocation.campaign_id, geoid)?;
            for row in changelog_rows(&history) {
                write_jsonl(
                    &mut out,
                    &json!({
                        "record": "changelog-row",
                        "geoid": geoid,
                        "signal_key": row.signal_key,
                        "from_tick": row.from_tick,
                        "to_tick": row.to_tick,
                        "from_value": row.from_value,
                        "to_value": row.to_value,
                        "from_atom_id": row.from_atom_id.map(hex_bytes),
                        "to_atom_id": hex_bytes(row.to_atom_id),
                    }),
                )?;
            }
        }
    }
    out.flush().map_err(|error| error.to_string())?;
    Ok(())
}

/// Bevy Startup system: run the one parsed command, then leave the app
/// through [`AppExit`] so the headless process terminates after the first
/// update.
pub fn run_headless_command(invocation: Res<HeadlessInvocation>, mut exit: MessageWriter<AppExit>) {
    let code = run_headless(&invocation);
    exit.write(match NonZero::<u8>::new(code) {
        Some(code) => AppExit::Error(code),
        None => AppExit::Success,
    });
}

fn tick_status_row(
    reader: &SemanticArchiveReaderV1,
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

/// Assemble one county dossier card: the durable committed tick, the
/// acknowledged page's verified tick and content hash (via one
/// title-scoped search pass that also resolves the place names behind the
/// card's link atoms), the freshness state, and the structured atoms.
fn county_dossier_card(
    reader: &SemanticArchiveReaderV1,
    campaign_id: CampaignId,
    geoid: &str,
) -> Result<Value, String> {
    let durable_tick = reader
        .committed_tick_status(campaign_id)
        .map_err(|error| error.to_string())?
        .map(|status| status.resolve_tick());
    let processed_tick = reader
        .archive_verification_status(campaign_id)
        .map_err(|error| error.to_string())?
        .map(|status| status.processed_tick());
    let atoms = reader
        .county_card_atoms(campaign_id, geoid)
        .map_err(|error| error.to_string())?;
    let title = atoms
        .iter()
        .find(|atom| atom.signal_key() == "subject")
        .and_then(|atom| match atom.value() {
            babylon_persistence::ArchiveAtomValueV1::Text(text) => Some(text.clone()),
            _ => None,
        })
        .unwrap_or_default();

    // One title-scoped search pass resolves both the county hit (verified
    // tick and exact content hash) and the place titles behind the link
    // atoms. A place the Archive does not acknowledge stays `name: null`.
    let hits = reader
        .search_known(campaign_id, &title, 50)
        .map_err(|error| error.to_string())?;
    let county_hit = hits.iter().find(|hit| {
        hit.page_ref().kind() == ArchiveSubjectKindV1::County && hit.page_ref().id() == geoid
    });
    let content_tick = county_hit.map(babylon_persistence::ArchiveSearchHitV1::verified_tick);
    let verified_tick = effective_verification_tick(content_tick, processed_tick);
    let content_sha256 = county_hit.map(|hit| hex_bytes(hit.content_sha256()));
    let place_title = |place_geoid: &str| {
        hits.iter()
            .find(|hit| {
                hit.page_ref().kind() == ArchiveSubjectKindV1::Place
                    && hit.page_ref().id() == place_geoid
            })
            .map(|hit| hit.title().to_owned())
    };
    let places = atoms
        .iter()
        .filter_map(place_link_geoid)
        .map(|place_geoid| PlaceName {
            name: place_title(&place_geoid),
            geoid: place_geoid,
        })
        .collect::<Vec<_>>();

    let freshness = match (durable_tick, verified_tick) {
        (None, _) => ArchiveFreshness::NoCommittedTick,
        (Some(_), None) => ArchiveFreshness::ArchivePending,
        (Some(durable), Some(verified)) if verified < durable => ArchiveFreshness::ArchivePending,
        (Some(_), Some(_)) => ArchiveFreshness::ArchiveCurrent,
    };

    Ok(json!({
        "record": "county-dossier",
        "geoid": geoid,
        "title": title,
        "durable_tick": durable_tick,
        "content_tick": content_tick,
        "processed_tick": processed_tick,
        "verified_tick": verified_tick,
        "freshness": freshness.as_str(),
        "content_sha256": content_sha256,
        "atoms": atoms.iter().map(atom_json).collect::<Vec<_>>(),
        "places": places
            .iter()
            .map(|place| json!({ "geoid": place.geoid, "name": place.name }))
            .collect::<Vec<_>>(),
    }))
}

/// Freshness can advance after a quiet receipt without rewriting page content.
/// An absent page stays unknown even when the campaign has been processed.
#[must_use]
pub const fn effective_verification_tick(
    content_tick: Option<u64>,
    processed_tick: Option<u64>,
) -> Option<u64> {
    match (content_tick, processed_tick) {
        (Some(content), Some(processed)) if processed > content => Some(processed),
        (content, _) => content,
    }
}

fn subject_history(
    reader: &SemanticArchiveReaderV1,
    campaign_id: CampaignId,
    geoid: &str,
) -> Result<Vec<ArchiveAtomV1>, String> {
    let subject = ArchiveAtomSubjectV1::try_new(ArchiveAtomSubjectKindV1::County, geoid.to_owned())
        .map_err(|error| error.to_string())?;
    reader
        .subject_atom_history(campaign_id, &subject)
        .map_err(|error| error.to_string())
}

/// Extract the place GEOID from one link atom's `place/<geoid>` text value.
pub(crate) fn place_link_geoid(atom: &ArchiveAtomV1) -> Option<String> {
    match atom.value() {
        babylon_persistence::ArchiveAtomValueV1::Text(text)
            if text.starts_with("place/") && text.len() == 13 =>
        {
            let geoid = &text["place/".len()..];
            if geoid.bytes().all(|byte| byte.is_ascii_digit()) {
                return Some(geoid.to_owned());
            }
            None
        }
        _ => None,
    }
}

/// Fold a subject's signal-keyed, tick-ordered atom history into the
/// supersession feed: the initial appearance of each signal key, then one
/// row for every consecutive pair whose atom identity changed (ADR249 R9).
/// Equal-value supersessions still emit a row — an identity change is a
/// change, even when the carried value repeats.
#[must_use]
pub fn changelog_rows(history: &[ArchiveAtomV1]) -> Vec<ChangelogRow> {
    let mut rows = Vec::new();
    let mut previous: Option<&ArchiveAtomV1> = None;
    for atom in history {
        match previous {
            Some(prior) if prior.signal_key() == atom.signal_key() => {
                if prior.atom_id() != atom.atom_id() {
                    rows.push(ChangelogRow {
                        signal_key: atom.signal_key().to_owned(),
                        from_tick: Some(prior.valid_tick()),
                        to_tick: atom.valid_tick(),
                        from_atom_id: Some(prior.atom_id()),
                        to_atom_id: atom.atom_id(),
                        from_value: Some(atom_value_json(prior.value())),
                        to_value: atom_value_json(atom.value()),
                    });
                }
            }
            _ => rows.push(ChangelogRow {
                signal_key: atom.signal_key().to_owned(),
                from_tick: None,
                to_tick: atom.valid_tick(),
                from_atom_id: None,
                to_atom_id: atom.atom_id(),
                from_value: None,
                to_value: atom_value_json(atom.value()),
            }),
        }
        previous = Some(atom);
    }
    rows
}

fn atom_json(atom: &ArchiveAtomV1) -> Value {
    json!({
        "signal_key": atom.signal_key(),
        "grant_key": atom.grant_key(),
        "evidence_class": atom.evidence_class().as_str(),
        "value": atom_value_json(atom.value()),
        "valid_tick": atom.valid_tick(),
        "atom_id": hex_bytes(atom.atom_id()),
    })
}

fn atom_value_json(value: &babylon_persistence::ArchiveAtomValueV1) -> Value {
    match value {
        babylon_persistence::ArchiveAtomValueV1::Text(text) => Value::String(text.clone()),
        babylon_persistence::ArchiveAtomValueV1::F64(number) => {
            serde_json::Number::from_f64(*number).map_or(Value::Null, Value::Number)
        }
        babylon_persistence::ArchiveAtomValueV1::U64(number) => Value::from(*number),
        babylon_persistence::ArchiveAtomValueV1::Bool(flag) => Value::from(*flag),
    }
}

fn hex_bytes(bytes: [u8; 32]) -> String {
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

#[cfg(test)]
mod tests {
    use super::*;
    use babylon_persistence::{
        ArchiveAtomSubjectV1, ArchiveAtomValueV1, ArchiveCitationV1, ArchiveEvidenceClassV1,
    };
    use uuid::Uuid;

    fn atom(signal_key: &str, value: &str, valid_tick: u64) -> ArchiveAtomV1 {
        ArchiveAtomV1::try_new(
            CampaignId::from_uuid(Uuid::nil()),
            ArchiveAtomSubjectV1::try_new(ArchiveAtomSubjectKindV1::County, "26163".to_owned())
                .expect("subject admits"),
            signal_key.to_owned(),
            "employment".to_owned(),
            ArchiveEvidenceClassV1::Observed,
            &ArchiveAtomValueV1::Text(value.to_owned()),
            ArchiveCitationV1::try_new("src".to_owned(), "loc".to_owned())
                .expect("citation admits"),
            valid_tick,
        )
        .expect("atom admits")
    }

    #[test]
    fn quiet_processing_advances_verification_without_creating_page_content() {
        assert_eq!(effective_verification_tick(Some(1), Some(3)), Some(3));
        assert_eq!(effective_verification_tick(Some(3), Some(1)), Some(3));
        assert_eq!(effective_verification_tick(Some(1), None), Some(1));
        assert_eq!(effective_verification_tick(None, Some(3)), None);
    }

    #[test]
    fn changelog_rows_emit_appearances_and_identity_changes_only() {
        let first = atom("employment", "728576 jobs", 1);
        let same = atom("employment", "728576 jobs", 1);
        let changed = atom("employment", "731000 jobs", 2);
        let untouched_a = atom("median-wage", "24.50", 1);
        let untouched_b = atom("median-wage", "24.50", 2);
        // Identical identity at the same tick emits nothing; the changed
        // pair emits exactly one row; a brand-new signal emits its
        // appearance with from_* null.
        let rows = changelog_rows(&[
            first.clone(),
            same,
            changed.clone(),
            untouched_a,
            untouched_b,
        ]);
        assert_eq!(
            rows.len(),
            4,
            "appearance + one identity change + one appearance + the equal-value \
             tick-2 supersession, got {rows:?}"
        );
        assert_eq!(rows[0].signal_key, "employment");
        assert_eq!(rows[0].from_tick, None);
        assert_eq!(rows[0].to_tick, 1);
        assert_eq!(rows[1].signal_key, "employment");
        assert_eq!(rows[1].from_tick, Some(1));
        assert_eq!(rows[1].to_tick, 2);
        assert_eq!(
            rows[1].from_value,
            Some(Value::String("728576 jobs".to_owned()))
        );
        assert_eq!(rows[1].to_value, Value::String("731000 jobs".to_owned()));
        assert_ne!(rows[1].from_atom_id, None);
        assert_eq!(rows[2].signal_key, "median-wage");
        assert_eq!(rows[2].from_tick, None);
        // The tick-2 median-wage atom mints a fresh identity even though
        // the carried value repeats: an identity change is a change.
        assert_eq!(rows[3].signal_key, "median-wage");
        assert_eq!(rows[3].from_tick, Some(1));
        assert_eq!(rows[3].to_tick, 2);
        assert_eq!(rows[3].from_value, Some(rows[3].to_value.clone()));
        let _ = first;
        let _ = changed;
    }

    #[test]
    fn equal_value_supersession_still_emits_a_row() {
        let first = atom("employment", "731000 jobs", 1);
        // Force a different identity at the same value by changing the
        // citation, which enters the canonical atom id.
        let second = ArchiveAtomV1::try_new(
            CampaignId::from_uuid(Uuid::nil()),
            ArchiveAtomSubjectV1::try_new(ArchiveAtomSubjectKindV1::County, "26163".to_owned())
                .expect("subject admits"),
            "employment".to_owned(),
            "employment".to_owned(),
            ArchiveEvidenceClassV1::Observed,
            &ArchiveAtomValueV1::Text("731000 jobs".to_owned()),
            ArchiveCitationV1::try_new("src".to_owned(), "other-loc".to_owned())
                .expect("citation admits"),
            2,
        )
        .expect("atom admits");
        assert_ne!(first.atom_id(), second.atom_id());
        let rows = changelog_rows(&[first, second]);
        assert_eq!(
            rows.len(),
            2,
            "appearance + the equal-value identity change"
        );
        assert_eq!(rows[1].from_value, Some(rows[1].to_value.clone()));
        assert_ne!(rows[1].from_atom_id, None);
    }

    #[test]
    fn freshness_spellings_are_stable() {
        assert_eq!(
            ArchiveFreshness::NoCommittedTick.as_str(),
            "no-committed-tick"
        );
        assert_eq!(ArchiveFreshness::ArchivePending.as_str(), "archive-pending");
        assert_eq!(ArchiveFreshness::ArchiveCurrent.as_str(), "archive-current");
    }

    #[test]
    fn place_link_geoid_accepts_only_place_text_values() {
        let place = atom("link", "place/2622000", 1);
        assert_eq!(place_link_geoid(&place), Some("2622000".to_owned()));
        let jobs = atom("employment", "728576 jobs", 1);
        assert_eq!(place_link_geoid(&jobs), None);
        let short = atom("link", "place/26220", 1);
        assert_eq!(place_link_geoid(&short), None);
    }

    #[test]
    fn hex_bytes_renders_lowercase_digest() {
        assert_eq!(hex_bytes([0xab; 32]), "ab".repeat(32));
        let bytes = [
            0x00, 0x0f, 0xff, 0x10, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00,
        ];
        assert_eq!(
            hex_bytes(bytes),
            format!(
                "{}000000000000000000000000000000000000000000000000000000",
                "000fff1001"
            )
        );
    }
}
