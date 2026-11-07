//! Personal presentation drafts. No saved value is an accepted command.

use std::fs::{self, OpenOptions};
use std::io::{Read, Write};
use std::path::{Path, PathBuf};

use babylon_persistence::runtime_session::{
    OrganizerAllocation, OrganizerChoice, OrganizerSnapshot,
};
use serde_json::json;

use super::editor::NoteEditor;
use fs::File;
use serde_json::Value;
use std::io::ErrorKind;
use uuid::Uuid;

pub(super) const MAX_EVIDENCE_REFERENCES: usize = 32;

#[derive(Clone, Debug, PartialEq, Eq)]
pub(super) struct OrganizerDraft {
    pub workplace_id: u64,
    pub choice: OrganizerChoice,
    pub collection_allocation: OrganizerAllocation,
    pub aid_allocation: OrganizerAllocation,
    pub notes: NoteEditor,
    pub references: Vec<[u8; 32]>,
    pub selected_reference: Option<[u8; 32]>,
}

impl OrganizerDraft {
    pub(super) fn captured(snapshot: &OrganizerSnapshot) -> Self {
        let collection = snapshot
            .collection
            .as_ref()
            .map_or(OrganizerAllocation::None, |r| {
                OrganizerAllocation::Collection {
                    target_cash_micros: r.initial_cash_micros,
                }
            });
        let aid =
            snapshot
                .aid
                .first()
                .map_or(OrganizerAllocation::None, |r| OrganizerAllocation::Aid {
                    food_quantity: r.initial_food_quantity,
                    cash_micros: r.initial_cash_micros,
                });
        Self::new(snapshot.view.workplace_id, collection, aid)
    }

    pub fn new(
        workplace_id: u64,
        collection_allocation: OrganizerAllocation,
        aid_allocation: OrganizerAllocation,
    ) -> Self {
        Self {
            workplace_id,
            choice: OrganizerChoice::Hold,
            collection_allocation,
            aid_allocation,
            notes: NoteEditor::default(),
            references: Vec::new(),
            selected_reference: None,
        }
    }
}

fn path(campaign: Uuid) -> Result<PathBuf, String> {
    let preference = crate::campaign_browser::preference_path()?;
    let base = preference
        .parent()
        .ok_or("Personal draft directory is unavailable.")?;
    Ok(base
        .join("organizer-drafts")
        .join(format!("{campaign}.json")))
}

pub(super) fn load(
    campaign: Uuid,
    workplace_id: u64,
    initial_collection: OrganizerAllocation,
    initial_aid: OrganizerAllocation,
) -> Result<OrganizerDraft, String> {
    read_at(
        &path(campaign)?,
        campaign,
        workplace_id,
        initial_collection,
        initial_aid,
    )
}

fn read_at(
    path: &Path,
    campaign: Uuid,
    workplace_id: u64,
    initial_collection: OrganizerAllocation,
    initial_aid: OrganizerAllocation,
) -> Result<OrganizerDraft, String> {
    let file = match File::open(path) {
        Ok(file) => file,
        Err(error) if error.kind() == ErrorKind::NotFound => {
            return Ok(OrganizerDraft::new(
                workplace_id,
                initial_collection,
                initial_aid,
            ))
        }
        Err(_) => return Err("Cannot read this campaign's personal draft.".into()),
    };
    let mut bytes = Vec::new();
    file.take(16_385)
        .read_to_end(&mut bytes)
        .map_err(|_| "Cannot read this campaign's personal draft.")?;
    if bytes.len() > 16_384 {
        return Err("Personal draft exceeds the supported size.".into());
    }
    let value: Value = serde_json::from_slice(&bytes)
        .map_err(|_| "Personal draft is invalid; retained for recovery.")?;
    let object = value
        .as_object()
        .ok_or("Personal draft is invalid; retained for recovery.")?;
    if value["schema"] != 4 {
        return Err("Personal draft format is unsupported; the original file is retained and will not be overwritten.".into());
    }
    if object.len() != 9
        || !object.contains_key("selected_reference")
        || value["campaign"] != campaign.to_string()
        || value["workplace"] != workplace_id
    {
        return Err(
            "Personal draft does not match this campaign and workplace; retained for recovery."
                .into(),
        );
    }
    let choice = serde_json::from_value(value["choice"].clone())
        .map_err(|_| "Personal draft has an unsupported approach.")?;
    let collection_allocation: OrganizerAllocation =
        serde_json::from_value(value["collection_allocation"].clone())
            .map_err(|_| "Personal draft contribution target is invalid; retained for recovery.")?;
    validate_collection(collection_allocation)?;
    let aid_allocation = serde_json::from_value(value["aid_allocation"].clone())
        .map_err(|_| "Personal draft aid allocation is invalid; retained for recovery.")?;
    validate_aid(aid_allocation)?;
    let notes = value["notes"]
        .as_str()
        .ok_or("Personal draft notes are invalid.")?;
    let references: Vec<[u8; 32]> = serde_json::from_value(value["references"].clone())
        .map_err(|_| "Personal draft evidence references are invalid.")?;
    let selected_reference = serde_json::from_value(value["selected_reference"].clone())
        .map_err(|_| "Personal draft evidence selection is invalid.")?;
    validate_references(&references, selected_reference)?;
    Ok(OrganizerDraft {
        workplace_id,
        choice,
        collection_allocation,
        aid_allocation,
        notes: NoteEditor::from_text(notes.to_owned()).map_err(str::to_owned)?,
        references,
        selected_reference,
    })
}

