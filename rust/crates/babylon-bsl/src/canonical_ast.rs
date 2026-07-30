//! Canonical AST serialization — CAS (`bsl-language.rst` §5): the byte
//! layout `rules_hash` hashes. Whitespace-, comment-, file-layout- and
//! option-order-insensitive: a formatting edit produces identical bytes,
//! while any change to a rule's meaning — including its `:material-basis`
//! string and its `:fuel` budget — produces different bytes.
//!
//! **Deviation from the Phase 1 plan's sketch, recorded:** the sketch
//! rendered atoms as text with `0x00` separators and insertion-order
//! hashing. The normative §5 defines a BINARY tagged encoding (§5.1–5.2),
//! canonical child reordering with `opt`-wrapped keyword options (§5.3),
//! and `rules_hash = SHA-256(0x03 ‖ u32 N ‖ CAS(r_1) ‖ …)` over rules
//! **sorted by rule id** (§5.5) — implemented as written, and proved
//! against §5.6's own pinned worked example (421 bytes, both digests).
//!
//! Per §5.4 there are no stringify fallbacks: an unencodable node (an
//! operator outside form-head position, a form whose head is not a
//! symbol/operator, an empty form) fails loudly.

use crate::reader::{Atom, SExpr, ScaledKind};
use sha2::{Digest, Sha256};

/// A loud CAS failure (§5.4 bans silent fallbacks).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CasError {
    /// Human-readable detail.
    pub message: String,
}

/// The canonical bytes of one node (§5.1–§5.3).
///
/// # Errors
/// [`CasError`] on any unencodable node — never a stringified fallback.
pub fn canonical_bytes(expr: &SExpr) -> Result<Vec<u8>, CasError> {
    let mut out = Vec::new();
    encode_node(expr, &mut out)?;
    Ok(out)
}

/// `rules_hash = SHA-256(0x03 ‖ u32 N ‖ CAS(r_1) ‖ … ‖ CAS(r_N))` with
/// the rule forms sorted by rule id in ascending ASCII byte order (§5.5).
/// Duplicate rule ids are a LOAD error (`E-LOAD-001`), not CAS's concern;
/// with duplicates present the sort is still deterministic (stable).
///
/// # Errors
/// [`CasError`] if any form is not a `rule` form with a qname id, or any
/// node is unencodable.
pub fn rules_hash_of(rules: &[SExpr]) -> Result<[u8; 32], CasError> {
    let mut ids: Vec<(&str, &SExpr)> = Vec::with_capacity(rules.len());
    for rule in rules {
        ids.push((rule_id(rule)?, rule));
    }
    ids.sort_by(|a, b| a.0.as_bytes().cmp(b.0.as_bytes()));
    let mut hasher = Sha256::new();
    hasher.update([0x03]);
    let count = u32::try_from(ids.len()).map_err(|_| CasError {
        message: "more than u32::MAX rules".into(),
    })?;
    hasher.update(count.to_be_bytes());
    for (_, rule) in ids {
        hasher.update(canonical_bytes(rule)?);
    }
    Ok(hasher.finalize().into())
}

/// A `rule` form's id: the qname immediately after the head (§2.3).
fn rule_id(expr: &SExpr) -> Result<&str, CasError> {
    let SExpr::List(items) = expr else {
        return Err(CasError {
            message: "a rule must be a form".into(),
        });
    };
    match items.as_slice() {
        [SExpr::Atom(Atom::Symbol(head)), SExpr::Atom(Atom::QName(id)), ..] if head == "rule" => {
            Ok(id)
        }
        _ => Err(CasError {
            message: "rules_hash input must be (rule <qname-id> ...) forms".into(),
        }),
    }
}

fn encode_node(expr: &SExpr, out: &mut Vec<u8>) -> Result<(), CasError> {
    match expr {
        SExpr::Atom(atom) => encode_atom(atom, out),
        SExpr::List(items) => encode_form(items, out),
    }
}

