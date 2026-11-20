//! Current independent source envelope. Derived opening rows are never encoded.
use super::{
    CatalogGeography, EconomicCatalogError, EconomicCatalogInput, SourceArtifact,
    SourceArtifactKind,
};
use babylon_kernel::clock::{CampaignDuration, DAYS_PER_TICK};
use babylon_kernel::content_digest;
use std::result::Result as StdResult;

type Result<T> = StdResult<T, EconomicCatalogError>;
pub(super) const DOMAIN: &[u8] = b"babylon.economic-catalog.v1\0";
pub(super) const MAX_CATALOG_BYTES: usize = 64 * 1024 * 1024;
const MAX_SOURCE_BYTES: usize = 32 * 1024 * 1024;
const MAX_SOURCE_ROWS: usize = 32;
const MAX_TEXT_BYTES: usize = 128;
// Matches the authoritative practice-contract organizer codec bound.
const MAX_ORGANIZER_CONFIG_BYTES: usize = 32 * 1024 * 1024;
/// The one compiler whose frame ends with the county review's footer. A catalog of an earlier
/// compiler keeps its bytes and has no county.
pub(super) const COUNTY_REVIEW_COMPILER: &str = "national-world-v12";
fn frames_county_review(compiler: &str) -> bool {
    compiler == COUNTY_REVIEW_COMPILER
}
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
    let footers = Footers::of(input, compiler)?;
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
        .and_then(|size| size.checked_add(footers.size()))
        .ok_or(EconomicCatalogError::Bound)?;
    if size > MAX_CATALOG_BYTES {
        return Err(EconomicCatalogError::Bound);
    }
    let mut out = Vec::new();
    out.try_reserve_exact(size)
        .map_err(|_| EconomicCatalogError::Bound)?;
    out.extend_from_slice(DOMAIN);
    out.extend_from_slice(&3_u16.to_be_bytes());
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
    footers.append(&mut out)?;
    if out.len() != size {
        return Err(EconomicCatalogError::Bound);
    }
    Ok(out)
}
/// The optional configurations that end a frame, encoded, in frame order.
struct Footers {
    organizer: Option<Vec<u8>>,
    city_pd: Option<Vec<u8>>,
    county_review: Option<Vec<u8>>,
    /// Whether the compiler frames the county review at all.
    county_framed: bool,
}
impl Footers {
    fn of(input: &EconomicCatalogInput, compiler: &str) -> Result<Self> {
        let organizer = input
            .organizer
            .as_ref()
            .map(babylon_practice_contract::encode_organizer_config)
            .transpose()
            .map_err(|_| EconomicCatalogError::Identity)?;
        if organizer.as_ref().map_or(0, Vec::len) > MAX_ORGANIZER_CONFIG_BYTES {
            return Err(EconomicCatalogError::Bound);
        }
        let city_pd = input
            .city_pd
            .as_ref()
            .map(babylon_practice_contract::encode_city_pd_config)
            .transpose()
            .map_err(|_| EconomicCatalogError::Identity)?;
        let county_review = input
            .county_review
            .as_ref()
            .map(babylon_practice_contract::encode_county_review_config)
            .transpose()
            .map_err(|_| EconomicCatalogError::Identity)?;
        let county_framed = frames_county_review(compiler);
        if county_review.is_some() && !county_framed {
            return Err(EconomicCatalogError::Identity);
        }
        Ok(Self {
            organizer,
            city_pd,
            county_review,
            county_framed,
        })
    }
    /// Bytes the footers take: a tag and a length for each, and the configuration it holds.
    fn size(&self) -> usize {
        let held = |value: &Option<Vec<u8>>| 5 + value.as_ref().map_or(0, Vec::len);
        let county = if self.county_framed {
            held(&self.county_review)
        } else {
            0
        };
        held(&self.organizer) + held(&self.city_pd) + county
    }
    fn append(self, out: &mut Vec<u8>) -> Result<()> {
        append_optional(out, self.organizer)?;
        append_optional(out, self.city_pd)?;
        if self.county_framed {
            append_optional(out, self.county_review)?;
        }
        Ok(())
    }
}
fn append_optional(out: &mut Vec<u8>, value: Option<Vec<u8>>) -> Result<()> {
    match value {
        None => {
            out.push(0);
            out.extend_from_slice(&0_u32.to_be_bytes());
        }
        Some(encoded) => {
            out.push(1);
            out.extend_from_slice(
                &u32::try_from(encoded.len())
                    .map_err(|_| EconomicCatalogError::Bound)?
                    .to_be_bytes(),
            );
            out.extend_from_slice(&encoded);
        }
    }
    Ok(())
}
pub(super) fn decode(bytes: &[u8]) -> Result<(EconomicCatalogInput, String)> {
    if bytes.len() > MAX_CATALOG_BYTES {
        return Err(EconomicCatalogError::Bound);
    }
    let mut c = Cursor { bytes, at: 0 };
    if c.take(DOMAIN.len())? != DOMAIN {
        return Err(EconomicCatalogError::WireDomain);
    }
    if u16::from_be_bytes(c.array()?) != 3 {
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
        if content_digest::sha256_of(bytes) != digest {
            return Err(EconomicCatalogError::Digest);
        }
        sources.push(SourceArtifact::capture(kind, bytes.to_vec()));
    }
    let organizer = c
        .optional_frame()?
        .map(babylon_practice_contract::decode_organizer_config)
        .transpose()
        .map_err(|_| EconomicCatalogError::Identity)?;
    let city_pd = c
        .optional_frame()?
        .map(babylon_practice_contract::decode_city_pd_config)
        .transpose()
        .map_err(|_| EconomicCatalogError::Identity)?;
    let county_review = if frames_county_review(&compiler) {
        c.optional_frame()?
            .map(babylon_practice_contract::decode_county_review_config)
            .transpose()
            .map_err(|_| EconomicCatalogError::Identity)?
    } else {
        None
    };
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
            organizer,
            city_pd,
            county_review,
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
    /// One optional footer: a presence tag, a length and the bytes. Absent is tag zero and length
    /// zero; present is tag one and a positive, bounded length.
    fn optional_frame(&mut self) -> Result<Option<&'a [u8]>> {
        let tag = self.byte()?;
        let length = usize::try_from(u32::from_be_bytes(self.array()?))
            .map_err(|_| EconomicCatalogError::Bound)?;
        if length > MAX_ORGANIZER_CONFIG_BYTES {
            return Err(EconomicCatalogError::Bound);
        }
        match (tag, length) {
            (0, 0) => Ok(None),
            (1, n) if n > 0 => self.take(n).map(Some),
            _ => Err(EconomicCatalogError::WireNoncanonical),
        }
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
    use crate::identity::CampaignId;
    use crate::michigan_defines::MichiganDefines;
    use uuid::Uuid;

    // Independent wire fixture: three one-byte identities, continuous clock,
    // national geography, and one GraphDeclarations source containing "abc".
    fn vector() -> Vec<u8> {
        let mut bytes = b"babylon.economic-catalog.v1\0\0\x03\0\0\0\0\0\0\0\x1c\0\x01c\0\x01s\0\x01p\0\0\0\0\0\0\0\0\0\x01\0\x01\x01".to_vec();
        bytes.extend_from_slice(&[
            0xba, 0x78, 0x16, 0xbf, 0x8f, 0x01, 0xcf, 0xea, 0x41, 0x41, 0x40, 0xde, 0x5d, 0xae,
            0x22, 0x23, 0xb0, 0x03, 0x61, 0xa3, 0x96, 0x17, 0x7a, 0x9c, 0xb4, 0x10, 0xff, 0x61,
            0xf2, 0x00, 0x15, 0xad,
        ]);
        bytes.extend_from_slice(b"\0\0\0\x03abc");
        bytes.extend_from_slice(&[0; 10]); // Explicit absent organizer and agency frames.
        bytes
    }
    #[test]
    fn independent_current_source_vector_round_trips_exactly() {
        let raw = vector();
        let (input, compiler) = decode(&raw).expect("the committed canonical bytes decode");
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
        assert_eq!(
            encode(&input, &compiler).expect("the fixture value encodes canonically"),
            raw
        );
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
            (version, 1, EconomicCatalogError::WireVersion),
            (timebase, 27, EconomicCatalogError::CompilerVersion),
            (duration_padding, 1, EconomicCatalogError::WireTag),
            (geography, 4, EconomicCatalogError::WireTag),
            (source_kind, 37, EconomicCatalogError::WireTag),
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
        duplicate.truncate(raw.len() - 10);
        duplicate.extend_from_slice(&raw[row..raw.len() - 10]);
        duplicate.extend_from_slice(&raw[raw.len() - 10..]);
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
    #[test]
    fn only_the_county_compiler_frames_a_county_review_footer() {
        let raw = vector();
        let (input, _) = decode(&raw).expect("the committed canonical bytes decode");
        // A compiler that does not frame the county ends after the City PD's footer and keeps the
        // bytes it always had.
        assert_eq!(encode(&input, "c").expect("it encodes"), raw);
        let framed =
            encode(&input, COUNTY_REVIEW_COMPILER).expect("the county's compiler frames it");
        let unframed_length = encode(&input, "national-world-v11")
            .expect("an earlier compiler encodes")
            .len();
        // The two names are as long as each other; the county's frame has a footer more.
        assert_eq!(framed.len(), unframed_length + 5);
        assert_eq!(&framed[framed.len() - 15..], &[0; 15]);
        let (decoded, compiler) = decode(&framed).expect("the framed bytes decode");
        assert_eq!(compiler, COUNTY_REVIEW_COMPILER);
        assert_eq!(decoded.county_review, None);
        assert_eq!(
            encode(&decoded, &compiler).expect("it encodes again"),
            framed
        );
        // The footer cannot be dropped from the county's frame, and a footer cannot be added to
        // another compiler's.
        assert_eq!(
            decode(&framed[..framed.len() - 5]).err(),
            Some(EconomicCatalogError::WireTruncated)
        );
        let mut padded = encode(&input, "national-world-v11").expect("an earlier compiler encodes");
        padded.extend_from_slice(&[0; 5]);
        assert_eq!(
            decode(&padded).err(),
            Some(EconomicCatalogError::WireTrailing)
        );
        // The footer is a presence tag and a length that cannot disagree.
        let mut lying = framed.clone();
        let tag = lying.len() - 5;
        lying[tag] = 1;
        assert_eq!(
            decode(&lying).err(),
            Some(EconomicCatalogError::WireNoncanonical)
        );
    }
    #[test]
    fn current_catalog_frame_retains_campaign_config_and_refuses_old_version() {
        let mut input = EconomicCatalogInput {
            scenario_id: "s".into(),
            preset_id: "p".into(),
            duration: CampaignDuration::Continuous,
            geography: CatalogGeography::MichiganControl,
            sources: vec![SourceArtifact::capture(
                SourceArtifactKind::GraphDeclarations,
                b"x".to_vec(),
            )],
            organizer: None,
            city_pd: None,
            county_review: None,
        };
        let d = MichiganDefines::parse(include_str!(concat!(
            env!("CARGO_MANIFEST_DIR"),
            "/../../../content/scenarios/michigan/defines.toml"
        )))
        .expect("the authored literal parses as the declared type");
        let campaign = CampaignId::from_uuid(Uuid::from_u128(26163));
        let config = crate::organizer_content::config(campaign, &d.organizer, [7; 32])
            .expect("the fixture call `config` succeeds for the authored inputs");
        input.organizer = Some(config.clone());
        let bytes =
            encode(&input, "michigan-control-v1").expect("the fixture value encodes canonically");
        let (decoded, _) = decode(&bytes).expect("the committed canonical bytes decode");
        assert_eq!(decoded.organizer, Some(config));
        assert_eq!(
            encode(&decoded, "michigan-control-v1").expect("the fixture value encodes canonically"),
            bytes
        );
        let mut old = bytes.clone();
        old[DOMAIN.len() + 1] = 2;
        assert_eq!(
            decode(&old).expect_err("the malformed bytes are refused"),
            EconomicCatalogError::WireVersion
        );
        let mut trailing = bytes.clone();
        trailing.push(0);
        assert_eq!(
            decode(&trailing).expect_err("the malformed bytes are refused"),
            EconomicCatalogError::WireTrailing
        );
        // Config presence and encoded length cannot disagree.
        let mut absent = bytes;
        let marker = absent.len()
            - babylon_practice_contract::encode_organizer_config(
                input
                    .organizer
                    .as_ref()
                    .expect("the fixture set the optional field before this read"),
            )
            .expect("the fixture value encodes to its canonical bytes")
            .len()
            - 10;
        absent[marker] = 0;
        assert_eq!(
            decode(&absent).expect_err("the malformed bytes are refused"),
            EconomicCatalogError::WireNoncanonical
        );
    }
}
