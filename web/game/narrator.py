"""Spec 094: The Wire — NarratorProvider interface + DeterministicNarrator.

Constitution III (AI observes, never controls):
    This module imports ZERO ``babylon.*`` modules. It is a pure
    ``dict -> dict`` function — no database access, no graph access, no
    WorldState access. The narrator consumes GameEvent dicts (already
    persisted by spec-092's ``resolve_tick``) and produces WireFeed dicts
    for presentation only.

R-NARR ruling:
    The DeterministicNarrator uses template-based narration. Same events
    produce byte-identical output. No LLM calls. The NarratorProvider
    interface is designed for future LLM provider drop-in (M8/Wave-6).

The WireFeed shape is documented in ``specs/094-the-wire/contracts/wire.yaml``
and derived from ``design/mockups/wire/wire-data.jsx``.
"""

from __future__ import annotations

import logging
from typing import Any, Protocol, runtime_checkable

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# Manufacturing Consent — five filters (Herman & Chomsky, 1988)
# --------------------------------------------------------------------------- #

_FILTER_IDS: tuple[str, ...] = (
    "ownership",
    "advertising",
    "sourcing",
    "flak",
    "ideology",
)

_FILTER_LABELS: dict[str, str] = {
    "ownership": "Ownership",
    "advertising": "Advertising",
    "sourcing": "Sourcing",
    "flak": "Flak",
    "ideology": "Anti-radical ideology",
}

_FILTER_COLORS: dict[str, str] = {
    "ownership": "var(--rent)",
    "advertising": "var(--heat)",
    "sourcing": "var(--cadre)",
    "flak": "var(--thermal)",
    "ideology": "var(--laser)",
}

_FILTER_DESCS: dict[str, str] = {
    "ownership": "Continental is owned by a holding group with auto/defense exposure.",
    "advertising": "Advertiser pressure shapes coverage of implicated industries.",
    "sourcing": "Named sources are state or state-adjacent.",
    "flak": "Prior favorable coverage was retracted under pressure.",
    "ideology": "The frame presupposes the legitimacy of the existing order.",
}


def _empty_filters() -> list[dict[str, Any]]:
    return [
        {
            "id": fid,
            "label": _FILTER_LABELS[fid],
            "desc": _FILTER_DESCS[fid],
            "hits": 0,
            "color": _FILTER_COLORS[fid],
        }
        for fid in _FILTER_IDS
    ]


# --------------------------------------------------------------------------- #
# Severity classification (matches spec-092 GameEvent.severity)
# --------------------------------------------------------------------------- #

_SEVERITY_MAP: dict[str, str] = {
    "critical": "critical",
    "warning": "warning",
    "informational": "info",
}

# Map event types to their contribution to each Manufacturing Consent filter.
# A template can declare which filters it hits and how many times.
# This is a static rule table — not NLP (see spec Known Gaps).
_EVENT_FILTER_HITS: dict[str, dict[str, int]] = {
    "uprising": {"ownership": 1, "sourcing": 2, "ideology": 2},
    "eviction_pipeline": {"ownership": 1, "advertising": 1, "ideology": 1},
    "excessive_force": {"sourcing": 2, "flak": 1, "ideology": 2},
    "solidarity_formed": {"flak": 1, "ideology": 1},
    "solidarity_broken": {"flak": 1, "ideology": 1},
    "consciousness_shift": {"ideology": 1},
    "heat_change": {"sourcing": 1},
    "value_transfer": {"ownership": 1},
    "extraction": {"ownership": 1, "advertising": 1},
    "rupture": {"ownership": 1, "sourcing": 2, "ideology": 2},
    "revolutionary_victory": {"ownership": 2, "ideology": 2},
    "ecological_collapse": {"ownership": 1, "ideology": 1},
    "fascist_consolidation": {"ownership": 1, "ideology": 2},
    "bifurcation": {"ideology": 1},
}


# --------------------------------------------------------------------------- #
# Event-type templates — each produces index entry + triptych story
# --------------------------------------------------------------------------- #


def _location_from_event(event: dict[str, Any]) -> str:
    """Extract a human-readable location from event data."""
    data = event.get("data", {})
    for key in ("territory_id", "location", "target_id"):
        val = data.get(key)
        if val and isinstance(val, str):
            return str(val.replace("t_", "").replace("_", " ").title())
    return "Wayne County"


def _slug_from_event(event: dict[str, Any], slug_template: str) -> str:
    """Fill in the slug template with event data."""
    location = _location_from_event(event).upper()
    return slug_template.format(location=location)


# --------------------------------------------------------------------------- #
# Class-scoped subject resolution (W1.7: MASS_AWAKENING, FASCIST_DRIFT)
# --------------------------------------------------------------------------- #

# Canonical social-class entity ids -> display names. Duplicated here (never
# imported) from babylon.models.entity_registry.ROLE_TO_ENTITY_ID: the
# narrator has zero babylon.* imports (Constitution III — see
# TestArticleIIIStructural in tests/unit/web/test_narrator.py).
_CLASS_ID_NAMES: dict[str, str] = {
    "C001": "the Periphery Proletariat",
    "C002": "the Comprador Bourgeoisie",
    "C003": "the Core Bourgeoisie",
    "C004": "the Labor Aristocracy",
    "C005": "the Carceral Enforcers",
    "C006": "the Internal Proletariat",
}


def _subject_from_class_id(class_id: str, names: dict[str, str] | None = None) -> str:
    """Resolve a social-class node id to a display subject — never a place.

    ``names`` (the bridge's real per-scenario entity names, passed via
    ``meta["class_names"]`` and stamped onto each event as ``_class_names``)
    wins outright — scenarios reuse canonical ids under different names
    (wayne_county's C002 is "Suburban Petty Bourgeoisie", not the registry's
    Comprador), and a confidently wrong canonical name is a fabrication.
    Without a real name, known canonical ids (C001-C006, the
    imperial-circuit scenario's six entities) get their registry class name.
    Unrecognized ids (custom-scenario class nodes) are humanized from the id
    string itself rather than guessing a place or falling back to a
    fabricated default.
    """
    if names and class_id in names:
        return names[class_id]
    if class_id in _CLASS_ID_NAMES:
        return _CLASS_ID_NAMES[class_id]
    return class_id.replace("_", " ").title()


#: Event types whose story is about a social class, not a territory — the
#: value names the event's ``data`` key holding the affected class node id.
#: MASS_AWAKENING/FASCIST_DRIFT have no place to report; resolving through
#: here keeps their narration honest instead of falling back to the
#: hardcoded "Wayne County" default (see _location_from_event).
_CLASS_SCOPED_SUBJECT_FIELD: dict[str, str] = {
    "mass_awakening": "target_id",
    "fascist_drift": "node_id",
}


def _subject_from_org_id(org_id: str, names: dict[str, str] | None = None) -> str:
    """Resolve an organization node id to a display subject — never a place.

    Mirrors :func:`_subject_from_class_id` for organizations (AW3-R1,
    RED_BROWN_COUP). ``names`` (the bridge's real per-scenario org names,
    passed via ``meta["org_names"]`` and stamped onto each event as
    ``_org_names``) wins outright. Unlike social classes (six fixed
    canonical roles reused across scenarios), organizations have no small
    fixed canonical set at all — every scenario creates its own — so there
    is no hardcoded fallback map here, only an honest humanization of the
    raw id when no real name is available.
    """
    if names and org_id in names:
        return names[org_id]
    return org_id.replace("_", " ").title()