pub(super) fn save(campaign: Uuid, draft: &OrganizerDraft) -> Result<(), String> {
    write_at(&path(campaign)?, campaign, draft)
}

fn write_at(path: &Path, campaign: Uuid, draft: &OrganizerDraft) -> Result<(), String> {
    validate_references(&draft.references, draft.selected_reference)?;
    validate_collection(draft.collection_allocation)?;
    validate_aid(draft.aid_allocation)?;
    let parent = path
        .parent()
        .ok_or("Personal draft directory is unavailable.")?;
    fs::create_dir_all(parent).map_err(|_| "Cannot create the personal draft directory.")?;
    let temporary = parent.join(format!(".{}.tmp", Uuid::new_v4()));
    let mut options = OpenOptions::new();
    options.write(true).create_new(true);
    #[cfg(unix)]
    {
        use std::os::unix::fs::OpenOptionsExt;
        options.mode(0o600);
    }
    let mut file = options
        .open(&temporary)
        .map_err(|_| "Cannot save the personal draft.")?;
    let bytes = serde_json::to_vec(&json!({"schema":4,"aid_allocation":draft.aid_allocation,"collection_allocation":draft.collection_allocation,"campaign":campaign.to_string(),"workplace":draft.workplace_id,"choice":draft.choice,"notes":draft.notes.text,"references":draft.references,"selected_reference":draft.selected_reference})).map_err(|_| "Cannot encode the personal draft.")?;
    let result = file
        .write_all(&bytes)
        .and_then(|()| file.sync_all())
        .and_then(|()| fs::rename(&temporary, path));
    if result.is_err() {
        let _ = fs::remove_file(&temporary);
    }
    result.map_err(|_| "Cannot save the personal draft; notes remain in this window.".into())
}

// Personal storage preserves exact captured micros. Whole-dollar entry and Review are
// validated against the selected current mandate in the amount editor.
fn validate_collection(allocation: OrganizerAllocation) -> Result<(), String> {
    match allocation {
        OrganizerAllocation::None => Ok(()),
        OrganizerAllocation::Collection { target_cash_micros } if target_cash_micros > 0 => Ok(()),
        _ => Err(
            "Personal draft contribution target must be positive; retained for recovery.".into(),
        ),
    }
}

fn validate_references(references: &[[u8; 32]], selected: Option<[u8; 32]>) -> Result<(), String> {
    if references.len() > MAX_EVIDENCE_REFERENCES
        || references
            .iter()
            .enumerate()
            .any(|(index, id)| references[..index].contains(id))
        || match selected {
            Some(id) => !references.contains(&id),
            None => !references.is_empty(),
        }
    {
        return Err(
            "Personal draft evidence references are invalid; retained for recovery.".into(),
        );
    }
    Ok(())
}

