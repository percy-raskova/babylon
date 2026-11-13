//! Stable neutral geographic fills, admitted against the complete rendered atlas.

use std::sync::OnceLock;

use babylon_kernel::content_digest;
use bevy::prelude::Color;
use serde::Deserialize;

use crate::atlas::CountyAtlas;

const ATLAS_BYTES: &[u8] = include_bytes!(concat!(
    env!("CARGO_MANIFEST_DIR"),
    "/../../../assets/map/county_atlas.bin"
));
const PALETTE_JSON: &str = include_str!(concat!(
    env!("CARGO_MANIFEST_DIR"),
    "/../../../assets/map/county_palette.json"
));

// Designed geographic blue, sage, ochre and mauve. Metric encodings live elsewhere.
const COLORS: [Color; 4] = [
    Color::srgb_u8(76, 111, 137),
    Color::srgb_u8(112, 135, 107),
    Color::srgb_u8(168, 137, 82),
    Color::srgb_u8(145, 108, 137),
];
pub(crate) const WAYNE_OUTLINE: Color = Color::srgb_u8(239, 191, 91);

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct PaletteAsset {
    schema_version: u32,
    atlas_sha256: String,
    counties: Vec<CountyColor>,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct CountyColor {
    fips: String,
    color: usize,
}

#[derive(Debug)]
struct CountyPalette {
    counties: Vec<CountyColor>,
}

impl CountyPalette {
    fn parse(json: &str, atlas_bytes: &[u8]) -> Result<Self, String> {
        use std::fmt::Write;

        let asset: PaletteAsset = serde_json::from_str(json)
            .map_err(|error| format!("invalid county palette JSON: {error}"))?;
        if asset.schema_version != 1 {
            return Err("unsupported county palette version".into());
        }
        let digest = content_digest::sha256_of(atlas_bytes).iter().fold(
            String::with_capacity(64),
            |mut output, byte| {
                write!(output, "{byte:02x}").expect("writing to String succeeds");
                output
            },
        );
        if asset.atlas_sha256 != digest {
            return Err("county palette atlas digest mismatch".into());
        }
        let atlas = CountyAtlas::parse(atlas_bytes)
            .map_err(|error| format!("county palette atlas admission failed: {error}"))?;
        if asset.counties.len() != atlas.len() {
            return Err("county palette must cover every atlas FIPS exactly once".into());
        }
        if asset
            .counties
            .windows(2)
            .any(|rows| rows[0].fips >= rows[1].fips)
        {
            return Err("county palette FIPS must be unique and ordered".into());
        }
        for (index, county) in asset.counties.iter().enumerate() {
            if atlas.county(index).map(|row| row.fips) != Some(county.fips.as_str()) {
                return Err(
                    "county palette FIPS must be complete, unique and atlas-ordered".into(),
                );
            }
            if county.color >= COLORS.len() {
                return Err("county palette index must be in 0..4".into());
            }
        }
        Ok(Self {
            counties: asset.counties,
        })
    }

    fn color(&self, fips: &str) -> Color {
        let index = self
            .counties
            .binary_search_by(|row| row.fips.as_str().cmp(fips))
            .expect("rendered county belongs to the admitted complete atlas palette");
        COLORS[self.counties[index].color]
    }
}

/// One immutable palette for every scope, period and neutral map view.
///
/// # Panics
/// If the embedded companion does not match the complete embedded atlas, or if
/// the caller names a county outside that atlas. Malformed assets have no fallback.
pub(crate) fn color(fips: &str) -> Color {
    static PALETTE: OnceLock<CountyPalette> = OnceLock::new();
    PALETTE
        .get_or_init(|| {
            CountyPalette::parse(PALETTE_JSON, ATLAS_BYTES)
                .unwrap_or_else(|error| panic!("county palette admission failed: {error}"))
        })
        .color(fips)
}

#[cfg(test)]
mod tests {
    use super::{CountyPalette, ATLAS_BYTES, COLORS, PALETTE_JSON};
    use serde_json::Value;

    #[test]
    fn companion_covers_every_county_and_has_four_stable_colors() {
        let palette = CountyPalette::parse(PALETTE_JSON, ATLAS_BYTES).expect("valid companion");
        assert_eq!(palette.counties.len(), 3222);
        for county in &palette.counties {
            assert_eq!(palette.color(&county.fips), super::color(&county.fips));
            assert!(COLORS.contains(&palette.color(&county.fips)));
        }
    }

    #[test]
    fn malformed_or_mismatched_assets_are_refused_without_fallback() {
        let original: Value = serde_json::from_str(PALETTE_JSON).expect("fixture JSON");
        for mutation in 0..7 {
            let mut asset = original.clone();
            match mutation {
                0 => asset["schema_version"] = 2.into(),
                1 => asset["atlas_sha256"] = "wrong".into(),
                2 => {
                    let _ = asset["counties"].as_array_mut().expect("array").pop();
                }
                3 => asset["counties"][1]["fips"] = asset["counties"][0]["fips"].clone(),
                4 => asset["counties"][0]["fips"] = "99999".into(),
                5 => asset["counties"][0]["color"] = 4.into(),
                6 => asset["counties"].as_array_mut().expect("array").swap(0, 1),
                _ => unreachable!(),
            }
            assert!(
                CountyPalette::parse(&asset.to_string(), ATLAS_BYTES).is_err(),
                "mutation {mutation} must fail admission"
            );
        }
    }
}
