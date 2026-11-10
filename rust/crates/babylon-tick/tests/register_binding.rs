//! Optional components preserve material identity and full admission behavior.

#[allow(dead_code, reason = "reuse the existing typed material fixture")]
#[path = "support/organizer_aid_fixture.rs"]
mod organizer_aid_fixture;

use babylon_graph::memory::MemoryGraph;
use babylon_graph::stable_element::{StableElementKey, StableElementResolver};
use babylon_graph::substrate::GraphSubstrate;
use babylon_kernel::content_digest;
use babylon_material_circuit::{
    AccountId, CashAccount, CircuitAccounting, CommodityDefinition, CommodityKind, GoodId,
    HistoricalCostBook, InstitutionLocation, MaterialCatalog, MaterialCircuitError, MonetaryBook,
    OrganizationAccountId, PublicAccountId, PublicAllocation, PublicBudget,
    PublicTransferTreatment, UnitId,
};
use babylon_practice_contract::{
    CityPdCase, CityPdCaseSource, CityPdCaseStatus, CityPdConfig, OrganizerConfig,
    OrganizerPeriodJournal, OrganizerState, PublicVenueHistory, PublicVenuePolicy,
};
use babylon_tick::material_world;
use babylon_tick::material_world::{
    CityPdRegister, CityPdRegisterError, MaterialWorldError, MaterialWorldRegister,
};
use std::collections::HashMap;

struct BindingFixture {
    catalog: MaterialCatalog,
    bare: MaterialWorldRegister,
    organizer: OrganizerConfig,
    organizer_state: OrganizerState,
    venue: PublicVenueHistory,
    city_pd: CityPdRegister,
    resolver: StableElementResolver,
}

impl BindingFixture {
    fn organized(&self, catalog: &MaterialCatalog) -> MaterialWorldRegister {
        self.bare
            .clone()
            .with_organizer(
                catalog,
                self.organizer.clone(),
                self.organizer_state.clone(),
                OrganizerPeriodJournal::empty(),
            )
            .expect("the captured organizer binds to the admitted material")
    }

    fn public(&self, catalog: &MaterialCatalog) -> MaterialWorldRegister {
        self.organized(catalog)
            .with_public_venue(catalog, self.venue.clone(), None)
            .expect("the public notice binds to the organizer")
    }

    fn compatible_foreign_catalog(&self) -> MaterialCatalog {
        let mut definition = self.catalog.clone().into_definition();
        // An unused commodity changes catalog identity without changing any
        // relation required by the existing state or its bound components.
        definition.commodities.push(CommodityDefinition {
            good_id: GoodId::from_bytes([254; 32]),
            unit_id: UnitId::from_bytes([254; 32]),
            kind: CommodityKind::Storable { grams_per_unit: 1 },
        });
        let foreign = MaterialCatalog::try_new(definition).expect("valid independent catalog");
        assert_ne!(foreign.catalog_digest(), self.catalog.catalog_digest());
        let readmitted = MaterialWorldRegister::try_new(&foreign, 0, self.bare.state().clone())
            .expect("the existing material independently admits under the foreign catalog");
        assert_eq!(readmitted.state(), self.bare.state());
        assert_eq!(readmitted.catalog_digest(), foreign.catalog_digest());
        foreign
    }
}

fn graph_resolver(scenario: &str) -> StableElementResolver {
    let mut graph = MemoryGraph::new();
    let mut names = HashMap::new();
    for name in ["agency", "workplace"] {
        let node = graph.add_node("actor").expect("real graph node");
        names.insert(node, name.to_owned());
    }
    StableElementResolver::seal(&graph, scenario, &names, &HashMap::new())
        .expect("sealed semantic identities")
}

fn binding(resolver: &StableElementResolver, name: &str) -> (u64, StableElementKey) {
    let key = resolver
        .node_key(
            resolver
                .node_handle_by_local_name(name)
                .expect("named node"),
        )
        .expect("sealed node key")
        .clone();
    let digest = content_digest::sha256_of(&key.canonical_bytes().expect("canonical key"));
    (
        u64::from_be_bytes(digest[..8].try_into().expect("eight digest bytes")),
        key,
    )
}

