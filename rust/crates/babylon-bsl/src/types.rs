//! The BSL type universe (spec §5 Types, `bsl-language.rst` §3): kernel
//! scalars, closed enums, booleans, `Int`, and typed node/edge-set
//! references. Intensivity is a per-field DECLARATION (`:kind
//! intensive|extensive` on `deffield` forms, §3.4), not a property of the
//! scalar type — `wealth` (Currency) is extensive while `consciousness`
//! (Intensity) is intensive, and no type makes that decidable. `FieldKind`
//! therefore travels alongside a field's `BslType`, and the typechecker
//! (not the type) enforces the aggregation law.

/// A BSL static type.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum BslType {
    /// The `[0, 1]` probability scalar.
    Probability,
    /// The `[0, 1]` intensity scalar.
    Intensity,
    /// The `[0, 1]` coefficient scalar.
    Coefficient,
    /// Fixed-point i128 micro-unit currency.
    Currency,
    /// `int-lit`'s static type (§1.5); also `count`'s result type (§3.4).
    Int,
    /// `#t` / `#f`.
    Bool,
    /// A closed enum, by its registered type name (e.g. `"DoctrineTag"`).
    Enum(&'static str),
    /// A typed node-set reference, by `NodeType` name.
    NodeSet(&'static str),
    /// A typed edge-set reference, by `EdgeType` name.
    EdgeSet(&'static str),
}

/// A field's declared intensivity kind (§3.4).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum FieldKind {
    /// Averages meaningfully only under an extensive weight.
    Intensive,
    /// Sums meaningfully over a population or region.
    Extensive,
}

/// A model field's declared type + kind — the typechecker's environment
/// entry for anything a fold can read.
#[derive(Debug, Clone)]
pub struct FieldDecl {
    /// The field's scalar type.
    pub ty: BslType,
    /// The field's declared intensivity kind.
    pub kind: FieldKind,
}
