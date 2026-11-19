//! Builders and short names for the County Review kernel tests.
use babylon_practice_contract::{
    Band, CountyPeriodFacts, CountyReviewConfig, CountyReviewCrew, CountyReviewGroup,
    CrewPeriodFacts, GroupKind, GroupPeriodFacts, PayMode, PlacedRow, PositionKey, Roster,
    RosterGroup, RosterRow, COUNTY_REVIEW_SCHEMA_VERSION,
};

pub const T1: Band = Band::Top1;
pub const N9: Band = Band::Next9;
pub const N40: Band = Band::Next40;
pub const B50: Band = Band::Bottom50;

/// `(group, crew, at_work, seeking, units)` and the households there.
pub type Placed = Vec<((u32, Option<u32>, u16, u16, u16), u64)>;
/// `(group, band, crew, at_work, seeking, units)`, the households and the reached.
pub type RowTuple = ((u32, Band, Option<u32>, u16, u16, u16), u64, u64);

/// People changes of one crew in one period.
#[derive(Clone, Copy, Default)]
pub struct Changes {
    pub left_at_work: u64,
    pub left_seeking: u64,
    pub hires: u64,
    pub separations: u64,
}

/// A configuration from `(households, roll units, has ownership income)` for each group and the
/// group of each crew.
pub fn config(groups: &[(u64, u64, bool)], crews: &[u32]) -> CountyReviewConfig {
    CountyReviewConfig {
        schema_version: COUNTY_REVIEW_SCHEMA_VERSION,
        campaign_id: [1; 16],
        actor_id: 9,
        authority_id: [2; 16],
        county: *b"26163",
        administration_label: "Administration".to_owned(),
        claimants_body_label: "Claimants".to_owned(),
        aid_body_label: "Aid".to_owned(),
        public_account_id: [3; 32],
        unit_price_micros: 280_000_000,
        going_wage_micros: 24_000_000,
        session_hours: 2,
        bring_hours: 2,
        first_session_period: 1,
        groups: groups
            .iter()
            .enumerate()
            .map(|(i, (households, roll, owners))| CountyReviewGroup {
                group_id: [u8::try_from(i).expect("few groups") + 1; 32],
                label: format!("Group {i}"),
                kind: GroupKind::Ordinary,
                opening_households: *households,
                roll_units: *roll,
                has_ownership_income: *owners,
                receives_mutual_aid: false,
            })
            .collect(),
        crews: crews
            .iter()
            .enumerate()
            .map(|(i, group)| CountyReviewCrew {
                crew_id: [u8::try_from(i).expect("few crews") + 1; 32],
                group: *group,
                site_id: [4; 32],
                unit_id: [5; 32],
                workplace_label: format!("Workplace {i}"),
                pay_mode: PayMode::Wage,
            })
            .collect(),
        content_digest: [8; 32],
        policy_source_digest: [9; 32],
    }
}

pub fn placed(rows: &[PlacedRow]) -> Placed {
    rows.iter()
        .map(|r| {
            (
                (r.group, r.crew, r.at_work, r.seeking, r.units),
                r.households,
            )
        })
        .collect()
}

pub fn rows(roster: &Roster) -> Vec<RowTuple> {
    roster
        .rows
        .iter()
        .map(|r| {
            let k = &r.key;
            (
                (k.group, k.band, k.crew, k.at_work, k.seeking, k.units),
                r.households,
                r.reached,
            )
        })
        .collect()
}

/// A roster written by hand from `(key, households, reached)`; each group's households are the
/// sum of its rows.
pub fn hand_roster(config: &CountyReviewConfig, rows: &[RowTuple]) -> Roster {
    let mut groups = vec![
        RosterGroup {
            households: 0,
            departed_units: 0
        };
        config.groups.len()
    ];
    let mut out: Vec<RosterRow> = rows
        .iter()
        .map(
            |((group, band, crew, at_work, seeking, units), households, reached)| {
                groups[usize::try_from(*group).expect("small group")].households += households;
                RosterRow {
                    key: PositionKey {
                        group: *group,
                        band: *band,
                        crew: *crew,
                        at_work: *at_work,
                        seeking: *seeking,
                        units: *units,
                    },
                    households: *households,
                    reached: *reached,
                }
            },
        )
        .collect();
    out.sort_by_key(|r| r.key);
    Roster {
        period: 0,
        groups,
        rows: out,
    }
}

/// The engine's facts for a roll-forward: opening and closing sums come from the roster and the
/// changes, and each group closes with `households`.
pub fn facts(
    config: &CountyReviewConfig,
    roster: &Roster,
    changes: &[(u32, Changes)],
    households: &[u64],
) -> CountyPeriodFacts {
    let crews = (0..config.crews.len())
        .map(|i| {
            let crew = u32::try_from(i).expect("few crews");
            let c = changes
                .iter()
                .find(|(index, _)| *index == crew)
                .map(|(_, c)| *c)
                .unwrap_or_default();
            let (e, s) = (roster.crew_at_work(crew), roster.crew_seeking(crew));
            CrewPeriodFacts {
                crew,
                accrued_wages_micros: 0,
                opening_at_work: e,
                opening_seeking: s,
                left_at_work: c.left_at_work,
                left_seeking: c.left_seeking,
                hires: c.hires,
                separations: c.separations,
                closing_at_work: (e + c.hires).saturating_sub(c.left_at_work + c.separations),
                closing_seeking: (s + c.separations).saturating_sub(c.left_seeking + c.hires),
            }
        })
        .collect();
    let groups = households
        .iter()
        .enumerate()
        .map(|(i, closing)| GroupPeriodFacts {
            group: u32::try_from(i).expect("few groups"),
            taxed_wages_micros: 0,
            wage_tax_collected_micros: 0,
            ownership_income_micros: 0,
            support_income_micros: 0,
            aid_income_micros: 0,
            free_hours: 0,
            closing_households: *closing,
        })
        .collect();
    CountyPeriodFacts {
        period: roster.period,
        crews,
        groups,
        cash_micros: 0,
        cash_floor_micros: 0,
        spending_limit_micros: 0,
        first_class_micros: 0,
    }
}