fn admitted_opening() -> (MaterialCatalog, MaterialWorldRegister) {
    let organizer_aid_fixture::Materials { catalog, mut state } =
        organizer_aid_fixture::aid_opening(false);
    let CircuitAccounting::Monetary(economy) = &mut state.accounting else {
        panic!("the existing fixture supplies monetary accounting");
    };
    let public = PublicAccountId::from_bytes([240; 32]);
    let agency = OrganizationAccountId::from_bytes([241; 32]);
    let mut snapshot = economy.book.snapshot();
    for account in [AccountId::Public(public), AccountId::Organization(agency)] {
        snapshot.accounts.push(CashAccount {
            id: account,
            cash: organizer_aid_fixture::money(0),
        });
        economy.financial.locations.push(InstitutionLocation {
            account,
            location: "county:26163".parse().expect("captured county"),
        });
    }
    economy.book = MonetaryBook::from_snapshot(snapshot).expect("zero balances conserve cash");
    economy.costs = HistoricalCostBook::open(
        &economy.book,
        economy.costs.snapshot().stocks,
        vec![],
        vec![],
        vec![],
    )
    .expect("the extended book has an explicit opening cost ledger");
    economy.financial.public_budgets.push(PublicBudget {
        public_account: public,
        period_cap: organizer_aid_fixture::money(10),
        cash_floor: organizer_aid_fixture::money(0),
    });
    economy.financial.public_allocations.push(PublicAllocation {
        public_account: public,
        recipient: AccountId::Organization(agency),
        treatment: PublicTransferTreatment::AgencyAppropriation,
        priority: 0,
        amount_per_period: organizer_aid_fixture::money(10),
    });
    let catalog = MaterialCatalog::try_new(catalog).expect("captured material definitions");
    let bare = MaterialWorldRegister::try_new(&catalog, 0, state).expect("admitted opening core");
    (catalog, bare)
}

fn fixture() -> BindingFixture {
    let (catalog, bare) = admitted_opening();
    let resolver = graph_resolver("register/binding");
    let agency = binding(&resolver, "agency");
    let workplace = binding(&resolver, "workplace");
    let mut organizer = organizer_aid_fixture::config();
    organizer.workplace_id = workplace.0;
    let organizer_state = babylon_practice_contract::initial_organizer_state(&organizer)
        .expect("captured organizer opening");
    let policy = PublicVenuePolicy::new(
        organizer.campaign_id,
        organizer.workplace_id,
        organizer.controlled_actor_id,
        organizer.workplace_partner.actor_id,
        organizer.workplace_partner.authority_id,
        agency.0,
        organizer.controlled_actor_id,
        organizer.content_digest,
        [9; 32],
    )
    .expect("captured independent public desk");
    let notice = babylon_practice_contract::initial_public_venue_notice(&policy)
        .expect("actual initial public record");
    let mut case = CityPdCase {
        case_id: [0; 32],
        actor_id: agency.0,
        subject_id: workplace.0,
        county: *b"26163",
        public_venue_id: notice.venue_id,
        source_id: notice.source_id,
        source_kind: CityPdCaseSource::CapturedPublicRecord,
        source_receipt_id: None,
        case_source_witness_id: None,
        observed_period: 0,
        acquired_period: 0,
        status: CityPdCaseStatus::Open,
    };
    case.case_id = babylon_practice_contract::city_pd_case_id(&case).expect("captured case ID");
    let config = CityPdConfig {
        schema_version: 1,
        campaign_id: organizer.campaign_id,
        actor_id: agency.0,
        authority_id: [2; 16],
        county: *b"26163",
        public_account_id: [240; 32],
        agency_account_id: [241; 32],
        investigator_household_account_id: organizer_aid_fixture::household().as_bytes(),
        investigator_entitlement_id: [6; 32],
        labor_unit_id: [2; 32],
        visit_hours: 2,
        hourly_wage_micros: 3,
        visit_cost_micros: 6,
        appropriation_micros: 10,
        appropriation_priority: 0,
        content_digest: [8; 32],
        policy_source_digest: [9; 32],
    };
    let city_pd = CityPdRegister::try_initial(
        config,
        case,
        vec![agency, workplace],
        &catalog,
        bare.state(),
        &resolver,
    )
    .expect("actual resolver-bound zero-cash opening decision");
    BindingFixture {
        catalog,
        bare,
        organizer,
        organizer_state,
        venue: PublicVenueHistory {
            policy,
            records: vec![notice],
        },
        city_pd,
        resolver,
    }
}

