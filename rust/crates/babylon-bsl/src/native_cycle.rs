//! Closed scheduled operations with fixed roles and no host-call namespace.

use crate::material_basis::SurfaceError;
use crate::reader::{Atom, SExpr};
use crate::rule_pipeline::RuleExecution;

fn malformed(message: impl Into<String>) -> SurfaceError {
    SurfaceError::Malformed {
        message: format!("native cycle: {}", message.into()),
    }
}

/// Classify a rule after the loader's bounded AST preflight. Finding this
/// form anywhere requires the complete closed rule shape, including when
/// someone tries to hide the invocation inside an expression or effect.
pub(crate) fn classify(rule: &SExpr) -> Result<RuleExecution, SurfaceError> {
    crate::causal_contract::validate_ast_walk_bounds(
        rule,
        crate::causal_contract::AST_WALK_LIMITS,
        "native cycle classification",
    )
    .map_err(|error| malformed(error.to_string()))?;
    let Some(operation) = find_operation(rule) else {
        return Ok(RuleExecution::Graph);
    };
    let (execution, causal_role, position, system) = match operation {
        "material-cycle" => (RuleExecution::MaterialCycle, None, "after", "metabolism"),
        "organizer-products" => (
            RuleExecution::OrganizerProducts,
            Some("mechanic"),
            "before",
            "ooda",
        ),
        "organizer-practice" => (
            RuleExecution::OrganizerPractice,
            Some("intent"),
            "after",
            "ooda",
        ),
        _ => unreachable!("only closed operation names enter classification"),
    };
    let SExpr::List(items) = rule else {
        unreachable!("an atom cannot contain a material-cycle form")
    };
    let mut remaining = items.get(2..).ok_or_else(|| malformed("expected a rule"))?;
    let mut seen = [false; 4];
    while let Some(SExpr::Atom(Atom::Keyword(keyword))) = remaining.first() {
        let index = match keyword.as_str() {
            "role" => 0,
            "evidence" => 1,
            "material-basis" => 2,
            "fuel" => 3,
            _ => return Err(malformed(format!("unexpected keyword :{keyword}"))),
        };
        if seen[index] {
            return Err(malformed(format!("duplicate keyword :{keyword}")));
        }
        seen[index] = true;
        if !matches!(remaining.get(1), Some(SExpr::Atom(_))) {
            return Err(malformed(format!("missing value for :{keyword}")));
        }
        if keyword == "evidence"
            && !matches!(remaining.get(1), Some(SExpr::Atom(Atom::Symbol(value))) if value == "designed")
        {
            return Err(malformed("the invocation requires :evidence designed"));
        }
        if keyword == "role" && causal_role.is_some_and(|expected| {
            !matches!(remaining.get(1), Some(SExpr::Atom(Atom::Symbol(actual))) if actual == expected)
        }) {
            return Err(malformed(format!("{operation} requires its declared causal role")));
        }
        remaining = &remaining[2..];
    }
    if seen != [true; 4] {
        return Err(malformed(
            "requires role, evidence, material-basis and fuel metadata",
        ));
    }
    let [SExpr::List(anchor), SExpr::List(invocation)] = remaining else {
        return Err(malformed(
            "requires only the fixed anchor followed by one native operation; bindings, domain, conditions and effects are forbidden",
        ));
    };
    if !matches!(anchor.as_slice(), [SExpr::Atom(Atom::Symbol(name)), SExpr::Atom(Atom::Keyword(actual_position)), SExpr::Atom(Atom::Symbol(actual_system))]
        if name == "anchor" && actual_position == position && actual_system == system)
    {
        return Err(malformed(format!(
            "{operation} requires (anchor :{position} {system})"
        )));
    }
    if !matches!(invocation.as_slice(), [SExpr::Atom(Atom::Symbol(name))] if name == operation) {
        return Err(malformed(format!(
            "requires one ({operation}) with no operands"
        )));
    }
    Ok(execution)
}

/// The caller has already checked AST walk bounds.
fn find_operation(rule: &SExpr) -> Option<&str> {
    let mut stack = vec![rule];
    while let Some(expr) = stack.pop() {
        if let SExpr::List(items) = expr {
            if let Some(
                operation @ ("material-cycle" | "organizer-products" | "organizer-practice"),
            ) = head(items)
            {
                return Some(operation);
            }
            if head(items) == Some("emit")
                && matches!(items.get(1), Some(SExpr::Atom(Atom::EnumRef { .. })))
            {
                // A typed emit's payload names are labels. Inspect every
                // value, even in an over-arity row, without calling the label.
                for payload in items.iter().skip(2) {
                    if let SExpr::List(pair) = payload {
                        stack.extend(pair.iter().skip(1));
                    }
                }
            } else {
                // A malformed emit has no reliable payload/type positions.
                stack.extend(items);
            }
        }
    }
    None
}

fn head(items: &[SExpr]) -> Option<&str> {
    match items.first() {
        Some(SExpr::Atom(Atom::Symbol(value))) => Some(value),
        _ => None,
    }
}
