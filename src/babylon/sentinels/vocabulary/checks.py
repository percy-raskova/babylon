"""Vocabulary-sentinel checks: the node-type vocabulary must stay closed.

Six gating rules, all read statically from source (no engine import, no
Django, no DB — cheap enough for the always-on fast gate):

**(a) No invented strings.** Every node-type literal stamped or queried
anywhere in ``src/``, ``web/`` or ``tests/`` must be a
:class:`~babylon.models.enums.topology.NodeType` member. This is the rule that
kills a fixture-invented type — the actual 2026-07-18 bug.

**(b) Production closure.** Every node type production *queries* must be a type
production *stamps*. A query for a type nothing produces is dead by
construction: it iterates the empty set forever. Test stamps deliberately do
not satisfy this rule (see
:data:`~babylon.sentinels.vocabulary.registry.PRODUCTION_ROOTS`).

**(c) Shape closure.** Every attribute a real ``add_node(id, TYPE, **kwargs)``
call stamps onto a KNOWN, production-stamped node type must be either a field
the corresponding Pydantic model actually declares, a documented graph-only
attribute a real production writer stamps (see
:data:`~babylon.sentinels.vocabulary.registry.EXTRA_STAMPABLE_ATTRIBUTES`), or
an explicit, reasoned exemption (see
:data:`~babylon.sentinels.vocabulary.registry.ATTRIBUTE_EXEMPTIONS`). This is
the rule that kills a fixture-fabricated SHAPE — task #45's audit
(2026-07-18) found ``territory_ids`` stamped on ``social_class`` nodes
(``SocialClass`` has no such field) plus five more live instances
(``agitation``/``factional_composition`` reading a flat key nested one level
deeper in production; ``class_consciousness``/``ooda_profile``/
``counter_intel_score`` never seeded at all). Deliberately scoped to REAL
``add_node`` calls whose node type resolves to a single literal (see
:func:`~babylon.sentinels._ast.add_node_attribute_stamps`) — ``update_node``
calls and duck-typed/attribute-agnostic utility tests are out of scope by
design, not by oversight (full reasoning: the audit report + the exemption
registry's own comments).

**(d) Edge-shape closure** (ADR087). Every fixture-stamped ``(edge_type,
SOURCE node type)`` combination must match a combination production stamps
the same literal way, or a cited
:data:`~babylon.sentinels.vocabulary.registry.EDGE_SOURCE_ALLOWLIST` entry —
see that data's own docstring for its deliberately narrower static scope.

**(e) Phantom-attribute closure** (task #40). No
:data:`~babylon.sentinels.vocabulary.registry.PHANTOM_ATTRIBUTE_READS` name
may be READ off a raw graph-node payload, or STAMPED via a real
``add_node(...)`` call, anywhere production or a test fixture does so — the
READ-side sibling of rule (c)'s STAMP-side check. The founding instance:
``ooda/initiative.py::compute_community_embeddedness`` read
``node_data.get("community_type")``, an attribute no production code ever
writes (community is never a main-graph node, INV-010), and was therefore
structurally always ``0.0``.

**(f) Wrong-rung Territory keying** (#39 T8). No ``Territory(...)`` call may
pass a bare FIPS-shaped string literal to ``id=``, or an H3-cell-derived
expression to ``county_fips=`` — the res-3 inversion class, both directions.
USScenario's historical bug minted the county FIPS straight into ``id``
(identity must live ONLY in ``county_fips``); the mirror-image mistake would
cross Wayne's hex path into the county grain. See
:func:`~babylon.sentinels._ast.territory_keying_uses` for the two recognised
forms and their documented static-heuristic narrowing.

Failure messages are written for an agent with no other context: each names the
offending ``file:line``, the offending string, the allowed set, the nearest
legal member, and one sentence on *why* the rule exists.
"""

from __future__ import annotations

import argparse
import difflib
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Final