fn assert_round_trip(
    fixture: &BindingFixture,
    catalog: &MaterialCatalog,
    register: &MaterialWorldRegister,
) {
    assert_eq!(register.state(), fixture.bare.state());
    assert_eq!(register.completed_tick(), fixture.bare.completed_tick());
    assert_eq!(register.catalog_digest(), catalog.catalog_digest());
    assert_eq!(register.organizer_config(), Some(&fixture.organizer));
    assert_eq!(register.organizer_state(), Some(&fixture.organizer_state));
    assert_eq!(
        register.organizer_journal(),
        Some(&OrganizerPeriodJournal::empty())
    );
    let reopened = MaterialWorldRegister::decode_external_with_resolver(
        catalog,
        register.canonical_bytes().to_vec(),
        &fixture.resolver,
    )
    .expect("bound bytes satisfy full external canonical admission");
    assert_eq!(&reopened, register);
}

#[test]
fn lawful_bindings_preserve_material_identity_and_canonical_round_trip() {
    let fixture = fixture();
    let organized = fixture.organized(&fixture.catalog);
    let public = fixture.public(&fixture.catalog);
    let complete = public
        .clone()
        .with_city_pd(&fixture.catalog, fixture.city_pd.clone(), &fixture.resolver)
        .expect("the real private decision binds to its public source and graph");
    for register in [&organized, &public, &complete] {
        assert_round_trip(&fixture, &fixture.catalog, register);
    }
    assert_eq!(organized.public_venue(), None);
    assert_eq!(public.public_venue(), Some(&fixture.venue));
    assert_eq!(complete.public_venue(), Some(&fixture.venue));
    assert_eq!(complete.city_pd(), Some(&fixture.city_pd));
    assert_ne!(organized.digest(), fixture.bare.digest());
    assert_ne!(public.digest(), organized.digest());
    assert_ne!(complete.digest(), public.digest());
}

#[test]
fn compatible_foreign_catalog_bindings_match_full_material_readmission() {
    let fixture = fixture();
    let foreign = fixture.compatible_foreign_catalog();
    let admitted = MaterialWorldRegister::try_new(&foreign, 0, fixture.bare.state().clone())
        .expect("full new-state admission remains supported");
    let organized = fixture
        .bare
        .clone()
        .with_organizer(
            &foreign,
            fixture.organizer.clone(),
            fixture.organizer_state.clone(),
            OrganizerPeriodJournal::empty(),
        )
        .expect("foreign compatible organizer binding preserves full readmission");
    let public = fixture
        .organized(&fixture.catalog)
        .with_public_venue(&foreign, fixture.venue.clone(), None)
        .expect("foreign compatible venue binding preserves full readmission");
    let complete = fixture
        .public(&fixture.catalog)
        .with_city_pd(&foreign, fixture.city_pd.clone(), &fixture.resolver)
        .expect("foreign compatible opponent binding preserves full readmission");
    let expected_organizer = admitted
        .with_organizer(
            &foreign,
            fixture.organizer.clone(),
            fixture.organizer_state.clone(),
            OrganizerPeriodJournal::empty(),
        )
        .expect("full admission with organizer");
    assert_eq!(organized, expected_organizer);
    let expected_public = expected_organizer
        .with_public_venue(&foreign, fixture.venue.clone(), None)
        .expect("full admission with venue");
    assert_eq!(public, expected_public);
    let expected_complete = expected_public
        .with_city_pd(&foreign, fixture.city_pd.clone(), &fixture.resolver)
        .expect("full admission with opponent");
    assert_eq!(complete, expected_complete);
    for register in [&organized, &public, &complete] {
        assert_round_trip(&fixture, &foreign, register);
        assert_eq!(
            MaterialWorldRegister::decode_external_with_resolver(
                &fixture.catalog,
                register.canonical_bytes().to_vec(),
                &fixture.resolver,
            ),
            Err(MaterialWorldError::Circuit(
                MaterialCircuitError::WireDomain
            )),
            "readmission must actually capture the foreign catalog identity",
        );
    }
}

