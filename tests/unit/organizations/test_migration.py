"""Tests for legacy migration (Feature 031, T030).

Tests migration of factions.json and institutions.json into Organization
subtypes per R8 mapping table.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from babylon.models.enums import (
    ConsciousnessTendency,
    OrgType,
    ServiceType,
)
from babylon.organizations.migration import (
    migrate_all,
    migrate_faction,
    migrate_institution,
)

DATA_DIR = Path(__file__).resolve().parents[3] / "src" / "babylon" / "data" / "game"


class TestMigrateFaction:
    """migrate_faction: faction JSON dict -> PoliticalFaction."""

    @pytest.mark.ledger
    def test_f001_fascist_tendency(self) -> None:
        """F001 'National Revival Movement' maps to FASCIST tendency."""
        data = _load_faction("F001")
        org = migrate_faction(data)
        assert org.org_type == OrgType.POLITICAL_FACTION
        assert org.id == "F001"
        assert org.name == "National Revival Movement"
        assert org.consciousness_tendency == ConsciousnessTendency.FASCIST
        assert org.ideology == "Fascism"

    @pytest.mark.ledger
    def test_f002_liberal_tendency(self) -> None:
        """F002 'Liberal Democratic Alliance' maps to LIBERAL tendency."""
        data = _load_faction("F002")
        org = migrate_faction(data)
        assert org.consciousness_tendency == ConsciousnessTendency.LIBERAL

    @pytest.mark.ledger
    def test_f003_revolutionary_tendency(self) -> None:
        """F003 'Revolutionary Workers Party' maps to REVOLUTIONARY tendency."""
        data = _load_faction("F003")
        org = migrate_faction(data)
        assert org.consciousness_tendency == ConsciousnessTendency.REVOLUTIONARY
        assert org.ideology == "Marxism-Leninism"

    @pytest.mark.ledger
    def test_f004_revolutionary_tendency(self) -> None:
        """F004 'People's Liberation Front' (MLM) maps to REVOLUTIONARY tendency."""
        data = _load_faction("F004")
        org = migrate_faction(data)
        assert org.consciousness_tendency == ConsciousnessTendency.REVOLUTIONARY

    @pytest.mark.ledger
    def test_all_four_factions_migrate(self) -> None:
        """All 4 factions migrate to PoliticalFaction."""
        factions_path = DATA_DIR / "factions.json"
        with factions_path.open() as f:
            data = json.load(f)
        for faction_data in data["factions"]:
            org = migrate_faction(faction_data)
            assert org.org_type == OrgType.POLITICAL_FACTION


class TestMigrateInstitution:
    """migrate_institution: institution JSON dict -> Organization subtype or None."""

    @pytest.mark.ledger
    def test_inst001_systemic_racism_dropped(self) -> None:
        """Inst001 'Systemic Racism' is dropped (not an organization)."""
        data = _load_institution("Inst001")
        result = migrate_institution(data)
        assert result is None

    @pytest.mark.ledger
    def test_inst002_policing_state_apparatus(self) -> None:
        """Inst002 'Policing' → StateApparatus."""
        data = _load_institution("Inst002")
        org = migrate_institution(data)
        assert org is not None
        assert org.org_type == OrgType.STATE_APPARATUS
        assert org.name == "Policing"

    @pytest.mark.ledger
    def test_inst003_mass_media_civil_society(self) -> None:
        """Inst003 'Mass Media' → CivilSocietyOrg(service_type=MEDIA)."""
        data = _load_institution("Inst003")
        org = migrate_institution(data)
        assert org is not None
        assert org.org_type == OrgType.CIVIL_SOCIETY
        assert org.service_type == ServiceType.MEDIA  # type: ignore[union-attr]

    @pytest.mark.ledger
    def test_inst004_labor_unions_civil_society(self) -> None:
        """Inst004 'Labor Unions' → CivilSocietyOrg(service_type=LABOR)."""
        data = _load_institution("Inst004")
        org = migrate_institution(data)
        assert org is not None
        assert org.org_type == OrgType.CIVIL_SOCIETY
        assert org.service_type == ServiceType.LABOR  # type: ignore[union-attr]

    @pytest.mark.ledger
    def test_inst005_military_state_apparatus(self) -> None:
        """Inst005 'Military' → StateApparatus."""
        data = _load_institution("Inst005")
        org = migrate_institution(data)
        assert org is not None
        assert org.org_type == OrgType.STATE_APPARATUS

    @pytest.mark.ledger
    def test_inst006_religious_civil_society(self) -> None:
        """Inst006 'Religious Institutions' → CivilSocietyOrg(service_type=RELIGIOUS)."""
        data = _load_institution("Inst006")
        org = migrate_institution(data)
        assert org is not None
        assert org.org_type == OrgType.CIVIL_SOCIETY
        assert org.service_type == ServiceType.RELIGIOUS  # type: ignore[union-attr]

    @pytest.mark.ledger
    def test_inst007_higher_education_civil_society(self) -> None:
        """Inst007 'Higher Education' → CivilSocietyOrg(service_type=EDUCATIONAL)."""
        data = _load_institution("Inst007")
        org = migrate_institution(data)
        assert org is not None
        assert org.org_type == OrgType.CIVIL_SOCIETY
        assert org.service_type == ServiceType.EDUCATIONAL  # type: ignore[union-attr]

    @pytest.mark.ledger
    def test_all_seven_institutions_migrate(self) -> None:
        """7 institutions: 6 to org subtypes, 1 dropped."""
        institutions_path = DATA_DIR / "institutions.json"
        with institutions_path.open() as f:
            data = json.load(f)
        results = [migrate_institution(inst) for inst in data["institutions"]]
        non_none = [r for r in results if r is not None]
        none_count = sum(1 for r in results if r is None)
        assert len(non_none) == 6
        assert none_count == 1


class TestMigrateAll:
    """migrate_all: batch migration returning org dict."""

    @pytest.mark.ledger
    def test_total_org_count(self) -> None:
        """4 factions + 6 institutions (1 dropped) = 10 orgs."""
        factions_path = DATA_DIR / "factions.json"
        institutions_path = DATA_DIR / "institutions.json"
        result = migrate_all(factions_path, institutions_path)
        assert len(result) == 10

    @pytest.mark.ledger
    def test_keys_are_ids(self) -> None:
        """Result dict keys are organization IDs."""
        factions_path = DATA_DIR / "factions.json"
        institutions_path = DATA_DIR / "institutions.json"
        result = migrate_all(factions_path, institutions_path)
        assert "F001" in result
        assert "F003" in result
        assert "Inst002" in result
        assert "Inst001" not in result  # dropped


# =========================================================================
# Helpers
# =========================================================================


def _load_faction(faction_id: str) -> dict:
    """Load a single faction by ID from factions.json."""
    factions_path = DATA_DIR / "factions.json"
    with factions_path.open() as f:
        data = json.load(f)
    for faction in data["factions"]:
        if faction["id"] == faction_id:
            return faction
    msg = f"Faction {faction_id} not found"
    raise ValueError(msg)


def _load_institution(inst_id: str) -> dict:
    """Load a single institution by ID from institutions.json."""
    institutions_path = DATA_DIR / "institutions.json"
    with institutions_path.open() as f:
        data = json.load(f)
    for inst in data["institutions"]:
        if inst["id"] == inst_id:
            return inst
    msg = f"Institution {inst_id} not found"
    raise ValueError(msg)