from babylon.models.enums.topology import NodeType
from babylon.sentinels._ast import (
    add_node_attribute_stamps,
    edge_source_type_uses,
    graph_node_attribute_reads,
    node_type_uses,
    territory_keying_uses,
)
from babylon.sentinels.base import LabelledCheck, SentinelCheckError, run_sensor
from babylon.sentinels.exemptions import is_exempt
from babylon.sentinels.vocabulary.registry import (
    ATTRIBUTE_EXEMPTIONS,
    EDGE_SOURCE_ALLOWLIST,
    EXTRA_STAMPABLE_ATTRIBUTES,
    LITERAL_EXEMPTIONS,
    MODEL_FIELDS_BY_NODE_TYPE,
    PHANTOM_ATTRIBUTE_EXEMPTIONS,
    PHANTOM_ATTRIBUTE_READS,
    PRODUCTION_ROOTS,
    SCAN_ROOTS,
    TERRITORY_KEYING_EXEMPTIONS,
    TICK_PREFIXED_NODE_TYPES,
    UNSTAMPED_QUERY_ALLOWLIST,
)

__all__ = [
    "fabricated_edge_sources",
    "fabricated_node_attributes",
    "invented_node_types",
    "main",
    "phantom_attribute_uses",
    "unstamped_queried_node_types",
    "wrong_rung_territory_keying",
]

#: Attribute keys every node carries that are never a model "field" in the
#: shape-closure sense -- ``id`` selects/echoes the node's own identifier
#: (redundant with the positional arg, a common authoring idiom), not a
#: declared attribute of the entity it represents.
_ALWAYS_OK_ATTRIBUTES: Final[frozenset[str]] = frozenset({"id"})

_REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[4]

#: Every legal node-type value, read live from the enum (never duplicated).
_ALLOWED: Final[frozenset[str]] = frozenset(member.value for member in NodeType)

_WHY_INVENTED: Final[str] = (
    "WHY THIS FAILS: a node type that exists only where you wrote it is a closed "
    "loop with no external referent. The query that reads it matches ZERO nodes "
    "forever, so the test goes green while the feature it covers is dead. This "
    "is not hypothetical: 'balkanization_faction' vs the canonical 'faction' "
    "silently disabled RED_SETTLER_TRAP_DETECTED, secession enumeration and "
    "FASCIST_RECRUITMENT, and every test over them passed."
)

_WHY_UNSTAMPED: Final[str] = (
    "WHY THIS FAILS: production queries this type but no production code ever "
    "stamps it, so the query iterates the empty set on every tick. Either the "
    "producer is missing (wire it) or the query is dead (delete it). A fixture "
    "that stamps the type does NOT make it real -- that is precisely how this "
    "class of bug stays invisible."
)

_WHY_FABRICATED: Final[str] = (
    "WHY THIS FAILS: an attribute the entity's own Pydantic model does not "
    "declare, and no production writer stamps either, exists ONLY in the "
    "fixture that wrote it. A production reader keying off this exact name "
    "matches ZERO real nodes forever, so the test goes green while the "
    "feature it covers is dead. This is not hypothetical: a fixture stamping "
    "'territory_ids' on a social_class node (SocialClass has no such field) "
    "gave six tests a green bar over four live bugs (educate targets, verb "
    "eligibility, aid population targets, base_population, and the "
    "per-territory economy panel)."
)

_WHY_FABRICATED_EDGE: Final[str] = (
    "WHY THIS FAILS: a fixture that ALSO hand-stamps the source node's own "
    "type in the SAME file, then wires an edge combination no production "
    "code creates the same literal way, is a closed loop with no external "
    "referent -- the exact failure class ADR085 diagnosed: a fabricated "
    "'vanguard' organization node feeding a fabricated org-sourced SOLIDARITY "
    "edge, the ONLY reachable path for a whole amplification branch that "
    "never had a real write side. A production reader gated on this "
    "(edge_type, source_type) combination reacts to ZERO real edges forever."
)

_WHY_PHANTOM: Final[str] = (
    "WHY THIS FAILS: an attribute no production code ever stamps onto a graph "
    "node is invisible forever to any reader keyed on it -- the SAME 'closed "
    "loop with no external referent' shape as an invented node type or a "
    "fabricated field, one level down: the READ side, not just the STAMP "
    "side. This is not hypothetical: ooda/initiative.py::"
    "compute_community_embeddedness read 'community_type' (community is "
    "never a main-graph node, INV-010) and was structurally always 0.0 in "
    "every real game (task #40)."
)

