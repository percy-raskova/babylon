//! The projection, the digests and the report of a mismatch.

use babylon_kernel::content_digest;
use std::fmt::Write as _;
use std::path::PathBuf;

/// Where the reference rows of every measured set are kept.
pub(crate) const REFERENCE_DIR: &str = "/media/user/dev-ssd/babylon-bench/restoring-forces/out";

/// The file without its `flow_` columns.
pub(crate) fn project(text: &str) -> String {
    let lines: Vec<&str> = text.split('\n').collect();
    let Some(header) = lines.first() else {
        return String::new();
    };
    let keep: Vec<usize> = header
        .split('\t')
        .enumerate()
        .filter(|(_, name)| !name.starts_with("flow_"))
        .map(|(index, _)| index)
        .collect();
    let mut out = String::new();
    for line in lines.iter().filter(|line| !line.is_empty()) {
        let fields: Vec<&str> = line.split('\t').collect();
        let kept: Vec<&str> = keep
            .iter()
            .filter_map(|&index| fields.get(index).copied())
            .collect();
        out.push_str(&kept.join("\t"));
        out.push('\n');
    }
    out
}

/// Lowercase hex sha256 of `text`'s bytes.
pub(crate) fn digest_hex(text: &str) -> String {
    let mut hex = String::with_capacity(64);
    for byte in content_digest::sha256_of(text.as_bytes()) {
        let _ = write!(hex, "{byte:02x}");
    }
    hex
}

/// The first place two files of rows differ: its period, its column and both values.
fn first_difference(produced: &str, reference: &str) -> String {
    let mut ours = produced.lines();
    let mut theirs = reference.lines();
    let (Some(ours_header), Some(theirs_header)) = (ours.next(), theirs.next()) else {
        return "one of the files is empty".to_owned();
    };
    let names: Vec<&str> = ours_header.split('\t').collect();
    let their_names: Vec<&str> = theirs_header.split('\t').collect();
    if names != their_names {
        let missing: Vec<&&str> = their_names.iter().filter(|n| !names.contains(n)).collect();
        let extra: Vec<&&str> = names.iter().filter(|n| !their_names.contains(n)).collect();
        return format!("the columns differ: missing {missing:?}, extra {extra:?}");
    }
    for (ours_line, theirs_line) in ours.zip(theirs) {
        if ours_line == theirs_line {
            continue;
        }
        let ours_fields: Vec<&str> = ours_line.split('\t').collect();
        let theirs_fields: Vec<&str> = theirs_line.split('\t').collect();
        let period = ours_fields.first().copied().unwrap_or("?");
        for (index, name) in names.iter().enumerate() {
            let a = ours_fields.get(index).copied().unwrap_or("?");
            let b = theirs_fields.get(index).copied().unwrap_or("?");
            if a != b {
                return format!(
                    "first difference: period {period}, column {name}: produced {a}, reference {b}"
                );
            }
        }
    }
    "the lines agree for as long as both go on; the files differ in length".to_owned()
}

/// Panics naming every run whose digest differs from the fixture's. The differing run's projected rows are
/// written under the target directory; if the reference file exists on the drive, the message names the
/// first differing period and column, else where the reference rows are.
pub(crate) fn assert_set(set: &str, produced: &[(&str, String)], fixture: &str) {
    let expected: Vec<(&str, &str)> = fixture
        .lines()
        .filter_map(|line| line.split_once(' '))
        .collect();
    let mut report = String::new();
    if expected.len() != produced.len() {
        let _ = writeln!(
            report,
            "the fixture holds {} runs and the bench made {}",
            expected.len(),
            produced.len()
        );
    }
    for ((name, rows), (fixed_name, fixed)) in produced.iter().zip(&expected) {
        if name != fixed_name {
            let _ = writeln!(report, "run {name} sits where the fixture has {fixed_name}");
            continue;
        }
        if digest_hex(rows) == *fixed {
            continue;
        }
        let directory = PathBuf::from(env!("CARGO_TARGET_TMPDIR"))
            .join("adjustment-bench")
            .join(set);
        let written = std::fs::create_dir_all(&directory)
            .and_then(|()| std::fs::write(directory.join(format!("{name}.tsv")), rows));
        let reference = PathBuf::from(REFERENCE_DIR)
            .join(set)
            .join(format!("{name}.tsv"));
        let detail = match std::fs::read_to_string(&reference) {
            Ok(text) => first_difference(rows, &project(&text)),
            Err(_) => {
                format!("the reference rows are in {REFERENCE_DIR}/{set}/ (not readable here)")
            }
        };
        let _ = writeln!(
            report,
            "run {name} differs (rows written: {}): {detail}",
            written.is_ok()
        );
    }
    assert!(report.is_empty(), "set {set} does not reproduce:\n{report}");
}

#[cfg(test)]
mod tests {
    use super::{digest_hex, project};

    #[test]
    fn the_projection_drops_only_flow_columns() {
        assert_eq!(
            project("period\tflow_x\tcash_a\n1\t2\t3\n"),
            "period\tcash_a\n1\t3\n"
        );
        let plain = "period\tcash_a\n1\t3\n2\t4\n";
        assert_eq!(project(plain), plain);
    }

    #[test]
    fn a_digest_is_lowercase_hex_of_the_bytes() {
        assert_eq!(
            digest_hex(""),
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        );
    }
}
