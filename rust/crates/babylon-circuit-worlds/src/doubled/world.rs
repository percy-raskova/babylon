//! Which doubled world opens: with or without public accounts, at which figures, and pushed how.
//!
//! The bench of the test economy measured two worlds, two scales and six pushes of the opening. They
//! are named here, so the bench has no world of its own and the scene's world is one of them.

use crate::doubled::figures::Figures;
use crate::{Household, Kind, Place, Places};
use babylon_material_circuit::AdjustmentRule;

/// Which of the bench's two worlds: no public account, or a treasury and a fund.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Economy {
    /// No treasury, no fund, no taxes: five household accounts a place.
    Plain,
    /// A treasury, a fund, their taxes and programs, and a supported household a place.
    Fund,
}

/// The figures of a set: a $1 price step and one period of outlay as opening cash (small), or a step of
/// 250 bps of the opening price, rounded down to the micro-unit, and two periods (national).
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Scale {
    /// A $1 step; each workplace opens with one period of its outlay.
    Small,
    /// A step of 250 bps of the opening price; each workplace opens with two periods of its outlay.
    National,
}

/// A change to the opening, made before the first period. The harvest is not here: it is a `Shock`.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum OpeningPush {
    /// P1: the owner household's cohort counts half its persons.
    LessDemand,
    /// P3: the shop opens with half its cash.
    LessMoney,
    /// P4: the clinic pays $11 an hour.
    HigherPay,
    /// P5: the fund's 16 tax rows at three quarters of their rate. Fund world, both places.
    LowerFundTaxes,
    /// P6: the power cut from the opening: the utility plans in batches of 10 hours, and `Shock::PowerCut`
    /// holds from period 1.
    PowerCut,
    /// P7: the owner household's cohort counts half again as many persons.
    MoreMouths,
}

/// A push and where it strikes.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Pushed {
    /// What changes.
    pub push: OpeningPush,
    /// Where.
    pub places: Places,
}

/// Everything that sets a doubled world before its first period.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct World {
    /// Which world.
    pub economy: Economy,
    /// Which figures.
    pub scale: Scale,
    /// The change to the opening, if any.
    pub pushed: Option<Pushed>,
    /// The rules the world opens with: `Runner::open_world` turns each on, in order, before the first step.
    pub rules: Vec<AdjustmentRule>,
}

/// Whether a choice of places includes the place.
const fn covers(places: Places, place: Place) -> bool {
    matches!(
        (places, place),
        (Places::Both, _) | (Places::A, Place::A) | (Places::B, Place::B)
    )
}

impl World {
    /// The scene's world: the fund world at the small figures, nothing pushed. `Runner::open` opens it.
    #[must_use]
    pub const fn scene() -> Self {
        Self {
            economy: Economy::Fund,
            scale: Scale::Small,
            pushed: None,
            rules: Vec::new(),
        }
    }

    /// The six rules in the order of `AdjustmentRule`, the restart with the periods of outlay of `scale`
    /// (1 period of outlay at the small figures, 2 at the national).
    #[must_use]
    pub const fn switches_at(scale: Scale) -> [AdjustmentRule; 6] {
        let outlay_periods = match scale {
            Scale::Small => 1,
            Scale::National => 2,
        };
        [
            AdjustmentRule::HiringWithinMeans,
            AdjustmentRule::SeekingInPlace,
            AdjustmentRule::StopWithoutPay,
            AdjustmentRule::RestingPrice,
            AdjustmentRule::OwnerRestart { outlay_periods },
            AdjustmentRule::GoodsStepDown,
        ]
    }

    /// `switches_at(self.scale)`: the six rules of this world.
    #[must_use]
    pub const fn switches(&self) -> [AdjustmentRule; 6] {
        Self::switches_at(self.scale)
    }

    /// The household accounts, in the engine's principal order: `Household::ALL` with the fund, the same
    /// without the two supported households in the plain world.
    #[must_use]
    pub fn households(&self) -> Vec<Household> {
        Household::ALL
            .iter()
            .copied()
            .filter(|h| match self.economy {
                Economy::Fund => true,
                Economy::Plain => !matches!(h, Household::Supported(_)),
            })
            .collect()
    }

    /// A household's persons at the opening without a push: plain workers 15/5/5/5 and owner 10; the fund
    /// world's are `Household::opening_persons`.
    #[must_use]
    pub const fn persons(&self, household: Household) -> u64 {
        match self.economy {
            Economy::Fund => household.opening_persons(),
            Economy::Plain => match household {
                Household::Workers(w) => match w.kind {
                    Kind::Utility => 15,
                    Kind::Farm | Kind::Clinic | Kind::Shop => 5,
                },
                Household::Owner(_) => 10,
                Household::Supported(_) => 0,
            },
        }
    }

    /// A cohort's persons after the push (P1 halves the owner's, P7 takes half again); stocks, purchases,
    /// cash and the hours stay those of `persons`.
    #[must_use]
    pub const fn cohort_persons(&self, household: Household) -> u64 {
        let persons = self.persons(household);
        match (household, self.pushed) {
            (Household::Owner(place), Some(Pushed { push, places })) if covers(places, place) => {
                match push {
                    OpeningPush::LessDemand => persons / 2,
                    OpeningPush::MoreMouths => persons + persons / 2,
                    OpeningPush::LessMoney
                    | OpeningPush::HigherPay
                    | OpeningPush::LowerFundTaxes
                    | OpeningPush::PowerCut => persons,
                }
            }
            _ => persons,
        }
    }

    /// Hours a person: 8 plain, 10 fund.
    #[must_use]
    pub const fn hours_per_person(&self) -> u64 {
        match self.economy {
            Economy::Plain => 8,
            Economy::Fund => 10,
        }
    }

    /// The catalog's figures of period 1: `Figures::OPENING`, or the power cut where it is pushed.
    #[must_use]
    pub fn opening_figures(&self) -> Figures {
        let mut figures = Figures::OPENING;
        for place in Place::ALL {
            if self.is_pushed(OpeningPush::PowerCut, place) {
                figures.utility_hours_per_batch[place.index()] = 10;
                figures.utility_output_per_batch[place.index()] = 9;
            }
        }
        figures
    }

    /// Whether this push strikes the place.
    #[must_use]
    pub const fn is_pushed(&self, push: OpeningPush, place: Place) -> bool {
        match self.pushed {
            Some(pushed) => {
                covers(pushed.places, place)
                    && matches!(
                        (pushed.push, push),
                        (OpeningPush::LessDemand, OpeningPush::LessDemand)
                            | (OpeningPush::LessMoney, OpeningPush::LessMoney)
                            | (OpeningPush::HigherPay, OpeningPush::HigherPay)
                            | (OpeningPush::LowerFundTaxes, OpeningPush::LowerFundTaxes)
                            | (OpeningPush::PowerCut, OpeningPush::PowerCut)
                            | (OpeningPush::MoreMouths, OpeningPush::MoreMouths)
                    )
            }
            None => false,
        }
    }
}
