//! The names of the doubled world: its places, workplaces, households and goods, and the bytes
//! each one has in the engine. Every identity is 32 copies of one byte, as the prototype's were.

use crate::WorldError;
use babylon_kernel::economic_location::EconomicLocation;
use babylon_material_circuit::{
    CorridorId, FinalDemandPrincipalId, GoodId, ProcessId, PublicAccountId, RouteId, SiteId,
    StaffingMemberId, StaffingPoolId, UnitId,
};

/// One of the two places of the doubled world.
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub enum Place {
    A,
    B,
}

impl Place {
    pub const ALL: [Place; 2] = [Place::A, Place::B];

    #[must_use]
    pub const fn index(self) -> usize {
        match self {
            Self::A => 0,
            Self::B => 1,
        }
    }

    #[must_use]
    pub const fn label(self) -> &'static str {
        match self {
            Self::A => "Place A",
            Self::B => "Place B",
        }
    }
}

/// The four kinds of workplace of a place.
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub enum Kind {
    Utility,
    Farm,
    Clinic,
    Shop,
}

impl Kind {
    pub const ALL: [Kind; 4] = [Kind::Utility, Kind::Farm, Kind::Clinic, Kind::Shop];

    #[must_use]
    pub const fn index(self) -> usize {
        match self {
            Self::Utility => 0,
            Self::Farm => 1,
            Self::Clinic => 2,
            Self::Shop => 3,
        }
    }

    #[must_use]
    pub const fn label(self) -> &'static str {
        match self {
            Self::Utility => "utility",
            Self::Farm => "farm",
            Self::Clinic => "clinic",
            Self::Shop => "shop",
        }
    }
}

/// An identity byte from a small index of the world (at most 127).
#[expect(
    clippy::cast_possible_truncation,
    reason = "every index of this world is below 128, and a const fn cannot use try_from"
)]
const fn byte(index: usize) -> u8 {
    index as u8
}

const fn bytes(value: u8) -> [u8; 32] {
    [value; 32]
}

/// One workplace of one place.
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct Workplace {
    pub place: Place,
    pub kind: Kind,
}

impl Workplace {
    /// Place A's four in kind order, then place B's.
    pub const ALL: [Workplace; 8] = [
        Workplace {
            place: Place::A,
            kind: Kind::Utility,
        },
        Workplace {
            place: Place::A,
            kind: Kind::Farm,
        },
        Workplace {
            place: Place::A,
            kind: Kind::Clinic,
        },
        Workplace {
            place: Place::A,
            kind: Kind::Shop,
        },
        Workplace {
            place: Place::B,
            kind: Kind::Utility,
        },
        Workplace {
            place: Place::B,
            kind: Kind::Farm,
        },
        Workplace {
            place: Place::B,
            kind: Kind::Clinic,
        },
        Workplace {
            place: Place::B,
            kind: Kind::Shop,
        },
    ];

    /// Four a place, then the kind.
    #[must_use]
    pub const fn index(self) -> usize {
        4 * self.place.index() + self.kind.index()
    }

    /// The workplace whose site this is, or `None` for a site of no workplace.
    #[must_use]
    pub fn from_site(site: SiteId) -> Option<Workplace> {
        let first = site.as_bytes()[0];
        if site.as_bytes().iter().any(|&b| b != first) {
            return None;
        }
        let index = usize::from(first).checked_sub(1)?;
        Self::ALL.get(index).copied()
    }

    #[must_use]
    pub const fn site_id(self) -> SiteId {
        SiteId::from_bytes(bytes(byte(self.index() + 1)))
    }

    /// The process of a utility, farm or clinic; a shop has none.
    #[must_use]
    pub const fn process_id(self) -> Option<ProcessId> {
        match self.kind {
            Kind::Shop => None,
            _ => Some(ProcessId::from_bytes(bytes(byte(self.index() + 1)))),
        }
    }

    #[must_use]
    pub const fn pool_id(self) -> StaffingPoolId {
        StaffingPoolId::from_bytes(bytes(byte(self.index() + 1)))
    }

    #[must_use]
    pub const fn member_id(self) -> StaffingMemberId {
        StaffingMemberId::from_bytes(bytes(byte(self.index() + 1)))
    }

    /// The household of the people who work here.
    #[must_use]
    pub const fn workers(self) -> Household {
        Household::Workers(self)
    }

    /// The member of `home`'s household at this workplace: the workplace's own member when `home` is it, else
    /// byte `0x40 + 8 x home.index() + self.index()` (the prototype's `lend_member`).
    #[must_use]
    pub const fn pair_member_id(self, home: Workplace) -> StaffingMemberId {
        if home.index() == self.index() {
            self.member_id()
        } else {
            StaffingMemberId::from_bytes(bytes(byte(0x40 + 8 * home.index() + self.index())))
        }
    }

    /// Every ordered pair `(home, host)` of two workplaces of one place, home first by index.
    pub fn pairs() -> impl Iterator<Item = (Workplace, Workplace)> {
        Self::ALL.into_iter().flat_map(|home| {
            Self::ALL
                .into_iter()
                .filter(move |host| host.place == home.place && *host != home)
                .map(move |host| (home, host))
        })
    }

