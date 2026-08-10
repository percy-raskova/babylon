//! Top-form declarations (`bsl-language.rst` §2.2's `<top-form>`): the
//! `deffield` and `intrinsic` forms, read into the registries the
//! typechecker and the fuel bound checker consume. Every check here is a
//! **load** check (§3): there is no partial load and no "skip the bad
//! declaration" mode.
//!
//! R9 chapter C1 lands three rulings in this module:
//!
//! - a `deffield`'s first segment may name a `NodeType`, an `EdgeType` **or**
//!   a `HyperedgeType` member (D31) — an unregistered segment is
//!   `E-LOAD-023`, resolved through [`crate::vocabulary`];
//! - every `EdgeType` carries one **implicitly declared** field,
//!   `<edge-type>/strength`, `:type Coefficient` `:kind extensive` (D32).
//!   Re-declaring it explicitly is `E-LOAD-001`, a duplicate field
//!   declaration, so there is exactly one home for its type and kind;
//! - every §5.2 form-head symbol is **reserved against the intrinsic
//!   namespace** (D33): declaring an intrinsic with one is `E-LOAD-024`,
//!   checked against the §5.2 list itself so adding a form tag automatically
//!   reserves it.

use crate::reader::{Atom, SExpr};
use crate::types::{BslType, FieldDecl, FieldKind};
use crate::vocabulary::{render_member, ClosedVocabulary, EnumKind, VocabularyError};
use std::collections::HashMap;

/// The §5.2 form tags that are valid `symbol`s, and are therefore reserved
/// against the intrinsic namespace (D33). The operator tags (`<`, `+`, …)
/// are excluded because an `intrinsic` name is a `symbol` (§1.4) and cannot
/// spell them, so no collision is expressible there. `opt` — the synthetic
/// keyword-option tag — is included: it is a §5.2 tag like any other.
pub const RESERVED_FORM_TAGS: [&str; 49] = [
    "add",
    "add-edge",
    "add-hyperedge",
    "add-node",
    "and",
    "anchor",
    "binding",
    "bindings",
    "ceiling",
    "deffield",
    "domain",
    "edge-between",
    "edges",
    "effects",
    "emit",
    "exists",
    "field-of",
    "fold",
    "for-each",
    "forall",
    "guard",
    "hyperedges",
    "hyperedges-of",
    "if",
    "intrinsic",
    "manifest",
    "members",
    "members-of",
    "metric",
    "metric-of",
    "neighbors",
    "nodes",
    "not",
    "opt",
    "or",
    "remove-edge",
    "remove-hyperedge",
    "remove-node",
    "rule",
    "scale",
    "select-max",
    "select-min",
    "set",
    "sub",
    "the",
    "update-edge",
    "update-hyperedge",
    "update-node",
    "when",
];

/// The declarable intrinsic set (`bsl-language.rst` §3.10). The Program 28
/// roadmap's R10 row holds it at `{exp, log}` **at most**, citing ADR176
/// r21; r21's own text pins a *mechanism* (transcendentals cross via a
/// pinned soft-float libm crate with golden vectors per intrinsic) and does
/// not enumerate a membership, so the enumeration is the roadmap's
/// rendering of it. **R10 is operative**, and this constant is written to
/// it.
///
/// **Recorded discrepancy, not resolved here** (D70): `round-half-even` is
/// *obliged* by §3.2 and §2.7 — the kernel must expose the same half-even
/// algorithm to rules — and sits **outside** this enumeration. §3.10's
/// rider slate records affirming it as a housekeeping proposal and
/// "declares nothing", so this crate admits nothing there: the set below is
/// exactly the two names, and resolving the discrepancy is the Director's.
pub const DECLARABLE_INTRINSICS: [&str; 2] = ["exp", "log"];

/// Intrinsic names that are **prohibited outright**, not merely undeclared
/// (§3.10, D71). `sigmoid` would hand content the exact mechanism ADR172
/// ruling 5 forbids, pre-packaged and named; it is the one part of the
/// doctrine gate that can be made mechanical, so it is.
pub const PROHIBITED_INTRINSIC_NAMES: [&str; 1] = ["sigmoid"];