_WHY_WRONG_RUNG: Final[str] = (
    "WHY THIS FAILS: Territory.id and Territory.county_fips are two DIFFERENT "
    "spatial rungs (Amendment U) -- a graph-local opaque label vs the real "
    "county identity resolve_county_identity reads. USScenario's historical "
    "res-3 bug minted the county FIPS straight into id (a bare FIPS string "
    "matching Territory's own id pattern only by coincidence, never "
    "resolvable as a real county by the economy); the mirror-image mistake "
    "would cross Wayne's hex path (h3_index-keyed, no county_fips) into the "
    "county grain, so a per-county reader would silently key off an H3 cell "
    "that resolves to no real county at all."
)


def _python_files(roots: tuple[str, ...]) -> Iterator[Path]:
    """Yield every ``.py`` file under ``roots``, sorted (deterministic order)."""
    for root in roots:
        base = _REPO_ROOT / root
        if not base.is_dir():
            raise SentinelCheckError(f"scan root missing: {base} (cannot verify the vocabulary)")
        yield from sorted(base.rglob("*.py"))


def _suggest(offender: str) -> str:
    """Nearest legal member for a rejected literal, as a ready-to-paste hint.

    Containment beats edit distance: the real-world offenders are a canonical
    name wearing a prefix or a suffix (``balkanization_faction`` for
    ``faction``) or a casing variant (``SocialClass`` for ``social_class``).
    Plain :mod:`difflib` scores ``balkanization_faction`` closer to
    ``organization`` than to ``faction``, which sends the reader the wrong way,
    so containment and a normalised-casing match are tried first.
    """
    normalised = offender.replace("_", "").lower()
    contained = sorted(
        (candidate for candidate in _ALLOWED if candidate in offender.lower()),
        key=len,
        reverse=True,
    )
    cased = [c for c in sorted(_ALLOWED) if c.replace("_", "") == normalised]
    fallback = difflib.get_close_matches(offender, sorted(_ALLOWED), n=1, cutoff=0.4)
    best = (cased or contained or fallback)[:1]
    if not best:
        return "no close match -- if this type is real, declare it in NodeType."
    member = NodeType(best[0])
    return f'did you mean NodeType.{member.name} ("{member.value}")?'


def invented_node_types() -> list[str]:
    """Rule (a): every node-type literal must be a :class:`NodeType` member.

    :returns: One violation string per offending literal, sorted by location.
    :raises SentinelCheckError: If a scan root is missing or a file is
        unparseable (exit 2 — infrastructure failure, never a silent pass).
    """
    violations: list[str] = []
    allowed = ", ".join(sorted(_ALLOWED))
    for path in _python_files(SCAN_ROOTS):
        rel = path.relative_to(_REPO_ROOT)
        for lineno, literal, role in node_type_uses(path):
            if literal in _ALLOWED or is_exempt(
                ("node_type_literal", rel.as_posix(), literal), LITERAL_EXEMPTIONS
            ):
                continue
            verb = "stamps" if role == "stamp" else "queries"
            violations.append(
                f'{rel}:{lineno} {verb} node type "{literal}", which is not a NodeType member.\n'
                f"    {_suggest(literal)}\n"
                f"    allowed: {allowed}\n"
                f"    fix: use NodeType.<MEMBER> here, or -- if this type is genuinely new --\n"
                f"         declare it in src/babylon/models/enums/topology.py::NodeType first.\n"
                f"    {_WHY_INVENTED}"
            )
    return violations