#[test]
fn bindings_retain_component_resolver_and_period_refusals() {
    let fixture = fixture();
    let mut invalid_organizer = fixture.organizer_state.clone();
    invalid_organizer.standing.authorized = false;
    invalid_organizer.standing.paused_reason = None;
    assert_eq!(
        fixture.bare.clone().with_organizer(
            &fixture.catalog,
            fixture.organizer.clone(),
            invalid_organizer,
            OrganizerPeriodJournal::empty(),
        ),
        Err(MaterialWorldError::Organizer(
            babylon_practice_contract::OrganizerError::InvalidState
        )),
    );
    let mut invalid_venue = fixture.venue.clone();
    invalid_venue.records.clear();
    assert_eq!(
        fixture.organized(&fixture.catalog).with_public_venue(
            &fixture.catalog,
            invalid_venue,
            None
        ),
        Err(MaterialWorldError::Wire),
    );
    let foreign_resolver = graph_resolver("register/foreign");
    assert_eq!(
        fixture.public(&fixture.catalog).with_city_pd(
            &fixture.catalog,
            fixture.city_pd.clone(),
            &foreign_resolver
        ),
        Err(MaterialWorldError::CityPd(CityPdRegisterError::Decision)),
    );
    assert_eq!(
        MaterialWorldRegister::try_new(&fixture.catalog, 1, fixture.bare.state().clone()),
        Err(MaterialWorldError::PeriodMismatch),
    );
}

#[test]
fn incompatible_foreign_catalog_bindings_preserve_full_admission_error() {
    let fixture = fixture();
    let mut definition = fixture.catalog.clone().into_definition();
    definition.household_needs.clear();
    let foreign = MaterialCatalog::try_new(definition).expect("valid catalog with different needs");
    let expected = MaterialWorldRegister::try_new(&foreign, 0, fixture.bare.state().clone())
        .expect_err("existing household stocks and purchase policies need their captured needs");
    assert!(matches!(expected, MaterialWorldError::Circuit(_)));
    assert_eq!(
        fixture.bare.clone().with_organizer(
            &foreign,
            fixture.organizer.clone(),
            fixture.organizer_state.clone(),
            OrganizerPeriodJournal::empty(),
        ),
        Err(expected),
    );
    assert_eq!(
        fixture.organized(&fixture.catalog).with_public_venue(
            &foreign,
            fixture.venue.clone(),
            None
        ),
        Err(expected),
    );
    assert_eq!(
        fixture.public(&fixture.catalog).with_city_pd(
            &foreign,
            fixture.city_pd.clone(),
            &fixture.resolver
        ),
        Err(expected),
    );
}

const REGISTER_HEADER: usize = b"babylon.material-world-register.v7\0".len() + 12;

fn register_sections(register: &MaterialWorldRegister) -> [&[u8]; 3] {
    let mut remaining = &register.canonical_bytes()[REGISTER_HEADER..];
    std::array::from_fn(|_| {
        let count = usize::try_from(u64::from_be_bytes(
            remaining[..8].try_into().expect("section length"),
        ))
        .expect("fixture section fits memory");
        let section = &remaining[8..8 + count];
        remaining = &remaining[8 + count..];
        section
    })
}

