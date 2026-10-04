//! One source-derived national organizer producer; no fixed-time fallback.
use crate::{
    economic_catalog::{
        EconomicCatalogError, EconomicCatalogInput, EconomicOpening, SourceArtifactKind,
    },
    national_economy::{NationalAidCapture, NationalGamePolicy, NATIONAL_SCENARIO_ID},
};
use babylon_graph::stable_element::StableElementKey;
use babylon_kernel::content_digest::sha256_of;
use babylon_practice_contract::{
    initial_organizer_state, OrganizerAidBinding, OrganizerAidKind, OrganizerConfig,
    OrganizerContribution, OrganizerHouseholdBinding, OrganizerParticipant, OrganizerPartner,
    OrganizerTimeBindingMode, ORGANIZER_SCHEMA_VERSION,
};
type Result<T> = std::result::Result<T, EconomicCatalogError>;
/// Digest of the exact current source frame with organizer field explicitly absent.
/// The final catalog digest additionally authenticates the complete organizer config.
#[derive(Clone, Copy)]
pub(crate) struct NationalOrganizerSourceBasis(pub(crate) [u8; 32]);
fn key(name: &str) -> StableElementKey {
    StableElementKey::Node {
        scenario: NATIONAL_SCENARIO_ID.into(),
        local_name: name.into(),
    }
}
fn actor(key: &StableElementKey) -> Result<u64> {
    let digest = sha256_of(
        &key.canonical_bytes()
            .map_err(|_| EconomicCatalogError::Identity)?,
    );
    let id = u64::from_be_bytes(
        digest[..8]
            .try_into()
            .map_err(|_| EconomicCatalogError::Identity)?,
    );
    if id == 0 {
        return Err(EconomicCatalogError::Identity);
    }
    Ok(id)
}
fn authority(campaign: [u8; 16], actor: u64) -> [u8; 16] {
    let mut bytes = b"babylon.organizer-input-authority.v1\0".to_vec();
    bytes.extend_from_slice(&campaign);
    bytes.extend_from_slice(&actor.to_be_bytes());
    let mut result = [0; 16];
    result.copy_from_slice(&sha256_of(&bytes)[..16]);
    result
}
pub(crate) fn assemble(
    campaign: [u8; 16],
    source_basis: NationalOrganizerSourceBasis,
    opening: &EconomicOpening,
    aid: &NationalAidCapture,
    input: &EconomicCatalogInput,
) -> Result<OrganizerConfig> {
    if campaign == [0; 16] || aid.children.len() != 3 || aid.mandates.len() != 2 {
        return Err(EconomicCatalogError::Identity);
    }
    let source = input
        .sources
        .iter()
        .find(|s| s.kind() == SourceArtifactKind::NationalGamePolicy)
        .ok_or(EconomicCatalogError::Source(
            SourceArtifactKind::NationalGamePolicy,
        ))?;
    if source.digest() != aid.source_hash {
        return Err(EconomicCatalogError::Digest);
    }
    let policy = NationalGamePolicy::from_captured_bytes(source.bytes())
        .map_err(|_| EconomicCatalogError::Source(SourceArtifactKind::NationalGamePolicy))?;
    let donor = &aid.children[0];
    let employed = opening
        .employment
        .iter()
        .filter(|e| e.payee == donor.principal)
        .collect::<Vec<_>>();
    if employed.len() != 1 {
        return Err(EconomicCatalogError::Identity);
    }
    let site = opening
        .sites
        .iter()
        .find(|s| s.site_id == employed[0].site_id)
        .ok_or(EconomicCatalogError::Identity)?;
    if site.processes.len() != 1 {
        return Err(EconomicCatalogError::Identity);
    }
    let workplace_actor = actor(&key("wayne-workplace-committee"))?;
    let neighborhood_actor = actor(&key("wayne-neighborhood-contact-group"))?;
    let ordinary_partner = |actor_id, label: String, partner_policy| OrganizerPartner {
        actor_id,
        authority_id: authority(campaign, actor_id),
        label,
        policy: partner_policy,
        permits_work_report: true,
        permits_maintenance_report: false,
    };
    let d = &policy.organizer;
    let workplace_partner = ordinary_partner(
        workplace_actor,
        d.workplace_partner_label.clone(),
        d.workplace_policy,
    );
    let neighborhood_partner = ordinary_partner(
        neighborhood_actor,
        d.neighborhood_partner_label.clone(),
        d.neighborhood_policy,
    );
    let participants = participants(aid, &policy, workplace_actor, neighborhood_actor);
    let mut bindings = aid
        .children
        .iter()
        .map(|child| OrganizerHouseholdBinding {
            contributor_id: child.contributor,
            principal_id: child.principal.as_bytes(),
        })
        .collect::<Vec<_>>();
    bindings.sort_unstable_by_key(|b| b.contributor_id);
    let aid_bindings = aid_bindings(campaign, aid, &policy)?;
    let collection = collection_mandate(campaign, source.digest(), aid, &policy)?;
    let config = OrganizerConfig {
        schema_version: ORGANIZER_SCHEMA_VERSION,
        campaign_id: campaign,
        controlled_actor_id: donor.actor,
        input_authority_id: authority(campaign, donor.actor),
        organization_label: d.organization_label.clone(),
        workplace_id: actor(&site.subject)?,
        workplace_process_id: site.processes[0].process_id.as_bytes(),
        workplace_label: site.label.clone(),
        workplace_partner,
        neighborhood_partner,
        participants,
        time_binding: OrganizerTimeBindingMode::Household { bindings },
        aid_bindings,
        collection: Some(collection),
        inquiry_hours: d.inquiry_hours,
        contact_hours: d.contact_hours,
        partner_response_hours: d.partner_response_hours,
        initial_agreement_through_period: d.initial_agreement_through_period,
        contact_renewal_periods: d.contact_renewal_periods,
        content_digest: source_basis.0,
        initial_observations: vec![],
    };
    initial_organizer_state(&config).map_err(|_| EconomicCatalogError::Identity)?;
    Ok(config)
}
fn collection_mandate(
    campaign: [u8; 16],
    source_hash: [u8; 32],
    aid: &NationalAidCapture,
    policy: &NationalGamePolicy,
) -> Result<babylon_practice_contract::OrganizerCollectionMandate> {
    let donor = &aid.children[0];
    let d = &policy.organizer;
    let first = aid.mandates.first().ok_or(EconomicCatalogError::Identity)?;
    let babylon_material_circuit::AccountId::Organization(account) = first.payer else {
        return Err(EconomicCatalogError::Identity);
    };
    if aid.mandates.iter().any(|m| {
        m.payer != first.payer
            || m.labor_unit_id != first.labor_unit_id
            || m.donor_actor != donor.actor
            || m.donor != donor.principal
    }) {
        return Err(EconomicCatalogError::Identity);
    }
    let mut collection_identity = b"babylon.organizer-collection-mandate.v1\0".to_vec();
    collection_identity.extend_from_slice(&campaign);
    collection_identity.extend_from_slice(&source_hash);
    collection_identity.extend_from_slice(&donor.actor.to_be_bytes());
    collection_identity.extend_from_slice(&donor.principal.as_bytes());
    collection_identity.extend_from_slice(&account.as_bytes());
    Ok(babylon_practice_contract::OrganizerCollectionMandate {
        mandate_id: sha256_of(&collection_identity),
        source_hash,
        actor_id: donor.actor,
        contributor_id: donor.contributor,
        household_principal_id: donor.principal.as_bytes(),
        organization_account_id: account.as_bytes(),
        social_class_target: sha256_of(
            &donor
                .class_subject
                .canonical_bytes()
                .map_err(|_| EconomicCatalogError::Identity)?,
        ),
        labor_unit_id: first.labor_unit_id.as_bytes(),
        cash_consent: d.collection_cash_consent,
        maximum_cash_micros: d.collection_maximum_cash_micros,
        protected_cash_floor_micros: d.collection_protected_cash_floor_micros,
        collection_hours: d.collection_hours,
    })
}
fn aid_bindings(
    campaign: [u8; 16],
    aid: &NationalAidCapture,
    policy: &NationalGamePolicy,
) -> Result<Vec<OrganizerAidBinding>> {
    let donor = &aid.children[0];
    let d = &policy.organizer;
    let ordinary_partner = |actor_id, label: String, partner_policy| OrganizerPartner {
        actor_id,
        authority_id: authority(campaign, actor_id),
        label,
        policy: partner_policy,
        permits_work_report: true,
        permits_maintenance_report: false,
    };
    aid.mandates
        .iter()
        .enumerate()
        .map(|(i, mandate)| {
            let child = &aid.children[i + 1];
            if mandate.donor != donor.principal
                || mandate.recipient != child.principal
                || mandate.recipient_actor != child.actor
            {
                return Err(EconomicCatalogError::Identity);
            }
            let local = i == 0;
            Ok(OrganizerAidBinding {
                kind: if local {
                    OrganizerAidKind::Local
                } else {
                    OrganizerAidKind::Remote
                },
                mandate_id: mandate.id,
                source_hash: mandate.source_hash,
                donor_contributor_id: donor.contributor,
                recipient_contributor_id: child.contributor,
                donor_principal_id: donor.principal.as_bytes(),
                recipient_principal_id: child.principal.as_bytes(),
                social_class_target: sha256_of(
                    &child
                        .class_subject
                        .canonical_bytes()
                        .map_err(|_| EconomicCatalogError::Identity)?,
                ),
                receiving_consent: if local {
                    d.local_receiving_consent
                } else {
                    d.remote_receiving_consent
                },
                partner: ordinary_partner(
                    child.actor,
                    if local {
                        d.local_partner_label.clone()
                    } else {
                        d.remote_partner_label.clone()
                    },
                    if local {
                        d.local_policy
                    } else {
                        d.remote_policy
                    },
                ),
                coordination_hours: d.aid_coordination_hours,
            })
        })
        .collect::<Result<Vec<_>>>()
}

fn participants(
    aid: &NationalAidCapture,
    policy: &NationalGamePolicy,
    workplace: u64,
    neighborhood: u64,
) -> Vec<OrganizerParticipant> {
    let d = &policy.organizer;
    let mut rows=aid.children.iter().enumerate().map(|(i,child)|{
        let mut actors=vec![child.actor];
        if i==0{actors.push(workplace)}else if i==1{actors.push(neighborhood)}
        actors.sort_unstable();
        OrganizerParticipant{contributor_id:child.contributor,label:format!("{} participant body",match i{0=>&d.organization_label,1=>&d.local_partner_label,_=>&d.remote_partner_label}),available_hours:d.contributor_hours_cap,commitments:actors.into_iter().map(|actor_id|OrganizerContribution{actor_id,hours:d.contact_hours}).collect(),concern:"Preserve household needs while deciding whether to help another household.".into(),objection:"A gift does not authorize political participation or promise a response.".into(),review_condition:"Review actual delivery, consumption and independently accepted practice after the period closes.".into()}
    }).collect::<Vec<_>>();
    rows.sort_unstable_by_key(|r| r.contributor_id);
    rows
}