#: Event types whose story is about an organization, not a territory or a
#: social class — the value names the event's ``data`` key holding the
#: affected org node id. RED_BROWN_COUP has no place to report; resolving
#: through here keeps its narration honest instead of falling back to the
#: hardcoded "Wayne County" default (see _location_from_event).
_ORG_SCOPED_SUBJECT_FIELD: dict[str, str] = {
    "red_brown_coup": "org_id",
}


def _resolve_location(event: dict[str, Any]) -> str:
    """Resolve the value that fills a template's ``{location}`` placeholder.

    Place-scoped templates defer to :func:`_location_from_event`. Class-scoped
    templates (see :data:`_CLASS_SCOPED_SUBJECT_FIELD`) resolve to the
    affected social class's display name instead — never the fabricated
    "Wayne County" default, since these events carry no territory at all.
    Org-scoped templates (see :data:`_ORG_SCOPED_SUBJECT_FIELD`) do the same
    for the affected organization.
    """
    event_type = event.get("type", "")
    class_subject_field = _CLASS_SCOPED_SUBJECT_FIELD.get(event_type)
    if class_subject_field is not None:
        class_id = event.get("data", {}).get(class_subject_field)
        if isinstance(class_id, str) and class_id:
            return _subject_from_class_id(class_id, event.get("_class_names"))
        return "an unidentified class formation"
    org_subject_field = _ORG_SCOPED_SUBJECT_FIELD.get(event_type)
    if org_subject_field is not None:
        org_id = event.get("data", {}).get(org_subject_field)
        if isinstance(org_id, str) and org_id:
            return _subject_from_org_id(org_id, event.get("_org_names"))
        return "an unidentified organization"
    return _location_from_event(event)


#: Payload keys that hold a social-class node id rather than a plain display
#: value — resolved through :func:`_subject_from_class_id` like {location}.
_CLASS_ID_FIELDS: frozenset[str] = frozenset({"target_id", "node_id", "triggering_source"})


def _format_data_value(key: str, value: Any, names: dict[str, str] | None = None) -> str:
    """Format one payload value for display in template text.

    Class-id fields resolve through :func:`_subject_from_class_id` (never
    leaking a raw id like ``"C001"`` into rendered prose); numbers render to
    3 decimal places; strings upper-case to match the intel-cable style;
    ``None`` renders as ``"UNCLASSIFIED"`` (e.g. FASCIST_DRIFT's ``regime``
    is unset on tick 1).
    """
    if key in _CLASS_ID_FIELDS and isinstance(value, str):
        return _subject_from_class_id(value, names)
    if value is None:
        return "UNCLASSIFIED"
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, (int, float)):
        return f"{value:.3f}"
    if isinstance(value, str):
        return value.upper()
    return str(value)


def _event_data_substitutions(event: dict[str, Any]) -> dict[str, str]:
    """Build a ``{payload_key: formatted_value}`` map for template filling.

    Lets bespoke templates cite real payload numbers (e.g.
    ``{old_consciousness}``) in their intel fields/assessment instead of
    static flavor text. A no-op for templates whose text never references
    these tokens (every pre-W1.7 template only ever uses ``{location}``).
    """
    data = event.get("data", {})
    if not isinstance(data, dict):
        return {}
    names = event.get("_class_names")
    return {
        key: _format_data_value(key, value, names)
        for key, value in data.items()
        if isinstance(key, str)
    }


# Each template is a dict with:
#   slug_template: str (with {location} placeholder)
#   hed: {c, l, i} headline templates
#   euphemisms: {term_id: {c, l, filter, note}}
#   continental: {kicker, dek, byline, paragraphs, bibliography}
#   liberated: {pre, post, paragraphs}
#   intel: {subj, origin, routing, caveat, fields, assessment, refs, distribution}
#   coverage: ["c", "l", "i"]

