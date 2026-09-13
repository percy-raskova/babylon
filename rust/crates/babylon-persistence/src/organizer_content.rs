//! Captured, explicitly Designed Wayne political content and graph incidence.

use babylon_graph::stable_element::StableElementKey;
use babylon_kernel::content_digest::sha256_of;
use babylon_practice_contract::{
    initial_organizer_state, OrganizerConfig, OrganizerContribution, OrganizerParticipant,
    OrganizerPartner, OrganizerPartnerPolicy, ORGANIZER_SCHEMA_VERSION,
};

use crate::{
    identity::CampaignId,
    michigan_cohorts::MICHIGAN_COHORT_SCENARIO,
    michigan_defines::{MichiganDefinesError, OrganizerDefines},
};

const DECLARATIONS: &str =
    include_str!("../../../../content/scenarios/michigan/organizer-declarations.bscn");
pub(crate) const COLLECTIVE: &str = "wayne-organizing-collective";
pub(crate) const WORKPLACE_COMMITTEE: &str = "wayne-workplace-committee";
pub(crate) const NEIGHBORHOOD: &str = "wayne-neighborhood-contact-group";
const CONTRIBUTOR_NAMES: [&str; 3] = [
    "wayne-collective-contributors",
    "wayne-workplace-contributors",
    "wayne-neighborhood-contributors",
];

/// Actor bytes derive from the authored stable key, never graph allocation order.
pub(crate) fn actor_id(name: &str) -> Result<u64, MichiganDefinesError> {
    let key = StableElementKey::Node {
        scenario: MICHIGAN_COHORT_SCENARIO.to_owned(),
        local_name: name.to_owned(),
    };
    let bytes = key
        .canonical_bytes()
        .map_err(|_| MichiganDefinesError::Canonical)?;
    let digest = sha256_of(&bytes);
    let id = u64::from_be_bytes(
        digest[..8]
            .try_into()
            .map_err(|_| MichiganDefinesError::Canonical)?,
    );
    if id == 0 {
        return Err(MichiganDefinesError::Canonical);
    }
    Ok(id)
}
fn authority(campaign: CampaignId, actor: u64) -> [u8; 16] {
    let mut bytes = b"babylon.organizer-input-authority.v1\0".to_vec();
    bytes.extend_from_slice(campaign.canonical_bytes());
    bytes.extend_from_slice(&actor.to_be_bytes());
    let digest = sha256_of(&bytes);
    let mut result = [0; 16];
    result.copy_from_slice(&digest[..16]);
    result
}
pub(crate) fn append_declarations(source: &str) -> Result<String, MichiganDefinesError> {
    let source = source
        .strip_suffix(")\n")
        .ok_or(MichiganDefinesError::Canonical)?;
    let mut source = source
        .replace(
            "(TERRITORY ORGANIZATION SOCIAL_CLASS)",
            "(TERRITORY ORGANIZATION SOCIAL_CLASS PARTICIPANT_BODY)",
        )
        .replace("(ECONOMIC_SECTOR)", "(ECONOMIC_SECTOR ORGANIZATION_BODY)");
    source.push_str("  (defvocabulary EdgeType (CONTACT))\n");
    source.push_str(DECLARATIONS);
    source.push_str(")\n");
    Ok(source)
}
pub(crate) fn config(
    campaign: CampaignId,
    d: &OrganizerDefines,
    workplace_process_id: [u8; 32],
) -> Result<OrganizerConfig, MichiganDefinesError> {
    let actors = [
        actor_id(COLLECTIVE)?,
        actor_id(WORKPLACE_COMMITTEE)?,
        actor_id(NEIGHBORHOOD)?,
    ];
    let labels = [
        "Wayne Organizing Collective",
        "Wayne Metal-Parts Workplace Committee",
        "Wayne Neighborhood Contact Group",
    ];
    let hours = [
        d.player_hours_per_period,
        d.partner_hours_per_period,
        d.partner_hours_per_period,
    ];
    let concerns = ["Understand the workplace report while honoring the neighborhood commitment.", "Reduced modeled work threatens our practical position; actual shifts and wages are not modeled.", "Keep the existing neighborhood contact practice accountable."];
    let objections = [
        "An inquiry can use the time already promised to standing work.",
        "A report is evidence, not a promise that the workplace will recover.",
        "Replacing our routine must last only one period unless we explicitly pause it.",
    ];
    let mut participants = Vec::new();
    for index in 0..3 {
        participants.push(OrganizerParticipant {
        contributor_id: actor_id(CONTRIBUTOR_NAMES[index])?, label: format!("{} participant body", labels[index]), available_hours: hours[index],
        commitments: vec![OrganizerContribution { actor_id: actors[index], hours: hours[index] }], concern: concerns[index].to_owned(), objection: objections[index].to_owned(),
        review_condition: "Review after the resolving period using performed practice and attributed evidence.".to_owned(),
    });
    }
    participants.sort_by_key(|row| row.contributor_id);
    let partner = |index: usize| OrganizerPartner {
        actor_id: actors[index],
        authority_id: authority(campaign, actors[index]),
        label: labels[index].to_owned(),
        policy: OrganizerPartnerPolicy::Participate,
        permits_work_report: true,
        permits_maintenance_report: true,
    };
    let mut identity = b"babylon.wayne-organizer-content.v1\0".to_vec();
    identity.extend_from_slice(DECLARATIONS.as_bytes());
    identity
        .extend_from_slice(&serde_json::to_vec(d).map_err(|_| MichiganDefinesError::Canonical)?);
    let config = OrganizerConfig {
        schema_version: ORGANIZER_SCHEMA_VERSION,
        campaign_id: *campaign.canonical_bytes(),
        controlled_actor_id: actors[0],
        input_authority_id: authority(campaign, actors[0]),
        organization_label: labels[0].to_owned(),
        workplace_process_id,
        workplace_id: actor_id("business-26163-31-33")?,
        workplace_label: "Wayne metal-parts workplace".to_owned(),
        workplace_partner: partner(1),
        neighborhood_partner: partner(2),
        participants,
        inquiry_hours: d.inquiry_hours,
        contact_hours: d.contact_hours,
        partner_response_hours: d.partner_response_hours,
        initial_agreement_through_period: d.initial_agreement_through_period,
        contact_renewal_periods: d.contact_renewal_periods,
        content_digest: sha256_of(&identity),
        initial_observations: Vec::new(),
    };
    initial_organizer_state(&config).map_err(|_| MichiganDefinesError::Canonical)?;
    Ok(config)
}

