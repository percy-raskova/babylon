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
use ratatui::layout::Rect;
use ratatui::style::Color;

/// `hypergraph_rs`'s truecolor triple as a ratatui color.
fn color(rgb: Rgb) -> Color {
    Color::Rgb(rgb.0, rgb.1, rgb.2)
}

/// Blit `grid` into `buf` with its top-left corner at `area`'s origin (Task
/// 32/§5: widened from the M0 walking skeleton's fixed `buf.area` origin so
/// a caller can size the 3D lane to an arbitrary sub-`Rect` of the frame,
/// e.g. a split TOPOLOGY pane that isn't the whole terminal).
///
/// Cells outside `buf`'s area are dropped (`cell_mut` returns `None` out of
/// bounds — never the panicking index path the assessment warns about).
pub fn blit_rect(grid: &CellGrid, buf: &mut Buffer, area: Rect) {
    let origin = (area.x, area.y);
    // Clip to AREA, not merely the buffer (verify-panel): an oversized
    // grid must never bleed into neighbouring widgets.
    let rows = grid.rows.min(area.height);
    let cols = grid.cols.min(area.width);
    for row in 0..rows {
        for col in 0..cols {
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

/// Blit `grid` into `buf`'s full area — the convenience delegate for
/// callers (and the existing M0 golden) that render into a `Buffer` whose
/// area IS the target rect.
pub fn blit(grid: &CellGrid, buf: &mut Buffer) {
    let area = buf.area;
    blit_rect(grid, buf, area);
}

#[cfg(test)]
mod tests {
    use super::*;
    use hypergraph_rs::raster::Cell;

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

    #[test]
    fn blit_rect_offsets_into_a_sub_area() {
        // Task 32/§5: `blit_rect` must place the grid's origin at `area`'s
        // corner, not the buffer's — a TOPOLOGY pane split off from a
        // larger frame is never at (0, 0).
        let grid = CellGrid {
            cols: 1,
            rows: 1,
            cells: vec![Cell {
                ch: '⠁',
                fg: Rgb(1, 2, 3),
                bg: Rgb(4, 5, 6),
            }],
        };
        let mut buf = Buffer::empty(Rect::new(0, 0, 4, 4));
        blit_rect(&grid, &mut buf, Rect::new(2, 1, 2, 2));
        let cell = buf.cell((2, 1)).expect("in bounds at the sub-area origin");
        assert_eq!(cell.symbol(), "⠁");
        assert_eq!(cell.fg, Color::Rgb(1, 2, 3));
        assert_eq!(cell.bg, Color::Rgb(4, 5, 6));
        // The buffer origin itself must be untouched.
        let untouched = buf.cell((0, 0)).expect("in bounds");
        assert_ne!(untouched.symbol(), "⠁");
    }
}
