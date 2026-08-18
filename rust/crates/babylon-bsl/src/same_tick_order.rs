//! Same-tick ordering as LOAD REFUSALS (Task W2, BSL Hygiene Knock-out —
//! `docs/superpowers/plans/2026-08-18-bsl-hygiene-knockout.md` §Task W2,
//! amended by `.superpowers/sdd/2026-08-18-bsl-hygiene-knockout/task-w2-
//! brief.md` and its binding `prep-adjudication.md`).
//!
//! **Boundary ruling (Director, 2026-08-18 ~13:40 EDT), the reason this is
//! a load-time check and not an external lint:** "if you need a sentinel
//! that's a code smell for you need to expand BSL" — semantic coherence
//! belongs IN the language as a load/type refusal, not bolted on
//! afterward. This module adds two such refusals, in the same family as
//! `E-LOAD-001` (content-set-wide, checked at load, over whatever content
//! set the caller actually loaded — never a hypothetical wider one).
//!
//! **Refusal 1 — `E-LOAD-058`, stale-default read.** For every
//! `(binding … :field f :optional :default d)` in rule `R`, compute `f`'s
//! *writer set*: every OTHER rule `W` in the content set with an
//! `(update-node … f (<op> …))` effect, **excluding `W` where
//! `W.rule_id == R.rule_id`** (adjudication §(c), verbatim, keyed on rule
//! IDENTITY, never on write TARGET — `solidarity/p0-transmit` reads `self`
//! and writes `it`, same rule, and must still self-exclude). If any
//! remaining writer's rule id does not sort strictly before `R`'s
//! (ascending byte order, §4.2/D116), `R` can observe `d` on a tick where
//! that writer already ran and left a real value from an EARLIER tick —
//! refused.
//!
//! **Refusal 2 — `E-LOAD-059`, unreset fan-in.** A field written by 2+
//! distinct rules in the content set needs its byte-earliest writer to be
//! either an unconditional `set` or the D127 unconditional-recompute shape
//! (adjudication §(d), verbatim: unconditional = no `(when …)` at all, or
//! a `(when …)` whose condition is the literal `#t` — nothing finer, no
//! guard-dominance analysis) — else refused as an accumulation with no
//! rule-identifiable reset.
//!
//! **The enforcement gate (R-W2a, the 2026-08-18 evening sitting).** The
//! 13 EXPOSED bindings in `consciousness.bsl` (rows 3-9, 14-16, 18, 20, 22
//! of the W2 pre-audit table) are DELIBERATE same-tick reads, mitigated by
//! guard structure or a documented one-tick-lag idiom the loader cannot
//! yet verify. Making refusal 1 enforce today would refuse a real,
//! working, byte-pinned pack. The Director's ruling: mint a per-binding
//! author declaration (working name `:prior-tick`) via constitutional
//! amendment — refusal 1's FINAL semantics refuse every UNDECLARED exposed
//! read, not every exposed read outright. W2 lands the fixture-level
//! refusals, the audit, and the amendment DRAFT
//! (`ai/_inbox/amendment-prior-tick-draft.md`); corpus enablement follows
//! ratification at a Director sitting. Until then, [`ENFORCE_SAME_TICK_
//! ORDERING`] stays `false` — see its own doc for the full citation.

use crate::bindings::{parse_bindings, BindSource};
use crate::material_basis::keyword_value;
use crate::reader::{Atom, SExpr};
use std::collections::{HashMap, HashSet};

/// Whether [`diagnose`]'s findings actually reject a load, or are computed
/// for inspection only. **`false` — OFF for the landed corpus.**
///
/// This constant IS the amendment gate R-W2a minted, not a placeholder for
/// one. **Corrected (W2 fix round 1, review finding I1): `split_content`
/// (`rule_pipeline.rs`) calls [`diagnose`] ONLY inside this gate** — when
/// the constant is `false`, no `Diagnosis` is computed on the load path at
/// all, so the branch is dead-code-eliminated and the default load is not
/// merely refusal-free but *cost*-free; there is no always-on inspection
/// channel through `split_content` itself (its return type carries none).
/// This crate's own fixture tests (this module's `tests` below) call
/// [`diagnose`] and [`Diagnosis::into_result`] directly, bypassing
/// `split_content` and the constant entirely, which is how W2.1's RED
/// tests and W2.4's audit both prove the refusal's exact behavior against
/// real content without waiting on ratification.
///
/// Flip this to `true` only as part of the ratification ceremony this
/// module's doc names: minting the `:prior-tick` declaration (or whatever
/// name the Director ratifies), teaching refusal 1 to honor it on the 13
/// rows the amendment draft lists, and re-running the W2.4 audit to prove
/// the post-ratification inventory is `[]`. Draft:
/// `ai/_inbox/amendment-prior-tick-draft.md` (Amendment AI — reserved
/// 2026-08-18 against the concurrently-drafted AH/defevent; DRAFT status,
/// not ratified by this PR).
pub const ENFORCE_SAME_TICK_ORDERING: bool = false;