/// `atom ::= 0x01  u8 len(kind)  kind_ascii  u32 len(payload)  payload`
/// with the §5.2 kind/payload table.
fn encode_atom(atom: &Atom, out: &mut Vec<u8>) -> Result<(), CasError> {
    let (kind, payload): (&str, Vec<u8>) = match atom {
        Atom::Int(v) => ("int", v.to_be_bytes().to_vec()),
        Atom::Currency(c) => ("cur", c.micro_units().to_be_bytes().to_vec()),
        Atom::Scaled(s) => {
            let kind = match s.kind {
                ScaledKind::Probability => "prob",
                ScaledKind::Intensity => "intn",
                ScaledKind::Coefficient => "coef",
            };
            let mut payload = s.unscaled.to_be_bytes().to_vec();
            payload.push(s.scale);
            (kind, payload)
        }
        Atom::Bool(b) => ("bool", vec![u8::from(*b)]),
        Atom::Symbol(s) => ("sym", s.clone().into_bytes()),
        Atom::QName(q) => ("qname", q.clone().into_bytes()),
        Atom::Keyword(k) => ("kw", k.clone().into_bytes()),
        Atom::EnumRef { enum_type, member } => {
            ("enum", format!("{enum_type}/{member}").into_bytes())
        }
        Atom::Str(s) => ("str", s.clone().into_bytes()),
        Atom::Operator(op) => {
            return Err(CasError {
                message: format!(
                    "operator '{op}' outside form-head position is unencodable (§5.4)"
                ),
            })
        }
    };
    write_atom(kind, &payload, out)
}

fn write_atom(kind: &str, payload: &[u8], out: &mut Vec<u8>) -> Result<(), CasError> {
    out.push(0x01);
    write_len_prefixed(kind.as_bytes(), payload, out)
}

fn write_len_prefixed(tag: &[u8], payload: &[u8], out: &mut Vec<u8>) -> Result<(), CasError> {
    let tag_len = u8::try_from(tag.len()).map_err(|_| CasError {
        message: "tag/kind name over 255 bytes".into(),
    })?;
    let payload_len = u32::try_from(payload.len()).map_err(|_| CasError {
        message: "payload over u32::MAX bytes".into(),
    })?;
    out.push(tag_len);
    out.extend_from_slice(tag);
    out.extend_from_slice(&payload_len.to_be_bytes());
    out.extend_from_slice(payload);
    Ok(())
}

/// One reordered child: a positional/body node, or an `opt`-wrapped
/// keyword option (a flag keyword wraps `#t`, per the §5.2 draft ruling).
enum Child<'a> {
    Node(&'a SExpr),
    Opt {
        name: &'a str,
        value: Option<&'a SExpr>,
    },
}

