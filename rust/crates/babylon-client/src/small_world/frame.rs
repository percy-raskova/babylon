//! The frame builder: one closed period of the small world as the hypergraph library's frame.
//!
//! Hours and money never meet here. Work flows, the hours ring and the workforce sets are `u64`
//! hours with their own scale; payments, the money ring, the owners' and the fund's sets and the
//! placement weights are money (millionths of a dollar) with theirs. Every figure drawn comes
//! from the period's receipts through `read_period`.

use super::layout::{
    self, FUND_AT, GROUP_SPREAD, MARK_Y, OUTLINE, PARTICLE_Y, PERSON_SPREAD, SET_Y, TREASURY_AT,
    WAGE_ANCHOR_Y, WORKPLACE_X,
};
use super::reading;
use super::reading::{GoodsMove, Party, PaymentKind, PeriodReading, ReadingError, WorkFlow};
use crate::palette::{BONE, CRIMSON, DIM, GOLD};
use babylon_circuit_worlds::doubled::HOURS_PER_PERSON;
use babylon_circuit_worlds::{Good, Household, Kind, PeriodResult, Place, Workplace};
use babylon_material_circuit::AccountId;
use hypergraph_rs::geometry::GeometryError;
use hypergraph_rs::geometry::OutlineParams;
use hypergraph_rs::geometry::Point;
use hypergraph_rs::geometry::Positions;
use hypergraph_rs::Hypergraph;
use hypergraph_rs_bevy::{
    FieldConfig, FieldError, FieldFrame, FieldStyles, Flow, Glyph, Hatch, HatchDirection,
    LineStyle, Palette, ParticleFrame, ParticleStyle, SetFrame, SetStyle, StreamStyle,
};
use std::collections::BTreeMap;
use std::fmt::{Display, Formatter, Result as FmtResult};
use std::num::NonZeroU64;
use std::time::Duration;

/// The stream of hours given to workplaces.
pub const STREAM_WORK: u16 = 0;
/// The streams of food, power and care.
pub const STREAM_GOODS: [u16; 3] = [1, 2, 3];
/// The streams of wages, purchases, taxes, benefits and profit.
pub const STREAM_MONEY: [u16; 5] = [4, 5, 6, 7, 8];
/// Hours one mark of the work stream stands for.
pub const HOURS_PER_MARK: u64 = 2;
/// Units one mark of a goods stream stands for.
pub const UNITS_PER_MARK: u64 = 4;
/// Millionths of a dollar one mark of a money stream stands for ($80).
pub const MONEY_PER_MARK: u64 = 80_000_000;

/// What the hours ring of a workplace starts at, grows by, and the hours that fill one step.
const HOURS_RING_BASE: f64 = 0.42;
const HOURS_RING_GAIN: f64 = 0.22;
const HOURS_RING_FULL: f64 = 120.0;
/// What the money ring of a workplace starts at, grows by, and the dollars that fill one step.
const MONEY_RING_BASE: f64 = 0.52;
const MONEY_RING_GAIN: f64 = 0.22;
const MONEY_RING_FULL_DOLLARS: f64 = 1_500.0;
/// A ring stops growing at this many steps.
const RING_STEPS_MAX: f64 = 2.0;
/// How far short of a body's centre an idle hour's hollow flow ends.
const IDLE_STOPS_SHORT: f64 = 0.7;
/// The glyph sizes of the particles: a group of up to 4, a person, a group of 5 to 8, 9 or more.
const PARTICLE_SIZES: [f32; 4] = [0.30, 0.13, 0.42, 0.52];

/// What a particle is: a household group, or each person of it.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub enum ParticleMode {
    #[default]
    Groups,
    People,
}

/// A body of the scene: a workplace, the treasury or the fund.
#[derive(Clone, Debug, PartialEq)]
pub struct BodyPicture {
    pub party: Party,
    pub id: String,
    pub at: Point,
    /// Hours reached, as a ring's radius; only on workplaces.
    pub hours_ring: Option<f32>,
    /// Money taken in, as a ring's radius; only on workplaces.
    pub money_ring: Option<f32>,
    /// Units made this period; only on workplaces.
    pub made: Option<u64>,
}

/// The three kinds of sets, each its own hypergraph with its own number.
#[derive(Debug, PartialEq)]
pub struct SetGraphs {
    /// Hours given to a workplace.
    pub workforces: Hypergraph<(), (), u64>,
    /// Book capital in millionths of a dollar.
    pub owners: Hypergraph<(), (), i128>,
    /// Benefits paid by the fund, in millionths of a dollar.
    pub fund: Hypergraph<(), (), i128>,
}

/// Everything the scene shows of one period.
#[derive(Debug, PartialEq)]
pub struct Picture {
    pub frame: FieldFrame,
    pub bodies: Vec<BodyPicture>,
    pub positions: Positions,
    pub sets: SetGraphs,
    pub reading: PeriodReading,
    pub mode: ParticleMode,
}

/// Why a picture cannot be built.
#[derive(Debug, Clone, PartialEq)]
pub enum FrameError {
    Reading(ReadingError),
    Field(FieldError),
    Geometry(GeometryError),
    /// A set, a household or an account the period does not hold.
    Edge(String),
    /// A sum overflowed, or a figure does not fit the type it is drawn in.
    Arithmetic,
}

impl Display for FrameError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FmtResult {
        match self {
            Self::Reading(e) => write!(f, "the period cannot be read: {e}"),
            Self::Field(e) => write!(f, "the library refuses the frame: {e}"),
            Self::Geometry(e) => write!(f, "the library's geometry refuses: {e}"),
            Self::Edge(what) => write!(f, "a set or household is missing: {what}"),
            Self::Arithmetic => write!(f, "a figure of the picture does not add up"),
        }
    }
}

impl std::error::Error for FrameError {}

impl From<ReadingError> for FrameError {
    fn from(error: ReadingError) -> Self {
        Self::Reading(error)
    }
}

