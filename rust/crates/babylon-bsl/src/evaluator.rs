//! The fuel-metered BSL expression evaluator (`bsl-language.rst` §4) — the
//! RUNTIME backstop to Task 13's static bound (§3.7 computes the worst case
//! at load; §4.5's meter still runs, because the static bound's own
//! soundness is exactly what an adversarial reviewer should doubt).
//!
//! Scope (Phase 1 Task 14): the **expression core** — literals, variable
//! references, the two numeric lanes (§3.3), strictly binary arithmetic,
//! comparison, `and`/`or`/`not`, `if`, and the [`crate::intrinsic_host`]
//! boundary. Folds, queries, effects and `guard` need the graph substrate
//! and land with Task 16; meeting one here is a loud error naming that
//! seam, never a default.
//!
//! Semantics held to the letter of §4:
//! - **§4.1**: strict, call-by-value, left to right; `and`/`or`
//!   short-circuit and `if` evaluates only the taken branch — the two
//!   deliberate exceptions.
//! - **§4.3**: binary64 ops are the IEEE-754 basic set; `Int` overflow is
//!   `E-EVAL-011`; binary64 division by zero is `E-EVAL-012`; a non-finite
//!   result is `E-EVAL-014` — never representable. Currency follows the
//!   §3.2 operator table via `babylon_kernel::Currency`'s pinned operators
//!   (the panic preconditions checked here first, so a rule failure is a
//!   structured tick-abort, not a process abort).
//! - **§4.5**: each AST node charges its **base** cost when it is evaluated
//!   (the §3.7 numbers without the ceiling multiplication); reaching or
//!   passing zero is `E-EVAL-040`.
//!
//! Two implementation-discovered notes, recorded in the reference:
//! - The §3.7/§4.5 boundary is off by one: a rule whose worst case consumes
//!   exactly its `:fuel` loads (§3.7 rejects only `bound > :fuel`) yet
//!   `E-EVAL-040`s at runtime, because the meter must stay strictly
//!   positive ("reaching or passing zero"). Noted in §4.5.
//! - `Int ÷ Int` has no pinned semantics: truncation is never implicit
//!   (§3.2) and §3.3 promotes `Int` only "in a binary64 expression". It is
//!   a loud error here pending the Phase-1 review.

use crate::fuel::{cost, IntrinsicCosts};
use crate::intrinsic_host::IntrinsicHost;
use crate::reader::{Atom, SExpr};
use babylon_kernel::{Coefficient, Currency};
use std::collections::HashMap;

/// A runtime BSL value. The static type system (§3.1) is finer than this —
/// `Probability`/`Intensity`/`Coefficient`/`Real` are all the binary64 lane
/// at runtime; their `[0,1]` domains are load-time knowledge and the store
/// boundary's range check (`E-EVAL-020`, Task 16), per §3.3's
/// promote-to-`Real` ruling.
#[derive(Debug, Clone, PartialEq)]
pub enum Value {
    /// `Int` — `i64`, checked arithmetic (§4.3).
    Int(i64),
    /// `Currency` — i128 micro-units, the §3.2 operator table.
    Currency(Currency),
    /// The binary64 lane (§3.3): `Probability` / `Intensity` /
    /// `Coefficient` / `Real`, always finite (`E-EVAL-014` otherwise).
    Real(f64),
    /// `Bool`.
    Bool(bool),
    /// A member of a closed enum — comparable with `=`/`!=` only, and only
    /// to the same enum type (§3.1).
    Enum {
        /// The closed enum's type name.
        enum_type: String,
        /// The member identifier.
        member: String,
    },
    /// `NodeRef` (§3.1) — produced by `self`, `add-node`, and node-query
    /// elements. No arithmetic, no ordering; refs are identities.
    NodeRef(babylon_graph::substrate::NodeId),
    /// `HyperedgeRef` (§3.1) — produced by `add-hyperedge` and hyperedge-
    /// query elements. Does NOT carry its `HyperedgeType` statically, which
    /// is why §2.6's hyperedge queries take the type as an operand.
    HyperedgeRef(babylon_graph::substrate::HyperedgeId),
}

