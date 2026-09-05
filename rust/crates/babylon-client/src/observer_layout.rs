//! Shared geometry for the world, persistent log, and progressive context panels.

use bevy::prelude::*;

#[derive(Component, Clone, Copy)]
pub(crate) enum ObserverRegion {
    Context,
    Log,
    History,
    Footer,
}

/// Logical UI coordinates. The world rectangle is converted back to window
/// coordinates once, for both camera viewports and pointer hit testing.
pub(crate) struct ObserverLayout {
    pub world: Rect,
    context: Rect,
    log: Rect,
    history: Rect,
    footer: Rect,
}

impl ObserverLayout {
    pub fn new(window_size: Vec2, scale: f32, history_open: bool) -> Self {
        let size = window_size / scale;
        let sidebar_width = (size.x * 0.24).clamp(280.0, 380.0);
        let world_right = (size.x - sidebar_width - 32.0).max(200.0);
        let context_bottom = size.y - 76.0;
        let context_top = (context_bottom - 156.0).max(200.0);
        let history_top = (context_bottom - 236.0).max(164.0);
        Self {
            world: Rect::new(
                16.0,
                100.0,
                world_right,
                if history_open {
                    history_top
                } else {
                    context_top
                } - 12.0,
            ),
            context: Rect::new(16.0, context_top, world_right, context_bottom),
            history: Rect::new(16.0, history_top, world_right, context_bottom),
            log: Rect::new(world_right + 16.0, 100.0, size.x - 16.0, size.y - 12.0),
            footer: Rect::new(16.0, size.y - 64.0, world_right, size.y - 12.0),
        }
    }

    pub fn region(&self, region: ObserverRegion) -> Rect {
        match region {
            ObserverRegion::Context => self.context,
            ObserverRegion::Log => self.log,
            ObserverRegion::History => self.history,
            ObserverRegion::Footer => self.footer,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn world_and_panels_remain_disjoint_at_supported_sizes_and_scales() {
        for size in [Vec2::new(1366.0, 768.0), Vec2::new(1920.0, 1080.0)] {
            for scale in [1.0, 1.15, 1.3] {
                for history_open in [false, true] {
                    let layout = ObserverLayout::new(size, scale, history_open);
                    let bottom = if history_open {
                        layout.history
                    } else {
                        layout.context
                    };
                    assert!(layout.world.width() > 600.0);
                    assert!(layout.world.height() > 100.0);
                    assert!(layout.world.max.y < bottom.min.y);
                    assert!(bottom.max.y < layout.footer.min.y);
                    for region in [layout.world, bottom, layout.footer] {
                        assert!(region.max.x < layout.log.min.x);
                        assert!(region.min.x >= 0.0 && region.min.y >= 0.0);
                        assert!(region.max.x <= size.x / scale);
                        assert!(region.max.y <= size.y / scale);
                    }
                    assert!(layout.log.max.x <= size.x / scale);
                    assert!(layout.log.max.y <= size.y / scale);
                }
            }
        }
    }
}
