//! Rasterize exact relative band widths with fractional coverage at subpixel boundaries.
use super::sankey_layout::{Band, DiagramLayout};
use super::state::{Direction, MoneyView};
use crate::observer_theme as theme;
use bevy::asset::RenderAssetUsages;
use bevy::color::ColorToPacked;
use bevy::prelude::*;
use bevy::render::render_resource::{Extent3d, TextureDimension, TextureFormat};

const WIDTH: u32 = 640;

pub(super) fn paint(layout: &DiagramLayout, view: &MoneyView) -> Image {
    let mut data = vec![0; WIDTH as usize * layout.height as usize * 4];
    let selected = view.selected_row();
    let mut highlighted = None;
    for band in &layout.bands {
        let row = &view.rows[band.row];
        if selected.is_some_and(|r| r.key == row.key) {
            highlighted = Some(band);
            continue;
        }
        let color = match row.key.direction {
            Direction::PaidTo => theme::YELLOW,
            Direction::ReceivedFrom => theme::BLUE,
            Direction::Internal => theme::GRAY,
        };
        stripe(&mut data, layout.height, band, color);
    }
    if let Some(band) = highlighted {
        stripe(&mut data, layout.height, band, theme::PAPER);
    }
    Image::new(
        Extent3d {
            width: WIDTH,
            height: layout.height,
            depth_or_array_layers: 1,
        },
        TextureDimension::D2,
        data,
        TextureFormat::Rgba8UnormSrgb,
        RenderAssetUsages::default(),
    )
}

#[allow(
    clippy::cast_possible_truncation,
    clippy::cast_sign_loss,
    reason = "pixel bounds and coverage are clamped to the bounded chart texture"
)]
fn stripe(pixels: &mut [u8], height: u32, band: &Band, color: Color) {
    let rgba = color.to_srgba().to_u8_array();
    for x in 0..WIDTH {
        let upper = band.upper_at((f64::from(x) + 0.5) / f64::from(WIDTH));
        let lower = upper + band.thickness;
        let start = upper.floor().clamp(0.0, f64::from(height)) as u32;
        let stop = lower.ceil().clamp(0.0, f64::from(height)) as u32;
        for y in start..stop {
            let coverage =
                (lower.min(f64::from(y) + 1.0) - upper.max(f64::from(y))).clamp(0.0, 1.0);
            let idx = ((y * WIDTH + x) * 4) as usize;
            let alpha = (255.0 * coverage).round() as u8;
            if alpha > 0 {
                pixels[idx..idx + 3].copy_from_slice(&rgba[..3]);
                pixels[idx + 3] = alpha;
            }
        }
    }
}