/// A declaration-surface rejection.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum DeclError {
    /// `E-LOAD-001` — a duplicate rule id, field declaration or intrinsic
    /// declaration across the content set (§2.2). Re-declaring an implicit
    /// `<edge-type>/strength` lands here too (D32).
    Duplicate {
        /// What was declared twice.
        name: String,
        /// The declaration kind, for the message.
        what: &'static str,
    },
    /// `E-LOAD-022` — a `deffield` whose type or kind disagrees with the
    /// kernel's model registration (D9: the kernel is checked against
    /// content, not the reverse).
    KernelDisagreement {
        /// The field.
        field: String,
        /// What disagrees.
        detail: String,
    },
    /// `E-LOAD-023` / `E-LOAD-030` / … — a closed-vocabulary failure.
    Vocabulary(VocabularyError),
    /// `E-LOAD-024` — an `intrinsic` declared with a reserved §5.2 form-head
    /// name, or with a prohibited name (§3.10's `sigmoid`).
    ReservedIntrinsicName {
        /// The offending name.
        name: String,
        /// Why it is reserved.
        reason: &'static str,
    },
    /// A form off the §2.9 grammar at a point this reader must destructure.
    Malformed {
        /// What was expected, and what was found.
        message: String,
    },
}

impl DeclError {
    /// The spec's error code, where the reference names one.
    #[must_use]
    pub fn spec_code(&self) -> Option<&'static str> {
        match self {
            Self::Duplicate { .. } => Some("E-LOAD-001"),
            Self::KernelDisagreement { .. } => Some("E-LOAD-022"),
            Self::Vocabulary(e) => Some(e.spec_code()),
            Self::ReservedIntrinsicName { .. } => Some("E-LOAD-024"),
            Self::Malformed { .. } => None,
        }
    }
}

impl std::fmt::Display for DeclError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Duplicate { name, what } => {
                write!(f, "E-LOAD-001: duplicate {what} declaration: {name}")
            }
            Self::KernelDisagreement { field, detail } => write!(
                f,
                "E-LOAD-022: deffield {field} disagrees with the kernel's \
                 registration: {detail}"
            ),
            Self::Vocabulary(e) => write!(f, "{e}"),
            Self::ReservedIntrinsicName { name, reason } => write!(
                f,
                "E-LOAD-024: intrinsic name '{name}' is reserved — {reason}"
            ),
            Self::Malformed { message } => write!(f, "malformed declaration: {message}"),
        }
    }
}

impl std::error::Error for DeclError {}

impl From<VocabularyError> for DeclError {
    fn from(e: VocabularyError) -> Self {
        Self::Vocabulary(e)
    }
}

fn malformed(message: impl Into<String>) -> DeclError {
    DeclError::Malformed {
        message: message.into(),
    }
}

/// The declared type + kind of a field, plus the graph-element kind that
/// owns it (§2.9's first segment).
#[derive(Debug, Clone)]
pub struct OwnedFieldDecl {
    /// The field's type and intensivity kind.
    pub decl: FieldDecl,
    /// Which enum kind the owning type belongs to.
    pub owner_kind: EnumKind,
    /// The owning type's member identifier, e.g. `SOCIAL_CLASS`.
    pub owner_member: String,
    /// Whether this row is the implicit `<edge-type>/strength` (D32) rather
    /// than an authored `deffield`.
    pub implicit: bool,
}

/// Every declared field of a content set, keyed by qname.
#[derive(Debug, Clone, Default)]
pub struct FieldRegistry {
    fields: HashMap<String, OwnedFieldDecl>,
}

impl FieldRegistry {
    /// Seed the registry with the implicit `<edge-type>/strength` field of
    /// every registered `EdgeType` (D32): `Coefficient`, `extensive`. The
    /// `extensive` kind is load-bearing — an intensive `strength` would
    /// make §2.4's `sum_strength` coverage row `E-TYPE-041` and therefore
    /// inexpressible.
    #[must_use]
    pub fn with_implicit_edge_strength(vocabulary: &ClosedVocabulary) -> Self {
        let mut fields = HashMap::new();
        for member in vocabulary.members(EnumKind::EdgeType) {
            let qname = format!("{}/strength", render_member(member));
            fields.insert(
                qname,
                OwnedFieldDecl {
                    decl: FieldDecl {
                        ty: BslType::Coefficient,
                        kind: FieldKind::Extensive,
                    },
                    owner_kind: EnumKind::EdgeType,
                    owner_member: member.clone(),
                    implicit: true,
                },
            );
        }
        Self { fields }
    }

