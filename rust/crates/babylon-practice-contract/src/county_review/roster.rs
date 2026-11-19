//! The household roster: the opening placement, the bands and the period roll-forward.
//!
//! Every step follows Appendix D.3 of the County Review design. Splits are exact, ties are settled
//! by the order of the answers and never by an identifier, and no rule reads the average of a
//! group.
use std::collections::BTreeMap;

use super::split;
use super::split::Ties;
use super::types::{
    Band, BandCount, CountyPeriodFacts, CountyReviewConfig, CountyReviewError, CrewPeriodFacts,
    GroupKind, GroupPeriodFacts, PositionKey, Roster, RosterGroup, RosterRow,
    COUNTY_REVIEW_MAX_ROWS, COUNTY_REVIEW_SCHEMA_VERSION,
};

/// The people a crew has at the opening.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct OpeningCrew {
    /// Index of the crew in the config.
    pub crew: u32,
    /// People at work.
    pub at_work: u64,
    /// People looking for work.
    pub seeking: u64,
}

/// One line of the opening placement, before bands are given.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct PlacedRow {
    /// Index of the group.
    pub group: u32,
    /// Index of the crew, or none.
    pub crew: Option<u32>,
    /// People at work in each household.
    pub at_work: u16,
    /// People looking for work in each household.
    pub seeking: u16,
    /// Units each household holds.
    pub units: u16,
    /// Households with these figures.
    pub households: u64,
}

/// The declared placement of hires, layoffs and departures, or one of its other bounds
/// (design 7.2). Production code passes `Declared`.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Placement {
    /// Households that treat the step alike are taken in proportion.
    Declared,
    /// Households that hold a unit are taken before those that hold none.
    HoldersFirst,
    /// Households that hold a unit are taken after those that hold none.
    HoldersLast,
}

/// Households of one position, and the reached among them.
type Table = BTreeMap<PositionKey, (u64, u64)>;

fn checked_add(a: u64, b: u64) -> Result<u64, CountyReviewError> {
    a.checked_add(b).ok_or(CountyReviewError::Arithmetic)
}

fn checked_sub(a: u64, b: u64) -> Result<u64, CountyReviewError> {
    a.checked_sub(b).ok_or(CountyReviewError::Arithmetic)
}

fn to_u16(value: u64) -> Result<u16, CountyReviewError> {
    u16::try_from(value).map_err(|_| CountyReviewError::Arithmetic)
}

fn index_u32(index: usize) -> Result<u32, CountyReviewError> {
    u32::try_from(index).map_err(|_| CountyReviewError::Arithmetic)
}

fn checked_mul(a: u64, b: u64) -> Result<u64, CountyReviewError> {
    a.checked_mul(b).ok_or(CountyReviewError::Arithmetic)
}

fn sum_u64<I: Iterator<Item = u64>>(mut values: I) -> Result<u64, CountyReviewError> {
    values.try_fold(0_u64, checked_add)
}

fn sum_checked<I: Iterator<Item = Result<u64, CountyReviewError>>>(
    mut values: I,
) -> Result<u64, CountyReviewError> {
    values.try_fold(0_u64, |total, value| checked_add(total, value?))
}

/// Checks a configuration's shape.
///
/// # Errors
///
/// A named refusal for a wrong schema, a zero price, wage or session length, groups or crews that
/// are not sorted and unique, a crew with an unknown group or in a collective residence, and a
/// collective residence that holds households.
pub fn validate_county_review_config(config: &CountyReviewConfig) -> Result<(), CountyReviewError> {
    if config.schema_version != COUNTY_REVIEW_SCHEMA_VERSION {
        return Err(CountyReviewError::UnsupportedSchema);
    }
    if config.unit_price_micros <= 0 || config.going_wage_micros <= 0 || config.session_hours == 0 {
        return Err(CountyReviewError::InvalidTerms);
    }
    if config.groups.len() > COUNTY_REVIEW_MAX_ROWS || config.crews.len() > COUNTY_REVIEW_MAX_ROWS {
        return Err(CountyReviewError::SizeLimit);
    }
    if !config
        .groups
        .windows(2)
        .all(|pair| pair[0].group_id < pair[1].group_id)
    {
        return Err(CountyReviewError::GroupsNotCanonical);
    }
    if !config
        .crews
        .windows(2)
        .all(|pair| pair[0].crew_id < pair[1].crew_id)
    {
        return Err(CountyReviewError::CrewsNotCanonical);
    }
    for crew in &config.crews {
        let group = usize::try_from(crew.group)
            .ok()
            .and_then(|index| config.groups.get(index))
            .ok_or(CountyReviewError::UnknownGroup)?;
        if group.kind == GroupKind::CollectiveResidence {
            return Err(CountyReviewError::CrewInCollectiveResidence);
        }
    }
    if config
        .groups
        .iter()
        .any(|g| g.kind == GroupKind::CollectiveResidence && g.opening_households != 0)
    {
        return Err(CountyReviewError::CollectiveResidenceWithHouseholds);
    }
    Ok(())
}