_TEMPLATES: dict[str, dict[str, Any]] = {
    "uprising": {
        "slug": "UPRISING \u00b7 {location}",
        "hed": {
            "c": "Authorities Report Civil Disturbance in {location}",
            "l": "WORKERS ROSE UP IN {location} // THE STREET HOLDS",
            "i": "CIVIL DISTURBANCE // {location} // RESPONSE ACTIVE",
        },
        "euphemisms": {
            "disturbance": {
                "c": "civil disturbance",
                "l": "UPRISING",
                "filter": "ideology",
                "note": "Framing a political act as a public-order issue erases the grievance.",
            },
            "authorities": {
                "c": "authorities",
                "l": "COPS / PIGS",
                "filter": "sourcing",
                "note": "State spokesperson is sole source. Verb erased: who dispersed whom?",
            },
            "unrest": {
                "c": "unrest",
                "l": "REBELLION",
                "filter": "ideology",
                "note": "Worth-doing-ness of the response is assumed, not argued.",
            },
        },
        "continental": {
            "kicker": "NATIONAL \u00b7 LAW ENFORCEMENT",
            "dek": "Law enforcement officials say a {euph:disturbance} in {location} was brought under control. Several individuals were detained.",
            "byline": "By Continental Staff \u00b7 Updated 2h ago",
            "paragraphs": [
                [
                    "{location} \u2014 {euph:authorities} responded to reports of a {euph:disturbance} in the area early Tuesday. Several individuals were {euph:detained} for questioning.",
                    {"sup": 1},
                ],
                [
                    "The {euph:authorities} confirmed the action was \u201cmeasured and proportionate\u201d to the underlying threat assessment.",
                    {"sup": 2},
                ],
            ],
            "bibliography": [
                {
                    "n": 1,
                    "src": "DHS Office of Public Affairs",
                    "kind": "press release",
                    "id": "DHS-OPA-001",
                    "chunk": "chunk_dhs_pr_001",
                    "sim": 0.91,
                },
                {
                    "n": 2,
                    "src": "Senior official",
                    "kind": "background",
                    "id": "BG-001",
                    "chunk": "chunk_bg_001",
                    "sim": 0.74,
                },
            ],
        },
        "liberated": {
            "pre": "[ BEGIN TRANSMISSION \u00b7 CIPHER: NONE \u00b7 BROADCAST IN THE CLEAR ]",
            "post": "[ END TRANSMISSION \u00b7 TUNE NEXT HOUR \u00b7 WE HOLD THE LINE ]",
            "paragraphs": [
                {
                    "body": [
                        "THE STREET HELD IN {location}. WORKERS DROPPED THEIR TOOLS AND THE {euph:authorities} SENT THE SHOCK TEAMS.",
                    ],
                    "margin": {
                        "ref": "WITNESS-001",
                        "chunk": "chunk_wit_001",
                        "note": "front-line timestamp confirmed",
                    },
                },
                {
                    "body": [
                        "THE STATE CALLS THIS A {euph:disturbance}. WE CALL IT WHAT IT IS: THE PEOPLE RISING.",
                    ],
                    "margin": {
                        "ref": "WCLF BULLETIN",
                        "chunk": "chunk_wclf_001",
                        "note": "broadcast 06:00 local",
                    },
                },
            ],
        },
        "intel": {
            "subj": "CIVIL DISTURBANCE \u00b7 {location} \u00b7 POST-ACTION",
            "origin": "FBI/HSI JOINT TASKFORCE \u2014 DETROIT FIELD OFFICE",
            "routing": ["\u25ae\u25ae\u25ae\u25ae\u25ae\u25ae/CT", "DHS/I&A", "DOJ/NSD"],
            "caveat": "HANDLE VIA COMINT CHANNELS ONLY",
            "fields": [
                ["EVENT", "DISTURBANCE / DETAIN"],
                ["LOCATION", "{location}"],
                ["DETAINEES", "8\u00d7 PROCESSED"],
                ["RESISTANCE", "OBSERVED"],
                ["CONFIDENCE", "HIGH \u00b7 0.82"],
            ],
            "assessment": [
                "Action timed to suppress labor coordination.",
                "Continental-press uptake via DHS/OPA release; framing nominal.",
            ],
            "refs": [
                {"tag": "CHUNK", "id": "chunk_sigint_001", "sim": 0.95, "src": "SIGINT capture"},
                {"tag": "CHUNK", "id": "chunk_dhs_001", "sim": 0.88, "src": "DHS press release"},
            ],
            "distribution": "\u25ae\u25ae\u25ae\u25ae\u25ae\u25ae / \u25ae\u25ae\u25ae\u25ae\u25ae\u25ae \u00b7 NOFORN \u00b7 30D RETAIN",
        },
        "coverage": ["c", "l", "i"],
    },
    "eviction_pipeline": {
        "slug": "EVICTION \u00b7 {location}",
        "hed": {
            "c": "Market Correction Brings {location} Rents to Regional Average",
            "l": "LANDLORD CLASS SQUEEZES HARDER IN {location}",
            "i": "RENT EXTRACTION +0.04 // {location}",
        },
        "euphemisms": {
            "market": {
                "c": "market correction",
                "l": "RENT HIKE",
                "filter": "ownership",
                "note": "A 18% hike is called a correction. The landlord grades their own paper.",
            },
            "tenants": {
                "c": "affected residents",
                "l": "TENANTS / FAMILIES",
                "filter": "sourcing",
                "note": "Subjecthood removed. The displaced are named only as data.",
            },
        },
        "continental": {
            "kicker": "LOCAL \u00b7 HOUSING",
            "dek": "A {euph:market} has brought {location} rents in line with regional averages, according to industry analysts.",
            "byline": "By Continental Staff \u00b7 Updated 4h ago",
            "paragraphs": [
                [
                    "{location} \u2014 A {euph:market} is bringing rents to the regional average, according to a new analysis. {euph:tenants} may see adjustments in the coming quarter.",
                    {"sup": 1},
                ],
            ],
            "bibliography": [
                {
                    "n": 1,
                    "src": "Real Estate Data Group",
                    "kind": "report",
                    "id": "RE-001",
                    "chunk": "chunk_re_001",
                    "sim": 0.85,
                },
            ],
        },
        "liberated": {
            "pre": "[ BEGIN TRANSMISSION \u00b7 CIPHER: NONE ]",
            "post": "[ END TRANSMISSION \u00b7 HOUSING IS A RIGHT ]",
            "paragraphs": [
                {
                    "body": [
                        "THE LANDLORDS HIT {location} WITH ANOTHER {euph:market}. 18% IN ONE QUARTER. THE {euph:tenants} ARE BEING DRIVEN INTO THE STREET.",
                    ],
                    "margin": {
                        "ref": "TENANT UNION",
                        "chunk": "chunk_tu_001",
                        "note": "rent roll timestamped",
                    },
                },
            ],
        },
        "intel": {
            "subj": "RENT EXTRACTION \u00b7 {location}",
            "origin": "FIELD STATION \u2014 WAYNE CO",
            "routing": ["DHS/I&A", "DOJ/NSD"],
            "caveat": "HANDLE VIA DOMESTIC CHANNELS",
            "fields": [
                ["EVENT", "RENT INCREASE"],
                ["LOCATION", "{location}"],
                ["DELTA", "+0.042"],
                ["CONFIDENCE", "MEDIUM \u00b7 0.71"],
            ],
            "assessment": [
                "Extraction intensifying in working-class neighborhoods.",
            ],
            "refs": [
                {"tag": "CHUNK", "id": "chunk_rent_001", "sim": 0.82, "src": "rent roll data"},
            ],
            "distribution": "\u25ae\u25ae\u25ae\u25ae\u25ae\u25ae / \u25ae\u25ae\u25ae\u25ae\u25ae\u25ae \u00b7 NOFORN",
        },
        "coverage": ["c", "l", "i"],
    },
    "excessive_force": {
        "slug": "REPRESSION \u00b7 {location}",
        "hed": {
            "c": "Law Enforcement Conducts Measured Response in {location}",
            "l": "PIGS ATTACKED THE PEOPLE IN {location}",
            "i": "USE OF FORCE // {location} // POST-ACTION",
        },
        "euphemisms": {
            "force": {
                "c": "measured response",
                "l": "BATTERING RAMS \u00b7 FLASHBANGS",
                "filter": "ideology",
                "note": "Worth-doing-ness assumed. The state grades its own paper.",
            },
            "detained": {
                "c": "detained for questioning",
                "l": "SNATCHED / ABDUCTED",
                "filter": "sourcing",
                "note": "Detain implies temporary. Many are held without charge.",
            },
        },
        "continental": {
            "kicker": "NATIONAL \u00b7 LAW ENFORCEMENT",
            "dek": "Officials confirmed a {euph:force} in {location}. Several individuals were {euph:detained}.",
            "byline": "By Continental Staff \u00b7 Updated 1h ago",
            "paragraphs": [
                [
                    "{location} \u2014 Authorities conducted a {euph:response} early Tuesday. The action was described as {euph:force}.",
                    {"sup": 1},
                ],
            ],
            "bibliography": [
                {
                    "n": 1,
                    "src": "DHS Office of Public Affairs",
                    "kind": "press release",
                    "id": "DHS-OPA-002",
                    "chunk": "chunk_dhs_002",
                    "sim": 0.89,
                },
            ],
        },
        "liberated": {
            "pre": "[ BEGIN TRANSMISSION ]",
            "post": "[ END TRANSMISSION ]",
            "paragraphs": [
                {
                    "body": [
                        "THE PIGS HIT {location} WITH {euph:force}. OUR COMRADES WERE {euph:detained}. WE HAVE THE PHOTOS.",
                    ],
                    "margin": {
                        "ref": "WITNESS-002",
                        "chunk": "chunk_wit_002",
                        "note": "porch camera timestamp",
                    },
                },
            ],
        },
        "intel": {
            "subj": "USE OF FORCE \u00b7 {location}",
            "origin": "FBI FIELD OFFICE",
            "routing": ["DOJ/NSD", "DHS/I&A"],
            "caveat": "HANDLE VIA COMINT CHANNELS ONLY",
            "fields": [
                ["EVENT", "FORCE / DETAIN"],
                ["LOCATION", "{location}"],
                ["DETAINEES", "14\u00d7 PROCESSED"],
                ["CONFIDENCE", "HIGH \u00b7 0.84"],
            ],
            "assessment": [
                "Timing assessed deliberate.",
                "Continental-press framing nominal.",
            ],
            "refs": [
                {
                    "tag": "CHUNK",
                    "id": "chunk_force_001",
                    "sim": 0.92,
                    "src": "after-action report",
                },
            ],
            "distribution": "\u25ae\u25ae\u25ae\u25ae\u25ae\u25ae \u00b7 NOFORN \u00b7 30D RETAIN",
        },
        "coverage": ["c", "l", "i"],
    },
    "consciousness_shift": {
        "slug": "CONSCIOUSNESS \u00b7 {location}",
        "hed": {
            "c": "Civic Engagement Groups Draw Renewed Interest in {location}",
            "l": "STUDY GROUPS HITTING HARD IN {location} // THE MASS LINE HOLDS",
            "i": "CONSCIOUSNESS \u0394 POSITIVE // {location}",
        },
        "euphemisms": {
            "engagement": {
                "c": "civic engagement",
                "l": "CLASS CONSCIOUSNESS",
                "filter": "ideology",
                "note": "Political education reframed as hobbyist interest.",
            },
        },
        "continental": {
            "kicker": "LOCAL \u00b7 COMMUNITY",
            "dek": "Local book clubs and {euph:engagement} groups in {location} report growing interest.",
            "byline": "By Continental Staff \u00b7 Updated 6h ago",
            "paragraphs": [
                [
                    "{location} \u2014 {euph:engagement} groups are seeing renewed interest from younger readers, organizers say."
                ],
            ],
            "bibliography": [],
        },
        "liberated": {
            "pre": "[ BEGIN TRANSMISSION ]",
            "post": "[ END TRANSMISSION ]",
            "paragraphs": [
                {
                    "body": [
                        "THE {euph:engagement} IS REAL. THE MASS LINE HOLDS IN {location}. STUDY GROUPS HITTING 200+ A WEEK."
                    ],
                    "margin": {
                        "ref": "ORG BULLETIN",
                        "chunk": "chunk_org_001",
                        "note": "weekly count",
                    },
                },
            ],
        },
        "intel": {
            "subj": "CONSCIOUSNESS SHIFT \u00b7 {location}",
            "origin": "FIELD STATION",
            "routing": ["DHS/I&A"],
            "caveat": "DOMESTIC ONLY",
            "fields": [
                ["EVENT", "CONSCIOUSNESS DELTA"],
                ["LOCATION", "{location}"],
                ["DELTA", "+0.022"],
                ["CONFIDENCE", "MEDIUM \u00b7 0.68"],
            ],
            "assessment": ["Gradual shift consistent with organizing activity."],
            "refs": [],
            "distribution": "\u25ae\u25ae\u25ae\u25ae\u25ae\u25ae \u00b7 DOMESTIC",
        },
        "coverage": ["c", "l", "i"],
    },
    "solidarity_formed": {
        "slug": "SOLIDARITY \u00b7 {location}",
        "hed": {
            "c": "Community Groups Form New Alliance in {location}",
            "l": "COMRADES UNITE IN {location} // THE LINE HOLDS",
            "i": "COORDINATION DETECTED // {location}",
        },
        "euphemisms": {
            "alliance": {
                "c": "new alliance",
                "l": "SOLIDARITY",
                "filter": "flak",
                "note": "A political act reframed as a bureaucratic merger.",
            },
        },
        "continental": {
            "kicker": "LOCAL \u00b7 COMMUNITY",
            "dek": "Several community groups have formed a {euph:alliance} in {location}.",
            "byline": "By Continental Staff \u00b7 Updated 8h ago",
            "paragraphs": [
                ["{location} \u2014 A {euph:alliance} of local groups was announced this week."]
            ],
            "bibliography": [],
        },
        "liberated": {
            "pre": "[ BEGIN TRANSMISSION ]",
            "post": "[ END TRANSMISSION ]",
            "paragraphs": [
                {
                    "body": [
                        "THE {euph:alliance} IS FORGED IN {location}. THE COMRADES STAND TOGETHER."
                    ],
                    "margin": None,
                },
            ],
        },
        "intel": {
            "subj": "COORDINATION \u00b7 {location}",
            "origin": "FIELD STATION",
            "routing": ["DHS/I&A", "DOJ/NSD"],
            "caveat": "DOMESTIC",
            "fields": [
                ["EVENT", "ALLIANCE FORMED"],
                ["LOCATION", "{location}"],
                ["CONFIDENCE", "LOW \u00b7 0.55"],
            ],
            "assessment": ["New coordination between previously unaffiliated groups."],
            "refs": [],
            "distribution": "\u25ae\u25ae\u25ae\u25ae\u25ae\u25ae \u00b7 DOMESTIC",
        },
        "coverage": ["c", "l", "i"],
    },
    "heat_change": {
        "slug": "SURVEILLANCE \u00b7 {location}",
        "hed": {
            "c": "Security Attention Increases in {location}",
            "l": "HEAT ON THE DOOR IN {location}",
            "i": "SURVEILLANCE INTENSITY +0.07 // {location}",
        },
        "euphemisms": {
            "attention": {
                "c": "security attention",
                "l": "SURVEILLANCE / HEAT",
                "filter": "sourcing",
                "note": "Repression reframed as prudent attention.",
            },
        },
        "continental": {
            "kicker": "NATIONAL \u00b7 SECURITY",
            "dek": "Officials confirmed increased {euph:attention} in {location}.",
            "byline": "By Continental Staff",
            "paragraphs": [
                [
                    "{location} \u2014 Law enforcement confirmed heightened {euph:attention} in the area."
                ]
            ],
            "bibliography": [],
        },
        "liberated": {
            "pre": "[ BEGIN TRANSMISSION ]",
            "post": "[ END TRANSMISSION ]",
            "paragraphs": [
                {
                    "body": [
                        "THE {euph:attention} IS ON OUR DOOR IN {location}. THE HEAT IS UP. STAY SHARP."
                    ],
                    "margin": None,
                },
            ],
        },
        "intel": {
            "subj": "SURVEILLANCE \u00b7 {location}",
            "origin": "FIELD STATION",
            "routing": ["DHS/I&A"],
            "caveat": "DOMESTIC",
            "fields": [
                ["EVENT", "HEAT CHANGE"],
                ["LOCATION", "{location}"],
                ["DELTA", "+0.071"],
                ["CONFIDENCE", "HIGH \u00b7 0.79"],
            ],
            "assessment": ["Surveillance intensifying on organizing networks."],
            "refs": [],
            "distribution": "\u25ae\u25ae\u25ae\u25ae\u25ae\u25ae \u00b7 DOMESTIC",
        },
        "coverage": ["c", "l", "i"],
    },
    "rupture": {
        "slug": "RUPTURE \u00b7 {location}",
        "hed": {
            "c": "System Stress Reported in {location}",
            "l": "THE DAM BREAKS IN {location} // RUPTURE",
            "i": "RUPTURE EVENT // {location} // CRITICAL",
        },
        "euphemisms": {
            "stress": {
                "c": "system stress",
                "l": "RUPTURE",
                "filter": "ideology",
                "note": "An existential crisis reframed as manageable stress.",
            },
        },
        "continental": {
            "kicker": "NATIONAL \u00b7 BREAKING",
            "dek": "Officials report {euph:stress} in {location}. The situation is developing.",
            "byline": "By Continental Staff \u00b7 Breaking",
            "paragraphs": [
                [
                    "{location} \u2014 {euph:stress} has been reported. Officials say the situation is being monitored."
                ]
            ],
            "bibliography": [],
        },
        "liberated": {
            "pre": "[ BEGIN TRANSMISSION \u00b7 URGENT ]",
            "post": "[ END TRANSMISSION ]",
            "paragraphs": [
                {
                    "body": [
                        "THE {euph:stress} IS HERE. THE DAM BREAKS IN {location}. THIS IS THE MOMENT."
                    ],
                    "margin": None,
                },
            ],
        },
        "intel": {
            "subj": "RUPTURE \u00b7 {location} \u00b7 CRITICAL",
            "origin": "JOINT TASKFORCE",
            "routing": ["\u25ae\u25ae\u25ae\u25ae\u25ae\u25ae/CT", "DHS/I&A", "DOJ/NSD", "SITROOM"],
            "caveat": "HANDLE VIA COMINT CHANNELS ONLY",
            "fields": [
                ["EVENT", "RUPTURE"],
                ["LOCATION", "{location}"],
                ["SEVERITY", "CRITICAL"],
                ["CONFIDENCE", "HIGH \u00b7 0.91"],
            ],
            "assessment": ["Existential system stress detected. recommend maximum coverage."],
            "refs": [],
            "distribution": "\u25ae\u25ae\u25ae\u25ae\u25ae\u25ae \u00b7 NOFORN \u00b7 30D RETAIN",
        },
        "coverage": ["c", "l", "i"],
    },
    "revolutionary_victory": {
        "slug": "REVOLUTION \u00b7 {location}",
        "hed": {
            "c": "Regime Change Reported in {location}",
            "l": "WE WIN IN {location} // THE REVOLUTION HOLDS",
            "i": "REGIME CHANGE // {location} // CONFIRMED",
        },
        "euphemisms": {
            "change": {
                "c": "regime change",
                "l": "REVOLUTION",
                "filter": "ownership",
                "note": "A victory reframed as a transfer of management.",
            },
        },
        "continental": {
            "kicker": "NATIONAL \u00b7 BREAKING",
            "dek": "A {euph:change} has been reported in {location}.",
            "byline": "By Continental Staff \u00b7 Breaking",
            "paragraphs": [
                [
                    "{location} \u2014 Officials confirmed a {euph:change}. The situation is developing."
                ]
            ],
            "bibliography": [],
        },
        "liberated": {
            "pre": "[ BEGIN TRANSMISSION \u00b7 VICTORY ]",
            "post": "[ END TRANSMISSION \u00b7 WE WIN ]",
            "paragraphs": [
                {
                    "body": [
                        "THE {euph:change} IS REAL. WE WIN IN {location}. THE PEOPLE HOLD THE LINE."
                    ],
                    "margin": None,
                },
            ],
        },
        "intel": {
            "subj": "REGIME CHANGE \u00b7 {location}",
            "origin": "JOINT TASKFORCE",
            "routing": ["SITROOM", "DHS/I&A", "DOJ/NSD"],
            "caveat": "HANDLE VIA COMINT CHANNELS ONLY",
            "fields": [
                ["EVENT", "REGIME CHANGE"],
                ["LOCATION", "{location}"],
                ["CONFIDENCE", "CONFIRMED"],
            ],
            "assessment": ["Revolutionary victory confirmed."],
            "refs": [],
            "distribution": "\u25ae\u25ae\u25ae\u25ae\u25ae\u25ae \u00b7 NOFORN",
        },
        "coverage": ["c", "l", "i"],
    },
    "ecological_collapse": {
        "slug": "COLLAPSE \u00b7 {location}",
        "hed": {
            "c": "Environmental Crisis Deepens in {location}",
            "l": "THE EARTH BETRAYED IN {location} // ECOCIDE",
            "i": "ECOCATASTROPHE // {location} // CONFIRMED",
        },
        "euphemisms": {
            "crisis": {
                "c": "environmental crisis",
                "l": "ECOCIDE",
                "filter": "ideology",
                "note": "Systemic ecological destruction reframed as a natural disaster.",
            },
        },
        "continental": {
            "kicker": "NATIONAL \u00b7 ENVIRONMENT",
            "dek": "An {euph:crisis} has been reported in {location}.",
            "byline": "By Continental Staff",
            "paragraphs": [
                [
                    "{location} \u2014 An {euph:crisis} is deepening. Officials say the situation is being assessed."
                ]
            ],
            "bibliography": [],
        },
        "liberated": {
            "pre": "[ BEGIN TRANSMISSION ]",
            "post": "[ END TRANSMISSION ]",
            "paragraphs": [
                {
                    "body": [
                        "THE {euph:crisis} IS HERE IN {location}. THE EARTH BETRAYED BY CAPITAL."
                    ],
                    "margin": None,
                },
            ],
        },
        "intel": {
            "subj": "ECOCATASTROPHE \u00b7 {location}",
            "origin": "FIELD STATION",
            "routing": ["DHS/I&A", "EPA"],
            "caveat": "DOMESTIC",
            "fields": [
                ["EVENT", "ECOLOGICAL COLLAPSE"],
                ["LOCATION", "{location}"],
                ["CONFIDENCE", "HIGH"],
            ],
            "assessment": ["Biocapacity threshold breached."],
            "refs": [],
            "distribution": "\u25ae\u25ae\u25ae\u25ae\u25ae\u25ae \u00b7 DOMESTIC",
        },
        "coverage": ["c", "l", "i"],
    },
    "fascist_consolidation": {
        "slug": "FASCISM \u00b7 {location}",
        "hed": {
            "c": "Order Restored in {location}",
            "l": "THE FASH TAKE HOLD IN {location}",
            "i": "AUTHORITARIAN SHIFT // {location} // CONFIRMED",
        },
        "euphemisms": {
            "order": {
                "c": "order restored",
                "l": "FASCIST CONSOLIDATION",
                "filter": "ideology",
                "note": "Authoritarian consolidation reframed as the restoration of order.",
            },
        },
        "continental": {
            "kicker": "NATIONAL \u00b7 BREAKING",
            "dek": "Officials report {euph:order} in {location}.",
            "byline": "By Continental Staff \u00b7 Breaking",
            "paragraphs": [
                ["{location} \u2014 {euph:order} was confirmed. The situation is stable."]
            ],
            "bibliography": [],
        },
        "liberated": {
            "pre": "[ BEGIN TRANSMISSION \u00b7 DARK HOUR ]",
            "post": "[ END TRANSMISSION ]",
            "paragraphs": [
                {
                    "body": [
                        "THE {euph:order} IS HERE IN {location}. THE FASH TAKE HOLD. WE DO NOT YIELD."
                    ],
                    "margin": None,
                },
            ],
        },
        "intel": {
            "subj": "AUTHORITARIAN SHIFT \u00b7 {location}",
            "origin": "JOINT TASKFORCE",
            "routing": ["SITROOM", "DHS/I&A"],
            "caveat": "HANDLE VIA RESTRICTED CHANNELS",
            "fields": [
                ["EVENT", "FASCIST CONSOLIDATION"],
                ["LOCATION", "{location}"],
                ["CONFIDENCE", "CONFIRMED"],
            ],
            "assessment": ["Authoritarian consolidation confirmed."],
            "refs": [],
            "distribution": "\u25ae\u25ae\u25ae\u25ae\u25ae\u25ae \u00b7 NOFORN",
        },
        "coverage": ["c", "l", "i"],
    },
    "mass_awakening": {
        # Class-scoped (see _CLASS_SCOPED_SUBJECT_FIELD): {location} below
        # fills with the affected class's display name, not a place.
        "slug": "AWAKENING \u00b7 {location}",
        "hed": {
            "c": "Renewed Civic Interest Reported Among {location}",
            "l": "{location} CROSS THE LINE // MASS AWAKENING",
            "i": "CONSCIOUSNESS THRESHOLD CROSSED // {location}",
        },
        "euphemisms": {
            "interest": {
                "c": "renewed civic interest",
                "l": "MASS AWAKENING",
                "filter": "ideology",
                "note": "A qualitative leap in class consciousness reframed as a passing poll blip.",
            },
        },
        "continental": {
            "kicker": "NATIONAL \u00b7 SOCIAL TRENDS",
            "dek": "Analysts note {euph:interest} among {location}, attributing the shift to localized conditions rather than any organized cause.",
            "byline": "By Continental Staff \u00b7 Updated 5h ago",
            "paragraphs": [
                [
                    "{location} \u2014 Pollsters report {euph:interest} in recent weeks. Sociologists caution the uptick is likely transient.",
                ],
            ],
            "bibliography": [],
        },
        "liberated": {
            "pre": "[ BEGIN TRANSMISSION \u00b7 THE MASS LINE HOLDS ]",
            "post": "[ END TRANSMISSION \u00b7 THEY SEE IT NOW ]",
            "paragraphs": [
                {
                    "body": [
                        "{location} HAVE CROSSED THE THRESHOLD. THIS IS NOT {euph:interest} \u2014 IT IS CLASS CONSCIOUSNESS TAKING HOLD. THEY SEE IT NOW.",
                    ],
                    "margin": {
                        "ref": "ORG BULLETIN",
                        "chunk": "chunk_awakening_001",
                        "note": "consciousness delta confirmed",
                    },
                },
            ],
        },
        "intel": {
            "subj": "MASS AWAKENING \u00b7 {location}",
            "origin": "FIELD STATION",
            "routing": ["DHS/I&A"],
            "caveat": "DOMESTIC ONLY",
            "fields": [
                ["EVENT", "CONSCIOUSNESS THRESHOLD CROSSED"],
                ["SUBJECT", "{location}"],
                ["CONSCIOUSNESS (OLD)", "{old_consciousness}"],
                ["CONSCIOUSNESS (NEW)", "{new_consciousness}"],
                ["TRANSMITTED BY", "{triggering_source}"],
            ],
            "assessment": [
                "Consciousness rose from {old_consciousness} to {new_consciousness}, crossing the mass-awakening threshold.",
                "Transmission traced to {triggering_source} via a live SOLIDARITY edge.",
            ],
            "refs": [],
            "distribution": "\u25ae\u25ae\u25ae\u25ae\u25ae\u25ae \u00b7 DOMESTIC",
        },
        "coverage": ["c", "l", "i"],
    },
    "fascist_drift": {
        # Class-scoped (see _CLASS_SCOPED_SUBJECT_FIELD): {location} below
        # fills with the affected class's display name, not a place.
        "slug": "DRIFT \u00b7 {location}",
        "hed": {
            "c": "Order-Minded Sentiment Grows Among {location}",
            "l": "{location} DRIFT RIGHT // THE FASH CIRCLE",
            "i": "FASCIST ALIGNMENT RISING // {location}",
        },
        "euphemisms": {
            "sentiment": {
                "c": "order-minded sentiment",
                "l": "FASCIST DRIFT",
                "filter": "ideology",
                "note": "A reactionary realignment under entitlement pressure reframed as a preference for order.",
            },
        },
        "continental": {
            "kicker": "NATIONAL \u00b7 SOCIAL TRENDS",
            "dek": "Officials note {euph:sentiment} among {location}, calling it a natural response to eroding conditions.",
            "byline": "By Continental Staff \u00b7 Updated 2h ago",
            "paragraphs": [
                [
                    "{location} \u2014 Analysts report {euph:sentiment} strengthening. Officials describe the trend as order restored to a group under strain, not a political realignment.",
                ],
            ],
            "bibliography": [],
        },
        "liberated": {
            "pre": "[ BEGIN TRANSMISSION \u00b7 WARNING ]",
            "post": "[ END TRANSMISSION \u00b7 WATCH THIS ONE ]",
            "paragraphs": [
                {
                    "body": [
                        "{location} ARE DRIFTING FASCIST. THIS IS NOT {euph:sentiment} \u2014 ENTITLEMENT UNDER PRESSURE, SOLIDARITY UNCUT, AND THE FASH ARE CIRCLING. WATCH THIS ONE.",
                    ],
                    "margin": {
                        "ref": "FIELD REPORT",
                        "chunk": "chunk_drift_001",
                        "note": "alignment delta confirmed",
                    },
                },
            ],
        },
        "intel": {
            "subj": "FASCIST DRIFT \u00b7 {location}",
            "origin": "FIELD STATION",
            "routing": ["DHS/I&A", "DOJ/NSD"],
            "caveat": "HANDLE VIA DOMESTIC CHANNELS",
            "fields": [
                ["EVENT", "FASCIST ALIGNMENT DRIFT"],
                ["SUBJECT", "{location}"],
                ["FASCIST PULL", "{fascist_pull}"],
                ["FASCIST ALIGNMENT", "{fascist_alignment}"],
                ["ENTITLEMENT", "{entitlement}"],
                ["SOLIDARITY", "{solidarity}"],
                ["REGIME", "{regime}"],
            ],
            "assessment": [
                "Fascist pull of {fascist_pull} pushed alignment to {fascist_alignment} under entitlement {entitlement} and solidarity {solidarity}.",
                "Dialectical regime at time of drift: {regime}.",
            ],
            "refs": [],
            "distribution": "\u25ae\u25ae\u25ae\u25ae\u25ae\u25ae \u00b7 NOFORN",
        },
        "coverage": ["c", "l", "i"],
    },
    "red_brown_coup": {
        # Org-scoped (see _ORG_SCOPED_SUBJECT_FIELD): {location} below
        # fills with the affected organization's display name, not a place.
        "slug": "COUP \u00b7 {location}",
        "hed": {
            "c": "Leadership Change Reported at {location}",
            "l": "{location} FALLS TO THE FASH // RED-BROWN COUP",
            "i": "ORGANIZATIONAL CAPTURE // {location} // CONFIRMED",
        },
        "euphemisms": {
            "change": {
                "c": "leadership change",
                "l": "RED-BROWN COUP",
                "filter": "ideology",
                "note": "A fascist capture of a labor organization from within, reframed as routine leadership turnover.",
            },
        },
        "continental": {
            "kicker": "NATIONAL \u00b7 LABOR",
            "dek": "Officials note a {euph:change} at {location} amid economic uncertainty.",
            "byline": "By Continental Staff \u00b7 Breaking",
            "paragraphs": [
                [
                    "{location} \u2014 A {euph:change} was confirmed following a wave of internal defections. The organization's new direction remains unclear.",
                ],
            ],
            "bibliography": [],
        },
        "liberated": {
            "pre": "[ BEGIN TRANSMISSION \u00b7 MAYDAY ]",
            "post": "[ END TRANSMISSION \u00b7 THE ROT SPREAD FROM WITHIN ]",
            "paragraphs": [
                {
                    "body": [
                        "{location} IS LOST. THE FASH TOOK IT FROM INSIDE \u2014 NOT A RAID, A ROT. {euph:change}, THEY CALL IT. WE CALL IT WHAT IT IS: BETRAYAL.",
                    ],
                    "margin": {
                        "ref": "FIELD REPORT",
                        "chunk": "chunk_coup_001",
                        "note": "defection count confirmed",
                    },
                },
            ],
        },
        "intel": {
            "subj": "ORGANIZATIONAL CAPTURE \u00b7 {location}",
            "origin": "FIELD STATION",
            "routing": ["DHS/I&A", "DOJ/NSD"],
            "caveat": "HANDLE VIA DOMESTIC CHANNELS",
            "fields": [
                ["EVENT", "RED-BROWN COUP"],
                ["ORGANIZATION", "{location}"],
                ["DEFECTIONS", "{defections}"],
                ["MEMBERSHIP", "{member_count}"],
                ["CONFIDENCE", "CONFIRMED"],
            ],
            "assessment": [
                "{defections} of {member_count} Labor Aristocracy members defected in a single crisis tick, exceeding the majority threshold.",
                "Organizational control has passed to the fascist faction.",
            ],
            "refs": [],
            "distribution": "\u25ae\u25ae\u25ae\u25ae\u25ae\u25ae \u00b7 NOFORN",
        },
        "coverage": ["c", "l", "i"],
    },
}


