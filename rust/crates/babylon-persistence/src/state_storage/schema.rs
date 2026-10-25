//! Source-model framing for every current material-circuit state branch. Every
//! variable row is parsed and bounded before its raw or closed variant storage
//! encoding is chosen. The circuit's own published constants own the domain and
//! schema version, so a wire bump cannot leave this walker behind.
use super::{StorageError, MAX_BYTES};
use crate::state_storage::layout;

pub(super) const REGISTER_DOMAIN: &[u8] = b"babylon.material-world-register.v5\0";
const STATE_DOMAIN: &[u8] = babylon_material_circuit::MATERIAL_CIRCUIT_STATE_DOMAIN_BYTES;
const STATE_VERSION: u16 = babylon_material_circuit::MATERIAL_CIRCUIT_STATE_SCHEMA_VERSION;
#[derive(Clone, Debug)]
pub(super) struct Section {
    pub id: u16,
    pub start: usize,
    pub end: usize,
    pub count: Option<usize>,
}
impl Section {
    pub fn raw<'a>(&self, bytes: &'a [u8]) -> &'a [u8] {
        &bytes[self.start..self.end]
    }
}
pub(super) struct Cursor<'a> {
    pub bytes: &'a [u8],
    pub pos: usize,
    pub end: usize,
}
impl<'a> Cursor<'a> {
    pub fn new(bytes: &'a [u8]) -> Self {
        Self {
            bytes,
            pos: 0,
            end: bytes.len(),
        }
    }
    pub fn take(&mut self, size: usize) -> Result<&'a [u8], StorageError> {
        let end = self.pos.checked_add(size).ok_or(StorageError::Bounds)?;
        if end > self.end {
            return Err(StorageError::Framing);
        }
        let value = &self.bytes[self.pos..end];
        self.pos = end;
        Ok(value)
    }
    pub fn number(&mut self, size: usize) -> Result<usize, StorageError> {
        if size > 8 {
            return Err(StorageError::Bounds);
        }
        let mut value = 0_u64;
        for byte in self.take(size)? {
            value = (value << 8) | u64::from(*byte);
        }
        usize::try_from(value).map_err(|_| StorageError::Bounds)
    }
    pub fn tag(&mut self, allowed: &[u8]) -> Result<u8, StorageError> {
        let tag = self.take(1)?[0];
        if !allowed.contains(&tag) {
            return Err(StorageError::Framing);
        }
        Ok(tag)
    }
    pub fn expect(&mut self, value: &[u8]) -> Result<(), StorageError> {
        if self.take(value.len())? != value {
            return Err(StorageError::Version);
        }
        Ok(())
    }
    pub fn done(&self) -> Result<(), StorageError> {
        if self.pos == self.end {
            Ok(())
        } else {
            Err(StorageError::Trailing)
        }
    }
}
struct StateParser<'a> {
    cursor: Cursor<'a>,
    sections: Vec<Section>,
}
impl StateParser<'_> {
    fn record(&mut self, id: u16, start: usize, count: Option<usize>) {
        self.sections.push(Section {
            id,
            start,
            end: self.cursor.pos,
            count,
        });
    }
    fn rows(&mut self, id: u16) -> Result<(), StorageError> {
        let shape = layout::layout(id).ok_or(StorageError::Layout)?;
        let start = self.cursor.pos;
        let count = self.cursor.number(4)?;
        if count > shape.maximum {
            return Err(StorageError::Count);
        }
        self.cursor
            .take(count.checked_mul(shape.width).ok_or(StorageError::Bounds)?)?;
        self.record(id, start, Some(count));
        Ok(())
    }
    fn variable(
        &mut self,
        id: u16,
        row: fn(&mut Cursor<'_>) -> Result<(), StorageError>,
    ) -> Result<(), StorageError> {
        let start = self.cursor.pos;
        let count = self.cursor.number(4)?;
        if count > 65536 {
            return Err(StorageError::Count);
        }
        for _ in 0..count {
            row(&mut self.cursor)?;
        }
        self.record(id, start, Some(count));
        Ok(())
    }
    fn branch(&mut self, id: u16) -> Result<bool, StorageError> {
        let start = self.cursor.pos;
        let tag = self.cursor.tag(&[0, 1])?;
        self.record(id, start, None);
        Ok(tag == 1)
    }
    fn recurring(&mut self) -> Result<(), StorageError> {
        let start = self.cursor.pos;
        let present = self.cursor.tag(&[0, 1])?;
        if present == 1 {
            self.cursor.take(16)?;
        }
        self.record(29, start, None);
        if present == 1 {
            for id in 30..=33 {
                self.rows(id)?;
            }
            self.variable(34, offer)?;
            for id in 35..=38 {
                self.rows(id)?;
            }
        }
        Ok(())
    }
    fn accounting(&mut self) -> Result<(), StorageError> {
        if !self.branch(23)? {
            return Ok(());
        }
        for id in 24..=28 {
            self.rows(id)?;
        }
        self.recurring()?;
        for id in 39..=50 {
            self.rows(id)?;
        }
        if self.branch(51)? {
            self.variable(52, time_policy)?;
            self.rows(53)?;
            self.rows(54)?;
        }
        self.variable(70, aid_mandate)?;
        self.rows(71)?;
        self.rows(72)?;
        Ok(())
    }
    fn state(&mut self, tick: usize) -> Result<(), StorageError> {
        let start = self.cursor.pos;
        self.cursor.expect(STATE_DOMAIN)?;
        // The domain is NUL-terminated and followed by the published version.
        self.cursor.expect(&[0])?;
        if self.cursor.number(2)? != usize::from(STATE_VERSION) {
            return Err(StorageError::Version);
        }
        // The admitting catalog digest authenticates the definitions this frame
        // was encoded against; the definitions themselves live in the catalog.
        self.cursor.take(32)?;
        if self.cursor.number(8)? != tick.checked_add(1).ok_or(StorageError::Bounds)? {
            return Err(StorageError::Framing);
        }
        self.record(1, start, None);
        self.rows(66)?;
        self.rows(67)?;
        for id in 9..=11 {
            self.rows(id)?;
        }
        self.rows(13)?;
        for id in 14..=17 {
            self.rows(id)?;
        }
        for id in 20..=21 {
            self.rows(id)?;
        }
        let start = self.cursor.pos;
        if self.cursor.tag(&[0, 1])? == 1 {
            self.cursor.take(16)?;
        }
        self.record(22, start, None);
        self.rows(60)?;
        self.rows(61)?;
        self.rows(65)?;
        self.accounting()?;
        self.cursor.done()
    }
}
fn aid_mandate(c: &mut Cursor<'_>) -> Result<(), StorageError> {
    // Mandate ID, independent source hash and three actor IDs.
    c.take(88)?;
    c.tag(&[1, 2, 3, 4])?;
    // Payer ID, five material identities, two quantities and exact currency.
    c.take(224)?;
    if c.tag(&[1, 2])? == 2 {
        c.take(96)?;
    }
    Ok(())
}
fn offer(c: &mut Cursor<'_>) -> Result<(), StorageError> {
    c.take(112)?;
    let tag = c.tag(&[1, 2, 3])?;
    c.take(match tag {
        1 => 0,
        2 => 56,
        3 => 48,
        _ => return Err(StorageError::Framing),
    })?;
    Ok(())
}
fn time_policy(c: &mut Cursor<'_>) -> Result<(), StorageError> {
    c.take(80)?;
    c.tag(&[1, 2])?;
    c.take(8)?;
    c.tag(&[1, 2])?;
    c.take(8)?;
    let count = c.number(4)?;
    if count > 65536 {
        return Err(StorageError::Count);
    }
    c.take(count.checked_mul(72).ok_or(StorageError::Bounds)?)?;
    Ok(())
}
pub(super) fn sections(bytes: &[u8]) -> Result<Vec<Section>, StorageError> {
    if bytes.len() > MAX_BYTES {
        return Err(StorageError::Bounds);
    }
    let mut register = Cursor::new(bytes);
    register.expect(REGISTER_DOMAIN)?;
    if register.number(4)? != 5 {
        return Err(StorageError::Version);
    }
    let tick = register.number(8)?;
    let state_length = register.number(8)?;
    let start = register.pos;
    register.take(state_length)?;
    let end = register.pos;
    let mut parser = StateParser {
        cursor: Cursor {
            bytes,
            pos: start,
            end,
        },
        sections: vec![Section {
            id: 0,
            start: 0,
            end: start,
            count: None,
        }],
    };
    parser.state(tick)?;
    let start = register.pos;
    if register.tag(&[0, 1])? == 1 {
        // Config, compact state and the retained evidence window.
        for _ in 0..3 {
            let size = register.number(8)?;
            register.take(size)?;
        }
    }
    register.done()?;
    parser.sections.push(Section {
        id: 69,
        start,
        end: register.pos,
        count: None,
    });
    Ok(parser.sections)
}