/// Collects the opening crews by group, each group's crews in crew order, skipping crews with
/// nobody in the labor force.
fn crews_by_group(
    config: &CountyReviewConfig,
    crews: &[OpeningCrew],
) -> Result<Vec<Vec<OpeningCrew>>, CountyReviewError> {
    let mut seen: BTreeMap<u32, OpeningCrew> = BTreeMap::new();
    for crew in crews {
        if seen.insert(crew.crew, *crew).is_some() {
            return Err(CountyReviewError::DuplicateCrew);
        }
    }
    let mut by_group: Vec<Vec<OpeningCrew>> = vec![Vec::new(); config.groups.len()];
    for (index, crew) in seen {
        let configured = usize::try_from(index)
            .ok()
            .and_then(|i| config.crews.get(i))
            .ok_or(CountyReviewError::UnknownCrew)?;
        if checked_add(crew.at_work, crew.seeking)? == 0 {
            continue;
        }
        let slot = usize::try_from(configured.group)
            .ok()
            .and_then(|g| by_group.get_mut(g))
            .ok_or(CountyReviewError::UnknownGroup)?;
        slot.push(crew);
    }
    Ok(by_group)
}

fn placed_row(
    group: u32,
    crew: Option<u32>,
    (at_work, seeking): (u64, u64),
    households: u64,
) -> Result<Option<PlacedRow>, CountyReviewError> {
    if households == 0 {
        return Ok(None);
    }
    Ok(Some(PlacedRow {
        group,
        crew,
        at_work: to_u16(at_work)?,
        seeking: to_u16(seeking)?,
        units: to_u16(seeking)?,
        households,
    }))
}

/// Places a group whose people in the labor force each have a household.
fn place_one_each(
    group: u32,
    households: u64,
    crews: &[OpeningCrew],
    out: &mut Vec<PlacedRow>,
) -> Result<(), CountyReviewError> {
    let mut placed = 0_u64;
    for crew in crews {
        out.extend(placed_row(group, Some(crew.crew), (1, 0), crew.at_work)?);
        out.extend(placed_row(group, Some(crew.crew), (0, 1), crew.seeking)?);
        placed = checked_add(placed, checked_add(crew.at_work, crew.seeking)?)?;
    }
    out.extend(placed_row(
        group,
        None,
        (0, 0),
        checked_sub(households, placed)?,
    )?);
    Ok(())
}

/// Places a crew's people over `h` households: work spread evenly, job-seekers to the households
/// with the fewest at work first, and a unit for each job-seeker.
fn place_crew(
    group: u32,
    crew: &OpeningCrew,
    h: u64,
    out: &mut Vec<PlacedRow>,
) -> Result<(), CountyReviewError> {
    let (q, r) = (crew.at_work / h, crew.at_work % h);
    let (sq, sr) = (crew.seeking / h, crew.seeking % h);
    let fewer = checked_sub(h, r)?;
    let fewer_with_extra = sr.min(fewer);
    let more_with_extra = checked_sub(sr, fewer_with_extra)?;
    let parts = [
        (Some(q), sq.checked_add(1), fewer_with_extra),
        (Some(q), Some(sq), checked_sub(fewer, fewer_with_extra)?),
        (q.checked_add(1), sq.checked_add(1), more_with_extra),
        (q.checked_add(1), Some(sq), checked_sub(r, more_with_extra)?),
    ];
    for (at_work, seeking, households) in parts {
        if households == 0 {
            continue;
        }
        let at_work = at_work.ok_or(CountyReviewError::Arithmetic)?;
        let seeking = seeking.ok_or(CountyReviewError::Arithmetic)?;
        out.extend(placed_row(
            group,
            Some(crew.crew),
            (at_work, seeking),
            households,
        )?);
    }
    Ok(())
}