impl From<FieldError> for FrameError {
    fn from(error: FieldError) -> Self {
        Self::Field(error)
    }
}

impl From<GeometryError> for FrameError {
    fn from(error: GeometryError) -> Self {
        Self::Geometry(error)
    }
}

/// Three beats of one second: hours, then goods, then money.
#[must_use]
pub fn field_config() -> FieldConfig {
    FieldConfig::three_beats(Duration::from_millis(1_000))
}

/// The palette: bone, crimson, gold and dim; the scene has no ground, so the ramp is dim.
#[must_use]
pub fn field_palette() -> Palette {
    Palette {
        ramp: [DIM, DIM, DIM],
        no_reading: DIM,
        swatches: vec![BONE, CRIMSON, GOLD, DIM],
    }
}

/// A mark stands for at least one: a zero figure fails the build, never a run.
const fn unit(n: u64) -> NonZeroU64 {
    match NonZeroU64::new(n) {
        Some(unit) => unit,
        None => panic!("a mark stands for at least one"),
    }
}

const HOURS_UNIT: NonZeroU64 = unit(HOURS_PER_MARK);
const UNITS_UNIT: NonZeroU64 = unit(UNITS_PER_MARK);
const MONEY_UNIT: NonZeroU64 = unit(MONEY_PER_MARK);

fn stream(
    beat: usize,
    per_mark: NonZeroU64,
    glyphs: (Glyph, Glyph),
    size: f32,
    swatch: u16,
) -> StreamStyle {
    StreamStyle {
        beat,
        unit: per_mark,
        full: glyphs.0,
        hollow: glyphs.1,
        size,
        swatch,
        share_drawn: 0.95,
        max_marks: 300,
    }
}

fn set_style(
    swatch: u16,
    width: f32,
    dash: Option<(f32, f32)>,
    hatch: (HatchDirection, f32),
) -> SetStyle {
    SetStyle {
        swatch,
        line: LineStyle { width, dash },
        hatch: Some(Hatch {
            direction: hatch.0,
            spacing: hatch.1,
            width: 0.025,
        }),
    }
}

/// The styles: four particles, three kinds of set, nine streams.
#[must_use]
pub fn field_styles() -> FieldStyles {
    let particle = |size: f32| ParticleStyle {
        glyph: Glyph::Disc,
        size,
        swatch: 0,
    };
    let mut streams = vec![stream(0, HOURS_UNIT, (Glyph::Disc, Glyph::Ring), 0.11, 0)];
    for _ in STREAM_GOODS {
        streams.push(stream(
            1,
            UNITS_UNIT,
            (Glyph::Square, Glyph::SquareFrame),
            0.13,
            1,
        ));
    }
    for _ in STREAM_MONEY {
        streams.push(stream(
            2,
            MONEY_UNIT,
            (Glyph::Streak, Glyph::Streak),
            0.34,
            2,
        ));
    }
    FieldStyles {
        particles: PARTICLE_SIZES.iter().map(|size| particle(*size)).collect(),
        sets: vec![
            set_style(0, 0.05, None, (HatchDirection::Deg45, 0.30)),
            set_style(2, 0.056, None, (HatchDirection::Deg135, 0.42)),
            set_style(2, 0.056, Some((0.28, 0.14)), (HatchDirection::Deg0, 0.34)),
        ],
        streams,
        region_outline: None,
    }
}

// ---- numbers: hours and money have their own conversions ----

#[expect(
    clippy::cast_precision_loss,
    reason = "hours of this world are far below 2^53"
)]
fn hours_f64(hours: u64) -> f64 {
    hours as f64
}

#[expect(
    clippy::cast_precision_loss,
    reason = "money of this world is far below 2^53 millionths; the figure only weights a position"
)]
fn dollars_f64(micro: i128) -> f64 {
    micro as f64 / 1e6
}

#[expect(
    clippy::cast_precision_loss,
    reason = "a count of persons is far below 2^53"
)]
fn count_f64(n: usize) -> f64 {
    n as f64
}

#[expect(
    clippy::cast_possible_truncation,
    reason = "a ring radius is a small figure; the scene draws in f32"
)]
fn narrow(value: f64) -> f32 {
    value as f32
}

fn hours_ring(reached: u64) -> Option<f32> {
    (reached > 0).then(|| {
        let steps = (hours_f64(reached) / HOURS_RING_FULL).min(RING_STEPS_MAX);
        narrow(HOURS_RING_BASE + HOURS_RING_GAIN * steps)
    })
}

fn money_ring(taken: i128) -> Option<f32> {
    (taken > 0).then(|| {
        let steps = (dollars_f64(taken) / MONEY_RING_FULL_DOLLARS).min(RING_STEPS_MAX);
        narrow(MONEY_RING_BASE + MONEY_RING_GAIN * steps)
    })
}

fn add_hours(a: u64, b: u64) -> Result<u64, FrameError> {
    a.checked_add(b).ok_or(FrameError::Arithmetic)
}

fn add_money(a: i128, b: i128) -> Result<i128, FrameError> {
    a.checked_add(b).ok_or(FrameError::Arithmetic)
}

/// Shares are counted apart from hours and money; they only weight a division.
fn add_shares(a: u64, b: u64) -> Result<u64, FrameError> {
    a.checked_add(b).ok_or(FrameError::Arithmetic)
}

/// A total of money split equally, the remainder to the first.
fn split_money(total: i128, n: usize) -> Result<Vec<i128>, FrameError> {
    let count = i128::try_from(n).map_err(|_| FrameError::Arithmetic)?;
    if count == 0 {
        return Err(missing("a household with no persons to share with"));
    }
    let mut shares = vec![total / count; n];
    shares[0] = add_money(shares[0], total % count)?;
    Ok(shares)
}

// ---- ids ----

fn place_letter(place: Place) -> &'static str {
    match place {
        Place::A => "a",
        Place::B => "b",
    }
}