/// The spec's evaluation error codes (§4.6 / §3.2), one variant per code
/// this module can raise.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum EvalCode {
    /// `E-EVAL-010` — a `Currency` result below zero (domain `[0, ∞)`).
    CurrencyNegative,
    /// `E-EVAL-011` — `Int` or `Currency` overflow.
    Overflow,
    /// `E-EVAL-012` — division by zero (binary64 lane, `Currency ÷
    /// Currency`, or `Currency ÷ integer` with a zero-or-negative divisor).
    DivisionByZero,
    /// `E-EVAL-013` — a `Currency ÷ Currency` ratio outside `[0, 1]`.
    CoefficientOutOfRange,
    /// `E-EVAL-014` — a binary64 operation producing a non-finite result.
    NonFinite,
    /// `E-EVAL-020` — a store whose resulting value falls outside the
    /// target field's declared range (§3.3: the range check happens once,
    /// at the store boundary — a loud failure, never a clamp).
    StoreRangeViolation,
    /// `E-EVAL-021` — `mean`/`min`/`max` over an empty set (§4.4), and —
    /// the same code for the same reason (D45) — a `select-max`/
    /// `select-min` over an empty query: there is no element to return and
    /// there is no null.
    EmptyAggregate,
    /// `E-EVAL-031` — the §2.8 existence discipline: removing what does
    /// not exist, adding what exists, an unknown or duplicated hyperedge
    /// member. Absence is never treated as success.
    ExistenceDiscipline,
    /// `E-EVAL-032` — a `members-of`/`hyperedges-of` whose referent is not
    /// of the annotated `HyperedgeType` (D24) — never a silently empty set.
    HyperedgeTypeMismatch,
    /// `E-EVAL-033` — an accessor (§2.10) whose referent is not of the
    /// qname's owning type, or which carries no value for the named
    /// declared field. **Never** a default value and never an absent read
    /// (D34); also the runtime half of `E-TYPE-014` on the update verbs,
    /// whose element is a reference §3.1 gives no static type.
    AccessorTypeOrValueMismatch,
    /// `E-EVAL-034` — an `edge-between` that resolves to no edge (§2.10).
    /// The accessor never yields an absent reference and never degrades to
    /// a no-op write.
    NoSuchEdge,
    /// `E-EVAL-035` — `the` against a graph that hydrated no node of the
    /// `:ceiling 1` carrier type (§2.10): a carrier the scenario forgot to
    /// hydrate fails loudly rather than reading as zero.
    UnhydratedCarrier,
    /// `E-EVAL-036` — a `metric-of` whose referent is not of the metric's
    /// declared domain type (§2.11).
    MetricDomainMismatch,
    /// `E-EVAL-037` — a metric the provider produced no value for (§2.11).
    /// Absence is never a zero.
    MetricValueAbsent,
    /// `E-EVAL-040` — the fuel meter reached or passed zero.
    FuelExhausted,
    /// `E-EVAL-039` — the `floor` intrinsic's argument is outside its
    /// ratified domain (ADR188 Row 2, §3.10 / D97): negative, non-finite,
    /// or a result that does not fit `Int`'s `i64` domain (§3.1). Never a
    /// silent wraparound, and never a silently-chosen rounding convention
    /// for the disputed (negative) domain floor/trunc diverge on — a loud
    /// failure instead (III.11).
    DemotionOutOfDomain,
}

impl EvalCode {
    /// The spec's error code string.
    #[must_use]
    pub fn spec_code(self) -> &'static str {
        match self {
            Self::CurrencyNegative => "E-EVAL-010",
            Self::Overflow => "E-EVAL-011",
            Self::DivisionByZero => "E-EVAL-012",
            Self::CoefficientOutOfRange => "E-EVAL-013",
            Self::NonFinite => "E-EVAL-014",
            Self::StoreRangeViolation => "E-EVAL-020",
            Self::EmptyAggregate => "E-EVAL-021",
            Self::ExistenceDiscipline => "E-EVAL-031",
            Self::HyperedgeTypeMismatch => "E-EVAL-032",
            Self::AccessorTypeOrValueMismatch => "E-EVAL-033",
            Self::NoSuchEdge => "E-EVAL-034",
            Self::UnhydratedCarrier => "E-EVAL-035",
            Self::MetricDomainMismatch => "E-EVAL-036",
            Self::MetricValueAbsent => "E-EVAL-037",
            Self::FuelExhausted => "E-EVAL-040",
            Self::DemotionOutOfDomain => "E-EVAL-039",
        }
    }
}

/// A loud evaluation failure (§4.6: aborts the tick, never converted into
/// a default value, a skipped effect, or a log line). `code` is `None`
/// where the reference names no `E-EVAL` code for the condition — no
/// invented codes (the Task 10 precedent).
#[derive(Debug, Clone, PartialEq)]
pub struct EvalError {
    /// The spec's code, where one is named.
    pub code: Option<EvalCode>,
    /// What failed, precisely.
    pub message: String,
}

impl EvalError {
    /// A coded error.
    #[must_use]
    pub fn coded(code: EvalCode, message: impl Into<String>) -> Self {
        Self {
            code: Some(code),
            message: message.into(),
        }
    }

    /// A loud error the reference names no code for.
    #[must_use]
    pub fn plain(message: impl Into<String>) -> Self {
        Self {
            code: None,
            message: message.into(),
        }
    }
}

impl std::fmt::Display for EvalError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self.code {
            Some(code) => write!(f, "{}: {}", code.spec_code(), self.message),
            None => write!(f, "{}", self.message),
        }
    }
}

impl std::error::Error for EvalError {}

/// The evaluation environment (§4.2, the expression-core slice): resolved
/// binding values and the declared intrinsic costs. The graph, tick and
/// `self`/`it` references join with Task 16.
pub struct EvalEnv<'a> {
    /// Resolved rule bindings, name → value (binding resolution itself is
    /// the loader's job, §3.5 — unbound here means the loader failed).
    pub bindings: HashMap<String, Value>,
    /// Declared `:cost` per intrinsic (§2.7), for the §4.5 charge.
    pub intrinsic_costs: &'a IntrinsicCosts,
}

/// Evaluate `expr`, decrementing `*fuel` per §4.5. Fuel exhaustion should
/// be unreachable when Task 13's static bound accepted the rule with a
/// strictly larger budget — reaching it anyway is diagnostic of a
/// static-bound soundness bug, not merely "the rule was expensive".
///
/// # Errors
///
/// The coded §4.3/§3.2 arithmetic failures, `E-EVAL-040` on fuel
/// exhaustion, and loud uncoded errors for shapes outside the §2 grammar
/// or outside this task's expression core.
pub fn evaluate(
    expr: &SExpr,
    env: &EvalEnv<'_>,
    host: &dyn IntrinsicHost,
    fuel: &mut u64,
) -> Result<Value, EvalError> {
    match expr {
        SExpr::Atom(atom) => {
            charge(fuel, atom_charge(atom))?;
            atom_value(atom, env)
        }
        SExpr::List(items) => eval_form(items, env, host, fuel),
    }
}