fn purpose_frame(register: &MaterialWorldRegister, tick: u64, sections: [&[u8]; 3]) -> Vec<u8> {
    let mut bytes = register.canonical_bytes()[..REGISTER_HEADER].to_vec();
    bytes[REGISTER_HEADER - 8..].copy_from_slice(&tick.to_be_bytes());
    for section in sections {
        bytes.extend_from_slice(
            &u64::try_from(section.len())
                .expect("fixture length")
                .to_be_bytes(),
        );
        bytes.extend_from_slice(section);
    }
    bytes
}

#[test]
fn historical_purpose_decode_preserves_complete_material_and_organizer_evidence() {
    let fixture = fixture();
    let organized = fixture.organized(&fixture.catalog);
    let public = fixture.public(&fixture.catalog);
    let complete = public
        .clone()
        .with_city_pd(&fixture.catalog, fixture.city_pd.clone(), &fixture.resolver)
        .expect("captured opponent binding");
    for register in [&fixture.bare, &organized, &public, &complete] {
        let decoded = material_world::decode_material_organizer_evidence(
            &fixture.catalog,
            register.canonical_bytes(),
        )
        .expect("historical purpose admits original complete bytes without a private resolver");
        assert_eq!(decoded.completed_tick, register.completed_tick());
        assert_eq!(&decoded.material, register.state());
        assert_eq!(
            decoded.organizer.as_ref().map(|value| &value.0),
            register.organizer_config()
        );
        assert_eq!(
            decoded.organizer.as_ref().map(|value| &value.1),
            register.organizer_state()
        );
        assert_eq!(
            decoded.organizer.as_ref().map(|value| &value.2),
            register.organizer_journal()
        );
        assert_eq!(decoded.public_venue.as_ref(), register.public_venue());
        assert_eq!(
            babylon_material_circuit::encode_material_circuit_state(
                &fixture.catalog,
                &decoded.material
            )
            .expect("admitted material retains exact canonical bytes"),
            register_sections(register)[0],
        );
    }
}

#[test]
fn historical_purpose_decode_preserves_refusals_and_error_precedence() {
    let fixture = fixture();
    let register = fixture.public(&fixture.catalog);
    let [state, organizer, private] = register_sections(&register);
    let foreign = fixture.compatible_foreign_catalog();
    assert_eq!(
        material_world::decode_material_organizer_evidence(&foreign, register.canonical_bytes()),
        Err(MaterialWorldError::Circuit(
            MaterialCircuitError::WireDomain
        )),
    );
    // Outer/private framing precedes material, material precedes period, and
    // period precedes organizer parsing even when several inputs are malformed.
    let mut trailing = register.canonical_bytes().to_vec();
    trailing.push(0);
    for bytes in [
        register.canonical_bytes()[..REGISTER_HEADER - 1].to_vec(),
        trailing,
        purpose_frame(&register, 1, [&[], &[2], &[2]]),
    ] {
        assert_eq!(
            material_world::decode_material_organizer_evidence(&fixture.catalog, &bytes),
            Err(MaterialWorldError::Wire)
        );
    }
    let mut trailing_state = state.to_vec();
    trailing_state.push(0);
    let mut version = state.to_vec();
    let schema = babylon_material_circuit::MATERIAL_CIRCUIT_STATE_DOMAIN_BYTES.len() + 1;
    version[schema..schema + 2].copy_from_slice(&u16::MAX.to_be_bytes());
    for (wire, expected) in [
        (&[][..], MaterialCircuitError::WireTruncated),
        (
            &state[..state.len() - 1],
            MaterialCircuitError::WireTruncated,
        ),
        (
            trailing_state.as_slice(),
            MaterialCircuitError::WireTrailing,
        ),
        (version.as_slice(), MaterialCircuitError::WireVersion),
    ] {
        let bytes = purpose_frame(&register, 1, [wire, &[2], private]);
        assert_eq!(
            material_world::decode_material_organizer_evidence(&fixture.catalog, &bytes),
            Err(MaterialWorldError::Circuit(expected))
        );
    }
    for tick in [1, u64::MAX] {
        let bytes = purpose_frame(&register, tick, [state, &[2], private]);
        assert_eq!(
            material_world::decode_material_organizer_evidence(&fixture.catalog, &bytes),
            Err(MaterialWorldError::PeriodMismatch)
        );
    }
    let bytes = purpose_frame(&register, 0, [state, &[2], private]);
    assert_eq!(
        material_world::decode_material_organizer_evidence(&fixture.catalog, &bytes),
        Err(MaterialWorldError::Wire)
    );
    let mut invalid_version = register.canonical_bytes().to_vec();
    invalid_version[REGISTER_HEADER - 12..REGISTER_HEADER - 8]
        .copy_from_slice(&u32::MAX.to_be_bytes());
    assert_eq!(
        material_world::decode_material_organizer_evidence(&fixture.catalog, &invalid_version),
        Err(MaterialWorldError::Wire)
    );
    // Opaque private contents remain outside this purpose decoder's authority.
    let opaque = purpose_frame(&register, 0, [state, organizer, &[1, 255]]);
    assert_eq!(
        material_world::decode_material_organizer_evidence(&fixture.catalog, &opaque),
        material_world::decode_material_organizer_evidence(
            &fixture.catalog,
            register.canonical_bytes()
        ),
    );
    assert!(MaterialWorldRegister::decode_external_with_resolver(
        &fixture.catalog,
        opaque,
        &fixture.resolver
    )
    .is_err());
}

