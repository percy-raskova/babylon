//! The 25 runs of a set: the doubled worlds of the restoring-forces rounds, each pushed one way.

use babylon_circuit_worlds::{Economy, Lasts, OpeningPush, Places, Pushed, Scale, Shock, World};
use babylon_material_circuit::AdjustmentRule;

/// The rules a set runs with. Task 1b has one; each rule task adds the next.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum Form {
    /// Rule A6 only: the engine as built, no new rule.
    A6,
    /// People look for work in their place (A14).
    Seek,
    /// A bound on hiring, with people looking for work in their place.
    Bound,
    /// No money, no work, with the bound and the seekers.
    Stop,
    /// A resting price, with the stop rule, the bound and the seekers.
    Rest,
    /// An owner restarts a stopped workplace, with the resting price, the stop rule, the bound and the seekers.
    Restart,
    /// A goods price steps down, with the six rules before it: the closest form.
    Down,
}

impl Form {
    /// The forms built so far.
    pub(crate) const ALL: [Self; 7] = [
        Self::A6,
        Self::Seek,
        Self::Bound,
        Self::Stop,
        Self::Rest,
        Self::Restart,
        Self::Down,
    ];

    /// The rules the form turns on, in the order of `AdjustmentRule`, taken from `World::switches_at(scale)`
    /// as each rule task adds its form. `A6` asks for none.
    pub(crate) fn rules(self, scale: Scale) -> Vec<AdjustmentRule> {
        let switches = World::switches_at(scale);
        match self {
            Self::A6 => switches.iter().take(0).copied().collect(),
            Self::Seek => vec![switches[1]],
            Self::Bound => vec![switches[0], switches[1]],
            Self::Stop => vec![switches[0], switches[1], switches[2]],
            Self::Rest => vec![switches[0], switches[1], switches[2], switches[3]],
            Self::Restart => vec![
                switches[0],
                switches[1],
                switches[2],
                switches[3],
                switches[4],
            ],
            Self::Down => switches.to_vec(),
        }
    }
}

/// One of the 25 runs: its file name, its world, and the shocks struck through `Runner::strike`
/// before the first step.
pub(crate) struct BenchRun {
    pub(crate) name: &'static str,
    pub(crate) world: World,
    pub(crate) strikes: Vec<(Shock, Places, Lasts)>,
}

/// How a run differs from the quiet world.
#[derive(Clone, Copy)]
enum Push {
    Opening(OpeningPush, Places),
    Harvest(Places, Lasts),
}

fn run(
    name: &'static str,
    economy: Economy,
    scale: Scale,
    rules: &[AdjustmentRule],
    push: Option<Push>,
) -> BenchRun {
    let (pushed, strikes) = match push {
        None => (None, Vec::new()),
        Some(Push::Opening(push, places)) => (Some(Pushed { push, places }), Vec::new()),
        Some(Push::Harvest(places, lasts)) => (None, vec![(Shock::HarvestFails, places, lasts)]),
    };
    BenchRun {
        name,
        world: World {
            economy,
            scale,
            pushed,
            rules: rules.to_vec(),
        },
        strikes,
    }
}

/// The pushes both worlds take, in the prototype's order, and the four of place A alone.
fn pushes() -> [(&'static str, &'static str, Push); 7] {
    [
        (
            "plain-P1",
            "fund-P1",
            Push::Opening(OpeningPush::LessDemand, Places::Both),
        ),
        (
            "plain-P2",
            "fund-P2",
            Push::Harvest(Places::Both, Lasts::UntilLifted),
        ),
        (
            "plain-P3",
            "fund-P3",
            Push::Opening(OpeningPush::LessMoney, Places::Both),
        ),
        (
            "plain-P4",
            "fund-P4",
            Push::Opening(OpeningPush::HigherPay, Places::Both),
        ),
        (
            "plain-P6",
            "fund-P6",
            Push::Opening(OpeningPush::PowerCut, Places::Both),
        ),
        (
            "plain-P7",
            "fund-P7",
            Push::Opening(OpeningPush::MoreMouths, Places::Both),
        ),
        (
            "plain-P8",
            "fund-P8",
            Push::Harvest(Places::Both, Lasts::TenPeriods),
        ),
    ]
}

fn one_place() -> [(&'static str, &'static str, Push); 4] {
    [
        (
            "plain-P2a",
            "fund-P2a",
            Push::Harvest(Places::A, Lasts::UntilLifted),
        ),
        (
            "plain-P4a",
            "fund-P4a",
            Push::Opening(OpeningPush::HigherPay, Places::A),
        ),
        (
            "plain-P6a",
            "fund-P6a",
            Push::Opening(OpeningPush::PowerCut, Places::A),
        ),
        (
            "plain-P8a",
            "fund-P8a",
            Push::Harvest(Places::A, Lasts::TenPeriods),
        ),
    ]
}

/// The 25 runs in the prototype's order: plain quiet, P1, P2, P3, P4, P6, P7, P8, P2a, P4a, P6a, P8a, then
/// fund quiet, P1, P2, P3, P4, P6, P7, P8, P5, P2a, P4a, P6a, P8a.
pub(crate) fn runs(form: Form, scale: Scale) -> Vec<BenchRun> {
    let rules = form.rules(scale);
    let mut out = vec![run("plain-quiet", Economy::Plain, scale, &rules, None)];
    for (plain, _, push) in pushes() {
        out.push(run(plain, Economy::Plain, scale, &rules, Some(push)));
    }
    for (plain, _, push) in one_place() {
        out.push(run(plain, Economy::Plain, scale, &rules, Some(push)));
    }
    out.push(run("fund-quiet", Economy::Fund, scale, &rules, None));
    for (_, fund, push) in pushes() {
        out.push(run(fund, Economy::Fund, scale, &rules, Some(push)));
    }
    out.push(run(
        "fund-P5",
        Economy::Fund,
        scale,
        &rules,
        Some(Push::Opening(OpeningPush::LowerFundTaxes, Places::Both)),
    ));
    for (_, fund, push) in one_place() {
        out.push(run(fund, Economy::Fund, scale, &rules, Some(push)));
    }
    out
}