/// Places a group with at least as many people in the labor force as households.
fn place_shared(
    group: u32,
    households: u64,
    crews: &[OpeningCrew],
    out: &mut Vec<PlacedRow>,
) -> Result<(), CountyReviewError> {
    let count = u64::try_from(crews.len()).map_err(|_| CountyReviewError::Arithmetic)?;
    if count > households {
        return Err(CountyReviewError::MoreCrewsThanHouseholds);
    }
    let weights = crews
        .iter()
        .map(|c| checked_sub(checked_add(c.at_work, c.seeking)?, 1))
        .collect::<Result<Vec<u64>, CountyReviewError>>()?;
    let split = split::apportion(checked_sub(households, count)?, &weights, Ties::Withhold)?;
    for (crew, share) in crews.iter().zip(&split.shares) {
        place_crew(group, crew, checked_add(1, *share)?, out)?;
    }
    out.extend(placed_row(group, None, (0, 0), split.withheld)?);
    Ok(())
}

fn place_group(
    group: u32,
    households: u64,
    crews: &[OpeningCrew],
) -> Result<Vec<PlacedRow>, CountyReviewError> {
    let mut out = Vec::new();
    let people = sum_checked(crews.iter().map(|c| checked_add(c.at_work, c.seeking)))?;
    if people < households {
        place_one_each(group, households, crews, &mut out)?;
    } else {
        place_shared(group, households, crews, &mut out)?;
    }
    Ok(out)
}

fn placed_units(rows: &[PlacedRow]) -> Result<u64, CountyReviewError> {
    sum_checked(
        rows.iter()
            .map(|r| checked_mul(u64::from(r.units), r.households)),
    )
}

/// Places every ordinary group's households at the opening, before bands.
///
/// # Errors
///
/// `MoreCrewsThanHouseholds` when a group has more crews with people than households,
/// `RollMismatch` when the units placed in a group differ from its roll, and the configuration's
/// own refusals.
pub fn opening_placement(
    config: &CountyReviewConfig,
    crews: &[OpeningCrew],
) -> Result<Vec<PlacedRow>, CountyReviewError> {
    validate_county_review_config(config)?;
    let by_group = crews_by_group(config, crews)?;
    let mut placed = Vec::new();
    for (index, (group, group_crews)) in config.groups.iter().zip(&by_group).enumerate() {
        if group.kind != GroupKind::Ordinary {
            continue;
        }
        let rows = place_group(index_u32(index)?, group.opening_households, group_crews)?;
        if placed_units(&rows)? != group.roll_units {
            return Err(CountyReviewError::RollMismatch);
        }
        placed.extend(rows);
    }
    placed.sort_by_key(|r| (r.group, r.crew, r.at_work, r.seeking, r.units));
    Ok(placed)
}

/// Whether a placed row belongs to a group with ownership income.
fn is_owner_row(config: &CountyReviewConfig, row: &PlacedRow) -> bool {
    usize::try_from(row.group)
        .ok()
        .and_then(|g| config.groups.get(g))
        .is_some_and(|g| g.has_ownership_income)
}

/// Takes the top 1% from the owners' households with nobody in the labor force.
fn take_top_band(
    config: &CountyReviewConfig,
    placed: &[PlacedRow],
    needed: u64,
    taken: &mut [u64],
) -> Result<(), CountyReviewError> {
    let candidates: Vec<usize> = (0..placed.len())
        .filter(|i| is_owner_row(config, &placed[*i]) && placed[*i].crew.is_none())
        .collect();
    let weights: Vec<u64> = candidates.iter().map(|i| placed[*i].households).collect();
    if sum_u64(weights.iter().copied())? < needed {
        return Err(CountyReviewError::TopBandInLaborForce);
    }
    let split = split::apportion(needed, &weights, Ties::Withhold)?;
    for (index, share) in candidates.iter().zip(&split.shares) {
        taken[*index] = *share;
    }
    Ok(())
}

/// Takes the next 40% from the other groups' households in the labor force, most people at work
/// first, whole levels while they fit.
fn take_wage_band(
    config: &CountyReviewConfig,
    placed: &[PlacedRow],
    needed: u64,
    taken: &mut [u64],
) -> Result<(), CountyReviewError> {
    let mut candidates: Vec<usize> = (0..placed.len())
        .filter(|i| !is_owner_row(config, &placed[*i]) && placed[*i].crew.is_some())
        .collect();
    candidates.sort_by_key(|i| std::cmp::Reverse(placed[*i].at_work));
    let mut still = needed;
    let mut start = 0;
    while still > 0 && start < candidates.len() {
        let level_work = placed[candidates[start]].at_work;
        let end = candidates[start..]
            .iter()
            .position(|i| placed[*i].at_work != level_work)
            .map_or(candidates.len(), |offset| start + offset);
        let level = &candidates[start..end];
        let weights: Vec<u64> = level.iter().map(|i| placed[*i].households).collect();
        let level_households = sum_u64(weights.iter().copied())?;
        if level_households <= still {
            for (index, weight) in level.iter().zip(&weights) {
                taken[*index] = *weight;
            }
            still = checked_sub(still, level_households)?;
        } else {
            let split = split::apportion(still, &weights, Ties::Withhold)?;
            for (index, share) in level.iter().zip(&split.shares) {
                taken[*index] = *share;
            }
            still = 0;
        }
        start = end;
    }
    if still > 0 {
        return Err(CountyReviewError::WageBandOutsideLaborForce);
    }
    Ok(())
}

