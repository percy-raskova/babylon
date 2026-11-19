//! A versioned presentation preference, independent of campaigns and drafts.

use std::fs::{self, File, OpenOptions};
use std::io::{ErrorKind, Read, Write};
use std::path::{Path, PathBuf};

use serde::{Deserialize, Serialize};
use uuid::Uuid;

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub(super) enum Outcome {
    Completed,
    Skipped,
}

#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct Preference {
    version: u8,
    seen: bool,
    outcome: Outcome,
}

pub(super) fn path() -> Result<PathBuf, String> {
    let campaign = crate::campaign_browser::preference_path()?;
    Ok(campaign
        .parent()
        .ok_or("Personal presentation directory is unavailable.")?
        .join("interface-tour.json"))
}

pub(super) fn read(path: &Path) -> Result<Option<Outcome>, String> {
    let file = match File::open(path) {
        Ok(file) => file,
        Err(error) if error.kind() == ErrorKind::NotFound => return Ok(None),
        Err(_) => return Err("Cannot read the interface tour preference.".into()),
    };
    let mut bytes = Vec::new();
    file.take(4_097)
        .read_to_end(&mut bytes)
        .map_err(|_| "Cannot read the interface tour preference.")?;
    if bytes.len() > 4_096 {
        return Err("Interface tour preference exceeds its supported size.".into());
    }
    let preference: Preference = serde_json::from_slice(&bytes)
        .map_err(|_| "Interface tour preference is invalid or unsupported.")?;
    if preference.version != 1 || !preference.seen {
        return Err("Interface tour preference is invalid or unsupported.".into());
    }
    Ok(Some(preference.outcome))
}

pub(super) fn write(path: &Path, outcome: Outcome) -> Result<(), String> {
    let parent = path
        .parent()
        .ok_or("Personal presentation directory is unavailable.")?;
    fs::create_dir_all(parent).map_err(|_| "Cannot create the presentation directory.")?;
    let temporary = parent.join(format!(".interface-tour-{}.tmp", Uuid::new_v4()));
    let mut options = OpenOptions::new();
    options.write(true).create_new(true);
    #[cfg(unix)]
    {
        use std::os::unix::fs::OpenOptionsExt as _;
        options.mode(0o600);
    }
    let mut file = options
        .open(&temporary)
        .map_err(|_| "Cannot save the interface tour preference.")?;
    let bytes = serde_json::to_vec(&Preference {
        version: 1,
        seen: true,
        outcome,
    })
    .map_err(|_| "Cannot encode the interface tour preference.")?;
    let result = file
        .write_all(&bytes)
        .and_then(|()| file.sync_all())
        .and_then(|()| fs::rename(&temporary, path));
    if result.is_err() {
        let _ = fs::remove_file(&temporary);
    }
    result.map_err(|_| "Cannot save the interface tour preference; play can continue.".into())
}

#[cfg(test)]
mod tests {
    use super::Outcome;
    use std::fs;
    use uuid::Uuid;

    #[test]
    fn completed_and_skipped_preferences_round_trip_without_campaign_data() {
        let directory = std::env::temp_dir().join(format!("tour-pref-{}", Uuid::new_v4()));
        let path = directory.join("interface-tour.json");
        assert_eq!(super::read(&path).expect("missing preference"), None);
        for outcome in [Outcome::Skipped, Outcome::Completed] {
            super::write(&path, outcome).expect("save preference");
            assert_eq!(super::read(&path).expect("read preference"), Some(outcome));
        }
        fs::write(&path, br#"{"version":2,"seen":true,"outcome":"completed"}"#)
            .expect("unsupported preference");
        assert!(super::read(&path).is_err());
        fs::remove_dir_all(directory).expect("remove disposable preference");
    }
}
