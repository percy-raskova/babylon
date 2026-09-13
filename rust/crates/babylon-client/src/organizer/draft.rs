//! Personal presentation drafts. No saved value is an accepted command.

use std::fs::{self, OpenOptions};
use std::io::{Read, Write};
use std::path::{Path, PathBuf};

use babylon_persistence::runtime_session::OrganizerChoice;
use serde_json::json;

use super::editor::NoteEditor;

pub(super) const MAX_EVIDENCE_REFERENCES: usize = 32;

#[derive(Clone, Debug, PartialEq, Eq)]
pub(super) struct OrganizerDraft {
    pub workplace_id: u64,
    pub choice: OrganizerChoice,
    pub notes: NoteEditor,
    pub references: Vec<[u8; 32]>,
    pub selected_reference: Option<[u8; 32]>,
}

impl OrganizerDraft {
    pub fn new(workplace_id: u64) -> Self {
        Self {
            workplace_id,
            choice: OrganizerChoice::Hold,
            notes: NoteEditor::default(),
            references: Vec::new(),
            selected_reference: None,
        }
    }
}

fn path(campaign: uuid::Uuid) -> Result<PathBuf, String> {
    let preference = crate::campaign_browser::preference_path()?;
    let base = preference
        .parent()
        .ok_or("Personal draft directory is unavailable.")?;
    Ok(base
        .join("organizer-drafts")
        .join(format!("{campaign}.json")))
}

pub(super) fn load(campaign: uuid::Uuid, workplace_id: u64) -> Result<OrganizerDraft, String> {
    read_at(&path(campaign)?, campaign, workplace_id)
}

fn read_at(path: &Path, campaign: uuid::Uuid, workplace_id: u64) -> Result<OrganizerDraft, String> {
    let file = match fs::File::open(path) {
        Ok(file) => file,
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => {
            return Ok(OrganizerDraft::new(workplace_id))
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
    let value: serde_json::Value = serde_json::from_slice(&bytes)
        .map_err(|_| "Personal draft is invalid; retained for recovery.")?;
    let object = value
        .as_object()
        .ok_or("Personal draft is invalid; retained for recovery.")?;
    if value["schema"] != 2 {
        return Err("Personal draft format is unsupported; the original file is retained and will not be overwritten.".into());
    }
    if object.len() != 7
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
        notes: NoteEditor::from_text(notes.to_owned()).map_err(str::to_owned)?,
        references,
        selected_reference,
    })
}

pub(super) fn save(campaign: uuid::Uuid, draft: &OrganizerDraft) -> Result<(), String> {
    write_at(&path(campaign)?, campaign, draft)
}