def _generic_template(event: dict[str, Any]) -> dict[str, Any]:
    """Fallback template for unrecognized event types."""
    title = event.get("title", "Event")
    location = _location_from_event(event)
    body = event.get("body", "")
    return {
        "slug": f"{title.upper()} \u00b7 {location.upper()}",
        "hed": {
            "c": f"{title} Reported in {location}",
            "l": f"{title.upper()} IN {location.upper()}",
            "i": f"{title.upper()} // {location.upper()}",
        },
        "euphemisms": {},
        "continental": {
            "kicker": "NATIONAL",
            "dek": body or f"An event was reported in {location}.",
            "byline": "By Continental Staff",
            "paragraphs": [[f"{location} \u2014 {body or title}."]],
            "bibliography": [],
        },
        "liberated": {
            "pre": "[ BEGIN TRANSMISSION ]",
            "post": "[ END TRANSMISSION ]",
            "paragraphs": [
                {
                    "body": [f"{title.upper()} IN {location.upper()}. {body.upper()}."],
                    "margin": None,
                }
            ],
        },
        "intel": {
            "subj": f"{title.upper()} \u00b7 {location.upper()}",
            "origin": "FIELD STATION",
            "routing": ["DHS/I&A"],
            "caveat": "DOMESTIC",
            "fields": [["EVENT", title], ["LOCATION", location], ["CONFIDENCE", "LOW \u00b7 0.50"]],
            "assessment": ["Insufficient data for assessment."],
            "refs": [],
            "distribution": "\u25ae\u25ae\u25ae\u25ae\u25ae\u25ae \u00b7 DOMESTIC",
        },
        "coverage": ["c", "l", "i"],
    }