fn kind_name(kind: Kind) -> &'static str {
    kind.label()
}

pub(super) fn workplace_id(w: Workplace) -> String {
    format!("workplace:{}:{}", place_letter(w.place), kind_name(w.kind))
}

fn household_byte(h: Household) -> u8 {
    h.principal().as_bytes()[0]
}

pub(super) fn household_id(h: Household) -> String {
    format!("household:{}", household_byte(h))
}

pub(super) fn person_id(h: Household, k: usize) -> String {
    format!("person:{}:{k}", household_byte(h))
}

pub(super) fn party_id(party: Party) -> String {
    match party {
        Party::Workplace(w) => workplace_id(w),
        Party::Household(h) => household_id(h),
        Party::Treasury => "treasury".to_string(),
        Party::Fund => "fund".to_string(),
    }
}

pub(super) fn workforce_edge(w: Workplace) -> String {
    format!("workforce:{}:{}", place_letter(w.place), kind_name(w.kind))
}

pub(super) fn owner_edge(place: Place) -> String {
    format!("owner:{}", place_letter(place))
}

pub(super) const FUND_EDGE: &str = "fund";

fn missing(what: &str) -> FrameError {
    FrameError::Edge(what.to_string())
}

// ---- who is there ----

/// How many persons each household holds and how many of them are at work.
struct Population {
    persons: BTreeMap<Household, usize>,
    at_work: BTreeMap<Household, usize>,
}

impl Population {
    fn of(result: &PeriodResult) -> Result<Self, FrameError> {
        let mut persons = BTreeMap::new();
        for h in Household::ALL {
            let cohort = result
                .closing
                .households
                .iter()
                .find(|c| c.principal_id == h.principal())
                .ok_or_else(|| missing(&format!("no cohort for {}", household_id(h))))?;
            persons.insert(
                h,
                usize::try_from(cohort.persons).map_err(|_| FrameError::Arithmetic)?,
            );
        }
        let mut at_work = BTreeMap::new();
        for member in &result.members {
            let w = Workplace::from_site(member.site_id)
                .ok_or_else(|| missing("a staffing member of no workplace"))?;
            let employed =
                usize::try_from(member.opening_employed).map_err(|_| FrameError::Arithmetic)?;
            let count = persons.get(&w.workers()).copied().unwrap_or(0);
            at_work.insert(w.workers(), employed.min(count));
        }
        Ok(Self { persons, at_work })
    }

    fn persons(&self, h: Household) -> usize {
        self.persons.get(&h).copied().unwrap_or(0)
    }

    fn at_work(&self, h: Household) -> usize {
        self.at_work.get(&h).copied().unwrap_or(0)
    }
}

/// Where the households and persons stand, and the particles that show them.
struct Standing {
    households: BTreeMap<Household, Point>,
    particles: Vec<ParticleFrame>,
    positions: Positions,
}

type Paid = BTreeMap<Household, Vec<(Point, f64)>>;

/// What paid each household this period: every anchor with its dollars, and the benefits alone.
fn paid_by(reading: &PeriodReading) -> (Paid, Paid) {
    let (mut all, mut benefits): (Paid, Paid) = (BTreeMap::new(), BTreeMap::new());
    for payment in &reading.payments {
        let Party::Household(h) = payment.payee else {
            continue;
        };
        let Some(at) = layout::anchor(payment.kind, payment.payer, h.place()) else {
            continue;
        };
        let weight = dollars_f64(payment.amount);
        all.entry(h).or_default().push((at, weight));
        if payment.kind == PaymentKind::Benefits {
            benefits.entry(h).or_default().push((at, weight));
        }
    }
    (all, benefits)
}

fn stand_of(paid: &Paid, h: Household) -> Result<Point, FrameError> {
    let anchors = paid.get(&h).map_or(&[][..], Vec::as_slice);
    Ok(layout::stand_at(h.place(), anchors)?)
}

fn group_style(persons: usize) -> u16 {
    match persons {
        0..=4 => 0,
        5..=8 => 2,
        _ => 3,
    }
}

fn particle(id: String, at: Point, style: u16) -> ParticleFrame {
    ParticleFrame {
        id,
        at: hypergraph_rs_bevy::plan_to_scene(at, PARTICLE_Y),
        style,
    }
}

fn body_positions(into: &mut Positions) {
    for w in Workplace::ALL {
        into.insert(workplace_id(w), (WORKPLACE_X[w.index()], 0.0));
    }
    into.insert("treasury", TREASURY_AT);
    into.insert("fund", FUND_AT);
}

fn stand(
    reading: &PeriodReading,
    pop: &Population,
    mode: ParticleMode,
) -> Result<Standing, FrameError> {
    let (all, benefits) = paid_by(reading);
    let mut raw = Vec::new();
    for h in Household::ALL {
        raw.push((household_id(h), stand_of(&all, h)?));
    }
    let groups = layout::spread_apart(&raw, GROUP_SPREAD)?;
    let mut households = BTreeMap::new();
    for h in Household::ALL {
        let at = groups
            .get(&household_id(h))
            .ok_or_else(|| missing(&household_id(h)))?;
        households.insert(h, at);
    }
    match mode {
        ParticleMode::Groups => {
            let mut positions = Positions::new();
            let mut particles = Vec::new();
            for (h, at) in &households {
                positions.insert(household_id(*h), *at);
                particles.push(particle(
                    household_id(*h),
                    *at,
                    group_style(pop.persons(*h)),
                ));
            }
            body_positions(&mut positions);
            Ok(Standing {
                households,
                particles,
                positions,
            })
        }
        ParticleMode::People => stand_people(&households, &benefits, pop),
    }
}