/// §4.5: subtract `amount`, erroring when the meter would reach or pass
/// zero — it stays strictly positive. `pub(crate)` so the effect executor
/// (`structural_verbs`, Task 16) charges through the SAME meter — one §4.5
/// accounting, not two.
pub(crate) fn charge(fuel: &mut u64, amount: u64) -> Result<(), EvalError> {
    if amount >= *fuel {
        return Err(EvalError::coded(
            EvalCode::FuelExhausted,
            "fuel meter reached zero — if the static bound accepted this rule, \
             the bound is unsound: escalate, do not raise :fuel blindly",
        ));
    }
    *fuel -= amount;
    Ok(())
}

/// The §3.7 base charge for an atom: literals, enum-refs and field paths
/// cost 0; a symbol is a variable reference and costs 1.
fn atom_charge(atom: &Atom) -> u64 {
    match atom {
        Atom::Symbol(_) => cost::VARIABLE_REF,
        _ => cost::LITERAL,
    }
}

fn atom_value(atom: &Atom, env: &EvalEnv<'_>) -> Result<Value, EvalError> {
    match atom {
        Atom::Int(n) => Ok(Value::Int(*n)),
        Atom::Currency(c) => Ok(Value::Currency(*c)),
        Atom::Scaled(s) => {
            // A p/i/c literal is unit-interval with scale ≤ 9, so the
            // unscaled integer is < 10⁹ — exact in f64 by construction.
            #[allow(clippy::cast_precision_loss)]
            let value = s.unscaled as f64 / 10f64.powi(i32::from(s.scale));
            Ok(Value::Real(value))
        }
        Atom::Bool(b) => Ok(Value::Bool(*b)),
        Atom::EnumRef { enum_type, member } => Ok(Value::Enum {
            enum_type: enum_type.clone(),
            member: member.clone(),
        }),
        Atom::Symbol(name) => env.bindings.get(name).cloned().ok_or_else(|| {
            EvalError::plain(format!(
                "unbound variable: {name} — binding resolution is a load-time \
                 gate (E-LOAD-010, §3.5); reaching this at evaluation is a \
                 loader bug"
            ))
        }),
        other => Err(EvalError::plain(format!(
            "atom is not a value in expression position: {other:?}"
        ))),
    }
}

/// Form heads the expression core deliberately does NOT evaluate — they
/// need the graph substrate and land with Task 16.
/// The R9 chapters' new heads (§2.7's selections, §2.8's `for-each` and the
/// two new update verbs, §2.10's accessors) join the list rather than fall
/// through to `eval_intrinsic`: an accessor treated as an undeclared
/// intrinsic would report `E-LOAD-021`, which is the wrong diagnosis for a
/// form the language *does* have.
const GRAPH_SEAM_HEADS: [&str; 27] = [
    "fold",
    "exists",
    "forall",
    "nodes",
    "edges",
    "neighbors",
    "hyperedges",
    "members-of",
    "hyperedges-of",
    "guard",
    "for-each",
    "update-node",
    "update-edge",
    "update-hyperedge",
    "add-node",
    "remove-node",
    "add-edge",
    "remove-edge",
    "add-hyperedge",
    "remove-hyperedge",
    "emit",
    "select-max",
    "select-min",
    "field-of",
    "edge-between",
    "the",
    "metric-of",
];

fn eval_form(
    items: &[SExpr],
    env: &EvalEnv<'_>,
    host: &dyn IntrinsicHost,
    fuel: &mut u64,
) -> Result<Value, EvalError> {
    if let Some(SExpr::Atom(Atom::Operator(op))) = items.first() {
        return eval_operator(op, &items[1..], env, host, fuel);
    }
    let Some(SExpr::Atom(Atom::Symbol(head))) = items.first() else {
        return Err(EvalError::plain(format!(
            "a form must be headed by a symbol or operator in expression \
             position, found {:?}",
            items.first()
        )));
    };
    match head.as_str() {
        "and" | "or" => eval_and_or(head, &items[1..], env, host, fuel),
        "not" => {
            charge(fuel, cost::ARITH_CMP_BOOL_BASE)?;
            let [operand] = &items[1..] else {
                return Err(EvalError::plain("(not <cond>) takes exactly one operand"));
            };
            let value = as_bool(evaluate(operand, env, host, fuel)?)?;
            Ok(Value::Bool(!value))
        }
        "if" => eval_if(&items[1..], env, host, fuel),
        h if GRAPH_SEAM_HEADS.contains(&h)
            || matches!(h, "add" | "sub" | "set" | "scale" | "members") =>
        {
            Err(EvalError::plain(format!(
                "({h} …) is outside the Task 14 expression core — folds, \
                 queries, selections, accessors and effects evaluate against \
                 the graph substrate (Task 16 / the Phase-2 query evaluator), \
                 never as a default here"
            )))
        }
        name => eval_intrinsic(name, &items[1..], env, host, fuel),
    }
}

