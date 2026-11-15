//! Publication refuses an uncaptured county even when every real account matches.
use super::{
    CampaignId, Client, Config, DurableMaterialRuntime, JournalError, MichiganContentPreset,
    MoneyJournalWriter, ObserverEconomyReader, Uuid,
};

fn points(owner: &mut Client, campaign: CampaignId) -> String {
    owner
        .query_one(
            "SELECT jsonb_agg(jsonb_build_array(location_key,encode(foundation_sha256,'hex'),
                 longitude::text,latitude::text) ORDER BY location_key)::text
             FROM babylon_state.economic_flow_location_v1 WHERE campaign_id=$1",
            &[campaign.as_uuid()],
        )
        .expect("read the complete campaign point identities and exact coordinates")
        .get(0)
}

pub(super) fn check(
    owner: &mut Client,
    config: &Config,
    observer: &ObserverEconomyReader,
    writer: &MoneyJournalWriter,
    campaign: CampaignId,
) {
    let expected = points(owner, campaign);
    let neighbor = CampaignId::from_uuid(Uuid::from_u128(0x73a3));
    let foundation = MichiganContentPreset::FourWeekStandard
        .create_foundation_for_campaign(&crate::test_support::catalog(), neighbor)
        .expect("second campaign has its own authored opening");
    let neighbor = DurableMaterialRuntime::create(config, neighbor, foundation)
        .expect("persist a distinct neighbor campaign")
        .campaign_id();
    for id in [campaign, neighbor] {
        assert_eq!(
            owner
                .execute(
                    "INSERT INTO babylon_state.economic_flow_location_v1
                         (campaign_id,foundation_sha256,location_key,longitude,latitude)
                     SELECT campaign_id,foundation_sha256,'county:99999',0,0
                     FROM babylon_state.material_campaign_foundation_v3 WHERE campaign_id=$1",
                    &[id.as_uuid()],
                )
                .expect("insert the same out-of-source point under each campaign's own foundation"),
            1
        );
    }
    let neighbor_before = points(owner, neighbor);
    assert_eq!(
        writer.publish(observer, campaign, 1),
        Err(JournalError::Projection),
        "an extra point alone invalidates the selected campaign's otherwise complete directory"
    );
    assert_eq!(
        owner
            .execute(
                "UPDATE babylon_state.economic_flow_location_v1 SET foundation_sha256=sha256(foundation_sha256)
                 WHERE campaign_id=$1 AND location_key=(SELECT min(location_key)
                     FROM babylon_state.economic_flow_location_v1 WHERE campaign_id=$1 AND location_key<>'county:99999')",
                &[campaign.as_uuid()],
            )
            .expect("change one real point's foundation while preserving its captured coordinates"),
        1
    );
    writer
        .rebuild(observer, campaign, 1)
        .expect("explicit rebuild restores points from the authenticated national source");
    assert_eq!(points(owner, campaign), expected);
    assert_eq!(points(owner, neighbor), neighbor_before);
}

/// Expired detail has released its point references. The old and changed county
/// longitudes compare equal as numbers, while their binary source fields differ.
pub(super) struct PointScale {
    key: String,
    original: String,
}

impl PointScale {
    pub(super) fn check_rejection(
        owner: &mut Client,
        observer: &ObserverEconomyReader,
        writer: &MoneyJournalWriter,
        campaign: CampaignId,
    ) -> Self {
        let point = Self::from_directory(owner, campaign);
        point.set(owner, campaign, true);
        assert_eq!(
            writer.publish(observer, campaign, 1),
            Err(JournalError::Projection),
            "a different source scale invalidates an otherwise complete expired period"
        );
        point.set(owner, campaign, false);
        point
    }

    fn from_directory(owner: &mut Client, campaign: CampaignId) -> Self {
        let row = owner
            .query_one(
                "SELECT location_key,longitude::text FROM babylon_state.economic_flow_location_v1
             WHERE campaign_id=$1 AND scale(longitude)>0 ORDER BY location_key LIMIT 1",
                &[campaign.as_uuid()],
            )
            .expect("a national county with fractional longitude");
        Self {
            key: row.get(0),
            original: row.get(1),
        }
    }

    pub(super) fn set(&self, owner: &mut Client, campaign: CampaignId, changed: bool) {
        let value = if changed {
            format!("{}0", self.original)
        } else {
            self.original.clone()
        };
        assert_eq!(
            owner
                .execute(
                    "UPDATE babylon_state.economic_flow_location_v1 SET longitude=$3::text::numeric
             WHERE campaign_id=$1 AND location_key=$2 AND longitude=$3::text::numeric",
                    &[campaign.as_uuid(), &self.key, &value],
                )
                .expect("preserve the numeric value and choose its exact scale"),
            1
        );
    }

    pub(super) fn require_original(&self, owner: &mut Client, campaign: CampaignId) {
        assert_eq!(owner.query_one(
            "SELECT longitude::text FROM babylon_state.economic_flow_location_v1 WHERE campaign_id=$1 AND location_key=$2",
            &[campaign.as_uuid(), &self.key],
        ).expect("read repaired point").get::<_, String>(0), self.original);
    }
}
