"""Tests for per-verb action serializers (Spec 040).

Each verb has a dedicated serializer that validates verb-specific fields
beyond the common base (org_id, target_id). These tests verify:
- Valid input acceptance
- Missing required params rejection
- Invalid enum values rejection
"""

from __future__ import annotations

import pytest


@pytest.mark.unit
class TestBaseActionSerializer:
    """BaseActionSerializer validates common fields shared by all verbs."""

    def test_valid_common_fields(self) -> None:
        from game.serializers import BaseActionSerializer

        s = BaseActionSerializer(data={"org_id": "org_1", "target_id": "hex_abc"})
        assert s.is_valid(), s.errors

    def test_missing_org_id(self) -> None:
        from game.serializers import BaseActionSerializer

        s = BaseActionSerializer(data={"target_id": "hex_abc"})
        assert not s.is_valid()
        assert "org_id" in s.errors

    def test_missing_target_id(self) -> None:
        from game.serializers import BaseActionSerializer

        s = BaseActionSerializer(data={"org_id": "org_1"})
        assert not s.is_valid()
        assert "target_id" in s.errors


@pytest.mark.unit
class TestEducateActionSerializer:
    """EducateActionSerializer requires consciousness_strategy."""

    def test_valid_educate(self) -> None:
        from game.serializers import EducateActionSerializer

        s = EducateActionSerializer(
            data={
                "org_id": "org_1",
                "target_id": "community_a",
                "consciousness_strategy": "REVOLUTIONARY",
            }
        )
        assert s.is_valid(), s.errors

    def test_all_consciousness_strategies(self) -> None:
        from game.serializers import EducateActionSerializer

        for strategy in ("REVOLUTIONARY", "LIBERAL", "FASCIST"):
            s = EducateActionSerializer(
                data={
                    "org_id": "org_1",
                    "target_id": "community_a",
                    "consciousness_strategy": strategy,
                }
            )
            assert s.is_valid(), f"Strategy {strategy} failed: {s.errors}"

    def test_missing_consciousness_strategy(self) -> None:
        from game.serializers import EducateActionSerializer

        s = EducateActionSerializer(data={"org_id": "org_1", "target_id": "community_a"})
        assert not s.is_valid()
        assert "consciousness_strategy" in s.errors

    def test_invalid_consciousness_strategy(self) -> None:
        from game.serializers import EducateActionSerializer

        s = EducateActionSerializer(
            data={
                "org_id": "org_1",
                "target_id": "community_a",
                "consciousness_strategy": "ANARCHIST",
            }
        )
        assert not s.is_valid()
        assert "consciousness_strategy" in s.errors


@pytest.mark.unit
class TestAidActionSerializer:
    """AidActionSerializer requires resource_type and amount."""

    def test_valid_aid(self) -> None:
        from game.serializers import AidActionSerializer

        s = AidActionSerializer(
            data={
                "org_id": "org_1",
                "target_id": "org_2",
                "resource_type": "MATERIAL",
                "amount": 5.0,
            }
        )
        assert s.is_valid(), s.errors

    def test_all_resource_types(self) -> None:
        from game.serializers import AidActionSerializer

        for rt in ("MATERIAL", "MEDICAL", "LEGAL", "INFRASTRUCTURE"):
            s = AidActionSerializer(
                data={
                    "org_id": "org_1",
                    "target_id": "org_2",
                    "resource_type": rt,
                    "amount": 1.0,
                }
            )
            assert s.is_valid(), f"Resource type {rt} failed: {s.errors}"

    def test_missing_resource_type(self) -> None:
        from game.serializers import AidActionSerializer

        s = AidActionSerializer(data={"org_id": "org_1", "target_id": "org_2", "amount": 5.0})
        assert not s.is_valid()
        assert "resource_type" in s.errors

    def test_missing_amount(self) -> None:
        from game.serializers import AidActionSerializer

        s = AidActionSerializer(
            data={"org_id": "org_1", "target_id": "org_2", "resource_type": "MATERIAL"}
        )
        assert not s.is_valid()
        assert "amount" in s.errors

    def test_invalid_resource_type(self) -> None:
        from game.serializers import AidActionSerializer

        s = AidActionSerializer(
            data={
                "org_id": "org_1",
                "target_id": "org_2",
                "resource_type": "NUCLEAR",
                "amount": 5.0,
            }
        )
        assert not s.is_valid()
        assert "resource_type" in s.errors


@pytest.mark.unit
class TestAttackSubmitSerializer:
    """AttackSubmitSerializer requires mode."""

    def test_valid_attack(self) -> None:
        from game.serializers import AttackSubmitSerializer

        s = AttackSubmitSerializer(
            data={"org_id": "org_1", "target_id": "org_2", "params": {"mode": "targeted"}}
        )
        assert s.is_valid(), s.errors

    def test_all_modes(self) -> None:
        from game.serializers import AttackSubmitSerializer

        for mode in ("targeted", "mass"):
            s = AttackSubmitSerializer(
                data={"org_id": "org_1", "target_id": "org_2", "params": {"mode": mode}}
            )
            assert s.is_valid(), f"Mode {mode} failed: {s.errors}"

    def test_missing_mode(self) -> None:
        from game.serializers import AttackSubmitSerializer

        s = AttackSubmitSerializer(data={"org_id": "org_1", "target_id": "org_2", "params": {}})
        assert not s.is_valid()
        assert "mode" in s.errors["params"]

    def test_invalid_mode(self) -> None:
        from game.serializers import AttackSubmitSerializer

        s = AttackSubmitSerializer(
            data={"org_id": "org_1", "target_id": "org_2", "params": {"mode": "NUKE"}}
        )
        assert not s.is_valid()
        assert "mode" in s.errors["params"]


@pytest.mark.unit
class TestCampaignActionSerializer:
    """CampaignActionSerializer requires campaign_type."""

    def test_valid_campaign(self) -> None:
        from game.serializers import CampaignActionSerializer

        s = CampaignActionSerializer(
            data={
                "org_id": "org_1",
                "target_id": "institution_1",
                "campaign_type": "ELECTORAL",
            }
        )
        assert s.is_valid(), s.errors

    def test_all_campaign_types(self) -> None:
        from game.serializers import CampaignActionSerializer

        for ct in ("ELECTORAL", "LEGISLATIVE", "PUBLIC_PRESSURE"):
            s = CampaignActionSerializer(
                data={
                    "org_id": "org_1",
                    "target_id": "institution_1",
                    "campaign_type": ct,
                }
            )
            assert s.is_valid(), f"Campaign type {ct} failed: {s.errors}"

    def test_missing_campaign_type(self) -> None:
        from game.serializers import CampaignActionSerializer

        s = CampaignActionSerializer(data={"org_id": "org_1", "target_id": "institution_1"})
        assert not s.is_valid()
        assert "campaign_type" in s.errors
