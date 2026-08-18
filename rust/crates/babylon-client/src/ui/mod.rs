//! The player-facing UI surfaces that are not the county map itself
//! (`crate::map`) or the tick loop's own plumbing (`crate::loop_ui`) —
//! B3 wave-1 Task 2 adds the first member, [`time`], the clock/pacing/
//! virtual-time module; Task 3 adds [`admin`], the declared admin surface;
//! Task 4 adds [`beats`], the narrative beat feed + latch card; Task 5 adds
//! [`story_card`], the tick-0 story card, the `N`-key restart, and the
//! §2.11 map-absence banner.

pub mod admin;
pub mod beats;
pub mod story_card;
pub mod time;
