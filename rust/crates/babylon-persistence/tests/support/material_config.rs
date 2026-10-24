//! Explicit shipped-content input; the production runtime has no implicit defaults.
use babylon_persistence::michigan_material::MichiganMaterialCatalog;

pub fn catalog() -> MichiganMaterialCatalog {
    MichiganMaterialCatalog::from_defines_toml(include_str!(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../../../content/scenarios/michigan/defines.toml"
    )))
    .expect("shipped numeric material fixture")
}