#[cfg(test)]
mod tests {
    use super::*;
    use babylon_practice_contract::organizer_view;
    #[test]
    fn authored_organizer_identity_captures_explicit_participant_incidence_and_costs() {
        let d = crate::michigan_defines::MichiganDefines::parse(include_str!(
            "../../../../content/scenarios/michigan/defines.toml"
        ))
        .unwrap();
        let campaign = CampaignId::from_uuid(uuid::Uuid::from_u128(26163));
        let config = config(campaign, &d.organizer, [7; 32]).unwrap();
        let state = initial_organizer_state(&config).unwrap();
        let view = organizer_view(&config, &state, config.controlled_actor_id).unwrap();
        assert_eq!(
            (view.available_hours, view.inquiry_hours, view.contact_hours),
            (16, 12, 8)
        );
        assert_eq!(
            view.positions
                .iter()
                .map(|row| row.promised_hours)
                .sum::<u64>(),
            16
        );
        assert_eq!(config.participants.len(), 3);
        assert_eq!(
            config
                .participants
                .iter()
                .map(|row| row.available_hours)
                .sum::<u64>(),
            32
        );
        let catalog = crate::test_support::catalog();
        let source = append_declarations(catalog.graph_scenario_source()).unwrap();
        assert_eq!(source.matches("HyperedgeType/ORGANIZATION_BODY").count(), 3);
        assert_eq!(source.matches("NodeType/PARTICIPANT_BODY").count(), 3);
        assert_eq!(source.matches("EdgeType/CONTACT").count(), 2);
        assert!(!source.contains("solidarity"));
        assert_ne!(
            actor_id(COLLECTIVE).unwrap(),
            actor_id(WORKPLACE_COMMITTEE).unwrap()
        );
        let path = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
            .join("../../../content/scenarios/michigan/defines.toml");
        let authored = crate::michigan_material::MichiganMaterialCatalog::load_for_preset(
            &path,
            crate::michigan_material::MichiganDeliveryPreset::OrganizeInWayne,
        )
        .unwrap();
        let foundation = crate::michigan_content::MichiganContentPreset::OrganizeInWayne
            .create_foundation_for_campaign(&authored, campaign)
            .unwrap();
        let register = foundation.initial_register();
        assert_eq!(
            register.organizer_config().unwrap().campaign_id,
            *campaign.canonical_bytes()
        );
        assert_eq!(register.organizer_state().unwrap().period, 0);
        assert_eq!(
            register.organizer_config().unwrap().workplace_id,
            actor_id("business-26163-31-33").unwrap()
        );
    }
}