def unstamped_queried_node_types() -> list[str]:
    """Rule (b): every production-queried node type must be production-stamped.

    :returns: One violation string per unstamped queried type, sorted by type.
    :raises SentinelCheckError: If a scan root is missing or a file is
        unparseable (exit 2 — infrastructure failure, never a silent pass).
    """
    stamped: set[str] = set()
    queried: dict[str, list[str]] = {}
    for path in _python_files(PRODUCTION_ROOTS):
        rel = path.relative_to(_REPO_ROOT)
        for lineno, literal, role in node_type_uses(path):
            if role == "stamp":
                stamped.add(literal)
            else:
                queried.setdefault(literal, []).append(f"{rel}:{lineno}")

    violations: list[str] = []
    for literal in sorted(queried):
        if literal in stamped or literal in UNSTAMPED_QUERY_ALLOWLIST:
            continue
        sites = ", ".join(sorted(queried[literal]))
        violations.append(
            f'node type "{literal}" is QUERIED by production but STAMPED by no '
            f"production code.\n"
            f"    queried at: {sites}\n"
            f"    stamped by production: {', '.join(sorted(stamped))}\n"
            f"    fix: stamp it where the node is created, or delete the dead query.\n"
            f"         Do NOT add it to UNSTAMPED_QUERY_ALLOWLIST without an owner decision.\n"
            f"    {_WHY_UNSTAMPED}"
        )
    return violations


def _suggest_attribute(node_type: str, offender: str) -> str:
    """Nearest legal field name for a rejected attribute, ready to paste.

    Mirrors :func:`_suggest`'s containment-then-fuzzy-match order (the real
    offenders so far are a canonical field wearing a different name --
    ``factional_composition`` for ``internal_balance`` -- rather than a
    typo), scoped to the one node type's declared fields.
    """
    allowed = MODEL_FIELDS_BY_NODE_TYPE.get(node_type, frozenset())
    fallback = difflib.get_close_matches(offender, sorted(allowed), n=1, cutoff=0.3)
    if not fallback:
        return (
            "no close match on the declared model -- if this is real graph-only "
            "shape a production writer stamps, add it to "
            "EXTRA_STAMPABLE_ATTRIBUTES; if a test needs an arbitrary "
            "attribute-agnostic name, add an ATTRIBUTE_EXEMPTIONS row."
        )
    return f'did you mean "{fallback[0]}"?'


def fabricated_node_attributes() -> list[str]:
    """Rule (c): every stamped node attribute must be real shape.

    :returns: One violation string per fabricated ``(file, node_type,
        attribute)``, sorted by location.
    :raises SentinelCheckError: If a scan root is missing or a file is
        unparseable (exit 2 — infrastructure failure, never a silent pass).
    """
    violations: list[str] = []
    for path in _python_files(SCAN_ROOTS):
        rel = path.relative_to(_REPO_ROOT)
        rel_posix = rel.as_posix()
        for lineno, node_type, attr in add_node_attribute_stamps(path):
            model_fields = MODEL_FIELDS_BY_NODE_TYPE.get(node_type)
            if model_fields is None:
                # Not one of the 8 production-stamped types (or an invented
                # string) -- rules (a)/(b) police the vocabulary itself;
                # shape-closure only applies where a real model exists.
                continue
            if attr in _ALWAYS_OK_ATTRIBUTES or attr in model_fields:
                continue
            if attr in EXTRA_STAMPABLE_ATTRIBUTES.get(node_type, frozenset()):
                continue
            if node_type in TICK_PREFIXED_NODE_TYPES and attr.startswith("tick_"):
                continue
            if is_exempt(("node_attribute", rel_posix, node_type, attr), ATTRIBUTE_EXEMPTIONS):
                continue
            violations.append(
                f'{rel}:{lineno} stamps attribute "{attr}" on a "{node_type}" node, '
                f"which its model does not declare and no production writer stamps.\n"
                f"    {_suggest_attribute(node_type, attr)}\n"
                f"    declared fields: {', '.join(sorted(model_fields))}\n"
                f"    fix: use a real declared field, or -- if this is genuine "
                f"graph-only shape a\n"
                f"         production system writes -- add it to "
                f"EXTRA_STAMPABLE_ATTRIBUTES with a citation.\n"
                f"    {_WHY_FABRICATED}"
            )
    return violations


