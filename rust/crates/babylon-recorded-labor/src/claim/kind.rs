/// The kind of money a group's hours back came through. `Work`: wages. `Owning`: profit (later rent and
/// interest). `Support`: benefits and the treasury's payments (later kin and aid). `NotRecorded`: money held at
/// the opening, whose kind was never recorded.
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)]
pub enum Claim {
    /// Wages.
    Work,
    /// Profit.
    Owning,
    /// Benefits and public payments.
    Support,
    /// Money held at the opening.
    NotRecorded,
}

impl Claim {
    /// Every kind, in the order of a `Mix`.
    pub const ALL: [Claim; 4] = [
        Claim::Work,
        Claim::Owning,
        Claim::Support,
        Claim::NotRecorded,
    ];

    /// Its place in `ALL`.
    #[must_use]
    pub const fn index(self) -> usize {
        match self {
            Self::Work => 0,
            Self::Owning => 1,
            Self::Support => 2,
            Self::NotRecorded => 3,
        }
    }
}
