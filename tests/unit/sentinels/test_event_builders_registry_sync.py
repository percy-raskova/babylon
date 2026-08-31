"""The ``EVENT_BUILDERS ⊆ registry`` one-way sync test (R4.4.1, C-1/I-5).

Mechanism tests run against synthetic registries/builder sources so they pin
the check's CONTRACT (the normalization rule, the direction of containment,
what counts as a violation) independent of the estate's own current facts —
the same split ``tests/unit/sentinels/test_fallback_coverage.py`` already
uses. ``TestTheRealEstateSyncsToday`` is the conformance half: it proves the
SHIPPED registry (``docs/reference/event-schema-registry.toml``) actually
contains every field the real ``EVENT_BUILDERS`` reads, right now — the task
brief's own requirement that this test "must PASS on the real estate at
landing."
"""

from __future__ import annotations

from pathlib import Path

import pytest

from babylon.sentinels.event_schema_registry.registry import (
    EventSchemaRegistry,
    RegistryKey,
    Tier1Row,
    Tier2Row,
    Tier3Row,
    load_registry,
)
from babylon.sentinels.event_schema_registry.sync import (
    event_builders_subset_violations,
    normalize_key,
)
from babylon.sentinels.fallback_coverage.registry import EVENT_BUILDERS_DICT, EVENT_BUILDERS_PATH


def _key(name: str, *, required: bool = True, source: str = "bsl") -> RegistryKey:
    return RegistryKey(name=name, required=required, source=source)


def _registry(
    tier1: tuple[Tier1Row, ...] = (), tier2: tuple[Tier2Row, ...] = ()
) -> EventSchemaRegistry:
    return EventSchemaRegistry(
        schema_version=2,
        measured_at="2026-08-18",
        python_event_type_total=100,
        # This factory supplies no BSL corpus; rows are synthetic sync inputs.
        bsl_emit_site_total=0,
        bsl_emit_name_total=0,
        bsl_content_glob="rust/crates/babylon-tick/content/rules/*.bsl",
        tier1=tier1,
        tier2=tier2,
        tier3=(Tier3Row(event_type="UNCOVERED", note="test"),),
    )


class TestNormalizeKey:
    """The ONE stated normalization rule: ``_`` and ``-`` compare equal."""

    def test_underscore_becomes_hyphen(self) -> None:
        assert normalize_key("territory_id") == "territory-id"

    def test_already_hyphenated_is_unchanged(self) -> None:
        assert normalize_key("territory-id") == "territory-id"

    def test_a_key_with_no_separator_is_unchanged(self) -> None:
        assert normalize_key("wealth") == "wealth"

    def test_both_spellings_normalize_to_the_same_string(self) -> None:
        assert normalize_key("solidarity_strength") == normalize_key("solidarity-strength")

    def test_case_is_not_touched(self) -> None:
        """The stated rule is `_` <-> `-` ONLY — a case mismatch must still
        fail loudly, not be silently forgiven by an over-eager normalizer."""
        assert normalize_key("Territory_Id") != normalize_key("territory-id")