#[test]
fn historical_purpose_decode_rejects_noncanonical_material_before_organizer() {
    let fixture = fixture();
    let register = fixture.organized(&fixture.catalog);
    let [state, _, private] = register_sections(&register);
    let mut inventory = Vec::new();
    for row in &register.state().inventory {
        inventory.extend_from_slice(&row.site_id.as_bytes());
        inventory.extend_from_slice(&row.good_id.as_bytes());
        inventory.extend_from_slice(&row.unit_id.as_bytes());
        inventory.extend_from_slice(&row.quantity.to_be_bytes());
    }
    let matches: Vec<usize> = state
        .windows(inventory.len())
        .enumerate()
        .filter_map(|(index, bytes)| (bytes == inventory).then_some(index))
        .collect();
    assert_eq!(
        matches.len(),
        1,
        "the actual inventory rows identify one wire region"
    );
    let mut noncanonical = state.to_vec();
    let row_length = 32 * 3 + 8;
    let offset = matches[0];
    for index in 0..row_length {
        noncanonical.swap(offset + index, offset + row_length + index);
    }
    let bytes = purpose_frame(&register, 1, [&noncanonical, &[2], private]);
    assert_eq!(
        material_world::decode_material_organizer_evidence(&fixture.catalog, &bytes),
        Err(MaterialWorldError::Circuit(
            MaterialCircuitError::WireNoncanonical
        )),
    );
}

#[test]
fn historical_purpose_decode_retains_organizer_binding_refusal() {
    let fixture = fixture();
    let register = fixture.organized(&fixture.catalog);
    let [material, _, private] = register_sections(&register);
    let mut unbound = fixture.organizer_state.clone();
    unbound.period = 1;
    let mut organizer = vec![1];
    for section in [
        babylon_practice_contract::encode_organizer_config(&fixture.organizer)
            .expect("valid captured config"),
        babylon_practice_contract::encode_organizer_state(&unbound)
            .expect("independently valid state with a different period"),
        babylon_practice_contract::encode_organizer_journal(
            &fixture.organizer,
            &OrganizerPeriodJournal::empty(),
        )
        .expect("independently valid opening journal"),
        vec![0],
    ] {
        organizer.extend_from_slice(
            &u64::try_from(section.len())
                .expect("fixture length")
                .to_be_bytes(),
        );
        organizer.extend_from_slice(&section);
    }
    let bytes = purpose_frame(&register, 0, [material, &organizer, private]);
    assert_eq!(
        material_world::decode_material_organizer_evidence(&fixture.catalog, &bytes),
        Err(MaterialWorldError::Organizer(
            babylon_practice_contract::OrganizerError::InvalidState,
        )),
    );
}