/// People: a worker household's employed persons cluster at its workplace's wage anchor, its
/// other persons at the point its benefits give (or home); owners and supported persons cluster
/// at their group's point. Then every person is spread.
fn stand_people(
    groups: &BTreeMap<Household, Point>,
    benefits: &Paid,
    pop: &Population,
) -> Result<Standing, FrameError> {
    let mut clustered: Vec<(String, Point)> = Vec::new();
    for h in Household::ALL {
        let n = pop.persons(h);
        let points = match h {
            Household::Workers(w) => {
                let employed = pop.at_work(h).min(n);
                let anchor = (WORKPLACE_X[w.index()], WAGE_ANCHOR_Y);
                let mut points = layout::cluster(anchor, employed);
                points.extend(layout::cluster(stand_of(benefits, h)?, n - employed));
                points
            }
            Household::Owner(_) | Household::Supported(_) => {
                let at = groups.get(&h).ok_or_else(|| missing(&household_id(h)))?;
                layout::cluster(*at, n)
            }
        };
        for (k, at) in points.into_iter().enumerate() {
            clustered.push((person_id(h, k), at));
        }
    }
    let spread = layout::spread_apart(&clustered, PERSON_SPREAD)?;
    let mut positions = Positions::new();
    let mut households = BTreeMap::new();
    let mut particles = Vec::new();
    for h in Household::ALL {
        let mut own = Vec::new();
        for k in 0..pop.persons(h) {
            let id = person_id(h, k);
            let at = spread.get(&id).ok_or_else(|| missing(&id))?;
            positions.insert(id.clone(), at);
            particles.push(particle(id, at, 1));
            own.push(at);
        }
        households.insert(h, mean(&own, h)?);
    }
    body_positions(&mut positions);
    Ok(Standing {
        households,
        particles,
        positions,
    })
}

fn mean(points: &[Point], h: Household) -> Result<Point, FrameError> {
    if points.is_empty() {
        return Err(missing(&format!("no persons in {}", household_id(h))));
    }
    let n = count_f64(points.len());
    let (x, y) = points
        .iter()
        .fold((0.0, 0.0), |sum, at| (sum.0 + at.0, sum.1 + at.1));
    Ok((x / n, y / n))
}

impl Standing {
    fn point(&self, party: Party) -> Result<Point, FrameError> {
        Ok(match party {
            Party::Workplace(w) => (WORKPLACE_X[w.index()], 0.0),
            Party::Household(h) => self
                .households
                .get(&h)
                .copied()
                .ok_or_else(|| missing(&format!("no place for {}", household_id(h))))?,
            Party::Treasury => TREASURY_AT,
            Party::Fund => FUND_AT,
        })
    }
}

// ---- bodies ----

fn bodies(result: &PeriodResult, reading: &PeriodReading) -> Result<Vec<BodyPicture>, FrameError> {
    let mut bodies = Vec::new();
    for w in Workplace::ALL {
        let mut reached = 0_u64;
        for flow in reading.work.iter().filter(|f| f.workplace == w) {
            reached = add_hours(add_hours(reached, flow.given)?, flow.idle)?;
        }
        let mut taken = 0_i128;
        for payment in reading
            .payments
            .iter()
            .filter(|p| p.payee == Party::Workplace(w))
        {
            taken = add_money(taken, payment.amount)?;
        }
        bodies.push(BodyPicture {
            party: Party::Workplace(w),
            id: workplace_id(w),
            at: (WORKPLACE_X[w.index()], 0.0),
            hours_ring: hours_ring(reached),
            money_ring: money_ring(taken),
            made: Some(result.summary.made[w.index()]),
        });
    }
    for (party, at) in [(Party::Treasury, TREASURY_AT), (Party::Fund, FUND_AT)] {
        bodies.push(BodyPicture {
            party,
            id: party_id(party),
            at,
            hours_ring: None,
            money_ring: None,
            made: None,
        });
    }
    Ok(bodies)
}

// ---- sets ----

fn put<M: Clone>(
    graph: &mut Hypergraph<(), (), M>,
    edge: &str,
    node: &str,
    value: M,
) -> Result<(), FrameError> {
    graph
        .add_node_to_edge_with_data(edge, node, value)
        .map_err(|error| FrameError::Edge(error.to_string()))
}

fn given_to(reading: &PeriodReading, w: Workplace) -> Result<u64, FrameError> {
    reading
        .work
        .iter()
        .filter(|f| f.workplace == w)
        .try_fold(0_u64, |sum, f| add_hours(sum, f.given))
}

/// A workforce: its household with the hours given, or its persons, ten hours each in order.
fn workforces(
    reading: &PeriodReading,
    pop: &Population,
    mode: ParticleMode,
) -> Result<Hypergraph<(), (), u64>, FrameError> {
    let mut graph = Hypergraph::new();
    for w in Workplace::ALL {
        let edge = workforce_edge(w);
        let given = given_to(reading, w)?;
        match mode {
            ParticleMode::Groups => put(&mut graph, &edge, &household_id(w.workers()), given)?,
            ParticleMode::People => {
                let mut left = given;
                for k in 0..pop.persons(w.workers()) {
                    let hours = left.min(HOURS_PER_PERSON);
                    left -= hours;
                    put(&mut graph, &edge, &person_id(w.workers(), k), hours)?;
                }
            }
        }
    }
    Ok(graph)
}

fn capital_of(result: &PeriodResult, account: AccountId) -> Result<i128, FrameError> {
    let book = result
        .closing
        .capital
        .iter()
        .find(|c| c.account == account)
        .ok_or_else(|| missing(&format!("no book capital for {account:?}")))?;
    add_money(
        add_money(
            book.opening_capital.micro_units(),
            book.contributed_capital.micro_units(),
        )?,
        book.retained_earnings.micro_units(),
    )
}

