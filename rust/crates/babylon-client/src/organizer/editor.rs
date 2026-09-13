//! UTF-8-safe, bounded presentation notes. Editing never produces an intent.

pub(super) const MAX_NOTE_BYTES: usize = 4096;

#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub(super) struct NoteEditor {
    pub text: String,
    pub cursor: usize,
    pub selected_all: bool,
}

impl NoteEditor {
    pub fn from_text(text: String) -> Result<Self, &'static str> {
        if text.len() > MAX_NOTE_BYTES
            || text
                .chars()
                .any(|value| value.is_control() && value != '\n')
        {
            return Err("Saved notes exceed the supported text limit.");
        }
        Ok(Self {
            cursor: text.len(),
            text,
            selected_all: false,
        })
    }

    fn replace_selection(&mut self) {
        if self.selected_all {
            self.text.clear();
            self.cursor = 0;
            self.selected_all = false;
        }
    }

    pub fn insert(&mut self, value: &str) {
        self.replace_selection();
        for character in value
            .chars()
            .filter(|value| !value.is_control() || *value == '\n')
        {
            if self.text.len() + character.len_utf8() > MAX_NOTE_BYTES {
                break;
            }
            self.text.insert(self.cursor, character);
            self.cursor += character.len_utf8();
        }
    }

    pub fn left(&mut self) {
        self.selected_all = false;
        self.cursor = self.text[..self.cursor]
            .char_indices()
            .next_back()
            .map_or(0, |(index, _)| index);
    }

    pub fn right(&mut self) {
        self.selected_all = false;
        self.cursor += self.text[self.cursor..]
            .chars()
            .next()
            .map_or(0, char::len_utf8);
    }

    pub fn home(&mut self) {
        self.cursor = 0;
        self.selected_all = false;
    }
    pub fn end(&mut self) {
        self.cursor = self.text.len();
        self.selected_all = false;
    }

    pub fn backspace(&mut self) {
        if self.selected_all {
            self.replace_selection();
            return;
        }
        let end = self.cursor;
        self.left();
        self.text.drain(self.cursor..end);
    }

    pub fn delete(&mut self) {
        if self.selected_all {
            self.replace_selection();
            return;
        }
        let begin = self.cursor;
        self.right();
        self.text.drain(begin..self.cursor);
        self.cursor = begin;
    }

    pub fn display(&self, focused: bool) -> String {
        if !focused {
            return self.text.clone();
        }
        if self.selected_all {
            return format!("[{}]", self.text);
        }
        let mut rendered = self.text.clone();
        rendered.insert(self.cursor, '|');
        rendered
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn editing_keeps_unicode_boundaries_and_replaces_selection() {
        let mut editor = NoteEditor::default();
        editor.insert("Workers’ café 🦋");
        editor.left();
        editor.backspace();
        assert_eq!(editor.text, "Workers’ café🦋");
        editor.delete();
        assert_eq!(editor.text, "Workers’ café");
        editor.selected_all = true;
        editor.insert("Ask about work.\nPreserve the objection.");
        assert_eq!(editor.text, "Ask about work.\nPreserve the objection.");
        assert_eq!(editor.cursor, editor.text.len());
    }

    #[test]
    fn notes_bound_bytes_without_splitting_a_character_or_accepting_controls() {
        let mut editor = NoteEditor::default();
        editor.insert(&"a".repeat(MAX_NOTE_BYTES - 1));
        editor.insert("🦋");
        assert_eq!(editor.text.len(), MAX_NOTE_BYTES - 1);
        editor.insert("\u{0}x");
        assert_eq!(editor.text.len(), MAX_NOTE_BYTES);
        assert!(!editor.text.contains('\u{0}'));
        editor.home();
        editor.backspace();
        assert_eq!(editor.cursor, 0);
        editor.end();
        editor.right();
        assert_eq!(editor.cursor, MAX_NOTE_BYTES);
    }
}