/// `form ::= 0x02  u8 len(tag)  tag_ascii  u32 nchildren  child*` with
/// §5.3's canonical child order: positional operands (source order), then
/// keyword options sorted by name in ascending ASCII byte order, then the
/// variadic body (source order). Generically: non-option children keep
/// source order; the sorted option block sits where the first option
/// appeared. A keyword followed by a non-keyword is a valued option; a
/// keyword followed by another keyword or the form's end is a flag.
fn encode_form(items: &[SExpr], out: &mut Vec<u8>) -> Result<(), CasError> {
    let Some((head, rest)) = items.split_first() else {
        return Err(CasError {
            message: "an empty form () has no tag (§5.2)".into(),
        });
    };
    let tag = match head {
        SExpr::Atom(Atom::Symbol(s)) => s.as_str(),
        SExpr::Atom(Atom::Operator(op)) => op.as_str(),
        _ => {
            return Err(CasError {
                message: "a form's head must be a symbol or operator (§5.2)".into(),
            })
        }
    };
    let mut positionals_before = Vec::new();
    let mut options: Vec<(&str, Option<&SExpr>)> = Vec::new();
    let mut body_after = Vec::new();
    let mut i = 0;
    while i < rest.len() {
        if let SExpr::Atom(Atom::Keyword(name)) = &rest[i] {
            let valued = rest
                .get(i + 1)
                .is_some_and(|next| !matches!(next, SExpr::Atom(Atom::Keyword(_))));
            if valued {
                options.push((name, Some(&rest[i + 1])));
                i += 2;
            } else {
                options.push((name, None));
                i += 1;
            }
        } else {
            if options.is_empty() {
                positionals_before.push(&rest[i]);
            } else {
                body_after.push(&rest[i]);
            }
            i += 1;
        }
    }
    options.sort_by(|a, b| a.0.as_bytes().cmp(b.0.as_bytes()));

    out.push(0x02);
    let n_children = positionals_before.len() + options.len() + body_after.len();
    let count = u32::try_from(n_children).map_err(|_| CasError {
        message: "form has more than u32::MAX children".into(),
    })?;
    let tag_len = u8::try_from(tag.len()).map_err(|_| CasError {
        message: "form tag over 255 bytes".into(),
    })?;
    out.push(tag_len);
    out.extend_from_slice(tag.as_bytes());
    out.extend_from_slice(&count.to_be_bytes());

    let children = positionals_before
        .into_iter()
        .map(Child::Node)
        .chain(
            options
                .into_iter()
                .map(|(name, value)| Child::Opt { name, value }),
        )
        .chain(body_after.into_iter().map(Child::Node));
    for child in children {
        match child {
            Child::Node(node) => encode_node(node, out)?,
            Child::Opt { name, value } => encode_opt(name, value, out)?,
        }
    }
    Ok(())
}

/// `opt ::= form("opt", atom("kw", <name>), <value node>)`; a flag keyword
/// encodes `atom("bool", 0x01)` as its value.
fn encode_opt(name: &str, value: Option<&SExpr>, out: &mut Vec<u8>) -> Result<(), CasError> {
    out.push(0x02);
    out.push(3); // len("opt")
    out.extend_from_slice(b"opt");
    out.extend_from_slice(&2u32.to_be_bytes());
    write_atom("kw", name.as_bytes(), out)?;
    match value {
        Some(node) => encode_node(node, out),
        None => write_atom("bool", &[0x01], out),
    }
}

#[cfg(test)]
mod tests {
    use super::{canonical_bytes, rules_hash_of};
    use crate::reader::{read, read_all};

    /// The §5.6 worked-example source, comment included (comments are
    /// whitespace and must not affect the bytes).
    const DEMO_RULE: &str = r#"
   ; a rule is data; this comment is not part of the hash
   (rule demo/hunger
     :material-basis "subsistence deficit at the point of reproduction"
     :fuel 64
     (bindings
       (binding wealth :field social-class/wealth))
     (when (< wealth 1000.5$))
     (effects
       (update-node self social-class/agitation (add 0.05i))))
"#;

    /// §5.6's pinned canonical bytes — 421 bytes, reproduced verbatim from
    /// the spec (which states both digests are "reproducible from this
    /// document alone").
    const PINNED_HEX: &str = concat!(
        "020472756c65000000060105716e616d650000000b64656d6f2f68756e676572",
        "02036f70740000000201026b77000000046675656c0103696e74000000080000",
        "00000000004002036f70740000000201026b770000000e6d6174657269616c2d",
        "626173697301037374720000003073756273697374656e636520646566696369",
        "742061742074686520706f696e74206f6620726570726f64756374696f6e0208",
        "62696e64696e677300000001020762696e64696e6700000002010373796d0000",
        "00067765616c746802036f70740000000201026b77000000056669656c640105",
        "716e616d6500000013736f6369616c2d636c6173732f7765616c746802047768",
        "656e0000000102013c00000002010373796d000000067765616c746801036375",
        "72000000100000000000000000000000003ba26b200207656666656374730000",
        "0001020b7570646174652d6e6f646500000003010373796d0000000473656c66",
        "0105716e616d6500000016736f6369616c2d636c6173732f616769746174696f",
        "6e0203616464000000010104696e746e00000011000000000000000000000000",
        "0000000502"
    );

    fn demo_rule() -> crate::reader::SExpr {
        read(DEMO_RULE).expect("worked example must parse").0
    }