    /// Read one `(deffield <qname> :type <T> :kind <k>)` form into the
    /// registry.
    ///
    /// # Errors
    ///
    /// [`DeclError::Vocabulary`] (`E-LOAD-023`) for an unregistered owning
    /// segment; [`DeclError::Duplicate`] (`E-LOAD-001`) for a second
    /// declaration of one field — including a re-declaration of an implicit
    /// `<edge-type>/strength`; [`DeclError::Malformed`] off the grammar.
    pub fn declare(
        &mut self,
        form: &SExpr,
        vocabulary: &ClosedVocabulary,
    ) -> Result<(), DeclError> {
        let (qname, ty, kind) = parse_deffield(form)?;
        let (owner_kind, owner_member) = vocabulary.owner_of_field(&qname)?;
        if let Some(existing) = self.fields.get(&qname) {
            let what = if existing.implicit {
                "field (the implicit <edge-type>/strength, D32)"
            } else {
                "field"
            };
            return Err(DeclError::Duplicate { name: qname, what });
        }
        self.fields.insert(
            qname,
            OwnedFieldDecl {
                decl: FieldDecl { ty, kind },
                owner_kind,
                owner_member: owner_member.to_owned(),
                implicit: false,
            },
        );
        Ok(())
    }

    /// Check every declared field against the kernel's model registration
    /// (`E-LOAD-022`, D9: the two must agree and the kernel is checked
    /// against content, not the reverse). Implicit rows are exempt: they
    /// have no authored declaration to disagree with.
    ///
    /// # Errors
    ///
    /// [`DeclError::KernelDisagreement`].
    pub fn check_against_kernel(
        &self,
        kernel: &HashMap<String, FieldDecl>,
    ) -> Result<(), DeclError> {
        let mut names: Vec<&String> = self.fields.keys().collect();
        names.sort(); // deterministic first-failure reporting
        for name in names {
            let owned = &self.fields[name];
            if owned.implicit {
                continue;
            }
            let Some(registered) = kernel.get(name) else {
                continue; // an unregistered field is the vocabulary's business
            };
            if registered.ty != owned.decl.ty || registered.kind != owned.decl.kind {
                return Err(DeclError::KernelDisagreement {
                    field: name.clone(),
                    detail: format!(
                        "content declares {:?}/{:?}, the kernel registers {:?}/{:?}",
                        owned.decl.ty, owned.decl.kind, registered.ty, registered.kind
                    ),
                });
            }
        }
        Ok(())
    }

    /// Look one field up by qname.
    #[must_use]
    pub fn get(&self, qname: &str) -> Option<&OwnedFieldDecl> {
        self.fields.get(qname)
    }

    /// The registry as the §3.4 typechecker's `fields` map.
    #[must_use]
    pub fn type_env_fields(&self) -> HashMap<String, FieldDecl> {
        self.fields
            .iter()
            .map(|(name, owned)| (name.clone(), owned.decl.clone()))
            .collect()
    }

    /// Every declared qname, ascending.
    #[must_use]
    pub fn qnames(&self) -> Vec<&str> {
        let mut names: Vec<&str> = self.fields.keys().map(String::as_str).collect();
        names.sort_unstable();
        names
    }
}

/// Destructure `(deffield <qname> :type <type-name> :kind intensive|extensive)`.
fn parse_deffield(form: &SExpr) -> Result<(String, BslType, FieldKind), DeclError> {
    let SExpr::List(items) = form else {
        return Err(malformed("a deffield must be a form"));
    };
    let [SExpr::Atom(Atom::Symbol(head)), SExpr::Atom(Atom::QName(qname)), options @ ..] =
        items.as_slice()
    else {
        return Err(malformed(
            "(deffield <qname> :type <T> :kind <k>) — unrecognized shape",
        ));
    };
    if head != "deffield" {
        return Err(malformed(format!(
            "expected (deffield …), found ({head} …)"
        )));
    }
    let mut ty: Option<BslType> = None;
    let mut kind: Option<FieldKind> = None;
    let mut cursor = options;
    while let [SExpr::Atom(Atom::Keyword(kw)), tail @ ..] = cursor {
        match (kw.as_str(), tail) {
            ("type", [SExpr::Atom(Atom::Symbol(name)), rest @ ..]) => {
                ty = Some(parse_type_name(name)?);
                cursor = rest;
            }
            ("kind", [SExpr::Atom(Atom::Symbol(name)), rest @ ..]) => {
                kind = Some(match name.as_str() {
                    "intensive" => FieldKind::Intensive,
                    "extensive" => FieldKind::Extensive,
                    other => {
                        return Err(malformed(format!(
                            ":kind is intensive|extensive, found {other}"
                        )))
                    }
                });
                cursor = rest;
            }
            (other, _) => {
                return Err(malformed(format!(
                    "a deffield takes :type and :kind, found :{other}"
                )))
            }
        }
    }
    if !cursor.is_empty() {
        return Err(malformed(format!(
            "unexpected trailing items in a deffield: {cursor:?}"
        )));
    }
    match (ty, kind) {
        (Some(ty), Some(kind)) => Ok((qname.clone(), ty, kind)),
        _ => Err(malformed("a deffield declares both :type and :kind (§2.9)")),
    }
}

