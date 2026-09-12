//! Closed syntax for invoking the current material period; no host-call namespace.

use crate::material_basis::SurfaceError;
use crate::reader::{Atom, SExpr};
use crate::rule_pipeline::RuleExecution;

fn malformed(message: impl Into<String>) -> SurfaceError {
    SurfaceError::Malformed {
        message: format!("material-cycle: {}", message.into()),
    }
}

/// Classify a rule after the loader's bounded AST preflight. Finding this
/// form anywhere requires the complete closed rule shape, including when
/// someone tries to hide the invocation inside an expression or effect.
pub(crate) fn classify(rule: &SExpr) -> Result<RuleExecution, SurfaceError> {
    crate::causal_contract::validate_ast_walk_bounds(
        rule,
        crate::causal_contract::AST_WALK_LIMITS,
        "material-cycle classification",
    )
    .map_err(|error| malformed(error.to_string()))?;
    let mut stack = vec![rule];
    let mut found = false;
    while let Some(expr) = stack.pop() {
        if let SExpr::List(items) = expr {
            if head(items) == Some("material-cycle") {
                found = true;
                break;
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
    if !found {
        return Ok(RuleExecution::Graph);
    }
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
        remaining = &remaining[2..];
    }
    if seen != [true; 4] {
        return Err(malformed(
            "requires role, evidence, material-basis and fuel metadata",
        ));
    }
    let [SExpr::List(anchor), SExpr::List(invocation)] = remaining else {
        return Err(malformed(
            "requires only (anchor :after metabolism) followed by (material-cycle); bindings, domain, conditions and effects are forbidden",
        ));
    };
    if !matches!(anchor.as_slice(), [SExpr::Atom(Atom::Symbol(name)), SExpr::Atom(Atom::Keyword(position)), SExpr::Atom(Atom::Symbol(system))]
        if name == "anchor" && position == "after" && system == "metabolism")
    {
        return Err(malformed("requires exactly (anchor :after metabolism)"));
    }
    if !matches!(invocation.as_slice(), [SExpr::Atom(Atom::Symbol(name))] if name == "material-cycle")
    {
        return Err(malformed("requires one (material-cycle) with no operands"));
    }
    Ok(RuleExecution::MaterialCycle)
}

fn head(items: &[SExpr]) -> Option<&str> {
    match items.first() {
        Some(SExpr::Atom(Atom::Symbol(value))) => Some(value),
        _ => None,
    }
}
