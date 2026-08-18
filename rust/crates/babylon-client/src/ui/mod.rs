//! The player-facing UI surfaces that are not the county map itself
//! (`crate::map`) or the tick loop's own plumbing (`crate::loop_ui`) —
//! B3 wave-1 Task 2 adds the first member, [`time`], the clock/pacing/
//! virtual-time module; Task 3 adds [`admin`], the declared admin surface.

pub mod admin;
pub mod time;