fn eval_operator(
    op: &str,
    operands: &[SExpr],
    env: &EvalEnv<'_>,
    host: &dyn IntrinsicHost,
    fuel: &mut u64,
) -> Result<Value, EvalError> {
    charge(fuel, cost::ARITH_CMP_BOOL_BASE)?;
    let [lhs_expr, rhs_expr] = operands else {
        return Err(EvalError::plain(format!(
            "({op} …) is strictly binary — ({op} a b c) is E-PARSE-040 (§2.7)"
        )));
    };
    let lhs = evaluate(lhs_expr, env, host, fuel)?;
    let rhs = evaluate(rhs_expr, env, host, fuel)?;
    match op {
        "+" | "-" | "*" | "/" => apply_arith(op, &lhs, &rhs),
        "<" | "<=" | ">" | ">=" => apply_ordering(op, &lhs, &rhs),
        "=" | "!=" => apply_equality(op, &lhs, &rhs),
        other => Err(EvalError::plain(format!("unknown operator: {other}"))),
    }
}

fn eval_and_or(
    head: &str,
    operands: &[SExpr],
    env: &EvalEnv<'_>,
    host: &dyn IntrinsicHost,
    fuel: &mut u64,
) -> Result<Value, EvalError> {
    charge(fuel, cost::ARITH_CMP_BOOL_BASE)?;
    if operands.is_empty() {
        return Err(EvalError::plain(format!(
            "({head}) with no operands is E-PARSE-021 — there is no implicit \
             identity element (§2.4)"
        )));
    }
    let stop_on = head == "or"; // and stops on #f, or stops on #t (§4.1)
    for operand in operands {
        let value = as_bool(evaluate(operand, env, host, fuel)?)?;
        if value == stop_on {
            return Ok(Value::Bool(stop_on)); // deliberate short-circuit
        }
    }
    Ok(Value::Bool(!stop_on))
}

fn eval_if(
    operands: &[SExpr],
    env: &EvalEnv<'_>,
    host: &dyn IntrinsicHost,
    fuel: &mut u64,
) -> Result<Value, EvalError> {
    charge(fuel, cost::IF_BASE)?;
    let [cond, then_branch, else_branch] = operands else {
        return Err(EvalError::plain(
            "(if <cond> <expr> <expr>) takes exactly three operands",
        ));
    };
    let taken = if as_bool(evaluate(cond, env, host, fuel)?)? {
        then_branch
    } else {
        else_branch
    };
    // §4.1: only the taken branch is evaluated (and therefore charged).
    evaluate(taken, env, host, fuel)
}

fn eval_intrinsic(
    name: &str,
    args: &[SExpr],
    env: &EvalEnv<'_>,
    host: &dyn IntrinsicHost,
    fuel: &mut u64,
) -> Result<Value, EvalError> {
    let Some(declared) = env.intrinsic_costs.declared_cost(name) else {
        return Err(EvalError::plain(format!(
            "call to undeclared intrinsic {name} — a load-time gate \
             (E-LOAD-021, §2.7); reaching this at evaluation is a loader bug"
        )));
    };
    charge(fuel, cost::INTRINSIC_CALL_BASE.saturating_add(declared))?;
    let mut values = Vec::with_capacity(args.len());
    for arg in args {
        values.push(evaluate(arg, env, host, fuel)?);
    }
    host.call(name, &values)
}

fn as_bool(value: Value) -> Result<bool, EvalError> {
    match value {
        Value::Bool(b) => Ok(b),
        other => Err(EvalError::plain(format!(
            "expected Bool where a <cond> is required, got {other:?}"
        ))),
    }
}

/// The binary64 view of a value, for the promoting lane (§3.3: `Int`
/// promotes to `Real` in a binary64 expression, never to `Currency`).
fn real_lane(value: &Value) -> Option<f64> {
    match value {
        Value::Real(r) => Some(*r),
        // i64 → f64 is round-to-nearest and deterministic; exactness above
        // 2⁵³ is not promised by §3.3's promotion, determinism is.
        #[allow(clippy::cast_precision_loss)]
        Value::Int(n) => Some(*n as f64),
        _ => None,
    }
}

fn apply_arith(op: &str, lhs: &Value, rhs: &Value) -> Result<Value, EvalError> {
    match (lhs, rhs) {
        (Value::Int(a), Value::Int(b)) => arith_int(op, *a, *b),
        (Value::Currency(a), Value::Currency(b)) => arith_currency(op, *a, *b),
        (Value::Currency(c), Value::Int(divisor)) if op == "/" => {
            currency_div_integer(*c, *divisor)
        }
        (Value::Currency(c), other) | (other, Value::Currency(c)) if op == "*" => {
            // §3.2: Currency multiplies by a Coefficient ONLY. `Real` is the
            // runtime coefficient carrier (c-literals and bindings land
            // there; the [0,1] domain is enforced below) — `Int` is a type
            // error at ANY value (bsl-language.rst:849), so it must not
            // slip through the promoting lane even where its f64 image
            // would be a legal coefficient (0 and 1).
            let Value::Real(coeff) = other else {
                return Err(EvalError::plain(format!(
                    "Currency × {other:?} is not in the §3.2 operator table \
                     (E-TYPE-030) — multiply by a Coefficient instead"
                )));
            };
            currency_mul_coefficient(*c, *coeff)
        }
        (Value::Currency(_), other) | (other, Value::Currency(_)) => {
            Err(EvalError::plain(format!(
                "Currency {op} {other:?} is not in the §3.2 operator table \
                 (E-TYPE-030) — the four pinned operations are ± Currency, \
                 × Coefficient, ÷ Currency, ÷ integer"
            )))
        }
        _ => match (real_lane(lhs), real_lane(rhs)) {
            (Some(a), Some(b)) => arith_real(op, a, b),
            _ => Err(EvalError::plain(format!(
                "no arithmetic is defined on ({op} {lhs:?} {rhs:?})"
            ))),
        },
    }
}