/// Refusal 1: rule `reader_rule`'s binding `binding_name` reads field
/// `field` with a declared `:optional :default`, and `writer_rule` — a
/// DIFFERENT rule in the same content set — writes `field` and sorts
/// on/after `reader_rule` in ascending rule-id byte order, so
/// `reader_rule` can observe the DECLARED DEFAULT on a tick where
/// `writer_rule` already ran and left a value from an earlier tick, not
/// this one's write.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct StaleDefaultRead {
    /// The rule doing the exposed `:optional :default` read.
    pub reader_rule: String,
    /// The binding name inside `reader_rule`.
    pub binding_name: String,
    /// The field the binding reads.
    pub field: String,
    /// A rule that writes `field` and does not sort strictly before
    /// `reader_rule` (the byte-least such writer, for a deterministic
    /// message — there may be more than one).
    pub writer_rule: String,
}

/// Refusal 2: `field` is written by 2+ distinct rules (`writers`, ascending
/// byte order) in the content set, and the byte-earliest of them is
/// neither an unconditional `set` nor the D127 unconditional-recompute
/// shape.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct UnresetFanIn {
    /// The multi-writer field.
    pub field: String,
    /// Every distinct writer rule id, ascending byte order.
    pub writers: Vec<String>,
}

/// The two refusals' typed rejections. `code`/`Display` follow the same
/// discipline every other load-error family in this crate does (S-11: a
/// typed, named, loud return value, never a warning or a log line).
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum SameTickOrderError {
    /// `E-LOAD-058`.
    StaleDefaultRead(StaleDefaultRead),
    /// `E-LOAD-059`.
    UnresetFanIn(UnresetFanIn),
}

impl SameTickOrderError {
    /// The spec code — see `docs/reference/bsl-language.rst`'s E-LOAD
    /// tables (W2.3 adds both rows).
    #[must_use]
    pub fn spec_code(&self) -> &'static str {
        match self {
            Self::StaleDefaultRead(_) => "E-LOAD-058",
            Self::UnresetFanIn(_) => "E-LOAD-059",
        }
    }
}

impl std::fmt::Display for SameTickOrderError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::StaleDefaultRead(v) => write!(
                f,
                "E-LOAD-058: stale-default read — rule {reader}'s binding `{binding}` reads \
                 field {field} with :optional :default, but rule {writer} writes {field} and \
                 does not sort strictly before {reader} in ascending rule-id byte order \
                 (§4.2/D116 same-tick evaluation order) — {reader} can observe the declared \
                 default on a tick where {writer} already ran and left a value from an EARLIER \
                 tick, never this one's write. Refused at load (S-11), content-set-wide, like \
                 E-LOAD-001. Gated by same_tick_order::ENFORCE_SAME_TICK_ORDERING — see that \
                 constant's doc and ai/_inbox/amendment-prior-tick-draft.md (Amendment AI, \
                 DRAFT) for the per-binding exemption this refusal's final semantics need.",
                reader = v.reader_rule,
                binding = v.binding_name,
                field = v.field,
                writer = v.writer_rule,
            ),
            Self::UnresetFanIn(v) => write!(
                f,
                "E-LOAD-059: unreset fan-in — field {field} is written by {n} rules in this \
                 content set ({writers}), and the byte-earliest writer is neither an \
                 unconditional `set` (no (when …), or (when #t)) nor the D127 \
                 unconditional-recompute shape (a :material-basis citing D127) — an \
                 accumulation with no rule-identifiable reset. Refused at load (S-11), \
                 content-set-wide, like E-LOAD-001.",
                field = v.field,
                n = v.writers.len(),
                writers = v.writers.join(", "),
            ),
        }
    }
}

impl std::error::Error for SameTickOrderError {}

/// Both refusals' findings against one content set, computed in full
/// regardless of [`ENFORCE_SAME_TICK_ORDERING`] — the gate decides whether
/// [`Diagnosis::into_result`] is actually called, not whether the analysis
/// runs.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct Diagnosis {
    /// Every refusal-1 finding, one per triggering binding (deterministic
    /// order: ascending `(reader_rule, field)`).
    pub stale_default_reads: Vec<StaleDefaultRead>,
    /// Every refusal-2 finding, one per triggering field (deterministic
    /// order: ascending `field`).
    pub unreset_fan_ins: Vec<UnresetFanIn>,
}

impl Diagnosis {
    /// Whether the content set has zero findings under either refusal.
    #[must_use]
    pub fn is_clean(&self) -> bool {
        self.stale_default_reads.is_empty() && self.unreset_fan_ins.is_empty()
    }