def fabricated_edge_sources() -> list[str]:
    """Rule (d): every fixture-stamped (edge_type, source_type) combination
    a fixture stamps must match a combination production stamps the same
    literal way, or be a cited :data:`EDGE_SOURCE_ALLOWLIST` entry.

    See :data:`~babylon.sentinels.vocabulary.registry.EDGE_SOURCE_ALLOWLIST`
    for this rule's deliberately NARROWER static scope (most real edge
    producers in this codebase write with a runtime id, not a literal, and
    are invisible to it by design — the allowlist docstring is the full
    accounting).

    :returns: One violation string per offending ``(file, line, combination)``.
    :raises SentinelCheckError: If a scan root is missing or a file is
        unparseable (exit 2 — infrastructure failure, never a silent pass).
    """
    produced: set[tuple[str, str]] = set()
    for path in _python_files(PRODUCTION_ROOTS):
        produced.update(
            (edge_type, source_type)
            for _lineno, edge_type, source_type in edge_source_type_uses(path)
        )

    violations: list[str] = []
    for path in _python_files(SCAN_ROOTS):
        rel = path.relative_to(_REPO_ROOT)
        for lineno, edge_type, source_type in edge_source_type_uses(path):
            combo = (edge_type, source_type)
            if combo in produced or combo in EDGE_SOURCE_ALLOWLIST:
                continue
            violations.append(
                f'{rel}:{lineno} stamps a "{edge_type}" edge sourced from a '
                f'"{source_type}" node -- a combination no production code '
                f"creates the same literal way.\n"
                f"    produced combinations: {sorted(produced) or 'none'}\n"
                f"    fix: wire a real producer for this (edge_type, source_type) pair "
                f"(and if it writes with a runtime id, note that in a comment -- this "
                f"rule cannot see it either way), or -- if this is a deliberate "
                f"negative control or a documented scanner blind spot -- add an\n"
                f"         EDGE_SOURCE_ALLOWLIST entry with a citation.\n"
                f"    {_WHY_FABRICATED_EDGE}"
            )
    return violations


def phantom_attribute_uses() -> list[str]:
    """Rule (e) (task #40): no banned attribute is read off, or stamped
    onto, a graph node — the phantom-attribute-read class.

    The READ-side sibling of rule (c): a
    :data:`~babylon.sentinels.vocabulary.registry.PHANTOM_ATTRIBUTE_READS`
    name is banned wherever it is read off a raw node-payload dict
    (:func:`~babylon.sentinels._ast.graph_node_attribute_reads` — any node
    type, deliberately: the point is no production code writes this
    attribute onto ANY graph node) or stamped via a real ``add_node(...)``
    call (any node type too, mirroring
    :data:`~babylon.sentinels.vocabulary.registry.UNSTAMPED_QUERY_ALLOWLIST`'s
    governance — a test fixture stamping the phantom attribute is the
    fabrication half of the identical bug, not a different one).

    :returns: One violation string per offending ``(file, line, attribute)``.
    :raises SentinelCheckError: If a scan root is missing or a file is
        unparseable (exit 2 — infrastructure failure, never a silent pass).
    """
    violations: list[str] = []
    for path in _python_files(SCAN_ROOTS):
        rel = path.relative_to(_REPO_ROOT)
        rel_posix = rel.as_posix()

        for lineno, attr in graph_node_attribute_reads(path, PHANTOM_ATTRIBUTE_READS):
            if is_exempt(("phantom_attribute_read", rel_posix, attr), PHANTOM_ATTRIBUTE_EXEMPTIONS):
                continue
            violations.append(
                f'{rel}:{lineno} reads phantom attribute "{attr}" off a graph-node '
                f"payload — no production code ever writes it there.\n"
                f"    fix: read the real substrate the attribute is meant to "
                f"represent, or — if this is a hand-verified non-graph-node "
                f"namespace — add a PHANTOM_ATTRIBUTE_EXEMPTIONS entry with a "
                f"citation.\n"
                f"    {_WHY_PHANTOM}"
            )

        for lineno, node_type, attr in add_node_attribute_stamps(path):
            if attr not in PHANTOM_ATTRIBUTE_READS:
                continue
            if is_exempt(
                ("phantom_attribute_stamp", rel_posix, attr), PHANTOM_ATTRIBUTE_EXEMPTIONS
            ):
                continue
            violations.append(
                f'{rel}:{lineno} stamps phantom attribute "{attr}" onto a '
                f'"{node_type}" node — no production reader can ever see it live, '
                f"because no production code writes it either.\n"
                f"    fix: delete the fabricated attribute from the fixture, or — "
                f"if it is load-bearing to an out-of-scope consumer — add a "
                f"PHANTOM_ATTRIBUTE_EXEMPTIONS entry with a citation.\n"
                f"    {_WHY_PHANTOM}"
            )
    return violations