def _fill_template(text: str, event: dict[str, Any]) -> str:
    """Fill in {location}, {payload_key}, and {euph:term} placeholders.

    {euph:term} placeholders are left for the paragraph-processing functions
    (the actual euphemism span markup happens at render time in the
    frontend). {payload_key} placeholders (e.g. {old_consciousness}) pull
    the real value from the event's data — used by the class-scoped bespoke
    templates (mass_awakening, fascist_drift) whose intel fields/assessment
    cite the actual numbers rather than static flavor text.
    """
    filled = text.replace("{location}", _resolve_location(event))
    for key, value in _event_data_substitutions(event).items():
        filled = filled.replace("{" + key + "}", value)
    return filled


def _fill_hed(hed_template: dict[str, str], event: dict[str, Any]) -> dict[str, str]:
    return {
        "c": _fill_template(hed_template["c"], event),
        "l": _fill_template(hed_template["l"], event),
        "i": _fill_template(hed_template["i"], event),
    }


def _fill_paragraphs(
    paragraphs: list[Any], event: dict[str, Any], template: dict[str, Any]
) -> list[list[Any]]:
    """Process template paragraphs into WireFeed paragraph format.

    Replaces {location} in strings. Leaves {euph:term} markers as span objects
    for the frontend to render. Actually, the frontend expects runs as:
    - string
    - {"euph": "term_id", "text": "display text"}
    - {"sup": int}

    So we need to parse {euph:term} from the template text and produce runs.
    """
    location = _resolve_location(event)
    euphemisms = template.get("euphemisms", {})
    result: list[list[dict[str, Any]]] = []

    for para in paragraphs:
        runs: list[Any] = []
        for run in para:
            if isinstance(run, str):
                # Parse {euph:term} markers and split into runs
                text = run.replace("{location}", location)
                # Also fill {euph:disturbance} style references with the euphemism text
                parts = text.split("{euph:")
                for i, part in enumerate(parts):
                    if i == 0:
                        if part:
                            runs.append(part)
                    else:
                        # This part starts with "term}rest"
                        term_end = part.find("}")
                        if term_end == -1:
                            runs.append(part)
                        else:
                            term_id = part[:term_end]
                            rest = part[term_end + 1 :]
                            if term_id in euphemisms:
                                runs.append({"euph": term_id, "text": euphemisms[term_id]["c"]})
                            if rest:
                                runs.append(rest)
            elif isinstance(run, dict):
                runs.append(dict(run))
        result.append(runs)
    return result