/// The capital an owner holds in a workplace: the workplace's book capital (negative counts 0)
/// times the owner's shares over the site's total, or `None` when the owner holds no share.
fn held_in(
    result: &PeriodResult,
    owner: Household,
    w: Workplace,
) -> Result<Option<i128>, FrameError> {
    let mut total = 0_u64;
    let mut mine = 0_u64;
    for claim in result
        .closing
        .ownership
        .iter()
        .filter(|c| c.issuer_site_id == w.site_id())
    {
        total = add_shares(total, claim.shares)?;
        if claim.beneficiary == AccountId::Household(owner.principal()) {
            mine = add_shares(mine, claim.shares)?;
        }
    }
    if mine == 0 {
        return Ok(None);
    }
    let capital = capital_of(result, AccountId::Site(w.site_id()))?.max(0);
    let held = capital
        .checked_mul(i128::from(mine))
        .ok_or(FrameError::Arithmetic)?
        / i128::from(total);
    Ok(Some(held))
}

/// An owner: its household (or each person with an equal share) with its own book capital, and
/// its workplaces with the capital it holds in them.
fn owners(
    result: &PeriodResult,
    pop: &Population,
    mode: ParticleMode,
) -> Result<Hypergraph<(), (), i128>, FrameError> {
    let mut graph = Hypergraph::new();
    for place in Place::ALL {
        let owner = Household::Owner(place);
        let edge = owner_edge(place);
        let own = capital_of(result, AccountId::Household(owner.principal()))?.max(0);
        match mode {
            ParticleMode::Groups => put(&mut graph, &edge, &household_id(owner), own)?,
            ParticleMode::People => {
                for (k, share) in split_money(own, pop.persons(owner))?
                    .into_iter()
                    .enumerate()
                {
                    put(&mut graph, &edge, &person_id(owner, k), share)?;
                }
            }
        }
        for w in Workplace::ALL {
            if let Some(held) = held_in(result, owner, w)? {
                put(&mut graph, &edge, &workplace_id(w), held)?;
            }
        }
    }
    Ok(graph)
}

/// The fund: every recipient of a program of the fund with what it was paid; a person's share is
/// equal among the household's persons not at work (all of them when none is out of work).
fn fund_set(
    result: &PeriodResult,
    pop: &Population,
    mode: ParticleMode,
) -> Result<Hypergraph<(), (), i128>, FrameError> {
    let mut paid: BTreeMap<Household, i128> = BTreeMap::new();
    for receipt in result
        .receipts
        .public_programs
        .iter()
        .filter(|r| r.public_account == babylon_circuit_worlds::fund())
    {
        let h = Household::from_principal(receipt.recipient)
            .ok_or_else(|| missing("a recipient of no household"))?;
        let sum = add_money(
            paid.get(&h).copied().unwrap_or(0),
            receipt.paid.micro_units(),
        )?;
        paid.insert(h, sum);
    }
    let mut graph = Hypergraph::new();
    for (h, micro) in paid {
        match mode {
            ParticleMode::Groups => put(&mut graph, FUND_EDGE, &household_id(h), micro)?,
            ParticleMode::People => {
                let n = pop.persons(h);
                let working = pop.at_work(h).min(n);
                let first = if working < n { working } else { 0 };
                for (offset, share) in split_money(micro, n - first)?.into_iter().enumerate() {
                    put(&mut graph, FUND_EDGE, &person_id(h, first + offset), share)?;
                }
            }
        }
    }
    Ok(graph)
}

fn frames_of<M: Clone>(
    graph: &Hypergraph<(), (), M>,
    ids: &[String],
    kind: u16,
    positions: &Positions,
    weight: impl Fn(&M) -> f64,
) -> Result<Vec<SetFrame>, FrameError> {
    let listed: Vec<(&str, u16)> = ids.iter().map(|id| (id.as_str(), kind)).collect();
    let (reach, cell, share) = OUTLINE[usize::from(kind)];
    let params = OutlineParams::new(reach, cell, share);
    Ok(hypergraph_rs_bevy::set_frames(
        graph,
        &listed,
        positions,
        weight,
        &params,
        SET_Y[usize::from(kind)],
    )?)
}

fn set_frames_of(sets: &SetGraphs, positions: &Positions) -> Result<Vec<SetFrame>, FrameError> {
    let workforce_ids: Vec<String> = Workplace::ALL.iter().map(|w| workforce_edge(*w)).collect();
    let owner_ids: Vec<String> = Place::ALL.iter().map(|p| owner_edge(*p)).collect();
    let mut frames = frames_of(&sets.workforces, &workforce_ids, 0, positions, |h| {
        hours_f64(*h)
    })?;
    frames.extend(frames_of(&sets.owners, &owner_ids, 1, positions, |m| {
        dollars_f64(*m)
    })?);
    frames.extend(frames_of(
        &sets.fund,
        &[FUND_EDGE.to_string()],
        2,
        positions,
        |m| dollars_f64(*m),
    )?);
    Ok(frames)
}

// ---- flows ----

fn good_stream(good: Good) -> u16 {
    match good {
        Good::Food => STREAM_GOODS[0],
        Good::Power => STREAM_GOODS[1],
        Good::Care => STREAM_GOODS[2],
    }
}

fn payment_stream(kind: PaymentKind) -> u16 {
    match kind {
        PaymentKind::Wages => STREAM_MONEY[0],
        PaymentKind::Purchases => STREAM_MONEY[1],
        PaymentKind::Taxes => STREAM_MONEY[2],
        PaymentKind::Benefits => STREAM_MONEY[3],
        PaymentKind::Profit => STREAM_MONEY[4],
    }
}

fn flow(stream: u16, from: Point, to: Point, amount: u64, hollow: bool) -> Flow {
    Flow {
        stream,
        from: hypergraph_rs_bevy::plan_to_scene(from, MARK_Y),
        to: hypergraph_rs_bevy::plan_to_scene(to, MARK_Y),
        amount,
        hollow,
    }
}

/// The point `short` before `body` on the way from `from`.
fn short_of(body: Point, from: Point, short: f64) -> Point {
    let (dx, dy) = (from.0 - body.0, from.1 - body.1);
    let length = dx.hypot(dy);
    if length <= short {
        return body;
    }
    (body.0 + dx / length * short, body.1 + dy / length * short)
}