    /// Gate-ON semantics: the FIRST finding, deterministically (refusal 1
    /// before refusal 2, each in the order above) — matching S-11's "loud
    /// failure, reject the whole content set" precedent, the same one
    /// `E-LOAD-001` follows (first-encountered, not an exhaustive list;
    /// the exhaustive inventory is what [`Diagnosis`]'s own fields are
    /// for, and what W2.4's audit reads directly).
    ///
    /// # Errors
    /// The first [`SameTickOrderError`], if this diagnosis is not clean.
    pub fn into_result(self) -> Result<(), SameTickOrderError> {
        if let Some(v) = self.stale_default_reads.into_iter().next() {
            return Err(SameTickOrderError::StaleDefaultRead(v));
        }
        if let Some(v) = self.unreset_fan_ins.into_iter().next() {
            return Err(SameTickOrderError::UnresetFanIn(v));
        }
        Ok(())
    }
}

/// The four update-ops §2.8 admits on an `update-node` field (`set`/`add`/
/// `sub`/`scale`) — the write-side half of what a writer rule DOES to a
/// field, needed for refusal 2's "an unconditional **set**" test (`add`/
/// `sub`/`scale` never discharge it, however unconditional the rule is:
/// an unconditional `add` is still a fan-in contributor, not a reset).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
enum WriteOp {
    Set,
    Add,
    Sub,
    Scale,
}

impl WriteOp {
    fn parse(head: &str) -> Option<Self> {
        match head {
            "set" => Some(Self::Set),
            "add" => Some(Self::Add),
            "sub" => Some(Self::Sub),
            "scale" => Some(Self::Scale),
            _ => None,
        }
    }
}

/// Every `(field, op)` pair one `(effects …)` write site performs, walked
/// depth-first through arbitrary `guard`/`for-each` nesting.
///
/// Mirrors `structural_verbs::find_deferred_shape_verb`'s own `emit`-payload
/// discipline (payload LABELS are not verb invocations — see that
/// function's doc for the G1/H1 history this walk deliberately repeats
/// rather than risks re-breaking with a shallower recursion): once a form's
/// head is confirmed `emit`, only its payload items' VALUES are recursed
/// into, never the items themselves (whose first element is a label, not a
/// verb). Every other head — including `guard`, `for-each`, and any
/// arithmetic form — falls through to the generic per-child recursion,
/// which is what reaches an `update-node` buried under `for-each` > `guard`
/// > `guard` the way `solidarity/p0-transmit` nests one.
fn walk_for_writes(expr: &SExpr, out: &mut Vec<(String, WriteOp)>) {
    let SExpr::List(items) = expr else { return };
    if let Some(SExpr::Atom(Atom::Symbol(head))) = items.first() {
        if head == "update-node" {
            if let [_, _target, SExpr::Atom(Atom::QName(field)), SExpr::List(op_form)] =
                items.as_slice()
            {
                if let Some(SExpr::Atom(Atom::Symbol(op_head))) = op_form.first() {
                    if let Some(op) = WriteOp::parse(op_head) {
                        out.push((field.clone(), op));
                    }
                }
            }
            return;
        }
        if head == "emit" {
            if matches!(items.get(1), Some(SExpr::Atom(Atom::EnumRef { .. }))) {
                for payload_item in items.iter().skip(2) {
                    if let SExpr::List(pair) = payload_item {
                        for value in pair.iter().skip(1) {
                            walk_for_writes(value, out);
                        }
                    }
                }
            } else {
                for item in items.iter().skip(1) {
                    walk_for_writes(item, out);
                }
            }
            return;
        }
    }
    for item in items {
        walk_for_writes(item, out);
    }
}

/// Every `(field, op)` write this rule's `(effects …)` body performs.
fn field_writes(rule_items: &[SExpr]) -> Vec<(String, WriteOp)> {
    let mut out = Vec::new();
    for child in rule_items {
        let SExpr::List(inner) = child else { continue };
        if matches!(inner.first(), Some(SExpr::Atom(Atom::Symbol(h))) if h == "effects") {
            for effect in &inner[1..] {
                walk_for_writes(effect, &mut out);
            }
        }
    }
    out
}

/// The rule's own `(when <expr>)` condition, or `None` when it declares no
/// top-level `when` at all (§2.3: `<when>?`, optional).
fn when_condition(rule_items: &[SExpr]) -> Option<&SExpr> {
    rule_items.iter().find_map(|child| match child {
        SExpr::List(inner)
            if matches!(inner.first(), Some(SExpr::Atom(Atom::Symbol(h))) if h == "when") =>
        {
            inner.get(1)
        }
        _ => None,
    })
}

/// Adjudication §(d), verbatim: unconditional = no `(when …)` at all, or a
/// `(when …)` whose condition is the literal `#t`. Nothing finer — no
/// guard-dominance analysis between a reset and its fan-in writers (the
/// adjudication's own explicit exclusion; a static-analysis project W2
/// does not attempt).
fn is_unconditional(rule_items: &[SExpr]) -> bool {
    match when_condition(rule_items) {
        None | Some(SExpr::Atom(Atom::Bool(true))) => true,
        Some(_) => false,
    }
}

