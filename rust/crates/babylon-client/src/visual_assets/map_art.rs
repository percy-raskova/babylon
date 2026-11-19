//! Select the artist's economic map pieces at launch, independently of simulation state.

use bevy::asset::{AssetServer, Handle, RenderAssetUsages};
use bevy::image::{Image, ImageSampler};
use image::codecs::png::PngDecoder;
use image::{DynamicImage, Limits};
use std::env;
use std::fs::{self, File};
use std::io::{Cursor, Error, ErrorKind, Result};
use std::path::Path;

const BUNDLED: &[u8] = include_bytes!("../../../../../assets/visual/economic-map-atlas.png");
const MAX_FILE_BYTES: u64 = 2 * 1024 * 1024;
const WIDTH: u32 = 512;
const HEIGHT: u32 = 384;
const SYMBOLS: u32 = 9;
const TILE: u32 = 128;

pub(super) fn load(server: &AssetServer) -> Handle<Image> {
    let path = env::var_os("BABYLON_MAP_SYMBOL_ATLAS");
    let image = select(path.as_deref().map(Path::new));
    server.add(image)
}

fn select(path: Option<&Path>) -> Image {
    if let Some(path) = path {
        match read_artist_file(path) {
            Ok(image) => return image,
            Err(error) => log::warn!(
                "BABYLON_MAP_SYMBOL_ATLAS {}: {error}. Using bundled economic map pieces.",
                path.display()
            ),
        }
    }
    decode(BUNDLED).expect("the manifest-verified embedded economic map atlas must decode")
}

fn read_artist_file(path: &Path) -> Result<Image> {
    use std::io::Read;

    if !fs::metadata(path)?.is_file() {
        return Err(Error::new(
            ErrorKind::InvalidInput,
            "expected a regular PNG file",
        ));
    }
    let mut bytes = Vec::new();
    File::open(path)?
        .take(MAX_FILE_BYTES + 1)
        .read_to_end(&mut bytes)?;
    if bytes.len() as u64 > MAX_FILE_BYTES {
        return Err(Error::new(ErrorKind::InvalidData, "PNG exceeds 2 MiB"));
    }
    decode(&bytes)
}

fn decode(bytes: &[u8]) -> Result<Image> {
    use image::GenericImageView;

    let invalid = |message| Error::new(ErrorKind::InvalidData, message);
    if !bytes.starts_with(b"\x89PNG\r\n\x1a\n\x00\x00\x00\x0dIHDR") {
        return Err(invalid("expected a PNG with an IHDR header"));
    }
    if bytes.get(16..20) != Some(WIDTH.to_be_bytes().as_slice())
        || bytes.get(20..24) != Some(HEIGHT.to_be_bytes().as_slice())
    {
        return Err(invalid("expected a 512 by 384 pixel PNG"));
    }
    if bytes.get(25) != Some(&6) {
        return Err(invalid("expected RGBA PNG color type"));
    }
    let mut limits = Limits::default();
    limits.max_image_width = Some(WIDTH);
    limits.max_image_height = Some(HEIGHT);
    limits.max_alloc = Some(8 * 1024 * 1024);
    let image_error = |e| Error::new(ErrorKind::InvalidData, e);
    let decoder = PngDecoder::with_limits(Cursor::new(bytes), limits).map_err(image_error)?;
    let pixels = DynamicImage::from_decoder(decoder)
        .map_err(image_error)?
        .into_rgba8();
    let columns = WIDTH / TILE;
    for index in 0..SYMBOLS {
        let row = index / columns;
        let column = index % columns;
        let tile = pixels.view(column * TILE, row * TILE, TILE, TILE);
        if !tile.pixels().any(|(_, _, pixel)| pixel[3] == 0)
            || !tile.pixels().any(|(_, _, pixel)| pixel[3] > 0)
        {
            return Err(Error::new(
                ErrorKind::InvalidData,
                format!(
                    "tile at row {}, column {} requires transparent and visible pixels",
                    row + 1,
                    column + 1
                ),
            ));
        }
    }
    let mut image = Image::from_dynamic(
        DynamicImage::ImageRgba8(pixels),
        true,
        RenderAssetUsages::default(),
    );
    image.sampler = ImageSampler::linear();
    Ok(image)
}

#[cfg(test)]
mod tests {
    use super::{BUNDLED, HEIGHT, MAX_FILE_BYTES, WIDTH};
    use image::{ImageBuffer, ImageFormat, Rgba, RgbaImage};
    use std::error::Error;
    use std::fs::File;
    use std::io::Cursor;
    use std::{env, fs};

    #[test]
    fn requested_pixels_replace_bundled_pieces_and_a_bad_file_restores_them(
    ) -> Result<(), Box<dyn Error>> {
        let path = env::temp_dir().join(format!("babylon-map-pieces-{}.png", uuid::Uuid::new_v4()));
        let expected = super::select(None)
            .data
            .expect("bundled atlas retains CPU pixels");
        assert_eq!(
            super::select(Some(&path)).data.as_deref(),
            Some(expected.as_slice())
        );

        let mut art = RgbaImage::new(WIDTH, HEIGHT);
        for y in [45, 173] {
            for x in [32, 160, 288, 416] {
                art.put_pixel(x, y, Rgba([61, 111, 193, 255]));
            }
        }
        art.put_pixel(32, 301, Rgba([61, 111, 193, 255]));
        art.save(&path)?;
        assert_eq!(
            super::select(Some(&path)).data.as_deref(),
            Some(art.as_raw().as_slice())
        );
        assert_ne!(art.as_raw(), &expected);
        fs::write(&path, b"invalid PNG")?;
        assert_eq!(
            super::select(Some(&path)).data.as_deref(),
            Some(expected.as_slice())
        );
        File::create(&path)?.set_len(MAX_FILE_BYTES + 1)?;
        assert!(super::read_artist_file(&path)
            .expect_err("invalid artist atlas must be rejected")
            .to_string()
            .contains("2 MiB"));
        fs::remove_file(&path)?;
        Ok(())
    }

    #[test]
    fn refuse_wrong_size_color_channels_or_an_unusable_tile() {
        let mut wrong_size = BUNDLED.to_vec();
        wrong_size[16] = 0xff;
        assert!(super::decode(&wrong_size)
            .expect_err("invalid artist atlas must be rejected")
            .to_string()
            .contains("512 by 384"));
        let mut wrong_channels = BUNDLED.to_vec();
        wrong_channels[25] = 2;
        assert!(super::decode(&wrong_channels)
            .expect_err("invalid artist atlas must be rejected")
            .to_string()
            .contains("RGBA"));
        for alpha in [0, 255] {
            let empty: RgbaImage = ImageBuffer::from_pixel(WIDTH, HEIGHT, Rgba([2, 4, 8, alpha]));
            let mut bytes = Cursor::new(Vec::new());
            empty
                .write_to(&mut bytes, ImageFormat::Png)
                .expect("encode invalid tile fixture");
            assert!(super::decode(bytes.get_ref())
                .expect_err("invalid artist atlas must be rejected")
                .to_string()
                .contains("row 1, column 1"));
        }
    }
}