def _fill_liberated_paragraphs(
    paragraphs: list[Any], event: dict[str, Any], template: dict[str, Any]
) -> list[dict[str, Any]]:
    """Process liberated-style paragraphs (with body/margin structure)."""
    location = _resolve_location(event)
    euphemisms = template.get("euphemisms", {})
    result: list[dict[str, Any]] = []

    for para in paragraphs:
        body_runs: list[Any] = []
        for run in para.get("body", []):
            if isinstance(run, str):
                text = run.replace("{location}", location)
                parts = text.split("{euph:")
                for i, part in enumerate(parts):
                    if i == 0:
                        if part:
                            body_runs.append(part)
                    else:
                        term_end = part.find("}")
                        if term_end == -1:
                            body_runs.append(part)
                        else:
                            term_id = part[:term_end]
                            rest = part[term_end + 1 :]
                            if term_id in euphemisms:
                                body_runs.append(
                                    {"euph": term_id, "text": euphemisms[term_id]["l"]}
                                )
                            if rest:
                                body_runs.append(rest)
            elif isinstance(run, dict):
                body_runs.append(dict(run))

        margin = para.get("margin")
        entry: dict[str, Any] = {"body": body_runs}
        if margin is not None:
            entry["margin"] = dict(margin)
        result.append(entry)
    return result


