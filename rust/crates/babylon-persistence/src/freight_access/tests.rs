use super::{Access, Reference};
use babylon_kernel::geography::CountyGeoid;
use flate2::write::GzEncoder;
use flate2::Compression;
use std::io::Write;

fn county(id: &str) -> CountyGeoid {
    CountyGeoid::try_from(id).expect("fixture county")
}

#[test]
fn restricted_graph_and_absent_matrix_keep_opposite_directions_distinct() {
    // The retained matrix is produced by the project's turn-aware truck router in
    // tests/unit/tools/test_qualify_michigan_road_terminals.py.
    let bytes = include_str!("fixtures/restricted.json");
    let mut encoder = GzEncoder::new(Vec::new(), Compression::fast());
    encoder
        .write_all(bytes.as_bytes())
        .expect("compress the fixture matrix");
    let compressed = encoder.finish().expect("finish the fixture gzip stream");
    let mut reference = Reference::fixture(bytes, &compressed);
    let wayne = county("26163");
    let other = county("26099");
    assert_eq!(reference.access(wayne, other), Access::Unqualified);
    assert!(reference
        .admit(&compressed[..compressed.len() - 1])
        .is_err());
    assert_eq!(reference.access(wayne, other), Access::Unqualified);
    reference
        .admit(&compressed)
        .expect("authenticated router output");
    assert_eq!(reference.access(wayne, other), Access::NoPermittedPath);
    assert!(
        matches!(reference.access(other, wayne), Access::Reachable { distance_mm } if distance_mm > 0)
    );
    assert_eq!(
        reference.access(wayne, wayne),
        Access::Reachable { distance_mm: 0 }
    );
}

#[test]
fn designed_bands_include_exact_boundaries() {
    assert_eq!(super::distance_band(50_000_000), "0–50 km");
    assert_eq!(super::distance_band(50_000_001), "over 50–150 km");
    assert_eq!(super::distance_band(150_000_001), "over 150–300 km");
    assert_eq!(super::distance_band(300_000_001), "over 300 km");
}
