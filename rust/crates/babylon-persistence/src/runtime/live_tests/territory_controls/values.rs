use babylon_bsl::identity_codec::StableBslValue;
use babylon_graph::stable_element::StableElementKey;
use babylon_tick::material_state::TerritoryStateRow;

fn rows(changed: bool) -> Vec<TerritoryStateRow> {
    let node = StableElementKey::Node {
        scenario: "proof".into(),
        local_name: "member".into(),
    };
    let group = StableElementKey::Hyperedge {
        scenario: "proof".into(),
        local_name: "group".into(),
    };
    let edge = StableElementKey::Edge {
        scenario: "proof".into(),
        edge_type: "member-of".into(),
        source_local_name: "member".into(),
        target_local_name: "group".into(),
    };
    let fields = vec![
        ("01-int-min".into(), StableBslValue::Int(i64::MIN)),
        ("02-int-max".into(), StableBslValue::Int(i64::MAX)),
        (
            "03-currency-min".into(),
            StableBslValue::CurrencyMicroUnits(i128::MIN),
        ),
        (
            "04-currency-max".into(),
            StableBslValue::CurrencyMicroUnits(i128::MAX),
        ),
        (
            "05-real".into(),
            StableBslValue::RealBits(if changed {
                1.0_f64.to_bits()
            } else {
                (-0.0_f64).to_bits()
            }),
        ),
        (
            "06-ratio-no-floor".into(),
            StableBslValue::RatioBits {
                value: 1.0_f64.to_bits(),
                floor: None,
                cap: Some(2.0_f64.to_bits()),
            },
        ),
        (
            "07-ratio-no-cap".into(),
            StableBslValue::RatioBits {
                value: 1.0_f64.to_bits(),
                floor: Some(0.25_f64.to_bits()),
                cap: None,
            },
        ),
        ("08-false".into(), StableBslValue::Bool(false)),
        (
            "09-enum".into(),
            StableBslValue::Enum {
                enum_type: "A".repeat(64),
                member: "Z".repeat(64),
            },
        ),
        ("10-node".into(), StableBslValue::Node(node)),
        ("11-hyperedge".into(), StableBslValue::Hyperedge(group)),
        ("12-edge".into(), StableBslValue::Edge(edge)),
    ];
    [("empty", Vec::new()), ("typed", fields)]
        .into_iter()
        .map(|(name, fields)| {
            TerritoryStateRow::try_new(
                StableElementKey::Node {
                    scenario: "proof".into(),
                    local_name: name.into(),
                },
                fields,
            )
            .unwrap()
        })
        .collect()
}