/// The §3.1 type names, as they are spelled in `:type` / `:returns`.
///
/// **Recorded rst gap (R9 step 3, 2026-08-10).** §2.9/§2.11/§2.7 write
/// `<type-name>` as a grammar nonterminal and never assign it a §1.4 atom
/// class, while §3.1's own table spells the types capitalized (`Currency`,
/// `Int`, …). A bare capitalized run matches **no** §1.4 atom class — an
/// `enum-ref` needs its `/`, and `symbol` is lowercase-only — so the
/// spec's own spelling is unlexable as written. This implementation reads
/// `<type-name>` as a lowercase `symbol` (`currency`, `int`, …), which is
/// what the crate's pre-existing `(deffield x :type int)` vector already
/// assumed and the only reading §1.4 admits. Flagged for the Phase-1
/// review; nothing else in the language depends on the choice.
///
/// # Errors
///
/// [`DeclError::Malformed`] for a name outside §3.1's closed table.
pub fn parse_type_name(name: &str) -> Result<BslType, DeclError> {
    match name {
        "int" => Ok(BslType::Int),
        "bool" => Ok(BslType::Bool),
        "currency" => Ok(BslType::Currency),
        "probability" => Ok(BslType::Probability),
        "intensity" => Ok(BslType::Intensity),
        "coefficient" => Ok(BslType::Coefficient),
        other => Err(malformed(format!(
            "'{other}' is not one of §3.1's type names (lowercase — see the \
             recorded rst gap on parse_type_name)"
        ))),
    }
}

/// Check one `intrinsic` declaration's NAME against the reserved and
/// prohibited sets (D33 / D71, both `E-LOAD-024`).
///
/// # Errors
///
/// [`DeclError::ReservedIntrinsicName`].
pub fn check_intrinsic_name(name: &str) -> Result<(), DeclError> {
    if PROHIBITED_INTRINSIC_NAMES.contains(&name) {
        return Err(DeclError::ReservedIntrinsicName {
            name: name.to_owned(),
            reason: "declaring it would hand content the imposed functional \
                     form ADR172 ruling 5 forbids, pre-packaged (§3.10)",
        });
    }
    if RESERVED_FORM_TAGS.contains(&name) {
        return Err(DeclError::ReservedIntrinsicName {
            name: name.to_owned(),
            reason: "it is a §5.2 form-head symbol, and a colliding intrinsic \
                     would make the form ambiguous with a call (§2.7)",
        });
    }
    Ok(())
}

/// §3.10 gate 1 — *is the intrinsic declarable?* Mechanical, checked at
/// load against [`DECLARABLE_INTRINSICS`].
///
/// **Gate 2 is not mechanical and is not here.** Cap-legality is not
/// doctrine-legality: `exp` sits inside the cap, and three of its five call
/// sites in the frozen estate stipulate a logistic sigmoid that ADR173 and
/// the standing 2026-07-29 no-imposed-functional-forms ruling retire. A
/// verbatim transcription would pass this check and violate the theory
/// line. That gate belongs to Director review, and its question is always
/// the same: *can this be re-derived as a measure instead?* The one part of
/// it that **can** be made mechanical is `sigmoid`'s prohibition, which
/// [`check_intrinsic_name`] enforces.
///
/// The reference names no numbered code for a declaration outside the cap
/// (§3.10's gate-1 sentence cites `E-LOAD-021`, which is the code for a
/// *call* to an undeclared intrinsic), so this error carries none — the
/// no-invented-codes precedent.
///
/// # Errors
///
/// [`DeclError::Malformed`] naming the cap and its authority chain.
pub fn check_intrinsic_cap(name: &str) -> Result<(), DeclError> {
    check_intrinsic_name(name)?;
    if DECLARABLE_INTRINSICS.contains(&name) {
        return Ok(());
    }
    Err(malformed(format!(
        "'{name}' is outside the declarable intrinsic set {DECLARABLE_INTRINSICS:?} \
         (§3.10, R10 citing ADR176 r21). Adding to it is a Director ruling, not \
         an authoring decision; note that round-half-even is obliged by §3.2 and \
         sits outside the enumeration as a recorded discrepancy"
    )))
}

#[cfg(test)]
mod tests {
    use super::{check_intrinsic_name, FieldRegistry, RESERVED_FORM_TAGS};
    use crate::reader::read;
    use crate::types::{BslType, FieldDecl, FieldKind};
    use crate::vocabulary::{ClosedVocabulary, EnumKind};
    use std::collections::HashMap;

