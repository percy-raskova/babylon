//! Source-model framing for every current material-circuit state branch. Every
//! variable row is parsed and bounded before its raw or closed variant storage
//! encoding is chosen. The circuit's own published constants own the domain and
//! schema version, so a wire bump cannot leave this walker behind.
use super::{StorageError, MAX_BYTES};
use crate::state_storage::layout;

pub(super) const REGISTER_DOMAIN: &[u8] = b"babylon.material-world-register.v7\0";
/// A register with a county review section.
const COUNTY_REGISTER_DOMAIN: &[u8] = b"babylon.material-world-register.v9\0";
/// The domain of the county review frame.
const COUNTY_FRAME_DOMAIN: &[u8] = b"babylon.material-world-register.county-review.v1\0";
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
            for id in [30, 31, 33] {
                self.rows(id)?;
            }
            self.variable(34, offer)?;
            for id in 35..=37 {
                self.rows(id)?;
            }
        }
        Ok(())
    }
    fn accounting(&mut self, lifecycle: bool) -> Result<(), StorageError> {
        if !self.branch(23)? {
            if lifecycle {
                return Err(StorageError::Framing);
            }
            return Ok(());
        }
        for id in 24..=28 {
            self.rows(id)?;
        }
        self.recurring()?;
        for id in 39..=50 {
            self.rows(id)?;
        }
        let start = self.cursor.pos;
        let time = self.cursor.tag(if lifecycle { &[2] } else { &[0, 1] })?;
        self.record(51, start, None);
        if time > 0 {
            self.rows(53)?;
            self.rows(54)?;
        }
        if time == 2 {
            let start = self.cursor.pos;
            lifecycle_section(&mut self.cursor)?;
            self.record(74, start, None);
        }
        self.rows(71)?;
        Ok(())
    }
    fn state(&mut self, tick: usize) -> Result<(), StorageError> {
        let start = self.cursor.pos;
        self.cursor.expect(STATE_DOMAIN)?;
        // The domain is NUL-terminated and followed by the published version.
        self.cursor.expect(&[0])?;
        let version = self.cursor.number(2)?;
        let lifecycle = version
            == usize::from(
                babylon_material_circuit::MATERIAL_CIRCUIT_LIFECYCLE_STATE_SCHEMA_VERSION,
            );
        if !lifecycle && version != usize::from(STATE_VERSION) {
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
        self.accounting(lifecycle)?;
        self.cursor.done()
    }
}
/// The complete v24 lifecycle extension owns its declared byte length. A truncated row
/// cannot borrow the following state section's count or identity bytes.
fn lifecycle_section(outer: &mut Cursor<'_>) -> Result<(), StorageError> {
    let size = outer.number(4)?;
    let mut body = Cursor::new(outer.take(size)?);
    body.take(5 * 4)?; // Birth and four death rates
    if body.tag(&[0, 1])? == 1 {
        body.take(8)?;
    }
    let count = body.number(4)?;
    if count == 0 || count > babylon_material_circuit::MAX_MATERIAL_CIRCUIT_ROWS {
        return Err(StorageError::Count);
    }
    for _ in 0..count {
        // Principal, current and prior ages, prior households, five rate carries,
        // and the three original age-band populations.
        body.take(32 + 2 * 32 + 8 + 5 * 4 + 3 * 8)?;
        let cohorts = body.number(2)?;
        if cohorts > 65 * 13 {
            return Err(StorageError::Count);
        }
        body.take(cohorts * 16)?; // Each deadline has a u64 date and u64 living count.
    }
    body.done()
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
/// The frames after the City PD's: the company frame in version 8, and in version 9 the company
/// frame when its domain leads the next frame, then the county review frame.
fn trailing_frames(register: &mut Cursor<'_>, version: usize) -> Result<(), StorageError> {
    if version == 7 {
        return Ok(());
    }
    let size = register.number(8)?;
    let first = register.take(size)?;
    let company = first.starts_with(babylon_material_circuit::COMPANY_PORTFOLIO_DOMAIN);
    if version == 8 {
        return if company {
            Ok(())
        } else {
            Err(StorageError::Framing)
        };
    }
    let county = if company {
        let size = register.number(8)?;
        register.take(size)?
    } else {
        first
    };
    if county.starts_with(COUNTY_FRAME_DOMAIN) {
        Ok(())
    } else {
        Err(StorageError::Framing)
    }
}
pub(super) fn sections(bytes: &[u8]) -> Result<Vec<Section>, StorageError> {
    if bytes.len() > MAX_BYTES {
        return Err(StorageError::Bounds);
    }
    let mut register = Cursor::new(bytes);
    let domain = register.take(REGISTER_DOMAIN.len())?;
    let version = register.number(4)?;
    if !((domain == REGISTER_DOMAIN && version == 7)
        || (domain == b"babylon.material-world-register.v8\0" && version == 8)
        || (domain == COUNTY_REGISTER_DOMAIN && version == 9))
    {
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
    let organizer_size = register.number(8)?;
    let organizer_end = register
        .pos
        .checked_add(organizer_size)
        .ok_or(StorageError::Bounds)?;
    if organizer_end > register.end {
        return Err(StorageError::Framing);
    }
    let mut organizer = Cursor {
        bytes,
        pos: register.pos,
        end: organizer_end,
    };
    if organizer.tag(&[0, 1])? == 1 {
        // Config, compact state, organizer journal and independent public venue.
        for _ in 0..4 {
            let size = organizer.number(8)?;
            organizer.take(size)?;
        }
    }
    organizer.done()?;
    register.pos = organizer_end;
    parser.sections.push(Section {
        id: 69,
        start,
        end: register.pos,
        count: None,
    });
    let start = register.pos;
    let size = register.number(8)?;
    let frame = register.take(size)?;
    if !matches!(frame.first(), Some(0 | 1)) || (frame[0] == 0 && frame.len() != 1) {
        return Err(StorageError::Framing);
    }
    trailing_frames(&mut register, version)?;
    register.done()?;
    parser.sections.push(Section {
        id: 73,
        start,
        end: register.pos,
        count: None,
    });
    Ok(parser.sections)
}

#[cfg(test)]
mod lifecycle_tests {
    use super::{Cursor, StateParser, StorageError, STATE_DOMAIN};

    #[test]
    fn lifecycle_storage_requires_the_whole_dated_cohort_frame() {
        let mut body = vec![0; 5 * 4];
        body.push(1);
        body.extend_from_slice(&2_u64.to_be_bytes());
        body.extend_from_slice(&1_u32.to_be_bytes());
        body.extend_from_slice(&[0; 32 + 2 * 32 + 8 + 5 * 4 + 3 * 8]);
        let group_offset = body.len();
        body.extend_from_slice(&1_u16.to_be_bytes());
        body.extend_from_slice(&846_u64.to_be_bytes());
        body.extend_from_slice(&67_u64.to_be_bytes());
        let size = u32::try_from(body.len()).expect("one small household");
        let frame =
            |declared: u32, b: &[u8]| [declared.to_be_bytes().as_slice(), b, &[0xaa; 8]].concat();
        let valid = frame(size, &body);
        let mut cursor = Cursor::new(&valid);
        super::lifecycle_section(&mut cursor).expect("one full household, one dated cohort");
        assert_eq!(cursor.take(8).expect("next section"), &[0xaa; 8]);
        for bad in [frame(size - 1, &body), frame(size + 1, &body)] {
            assert!(super::lifecycle_section(&mut Cursor::new(&bad)).is_err());
        }
        body[group_offset..group_offset + 2].copy_from_slice(&846_u16.to_be_bytes());
        assert!(matches!(
            super::lifecycle_section(&mut Cursor::new(&frame(size, &body))),
            Err(StorageError::Count)
        ));
    }

    #[test]
    fn provisional_mixed_age_state_is_not_a_dated_cohort_save() {
        let state = [STATE_DOMAIN, &[0], &23_u16.to_be_bytes()].concat();
        let mut parser = StateParser {
            cursor: Cursor::new(&state),
            sections: Vec::new(),
        };
        assert!(matches!(parser.state(0), Err(StorageError::Version)));
    }
}

#[cfg(test)]
mod trailing_frame_tests {
    use super::{trailing_frames, Cursor, StorageError, COUNTY_FRAME_DOMAIN};

    fn framed(body: &[u8]) -> Vec<u8> {
        let mut bytes = u64::try_from(body.len())
            .expect("a short frame")
            .to_be_bytes()
            .to_vec();
        bytes.extend_from_slice(body);
        bytes
    }

    fn company() -> Vec<u8> {
        framed(
            &[
                babylon_material_circuit::COMPANY_PORTFOLIO_DOMAIN,
                b"decisions",
            ]
            .concat(),
        )
    }

    fn county() -> Vec<u8> {
        framed(&[COUNTY_FRAME_DOMAIN, b"config and state"].concat())
    }

    fn walk(version: usize, bytes: &[u8]) -> Result<(), StorageError> {
        let mut cursor = Cursor::new(bytes);
        trailing_frames(&mut cursor, version)?;
        cursor.done()
    }

    #[test]
    fn version_seven_has_no_trailing_frame_and_version_eight_has_the_company_frame() {
        assert!(walk(7, &[]).is_ok());
        assert!(walk(7, &company()).is_err());
        assert!(walk(8, &company()).is_ok());
        assert!(walk(8, &[]).is_err());
        assert!(walk(8, &county()).is_err());
    }

    #[test]
    fn version_nine_has_the_county_frame_after_an_optional_company_frame() {
        assert!(walk(9, &county()).is_ok());
        assert!(walk(9, &[company(), county()].concat()).is_ok());
        assert!(walk(9, &company()).is_err());
        assert!(walk(9, &[]).is_err());
        assert!(walk(9, &[county(), company()].concat()).is_err());
        assert!(walk(9, &[county(), county()].concat()).is_err());
        assert!(walk(9, &framed(b"not the county's domain")).is_err());
        assert!(walk(9, &[county(), vec![0]].concat()).is_err());
    }
}