def _fill_intel_fields(fields: list[Any], event: dict[str, Any]) -> list[list[Any]]:
    return [[k, _fill_template(v, event) if isinstance(v, str) else v] for k, v in fields]


def _fill_intel(intel_template: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "classification": "TS//SI//NOFORN",
        "cable_id": f"{event.get('tick', 0):04d}-A",
        "origin": _fill_template(intel_template["origin"], event),
        "routing": list(intel_template["routing"]),
        "caveat": intel_template["caveat"],
        "subj": _fill_template(intel_template["subj"], event),
        "fields": _fill_intel_fields(intel_template["fields"], event),
        "assessment": [_fill_template(a, event) for a in intel_template["assessment"]],
        "refs": [dict(r) for r in intel_template["refs"]],
        "distribution": intel_template["distribution"],
    }
    return result


def _build_index_entry(event: dict[str, Any], template: dict[str, Any]) -> dict[str, Any]:
    location = _resolve_location(event)
    slug = template["slug"].replace("{location}", location.upper())
    hed = _fill_hed(template["hed"], event)
    severity_raw = event.get("severity", "informational")
    severity = _SEVERITY_MAP.get(severity_raw, "info")
    entry: dict[str, Any] = {
        "id": event.get("id", ""),
        "tick": event.get("tick", 0),
        "slug": slug,
        "hed": hed,
        "coverage": list(template.get("coverage", ["c", "l", "i"])),
        "severity": severity,
    }
    return entry


