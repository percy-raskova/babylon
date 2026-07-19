"""Tests for the QCEW-sourced Business seed artifact + runtime builder (ADR086).

Two layers of verification:

- **Artifact provenance (pure, DB-free)** — pins the committed real-data values
  so any drift is caught in CI without touching the data drive. The exact
  employment figures below are the real BLS QCEW private-sector aggregates
  (year 2024) spot-verified against ``fact_qcew_annual`` at generation time.
- **Builder determinism/shape** — ``build_seeded_businesses`` is pure and
  deterministic, produces real ``Business`` models, and fails loudly on an
  unknown scope.
- **DB re-derivation (drive-gated)** — when the reference DB is present, the
  artifact's Wayne figures are re-derived through the SAME house consumer
  (``get_county_employment_by_naics``) the game economics uses, proving the
  artifact is not a stale hand-edit.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from babylon.engine.scenarios.business_seeds import (
    ARTIFACT_PATH,
    build_seeded_businesses,
    load_seed_data,
)
from babylon.models.entities.organization import Business
from babylon.models.enums import ClassCharacter, OrgType

# Real QCEW private-sector employment (2024), spot-verified against the raw DB.
_WAYNE_HEALTHCARE_2024 = 116760
_WAYNE_MANUFACTURING_2024 = 89659
_US_HEALTHCARE_2024 = 22046994

_REFERENCE_DB = Path(__file__).resolve().parents[4] / "data" / "sqlite" / "marxist-data-3NF.sqlite"


class TestSeedArtifactProvenance:
    """The committed artifact carries real, verifiable QCEW figures."""

    def test_artifact_has_both_canonical_scopes(self) -> None:
        data = load_seed_data()
        assert set(data["scopes"]) == {"US", "26163"}

    def test_content_hash_matches_scopes(self) -> None:
        """The stamped hash is the sha256 of the canonical scope payload —
        a tamper/regeneration integrity check."""
        data = load_seed_data()
        canonical = json.dumps(data["scopes"], sort_keys=True, separators=(",", ":"))
        recomputed = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        assert data["content_hash"] == recomputed

    def test_wayne_healthcare_is_the_real_figure(self) -> None:
        """Real BLS value, never a rounded invention (116,760 is not round)."""
        data = load_seed_data()
        wayne = {
            s["naics_2digit"]: s["employment_count"] for s in data["scopes"]["26163"]["sectors"]
        }
        assert wayne["62"] == _WAYNE_HEALTHCARE_2024
        assert wayne["31-33"] == _WAYNE_MANUFACTURING_2024

    def test_us_healthcare_is_the_real_figure(self) -> None:
        data = load_seed_data()
        us = {s["naics_2digit"]: s["employment_count"] for s in data["scopes"]["US"]["sectors"]}
        assert us["62"] == _US_HEALTHCARE_2024

    def test_employment_values_are_not_round_inventions(self) -> None:
        """Fabricated seed numbers are almost always round; real QCEW totals
        are not. Every pinned figure fails a %1000==0 round-number test."""
        for value in (_WAYNE_HEALTHCARE_2024, _WAYNE_MANUFACTURING_2024, _US_HEALTHCARE_2024):
            assert value % 1000 != 0

    def test_sectors_are_rank_ordered_by_employment(self) -> None:
        data = load_seed_data()
        for entry in data["scopes"].values():
            emps = [s["employment_count"] for s in entry["sectors"]]
            assert emps == sorted(emps, reverse=True)
            assert [s["rank"] for s in entry["sectors"]] == list(range(1, len(emps) + 1))


class TestBuildSeededBusinesses:
    """``build_seeded_businesses`` is pure, deterministic, and honest."""

    def test_two_builds_are_identical(self) -> None:
        """Determinism (Constitution III.7): same inputs -> same output."""
        a = build_seeded_businesses("26163", ["T1", "T2"])
        b = build_seeded_businesses("26163", ["T1", "T2"])
        assert a == b
        assert list(a) == list(b)  # identical id ordering

    def test_all_are_real_bourgeois_businesses(self) -> None:
        businesses = build_seeded_businesses("26163", ["T1"])
        assert businesses  # non-empty
        for biz in businesses.values():
            assert isinstance(biz, Business)
            assert biz.org_type == OrgType.BUSINESS
            assert biz.class_character == ClassCharacter.BOURGEOIS
            assert biz.sector  # non-empty real title
            assert biz.employment_count > 0

    def test_employment_matches_artifact_exactly(self) -> None:
        data = load_seed_data()
        expected = {
            s["sector_title"]: s["employment_count"] for s in data["scopes"]["26163"]["sectors"]
        }
        for biz in build_seeded_businesses("26163", []).values():
            assert biz.employment_count == expected[biz.sector]

    def test_names_use_real_geography_and_sector(self) -> None:
        businesses = build_seeded_businesses("26163", ["T1"])
        names = {b.name for b in businesses.values()}
        assert "Wayne County Healthcare" in names
        assert "Wayne County Manufacturing" in names

    def test_us_scope_names(self) -> None:
        names = {b.name for b in build_seeded_businesses("US", ["T1"]).values()}
        assert "United States Healthcare" in names

    def test_territories_are_applied(self) -> None:
        businesses = build_seeded_businesses("US", ["HEX_A", "HEX_B"])
        for biz in businesses.values():
            assert biz.territory_ids == ["HEX_A", "HEX_B"]

    def test_ids_are_deterministic_unique_and_ordered(self) -> None:
        ids = list(build_seeded_businesses("US", []))
        assert ids == sorted(ids)  # BIZ_US_01, BIZ_US_02, ...
        assert len(ids) == len(set(ids))
        assert all(i.startswith("BIZ_US_") for i in ids)

    def test_unknown_scope_fails_loudly(self) -> None:
        """No silent empty seeding for a typo'd scope (Constitution III.11)."""
        with pytest.raises(KeyError):
            build_seeded_businesses("nonexistent", [])


@pytest.mark.skipif(
    not _REFERENCE_DB.exists(),
    reason="reference DB absent (CI-without-drive); provenance pinned by committed values above",
)
class TestArtifactReDerivesFromDB:
    """When the drive is present, the artifact is re-derivable through the SAME
    house consumer the game economics uses — proving it is not a stale edit."""

    def test_wayne_matches_house_consumer(self) -> None:
        from babylon.domain.economics.throughput.adapters import SQLiteQCEWCountyNAICSSource
        from babylon.reference.database import get_normalized_session_factory

        data = load_seed_data()
        year = data["source"]["year"]
        source = SQLiteQCEWCountyNAICSSource(get_normalized_session_factory())
        by_label = source.get_county_employment_by_naics("26163", year)
        for sector in data["scopes"]["26163"]["sectors"]:
            assert by_label[sector["naics_2digit"]] == sector["employment_count"]


def test_artifact_path_points_at_committed_file() -> None:
    assert ARTIFACT_PATH.name == "business_seeds.json"
    assert ARTIFACT_PATH.exists()
