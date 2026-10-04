//! Exact checkpoint references; canonical envelope bytes never become storage refs.
use babylon_kernel::content_digest::sha256_of;
const MAX_BYTES: usize = crate::committed_tick_envelope::MAX_COMMITTED_TICK_ROW_BATCH_BYTES;
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(crate) enum Error {
    Tag,
    Source,
    Length,
    Digest,
    Inline,
    Allocation,
}
#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) struct Reference {
    pub tag: u8,
    pub source: u8,
    pub decoded_length: usize,
    pub digest: [u8; 32],
    pub inline: Option<Vec<u8>>,
}
fn source(tag: u8) -> Result<u8, Error> {
    match tag {
        1 => Ok(1),
        2 => Ok(2),
        3..=8 => Ok(3),
        9 => Ok(4),
        _ => Err(Error::Tag),
    }
}
impl Reference {
    pub(crate) fn capture(tag: u8, exact: &[u8]) -> Result<Self, Error> {
        if exact.len() > MAX_BYTES {
            return Err(Error::Length);
        }
        let source = source(tag)?;
        let inline = if tag == 2 {
            let mut bytes = Vec::new();
            bytes
                .try_reserve_exact(exact.len())
                .map_err(|_| Error::Allocation)?;
            bytes.extend_from_slice(exact);
            Some(bytes)
        } else {
            None
        };
        Ok(Self {
            tag,
            source,
            decoded_length: exact.len(),
            digest: sha256_of(exact),
            inline,
        })
    }
    pub(crate) fn from_storage(
        tag: u8,
        stored_source: u8,
        length: usize,
        digest: [u8; 32],
        inline: Option<Vec<u8>>,
    ) -> Result<Self, Error> {
        if stored_source != source(tag)? {
            return Err(Error::Source);
        }
        if length > MAX_BYTES {
            return Err(Error::Length);
        }
        if (tag == 2) != inline.is_some() {
            return Err(Error::Inline);
        }
        if let Some(bytes) = &inline {
            if bytes.len() != length {
                return Err(Error::Length);
            }
            if sha256_of(bytes) != digest {
                return Err(Error::Digest);
            }
        }
        Ok(Self {
            tag,
            source: stored_source,
            decoded_length: length,
            digest,
            inline,
        })
    }
    pub(crate) fn resolve<'a>(
        &'a self,
        graph: &'a [u8],
        foundation: &'a [Vec<u8>; 6],
        semantic: &'a [u8],
    ) -> Result<&'a [u8], Error> {
        let bytes = match self.source {
            1 => graph,
            2 => self.inline.as_deref().ok_or(Error::Inline)?,
            3 => foundation
                .get(usize::from(self.tag).checked_sub(3).ok_or(Error::Tag)?)
                .ok_or(Error::Tag)?
                .as_slice(),
            4 => semantic,
            _ => return Err(Error::Source),
        };
        if self.source != source(self.tag)? {
            return Err(Error::Source);
        }
        if bytes.len() != self.decoded_length {
            return Err(Error::Length);
        }
        if sha256_of(bytes) != self.digest {
            return Err(Error::Digest);
        }
        Ok(bytes)
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn nine_sections_reconstruct_original_exact_bytes_without_duplicate_payloads() {
        let graph = b"graph";
        let semantic = b"semantic";
        let foundation = std::array::from_fn(|i| vec![u8::try_from(i).unwrap(); i + 1]);
        for tag in 1..=9 {
            let original = match tag {
                1 => graph.as_slice(),
                2 => b"world-registers",
                3..=8 => foundation[usize::from(tag) - 3].as_slice(),
                _ => semantic.as_slice(),
            };
            let reference = Reference::capture(tag, original).unwrap();
            assert_eq!(reference.inline.is_some(), tag == 2);
            let restored = reference.resolve(graph, &foundation, semantic).unwrap();
            assert_eq!(restored, original);
            assert_eq!(
                crate::semantic_codec::encode_checkpoint_row(tag, 0, 1, restored).unwrap(),
                crate::semantic_codec::encode_checkpoint_row(tag, 0, 1, original).unwrap()
            );
        }
    }
    #[test]
    fn changed_canonical_sources_and_invalid_inline_shape_refuse() {
        let foundation = std::array::from_fn(|_| Vec::new());
        let reference = Reference::capture(1, b"original").unwrap();
        assert_eq!(
            reference.resolve(b"modified", &foundation, b""),
            Err(Error::Digest)
        );
        assert_eq!(
            Reference::from_storage(2, 1, 0, sha256_of(b""), None),
            Err(Error::Source)
        );
        assert_eq!(
            Reference::from_storage(1, 1, 0, sha256_of(b""), Some(Vec::new())),
            Err(Error::Inline)
        );
        assert_eq!(
            Reference::from_storage(2, 2, 1, sha256_of(b"x"), Some(Vec::new())),
            Err(Error::Length)
        );
        assert_eq!(
            Reference::from_storage(2, 2, 1, sha256_of(b"y"), Some(vec![b'x'])),
            Err(Error::Digest)
        );
        assert_eq!(
            Reference::from_storage(9, 4, MAX_BYTES + 1, [0; 32], None),
            Err(Error::Length)
        );
        assert_eq!(Reference::capture(0, b""), Err(Error::Tag));
    }
}