/// Gives every placed household its band. `taken[i]` is the households of row `i` that take the
/// upper band of their two: the top 1% for owners and the next 40% for the rest.
fn band_rows(
    config: &CountyReviewConfig,
    placed: &[PlacedRow],
) -> Result<Vec<RosterRow>, CountyReviewError> {
    let (mut owners, mut others) = (0_u64, 0_u64);
    for group in &config.groups {
        if group.kind != GroupKind::Ordinary {
            continue;
        }
        let total = if group.has_ownership_income {
            &mut owners
        } else {
            &mut others
        };
        *total = checked_add(*total, group.opening_households)?;
    }
    let top_needed = split::ratio_split(owners, 1, 9)?.0;
    let wage_needed = split::ratio_split(others, 4, 5)?.0;
    let mut taken = vec![0_u64; placed.len()];
    take_top_band(config, placed, top_needed, &mut taken)?;
    take_wage_band(config, placed, wage_needed, &mut taken)?;
    let mut rows = Vec::new();
    for (row, upper) in placed.iter().zip(&taken) {
        let (upper_band, lower_band) = if is_owner_row(config, row) {
            (Band::Top1, Band::Next9)
        } else {
            (Band::Next40, Band::Bottom50)
        };
        for (band, households) in [
            (upper_band, *upper),
            (lower_band, checked_sub(row.households, *upper)?),
        ] {
            if households > 0 {
                rows.push(RosterRow {
                    key: PositionKey {
                        group: row.group,
                        band,
                        crew: row.crew,
                        at_work: row.at_work,
                        seeking: row.seeking,
                        units: row.units,
                    },
                    households,
                    reached: 0,
                });
            }
        }
    }
    rows.sort_by_key(|r| r.key);
    Ok(rows)
}

/// Places the opening reach on each group's rows.
fn place_opening_reach(
    config: &CountyReviewConfig,
    rows: &mut [RosterRow],
    opening_reach: &[(u32, u64)],
) -> Result<(), CountyReviewError> {
    let mut per_group: BTreeMap<u32, u64> = BTreeMap::new();
    for (group, reached) in opening_reach {
        let total = per_group.entry(*group).or_insert(0);
        *total = checked_add(*total, *reached)?;
    }
    for (group, reached) in per_group {
        let configured = usize::try_from(group)
            .ok()
            .and_then(|g| config.groups.get(g))
            .ok_or(CountyReviewError::UnknownGroup)?;
        if reached == 0 {
            continue;
        }
        if configured.kind != GroupKind::Ordinary {
            return Err(CountyReviewError::OpeningReachNotPlaceable);
        }
        let indices: Vec<usize> = (0..rows.len())
            .filter(|i| rows[*i].key.group == group)
            .collect();
        let weights: Vec<u64> = indices.iter().map(|i| rows[*i].households).collect();
        let split = split::apportion(reached, &weights, Ties::Withhold)
            .map_err(|_| CountyReviewError::OpeningReachNotPlaceable)?;
        if split.withheld > 0 {
            return Err(CountyReviewError::OpeningReachNotPlaceable);
        }
        for (index, share) in indices.iter().zip(&split.shares) {
            rows[*index].reached = *share;
        }
    }
    Ok(())
}

/// Builds the opening roster: the placement, the bands of the rule of thirds, and the reach.
///
/// `opening_reach` lists `(group, households reached)`.
///
/// # Errors
///
/// The placement's refusals, `TopBandInLaborForce` when the owners have too few households with
/// nobody in the labor force, `WageBandOutsideLaborForce` when the other households have too few in
/// the labor force, and `OpeningReachNotPlaceable` when reach cannot be put on a group's households.
pub fn opening_roster(
    config: &CountyReviewConfig,
    crews: &[OpeningCrew],
    opening_reach: &[(u32, u64)],
) -> Result<Roster, CountyReviewError> {
    let placed = opening_placement(config, crews)?;
    let mut rows = band_rows(config, &placed)?;
    place_opening_reach(config, &mut rows, opening_reach)?;
    let groups = config
        .groups
        .iter()
        .map(|g| RosterGroup {
            households: if g.kind == GroupKind::Ordinary {
                g.opening_households
            } else {
                0
            },
            departed_units: 0,
        })
        .collect();
    Ok(Roster {
        period: 0,
        groups,
        rows,
    })
}