fn arith_int(op: &str, a: i64, b: i64) -> Result<Value, EvalError> {
    let overflow = || {
        EvalError::coded(
            EvalCode::Overflow,
            format!("Int overflow: ({op} {a} {b}) leaves i64"),
        )
    };
    match op {
        "+" => a.checked_add(b).map(Value::Int).ok_or_else(overflow),
        "-" => a.checked_sub(b).map(Value::Int).ok_or_else(overflow),
        "*" => a.checked_mul(b).map(Value::Int).ok_or_else(overflow),
        "/" => Err(EvalError::plain(
            "Int ÷ Int has no pinned semantics: truncation is never implicit \
             (§3.2) and §3.3 promotes Int only in a binary64 expression — \
             flagged for the Phase-1 review; divide in the binary64 lane or \
             use Currency ÷ integer",
        )),
        _ => Err(EvalError::plain(format!(
            "unknown arithmetic operator {op}"
        ))),
    }
}

fn arith_real(op: &str, a: f64, b: f64) -> Result<Value, EvalError> {
    if op == "/" && b == 0.0 {
        return Err(EvalError::coded(
            EvalCode::DivisionByZero,
            "division by zero in the binary64 lane",
        ));
    }
    let result = match op {
        "+" => a + b,
        "-" => a - b,
        "*" => a * b,
        "/" => a / b,
        _ => {
            return Err(EvalError::plain(format!(
                "unknown arithmetic operator {op}"
            )))
        }
    };
    if result.is_finite() {
        Ok(Value::Real(result))
    } else {
        Err(EvalError::coded(
            EvalCode::NonFinite,
            format!("({op} {a} {b}) produced a non-finite binary64 result"),
        ))
    }
}

fn arith_currency(op: &str, a: Currency, b: Currency) -> Result<Value, EvalError> {
    match op {
        "+" | "-" => {
            let result = if op == "+" {
                a.checked_add(b)
            } else {
                a.checked_sub(b)
            }
            .map_err(|e| EvalError::coded(EvalCode::Overflow, format!("{} left i128", e.op)))?;
            if result.micro_units() < 0 {
                return Err(EvalError::coded(
                    EvalCode::CurrencyNegative,
                    "Currency result below zero — the domain is [0, ∞) (§3.2)",
                ));
            }
            Ok(Value::Currency(result))
        }
        "/" => {
            // Pre-check div_currency's panic preconditions so a rule
            // failure is a structured tick-abort (§4.6), never a process
            // abort: zero divisor is E-EVAL-012; a ratio outside [0,1] is
            // E-EVAL-013.
            if b.micro_units() == 0 {
                return Err(EvalError::coded(
                    EvalCode::DivisionByZero,
                    "Currency ÷ Currency with a zero divisor",
                ));
            }
            let in_domain = if b.micro_units() > 0 {
                (0..=b.micro_units()).contains(&a.micro_units())
            } else {
                (b.micro_units()..=0).contains(&a.micro_units())
            };
            if !in_domain {
                return Err(EvalError::coded(
                    EvalCode::CoefficientOutOfRange,
                    "Currency ÷ Currency ratio outside the Coefficient [0,1] domain",
                ));
            }
            Ok(Value::Real(a.div_currency(b).get()))
        }
        "*" => Err(EvalError::plain(
            "Currency × Currency is E-TYPE-030 (an area of money) — \
             multiply by a Coefficient instead (§3.2)",
        )),
        _ => Err(EvalError::plain(format!(
            "unknown arithmetic operator {op}"
        ))),
    }
}

fn currency_div_integer(c: Currency, divisor: i64) -> Result<Value, EvalError> {
    if divisor <= 0 {
        return Err(EvalError::coded(
            EvalCode::DivisionByZero,
            "Currency ÷ integer with a zero or negative divisor (§3.2)",
        ));
    }
    Ok(Value::Currency(c.div_integer(i128::from(divisor))))
}

fn currency_mul_coefficient(c: Currency, coeff: f64) -> Result<Value, EvalError> {
    let coefficient = Coefficient::new(coeff).map_err(|_| {
        EvalError::plain(format!(
            "Currency × {coeff} — the multiplier is outside the Coefficient \
             [0,1] domain, so the expression is Currency × Real, which is \
             E-TYPE-030 (§3.2); the typechecker is the primary gate here"
        ))
    })?;
    let result = c
        .mul_coefficient(coefficient)
        .map_err(|e| EvalError::coded(EvalCode::Overflow, format!("{} left i128", e.op)))?;
    Ok(Value::Currency(result))
}

