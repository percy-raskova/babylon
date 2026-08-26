"""Typed, checked-in check manifests for Babylon pull-request policy."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal

CheckKind = Literal["blocking", "advisory"]


@dataclass(frozen=True, slots=True)
class CheckRequirement:
    """One expected check and its exact accepted conclusions."""

    context: str
    kind: CheckKind
    allowed_conclusions: frozenset[str]


BASELINE_CEREMONY_CONTEXT: Final[str] = "Baseline Ceremony Gate (§6.5 provenance)"


DEV_CHECK_MANIFEST: Final[tuple[CheckRequirement, ...]] = (
    CheckRequirement(
        "Fast Gate (hygiene, lint, format, imports, types, lock)",
        "blocking",
        frozenset({"SUCCESS"}),
    ),
    CheckRequirement("Unit Tests (xdist, coverage gate)", "blocking", frozenset({"SUCCESS"})),
    CheckRequirement(
        "Determinism Gate (byte-identical dense goldens)",
        "blocking",
        frozenset({"SUCCESS"}),
    ),
    CheckRequirement("Secret Scan (gitleaks, full history)", "blocking", frozenset({"SUCCESS"})),
    CheckRequirement(
        "IaC Config Scan (trivy, HIGH+CRITICAL blocking)",
        "blocking",
        frozenset({"SUCCESS"}),
    ),
    CheckRequirement(
        "Security Audit (pip-audit policy — blocking since item-41)",
        "blocking",
        frozenset({"SUCCESS"}),
    ),
    CheckRequirement(
        "Rust Gate (fmt, clippy, test, doc — rust/ workspace)",
        "blocking",
        frozenset({"SUCCESS"}),
    ),
    CheckRequirement(BASELINE_CEREMONY_CONTEXT, "blocking", frozenset({"SUCCESS"})),
    CheckRequirement(
        "Postgres Integration Tier (PG 17, pinned runtime)",
        "blocking",
        frozenset({"SUCCESS"}),
    ),
)

MAIN_CHECK_MANIFEST: Final[tuple[CheckRequirement, ...]] = (
    CheckRequirement(
        "Fast Gate (hygiene, lint, format, imports, types, lock)",
        "blocking",
        frozenset({"SUCCESS"}),
    ),
    CheckRequirement("Unit Tests (xdist, coverage gate)", "blocking", frozenset({"SUCCESS"})),
    CheckRequirement(
        "Determinism Gate (byte-identical dense goldens)",
        "blocking",
        frozenset({"SUCCESS"}),
    ),
    CheckRequirement(
        "Security Audit (pip-audit policy — blocking since item-41)",
        "blocking",
        frozenset({"SUCCESS"}),
    ),
    CheckRequirement(
        "Non-Unit Tests (integration, scenarios, property, contract)",
        "blocking",
        frozenset({"SUCCESS"}),
    ),
    CheckRequirement("Postgres Integration (web bridge)", "blocking", frozenset({"SUCCESS"})),
    CheckRequirement(
        "Determinism Bundle (Postgres-backed, strict)",
        "blocking",
        frozenset({"SUCCESS"}),
    ),
    CheckRequirement(
        "Reference-Data Tests (ci-data-v1 subset)",
        "blocking",
        frozenset({"SUCCESS"}),
    ),
    CheckRequirement(
        "Documentation Build (doctest blocks; manual advisory)",
        "blocking",
        frozenset({"SUCCESS"}),
    ),
    CheckRequirement("Secret Scan (gitleaks, full history)", "blocking", frozenset({"SUCCESS"})),
    CheckRequirement(
        "IaC Config Scan (trivy, HIGH+CRITICAL blocking)",
        "blocking",
        frozenset({"SUCCESS"}),
    ),
    CheckRequirement(
        "AI Tests (advisory — non-deterministic)",
        "advisory",
        frozenset({"SUCCESS", "NEUTRAL", "SKIPPED"}),
    ),
    CheckRequirement(
        "Image Scan (trivy — advisory until postgis bump)",
        "advisory",
        frozenset({"SUCCESS", "NEUTRAL", "SKIPPED"}),
    ),
)

DEV_BLOCKING_CONTEXTS: Final[tuple[str, ...]] = tuple(
    requirement.context for requirement in DEV_CHECK_MANIFEST if requirement.kind == "blocking"
)


def manifest_for_base(base_ref: str) -> tuple[CheckRequirement, ...]:
    """Return the exact expected manifest for one sanctioned base."""
    if base_ref == "dev":
        return DEV_CHECK_MANIFEST
    if base_ref == "main":
        return MAIN_CHECK_MANIFEST
    raise ValueError(f"no check manifest for base {base_ref!r}")