def wrong_rung_territory_keying() -> list[str]:
    """Rule (f) (#39 T8): no ``Territory(...)`` call keys the wrong rung.

    The res-3 inversion class, both directions — see
    :func:`~babylon.sentinels._ast.territory_keying_uses` for the two
    recognised forms and their documented static-heuristic narrowing.

    :returns: One violation string per offending call site, sorted by location.
    :raises SentinelCheckError: If a scan root is missing or a file is
        unparseable (exit 2 — infrastructure failure, never a silent pass).
    """
    violations: list[str] = []
    for path in _python_files(SCAN_ROOTS):
        rel = path.relative_to(_REPO_ROOT)
        rel_posix = rel.as_posix()
        for lineno, kind, detail in territory_keying_uses(path):
            if is_exempt(
                ("territory_keying", rel_posix, kind, detail), TERRITORY_KEYING_EXEMPTIONS
            ):
                continue
            if kind == "fips_literal_id":
                violations.append(
                    f'{rel}:{lineno} passes bare FIPS-shaped literal "{detail}" to '
                    f"Territory(id=...) -- the res-3 inversion bug's exact shape.\n"
                    f"    fix: id must be a T-prefixed opaque label (e.g. an f-string "
                    f"built from a counter, f'T{{i:04d}}') or an H3-cell variable; the "
                    f"real county identity belongs ONLY in county_fips=.\n"
                    f"    {_WHY_WRONG_RUNG}"
                )
            else:
                violations.append(
                    f'{rel}:{lineno} passes H3-cell-derived expression "{detail}" to '
                    f"Territory(county_fips=...) -- the mirror-image res-3 inversion.\n"
                    f"    fix: county_fips must be a real 5-digit county FIPS from "
                    f"reference data (dim_county/bridge_county_h3), never an H3 cell "
                    f"value -- Wayne's hex path and the county path must never cross.\n"
                    f"    {_WHY_WRONG_RUNG}"
                )
    return sorted(violations)


#: All six rules gate: an invented type, a producerless query, a fabricated
#: node shape, a fabricated edge-source combination, a phantom-attribute
#: read/stamp, and a wrong-rung Territory keying are each a live defect, not
#: an observation.
_GATING_CHECKS: Final[tuple[LabelledCheck, ...]] = (
    ("invented-node-type", invented_node_types),
    ("unstamped-queried-node-type", unstamped_queried_node_types),
    ("fabricated-node-attribute", fabricated_node_attributes),
    ("fabricated-edge-source", fabricated_edge_sources),
    ("phantom-attribute-use", phantom_attribute_uses),
    ("wrong-rung-territory-keying", wrong_rung_territory_keying),
)


def _summary(advisory_count: int) -> str:
    """Clean one-line summary: the vocabulary size actually enforced."""
    _ = advisory_count  # This sentinel declares no advisory tier.
    return (
        f"VOCABULARY clean: {len(_ALLOWED)} declared node types; "
        f"every literal in {'/, '.join(SCAN_ROOTS)}/ is a NodeType member, "
        f"every production query has a production producer, every "
        f"stamped attribute on a production-stamped node type is real shape, "
        f"every fixture-stamped (edge_type, source_type) combination has "
        f"a production producer or a cited allowlist entry, no "
        f"phantom attribute is read off or stamped onto any graph node, and "
        f"no Territory(...) call keys the wrong spatial rung."
    )


def main(argv: list[str] | None = None) -> int:
    """Run the node-type vocabulary check and return the exit code.

    :param argv: CLI args (``--check`` is accepted as the CI-mode alias; the
        behavior is always to gate).
    :returns: 0 clean, 1 violations found, 2 infrastructure failure.
    """
    parser = argparse.ArgumentParser(
        description="Graph node-type vocabulary — static closure (III.11 / VIII.12 gate)."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="CI-mode alias; the tool always gates (exit 1 on violations).",
    )
    parser.parse_args(argv)
    return run_sensor("VOCABULARY", _GATING_CHECKS, (), _summary)


if __name__ == "__main__":
    sys.exit(main())
