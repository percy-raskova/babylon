//! Native campaign catalog and read-only comparison of separately committed worlds.

mod aggregate;

#[path = "campaign_browser/state.rs"]
mod state;

use state::staffing_difference;
pub(crate) use state::{preference_path, write_preference, ComparisonPanel};
pub use state::{CampaignBrowserCommand, CampaignBrowserPlugin, ComparisonSection};