    #[must_use]
    pub fn label(self) -> String {
        format!("{} {}", self.place.label(), self.kind.label())
    }
}

/// One of the twelve household accounts.
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub enum Household {
    Workers(Workplace),
    Owner(Place),
    Supported(Place),
}

impl Household {
    /// In the engine's principal byte order: 11 to 18, then 20 to 23.
    pub const ALL: [Household; 12] = [
        Household::Workers(Workplace {
            place: Place::A,
            kind: Kind::Utility,
        }),
        Household::Workers(Workplace {
            place: Place::B,
            kind: Kind::Utility,
        }),
        Household::Workers(Workplace {
            place: Place::A,
            kind: Kind::Farm,
        }),
        Household::Workers(Workplace {
            place: Place::B,
            kind: Kind::Farm,
        }),
        Household::Workers(Workplace {
            place: Place::A,
            kind: Kind::Clinic,
        }),
        Household::Workers(Workplace {
            place: Place::B,
            kind: Kind::Clinic,
        }),
        Household::Workers(Workplace {
            place: Place::A,
            kind: Kind::Shop,
        }),
        Household::Workers(Workplace {
            place: Place::B,
            kind: Kind::Shop,
        }),
        Household::Owner(Place::A),
        Household::Owner(Place::B),
        Household::Supported(Place::A),
        Household::Supported(Place::B),
    ];

    /// Workers 11 + 2 kind + place (the two places' households of a kind sit side by side),
    /// owners 20 and 21, supported 22 and 23.
    #[must_use]
    pub const fn principal(self) -> FinalDemandPrincipalId {
        let value = match self {
            Self::Workers(w) => 11 + 2 * w.kind.index() + w.place.index(),
            Self::Owner(place) => 20 + place.index(),
            Self::Supported(place) => 22 + place.index(),
        };
        FinalDemandPrincipalId::from_bytes(bytes(byte(value)))
    }

    #[must_use]
    pub fn from_principal(id: FinalDemandPrincipalId) -> Option<Household> {
        let first = id.as_bytes()[0];
        if id.as_bytes().iter().any(|&b| b != first) {
            return None;
        }
        Self::ALL.iter().copied().find(|h| h.principal() == id)
    }

    #[must_use]
    pub const fn place(self) -> Place {
        match self {
            Self::Workers(w) => w.place,
            Self::Owner(place) | Self::Supported(place) => place,
        }
    }

    /// 12 utility workers, 4 of each other kind, 8 owners and 8 supported people a place.
    #[must_use]
    pub const fn opening_persons(self) -> u64 {
        match self {
            Self::Workers(w) => match w.kind {
                Kind::Utility => 12,
                Kind::Farm | Kind::Clinic | Kind::Shop => 4,
            },
            Self::Owner(_) | Self::Supported(_) => 8,
        }
    }

    #[must_use]
    pub fn label(self) -> String {
        match self {
            Self::Workers(w) => format!("{} workers", w.label()),
            Self::Owner(place) => format!("{} owners", place.label()),
            Self::Supported(place) => format!("{} supported", place.label()),
        }
    }
}

/// The three goods.
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub enum Good {
    Food,
    Power,
    Care,
}

impl Good {
    pub const ALL: [Good; 3] = [Good::Food, Good::Power, Good::Care];

    #[must_use]
    pub const fn good_id(self) -> GoodId {
        let value = match self {
            Self::Food => 1,
            Self::Power => 2,
            Self::Care => 3,
        };
        GoodId::from_bytes(bytes(value))
    }

    #[must_use]
    pub fn from_good(id: GoodId) -> Option<Good> {
        Self::ALL.iter().copied().find(|g| g.good_id() == id)
    }
}

/// The treasury's account.
#[must_use]
pub const fn treasury() -> PublicAccountId {
    PublicAccountId::from_bytes(bytes(30))
}

/// The fund's account.
#[must_use]
pub const fn fund() -> PublicAccountId {
    PublicAccountId::from_bytes(bytes(31))
}

/// The unit of every good.
#[must_use]
pub const fn goods_unit() -> UnitId {
    UnitId::from_bytes(bytes(1))
}

/// The unit of hours.
#[must_use]
pub const fn hours_unit() -> UnitId {
    UnitId::from_bytes(bytes(2))
}

/// The shop's supply route of a place: 2, then 6.
#[must_use]
pub const fn route(place: Place) -> RouteId {
    RouteId::from_bytes(bytes(byte(2 + 4 * place.index())))
}

/// The shop's handling corridor of a place: 4, then 8.
#[must_use]
pub const fn corridor(place: Place) -> CorridorId {
    CorridorId::from_bytes(bytes(byte(4 + 4 * place.index())))
}

/// The location both places carry in the engine's data.
///
/// # Errors
/// `WorldError::Location` when the authored text does not parse.
pub fn location() -> Result<EconomicLocation, WorldError> {
    "county:26163"
        .parse()
        .map_err(|_| WorldError::Location("county:26163".to_string()))
}