fn check_row(config: &CountyReviewConfig, row: &RosterRow) -> Result<(), CountyReviewError> {
    let key = &row.key;
    if row.households == 0 {
        return Err(CountyReviewError::EmptyRosterRow);
    }
    if row.reached > row.households {
        return Err(CountyReviewError::ReachedExceedsHouseholds);
    }
    let group = usize::try_from(key.group)
        .ok()
        .and_then(|g| config.groups.get(g))
        .ok_or(CountyReviewError::UnknownGroup)?;
    if group.kind != GroupKind::Ordinary {
        return Err(CountyReviewError::CollectiveResidenceWithHouseholds);
    }
    match key.crew {
        None if key.at_work != 0 || key.seeking != 0 => {
            Err(CountyReviewError::CrewlessRowInLaborForce)
        }
        None => Ok(()),
        Some(_) if key.band == Band::Top1 => Err(CountyReviewError::TopBandWithCrew),
        Some(crew) => {
            let configured = usize::try_from(crew)
                .ok()
                .and_then(|c| config.crews.get(c))
                .ok_or(CountyReviewError::UnknownCrew)?;
            if configured.group == key.group {
                Ok(())
            } else {
                Err(CountyReviewError::CrewGroupMismatch)
            }
        }
    }
}

/// Checks a roster against the configuration: sorted unique rows, no empty row, indices in range,
/// the bands' and crews' rules, and each group's rows adding to its households. Totals of people
/// and units must fit in a `u64`, so the roster's counting methods are exact.
///
/// # Errors
///
/// The first refusal found, by name.
pub fn validate_roster(
    config: &CountyReviewConfig,
    roster: &Roster,
) -> Result<(), CountyReviewError> {
    if roster.groups.len() != config.groups.len() {
        return Err(CountyReviewError::RosterShape);
    }
    if roster.rows.len() > COUNTY_REVIEW_MAX_ROWS {
        return Err(CountyReviewError::SizeLimit);
    }
    if !roster.rows.windows(2).all(|pair| pair[0].key < pair[1].key) {
        return Err(CountyReviewError::RosterNotCanonical);
    }
    let mut per_group = vec![0_u64; config.groups.len()];
    let (mut at_work, mut seeking, mut units) = (0_u128, 0_u128, 0_u128);
    for row in &roster.rows {
        check_row(config, row)?;
        let slot = usize::try_from(row.key.group)
            .ok()
            .and_then(|g| per_group.get_mut(g))
            .ok_or(CountyReviewError::UnknownGroup)?;
        *slot = checked_add(*slot, row.households)?;
        let households = u128::from(row.households);
        at_work += u128::from(row.key.at_work) * households;
        seeking += u128::from(row.key.seeking) * households;
        units += u128::from(row.key.units) * households;
    }
    for total in [at_work, seeking, units] {
        u64::try_from(total).map_err(|_| CountyReviewError::Arithmetic)?;
    }
    for (rostered, summed) in roster.groups.iter().zip(&per_group) {
        if rostered.households != *summed {
            return Err(CountyReviewError::GroupHouseholdsMismatch);
        }
    }
    Ok(())
}

impl Roster {
    /// People at work in a crew: `at_work` times households over the crew's rows.
    ///
    /// Exact for a roster that passed `validate_roster`; saturates otherwise.
    #[must_use]
    pub fn crew_at_work(&self, crew: u32) -> u64 {
        self.sum_over(|k| k.crew == Some(crew), |k| k.at_work)
    }

    /// People looking for work in a crew.
    ///
    /// Exact for a roster that passed `validate_roster`; saturates otherwise.
    #[must_use]
    pub fn crew_seeking(&self, crew: u32) -> u64 {
        self.sum_over(|k| k.crew == Some(crew), |k| k.seeking)
    }

    /// Units held in a group: `units` times households over the group's rows.
    ///
    /// Exact for a roster that passed `validate_roster`; saturates otherwise.
    #[must_use]
    pub fn group_units(&self, group: u32) -> u64 {
        self.sum_over(|k| k.group == group, |k| k.units)
    }

    fn sum_over(
        &self,
        keep: impl Fn(&PositionKey) -> bool,
        figure: impl Fn(&PositionKey) -> u16,
    ) -> u64 {
        self.rows
            .iter()
            .filter(|row| keep(&row.key))
            .fold(0_u64, |total, row| {
                total.saturating_add(u64::from(figure(&row.key)).saturating_mul(row.households))
            })
    }

