//! Strict single-line source CSV shared by pinned county and world captures.

#[derive(Clone, Copy, Debug)]
pub(crate) struct InvalidRecord;

pub(crate) fn record(line: &str, columns: usize) -> Result<Vec<String>, InvalidRecord> {
    let mut input = line.chars().peekable();
    let mut fields = Vec::with_capacity(columns);
    loop {
        if fields.len() == columns {
            return Err(InvalidRecord);
        }
        let mut field = String::new();
        if input.peek() == Some(&'"') {
            input.next();
            loop {
                match input.next() {
                    Some('"') if input.peek() == Some(&'"') => {
                        input.next();
                        field.push('"');
                    }
                    Some('"') => break,
                    Some(value) if !value.is_control() => field.push(value),
                    _ => return Err(InvalidRecord),
                }
            }
        } else {
            while input.peek().is_some_and(|value| *value != ',') {
                let value = input.next().ok_or(InvalidRecord)?;
                if value == '"' || value.is_control() {
                    return Err(InvalidRecord);
                }
                field.push(value);
            }
        }
        fields.push(field);
        match input.next() {
            Some(',') => {}
            None if fields.len() == columns => return Ok(fields),
            _ => return Err(InvalidRecord),
        }
    }
}
