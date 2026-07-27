//! `hypergraph_rs::raster::CellGrid` → ratatui buffer blit (the 3D lane's
//! foundation, BD-3/BD-10).
//!
//! The adapter is isomorphic per hypergraph-rs's own RATATUI-ASSESSMENT:
//! `Cell { ch, fg, bg }` maps 1:1 onto a ratatui buffer cell via
//! `set_char` + `Color::Rgb`; braille glyphs (U+2800–U+28FF) are always a
//! single `char` of unicode width 1 (guarded by a test below). Pure and
//! deterministic — no clock, no randomness.

use hypergraph_rs::raster::{CellGrid, Rgb};
use ratatui::buffer::Buffer;
use ratatui::style::Color;

/// `hypergraph_rs`'s truecolor triple as a ratatui color.
fn color(rgb: Rgb) -> Color {
    Color::Rgb(rgb.0, rgb.1, rgb.2)
}

/// Blit `grid` into `buf` with its top-left corner at `buf`'s area origin.
///
/// Cells outside `buf`'s area are dropped (`cell_mut` returns `None` out of
/// bounds — never the panicking index path the assessment warns about).
pub fn blit(grid: &CellGrid, buf: &mut Buffer) {
    let origin = (buf.area.x, buf.area.y);
    for row in 0..grid.rows {
        for col in 0..grid.cols {
            let src = &grid.cells[usize::from(row) * usize::from(grid.cols) + usize::from(col)];
            let pos = (origin.0 + col, origin.1 + row);
            if let Some(cell) = buf.cell_mut(pos) {
                cell.set_char(src.ch)
                    .set_fg(color(src.fg))
                    .set_bg(color(src.bg));
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use hypergraph_rs::raster::Cell;
    use ratatui::layout::Rect;

    #[test]
    fn braille_block_is_width_one() {
        // The assessment's load-bearing unverified claim, verified: every
        // braille codepoint must be unicode-width 1, else ratatui blanks the
        // following cell and cell alignment breaks silently.
        for cp in 0x2800..=0x28FFu32 {
            let ch = char::from_u32(cp).expect("braille block is valid chars");
            assert_eq!(
                unicode_width::UnicodeWidthChar::width(ch),
                Some(1),
                "braille U+{cp:04X} must be width 1"
            );
        }
    }

    #[test]
    fn blit_maps_cells_one_to_one_and_drops_out_of_bounds() {
        let grid = CellGrid {
            cols: 2,
            rows: 1,
            cells: vec![
                Cell {
                    ch: '⠿',
                    fg: Rgb(200, 16, 46),
                    bg: Rgb(10, 10, 10),
                },
                Cell {
                    ch: 'x',
                    fg: Rgb(255, 214, 0),
                    bg: Rgb(0, 0, 0),
                },
            ],
        };
        // A 1x1 target: the second column must drop, not panic.
        let mut buf = Buffer::empty(Rect::new(0, 0, 1, 1));
        blit(&grid, &mut buf);
        let cell = buf.cell((0, 0)).expect("in bounds");
        assert_eq!(cell.symbol(), "⠿");
        assert_eq!(cell.fg, Color::Rgb(200, 16, 46));
        assert_eq!(cell.bg, Color::Rgb(10, 10, 10));
    }
}