    /// Who works in each band, top first. A household has work when someone is at work, is only
    /// seeking when nobody is at work and someone is looking, and is otherwise outside the labor
    /// force.
    ///
    /// Exact for a roster that passed `validate_roster`; saturates otherwise.
    #[must_use]
    pub fn band_counts(&self) -> Vec<BandCount> {
        [Band::Top1, Band::Next9, Band::Next40, Band::Bottom50]
            .into_iter()
            .map(|band| self.count_band(band))
            .collect()
    }

    fn count_band(&self, band: Band) -> BandCount {
        let mut count = BandCount {
            band,
            households: 0,
            with_work: 0,
            seeking_only: 0,
            outside_labor_force: 0,
            people_at_work: 0,
            people_seeking: 0,
            units: 0,
        };
        for row in self.rows.iter().filter(|r| r.key.band == band) {
            let (key, households) = (&row.key, row.households);
            count.households = count.households.saturating_add(households);
            let kind = if key.at_work >= 1 {
                &mut count.with_work
            } else if key.seeking >= 1 {
                &mut count.seeking_only
            } else {
                &mut count.outside_labor_force
            };
            *kind = kind.saturating_add(households);
            let person_total =
                |per_household: u16| u64::from(per_household).saturating_mul(households);
            count.people_at_work = count
                .people_at_work
                .saturating_add(person_total(key.at_work));
            count.people_seeking = count
                .people_seeking
                .saturating_add(person_total(key.seeking));
            count.units = count.units.saturating_add(person_total(key.units));
        }
        count
    }
}

/// A step of the period: who is taken, from where, and what they become.
#[derive(Debug, Clone, Copy)]
enum Move {
    LeftAtWork,
    LeftSeeking,
    Hire,
    Separation,
}

impl Move {
    fn eligible(self, key: &PositionKey) -> bool {
        match self {
            Move::LeftAtWork | Move::Separation => key.at_work >= 1,
            Move::LeftSeeking | Move::Hire => key.seeking >= 1,
        }
    }

    /// The level a household stands at; the lowest rank is taken first.
    fn rank(self, key: &PositionKey) -> i32 {
        match self {
            Move::LeftAtWork | Move::Separation => -i32::from(key.at_work),
            Move::LeftSeeking => -i32::from(key.seeking),
            Move::Hire => i32::from(key.at_work),
        }
    }

    fn result(self, key: &PositionKey) -> Result<PositionKey, CountyReviewError> {
        let down = |v: u16| v.checked_sub(1).ok_or(CountyReviewError::Arithmetic);
        let up = |v: u16| v.checked_add(1).ok_or(CountyReviewError::Arithmetic);
        let mut moved = *key;
        match self {
            Move::LeftAtWork => moved.at_work = down(key.at_work)?,
            Move::LeftSeeking => moved.seeking = down(key.seeking)?,
            Move::Hire => {
                moved.at_work = up(key.at_work)?;
                moved.seeking = down(key.seeking)?;
            }
            Move::Separation => {
                moved.at_work = down(key.at_work)?;
                moved.seeking = up(key.seeking)?;
            }
        }
        Ok(moved)
    }
}

fn add_households(
    table: &mut Table,
    key: PositionKey,
    households: u64,
    reached: u64,
) -> Result<(), CountyReviewError> {
    let entry = table.entry(key).or_insert((0, 0));
    entry.0 = checked_add(entry.0, households)?;
    entry.1 = checked_add(entry.1, reached)?;
    Ok(())
}

/// How many of `count` households taken from a row are reached: unreached and reached are taken in
/// proportion, an exact tie going to the unreached.
fn reached_share(households: u64, reached: u64, count: u64) -> Result<u64, CountyReviewError> {
    let split = split::apportion(
        count,
        &[checked_sub(households, reached)?, reached],
        Ties::InOrder,
    )?;
    split
        .shares
        .get(1)
        .copied()
        .ok_or(CountyReviewError::Arithmetic)
}

/// Moves `count` households of one row to `target`, unreached and reached in proportion.
fn move_households(
    table: &mut Table,
    key: PositionKey,
    target: PositionKey,
    count: u64,
) -> Result<(), CountyReviewError> {
    if count == 0 {
        return Ok(());
    }
    let (households, reached) = *table.get(&key).ok_or(CountyReviewError::Arithmetic)?;
    let moved_reached = reached_share(households, reached, count)?;
    let remaining = checked_sub(households, count)?;
    if remaining == 0 {
        table.remove(&key);
    } else {
        table.insert(key, (remaining, checked_sub(reached, moved_reached)?));
    }
    add_households(table, target, count, moved_reached)
}