    fn hex(bytes: &[u8]) -> String {
        use std::fmt::Write as _;
        bytes.iter().fold(String::new(), |mut acc, b| {
            let _ = write!(acc, "{b:02x}");
            acc
        })
    }

    #[test]
    fn the_spec_worked_example_reproduces_byte_for_byte() {
        let bytes = canonical_bytes(&demo_rule()).unwrap();
        assert_eq!(bytes.len(), 421, "§5.6 pins exactly 421 canonical bytes");
        assert_eq!(hex(&bytes), PINNED_HEX);
    }

    #[test]
    fn the_spec_worked_example_digests_reproduce() {
        use sha2::{Digest, Sha256};
        let bytes = canonical_bytes(&demo_rule()).unwrap();
        let single = Sha256::digest(&bytes);
        assert_eq!(
            hex(&single),
            "8a62d0b5724de24ec36ea0dfb3f4d120a63d90a56bad2a4605e645368f304da3"
        );
        let rules_hash = rules_hash_of(&[demo_rule()]).unwrap();
        assert_eq!(
            hex(&rules_hash),
            "4e6fbf64c771bd8e2f7874b4c906d0330458ba965911d00a9a731ea8a724238f"
        );
    }

    #[test]
    fn formatting_and_comments_never_change_the_bytes() {
        let reformatted = "(rule demo/hunger :material-basis \
         \"subsistence deficit at the point of reproduction\" :fuel 64 \
         (bindings (binding wealth :field social-class/wealth)) \
         (when (< wealth 1000.5$)) ; inline comment\n \
         (effects (update-node self social-class/agitation (add 0.05i))))";
        let (expr, _) = read(reformatted).unwrap();
        assert_eq!(
            canonical_bytes(&expr).unwrap(),
            canonical_bytes(&demo_rule()).unwrap()
        );
    }

    #[test]
    fn option_order_is_a_formatting_concern() {
        // §5.6's own note: :fuel sorts before :material-basis regardless of
        // source order ("fuel" < "material-basis" in ASCII).
        let swapped = DEMO_RULE.replacen(
            ":material-basis \"subsistence deficit at the point of reproduction\"\n     :fuel 64",
            ":fuel 64\n     :material-basis \"subsistence deficit at the point of reproduction\"",
            1,
        );
        assert_ne!(
            swapped, DEMO_RULE,
            "the swap must actually rewrite the source"
        );
        let (expr, _) = read(&swapped).unwrap();
        assert_eq!(
            canonical_bytes(&expr).unwrap(),
            canonical_bytes(&demo_rule()).unwrap()
        );
    }

    #[test]
    fn literal_canonicalization_reaches_the_bytes() {
        // §5.4: 0.50c ≡ 0.5c and 1000.5$ ≡ 1000.500$ — identical bytes.
        let a = read("(x 0.50c 1000.5$)").unwrap().0;
        let b = read("(x 0.5c 1000.500$)").unwrap().0;
        assert_eq!(canonical_bytes(&a).unwrap(), canonical_bytes(&b).unwrap());
    }

    #[test]
    fn a_flag_keyword_encodes_as_a_bool_true_option() {
        // (binding x :optional) ≡ the §5.2 draft ruling's explicit shape.
        let flag = read("(binding x :optional)").unwrap().0;
        let bytes = canonical_bytes(&flag).unwrap();
        let explicit = read("(binding x :optional #t)").unwrap().0;
        assert_eq!(bytes, canonical_bytes(&explicit).unwrap());
    }

    #[test]
    fn the_empty_content_set_has_the_pinned_rules_hash() {
        // SHA-256(0x03 ‖ u32 0) — the same value babylon-kernel's
        // ContentDigest test pins independently (cross-crate agreement on
        // the mandatory-rules_hash contract).
        assert_eq!(
            hex(&rules_hash_of(&[]).unwrap()),
            "a665e6b115dd56fd3e0c89be631e6eda8e9666b822e0bd7026bf0822c4bbc68f"
        );
    }

