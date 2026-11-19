//! Builders and short names for the County Review kernel tests.
use babylon_practice_contract as practice_contract;
use babylon_practice_contract::{
    Band, CountyPeriodFacts, CountyReviewConfig, CountyReviewCrew, CountyReviewGroup,
    CrewPeriodFacts, GroupKind, GroupPeriodFacts, OpeningCrew, PayMode, PlacedRow, PositionKey,
    Roster, RosterGroup, RosterRow, SessionRecord, SessionRow, COUNTY_REVIEW_SCHEMA_VERSION,
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

pub fn open(crew: u32, at_work: u64, seeking: u64) -> OpeningCrew {
    OpeningCrew {
        crew,
        at_work,
        seeking,
    }
}

/// A small xorshift generator: the tests need no dependency.
pub struct Rng(pub u64);
impl Rng {
    fn draw(&mut self) -> u64 {
        self.0 ^= self.0 << 13;
        self.0 ^= self.0 >> 7;
        self.0 ^= self.0 << 17;
        self.0
    }
    pub fn up_to(&mut self, bound: u64) -> u64 {
        self.draw() % (bound + 1)
    }
}

/// A random county the law accepts, and its opening roster.
pub fn random_opening(rng: &mut Rng) -> Option<(CountyReviewConfig, Vec<OpeningCrew>, Roster)> {
    let group_count = usize::try_from(1 + rng.up_to(2)).expect("small");
    let crew_count = 1 + rng.up_to(3);
    let crew_groups: Vec<u32> = (0..crew_count)
        .map(|_| {
            u32::try_from(rng.up_to(u64::try_from(group_count).expect("small") - 1)).expect("small")
        })
        .collect();
    let crews: Vec<OpeningCrew> = (0..crew_count)
        .map(|i| {
            open(
                u32::try_from(i).expect("small"),
                rng.up_to(15),
                rng.up_to(8),
            )
        })
        .collect();
    let groups: Vec<(u64, u64, bool)> = (0..group_count)
        .map(|g| {
            let seekers: u64 = crews
                .iter()
                .zip(&crew_groups)
                .filter(|(_, group)| usize::try_from(**group).expect("small") == g)
                .map(|(c, _)| c.seeking)
                .sum();
            (1 + rng.up_to(39), seekers, rng.up_to(2) == 0)
        })
        .collect();
    let c = config(&groups, &crew_groups);
    let reach: Vec<(u32, u64)> = groups
        .iter()
        .enumerate()
        .map(|(g, (households, _, _))| {
            (u32::try_from(g).expect("small"), rng.up_to(households / 4))
        })
        .collect();
    let roster = practice_contract::opening_roster(&c, &crews, &reach).ok()?;
    Some((c, crews, roster))
}

/// A position by its six answers.
const fn key(
    group: u32,
    band: Band,
    crew: Option<u32>,
    at_work: u16,
    seeking: u16,
    units: u16,
) -> PositionKey {
    PositionKey {
        group,
        band,
        crew,
        at_work,
        seeking,
        units,
    }
}

/// The worked example of design 7.7: one at work, a full period, holding a unit.
pub const A: PositionKey = key(0, B50, Some(0), 1, 1, 1);
/// One at work, a full period, off the roll.
pub const D: PositionKey = key(0, N40, Some(0), 1, 0, 0);
/// One at work, half a period, holding a unit.
pub const B: PositionKey = key(0, B50, Some(1), 1, 1, 1);
/// No wage, holding a unit.
pub const C: PositionKey = key(1, B50, Some(2), 0, 1, 1);

pub const fn tuple(key: PositionKey, households: u64, reached: u64) -> RowTuple {
    (
        (
            key.group,
            key.band,
            key.crew,
            key.at_work,
            key.seeking,
            key.units,
        ),
        households,
        reached,
    )
}

/// A county of the worked example's shape holding the given rows. Group 0 has crews 0 and 1,
/// group 1 has crew 2. Crew 0 was paid `11_520_000_000`, crew 1 `1_920_000_000` and crew 2 nothing;
/// group 0 had `13_440_000_000` taxed of which `2_016_000_000` was collected; both groups have 100
/// free hours; the county has cash for every unit.
pub fn world_with(rows_held: &[RowTuple]) -> (CountyReviewConfig, Roster, CountyPeriodFacts) {
    let c = config(&[(4, 3, false), (2, 2, false)], &[0, 0, 1]);
    let r = hand_roster(&c, rows_held);
    let households: Vec<u64> = r.groups.iter().map(|g| g.households).collect();
    let mut f = facts(&c, &r, &[], &households);
    for (crew, wages) in [(0, 11_520_000_000), (1, 1_920_000_000), (2, 0)] {
        f.crews[crew].accrued_wages_micros = wages;
    }
    f.groups[0].taxed_wages_micros = 13_440_000_000;
    f.groups[0].wage_tax_collected_micros = 2_016_000_000;
    for group in &mut f.groups {
        group.free_hours = 100;
    }
    f.cash_micros = 10_000_000_000;
    f.spending_limit_micros = 10_000_000_000;
    (c, r, f)
}

/// The worked example of design 7.7, built by hand: `A` x 2, `D` x 1, `B` x 1 and `C` x 2.
pub fn world() -> (CountyReviewConfig, Roster, CountyPeriodFacts) {
    world_with(&[
        tuple(A, 2, 0),
        tuple(D, 1, 0),
        tuple(B, 1, 0),
        tuple(C, 2, 0),
    ])
}

/// Sets the households reached in a position.
pub fn reach(roster: &mut Roster, position: PositionKey, reached: u64) {
    roster
        .rows
        .iter_mut()
        .find(|row| row.key == position)
        .expect("the position is in the roster")
        .reached = reached;
}

/// Sets the county's cash so that it pays `units` household units on `world()`'s unit price.
pub fn short(facts: &mut CountyPeriodFacts, units: i128) {
    facts.cash_micros = units * 280_000_000;
}

/// A position's row in a record.
pub fn row(record: &SessionRecord, position: PositionKey) -> &SessionRow {
    record
        .rows
        .iter()
        .find(|r| r.key == position)
        .expect("the position is in the record")
}

fn checked_total(values: impl Iterator<Item = u64>) -> u64 {
    values.fold(0, |total, value| {
        total.checked_add(value).expect("the totals are small")
    })
}

/// Asserts the identities of one position's row.
fn row_balanced(r: &SessionRow) {
    let units = u64::from(r.key.units);
    assert!(
        r.reached <= r.households,
        "reached never exceeds households"
    );
    assert_eq!(r.units_listed, units * r.households, "listed units");
    assert_eq!(
        r.units_paid + r.units_unpaid,
        r.units_listed,
        "paid and unpaid make the listed"
    );
    assert_eq!(
        r.asked,
        r.asked_paid + r.asked_no_place,
        "askers are paid or find no place"
    );
    assert_eq!(
        r.reached,
        r.asked_paid
            + r.asked_no_place
            + r.asked_no_time
            + r.came_from_roll
            + r.roll_no_time
            + r.nothing_at_stake
            + r.not_worth_time,
        "every reached household is counted once"
    );
    if units > 0 {
        assert_eq!(r.asked, 0, "a household that holds a unit does not ask");
        assert_eq!(
            r.losers,
            r.units_unpaid.div_ceil(units),
            "units are lost a household at a time"
        );
        assert!(r.losers_reached <= r.losers.min(r.reached));
        assert!(
            r.losers - r.losers_reached <= r.households - r.reached,
            "unreached losers are unreached households"
        );
        assert!(r.came_from_roll + r.roll_no_time <= r.losers_reached);
    } else {
        assert_eq!((r.units_listed, r.losers, r.came_from_roll), (0, 0, 0));
    }
    assert!(
        r.brought <= r.households - r.reached,
        "a position cannot grow past its households"
    );
    let came = r.asked_paid + r.came_from_roll;
    assert!(r.brought <= came, "only households that came bring one");
    if came > 0 {
        assert_eq!(
            r.hours_in_room % came,
            0,
            "each household in the room spends the same hours"
        );
    } else {
        assert_eq!(r.hours_in_room, 0);
    }
    assert!(r.rank >= 1);
}

/// Asserts the identities of the lines and the money.
fn money_balanced(record: &SessionRecord) {
    let listed = checked_total(record.rows.iter().map(|r| r.units_listed));
    let paid = checked_total(record.rows.iter().map(|r| r.units_paid));
    let asked_paid = checked_total(record.rows.iter().map(|r| r.asked_paid));
    assert_eq!(listed, record.household_units_listed);
    assert!(record.household_units_payable <= listed);
    assert!(
        paid + asked_paid + record.kept_back_units <= record.household_units_payable,
        "units paid and kept back are never more than the county can pay"
    );
    assert_eq!(asked_paid, record.aid_roll_households);
    assert_eq!(
        checked_total(record.rows.iter().map(|r| r.came_from_roll)),
        record.claimants_roll_households
    );
    assert!(record.relief_micros <= record.roll_total_micros);
    if record.relief_micros == record.roll_total_micros {
        assert_eq!(
            record.household_units_payable, listed,
            "a whole roll pays every unit listed"
        );
    }
    let mut price = None;
    let mut household_total = 0_i128;
    let mut last_group = None;
    for line in &record.lines {
        assert!(
            line.units > 0 && line.amount_micros > 0,
            "no empty line reaches the engine"
        );
        assert!(
            last_group < Some(line.group),
            "lines follow the groups' order"
        );
        last_group = Some(line.group);
        let each = line.amount_micros / i128::from(line.units);
        assert_eq!(
            each * i128::from(line.units),
            line.amount_micros,
            "a line is whole units"
        );
        assert_eq!(
            *price.get_or_insert(each),
            each,
            "every line is at one unit price"
        );
        household_total += line.amount_micros;
    }
    let collective_total: i128 = record
        .collective_lines
        .iter()
        .map(|l| l.amount_micros)
        .sum();
    assert!(
        record.collective_lines.iter().all(|l| l.amount_micros > 0),
        "no empty line reaches the engine"
    );
    assert!(
        household_total + collective_total <= record.relief_micros,
        "the lines sum to no more than the money for relief"
    );
    if let Some(price) = price {
        assert_eq!(record.roll_total_micros % price, 0);
        assert_eq!(
            household_total,
            price * i128::from(paid + asked_paid),
            "household lines are the units paid, at the price"
        );
    }
}

/// Asserts every identity of design 7.13 that a record can show.
pub fn balanced(record: &SessionRecord) {
    let mut keys: Vec<PositionKey> = Vec::new();
    for r in &record.rows {
        assert!(!keys.contains(&r.key), "positions are unique");
        keys.push(r.key);
        row_balanced(r);
    }
    let top = record.rows.iter().map(|r| r.rank).max().unwrap_or(0);
    for rank in 1..=top {
        assert!(
            record.rows.iter().any(|r| r.rank == rank),
            "ranks follow one another"
        );
    }
    money_balanced(record);
}