def _build_story(event: dict[str, Any], template: dict[str, Any]) -> dict[str, Any]:
    location = _resolve_location(event)
    continental = template["continental"]
    liberated = template["liberated"]
    intel_template = template["intel"]

    story: dict[str, Any] = {
        "id": event.get("id", ""),
        "tick": event.get("tick", 0),
        "location": location,
        "time_local": "",
        "continental": {
            "brand": "CONTINENTAL",
            "monogram": "C\u2022N",
            "kicker": _fill_template(continental["kicker"], event),
            "hed": _fill_template(continental["dek"], event),  # use dek as hed for the story
            "dek": _fill_template(continental["dek"], event),
            "byline": continental["byline"],
            "paragraphs": _fill_paragraphs(continental["paragraphs"], event, template),
            "bibliography": [dict(b) for b in continental.get("bibliography", [])],
        },
        "liberated": {
            "brand": "FREE SIGNAL",
            "callsign": "WCLF-PIRATE-887",
            "operator": "RASKOVA-2",
            "hed": template["hed"]["l"].replace("{location}", location),
            "pre": _fill_template(liberated["pre"], event),
            "post": _fill_template(liberated["post"], event),
            "paragraphs": _fill_liberated_paragraphs(liberated["paragraphs"], event, template),
        },
        "intel": _fill_intel(intel_template, event),
    }
    # Fix: continental hed should be the headline, not the dek
    story["continental"]["hed"] = _fill_template(template["hed"]["c"], event)
    return story


def _compute_filters(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    filters = _empty_filters()
    filter_index = {f["id"]: f for f in filters}
    for event in events:
        event_type = event.get("type", "")
        hits_map = _EVENT_FILTER_HITS.get(event_type, {})
        for filter_id, hits in hits_map.items():
            if filter_id in filter_index:
                filter_index[filter_id]["hits"] += hits
    return filters


def _select_active_story(events: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Select the active story — the most recent critical/warning event."""
    if not events:
        return None
    # Prefer critical, then warning, then the first event
    for severity in ("critical", "warning"):
        for event in events:
            if event.get("severity") == severity:
                return event
    return events[0]


def _build_meta(meta: dict[str, Any], events: list[dict[str, Any]]) -> dict[str, Any]:
    """Build the wire feed meta block from the provided meta + events."""
    tick = meta.get("tick", 0)
    tick = max(tick, 0) if not events else max(tick, max(e.get("tick", 0) for e in events))
    return {
        "tick": tick,
        "session": meta.get("session", ""),
        "operator": meta.get("operator", "RASKOVA-2"),
        "freq": meta.get("freq", "88.7 MHz"),
        "qth": meta.get("qth", "WAYNE CO / GRID EN82"),
        "classification": meta.get("classification", "TS//SI//NOFORN"),
        "cable_id": meta.get("cable_id", f"{tick:04d}-A"),
        "page_of": meta.get("page_of", "001/001"),
        "timestamp_utc": meta.get("timestamp_utc", "2026-01-01T00:00:00Z"),
    }


# --------------------------------------------------------------------------- #
# NarratorProvider Protocol
# --------------------------------------------------------------------------- #


@runtime_checkable
class NarratorProvider(Protocol):
    """Interface for Wire feed narration.

    Implementations MUST be pure functions: same inputs produce byte-identical
    outputs. No engine state writes (Constitution III). The ``visibility``
    parameter is a no-op pass-through until spec-077 supplies the hegemony
    mechanic.
    """

    def narrate(
        self,
        events: list[dict[str, Any]],
        meta: dict[str, Any],
        visibility: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Produce a WireFeed dict from GameEvent dicts.

        Args:
            events: List of GameEvent dicts (id/type/tick/severity/title/body/data).
            meta: Presentation metadata (tick/session/operator/freq/qth/...).
            visibility: No-op pass-through for spec-077 hegemony hooks.

        Returns:
            WireFeed dict matching specs/094-the-wire/contracts/wire.yaml.
        """
        ...


# --------------------------------------------------------------------------- #
# DeterministicNarrator — template-based implementation
# --------------------------------------------------------------------------- #


class DeterministicNarrator:
    """Template-based narrator. Same events produce byte-identical output.

    No LLM calls (R-NARR ruling). No ``babylon.*`` imports (Constitution III).
    Pure ``dict -> dict`` function with no side effects.
    """

    def narrate(
        self,
        events: list[dict[str, Any]],
        meta: dict[str, Any],
        visibility: dict[str, Any] | None = None,  # noqa: ARG002 — no-op pass-through (spec-077)
    ) -> dict[str, Any]:
        """Produce a WireFeed from GameEvent dicts.

        This is a pure function: same inputs always produce the same output.
        The ``visibility`` parameter is accepted but ignored (no-op pass-through
        for spec-077 hegemony hooks).
        """
        # Deep-copy inputs to prevent any mutation
        events_copy = [dict(e) for e in events]
        meta_copy = dict(meta)

        # Real per-scenario class names from the bridge (meta["class_names"]).
        # Stamped onto each event copy as a private key so the module-level
        # fill helpers can resolve class ids without a signature cascade;
        # _build_meta allowlists output keys, so the channel never leaks
        # into the wire.yaml contract.
        class_names = meta_copy.get("class_names")
        if isinstance(class_names, dict):
            for event in events_copy:
                event["_class_names"] = class_names

        # Real per-scenario org names from the bridge (meta["org_names"]),
        # AW3-R1 — mirrors the class_names channel above for org-scoped
        # events (RED_BROWN_COUP). _build_meta allowlists output keys, so
        # this channel never leaks into the wire.yaml contract either.
        org_names = meta_copy.get("org_names")
        if isinstance(org_names, dict):
            for event in events_copy:
                event["_org_names"] = org_names

        # Build index entries
        index_entries: list[dict[str, Any]] = []
        all_euphemisms: dict[str, dict[str, Any]] = {}

        for event in events_copy:
            event_type = event.get("type", "")
            template = _TEMPLATES.get(event_type) or _generic_template(event)
            index_entries.append(_build_index_entry(event, template))

            # Collect euphemisms from this template
            for term_id, entry in template.get("euphemisms", {}).items():
                if term_id not in all_euphemisms:
                    all_euphemisms[term_id] = dict(entry)

        # Select active story
        active_event = _select_active_story(events_copy)
        story: dict[str, Any] | None = None
        if active_event is not None:
            active_type = active_event.get("type", "")
            active_template = _TEMPLATES.get(active_type) or _generic_template(active_event)
            story = _build_story(active_event, active_template)

            # Ensure the active story's euphemisms are in the map
            for term_id, entry in active_template.get("euphemisms", {}).items():
                if term_id not in all_euphemisms:
                    all_euphemisms[term_id] = dict(entry)

        # Compute Manufacturing Consent filters
        filters = _compute_filters(events_copy)

        # Build meta
        wire_meta = _build_meta(meta_copy, events_copy)

        return {
            "meta": wire_meta,
            "index": index_entries,
            "euphemisms": all_euphemisms,
            "story": story,
            "filters": filters,
        }
