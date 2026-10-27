//! The aggregate material-row decoder must be the strict inverse of its encoder.
//!
//! Durable restore reads the `SemanticState` bytes a committed period published,
//! so the decoder must reproduce the exact typed rows and refuse every frame the
//! encoder could not have produced.

use babylon_bsl::identity_codec::StableBslValue;
use babylon_graph::stable_element::StableElementKey;
use babylon_kernel::H3CellId;
use babylon_tick::h3_runtime::MichiganDynamicHexValueBits;
use babylon_tick::material_state::{
    DynamicHexStateRow, MaterialStateError, MaterialStateRows, MaterialStateRowsInput,
    OrganizationStateRow, TerritoryStateRow, WorldRegisterRow,
};

fn node_key(local_name: &str) -> StableElementKey {
    StableElementKey::Node {
        scenario: "test/material-state".to_owned(),
        local_name: local_name.to_owned(),
    }
}

fn authored_rows() -> MaterialStateRows {
    let value_bits = MichiganDynamicHexValueBits {
        c: 0.25_f64.to_bits(),
        v: 0.5_f64.to_bits(),
        s: 0.75_f64.to_bits(),
        k: 0.125_f64.to_bits(),
        biocapacity_stock: 2.0_f64.to_bits(),
        energy_stock: 3.0_f64.to_bits(),
        raw_material_stock: 4.0_f64.to_bits(),
        internet_access_pct: 0.5_f64.to_bits(),
        surveillance_coupling: 0.5_f64.to_bits(),
    };
    MaterialStateRows::try_from_rows(MaterialStateRowsInput {
        world_registers: vec![WorldRegisterRow::try_new(
            "world/completed-tick".to_owned(),
            StableBslValue::Int(7),
        )
        .expect("the derived world register row is canonical")],
        territories: vec![TerritoryStateRow::try_new(
            node_key("territory-a"),
            vec![(
                "social-class/employed-population".to_owned(),
                StableBslValue::Int(5),
            )],
        )
        .expect("the authored territory row is canonical")],
        dynamic_hexes: vec![DynamicHexStateRow::try_new(
            H3CellId::try_from(0x0872_6648_00ff_ffff_u64)
                .expect("the fixture cell is one valid H3 index"),
            value_bits,
        )
        .expect("the authored dynamic row is canonical")],
        organizations: vec![OrganizationStateRow::try_new(
            node_key("organization-a"),
            StableBslValue::Enum {
                enum_type: "OrgKind".to_owned(),
                member: "FIRM".to_owned(),
            },
            vec![node_key("territory-a")],
            vec![(
                "business/probability".to_owned(),
                StableBslValue::RealBits(0.5_f64.to_bits()),
            )],
        )
        .expect("the authored organization row is canonical")],
    })
    .expect("the authored rows compose one canonical checkpoint")
}

#[test]
fn material_state_rows_decoder_is_the_exact_inverse_of_the_encoder() {
    let rows = authored_rows();
    let decoded = MaterialStateRows::decode(rows.canonical_bytes()).expect("canonical rows decode");
    assert_eq!(
        decoded.canonical_bytes(),
        rows.canonical_bytes(),
        "the decoded rows preserve the exact canonical bytes"
    );
    assert_eq!(
        decoded.source_digest(),
        rows.source_digest(),
        "the decoded rows preserve their source digest"
    );
    assert_eq!(
        decoded.source_count(),
        4,
        "the decoded rows keep the aggregate row count"
    );
    assert_eq!(
        decoded.world_registers().rows(),
        rows.world_registers().rows(),
        "the world-register batch round-trips"
    );
    assert_eq!(
        decoded.territories().rows(),
        rows.territories().rows(),
        "the territory batch round-trips"
    );
    assert_eq!(
        decoded.dynamic_hexes().rows(),
        rows.dynamic_hexes().rows(),
        "the dynamic-H3 batch round-trips"
    );
    assert_eq!(
        decoded.organizations().rows(),
        rows.organizations().rows(),
        "the organization batch round-trips"
    );
}

#[test]
fn material_state_rows_decoder_refuses_every_noncanonical_frame() {
    let rows = authored_rows();
    let bytes = rows.canonical_bytes();

    let mut wrong_domain = bytes.to_vec();
    wrong_domain[0] ^= 0xff;
    assert_eq!(
        MaterialStateRows::decode(&wrong_domain),
        Err(MaterialStateError::Frame {
            reason: "material state rows domain"
        })
    );

    let mut wrong_version = bytes.to_vec();
    let version = b"babylon.material-state-rows\0".len();
    wrong_version[version + 3] = 2;
    assert_eq!(
        MaterialStateRows::decode(&wrong_version),
        Err(MaterialStateError::Frame {
            reason: "material state rows layout version"
        })
    );

    let mut trailing = bytes.to_vec();
    trailing.push(0);
    assert_eq!(
        MaterialStateRows::decode(&trailing),
        Err(MaterialStateError::Frame {
            reason: "material state rows trailing bytes"
        })
    );

    let truncated = &bytes[..bytes.len() - 1];
    assert_eq!(
        MaterialStateRows::decode(truncated),
        Err(MaterialStateError::Frame {
            reason: "the material state row frames are truncated"
        })
    );
}

#[test]
fn material_state_rows_decoder_refuses_a_family_interleaved_frame() {
    let rows = authored_rows();
    let bytes = rows.canonical_bytes();
    // The aggregate frame has no family tag, so a frame may name its families in
    // any order. Only the encoder's exact world/territory/dynamic/organization
    // order is canonical, and a decoded frame must reproduce it.
    let header = b"babylon.material-state-rows\0".len() + 4 + 4;
    let mut offset = header;
    let mut frames = Vec::new();
    while offset < bytes.len() {
        let length = usize::try_from(u32::from_be_bytes(
            bytes[offset..offset + 4]
                .try_into()
                .expect("each frame carries a four-byte width"),
        ))
        .expect("the frame width fits the host");
        let start = offset;
        offset += 4 + length;
        frames.push(&bytes[start..offset]);
    }
    assert_eq!(frames.len(), 4, "the fixture encodes four rows");
    let mut interleaved = bytes[..header].to_vec();
    for frame in [frames[1], frames[0], frames[2], frames[3]] {
        interleaved.extend_from_slice(frame);
    }
    assert_eq!(
        MaterialStateRows::decode(&interleaved),
        Err(MaterialStateError::NonCanonicalState),
        "a decodable but non-canonical family order is refused"
    );
}
