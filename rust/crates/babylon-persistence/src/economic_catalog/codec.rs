//! Current independent source envelope. Derived opening rows are never encoded.
use super::{
    CatalogGeography, EconomicCatalogError, EconomicCatalogInput, SourceArtifact,
    SourceArtifactKind,
};
use babylon_kernel::{
    clock::{CampaignDuration, DAYS_PER_TICK},
    content_digest::sha256_of,
};

type Result<T> = std::result::Result<T, EconomicCatalogError>;
pub(super) const DOMAIN: &[u8] = b"babylon.economic-catalog.v1\0";
pub(super) const MAX_CATALOG_BYTES: usize = 64 * 1024 * 1024;
const MAX_SOURCE_BYTES: usize = 32 * 1024 * 1024;
const MAX_SOURCE_ROWS: usize = 32;
const MAX_TEXT_BYTES: usize = 128;
fn text(out: &mut Vec<u8>, text: &str) -> Result<()> {
    if text.is_empty() || text.len() > MAX_TEXT_BYTES || text.contains('\0') {
        return Err(EconomicCatalogError::Identity);
    }
    out.extend_from_slice(
        &u16::try_from(text.len())
            .map_err(|_| EconomicCatalogError::Bound)?
            .to_be_bytes(),
    );
    out.extend_from_slice(text.as_bytes());
    Ok(())
}
pub(super) fn encode(input: &EconomicCatalogInput, compiler: &str) -> Result<Vec<u8>> {
    if input.sources.is_empty() || input.sources.len() > MAX_SOURCE_ROWS {
        return Err(EconomicCatalogError::Bound);
    }
    let source_size = input.sources.iter().try_fold(0_usize, |n, row| {
        if row.bytes().is_empty() || row.bytes().len() > MAX_SOURCE_BYTES {
            return Err(EconomicCatalogError::Bound);
        }
        n.checked_add(37)
            .and_then(|n| n.checked_add(row.bytes().len()))
            .ok_or(EconomicCatalogError::Bound)
    })?;
    let size = source_size
        .checked_add(
            DOMAIN.len()
                + 2
                + 8
                + 6
                + compiler.len()
                + input.scenario_id.len()
                + input.preset_id.len()
                + 9
                + 1
                + 2,
        )
        .ok_or(EconomicCatalogError::Bound)?;
    if size > MAX_CATALOG_BYTES {
        return Err(EconomicCatalogError::Bound);
    }
    let mut out = Vec::new();
    out.try_reserve_exact(size)
        .map_err(|_| EconomicCatalogError::Bound)?;
    out.extend_from_slice(DOMAIN);
    out.extend_from_slice(&1_u16.to_be_bytes());
    out.extend_from_slice(&DAYS_PER_TICK.to_be_bytes());
    text(&mut out, compiler)?;
    text(&mut out, &input.scenario_id)?;
    text(&mut out, &input.preset_id)?;
    out.extend_from_slice(
        &input
            .duration
            .canonical_bytes()
            .map_err(|_| EconomicCatalogError::Identity)?,
    );
    out.push(match input.geography {
        CatalogGeography::NationalCounties => 1,
        CatalogGeography::NationalCountiesWithMichiganDetail => 2,
        CatalogGeography::MichiganControl => 3,
    });
    out.extend_from_slice(
        &u16::try_from(input.sources.len())
            .map_err(|_| EconomicCatalogError::Bound)?
            .to_be_bytes(),
    );
    let mut previous = None;
    for source in &input.sources {
        if previous.is_some_and(|kind| kind >= source.kind()) {
            return Err(EconomicCatalogError::WireNoncanonical);
        }
        previous = Some(source.kind());
        out.push(source.kind() as u8);
        out.extend_from_slice(&source.digest());
        out.extend_from_slice(
            &u32::try_from(source.bytes().len())
                .map_err(|_| EconomicCatalogError::Bound)?
                .to_be_bytes(),
        );
        out.extend_from_slice(source.bytes());
    }
    if out.len() != size {
        return Err(EconomicCatalogError::Bound);
    }
    Ok(out)
}
pub(super) fn decode(bytes: &[u8]) -> Result<(EconomicCatalogInput, String)> {
    if bytes.len() > MAX_CATALOG_BYTES {
        return Err(EconomicCatalogError::Bound);
    }
    let mut c = Cursor { bytes, at: 0 };
    if c.take(DOMAIN.len())? != DOMAIN {
        return Err(EconomicCatalogError::WireDomain);
    }
    if u16::from_be_bytes(c.array()?) != 1 {
        return Err(EconomicCatalogError::WireVersion);
    }
    if u64::from_be_bytes(c.array()?) != DAYS_PER_TICK {
        return Err(EconomicCatalogError::CompilerVersion);
    }
    let compiler = c.text()?;
    let scenario_id = c.text()?;
    let preset_id = c.text()?;
    let duration =
        CampaignDuration::decode(c.array()?).map_err(|_| EconomicCatalogError::WireTag)?;
    let geography = match c.byte()? {
        1 => CatalogGeography::NationalCounties,
        2 => CatalogGeography::NationalCountiesWithMichiganDetail,
        3 => CatalogGeography::MichiganControl,
        _ => return Err(EconomicCatalogError::WireTag),
    };
    let count = usize::from(u16::from_be_bytes(c.array()?));
    if count == 0 || count > MAX_SOURCE_ROWS {
        return Err(EconomicCatalogError::Bound);
    }
    let mut sources = Vec::with_capacity(count);
    let mut previous = None;
    for _ in 0..count {
        let kind = SourceArtifactKind::try_from(c.byte()?)?;
        if previous.is_some_and(|p| p >= kind) {
            return Err(EconomicCatalogError::WireNoncanonical);
        }
        previous = Some(kind);
        let digest: [u8; 32] = c.array()?;
        let size = usize::try_from(u32::from_be_bytes(c.array()?))
            .map_err(|_| EconomicCatalogError::Bound)?;
        if size == 0 || size > MAX_SOURCE_BYTES {
            return Err(EconomicCatalogError::Bound);
        }
        let bytes = c.take(size)?;
        if sha256_of(bytes) != digest {
            return Err(EconomicCatalogError::Digest);
        }
        sources.push(SourceArtifact::capture(kind, bytes.to_vec()));
    }
    if c.at != bytes.len() {
        return Err(EconomicCatalogError::WireTrailing);
    }
    Ok((
        EconomicCatalogInput {
            scenario_id,
            preset_id,
            duration,
            sources,
            geography,
            organizer: None,
        },
        compiler,
    ))
}
struct Cursor<'a> {
    bytes: &'a [u8],
    at: usize,
}
impl<'a> Cursor<'a> {
    fn take(&mut self, size: usize) -> Result<&'a [u8]> {
        let end = self
            .at
            .checked_add(size)
            .ok_or(EconomicCatalogError::Bound)?;
        let part = self
            .bytes
            .get(self.at..end)
            .ok_or(EconomicCatalogError::WireTruncated)?;
        self.at = end;
        Ok(part)
    }
    fn array<const N: usize>(&mut self) -> Result<[u8; N]> {
        self.take(N)?
            .try_into()
            .map_err(|_| EconomicCatalogError::WireTruncated)
    }
    fn byte(&mut self) -> Result<u8> {
        Ok(self.array::<1>()?[0])
    }
    fn text(&mut self) -> Result<String> {
        let n = usize::from(u16::from_be_bytes(self.array()?));
        if n == 0 || n > MAX_TEXT_BYTES {
            return Err(EconomicCatalogError::Bound);
        }
        let bytes = self.take(n)?;
        let text = std::str::from_utf8(bytes).map_err(|_| EconomicCatalogError::Identity)?;
        if text.contains('\0') {
            return Err(EconomicCatalogError::Identity);
        }
        Ok(text.to_owned())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // Independent wire fixture: three one-byte identities, continuous clock,
    // national geography, and one GraphDeclarations source containing "abc".
    fn vector() -> Vec<u8> {
        let mut bytes = b"babylon.economic-catalog.v1\0\0\x01\0\0\0\0\0\0\0\x1c\0\x01c\0\x01s\0\x01p\0\0\0\0\0\0\0\0\0\x01\0\x01\x01".to_vec();
        bytes.extend_from_slice(&[
            0xba, 0x78, 0x16, 0xbf, 0x8f, 0x01, 0xcf, 0xea, 0x41, 0x41, 0x40, 0xde, 0x5d, 0xae,
            0x22, 0x23, 0xb0, 0x03, 0x61, 0xa3, 0x96, 0x17, 0x7a, 0x9c, 0xb4, 0x10, 0xff, 0x61,
            0xf2, 0x00, 0x15, 0xad,
        ]);
        bytes.extend_from_slice(b"\0\0\0\x03abc");
        bytes
    }
    #[test]
    fn independent_current_source_vector_round_trips_exactly() {
        let raw = vector();
        let (input, compiler) = decode(&raw).unwrap();
        assert_eq!(compiler, "c");
        assert_eq!(input.scenario_id, "s");
        assert_eq!(input.preset_id, "p");
        assert_eq!(input.duration, CampaignDuration::Continuous);
        assert_eq!(input.geography, CatalogGeography::NationalCounties);
        assert_eq!(input.sources.len(), 1);
        assert_eq!(
            input.sources[0].kind(),
            SourceArtifactKind::GraphDeclarations
        );
        assert_eq!(input.sources[0].bytes(), b"abc");
        assert_eq!(encode(&input, &compiler).unwrap(), raw);
    }
    #[test]
    fn source_wire_refuses_wrong_version_timebase_scope_digest_and_trailing_data() {
        let raw = vector();
        let version = DOMAIN.len() + 1;
        let timebase = DOMAIN.len() + 9;
        let duration_padding = DOMAIN.len() + 27;
        let geography = DOMAIN.len() + 28;
        let source_kind = DOMAIN.len() + 31;
        for (offset, value, error) in [
            (version, 2, EconomicCatalogError::WireVersion),
            (timebase, 27, EconomicCatalogError::CompilerVersion),
            (duration_padding, 1, EconomicCatalogError::WireTag),
            (geography, 4, EconomicCatalogError::WireTag),
            (source_kind, 35, EconomicCatalogError::WireTag),
            (source_kind + 1, 0, EconomicCatalogError::Digest),
        ] {
            let mut altered = raw.clone();
            altered[offset] = value;
            assert_eq!(decode(&altered).err(), Some(error), "offset {offset}");
        }
        let mut trailing = raw.clone();
        trailing.push(0);
        assert_eq!(
            decode(&trailing).err(),
            Some(EconomicCatalogError::WireTrailing)
        );
        for length in 0..raw.len() {
            assert!(decode(&raw[..length]).is_err(), "truncated at {length}");
        }
    }
    #[test]
    fn source_wire_refuses_duplicate_roles_and_unbounded_claims_before_allocation() {
        let raw = vector();
        let count = DOMAIN.len() + 29;
        let row = DOMAIN.len() + 31;
        let mut duplicate = raw.clone();
        duplicate[count + 1] = 2;
        duplicate.extend_from_slice(&raw[row..]);
        assert_eq!(
            decode(&duplicate).err(),
            Some(EconomicCatalogError::WireNoncanonical)
        );
        let mut oversized_count = raw.clone();
        oversized_count[count + 1] = 33;
        assert_eq!(
            decode(&oversized_count).err(),
            Some(EconomicCatalogError::Bound)
        );
        let mut oversized_source = raw;
        oversized_source[row + 33..row + 37].copy_from_slice(&u32::MAX.to_be_bytes());
        assert_eq!(
            decode(&oversized_source).err(),
            Some(EconomicCatalogError::Bound)
        );
    }
}