class TestEventBuildersSubsetViolationsMechanism:
    """Synthetic registries + synthetic builder sources — pins the CHECK's
    contract, independent of the real estate's current facts."""

    def _write_builders(self, tmp_path: Path, body: str) -> Path:
        path = tmp_path / "synthetic_builders.py"
        path.write_text(
            f"from babylon.models.enums import EventType\n\n_BUILDERS = {{\n{body}\n}}\n"
        )
        return path

    def test_exact_match_is_clean(self, tmp_path: Path) -> None:
        registry = _registry(
            tier1=(
                Tier1Row(
                    event_type="FOO",
                    citations=("x.bsl:1",),
                    keys=(_key("wealth"), _key("target-id")),
                ),
            )
        )
        builders = self._write_builders(
            tmp_path,
            "    EventType.FOO: lambda tick, timestamp, payload: Foo(\n"
            '        wealth=payload.get("wealth", 0.0),\n'
            '        target_id=payload.get("target_id", ""),\n'
            "    ),\n",
        )
        violations = event_builders_subset_violations(
            registry, builders_path=builders, builders_dict="_BUILDERS"
        )
        assert violations == []

    def test_underscore_hyphen_mismatch_alone_is_not_a_violation(self, tmp_path: Path) -> None:
        """The whole point of stating the normalization rule: the FIRST run
        must not fail on spelling convention alone."""
        registry = _registry(
            tier1=(
                Tier1Row(
                    event_type="FOO",
                    citations=("x.bsl:1",),
                    keys=(_key("solidarity-strength"),),
                ),
            )
        )
        builders = self._write_builders(
            tmp_path,
            "    EventType.FOO: lambda tick, timestamp, payload: Foo(\n"
            '        solidarity_strength=payload.get("solidarity_strength", 0.0),\n'
            "    ),\n",
        )
        violations = event_builders_subset_violations(
            registry, builders_path=builders, builders_dict="_BUILDERS"
        )
        assert violations == []

    def test_a_builder_field_absent_from_the_registry_row_is_a_violation(
        self, tmp_path: Path
    ) -> None:
        registry = _registry(
            tier1=(Tier1Row(event_type="FOO", citations=("x.bsl:1",), keys=(_key("wealth"),)),)
        )
        builders = self._write_builders(
            tmp_path,
            "    EventType.FOO: lambda tick, timestamp, payload: Foo(\n"
            '        wealth=payload.get("wealth", 0.0),\n'
            '        cause=payload.get("cause", "unknown"),\n'
            "    ),\n",
        )
        violations = event_builders_subset_violations(
            registry, builders_path=builders, builders_dict="_BUILDERS"
        )
        assert len(violations) == 1
        assert "FOO" in violations[0]
        assert "cause" in violations[0]

    def test_a_builder_for_an_eventtype_with_no_registry_row_at_all_is_a_violation(
        self, tmp_path: Path
    ) -> None:
        registry = _registry()  # no tier1, no tier2 rows at all
        builders = self._write_builders(
            tmp_path,
            "    EventType.UNREGISTERED: lambda tick, timestamp, payload: Foo(\n"
            '        wealth=payload.get("wealth", 0.0),\n'
            "    ),\n",
        )
        violations = event_builders_subset_violations(
            registry, builders_path=builders, builders_dict="_BUILDERS"
        )
        assert len(violations) == 1
        assert "UNREGISTERED" in violations[0]

    def test_a_builder_with_no_payload_reads_at_all_is_never_a_violation(
        self, tmp_path: Path
    ) -> None:
        """An EventType with no registry row and a builder that reads
        nothing off the payload has nothing to be a subset violation about —
        an empty field set is trivially a subset of anything, including
        'no row'."""
        registry = _registry()
        builders = self._write_builders(
            tmp_path,
            "    EventType.NOFIELDS: lambda tick, timestamp, payload: Foo(),\n",
        )
        violations = event_builders_subset_violations(
            registry, builders_path=builders, builders_dict="_BUILDERS"
        )
        assert violations == []

    def test_tier2_rows_satisfy_the_check_by_construction(self, tmp_path: Path) -> None:
        """Tier 2 rows ARE the builder's own field set (transcribed) — this
        is the C-1 "satisfied by construction" case, exercised directly."""
        registry = _registry(
            tier2=(
                Tier2Row(
                    event_type="BAR",
                    note="test",
                    keys=(_key("org_id", source="builder"), _key("target_id", source="builder")),
                ),
            )
        )
        builders = self._write_builders(
            tmp_path,
            "    EventType.BAR: lambda tick, timestamp, payload: Bar(\n"
            '        org_id=payload.get("org_id", ""),\n'
            '        target_id=payload.get("target_id", ""),\n'
            "    ),\n",
        )
        violations = event_builders_subset_violations(
            registry, builders_path=builders, builders_dict="_BUILDERS"
        )
        assert violations == []

    def test_a_control_ratio_crisis_shaped_narrower_builder_is_clean(self, tmp_path: Path) -> None:
        """The survey's own worked example: a builder reading FEWER fields
        than a Tier 1 row's UNION (some of them optional/branch-specific) is
        not a violation — narrower is always fine, only EXTRA fields are."""
        registry = _registry(
            tier1=(
                Tier1Row(
                    event_type="CONTROL_RATIO_CRISIS",
                    citations=("cr.bsl:1", "cr.bsl:2"),
                    keys=(
                        _key("enforcer-population"),
                        _key("prisoner-population"),
                        _key("control-capacity"),
                        _key("max-controllable"),
                        _key("over-capacity-by"),
                        _key("capacity-threshold"),
                        _key("actual-ratio", required=False),
                        _key("control-ratio", required=False),
                    ),
                ),
            )
        )
        builders = self._write_builders(
            tmp_path,
            "    EventType.CONTROL_RATIO_CRISIS: lambda tick, timestamp, payload: X(\n"
            '        prisoner_population=payload.get("prisoner_population", 0),\n'
            '        enforcer_population=payload.get("enforcer_population", 0),\n'
            '        control_ratio=payload.get("control_ratio", 0.0),\n'
            '        capacity_threshold=payload.get("capacity_threshold", 0.0),\n'
            "    ),\n",
        )
        violations = event_builders_subset_violations(
            registry, builders_path=builders, builders_dict="_BUILDERS"
        )
        assert violations == []


@pytest.fixture(scope="module")
def registry() -> EventSchemaRegistry:
    return load_registry()


class TestTheRealEstateSyncsToday:
    """Conformance half: the SHIPPED registry against the REAL EVENT_BUILDERS.

    This is the task brief's own binding requirement — "the sync test must
    PASS on the real estate at landing (normalization correct) — a
    failing-at-landing sync test means your registry or normalization is
    wrong, not the estate." A green run here is exactly that proof.
    """

    def test_event_builders_is_a_subset_of_the_registry(
        self, registry: EventSchemaRegistry
    ) -> None:
        violations = event_builders_subset_violations(
            registry, builders_path=EVENT_BUILDERS_PATH, builders_dict=EVENT_BUILDERS_DICT
        )
        assert violations == [], "\n".join(violations)

    def test_the_entity_death_and_superwage_crisis_divergences_are_the_only_builder_only_keys(
        self, registry: EventSchemaRegistry
    ) -> None:
        """Pins the REAL divergences this check exists to catch (found
        by direct comparison at authoring time, not invented) — a future
        R4.4.2 repair should shrink this set, not grow it silently.

        2026-08-21 worktree-sweep integration: SURPLUS_EXTRACTION grew three
        keys, LOUDLY — the imperial-rent port's BSL emit spells the endpoints
        `source`/`target` (kebab) where the frozen ExtractionEvent builder
        reads `source_id`/`target_id`, and `mechanism` is a string no BSL
        payload can carry (§2.8). Each key carries a note in the registry
        row; renaming the BSL keys was rejected at integration time as a
        non-minimal rewrite of the port's conformance pins."""
        builder_only_by_type = {
            row.event_type: sorted(k.name for k in row.keys if k.source == "builder-only")
            for row in registry.tier1
            if any(k.source == "builder-only" for k in row.keys)
        }
        assert builder_only_by_type == {
            "ENTITY_DEATH": ["cause"],
            "SUPERWAGE_CRISIS": ["payer-id", "receiver-id"],
            "SURPLUS_EXTRACTION": ["mechanism", "source-id", "target-id"],
        }
