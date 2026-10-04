//! Current V16 identity fields, copied from their typed encoder order.
use super::{Error, Result};
use crate::state_storage::IdentityKind as K;
#[derive(Clone, Copy)]
pub(super) enum Kind {
    Fixed(K),
    Account(usize),
    Purpose,
    Location(usize),
    AidTransport(K),
}
#[derive(Clone, Copy)]
pub(super) struct Field {
    pub offset: usize,
    pub kind: Kind,
}
const fn f(offset: usize, kind: K) -> Field {
    Field {
        offset,
        kind: Kind::Fixed(kind),
    }
}
const fn a(offset: usize, tag: usize) -> Field {
    Field {
        offset,
        kind: Kind::Account(tag),
    }
}
const FIELDS_1: &[Field] = &[f(0, K::Process), f(32, K::Site)];
const FIELDS_2: &[Field] = &[f(0, K::FreightLot), f(32, K::Order), f(64, K::Route)];
const FIELDS_4_TO_6: &[Field] = &[f(0, K::Order)];
const FIELDS_7: &[Field] = &[f(0, K::Site), f(33, K::Order)];
const FIELDS_8: &[Field] = &[
    f(0, K::Order),
    f(32, K::Site),
    f(64, K::FinalDemandPrincipal),
    f(96, K::Good),
    f(128, K::Unit),
];
const FIELDS_9: &[Field] = &[
    f(0, K::Order),
    f(32, K::Site),
    f(64, K::Site),
    f(96, K::Good),
    f(128, K::Unit),
];
const FIELDS_10: &[Field] = &[
    f(0, K::Site),
    f(32, K::Process),
    f(64, K::Good),
    f(96, K::Unit),
    f(128, K::Unit),
];
const FIELDS_11: &[Field] = &[
    Field {
        offset: 2,
        kind: Kind::Purpose,
    },
    Field {
        offset: 36,
        kind: Kind::Location(34),
    },
    Field {
        offset: 86,
        kind: Kind::Location(84),
    },
];
const FIELDS_12: &[Field] = &[f(0, K::Shift), a(33, 32), a(66, 65)];
const FIELDS_13: &[Field] = &[f(0, K::Site), f(32, K::Unit)];
const FIELDS_14: &[Field] = &[
    f(0, K::FinalDemandPrincipal),
    f(32, K::Site),
    f(64, K::Good),
    f(96, K::Unit),
    f(128, K::Order),
];
const FIELDS_15: &[Field] = &[
    f(0, K::FinalDemandPrincipal),
    f(32, K::Good),
    f(64, K::Unit),
];
const FIELDS_18: &[Field] = &[f(0, K::Site), f(32, K::Good), f(64, K::Unit)];
const FIELDS_19: &[Field] = &[a(1, 0)];
const FIELDS_20: &[Field] = &[
    f(8, K::Order),
    f(40, K::Site),
    a(73, 72),
    f(105, K::Good),
    f(137, K::Unit),
];
const FIELDS_21: &[Field] = &[
    f(8, K::FinalDemandPrincipal),
    f(40, K::Good),
    f(72, K::Unit),
];
const FIELDS_22: &[Field] = &[
    f(16, K::Process),
    f(48, K::Site),
    f(80, K::Good),
    f(112, K::Unit),
];
const FIELDS_23: &[Field] = &[
    f(8, K::Process),
    f(40, K::Site),
    f(72, K::Good),
    f(104, K::Unit),
];
const FIELDS_24: &[Field] = &[f(8, K::PublicAccount), a(41, 40)];
const FIELDS_25: &[Field] = &[a(9, 8), f(41, K::PublicAccount)];
const FIELDS_26: &[Field] = &[f(8, K::Site), a(41, 40)];
const FIELDS_27: &[Field] = &[f(8, K::Contribution), a(41, 40), f(73, K::Site)];
const FIELDS_28: &[Field] = &[
    f(0, K::StaffingPool),
    f(32, K::Site),
    f(64, K::Unit),
    f(96, K::StaffingMember),
    f(128, K::FinalDemandPrincipal),
];
const FIELDS_29: &[Field] = &[
    f(0, K::StaffingMember),
    f(32, K::Site),
    f(64, K::Unit),
    f(96, K::FinalDemandPrincipal),
];
const FIELDS_30: &[Field] = &[f(8, K::Installation), f(40, K::Process), f(72, K::Site)];
const FIELDS_31: &[Field] = &[f(8, K::EquipmentCohort), f(40, K::Process), f(72, K::Site)];
const FIELDS_32: &[Field] = &[
    f(8, K::Order),
    f(40, K::Process),
    f(72, K::Site),
    f(104, K::Site),
];
const FIELDS_33: &[Field] = &[f(8, K::Process), f(40, K::Site)];
const FIELDS_34: &[Field] = &[f(0, K::FinalDemandPrincipal), f(40, K::Unit)];