fn work_flows(
    work: &[WorkFlow],
    standing: &Standing,
    into: &mut Vec<Flow>,
) -> Result<(), FrameError> {
    for f in work {
        let from = standing.point(Party::Household(f.household))?;
        let body = standing.point(Party::Workplace(f.workplace))?;
        if f.given > 0 {
            into.push(flow(STREAM_WORK, from, body, f.given, false));
        }
        if f.idle > 0 {
            let end = short_of(body, from, IDLE_STOPS_SHORT);
            into.push(flow(STREAM_WORK, from, end, f.idle, true));
        }
    }
    Ok(())
}

fn goods_flows(
    goods: &[GoodsMove],
    standing: &Standing,
    into: &mut Vec<Flow>,
) -> Result<(), FrameError> {
    for m in goods {
        let (from, to) = (standing.point(m.from)?, standing.point(m.to)?);
        into.push(flow(good_stream(m.good), from, to, m.quantity, true));
    }
    Ok(())
}

fn money_flows(
    reading: &PeriodReading,
    standing: &Standing,
    into: &mut Vec<Flow>,
) -> Result<(), FrameError> {
    for p in &reading.payments {
        let amount = u64::try_from(p.amount).map_err(|_| FrameError::Arithmetic)?;
        if amount > 0 {
            let (from, to) = (standing.point(p.payer)?, standing.point(p.payee)?);
            into.push(flow(payment_stream(p.kind), from, to, amount, false));
        }
    }
    Ok(())
}

