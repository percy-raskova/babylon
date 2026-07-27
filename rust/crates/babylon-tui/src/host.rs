//! The Python↔Rust seam: every read crosses as a JSON string (design §4).

/// Host surface the Python side implements (M1: lobby + read-only Archive).
///
/// Every method returns a JSON string; absence is JSON `null` or `[]`, never
/// a fabricated value (Constitution III.11 — honest absence). The M1 methods
/// carry default implementations returning the honest-absence encoding so
/// milestone-earlier fakes keep compiling; the production Python host
/// overrides every method.
pub trait Host {
    /// The lobby campaign catalog as a JSON array string.
    fn lobby_catalog_json(&self) -> String;

    /// The rendered Archive page for `subject` as JSON: a Markdown string,
    /// or `null` when the vault has no page for it (plan Task 17).
    fn read_page_json(&self, _subject: &str) -> String {
        "null".to_string()
    }

    /// Every known page subject, sorted, as a JSON array of strings.
    fn known_subjects_json(&self) -> String {
        "[]".to_string()
    }

    /// Subjects whose pages link to `subject`, as a JSON array of strings.
    fn backlinks_json(&self, _subject: &str) -> String {
        "[]".to_string()
    }

    /// The frozen view-model for `subject` as a JSON object, or `null`
    /// (feeds the peek overlay's depth rendering).
    fn subject_view_json(&self, _subject: &str) -> String {
        "null".to_string()
    }

    /// Watchlist rows as a JSON array (M1 reads; pin writes land in M2).
    fn watchlist_json(&self) -> String {
        "[]".to_string()
    }
}