fn write_at(path: &Path, campaign: uuid::Uuid, draft: &OrganizerDraft) -> Result<(), String> {
    validate_references(&draft.references, draft.selected_reference)?;
    let parent = path
        .parent()
        .ok_or("Personal draft directory is unavailable.")?;
    fs::create_dir_all(parent).map_err(|_| "Cannot create the personal draft directory.")?;
    let temporary = parent.join(format!(".{}.tmp", uuid::Uuid::new_v4()));
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
    let bytes = serde_json::to_vec(&json!({"schema":2,"campaign":campaign.to_string(),"workplace":draft.workplace_id,"choice":draft.choice,"notes":draft.notes.text,"references":draft.references,"selected_reference":draft.selected_reference})).map_err(|_| "Cannot encode the personal draft.")?;
    let result = file
        .write_all(&bytes)
        .and_then(|()| file.sync_all())
        .and_then(|()| fs::rename(&temporary, path));
    if result.is_err() {
        let _ = fs::remove_file(&temporary);
    }
    result.map_err(|_| "Cannot save the personal draft; notes remain in this window.".into())
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

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn draft_references_roundtrip_without_executable_authority() {
        let campaign = uuid::Uuid::new_v4();
        let directory = std::env::temp_dir().join(format!("babylon-draft-references-{campaign}"));
        fs::create_dir_all(&directory).unwrap();
        let path = directory.join("draft.json");
        let first = [1u8; 32];
        let second = [2u8; 32];
        let value = json!({"schema":2,"campaign":campaign.to_string(),"workplace":42,
            "choice":"reinforce","notes":"Keep the café report.",
            "references":[first,second],"selected_reference":second});
        fs::write(&path, serde_json::to_vec(&value).unwrap()).unwrap();
        let draft = read_at(&path, campaign, 42).expect("current draft references must load");
        assert_eq!(draft.notes.text, "Keep the café report.");
        write_at(&path, campaign, &draft).unwrap();
        assert_eq!(read_at(&path, campaign, 42).unwrap(), draft);
        let saved: serde_json::Value = serde_json::from_slice(&fs::read(&path).unwrap()).unwrap();
        assert_eq!(saved, value);
        for key in ["nonce", "authority_id", "commitment", "command"] {
            assert!(saved.get(key).is_none());
        }
        assert!(read_at(&path, uuid::Uuid::new_v4(), 42).is_err());
        assert!(read_at(&path, campaign, 43).is_err());
        fs::remove_file(path).unwrap();
        fs::remove_dir(directory).unwrap();
    }

    #[test]
    fn draft_references_refuse_old_or_malformed_files_without_overwriting_them() {
        let campaign = uuid::Uuid::new_v4();
        let directory = std::env::temp_dir().join(format!("babylon-draft-refusals-{campaign}"));
        fs::create_dir_all(&directory).unwrap();
        let path = directory.join("draft.json");
        let first = [1u8; 32];
        let second = [2u8; 32];
        let current = json!({"schema":2,"campaign":campaign.to_string(),"workplace":42,
            "choice":"hold","notes":"Preserve these bytes.",
            "references":[first],"selected_reference":first});
        let mut malformed = Vec::new();
        let mut old = current.clone();
        old["schema"] = json!(1);
        old.as_object_mut().unwrap().remove("references");
        old.as_object_mut().unwrap().remove("selected_reference");
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
            .unwrap()
            .remove("selected_reference");
        unknown_selection["unknown_selection"] = serde_json::Value::Null;
        malformed.push(unknown_selection);
        let mut excessive = current.clone();
        excessive["references"] = json!((0..33).map(|value| [value; 32]).collect::<Vec<_>>());
        malformed.push(excessive);
        for value in malformed {
            let bytes = serde_json::to_vec(&value).unwrap();
            fs::write(&path, &bytes).unwrap();
            assert!(read_at(&path, campaign, 42).is_err());
            assert_eq!(fs::read(&path).unwrap(), bytes);
        }
        fs::remove_file(path).unwrap();
        fs::remove_dir(directory).unwrap();
    }

    #[test]
    fn saved_draft_is_campaign_bound_and_carries_no_command_authority() {
        let campaign = uuid::Uuid::new_v4();
        let directory = std::env::temp_dir().join(format!("babylon-organizer-draft-{campaign}"));
        let path = directory.join("draft.json");
        let mut draft = OrganizerDraft::new(42);
        draft.notes.insert("Keep the workplace objection.");
        draft.choice = OrganizerChoice::Reinforce;
        write_at(&path, campaign, &draft).unwrap();
        assert_eq!(read_at(&path, campaign, 42).unwrap(), draft);
        assert!(read_at(&path, uuid::Uuid::new_v4(), 42).is_err());
        assert!(read_at(&path, campaign, 43).is_err());
        let bytes = fs::read(&path).unwrap();
        let value: serde_json::Value = serde_json::from_slice(&bytes).unwrap();
        assert!(value.get("nonce").is_none());
        assert!(value.get("authority_id").is_none());
        assert!(value.get("commitment").is_none());
        assert_eq!(fs::read_dir(&directory).unwrap().count(), 1);
        fs::remove_file(path).unwrap();
        fs::remove_dir(directory).unwrap();
    }
}