const FIELDS_35: &[Field] = &[
    f(0, K::Order),
    f(32, K::AidMandate),
    Field {
        offset: 81,
        kind: Kind::AidTransport(K::Route),
    },
    Field {
        offset: 113,
        kind: Kind::AidTransport(K::LogisticsNode),
    },
    Field {
        offset: 145,
        kind: Kind::AidTransport(K::LogisticsNode),
    },
    a(178, 177),
    f(210, K::FinalDemandPrincipal),
    f(242, K::FinalDemandPrincipal),
    f(274, K::Good),
    f(306, K::Unit),
];

const FIELDS_36: &[Field] = &[
    f(144, K::FinalDemandPrincipal),
    f(176, K::OrganizationAccount),
    f(208, K::Unit),
];

pub(super) fn fields(tag: u8) -> Result<&'static [Field]> {
    Ok(match tag {
        1 | 17 => FIELDS_1,
        2 | 3 => FIELDS_2,
        4..=6 => FIELDS_4_TO_6,
        7 => FIELDS_7,
        8 => FIELDS_8,
        9 | 16 => FIELDS_9,
        10 => FIELDS_10,
        11 => FIELDS_11,
        12 => FIELDS_12,
        13 => FIELDS_13,
        14 => FIELDS_14,
        15 => FIELDS_15,
        18 => FIELDS_18,
        19 => FIELDS_19,
        20 => FIELDS_20,
        21 => FIELDS_21,
        22 => FIELDS_22,
        23 => FIELDS_23,
        24 => FIELDS_24,
        25 => FIELDS_25,
        26 => FIELDS_26,
        27 => FIELDS_27,
        28 => FIELDS_28,
        29 => FIELDS_29,
        30 => FIELDS_30,
        31 => FIELDS_31,
        32 => FIELDS_32,
        33 => FIELDS_33,
        34 => FIELDS_34,
        35 => FIELDS_35,
        36 => FIELDS_36,
        _ => return Err(Error::Family),
    })
}

fn account(tag: u8) -> Result<K> {
    Ok(match tag {
        1 => K::Site,
        2 => K::FinalDemandPrincipal,
        3 => K::OrganizationAccount,
        4 => K::PublicAccount,
        _ => return Err(Error::IdentityTag),
    })
}
pub(super) fn resolve_kind(kind: Kind, row: &[u8]) -> Result<Option<K>> {
    Ok(Some(match kind {
        Kind::Fixed(k) => k,
        Kind::AidTransport(k) => match *row.get(80).ok_or(Error::Truncated)? {
            1 => return Ok(None),
            2 => k,
            _ => return Err(Error::IdentityTag),
        },
        Kind::Account(offset) => account(*row.get(offset).ok_or(Error::Truncated)?)?,
        Kind::Purpose => match row.first().copied().ok_or(Error::Truncated)? {
            1..=3 | 8..=10 => K::Order,
            4..=6 => K::Shift,
            7 => return Ok(None),
            _ => return Err(Error::IdentityTag),
        },
        Kind::Location(offset) => match *row.get(offset).ok_or(Error::Truncated)? {
            1 => account(*row.get(offset + 1).ok_or(Error::Truncated)?)?,
            2 | 4 => K::Order,
            3 => K::Shift,
            _ => return Err(Error::IdentityTag),
        },
    }))
}
