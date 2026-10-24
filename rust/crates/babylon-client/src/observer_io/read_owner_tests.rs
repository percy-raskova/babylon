//! Reader ownership must survive opening without crossing an authority or scope.

use super::{ObservationCache, ObservationCacheKey, ObserverEconomyReader, ObserverVisibility};
use crate::observer::Perspective;
use babylon_persistence::identity::CampaignId;
use babylon_persistence::observer_reader::ObserverEconomyError;

use std::cell::Cell;
use uuid::Uuid;

fn key() -> ObservationCacheKey {
    ObservationCacheKey {
        campaign: CampaignId::from_uuid(Uuid::from_u128(342)),
        epoch: Some(1),
        perspective: Perspective::PlayerKnowledge,
        foundation: Some("a".repeat(64)),
        qualification: None,
    }
}

fn reader(visibility: ObserverVisibility) -> ObserverEconomyReader {
    ObserverEconomyReader::connect(
        &"host=127.0.0.1 port=5432 dbname=babylon user=babylon_observer"
            .parse()
            .expect("the authored literal parses as the declared type"),
        visibility,
    )
    .expect("the test database accepts the connection")
}

#[test]
fn full_reader_owner_survives_opening_and_next_period_work() {
    let mut cache = ObservationCache::default();
    cache.reconcile(key());
    let connects = Cell::new(0);
    for _ in 0..2 {
        let work = cache
            .reader(ObserverVisibility::FullObserver, || {
                connects.set(connects.get() + 1);
                Ok(reader(ObserverVisibility::FullObserver))
            })
            .expect("the fixture call `reader` succeeds for the authored inputs");
        // Work::opening drops its handle before preparing restricted presentation.
        drop(work);
        cache.reconcile(key());
    }
    assert_eq!(
        connects.get(),
        1,
        "a fresh capability loses admitted source ownership"
    );
}

#[test]
fn known_refresh_never_receives_or_replaces_the_full_reader() {
    let mut cache = ObservationCache::default();
    let connects = Cell::new(0);
    for visibility in [
        ObserverVisibility::FullObserver,
        ObserverVisibility::KnownPreview,
        ObserverVisibility::FullObserver,
    ] {
        let work = cache
            .reader(visibility, || {
                connects.set(connects.get() + 1);
                Ok(reader(visibility))
            })
            .expect("the fixture call `reader` succeeds for the authored inputs");
        assert_eq!(work.visibility(), visibility);
    }
    assert_eq!(
        connects.get(),
        2,
        "restricted presentation must preserve the private owner"
    );
}

#[test]
fn changed_campaign_epoch_foundation_or_perspective_replaces_the_owner() {
    for changed in [
        ObservationCacheKey {
            campaign: CampaignId::from_uuid(Uuid::from_u128(343)),
            ..key()
        },
        ObservationCacheKey {
            epoch: Some(2),
            ..key()
        },
        ObservationCacheKey {
            foundation: Some("b".repeat(64)),
            ..key()
        },
        ObservationCacheKey {
            perspective: Perspective::FullObserver,
            ..key()
        },
    ] {
        let mut cache = ObservationCache::default();
        let connects = Cell::new(0);
        for current in [key(), changed] {
            cache.reconcile(current);
            cache
                .reader(ObserverVisibility::FullObserver, || {
                    connects.set(connects.get() + 1);
                    Ok(reader(ObserverVisibility::FullObserver))
                })
                .expect("the fixture call `reader` succeeds for the authored inputs");
        }
        assert_eq!(connects.get(), 2);
    }
}

#[test]
fn crossed_visibility_is_refused_before_reader_retention() {
    let mut cache = ObservationCache::default();
    for expected in [
        ObserverVisibility::FullObserver,
        ObserverVisibility::KnownPreview,
    ] {
        let actual = match expected {
            ObserverVisibility::FullObserver => ObserverVisibility::KnownPreview,
            ObserverVisibility::KnownPreview => ObserverVisibility::FullObserver,
        };
        assert!(matches!(
            cache.reader(expected, || Ok(reader(actual))),
            Err(ObserverEconomyError::Authority)
        ));
        assert_eq!(
            cache
                .reader(expected, || Ok(reader(expected)))
                .expect("the fixture call `reader` succeeds for the authored inputs")
                .visibility(),
            expected
        );
    }
}

#[test]
fn failed_reader_construction_is_retried() {
    let mut cache = ObservationCache::default();
    assert!(matches!(
        cache.reader(ObserverVisibility::FullObserver, || Err(
            ObserverEconomyError::MissingDsn
        )),
        Err(ObserverEconomyError::MissingDsn)
    ));
    assert_eq!(
        cache
            .reader(ObserverVisibility::FullObserver, || Ok(reader(
                ObserverVisibility::FullObserver
            )))
            .expect("the fixture call `reader` succeeds for the authored inputs")
            .visibility(),
        ObserverVisibility::FullObserver
    );
}