/// The next level to take from: the rows at the lowest rank, in the order of their answers.
fn next_level(table: &Table, step: Move) -> Option<Vec<PositionKey>> {
    let best = table
        .keys()
        .filter(|k| step.eligible(k))
        .map(|k| step.rank(k))
        .min()?;
    let mut keys: Vec<PositionKey> = table
        .keys()
        .filter(|k| step.eligible(k) && step.rank(k) == best)
        .copied()
        .collect();
    keys.sort_by_key(|k| (k.units, k.seeking, k.at_work, k.band, *k));
    Some(keys)
}

/// Splits a level into the groups that are taken one after the other.
fn tiers(level: Vec<PositionKey>, placement: Placement) -> Vec<Vec<PositionKey>> {
    let (holders, others): (Vec<PositionKey>, Vec<PositionKey>) =
        level.iter().partition(|k| k.units >= 1);
    let ordered = match placement {
        Placement::Declared => vec![level],
        Placement::HoldersFirst => vec![holders, others],
        Placement::HoldersLast => vec![others, holders],
    };
    ordered.into_iter().filter(|t| !t.is_empty()).collect()
}

/// Takes up to `n` households from one level and returns how many are still to take.
fn take_level(
    table: &mut Table,
    level: Vec<PositionKey>,
    n: u64,
    step: Move,
    placement: Placement,
) -> Result<u64, CountyReviewError> {
    let mut remaining = n;
    for tier in tiers(level, placement) {
        if remaining == 0 {
            break;
        }
        let weights: Vec<u64> = tier
            .iter()
            .map(|k| table.get(k).map_or(0, |entry| entry.0))
            .collect();
        let tier_households = sum_u64(weights.iter().copied())?;
        let shares = if tier_households <= remaining {
            weights
        } else {
            split::apportion(remaining, &weights, Ties::InOrder)?.shares
        };
        for (key, share) in tier.iter().zip(&shares) {
            move_households(table, *key, step.result(key)?, *share)?;
        }
        remaining = checked_sub(remaining, sum_u64(shares.iter().copied())?)?;
    }
    Ok(remaining)
}

/// Applies one step to `people` persons, one household at a time, level by level.
fn apply_step(
    table: &mut Table,
    people: u64,
    step: Move,
    placement: Placement,
) -> Result<(), CountyReviewError> {
    let mut remaining = people;
    while remaining > 0 {
        let level = next_level(table, step).ok_or(CountyReviewError::RosterEngineMismatch)?;
        remaining = take_level(table, level, remaining, step, placement)?;
    }
    Ok(())
}

fn table_sum(
    table: &Table,
    figure: impl Fn(&PositionKey) -> u16,
) -> Result<u64, CountyReviewError> {
    sum_checked(
        table
            .iter()
            .map(|(k, v)| checked_mul(u64::from(figure(k)), v.0)),
    )
}

/// Rolls one crew's rows through the period. Rows left with nobody in the labor force move to
/// `crewless`.
fn roll_crew(
    table: &mut Table,
    crewless: &mut Table,
    facts: &CrewPeriodFacts,
    placement: Placement,
) -> Result<(), CountyReviewError> {
    if table_sum(table, |k| k.at_work)? != facts.opening_at_work
        || table_sum(table, |k| k.seeking)? != facts.opening_seeking
    {
        return Err(CountyReviewError::RosterEngineMismatch);
    }
    apply_step(table, facts.left_at_work, Move::LeftAtWork, placement)?;
    apply_step(table, facts.left_seeking, Move::LeftSeeking, placement)?;
    apply_step(table, facts.hires, Move::Hire, placement)?;
    apply_step(table, facts.separations, Move::Separation, placement)?;
    if table_sum(table, |k| k.at_work)? != facts.closing_at_work
        || table_sum(table, |k| k.seeking)? != facts.closing_seeking
    {
        return Err(CountyReviewError::RosterEngineMismatch);
    }
    let out_of_work: Vec<PositionKey> = table
        .keys()
        .filter(|k| k.at_work == 0 && k.seeking == 0)
        .copied()
        .collect();
    for key in out_of_work {
        let (households, reached) = table.remove(&key).ok_or(CountyReviewError::Arithmetic)?;
        add_households(
            crewless,
            PositionKey { crew: None, ..key },
            households,
            reached,
        )?;
    }
    Ok(())
}

