//! Shared admitted material foundation for durable database integration tests.
use super::material_runtime::MaterialRuntimeFoundation;
use super::michigan_content::MichiganContentPreset;
use super::michigan_material::MichiganDeliveryPreset;
use super::michigan_material::MichiganMaterialCatalog;

pub fn foundation() -> MaterialRuntimeFoundation {
    let catalog = MichiganMaterialCatalog::from_defines_toml(include_str!(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../../../content/scenarios/michigan/defines.toml"
    )))
    .expect("current authored material parameters");
    MichiganContentPreset::new_campaign(MichiganDeliveryPreset::Standard)
        .create_foundation(&catalog)
        .expect("current material foundation")
}