fn apply_ordering(op: &str, lhs: &Value, rhs: &Value) -> Result<Value, EvalError> {
    let ordering = match (lhs, rhs) {
        (Value::Int(a), Value::Int(b)) => a.cmp(b),
        (Value::Currency(a), Value::Currency(b)) => a.micro_units().cmp(&b.micro_units()),
        _ => match (real_lane(lhs), real_lane(rhs)) {
            // Values are finite by construction (E-EVAL-014), so binary64
            // ordering is total here.
            (Some(a), Some(b)) => a
                .partial_cmp(&b)
                .ok_or_else(|| EvalError::plain("non-finite value reached a comparison"))?,
            _ => {
                return Err(EvalError::plain(format!(
                    "({op} {lhs:?} {rhs:?}) — ordering is defined within one \
                     numeric lane only (Enum and Bool compare with =/!= alone, \
                     §3.1)"
                )))
            }
        },
    };
    let result = match op {
        "<" => ordering.is_lt(),
        "<=" => ordering.is_le(),
        ">" => ordering.is_gt(),
        ">=" => ordering.is_ge(),
        _ => return Err(EvalError::plain(format!("unknown ordering operator {op}"))),
    };
    Ok(Value::Bool(result))
}

fn apply_equality(op: &str, lhs: &Value, rhs: &Value) -> Result<Value, EvalError> {
    let equal = match (lhs, rhs) {
        (Value::Bool(a), Value::Bool(b)) => a == b,
        (
            Value::Enum {
                enum_type: ta,
                member: ma,
            },
            Value::Enum {
                enum_type: tb,
                member: mb,
            },
        ) => {
            if ta != tb {
                return Err(EvalError::plain(format!(
                    "Enum<{ta}> compares only to the same enum type, found \
                     Enum<{tb}> (§3.1)"
                )));
            }
            ma == mb
        }
        (Value::Int(a), Value::Int(b)) => a == b,
        (Value::Currency(a), Value::Currency(b)) => a == b,
        // Exact IEEE-754 equality: the basic ops are correctly rounded and
        // reproduce bit-exactly (§4.3), so exact comparison is
        // deterministic — clippy's suggested epsilon margin would be an
        // invented semantics the spec does not have.
        _ => match (real_lane(lhs), real_lane(rhs)) {
            #[allow(clippy::float_cmp)]
            (Some(a), Some(b)) => a == b,
            _ => {
                return Err(EvalError::plain(format!(
                    "({op} {lhs:?} {rhs:?}) — equality is defined within one \
                     lane only"
                )))
            }
        },
    };
    Ok(Value::Bool(if op == "=" { equal } else { !equal }))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::intrinsic_host::EmptyIntrinsicHost;
    use crate::reader::read;
    use std::collections::HashMap;

    fn costs() -> IntrinsicCosts {
        IntrinsicCosts::new(HashMap::from([("double".to_owned(), 4)]))
    }

    fn eval_with(
        source: &str,
        bindings: HashMap<String, Value>,
        fuel: &mut u64,
    ) -> Result<Value, EvalError> {
        let costs = costs();
        let env = EvalEnv {
            bindings,
            intrinsic_costs: &costs,
        };
        let (expr, _) = read(source).expect("test source must parse");
        evaluate(&expr, &env, &EmptyIntrinsicHost, fuel)
    }

    fn eval(source: &str) -> Result<Value, EvalError> {
        let mut fuel = 10_000;
        eval_with(source, HashMap::new(), &mut fuel)
    }

    fn wealth_bindings() -> HashMap<String, Value> {
        HashMap::from([(
            "wealth".to_owned(),
            Value::Currency(Currency::from_micro_units(900_000_000)), // 900$
        )])
    }

    #[test]
    fn the_demo_rule_condition_evaluates_with_pinned_fuel() {
        // The §5.6 rule's condition against wealth = 900$: true, and the
        // consumed fuel is exactly the static per-node sum — cmp(1) +
        // variable-ref(1) + literal(0) = 2 of the declared 64.
        let mut fuel = 64;
        let result = eval_with("(< wealth 1000.5$)", wealth_bindings(), &mut fuel).unwrap();
        assert_eq!(result, Value::Bool(true));
        assert_eq!(
            fuel, 62,
            ":fuel-used is a conformance-vector quantity (§6.1)"
        );
    }

    #[test]
    fn arithmetic_is_strictly_binary() {
        let err = eval("(+ 1 2 3)").unwrap_err();
        assert!(err.message.contains("E-PARSE-040"), "{err}");
        assert_eq!(eval("(+ 1 2)").unwrap(), Value::Int(3));
    }

    #[test]
    fn int_arithmetic_is_checked_i64() {
        assert_eq!(eval("(* 3 4)").unwrap(), Value::Int(12));
        let err = eval("(* 9223372036854775807 2)").unwrap_err();
        assert_eq!(err.code, Some(EvalCode::Overflow));
        assert_eq!(err.code.unwrap().spec_code(), "E-EVAL-011");
    }

    #[test]
    fn int_division_is_a_loud_unpinned_gap_not_truncation() {
        let err = eval("(/ 4 2)").unwrap_err();
        assert_eq!(err.code, None);
        assert!(err.message.contains("no pinned semantics"), "{err}");
    }

    #[test]
    fn int_promotes_to_real_in_a_binary64_expression() {
        assert_eq!(eval("(+ 1 0.5c)").unwrap(), Value::Real(1.5));
        assert_eq!(eval("(* 2 0.25p)").unwrap(), Value::Real(0.5));
    }

    #[test]
    fn binary64_division_by_zero_is_e_eval_012() {
        let err = eval("(/ 1 0.0c)").unwrap_err();
        assert_eq!(err.code, Some(EvalCode::DivisionByZero));
    }

    #[test]
    fn a_non_finite_binary64_result_is_e_eval_014() {
        // Square (1e9 + 0.5) six times: finite through 1e288, then inf.
        let mut source = "(+ 1000000000 0.5c)".to_owned();
        for _ in 0..6 {
            source = format!("(* {source} {source})");
        }
        let err = eval(&source).unwrap_err();
        assert_eq!(err.code, Some(EvalCode::NonFinite));
        assert_eq!(err.code.unwrap().spec_code(), "E-EVAL-014");
    }

    #[test]
    fn currency_addition_and_subtraction_are_checked_both_ends() {
        assert_eq!(
            eval("(+ 900$ 100.5$)").unwrap(),
            Value::Currency(Currency::from_micro_units(1_000_500_000))
        );
        // Below zero: E-EVAL-010, the [0, ∞) domain — never a signed result.
        let err = eval("(- 100$ 200$)").unwrap_err();
        assert_eq!(err.code, Some(EvalCode::CurrencyNegative));
        // i128 overflow through a binding: E-EVAL-011.
        let big = HashMap::from([(
            "hoard".to_owned(),
            Value::Currency(Currency::from_micro_units(i128::MAX)),
        )]);
        let mut fuel = 10_000;
        let err = eval_with("(+ hoard hoard)", big, &mut fuel).unwrap_err();
        assert_eq!(err.code, Some(EvalCode::Overflow));
    }

    #[test]
    fn currency_times_coefficient_rounds_half_even_and_commutes() {
        let half = Value::Currency(Currency::from_micro_units(500_000_000));
        assert_eq!(eval("(* 1000$ 0.5c)").unwrap(), half);
        assert_eq!(eval("(* 0.5c 1000$)").unwrap(), half);
    }

    /// §3.2 (bsl-language.rst:849): "``Currency × Int`` [is a] type error;
    /// multiply by a ``Coefficient`` or divide by an ``Int`` instead" — at
    /// ANY value. `Int` must not slip through the promoting lane even where
    /// its f64 image would be a valid coefficient (0 and 1), in either
    /// operand order.
    #[test]
    fn currency_times_int_is_rejected_at_every_value() {
        for src in ["(* 1000$ 1)", "(* 1 1000$)", "(* 1000$ 0)", "(* 3 1000$)"] {
            let err = eval(src).expect_err(src);
            assert!(
                err.message.contains("E-TYPE-030"),
                "{src}: expected the §3.2 operator-table rejection, got: {}",
                err.message
            );
        }
    }

    #[test]
    fn currency_ratio_is_a_coefficient_with_both_domain_codes() {
        assert_eq!(eval("(/ 500$ 1000$)").unwrap(), Value::Real(0.5));
        let over = eval("(/ 1000$ 500$)").unwrap_err();
        assert_eq!(over.code, Some(EvalCode::CoefficientOutOfRange));
        let zero = eval("(/ 500$ 0$)").unwrap_err();
        assert_eq!(zero.code, Some(EvalCode::DivisionByZero));
    }

    #[test]
    fn currency_div_integer_is_half_even_and_rejects_nonpositive_divisors() {
        assert_eq!(
            eval("(/ 1000$ 4)").unwrap(),
            Value::Currency(Currency::from_micro_units(250_000_000))
        );
        let err = eval("(/ 1000$ -4)").unwrap_err();
        assert_eq!(err.code, Some(EvalCode::DivisionByZero));
    }

    #[test]
    fn off_table_currency_mixes_are_loud_type_shaped_errors() {
        for source in ["(+ 100$ 1)", "(* 100$ 2)", "(* 100$ 200$)"] {
            let err = eval(source).unwrap_err();
            assert_eq!(err.code, None, "{source}");
            assert!(err.message.contains("E-TYPE-030"), "{source}: {err}");
        }
    }

    #[test]
    fn comparisons_stay_within_one_lane() {
        assert_eq!(eval("(< 900$ 1000.5$)").unwrap(), Value::Bool(true));
        assert_eq!(eval("(>= 3 3)").unwrap(), Value::Bool(true));
        assert_eq!(eval("(< 0 0.5c)").unwrap(), Value::Bool(true));
        let err = eval("(< 100$ 0.5c)").unwrap_err();
        assert_eq!(err.code, None);
    }

    #[test]
    fn enum_members_compare_with_equality_only_within_one_type() {
        assert_eq!(
            eval("(= NodeType/SOCIAL_CLASS NodeType/SOCIAL_CLASS)").unwrap(),
            Value::Bool(true)
        );
        assert_eq!(
            eval("(!= NodeType/SOCIAL_CLASS NodeType/TERRITORY)").unwrap(),
            Value::Bool(true)
        );
        assert!(eval("(= NodeType/SOCIAL_CLASS EdgeType/SOLIDARITY)").is_err());
        assert!(eval("(< NodeType/SOCIAL_CLASS NodeType/TERRITORY)").is_err());
    }

    #[test]
    fn and_and_or_short_circuit_left_to_right() {
        // The unbound second operand would be a loud error if evaluated;
        // the short-circuit means it never is (§4.1's deliberate exception).
        assert_eq!(
            eval("(and (< 1 0) undeclared-var)").unwrap(),
            Value::Bool(false)
        );
        assert_eq!(
            eval("(or (< 0 1) undeclared-var)").unwrap(),
            Value::Bool(true)
        );
        let err = eval("(and)").unwrap_err();
        assert!(err.message.contains("E-PARSE-021"), "{err}");
    }

    #[test]
    fn if_evaluates_and_charges_only_the_taken_branch() {
        let mut fuel = 100;
        let result = eval_with("(if (< 0 1) 1 undeclared-var)", HashMap::new(), &mut fuel);
        assert_eq!(result.unwrap(), Value::Int(1));
        // if(1) + cmp(1) + two literals(0) + taken literal(0) = 2 consumed.
        assert_eq!(fuel, 98);
    }

    #[test]
    fn not_negates_bools_and_rejects_numbers() {
        assert_eq!(eval("(not #f)").unwrap(), Value::Bool(true));
        assert!(eval("(not 1)").is_err());
    }

    #[test]
    fn unbound_variables_are_loud_loader_bugs_never_defaults() {
        let err = eval("(+ 1 undeclared-var)").unwrap_err();
        assert!(err.message.contains("E-LOAD-010"), "{err}");
    }

    #[test]
    fn fuel_exhaustion_at_the_exact_boundary_is_e_eval_040() {
        // (< wealth 1000.5$) consumes 2. A meter of 2 reaches zero on the
        // second charge — E-EVAL-040 by §4.5's "reaching or passing zero";
        // a meter of 3 stays strictly positive and succeeds.
        let mut starved = 2;
        let err = eval_with("(< wealth 1000.5$)", wealth_bindings(), &mut starved).unwrap_err();
        assert_eq!(err.code, Some(EvalCode::FuelExhausted));
        assert_eq!(err.code.unwrap().spec_code(), "E-EVAL-040");
        let mut enough = 3;
        assert!(eval_with("(< wealth 1000.5$)", wealth_bindings(), &mut enough).is_ok());
        assert_eq!(enough, 1);
    }

    #[test]
    fn intrinsic_calls_charge_declared_cost_and_cross_the_host_boundary() {
        struct Doubler;
        impl crate::intrinsic_host::IntrinsicHost for Doubler {
            fn call(&self, name: &str, args: &[Value]) -> Result<Value, EvalError> {
                assert_eq!(name, "double");
                match args {
                    [Value::Int(n)] => Ok(Value::Int(n * 2)),
                    other => Err(EvalError::plain(format!("bad args {other:?}"))),
                }
            }
        }
        let costs = costs();
        let env = EvalEnv {
            bindings: HashMap::new(),
            intrinsic_costs: &costs,
        };
        let (expr, _) = read("(double 5)").unwrap();
        let mut fuel = 100;
        let result = evaluate(&expr, &env, &Doubler, &mut fuel).unwrap();
        assert_eq!(result, Value::Int(10));
        // base(5) + declared(4) + literal arg(0) = 9 consumed.
        assert_eq!(fuel, 91);
        // The empty host fails loud on the same call.
        let mut fuel2 = 100;
        assert!(evaluate(&expr, &env, &EmptyIntrinsicHost, &mut fuel2).is_err());
        // An intrinsic with no declared cost is a loud loader-bug error.
        let err = eval("(sigmoid 0.5c)").unwrap_err();
        assert!(err.message.contains("E-LOAD-021"), "{err}");
    }

    /// End-to-end: `(floor x)` through the real evaluator and the real
    /// `KernelIntrinsicHost` (ADR188 Row 2), not a test double — proves the
    /// fuel-metered call boundary and the intrinsic's own domain check
    /// compose correctly.
    #[test]
    fn floor_call_evaluates_through_the_kernel_intrinsic_host() {
        let costs = IntrinsicCosts::new(HashMap::from([("floor".to_owned(), 3)]));
        let env = EvalEnv {
            bindings: HashMap::from([("x".to_owned(), Value::Real(7.8))]),
            intrinsic_costs: &costs,
        };
        let (expr, _) = read("(floor x)").unwrap();
        let mut fuel = 100;
        let result = evaluate(
            &expr,
            &env,
            &crate::intrinsic_host::KernelIntrinsicHost,
            &mut fuel,
        )
        .unwrap();
        assert_eq!(result, Value::Int(7));

        // A negative binding surfaces the intrinsic's own E-EVAL-039,
        // through the full evaluator, not just the unit-tested host.
        let neg_env = EvalEnv {
            bindings: HashMap::from([("x".to_owned(), Value::Real(-2.5))]),
            intrinsic_costs: &costs,
        };
        let mut fuel2 = 100;
        let err = evaluate(
            &expr,
            &neg_env,
            &crate::intrinsic_host::KernelIntrinsicHost,
            &mut fuel2,
        )
        .unwrap_err();
        assert_eq!(err.code, Some(EvalCode::DemotionOutOfDomain));
        assert_eq!(err.code.unwrap().spec_code(), "E-EVAL-039");
    }

    #[test]
    fn graph_seam_forms_are_loud_task_16_errors_never_defaults() {
        for source in [
            "(fold sum (nodes NodeType/SOCIAL_CLASS) it)",
            "(exists (nodes NodeType/SOCIAL_CLASS))",
            "(update-node self social-class/agitation (add 0.05i))",
            "(guard #t (emit EventType/RUPTURE))",
        ] {
            let err = eval(source).unwrap_err();
            assert!(err.message.contains("Task 16"), "{source}: {err}");
        }
    }
}