/// The D127 unconditional-recompute shape's discharge test, read the same
/// way the W2 pre-audit table itself established "0 [fields] with a
/// literal unconditional reset or D127 marker" — a literal `D127` citation
/// in the rule's own `:material-basis` prose, the citation-as-declaration
/// idiom this spec already uses pervasively (row 26's own material-basis
/// text cites D116 the same way). Comments are unavailable here — the
/// reader strips them before any `SExpr` exists (`canonical_ast`'s own
/// module doc) — so `:material-basis` is the only AST-visible citation
/// surface, and is the one the W2 pre-audit's own `rg -n D127` methodology
/// searched in the first place.
fn cites_d127(rule_items: &[SExpr]) -> bool {
    matches!(
        keyword_value(rule_items, "material-basis"),
        Some(Atom::Str(text)) if text.contains("D127")
    )
}

/// One rule's facts, precomputed once per [`diagnose`] call.
struct RuleFacts<'a> {
    id: &'a str,
    bindings: Vec<crate::bindings::BindingDecl>,
    writes: Vec<(String, WriteOp)>,
    unconditional: bool,
    d127: bool,
}

/// Diagnose both refusals against one content set — the paired `(rule_id,
/// rule_form)` list `rule_pipeline::split_content` already produces (so
/// this needs no second content-set notion, and no `LoadContext`: both
/// refusals are decidable from the rule forms alone, exactly like
/// `E-LOAD-001`).
///
/// A rule whose `(bindings …)` cannot be parsed at all is silently
/// EXCLUDED from this analysis, never reported here — `rule_pipeline::
/// load_rule_form`'s own call to `bindings::parse_bindings` is what owns
/// that rejection; duplicating it here would be a second, redundant error
/// path for the same defect (this module's job is same-tick ordering, not
/// binding-surface validity).
///
/// # Panics
/// Never, in practice: the internal `.expect()` on a field's byte-earliest
/// writer id resolving back to a known rule cannot fail, because every id
/// in `writer_ids` (and therefore every `earliest`) was inserted FROM
/// `facts` in the loop immediately above — there is no code path that adds
/// a writer id `diagnose` did not itself first see as a rule id in `facts`.
#[must_use]
pub fn diagnose(rules: &[(String, SExpr)]) -> Diagnosis {
    let mut facts: Vec<RuleFacts<'_>> = Vec::with_capacity(rules.len());
    for (id, form) in rules {
        let SExpr::List(items) = form else { continue };
        let Ok(bindings) = parse_bindings(form) else {
            continue;
        };
        facts.push(RuleFacts {
            id: id.as_str(),
            writes: field_writes(items),
            unconditional: is_unconditional(items),
            d127: cites_d127(items),
            bindings,
        });
    }

    // field -> distinct writer rule ids (any op).
    let mut writer_ids: HashMap<String, HashSet<String>> = HashMap::new();
    // (field, rule id) -> ops that rule used on that field.
    let mut writer_ops: HashMap<(String, String), HashSet<WriteOp>> = HashMap::new();
    for r in &facts {
        for (field, op) in &r.writes {
            writer_ids
                .entry(field.clone())
                .or_default()
                .insert(r.id.to_owned());
            writer_ops
                .entry((field.clone(), r.id.to_owned()))
                .or_default()
                .insert(*op);
        }
    }

    let mut stale_default_reads = Vec::new();
    for r in &facts {
        for b in &r.bindings {
            if !b.optional || b.default.is_none() {
                continue;
            }
            let BindSource::Field(field) = &b.source else {
                continue;
            };
            let Some(ids) = writer_ids.get(field) else {
                continue; // NO-WRITER
            };
            let mut offenders: Vec<&String> = ids
                .iter()
                .filter(|w| w.as_str() != r.id && w.as_bytes() >= r.id.as_bytes())
                .collect();
            offenders.sort_by(|a, b| a.as_bytes().cmp(b.as_bytes()));
            if let Some(writer) = offenders.first() {
                stale_default_reads.push(StaleDefaultRead {
                    reader_rule: r.id.to_owned(),
                    binding_name: b.name.clone(),
                    field: field.clone(),
                    writer_rule: (*writer).clone(),
                });
            }
        }
    }
    stale_default_reads.sort_by(|a, b| {
        (a.reader_rule.as_bytes(), a.field.as_bytes())
            .cmp(&(b.reader_rule.as_bytes(), b.field.as_bytes()))
    });

    let mut unreset_fan_ins = Vec::new();
    let mut fields: Vec<&String> = writer_ids.keys().collect();
    fields.sort_by(|a, b| a.as_bytes().cmp(b.as_bytes()));
    for field in fields {
        let mut writers: Vec<&String> = writer_ids[field].iter().collect();
        writers.sort_by(|a, b| a.as_bytes().cmp(b.as_bytes()));
        if writers.len() < 2 {
            continue; // not multi-writer
        }
        let earliest = writers[0];
        // `earliest` came out of `writer_ids`, itself built only from rule
        // ids present in `facts` — the lookup cannot miss.
        let earliest_rule = facts
            .iter()
            .find(|r| r.id == earliest.as_str())
            .expect("a writer rule id always names a rule in `facts`");
        let sets = writer_ops
            .get(&(field.clone(), earliest.clone()))
            .is_some_and(|ops| ops.contains(&WriteOp::Set));
        let discharged = earliest_rule.unconditional && (sets || earliest_rule.d127);
        if !discharged {
            unreset_fan_ins.push(UnresetFanIn {
                field: field.clone(),
                writers: writers.into_iter().cloned().collect(),
            });
        }
    }

    Diagnosis {
        stale_default_reads,
        unreset_fan_ins,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Parse a multi-rule content set through the REAL production entry
    /// point, `rule_pipeline::split_content`, discarding its
    /// `(intrinsic …)` half — `diagnose` needs only the paired
    /// `(rule_id, form)` list. W2 fix round 1 (review finding, discovered
    /// while building the corpus-wide inventory): an earlier version of
    /// this helper called `canonical_ast::rule_id` directly over every
    /// top-level form, which panicked on `decomposition.bsl`/
    /// `territory.bsl` — both declare a top-level `(intrinsic floor …)`
    /// form (§2.2), which is legal content `split_content` already knows
    /// to segregate. Reusing the real splitter here is also the DRY fix:
    /// one fewer place a second, narrower content-set parser could drift
    /// from the one the loader actually runs.
    fn rules(source: &str) -> Vec<(String, SExpr)> {
        crate::rule_pipeline::split_content(source)
            .expect("test fixture must be a legal content set")
            .1
    }

    // ---- W2.1(a): reader-before-writer refuses -------------------------

    #[test]
    fn a_reader_before_writer_optional_default_pair_refuses() {
        // `a/reader` sorts before `b/writer` — the writer does NOT sort
        // strictly before the reader, so refusal 1 must fire.
        let source = r#"
(rule a/reader :material-basis "x" :fuel 10
  (bindings (binding v :field ns/f :optional :default 0))
  (when #t)
  (effects (update-node self ns/other (set 1))))
(rule b/writer :material-basis "y" :fuel 10
  (bindings)
  (when #t)
  (effects (update-node self ns/f (set 1))))
"#;
        let diagnosis = diagnose(&rules(source));
        assert_eq!(diagnosis.stale_default_reads.len(), 1, "{diagnosis:?}");
        let finding = &diagnosis.stale_default_reads[0];
        assert_eq!(finding.reader_rule, "a/reader");
        assert_eq!(finding.writer_rule, "b/writer");
        assert_eq!(finding.field, "ns/f");
        assert_eq!(finding.binding_name, "v");
        let err = diagnosis.into_result().unwrap_err();
        assert_eq!(err.spec_code(), "E-LOAD-058");
        assert!(err.to_string().contains("a/reader"), "{err}");
        assert!(err.to_string().contains("b/writer"), "{err}");
        assert!(err.to_string().contains("ns/f"), "{err}");
    }

    /// The dual: a writer that DOES sort strictly before the reader must
    /// load clean under refusal 1.
    #[test]
    fn a_writer_sorting_before_the_reader_loads_clean() {
        let source = r#"
(rule a/writer :material-basis "x" :fuel 10
  (bindings)
  (when #t)
  (effects (update-node self ns/f (set 1))))
(rule b/reader :material-basis "y" :fuel 10
  (bindings (binding v :field ns/f :optional :default 0))
  (when #t)
  (effects (update-node self ns/other (set 1))))
"#;
        let diagnosis = diagnose(&rules(source));
        assert!(diagnosis.stale_default_reads.is_empty(), "{diagnosis:?}");
        assert!(diagnosis.into_result().is_ok());
    }

    // ---- W2.1(b): multi-writer, no earlier unconditional set, refuses --

    #[test]
    fn a_multi_writer_field_with_no_unconditional_set_refuses() {
        let source = r#"
(rule a/first :material-basis "x" :fuel 10
  (bindings)
  (when (> 1 0))
  (effects (update-node self ns/f (set 1))))
(rule b/second :material-basis "y" :fuel 10
  (bindings)
  (when (> 2 0))
  (effects (update-node self ns/f (add 1))))
"#;
        let diagnosis = diagnose(&rules(source));
        assert_eq!(diagnosis.unreset_fan_ins.len(), 1, "{diagnosis:?}");
        let finding = &diagnosis.unreset_fan_ins[0];
        assert_eq!(finding.field, "ns/f");
        assert_eq!(
            finding.writers,
            vec!["a/first".to_owned(), "b/second".to_owned()]
        );
        let err = diagnosis.into_result().unwrap_err();
        assert_eq!(err.spec_code(), "E-LOAD-059");
        assert!(err.to_string().contains("ns/f"), "{err}");
    }

    /// The dual: an EARLIER unconditional `set` discharges refusal 2.
    #[test]
    fn an_earlier_unconditional_set_discharges_the_fan_in_refusal() {
        let source = r#"
(rule a/reset :material-basis "x" :fuel 10
  (bindings)
  (when #t)
  (effects (update-node self ns/f (set 0))))
(rule b/accumulate :material-basis "y" :fuel 10
  (bindings)
  (when (> 1 0))
  (effects (update-node self ns/f (add 1))))
"#;
        let diagnosis = diagnose(&rules(source));
        assert!(diagnosis.unreset_fan_ins.is_empty(), "{diagnosis:?}");
    }

    /// A rule with NO `(when …)` at all is unconditional too (not only a
    /// literal `(when #t)`).
    #[test]
    fn a_writer_with_no_when_clause_at_all_is_unconditional() {
        let source = r#"
(rule a/reset :material-basis "x" :fuel 10
  (bindings)
  (effects (update-node self ns/f (set 0))))
(rule b/accumulate :material-basis "y" :fuel 10
  (bindings)
  (when (> 1 0))
  (effects (update-node self ns/f (add 1))))
"#;
        let diagnosis = diagnose(&rules(source));
        assert!(diagnosis.unreset_fan_ins.is_empty(), "{diagnosis:?}");
    }

    /// The D127-marked shape discharges refusal 2 even though its op is
    /// `add`, not `set` — the citation is the whole discharge, per this
    /// module's own doc.
    #[test]
    fn a_d127_cited_unconditional_writer_discharges_the_fan_in_refusal() {
        let source = r#"
(rule a/recompute :material-basis "D127 unconditional recompute" :fuel 10
  (bindings)
  (when #t)
  (effects (update-node self ns/f (add 0))))
(rule b/also-writes :material-basis "y" :fuel 10
  (bindings)
  (when (> 1 0))
  (effects (update-node self ns/f (add 1))))
"#;
        let diagnosis = diagnose(&rules(source));
        assert!(diagnosis.unreset_fan_ins.is_empty(), "{diagnosis:?}");
    }

    // ---- W2.1(c): row-37 self-exclusion, keyed on rule identity --------

    /// The row-37 shape: ONE rule reads field `f` on `self` and writes `f`
    /// on `it` — must LOAD, proving the self-exclusion is keyed on rule
    /// identity, not on write target (`self` vs `it`).
    #[test]
    fn the_row_37_shape_reads_self_writes_it_same_rule_loads_clean() {
        let source = r#"
(rule ns/only-rule :material-basis "x" :fuel 10
  (bindings (binding r :field ns/f :optional :default 0))
  (when #t)
  (effects (update-node it ns/f (set r))))
"#;
        let diagnosis = diagnose(&rules(source));
        assert!(
            diagnosis.stale_default_reads.is_empty(),
            "self-exclusion must be keyed on rule identity, not write target: {diagnosis:?}"
        );
        assert!(diagnosis.into_result().is_ok());
    }

    /// The mutation-check adjudication §(c) itself asks for: WITHOUT the
    /// self-exclusion, a rule that reads a field via `:optional :default`
    /// and also writes that SAME field to `self` would trip refusal 1 on
    /// almost every read-modify-write rule in the corpus. This fixture
    /// proves the positive control — a rule whose only "writer" of `f` is
    /// itself must load clean, matching `consciousness/p6-route`'s own
    /// shape (reads `r/l/f`, writes `r/l/f`, no OTHER writer).
    #[test]
    fn a_rule_that_only_writes_its_own_read_field_to_self_loads_clean() {
        let source = r#"
(rule ns/read-modify-write :material-basis "x" :fuel 10
  (bindings (binding v :field ns/f :optional :default 0))
  (when #t)
  (effects (update-node self ns/f (set v))))
"#;
        let diagnosis = diagnose(&rules(source));
        assert!(diagnosis.stale_default_reads.is_empty(), "{diagnosis:?}");
    }

    // ---- W2.4: the audit, against the real landed corpus -----------------

    const CONSCIOUSNESS_BSL: &str =
        include_str!("../../babylon-tick/content/rules/consciousness.bsl");
    const SOLIDARITY_BSL: &str = include_str!("../../babylon-tick/content/rules/solidarity.bsl");
    const DECOMPOSITION_BSL: &str =
        include_str!("../../babylon-tick/content/rules/decomposition.bsl");
    const CONTROL_RATIO_BSL: &str =
        include_str!("../../babylon-tick/content/rules/control-ratio.bsl");
    const PRODUCTION_BSL: &str = include_str!("../../babylon-tick/content/rules/production.bsl");
    const TERRITORY_BSL: &str = include_str!("../../babylon-tick/content/rules/territory.bsl");
    const VITALITY_BSL: &str = include_str!("../../babylon-tick/content/rules/vitality.bsl");
    const LIFECYCLE_BSL: &str = include_str!("../../babylon-tick/content/rules/lifecycle.bsl");
    const DISPOSSESSION_BSL: &str =
        include_str!("../../babylon-tick/content/rules/dispossession.bsl");
    const METABOLISM_BSL: &str = include_str!("../../babylon-tick/content/rules/metabolism.bsl");
    const ORGANIZATION_BSL: &str =
        include_str!("../../babylon-tick/content/rules/organization.bsl");
    const WORLDVIEW_BSL: &str = include_str!("../../babylon-tick/content/rules/worldview.bsl");
    const FUNDAMENTAL_THEOREM_BSL: &str =
        include_str!("../../babylon-tick/content/rules/fundamental-theorem.bsl");

    /// Refusal 1, gate forced ON, against `consciousness.bsl` loaded SOLO
    /// (its own content set — the W2 pre-audit's own finding: every
    /// committed load path loads this pack alone). Must name EXACTLY the
    /// 13 EXPOSED rows of the pre-audit table (rows 3-9, 14-16, 18, 20,
    /// 22) — not 23, not 24: this simultaneously proves the self-exclusion
    /// (which would otherwise flip rows 23-26 too, per adjudication §(c))
    /// and pins the audit's own headline number.
    #[test]
    fn refusal_1_fires_on_exactly_the_13_exposed_bindings_of_consciousness_bsl() {
        let diagnosis = diagnose(&rules(CONSCIOUSNESS_BSL));
        let mut got: Vec<(String, String)> = diagnosis
            .stale_default_reads
            .iter()
            .map(|f| (f.reader_rule.clone(), f.binding_name.clone()))
            .collect();
        got.sort();
        let mut want: Vec<(String, String)> = vec![
            ("consciousness/p0-position", "r"),
            ("consciousness/p0-position", "l"),
            ("consciousness/p0-position", "f"),
            ("consciousness/p1-inbox-reset", "r"),
            ("consciousness/p1-inbox-reset", "l"),
            ("consciousness/p1-inbox-reset", "f"),
            ("consciousness/p3-class-solidarity-push", "r"),
            ("consciousness/p5-agitation", "r"),
            ("consciousness/p5-agitation", "l"),
            ("consciousness/p5-agitation", "f"),
            ("consciousness/p5-agitation", "prev-wages"),
            ("consciousness/p5-agitation", "prev-wealth"),
            ("consciousness/p5-agitation", "agitation"),
        ]
        .into_iter()
        .map(|(r, b)| (r.to_owned(), b.to_owned()))
        .collect();
        want.sort();
        assert_eq!(got.len(), 13, "{got:#?}");
        assert_eq!(got, want);
    }

    /// `solidarity.bsl` loaded SOLO: refusal 1 must find ZERO violations —
    /// its two bindings are both NO-WRITER (one true, one self-excluded,
    /// row 37).
    #[test]
    fn refusal_1_is_silent_on_solidarity_bsl_loaded_solo() {
        let diagnosis = diagnose(&rules(SOLIDARITY_BSL));
        assert!(diagnosis.stale_default_reads.is_empty(), "{diagnosis:?}");
    }

    /// Refusal 2 against `consciousness.bsl` (this crate's own checkout,
    /// POST the W2.5 repair — `p1-inbox-reset`'s guard is `(when #t)`):
    /// exactly the r/l/f/agitation complementary-guard class — four
    /// fields, per the W2.4 adjudicated expectation — and NOTHING on
    /// either inbox field. Before W2.5's repair this assertion FAILS (six
    /// fields fire, including `wages-inbox` — the real latent defect
    /// adjudication §(d) found — and `solidarity-inbox`, a false
    /// positive); this is the RED signal W2.5's content repair turns
    /// GREEN, not a check this module's own logic satisfies unassisted.
    #[test]
    fn refusal_2_fires_on_exactly_the_r_l_f_agitation_complementary_guard_class() {
        let diagnosis = diagnose(&rules(CONSCIOUSNESS_BSL));
        let mut got: Vec<String> = diagnosis
            .unreset_fan_ins
            .iter()
            .map(|f| f.field.clone())
            .collect();
        got.sort();
        assert_eq!(
            got,
            vec![
                "social-class/agitation",
                "social-class/fascist",
                "social-class/liberal",
                "social-class/revolutionary",
            ],
            "{got:#?} — expected exactly the complementary-guard class; a \
             solidarity-inbox/wages-inbox appearance here means W2.5's \
             (when #t) repair on p1-inbox-reset has not landed (or regressed)"
        );
    }

    /// `solidarity.bsl` loaded SOLO: refusal 2 must find zero violations —
    /// its one multi-writer-eligible field (`revolutionary`) has only ONE
    /// writer rule within this solo content set (`solidarity/p0-transmit`
    /// itself), so it never reaches the 2-distinct-writers threshold.
    #[test]
    fn refusal_2_is_silent_on_solidarity_bsl_loaded_solo() {
        let diagnosis = diagnose(&rules(SOLIDARITY_BSL));
        assert!(diagnosis.unreset_fan_ins.is_empty(), "{diagnosis:?}");
    }

    /// W2 fix round 1, review finding C1 (Critical): refusal 1 has no
    /// unmeasured surface (`:optional :default` exists only in
    /// `consciousness.bsl`/`solidarity.bsl`, both already pinned above),
    /// but refusal 2 has NO such precondition — it can fire on any
    /// multi-writer field in ANY pack. This pins the exact finding set
    /// across all 13 landed packs solo, plus the two committed co-loads
    /// (`decomposition+control-ratio`, `carceral_arc_conformance.rs`;
    /// `vitality+lifecycle`, `multi_rule_conformance.rs`/
    /// `us_counties_demo.rs`/the client's `EngineSession`) — the complete
    /// content-set inventory `w2-preaudit-table.md` §1 already
    /// established as the whole committed surface, no third co-load
    /// exists. `fundamental-theorem.bsl` runs SOLO everywhere it loads
    /// (`engine_link.rs`'s `RULE` const, never combined with
    /// `DEMO_VITALITY`/`DEMO_LIFECYCLE` in one `format!`), so it needs no
    /// separate co-load entry.
    ///
    /// Six fields fire, across three packs, all classified in the W2 fix
    /// round 1 report (`task-w2-report.md` §"Fix round 1"): NONE are a
    /// real latent defect — `decomposition/{active,population,wealth}`
    /// and `production/production-value` are the complementary-guard
    /// class (role is scenario-seeded and never written by ANY rule in
    /// the corpus, confirmed by `rg 'social-class/role'
    /// content/rules/*.bsl` finding zero `update-node` sites; WAGES-edge
    /// existence is likewise immutable, confirmed by zero
    /// `add-edge`/`remove-edge` sites on `EdgeType/WAGES` anywhere);
    /// `production/wealth` and `territory/population` are false
    /// positives of a DIFFERENT kind — permanent, legitimately-
    /// accumulating economic/spatial stocks (never a this-tick-only
    /// carrier needing a reset), `territory.bsl`'s own header explicitly
    /// documenting the deliberate sequential-phase composition refusal 2
    /// mistakes for unreset fan-in ("camp decay eats this-tick displaced
    /// arrivals").
    #[test]
    fn refusal_2_inventory_over_the_whole_landed_corpus() {
        let solo_packs: &[(&str, &str)] = &[
            ("consciousness", CONSCIOUSNESS_BSL),
            ("solidarity", SOLIDARITY_BSL),
            ("decomposition", DECOMPOSITION_BSL),
            ("control-ratio", CONTROL_RATIO_BSL),
            ("production", PRODUCTION_BSL),
            ("territory", TERRITORY_BSL),
            ("vitality", VITALITY_BSL),
            ("lifecycle", LIFECYCLE_BSL),
            ("dispossession", DISPOSSESSION_BSL),
            ("metabolism", METABOLISM_BSL),
            ("organization", ORGANIZATION_BSL),
            ("worldview", WORLDVIEW_BSL),
            ("fundamental-theorem", FUNDAMENTAL_THEOREM_BSL),
        ];
        assert_eq!(
            solo_packs.len(),
            13,
            "the corpus is 13 packs — see w2-preaudit-table.md §0"
        );

        let mut got: Vec<(&str, String)> = Vec::new();
        for (name, src) in solo_packs {
            let diagnosis = diagnose(&rules(src));
            got.extend(
                diagnosis
                    .unreset_fan_ins
                    .into_iter()
                    .map(|f| (*name, f.field)),
            );
        }
        let deco_cr = format!("{DECOMPOSITION_BSL}\n{CONTROL_RATIO_BSL}");
        let diagnosis = diagnose(&rules(&deco_cr));
        got.extend(
            diagnosis
                .unreset_fan_ins
                .into_iter()
                .map(|f| ("decomposition+control-ratio", f.field)),
        );
        let vit_life = format!("{VITALITY_BSL}\n{LIFECYCLE_BSL}");
        let diagnosis = diagnose(&rules(&vit_life));
        got.extend(
            diagnosis
                .unreset_fan_ins
                .into_iter()
                .map(|f| ("vitality+lifecycle", f.field)),
        );
        got.sort();

        let mut want: Vec<(&str, String)> = vec![
            // consciousness solo (post-W2.5-repair) — the r/l/f/agitation
            // complementary-guard class this module's dedicated test
            // (`refusal_2_fires_on_exactly_the_r_l_f_agitation_
            // complementary_guard_class`) already pins in isolation;
            // repeated here so THIS test is the single source of truth
            // for the whole corpus, not just the other 12 packs.
            ("consciousness", "social-class/agitation"),
            ("consciousness", "social-class/fascist"),
            ("consciousness", "social-class/liberal"),
            ("consciousness", "social-class/revolutionary"),
            ("decomposition", "social-class/active"),
            ("decomposition", "social-class/population"),
            ("decomposition", "social-class/wealth"),
            ("decomposition+control-ratio", "social-class/active"),
            ("decomposition+control-ratio", "social-class/population"),
            ("decomposition+control-ratio", "social-class/wealth"),
            ("production", "social-class/production-value"),
            ("production", "social-class/wealth"),
            ("territory", "territory/population"),
        ]
        .into_iter()
        .map(|(pack, field)| (pack, field.to_owned()))
        .collect();
        want.sort();

        assert_eq!(
            got, want,
            "corpus-wide refusal-2 inventory drifted from the W2 fix round 1 \
             classification — re-triage any new/missing row before trusting \
             this test again (report.md's Fix-round-1 section)"
        );
    }
}