fn validate_aid(allocation: OrganizerAllocation) -> Result<(), String> {
    match allocation {
        OrganizerAllocation::None => Ok(()),
        OrganizerAllocation::Aid {
            food_quantity,
            cash_micros,
        } if cash_micros >= 0 && (food_quantity > 0 || cash_micros > 0) => Ok(()),
        _ => Err("Personal draft aid amounts are invalid; retained for recovery.".into()),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::Value;
    use uuid::Uuid;

    #[test]
    fn repaired_exact_captured_fraction_saves_unrelated_personal_notes_and_reference() {
        use babylon_persistence::runtime_session::OrganizerSnapshot;
        let capture: Value = serde_json::from_str(include_str!(
            "../../../babylon-persistence/tests/fixtures/cash_only_no_food_v18.json"
        ))
        .expect("cash-only producer capture");
        let snapshot: OrganizerSnapshot =
            serde_json::from_value(capture["snapshot"].clone()).expect("ordinary visible snapshot");
        let campaign = Uuid::from_bytes(snapshot.body_scope.campaign_id);
        let path = std::env::temp_dir()
            .join(format!("babylon-fractional-personal-{}", Uuid::new_v4()))
            .join("draft.json");
        let mut draft = OrganizerDraft::captured(&snapshot);
        let original = draft.aid_allocation;
        assert_eq!(
            original,
            OrganizerAllocation::Aid {
                food_quantity: 0,
                cash_micros: 3
            }
        );
        draft.notes =
            NoteEditor::from_text("Keep the actual amount.".into()).expect("bounded personal text");
        // Personal storage preserves an opaque retained reference even if the current view no longer carries it.
        let id = Some([19; 32]);
        draft.references.push([19; 32]);
        draft.selected_reference = id;
        write_at(&path, campaign, &draft)
            .expect("notes can save while the captured amount is untouched");
        let opened = read_at(
            &path,
            campaign,
            snapshot.view.workplace_id,
            draft.collection_allocation,
            original,
        )
        .expect("reopen the saved personal record");
        assert_eq!(
            (
                opened.aid_allocation,
                opened.notes.text,
                opened.selected_reference
            ),
            (original, draft.notes.text, id)
        );
        fs::remove_file(&path).expect("remove owned test record");
        fs::remove_dir(path.parent().expect("isolated parent directory"))
            .expect("remove owned empty directory");
    }

    #[test]
    fn draft_references_roundtrip_without_executable_authority() {
        let campaign = Uuid::new_v4();
        let directory = std::env::temp_dir().join(format!("babylon-draft-references-{campaign}"));
        fs::create_dir_all(&directory).expect("the fixture directory is creatable");
        let path = directory.join("draft.json");
        let first = [1u8; 32];
        let second = [2u8; 32];
        let value = json!({"schema":4,"aid_allocation":{"aid":{"food_quantity":0,"cash_micros":"123000000"}},"collection_allocation":"none","campaign":campaign.to_string(),"workplace":42,
            "choice":"reinforce","notes":"Keep the café report.",
            "references":[first,second],"selected_reference":second});
        fs::write(
            &path,
            serde_json::to_vec(&value).expect("the value serializes to canonical JSON bytes"),
        )
        .expect("the fixture sink accepts the authored bytes");
        let draft = read_at(
            &path,
            campaign,
            42,
            OrganizerAllocation::None,
            OrganizerAllocation::None,
        )
        .expect("current draft references must load");
        assert_eq!(draft.notes.text, "Keep the café report.");
        write_at(&path, campaign, &draft).expect("the fixture file accepts the authored bytes");
        assert_eq!(
            read_at(
                &path,
                campaign,
                42,
                OrganizerAllocation::None,
                OrganizerAllocation::None
            )
            .expect("the fixture file holds the authored range"),
            draft
        );
        let saved: Value = serde_json::from_slice(
            &fs::read(&path).expect("the fixture reader returns its authored facts"),
        )
        .expect("the authored bytes match the declared schema");
        assert_eq!(saved, value);
        for key in ["nonce", "authority_id", "commitment", "command"] {
            assert!(saved.get(key).is_none());
        }
        assert!(read_at(
            &path,
            Uuid::new_v4(),
            42,
            OrganizerAllocation::None,
            OrganizerAllocation::None
        )
        .is_err());
        assert!(read_at(
            &path,
            campaign,
            43,
            OrganizerAllocation::None,
            OrganizerAllocation::None
        )
        .is_err());
        fs::remove_file(path).expect("the fixture file exists before removal");
        fs::remove_dir(directory).expect("the fixture directory exists before removal");
    }

    #[test]
    fn draft_references_refuse_old_or_malformed_files_without_overwriting_them() {
        let campaign = Uuid::new_v4();
        let directory = std::env::temp_dir().join(format!("babylon-draft-refusals-{campaign}"));
        fs::create_dir_all(&directory).expect("the fixture directory is creatable");
        let path = directory.join("draft.json");
        let first = [1u8; 32];
        let second = [2u8; 32];
        let current = json!({"schema":4,"aid_allocation":"none","collection_allocation":"none","campaign":campaign.to_string(),"workplace":42,
            "choice":"hold","notes":"Preserve these bytes.",
            "references":[first],"selected_reference":first});
        let mut malformed = Vec::new();
        let mut old = current.clone();
        old["schema"] = json!(1);
        old.as_object_mut()
            .expect("the JSON fixture field is an object")
            .remove("references");
        old.as_object_mut()
            .expect("the JSON fixture field is an object")
            .remove("selected_reference");
        malformed.push(old);
        let mut duplicate = current.clone();
        duplicate["references"] = json!([first, first]);
        malformed.push(duplicate);
        let mut foreign_selection = current.clone();
        foreign_selection["selected_reference"] = json!(second);
        malformed.push(foreign_selection);
        let mut unknown_selection = current.clone();
        unknown_selection
            .as_object_mut()
            .expect("the JSON fixture field is an object")
            .remove("selected_reference");
        unknown_selection["unknown_selection"] = Value::Null;
        malformed.push(unknown_selection);
        let mut excessive = current.clone();
        excessive["references"] = json!((0..33).map(|value| [value; 32]).collect::<Vec<_>>());
        malformed.push(excessive);
        for value in malformed {
            let bytes =
                serde_json::to_vec(&value).expect("the value serializes to canonical JSON bytes");
            fs::write(&path, &bytes).expect("the fixture sink accepts the authored bytes");
            assert!(read_at(
                &path,
                campaign,
                42,
                OrganizerAllocation::None,
                OrganizerAllocation::None
            )
            .is_err());
            assert_eq!(
                fs::read(&path).expect("the fixture reader returns its authored facts"),
                bytes
            );
        }
        fs::remove_file(path).expect("the fixture file exists before removal");
        fs::remove_dir(directory).expect("the fixture directory exists before removal");
    }

    #[test]
    fn saved_draft_is_campaign_bound_and_carries_no_command_authority() {
        let campaign = Uuid::new_v4();
        let directory = std::env::temp_dir().join(format!("babylon-organizer-draft-{campaign}"));
        let path = directory.join("draft.json");
        let mut draft =
            OrganizerDraft::new(42, OrganizerAllocation::None, OrganizerAllocation::None);
        draft.notes.insert("Keep the workplace objection.");
        draft.choice = OrganizerChoice::Reinforce;
        draft.collection_allocation = OrganizerAllocation::Collection {
            target_cash_micros: 123_000_000,
        };
        write_at(&path, campaign, &draft).expect("the fixture file accepts the authored bytes");
        assert_eq!(
            read_at(
                &path,
                campaign,
                42,
                OrganizerAllocation::None,
                OrganizerAllocation::None
            )
            .expect("the fixture file holds the authored range"),
            draft
        );
        assert!(read_at(
            &path,
            Uuid::new_v4(),
            42,
            OrganizerAllocation::None,
            OrganizerAllocation::None
        )
        .is_err());
        assert!(read_at(
            &path,
            campaign,
            43,
            OrganizerAllocation::None,
            OrganizerAllocation::None
        )
        .is_err());
        let bytes = fs::read(&path).expect("the fixture reader returns its authored facts");
        let value: Value =
            serde_json::from_slice(&bytes).expect("the authored bytes match the declared schema");
        assert!(value.get("nonce").is_none());
        assert!(value.get("authority_id").is_none());
        assert!(value.get("commitment").is_none());
        assert_eq!(
            value["collection_allocation"]["collection"]["target_cash_micros"],
            "123000000"
        );
        assert_eq!(
            fs::read_dir(&directory)
                .expect("the fixture directory is readable")
                .count(),
            1
        );
        fs::remove_file(path).expect("the fixture file exists before removal");
        fs::remove_dir(directory).expect("the fixture directory exists before removal");
    }
}