/// Lowers a group's households by taking those with nobody in the labor force, in proportion.
fn shrink_group(
    crewless: &mut Table,
    group_index: u32,
    group: &mut RosterGroup,
    facts: &GroupPeriodFacts,
) -> Result<(), CountyReviewError> {
    if facts.closing_households > group.households {
        return Err(CountyReviewError::RosterEngineMismatch);
    }
    let leaving = checked_sub(group.households, facts.closing_households)?;
    if leaving == 0 {
        return Ok(());
    }
    let mut keys: Vec<PositionKey> = crewless
        .keys()
        .filter(|k| k.group == group_index)
        .copied()
        .collect();
    keys.sort_by_key(|k| (k.units, k.band, *k));
    let weights: Vec<u64> = keys.iter().map(|k| crewless[k].0).collect();
    if sum_u64(weights.iter().copied())? < leaving {
        return Err(CountyReviewError::HouseholdsBelowLaborHouseholds);
    }
    let split = split::apportion(leaving, &weights, Ties::InOrder)?;
    for (key, share) in keys.iter().zip(&split.shares) {
        let (households, reached) = crewless[key];
        let left_reached = reached_share(households, reached, *share)?;
        let remaining = checked_sub(households, *share)?;
        if remaining == 0 {
            crewless.remove(key);
        } else {
            crewless.insert(*key, (remaining, checked_sub(reached, left_reached)?));
        }
        let departed = u64::from(key.units)
            .checked_mul(*share)
            .ok_or(CountyReviewError::Arithmetic)?;
        group.departed_units = checked_add(group.departed_units, departed)?;
    }
    group.households = facts.closing_households;
    Ok(())
}

pub(super) fn check_facts_shape(
    config: &CountyReviewConfig,
    facts: &CountyPeriodFacts,
) -> Result<(), CountyReviewError> {
    let crews_in_order = facts.crews.len() == config.crews.len()
        && facts
            .crews
            .iter()
            .enumerate()
            .all(|(i, f)| u32::try_from(i) == Ok(f.crew));
    let groups_in_order = facts.groups.len() == config.groups.len()
        && facts
            .groups
            .iter()
            .enumerate()
            .all(|(i, f)| u32::try_from(i) == Ok(f.group));
    if crews_in_order && groups_in_order {
        Ok(())
    } else {
        Err(CountyReviewError::FactsShape)
    }
}

/// Rolls the roster through one period of the engine's hires, layoffs and departures.
///
/// Equals `roll_forward_with(.., Placement::Declared)`.
///
/// # Errors
///
/// See `roll_forward_with`.
pub fn roll_forward(
    config: &CountyReviewConfig,
    roster: &Roster,
    facts: &CountyPeriodFacts,
) -> Result<Roster, CountyReviewError> {
    roll_forward_with(config, roster, facts, Placement::Declared)
}

/// Rolls the roster through one period with the given placement.
///
/// Each crew's roster sums must equal the engine's opening sums, and its closing sums must follow
/// from the period's changes. Households keep their bands, and a household that moves stays
/// reached or unreached.
///
/// # Errors
///
/// `RosterEngineMismatch` when the roster and the engine disagree, `FactsShape` when the facts do
/// not hold one entry for each crew and group, `HouseholdsBelowLaborHouseholds` when a group lost
/// more households than the ones with nobody in the labor force, and the roster's own refusals.
pub fn roll_forward_with(
    config: &CountyReviewConfig,
    roster: &Roster,
    facts: &CountyPeriodFacts,
    placement: Placement,
) -> Result<Roster, CountyReviewError> {
    validate_roster(config, roster)?;
    check_facts_shape(config, facts)?;
    let mut by_crew: Vec<Table> = vec![Table::new(); config.crews.len()];
    let mut crewless = Table::new();
    for row in &roster.rows {
        let table = match row.key.crew {
            Some(crew) => by_crew
                .get_mut(usize::try_from(crew).map_err(|_| CountyReviewError::UnknownCrew)?)
                .ok_or(CountyReviewError::UnknownCrew)?,
            None => &mut crewless,
        };
        add_households(table, row.key, row.households, row.reached)?;
    }
    for (table, crew_facts) in by_crew.iter_mut().zip(&facts.crews) {
        roll_crew(table, &mut crewless, crew_facts, placement)?;
    }
    let mut groups = roster.groups.clone();
    for ((index, group), group_facts) in groups.iter_mut().enumerate().zip(&facts.groups) {
        shrink_group(&mut crewless, index_u32(index)?, group, group_facts)?;
    }
    let mut merged = crewless;
    for table in by_crew {
        merged.extend(table);
    }
    let rolled = Roster {
        period: checked_add(roster.period, 1)?,
        groups,
        rows: merged
            .into_iter()
            .map(|(key, (households, reached))| RosterRow {
                key,
                households,
                reached,
            })
            .collect(),
    };
    validate_roster(config, &rolled)?;
    Ok(rolled)
}
