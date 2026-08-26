use babylon_kernel::{ReplayIdentityError, ReplaySeed, ReplaySessionIdV1, RngLayoutVersion};

fn checked_session_from_bytes(bytes: &[u8]) -> Result<ReplaySessionIdV1, ReplayIdentityError> {
    ReplaySessionIdV1::try_from(bytes)
}

fn checked_session_from_string(value: &str) -> Result<ReplaySessionIdV1, ReplayIdentityError> {
    ReplaySessionIdV1::try_from(value)
}

fn seed_from_i64(value: i64) -> ReplaySeed {
    ReplaySeed::new(value)
}

#[test]
fn checked_constructors_accept_graphic_ascii_at_the_session_boundaries() {
    let one = checked_session_from_bytes(b"!").unwrap();
    let maximum = checked_session_from_string(&"~".repeat(256)).unwrap();

    assert_eq!(one.as_bytes(), b"!");
    assert_eq!(maximum.as_bytes(), "~".repeat(256).as_bytes());
}

#[test]
fn canonical_session_bytes_prefix_the_exact_u16_big_endian_length() {
    let session = checked_session_from_string("A9!").unwrap();

    assert_eq!(session.canonical_bytes().unwrap(), b"\0\x03A9!");
}

#[test]
fn checked_session_rejects_non_graphic_or_out_of_range_bytes() {
    let invalid = [
        b"".as_slice(),
        b"has space".as_slice(),
        b"line\nfeed".as_slice(),
        b"del\x7f".as_slice(),
        "non-ascii-é".as_bytes(),
    ];

    for bytes in invalid {
        assert!(checked_session_from_bytes(bytes).is_err(), "{bytes:?}");
    }

    assert!(checked_session_from_string(&"A".repeat(257)).is_err());
}

#[test]
fn replay_seed_uses_exact_signed_i64_big_endian_bytes() {
    let cases = [
        (i64::MIN, [0x80, 0, 0, 0, 0, 0, 0, 0]),
        (-1, [0xff; 8]),
        (0, [0; 8]),
        (1, [0, 0, 0, 0, 0, 0, 0, 1]),
        (i64::MAX, [0x7f, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff]),
    ];

    for (value, expected) in cases {
        assert_eq!(seed_from_i64(value).to_be_bytes(), expected);
    }
}

#[test]
fn rng_layout_version_accepts_only_the_two_governed_layouts() {
    assert_eq!(RngLayoutVersion::try_from(1), Ok(RngLayoutVersion::V1));
    assert_eq!(RngLayoutVersion::try_from(2), Ok(RngLayoutVersion::V2));

    for value in [0, 3, u32::MAX] {
        assert!(matches!(
            RngLayoutVersion::try_from(value),
            Err(ReplayIdentityError::UnsupportedRngLayoutVersion { value: actual }) if actual == value
        ));
    }
}