    #[test]
    fn rules_hash_sorts_by_rule_id_not_input_order() {
        let a = read("(rule aa/first :fuel 1 (when #t))").unwrap().0;
        let b = read("(rule zz/last :fuel 1 (when #t))").unwrap().0;
        assert_eq!(
            rules_hash_of(&[a.clone(), b.clone()]).unwrap(),
            rules_hash_of(&[b, a]).unwrap()
        );
    }

    #[test]
    fn unencodable_nodes_fail_loudly_never_stringify() {
        // An operator outside head position (§5.4's no-fallback law).
        let stray_op = read("(x <)").unwrap().0;
        assert!(canonical_bytes(&stray_op).is_err());
        // A form headed by a non-symbol.
        let headless = read("((a) b)").unwrap().0;
        assert!(canonical_bytes(&headless).is_err());
        // An empty form.
        let empty = read("()").unwrap().0;
        assert!(canonical_bytes(&empty).is_err());
        // rules_hash over a non-rule form.
        let not_a_rule = read("(deffield x :type int)").unwrap().0;
        assert!(rules_hash_of(&[not_a_rule]).is_err());
    }

    #[test]
    fn the_encoding_is_self_delimiting() {
        // §5.2: "unambiguously parseable back to the AST" — decode the
        // canonical bytes with an independent test-only decoder, re-encode
        // the decoded tree verbatim, and require byte identity.
        let bytes = canonical_bytes(&demo_rule()).unwrap();
        let (node, consumed) = decode(&bytes);
        assert_eq!(consumed, bytes.len(), "decoder must consume every byte");
        assert_eq!(reencode(&node), bytes);
    }

    #[test]
    fn read_all_of_a_two_rule_file_hashes_deterministically() {
        let forms =
            read_all(b"(rule b/two :fuel 1 (when #t))\n(rule a/one :fuel 1 (when #t))").unwrap();
        assert!(rules_hash_of(&forms).is_ok());
    }

    /// Minimal independent decoder for the self-delimitation test only.
    enum CasNode {
        Atom {
            kind: Vec<u8>,
            payload: Vec<u8>,
        },
        Form {
            tag: Vec<u8>,
            children: Vec<CasNode>,
        },
    }

    fn decode(bytes: &[u8]) -> (CasNode, usize) {
        let node_type = bytes[0];
        let name_len = usize::from(bytes[1]);
        let name = bytes[2..2 + name_len].to_vec();
        let mut pos = 2 + name_len;
        let count = u32::from_be_bytes(bytes[pos..pos + 4].try_into().unwrap()) as usize;
        pos += 4;
        match node_type {
            0x01 => {
                let payload = bytes[pos..pos + count].to_vec();
                (
                    CasNode::Atom {
                        kind: name,
                        payload,
                    },
                    pos + count,
                )
            }
            0x02 => {
                let mut children = Vec::with_capacity(count);
                for _ in 0..count {
                    let (child, used) = decode(&bytes[pos..]);
                    children.push(child);
                    pos += used;
                }
                (
                    CasNode::Form {
                        tag: name,
                        children,
                    },
                    pos,
                )
            }
            other => panic!("unknown node type byte {other:#04x}"),
        }
    }

    fn reencode(node: &CasNode) -> Vec<u8> {
        let mut out = Vec::new();
        match node {
            CasNode::Atom { kind, payload } => {
                out.push(0x01);
                out.push(u8::try_from(kind.len()).unwrap());
                out.extend_from_slice(kind);
                out.extend_from_slice(&u32::try_from(payload.len()).unwrap().to_be_bytes());
                out.extend_from_slice(payload);
            }
            CasNode::Form { tag, children } => {
                out.push(0x02);
                out.push(u8::try_from(tag.len()).unwrap());
                out.extend_from_slice(tag);
                out.extend_from_slice(&u32::try_from(children.len()).unwrap().to_be_bytes());
                for child in children {
                    out.extend_from_slice(&reencode(child));
                }
            }
        }
        out
    }
}
