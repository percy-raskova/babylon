//! The national campaign must advance past the shipped per-close capacity ceilings.

use std::path::PathBuf;
use std::sync::atomic::{AtomicU64, Ordering};

use babylon_persistence::qualification_audit::national;

struct Scratch(PathBuf);

impl Scratch {
    fn new() -> Self {
        static NEXT: AtomicU64 = AtomicU64::new(0);
        let path = std::env::temp_dir().join(format!(
            "babylon-national-horizon-{}-{}",
            std::process::id(),
            NEXT.fetch_add(1, Ordering::Relaxed)
        ));
        Self(path)
    }
}

impl Drop for Scratch {
    fn drop(&mut self) {
        std::fs::remove_dir_all(&self.0).ok();
    }
}

#[test]
fn national_campaign_advances_past_the_shipped_delivery_order_ceiling() {
    let scratch = Scratch::new();
    let output = scratch.0.join("evidence");
    let store = output.join("campaign.sqlite");
    let run = national::run_national(&store, &output, 4)
        .expect("the national campaign advances four ordinary turns");
    assert_eq!(run.periods, 4);
    assert_eq!(run.advances.len(), 4);
    assert_eq!(run.charges.len(), 4);
}