/// Build the picture of one closed period.
///
/// # Errors
/// `FrameError` when the period cannot be read, a household, account or set is missing from it,
/// a figure overflows, or the library's geometry refuses a number.
pub fn build_picture(result: &PeriodResult, mode: ParticleMode) -> Result<Picture, FrameError> {
    let reading = reading::read_period(result)?;
    let pop = Population::of(result)?;
    let standing = stand(&reading, &pop, mode)?;
    let sets = SetGraphs {
        workforces: workforces(&reading, &pop, mode)?,
        owners: owners(result, &pop, mode)?,
        fund: fund_set(result, &pop, mode)?,
    };
    let mut flows = Vec::new();
    work_flows(&reading.work, &standing, &mut flows)?;
    goods_flows(&reading.goods, &standing, &mut flows)?;
    money_flows(&reading, &standing, &mut flows)?;
    let frame = FieldFrame {
        period: reading.period,
        regions: Vec::new(),
        particles: standing.particles.clone(),
        sets: set_frames_of(&sets, &standing.positions)?,
        flows,
    };
    Ok(Picture {
        frame,
        bodies: bodies(result, &reading)?,
        positions: standing.positions,
        sets,
        reading,
        mode,
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use babylon_circuit_worlds::{Lasts, Places, Runner, Shock};
    use bevy::prelude::*;
    use bevy::time::TimeUpdateStrategy;
    use hypergraph_rs::geometry;
    use hypergraph_rs::geometry::Outline;
    use hypergraph_rs_bevy::{
        FieldPlugin, FieldSystems, FlowReport, FrameRefused, ParticleId, ShowPeriod, StreamReport,
    };
    use std::error::Error;

    type TestResult = Result<(), Box<dyn Error>>;

    fn first_result() -> Result<PeriodResult, Box<dyn Error>> {
        let mut runner = Runner::open()?;
        Ok(runner.step()?.clone())
    }

    fn quiet(mode: ParticleMode) -> Result<Picture, Box<dyn Error>> {
        Ok(build_picture(&first_result()?, mode)?)
    }

    fn particle_of<'a>(
        picture: &'a Picture,
        id: &str,
    ) -> Result<&'a ParticleFrame, Box<dyn Error>> {
        picture
            .frame
            .particles
            .iter()
            .find(|p| p.id == id)
            .ok_or_else(|| format!("no particle {id}").into())
    }

    fn set_of<'a>(picture: &'a Picture, id: &str) -> Result<&'a SetFrame, Box<dyn Error>> {
        picture
            .frame
            .sets
            .iter()
            .find(|s| s.id == id)
            .ok_or_else(|| format!("no set {id}").into())
    }

    fn member(set: &SetFrame, id: &str) -> Result<f64, Box<dyn Error>> {
        set.members
            .iter()
            .find(|(node, _)| node == id)
            .map(|(_, value)| *value)
            .ok_or_else(|| format!("no member {id} in {}", set.id).into())
    }

    fn near(a: Vec3, b: Vec3) -> bool {
        a.distance(b) < 1e-5
    }

    #[test]
    fn the_quiet_period_stands_by_its_ties() -> TestResult {
        let picture = quiet(ParticleMode::Groups)?;
        assert_eq!(picture.frame.particles.len(), 12);
        for w in Workplace::ALL {
            let p = particle_of(&picture, &household_id(w.workers()))?;
            let want = hypergraph_rs_bevy::plan_to_scene((WORKPLACE_X[w.index()], 3.3), 0.10);
            assert!(near(p.at, want), "{w:?} stands at {:?}", p.at);
            let style = if w.kind == Kind::Utility { 3 } else { 0 };
            assert_eq!(p.style, style, "{w:?}");
        }
        for (place, x) in [(Place::A, -7.08), (Place::B, 6.52)] {
            let owner = particle_of(&picture, &household_id(Household::Owner(place)))?;
            assert!(near(
                owner.at,
                hypergraph_rs_bevy::plan_to_scene((x, -2.4), 0.10)
            ));
            assert_eq!(owner.style, 2);
        }
        let a = Household::Supported(Place::A);
        let b = Household::Supported(Place::B);
        for h in [a, b] {
            assert_eq!(particle_of(&picture, &household_id(h))?.style, 2);
        }
        let (pa, pb) = (
            picture.positions.get(&household_id(a)).ok_or("a placed")?,
            picture.positions.get(&household_id(b)).ok_or("b placed")?,
        );
        assert!((f64::midpoint(pa.0, pb.0) - 1.1).abs() < 1e-9);
        assert!((f64::midpoint(pa.1, pb.1) - 8.3).abs() < 1e-9);
        let apart = (pa.0 - pb.0).hypot(pa.1 - pb.1);
        assert!((apart - SUPPORTED_APART).abs() < 1e-9, "apart {apart}");
        assert!(pa.0 < pb.0, "Place A's stands left of Place B's");
        assert!((pa.1 - pb.1).abs() < 1e-9, "side by side");
        for p in &picture.frame.particles {
            let at = picture.positions.get(&p.id).ok_or("a placed particle")?;
            assert_eq!(p.at, hypergraph_rs_bevy::plan_to_scene(at, 0.10));
        }
        Ok(())
    }

    /// The distance between the two supported groups: twice the lean of a benefit's anchor.
    const SUPPORTED_APART: f64 = 2.0;

    #[test]
    fn an_owner_s_set_is_one_outline() -> TestResult {
        let picture = quiet(ParticleMode::Groups)?;
        for place in Place::ALL {
            let set = set_of(&picture, &owner_edge(place))?;
            let Some(Outline::Membrane { paths }) = &set.outline else {
                return Err(format!("{} is not a membrane: {:?}", set.id, set.outline).into());
            };
            assert_eq!(paths.len(), 1, "{} draws {} loops", set.id, paths.len());
            let mut held = vec![household_id(Household::Owner(place))];
            held.extend(
                Workplace::ALL
                    .iter()
                    .filter(|w| w.place == place)
                    .map(|w| workplace_id(*w)),
            );
            for id in held {
                let at = picture.positions.get(&id).ok_or("a placed member")?;
                assert!(geometry::contains(paths, at), "{id} at {at:?} is outside");
            }
        }
        Ok(())
    }

    #[test]
    fn the_three_kinds_of_sets_are_real_hyperedges() -> TestResult {
        let picture = quiet(ParticleMode::Groups)?;
        assert_eq!(picture.frame.sets.len(), 11);
        let hours = [120.0, 40.0, 40.0, 40.0];
        for w in Workplace::ALL {
            let set = set_of(&picture, &workforce_edge(w))?;
            assert_eq!(set.members.len(), 1);
            assert_eq!(
                member(set, &household_id(w.workers()))?,
                hours[w.kind.index()]
            );
            assert!(
                matches!(set.outline, Some(Outline::Ring { .. })),
                "{}",
                set.id
            );
        }
        for place in Place::ALL {
            let set = set_of(&picture, &owner_edge(place))?;
            assert_eq!(set.members.len(), 5);
            let want = [1_200.0, 1_760.0, 880.0, 2_400.0];
            for w in Workplace::ALL.iter().filter(|w| w.place == place) {
                let got = member(set, &workplace_id(*w))?;
                assert_eq!(got, want[w.kind.index()], "{w:?}");
            }
            let own = member(set, &household_id(Household::Owner(place)))?;
            assert_eq!(own, 944.0);
        }
        let fund = set_of(&picture, "fund")?;
        assert_eq!(fund.members.len(), 10);
        for (id, value) in &fund.members {
            let supported = Place::ALL
                .iter()
                .any(|p| *id == household_id(Household::Supported(*p)));
            let want = if supported { 480.0 } else { 0.0 };
            assert_eq!(*value, want, "{id}");
        }
        Ok(())
    }

    fn report_of(
        report: &FlowReport,
        stream: u16,
        hollow: bool,
    ) -> Result<StreamReport, Box<dyn Error>> {
        report
            .streams
            .iter()
            .find(|r| r.stream == stream && r.hollow == hollow)
            .copied()
            .ok_or_else(|| format!("no report for stream {stream}").into())
    }

    #[test]
    fn each_stream_draws_and_counts_exactly_its_own_total() -> TestResult {
        let picture = quiet(ParticleMode::Groups)?;
        let (_, report) =
            hypergraph_rs_bevy::select_flows(&picture.frame.flows, &field_styles().streams)?;
        for r in &report.streams {
            assert_eq!(r.drawn + r.not_drawn, r.total, "{r:?}");
        }
        let work = report_of(&report, STREAM_WORK, false)?;
        assert_eq!((work.total, work.drawn, work.marks), (480, 480, 240));
        assert_eq!(report_of(&report, STREAM_WORK, true)?.total, 0);
        let goods = [(160, 152, 8), (240, 228, 12), (80, 76, 4)];
        for (stream, (total, drawn, not_drawn)) in STREAM_GOODS.iter().zip(goods) {
            let hollow = report_of(&report, *stream, true)?;
            assert_eq!(
                (hollow.total, hollow.drawn, hollow.not_drawn),
                (total, drawn, not_drawn),
                "stream {stream}"
            );
            assert_eq!(report_of(&report, *stream, false)?.total, 0);
        }
        let dollars = [4_800_u128, 10_320, 1_280, 1_280, 1_280];
        for (stream, want) in STREAM_MONEY.iter().zip(dollars) {
            let full = report_of(&report, *stream, false)?;
            assert_eq!(full.total, want * 1_000_000, "stream {stream}");
            assert_eq!(report_of(&report, *stream, true)?.total, 0);
        }
        assert!(picture
            .frame
            .flows
            .iter()
            .filter(|f| STREAM_GOODS.contains(&f.stream))
            .all(|f| f.hollow));
        Ok(())
    }

    #[test]
    fn people_stand_in_their_membranes() -> TestResult {
        let picture = quiet(ParticleMode::People)?;
        assert_eq!(picture.frame.particles.len(), 80);
        let utility = Workplace {
            place: Place::A,
            kind: Kind::Utility,
        };
        let set = set_of(&picture, &workforce_edge(utility))?;
        assert_eq!(set.members.len(), 12);
        assert!(set
            .members
            .iter()
            .all(|(_, hours)| (*hours - 10.0).abs() < 1e-9));
        let fund = set_of(&picture, "fund")?;
        let paid: Vec<f64> = fund
            .members
            .iter()
            .filter(|(_, value)| *value > 0.0)
            .map(|(_, value)| *value)
            .collect();
        assert_eq!(paid.len(), 16);
        assert!(paid.iter().all(|dollars| (*dollars - 60.0).abs() < 1e-9));
        Ok(())
    }

    #[test]
    fn the_harvest_failed_in_a_shows_in_the_next_period() -> TestResult {
        let mut runner = Runner::open()?;
        runner.step()?;
        runner.strike(Shock::HarvestFails, Places::A, Lasts::UntilLifted)?;
        let second = runner.step()?.clone();
        let picture = build_picture(&second, ParticleMode::Groups)?;
        let made = |id: &str| -> Result<Option<u64>, Box<dyn Error>> {
            Ok(picture
                .bodies
                .iter()
                .find(|b| b.id == id)
                .ok_or("a body")?
                .made)
        };
        assert_eq!(made("workplace:a:farm")?, Some(36));
        assert_eq!(made("workplace:b:farm")?, Some(40));
        let given: u64 = picture.reading.work.iter().map(|f| f.given).sum();
        assert_eq!(given, 480);
        Ok(())
    }

    fn twelve_periods(mode: ParticleMode) -> Result<Vec<Picture>, Box<dyn Error>> {
        let mut runner = Runner::open()?;
        let mut pictures = Vec::new();
        for period in 1..=12 {
            if period == 3 {
                runner.strike(Shock::HarvestFails, Places::B, Lasts::TenPeriods)?;
            }
            pictures.push(build_picture(&runner.step()?.clone(), mode)?);
        }
        Ok(pictures)
    }

    #[test]
    fn the_same_steps_give_the_same_frames_twice() -> TestResult {
        for mode in [ParticleMode::Groups, ParticleMode::People] {
            assert_eq!(twelve_periods(mode)?, twelve_periods(mode)?, "{mode:?}");
        }
        Ok(())
    }

    #[derive(Resource, Default)]
    struct Refusals(Vec<FrameRefused>);

    fn collect(mut refused: MessageReader<FrameRefused>, mut out: ResMut<Refusals>) {
        out.0.extend(refused.read().cloned());
    }

    fn field_app() -> Result<App, Box<dyn Error>> {
        let plugin = FieldPlugin::new(field_config(), field_styles(), field_palette())?;
        let mut app = App::new();
        app.add_plugins(MinimalPlugins)
            .add_plugins(AssetPlugin::default())
            .init_asset::<Mesh>()
            .init_asset::<Image>()
            .init_asset::<StandardMaterial>()
            .insert_resource(TimeUpdateStrategy::ManualDuration(Duration::from_millis(
                10,
            )))
            .init_resource::<Refusals>()
            .add_plugins(plugin)
            .add_systems(Update, collect.after(FieldSystems::Animate));
        app.finish();
        app.cleanup();
        Ok(app)
    }

    #[test]
    fn the_plugin_accepts_every_quiet_frame() -> TestResult {
        for mode in [ParticleMode::Groups, ParticleMode::People] {
            let picture = quiet(mode)?;
            let mut app = field_app()?;
            app.world_mut()
                .write_message(ShowPeriod(Box::new(picture.frame)));
            for _ in 0..3 {
                app.update();
            }
            let refused = &app.world().resource::<Refusals>().0;
            assert!(refused.is_empty(), "{mode:?}: {refused:?}");
            assert_eq!(app.world().resource::<FlowReport>().period, Some(1));
        }
        Ok(())
    }

    #[test]
    fn a_household_with_no_place_is_an_error_not_the_origin() {
        let standing = Standing {
            households: BTreeMap::new(),
            particles: Vec::new(),
            positions: Positions::new(),
        };
        assert!(matches!(
            standing.point(Party::Household(Household::ALL[0])),
            Err(FrameError::Edge(_))
        ));
        assert!(standing.point(Party::Treasury).is_ok());
    }

    #[test]
    fn the_library_plugin_runs_in_the_client() -> TestResult {
        let mut app = field_app()?;
        let frame = FieldFrame {
            period: 1,
            particles: vec![ParticleFrame {
                id: "p".to_owned(),
                at: Vec3::new(1.0, 0.1, -1.0),
                style: 0,
            }],
            flows: vec![Flow {
                stream: 0,
                from: Vec3::new(1.0, 0.1, -1.0),
                to: Vec3::new(4.0, 0.1, -1.0),
                amount: 3,
                hollow: false,
            }],
            ..FieldFrame::default()
        };
        app.world_mut().write_message(ShowPeriod(Box::new(frame)));
        for _ in 0..3 {
            app.update();
        }
        assert_eq!(app.world().resource::<Refusals>().0.len(), 0);
        assert_eq!(app.world().resource::<FlowReport>().period, Some(1));
        let mut ids = app.world_mut().query::<&ParticleId>();
        let found: Vec<String> = ids.iter(app.world()).map(|id| id.0.clone()).collect();
        assert_eq!(found, vec!["p".to_owned()]);
        Ok(())
    }

    #[test]
    fn the_styles_name_the_plans_units() {
        let styles = field_styles();
        assert_eq!(styles.streams.len(), 9);
        assert_eq!(styles.streams[0].unit.get(), HOURS_PER_MARK);
        assert!(STREAM_GOODS
            .iter()
            .all(|s| styles.streams[usize::from(*s)].unit.get() == UNITS_PER_MARK));
        assert!(STREAM_MONEY
            .iter()
            .all(|s| styles.streams[usize::from(*s)].unit.get() == MONEY_PER_MARK));
        assert_eq!(styles.particles.len(), 4);
        assert_eq!(styles.sets.len(), 3);
    }
}
