//! Database-free capture of one exact replay campaign foundation.

mod content;

pub use content::{FoundationContentError, FoundationContentKind};

#[path = "foundation/bundle.rs"]
mod bundle;

use bundle::FoundationSources;
pub use bundle::{CampaignFoundation, FoundationContentBundle};
