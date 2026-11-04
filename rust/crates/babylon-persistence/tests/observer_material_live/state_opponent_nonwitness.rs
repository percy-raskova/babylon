//! Restricted reader of a paid visit whose log excludes the controlled actor.

use super::{organizer, DisposableTarget};

#[test]
#[ignore = "requires the task-owned disposable PostgreSQL runtime and national source"]
fn national_city_pd_paid_nonwitness_restricted_archive() {
    let mut target = DisposableTarget::create();
    organizer::state_opponent::qualify_paid_nonwitness(&mut target);
}