    fn vocabulary() -> ClosedVocabulary {
        ClosedVocabulary::new([
            (
                EnumKind::NodeType,
                vec!["SOCIAL_CLASS".to_owned(), "POLITY".to_owned()],
            ),
            (
                EnumKind::EdgeType,
                vec!["SOLIDARITY".to_owned(), "EXPLOITATION".to_owned()],
            ),
            (EnumKind::HyperedgeType, vec!["ECONOMIC_SECTOR".to_owned()]),
        ])
        .unwrap()
    }

    fn form(source: &str) -> crate::reader::SExpr {
        read(source).expect("test source must parse").0
    }

    #[test]
    fn every_edge_type_carries_an_implicit_extensive_coefficient_strength() {
        let registry = FieldRegistry::with_implicit_edge_strength(&vocabulary());
        let strength = registry.get("solidarity/strength").expect("D32");
        assert_eq!(strength.decl.ty, BslType::Coefficient);
        assert_eq!(
            strength.decl.kind,
            FieldKind::Extensive,
            "the extensive kind is what makes §2.4's sum_strength row \
             honourable under §3.4 without an exemption (D32)"
        );
        assert!(strength.implicit);
        assert!(registry.get("exploitation/strength").is_some());
    }

    #[test]
    fn redeclaring_the_implicit_strength_field_is_e_load_001() {
        let mut registry = FieldRegistry::with_implicit_edge_strength(&vocabulary());
        let err = registry
            .declare(
                &form("(deffield solidarity/strength :type coefficient :kind extensive)"),
                &vocabulary(),
            )
            .unwrap_err();
        assert_eq!(err.spec_code(), Some("E-LOAD-001"));
    }

    #[test]
    fn a_deffield_may_own_off_a_node_edge_or_hyperedge_type() {
        let v = vocabulary();
        let mut registry = FieldRegistry::default();
        for source in [
            "(deffield social-class/wealth :type currency :kind extensive)",
            "(deffield exploitation/tension :type intensity :kind intensive)",
            "(deffield economic-sector/output :type currency :kind extensive)",
        ] {
            registry.declare(&form(source), &v).expect(source);
        }
        assert_eq!(
            registry.get("exploitation/tension").unwrap().owner_kind,
            EnumKind::EdgeType
        );
        assert_eq!(
            registry.get("economic-sector/output").unwrap().owner_kind,
            EnumKind::HyperedgeType
        );
    }

    #[test]
    fn a_deffield_owning_off_no_registered_type_is_e_load_023() {
        let mut registry = FieldRegistry::default();
        let err = registry
            .declare(
                &form("(deffield imperium/rent :type currency :kind extensive)"),
                &vocabulary(),
            )
            .unwrap_err();
        assert_eq!(err.spec_code(), Some("E-LOAD-023"));
    }

    #[test]
    fn a_duplicate_authored_field_is_e_load_001() {
        let v = vocabulary();
        let mut registry = FieldRegistry::default();
        let source = "(deffield social-class/wealth :type currency :kind extensive)";
        registry.declare(&form(source), &v).unwrap();
        assert_eq!(
            registry.declare(&form(source), &v).unwrap_err().spec_code(),
            Some("E-LOAD-001")
        );
    }

    #[test]
    fn kernel_disagreement_is_e_load_022() {
        let v = vocabulary();
        let mut registry = FieldRegistry::default();
        registry
            .declare(
                &form("(deffield social-class/wealth :type currency :kind extensive)"),
                &v,
            )
            .unwrap();
        let kernel = HashMap::from([(
            "social-class/wealth".to_owned(),
            FieldDecl {
                ty: BslType::Currency,
                kind: FieldKind::Intensive, // the kernel says intensive
            },
        )]);
        assert_eq!(
            registry
                .check_against_kernel(&kernel)
                .unwrap_err()
                .spec_code(),
            Some("E-LOAD-022")
        );
    }

    #[test]
    fn every_form_head_symbol_is_reserved_against_the_intrinsic_namespace() {
        for tag in RESERVED_FORM_TAGS {
            let err = check_intrinsic_name(tag).unwrap_err();
            assert_eq!(err.spec_code(), Some("E-LOAD-024"), "{tag}");
        }
        assert_eq!(check_intrinsic_name("exp"), Ok(()));
        assert_eq!(check_intrinsic_name("log"), Ok(()));
    }

    #[test]
    fn sigmoid_is_prohibited_outright_not_merely_undeclared() {
        let err = check_intrinsic_name("sigmoid").unwrap_err();
        assert_eq!(err.spec_code(), Some("E-LOAD-024"));
        assert!(format!("{err}").contains("ADR172"), "{err}");
    }
}
