"""Unit + freshness tests for the event-schema registry (theme 7, C-1 rescope).

R4.1.1 (RED) + R4.1.2 (GREEN) of the BSL refactor program's Phase 4: the
registry's per-tier membership must match a FRESH measurement taken at test
time — never a stale hardcoded count — and every Tier 1 row must cite a real
``file:line`` a live re-scan of ``content/rules/*.bsl`` actually confirms.
This is the same "documents-agree, re-derive from source, never trust a
snapshot" discipline ``tests/unit/reference/test_bsl_grammar_sync.py`` runs
for the BSL grammar appendix, applied to the event-schema registry instead.

Scanner method note (the plan's own grep-undercount warning): the BSL side
uses a REAL parse (:mod:`babylon.sentinels.event_schema_registry.bsl_emit_scan`
tokenizes and parses ``.bsl`` source into an S-expression tree and finds
``emit`` forms by tree shape), not a line-oriented pattern — the class of
undercount the plan names (``solidarity.bsl``'s multi-line
``(emit\\n  EventType/…`` forms) is exercised directly by
``TestBslEmitScanner``. The Python side uses :mod:`ast`
(``eventtype_dict_value_get_string_keys`` in ``babylon.sentinels._ast``) —
also a real parse, never a regex over source text.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from babylon.models.enums.events import EventType
from babylon.sentinels._ast import eventtype_dict_value_get_string_keys
from babylon.sentinels.base import SentinelCheckError
from babylon.sentinels.event_schema_registry.bsl_emit_scan import (
    EmitSite,
    scan_directory,
    scan_file,
)
from babylon.sentinels.event_schema_registry.registry import (
    REGISTRY_PATH,
    REPO_ROOT,
    EventSchemaRegistry,
    load_registry,
    normalize_key,
)
from babylon.sentinels.fallback_coverage.registry import (
    BUS_BOUNDARY_LEDGER,
    EVENT_BUILDERS_DICT,
    EVENT_BUILDERS_PATH,
)

RULES_DIR = REPO_ROOT / "rust" / "crates" / "babylon-tick" / "content" / "rules"


def _kebab_names(keys: tuple) -> frozenset[str]:
    return frozenset(k.name for k in keys)


def _bsl_only_names(keys: tuple) -> frozenset[str]:
    return frozenset(k.name for k in keys if k.source == "bsl")


def _builder_only_names(keys: tuple) -> frozenset[str]:
    return frozenset(k.name for k in keys if k.source == "builder-only")


# =============================================================================
# The scanner itself: a real S-expression parse, not a line-oriented pattern.
# =============================================================================


class TestBslEmitScanner:
    """Pins the scanner's actual claim: tree-shape, not text-pattern, matching."""

    def test_single_line_emit_is_found(self, tmp_path: Path) -> None:
        f = tmp_path / "single.bsl"
        f.write_text("(rule r (effects (emit EventType/FOO (a 1) (b 2))))\n")
        sites = scan_file(f, tmp_path)
        assert len(sites) == 1
        assert sites[0].event_type == "FOO"
        assert sites[0].keys == ("a", "b")

    def test_multiline_emit_is_found_the_plan_own_undercount_case(self, tmp_path: Path) -> None:
        """The exact shape the plan warns a naive ``\\(emit `` grep misses:
        the operand on its own line, not on the ``(emit`` line."""
        f = tmp_path / "multi.bsl"
        f.write_text("(rule r (effects\n  (emit\n    EventType/BAR\n    (x 1)\n    (y 2))))\n")
        sites = scan_file(f, tmp_path)
        assert len(sites) == 1
        assert sites[0].event_type == "BAR"
        assert sites[0].keys == ("x", "y")

    def test_parens_inside_a_doc_string_do_not_corrupt_depth_tracking(self, tmp_path: Path) -> None:
        """A ``:material-basis`` string containing literal ``(``/``)`` — as
        the real estate's own doc strings routinely do — must not be
        mistaken for structural parens."""
        f = tmp_path / "doc.bsl"
        f.write_text(
            "(rule r\n"
            '  :material-basis "the frozen (if a b) form, transcribed"\n'
            "  (effects (emit EventType/BAZ (k 1))))\n"
        )
        sites = scan_file(f, tmp_path)
        assert len(sites) == 1
        assert sites[0].event_type == "BAZ"
        assert sites[0].keys == ("k",)

    def test_a_comment_containing_a_paren_is_dropped_not_parsed(self, tmp_path: Path) -> None:
        f = tmp_path / "comment.bsl"
        f.write_text(
            "; a stray ) in a comment should never be treated as structure\n"
            "(rule r (effects (emit EventType/QUX (k 1))))\n"
        )
        sites = scan_file(f, tmp_path)
        assert len(sites) == 1
        assert sites[0].event_type == "QUX"

    def test_two_emit_sites_for_the_same_type_both_captured(self, tmp_path: Path) -> None:
        f = tmp_path / "branches.bsl"
        f.write_text(
            "(rule r (effects\n"
            "  (guard c1 (emit EventType/TWO_SHAPE (a 1) (b 2)))\n"
            "  (guard c2 (emit EventType/TWO_SHAPE (a 1)))))\n"
        )
        sites = scan_file(f, tmp_path)
        assert len(sites) == 2
        assert {s.keys for s in sites} == {("a", "b"), ("a",)}

    def test_line_numbers_point_at_the_open_paren(self, tmp_path: Path) -> None:
        f = tmp_path / "lines.bsl"
        f.write_text("(rule r\n  (effects\n    (emit EventType/LINE (k 1))))\n")
        sites = scan_file(f, tmp_path)
        assert sites[0].line == 3

    def test_unbalanced_parens_raise_loudly(self, tmp_path: Path) -> None:
        f = tmp_path / "broken.bsl"
        f.write_text("(rule r (effects (emit EventType/X (k 1))\n")
        with pytest.raises(SentinelCheckError, match="unbalanced"):
            scan_file(f, tmp_path)

    def test_an_unterminated_string_raises_loudly_not_masks_swallowed_emits(
        self, tmp_path: Path
    ) -> None:
        f = tmp_path / "unterminated.bsl"
        f.write_text(
            "(rule r (effects (emit EventType/A (k 1))))\n"
            '"an unterminated string swallows the rest of the file\n'
            "(rule s (effects (emit EventType/MASKED (k 1))))\n"
        )
        with pytest.raises(SentinelCheckError, match="unterminated string"):
            scan_file(f, tmp_path)

    def test_missing_directory_raises_loudly_not_empty(self, tmp_path: Path) -> None:
        with pytest.raises(SentinelCheckError, match="no \\*\\.bsl files"):
            scan_directory(tmp_path / "does-not-exist", tmp_path)

    def test_repo_relative_path_is_posix_and_stable(self, tmp_path: Path) -> None:
        sub = tmp_path / "content" / "rules"
        sub.mkdir(parents=True)
        f = sub / "one.bsl"
        f.write_text("(rule r (effects (emit EventType/X (k 1))))\n")
        sites = scan_file(f, tmp_path)
        assert sites[0].path == "content/rules/one.bsl"


# =============================================================================
# The loaded registry against the real, current estate.
# =============================================================================


@pytest.fixture(scope="module")
def registry() -> EventSchemaRegistry:
    return load_registry()


@pytest.fixture(scope="module")
def fresh_bsl_sites() -> tuple[EmitSite, ...]:
    return scan_directory(RULES_DIR, REPO_ROOT)


@pytest.fixture(scope="module")
def fresh_builder_fields() -> dict[str, tuple[str, ...]]:
    return eventtype_dict_value_get_string_keys(EVENT_BUILDERS_PATH, EVENT_BUILDERS_DICT)


@pytest.fixture(scope="module")
def fresh_event_type_members() -> frozenset[str]:
    return frozenset(member.name for member in EventType)


class TestRegistryFileItself:
    def test_the_registry_file_exists(self) -> None:
        assert REGISTRY_PATH.exists(), f"{REGISTRY_PATH} is missing"

    def test_loads_without_error(self, registry: EventSchemaRegistry) -> None:
        assert registry.schema_version == 2

    @pytest.mark.parametrize("replacement", ("1", "3", '"2"', "true"))
    def test_unsupported_schema_version_fails_loudly(
        self, tmp_path: Path, replacement: str
    ) -> None:
        registry_path = tmp_path / "event-schema-registry.toml"
        source = REGISTRY_PATH.read_text(encoding="utf-8")
        registry_path.write_text(
            source.replace("schema_version = 2", f"schema_version = {replacement}", 1),
            encoding="utf-8",
        )

        with pytest.raises(SentinelCheckError, match="unsupported schema_version"):
            load_registry(registry_path)

    def test_declared_total_matches_a_fresh_events_py_count(
        self, registry: EventSchemaRegistry, fresh_event_type_members: frozenset[str]
    ) -> None:
        """The TOML header's own ``python_event_type_total`` is itself a
        claim this proves fresh, not a number to trust because it is
        written down — CLAUDE.md's "100" and the plan's own AST-verified
        correction of the survey's stale "98" both hinge on this staying
        true."""
        assert registry.python_event_type_total == len(fresh_event_type_members)

    def test_bsl_emit_measurements_match_a_fresh_scan(
        self, registry: EventSchemaRegistry, fresh_bsl_sites: tuple[EmitSite, ...]
    ) -> None:
        """The registry records the live BSL site's total and name total."""
        assert registry.bsl_emit_site_total == len(fresh_bsl_sites)
        assert registry.bsl_emit_name_total == len({site.event_type for site in fresh_bsl_sites})


class TestTier1MatchesAFreshBslScan:
    """R4.1.1's core claim: Tier 1 membership and every row's key set must
    equal what a live re-scan of content/rules/*.bsl finds RIGHT NOW — not
    what was true when the TOML was authored. A new port adding an emit site
    reds this test until the registry is updated (the same ratchet
    ``sentinels/fallback_coverage`` runs for the bus-boundary surface)."""

    def test_tier1_event_types_equal_the_fresh_distinct_emit_names_minus_unminted(
        self,
        registry: EventSchemaRegistry,
        fresh_bsl_sites: tuple[EmitSite, ...],
        fresh_event_type_members: frozenset[str],
    ) -> None:
        fresh_names = {s.event_type for s in fresh_bsl_sites}
        # BSL-only names (no Python EventType counterpart) are NOT tier1 —
        # they belong in unminted_bsl_only instead (see that test class).
        fresh_real_names = fresh_names & fresh_event_type_members
        registry_names = {row.event_type for row in registry.tier1}
        assert registry_names == fresh_real_names

    def test_no_fresh_bsl_only_name_is_missing_from_unminted(
        self,
        registry: EventSchemaRegistry,
        fresh_bsl_sites: tuple[EmitSite, ...],
        fresh_event_type_members: frozenset[str],
    ) -> None:
        fresh_names = {s.event_type for s in fresh_bsl_sites}
        bsl_only = fresh_names - fresh_event_type_members
        unminted_names = {row.name for row in registry.unminted_bsl_only}
        assert bsl_only == unminted_names, (
            f"BSL emits {sorted(bsl_only)} with no Python EventType counterpart "
            f"— unminted_bsl_only declares {sorted(unminted_names)}"
        )

    def test_every_tier1_row_key_set_matches_the_union_of_its_fresh_sites(
        self,
        registry: EventSchemaRegistry,
        fresh_bsl_sites: tuple[EmitSite, ...],
    ) -> None:
        by_type: dict[str, list[EmitSite]] = {}
        for site in fresh_bsl_sites:
            by_type.setdefault(site.event_type, []).append(site)

        for row in registry.tier1:
            sites = by_type.get(row.event_type, [])
            assert sites, f"registry tier1 row {row.event_type!r} has no fresh emit site at all"
            key_sets = [frozenset(s.keys) for s in sites]
            union = frozenset().union(*key_sets)
            always_present = frozenset.intersection(*key_sets)

            bsl_keys = _bsl_only_names(row.keys)
            assert bsl_keys == union, (
                f"{row.event_type}: registry bsl-sourced keys {sorted(bsl_keys)} != "
                f"fresh union {sorted(union)}"
            )
            for key in row.keys:
                if key.source != "bsl":
                    continue
                is_always_present = key.name in always_present
                assert key.required == is_always_present, (
                    f"{row.event_type}.{key.name}: registry says required="
                    f"{key.required}, but it is "
                    f"{'present at every' if is_always_present else 'absent from at least one'} "
                    "fresh site"
                )

    def test_builder_only_keys_are_real_builder_reads_not_bsl_provided(
        self,
        registry: EventSchemaRegistry,
        fresh_bsl_sites: tuple[EmitSite, ...],
        fresh_builder_fields: dict[str, tuple[str, ...]],
    ) -> None:
        by_type: dict[str, list[EmitSite]] = {}
        for site in fresh_bsl_sites:
            by_type.setdefault(site.event_type, []).append(site)

        for row in registry.tier1:
            builder_only = _builder_only_names(row.keys)
            if not builder_only:
                continue
            observed_bsl = frozenset().union(
                *(frozenset(s.keys) for s in by_type.get(row.event_type, []))
            )
            normalized_bsl = {normalize_key(k) for k in observed_bsl}
            builder_fields = fresh_builder_fields.get(row.event_type, ())
            normalized_builder_fields = {normalize_key(f) for f in builder_fields}
            for key in builder_only:
                assert normalize_key(key) not in normalized_bsl, (
                    f"{row.event_type}.{key} is flagged builder-only but a fresh "
                    "BSL site now provides it — promote it to source=bsl"
                )
                assert normalize_key(key) in normalized_builder_fields, (
                    f"{row.event_type}.{key} is flagged builder-only but no fresh "
                    "EVENT_BUILDERS read backs it any more — remove the row"
                )


class TestTier1CitationsAreReal:
    """Every Tier 1 row's citation must point at a real, current emit site —
    not a stale line number left behind by a later edit."""

    @classmethod
    @pytest.fixture(scope="class")
    def fresh_sites_by_location(cls) -> dict[tuple[str, int], EmitSite]:
        sites = scan_directory(RULES_DIR, REPO_ROOT)
        return {(s.path, s.line): s for s in sites}

    def test_every_tier1_row_has_at_least_one_citation(self, registry: EventSchemaRegistry) -> None:
        for row in registry.tier1:
            assert row.citations, f"{row.event_type} has no citations"

    def test_every_citation_resolves_to_a_real_emit_site_of_the_right_type(
        self,
        registry: EventSchemaRegistry,
        fresh_sites_by_location: dict[tuple[str, int], EmitSite],
    ) -> None:
        for row in registry.tier1:
            for citation in row.citations:
                path_str, _, line_str = citation.rpartition(":")
                location = (path_str, int(line_str))
                assert location in fresh_sites_by_location, (
                    f"{row.event_type}'s citation {citation!r} does not resolve "
                    "to any fresh emit site"
                )
                assert fresh_sites_by_location[location].event_type == row.event_type, (
                    f"{row.event_type}'s citation {citation!r} resolves to a "
                    f"DIFFERENT EventType at that line"
                )


class TestUnmintedBslOnlyNames:
    """Real BSL evidence deliberately absent from Python's EventType universe."""

    def test_no_unminted_name_is_a_real_event_type_member(
        self, registry: EventSchemaRegistry, fresh_event_type_members: frozenset[str]
    ) -> None:
        for row in registry.unminted_bsl_only:
            assert row.name not in fresh_event_type_members, (
                f"{row.name} is flagged unminted_bsl_only but IS now a real "
                "EventType member — move it to tier1/tier2/tier3, whichever fits"
            )

    def test_no_unminted_name_double_counted_in_a_tier(self, registry: EventSchemaRegistry) -> None:
        tiered = (
            {r.event_type for r in registry.tier1}
            | {r.event_type for r in registry.tier2}
            | {r.event_type for r in registry.tier3}
        )
        for row in registry.unminted_bsl_only:
            assert row.name not in tiered

    def test_only_the_governed_measurement_event_remains_unminted(
        self,
        registry: EventSchemaRegistry,
        fresh_bsl_sites: tuple[EmitSite, ...],
        fresh_event_type_members: frozenset[str],
    ) -> None:
        """The live scan and registry retain the one governed unminted measure."""
        expected = {"SUBSISTENCE_CLEARANCE_MEASURED"}
        emitted_unminted = {
            site.event_type
            for site in fresh_bsl_sites
            if site.event_type not in fresh_event_type_members
        }
        registry_unminted = {row.name for row in registry.unminted_bsl_only}
        assert emitted_unminted == expected
        assert registry_unminted == expected


class TestTier2MatchesFreshEventBuilders:
    """Tier 2 = builder-covered EventTypes minus Tier 1, verbatim-transcribed."""

    def test_tier2_event_types_equal_fresh_builder_coverage_minus_tier1(
        self,
        registry: EventSchemaRegistry,
        fresh_builder_fields: dict[str, tuple[str, ...]],
    ) -> None:
        tier1_names = {row.event_type for row in registry.tier1}
        fresh_tier2_expected = set(fresh_builder_fields.keys()) - tier1_names
        registry_tier2_names = {row.event_type for row in registry.tier2}
        assert registry_tier2_names == fresh_tier2_expected

    def test_every_tier2_row_key_set_matches_its_fresh_builder_fields_verbatim(
        self,
        registry: EventSchemaRegistry,
        fresh_builder_fields: dict[str, tuple[str, ...]],
    ) -> None:
        for row in registry.tier2:
            fresh_fields = frozenset(fresh_builder_fields.get(row.event_type, ()))
            registry_fields = _kebab_names(row.keys)
            assert registry_fields == fresh_fields, (
                f"{row.event_type}: registry keys {sorted(registry_fields)} != "
                f"fresh EVENT_BUILDERS fields {sorted(fresh_fields)}"
            )

    def test_every_tier2_row_discloses_its_own_incompleteness(
        self, registry: EventSchemaRegistry
    ) -> None:
        for row in registry.tier2:
            assert row.note, f"{row.event_type} tier2 row has no note"


class TestTier3IsTheArithmeticRemainder:
    def test_tier3_equals_all_members_minus_tier1_minus_builder_covered(
        self,
        registry: EventSchemaRegistry,
        fresh_event_type_members: frozenset[str],
        fresh_builder_fields: dict[str, tuple[str, ...]],
    ) -> None:
        tier1_names = {row.event_type for row in registry.tier1}
        builder_covered = set(fresh_builder_fields.keys())
        expected_tier3 = fresh_event_type_members - tier1_names - builder_covered
        registry_tier3_names = {row.event_type for row in registry.tier3}
        assert registry_tier3_names == expected_tier3

    def test_no_tier3_row_has_a_key_list(self, registry: EventSchemaRegistry) -> None:
        for row in registry.tier3:
            assert not hasattr(row, "keys")

    def test_tier3_matches_the_fallback_coverage_bus_boundary_ledger(
        self, registry: EventSchemaRegistry
    ) -> None:
        """Independent cross-check: ``sentinels/fallback_coverage``'s own
        BUS_BOUNDARY_LEDGER already names every EventType absent from
        EVENT_BUILDERS. Since Tier 1 ⊆ builder-covered for every landed
        content EventType today, Tier 3 (no builder, no BSL) should equal
        that ledger's member set exactly — two independently-built registries
        agreeing is real evidence neither drifted."""
        ledger_members = {row.member for row in BUS_BOUNDARY_LEDGER}
        registry_tier3_names = {row.event_type for row in registry.tier3}
        assert registry_tier3_names == ledger_members


class TestPerTierCountsSumToTheDeclaredTotal:
    def test_tier1_plus_tier2_plus_tier3_equals_python_event_type_total(
        self, registry: EventSchemaRegistry
    ) -> None:
        assert (
            len(registry.tier1) + len(registry.tier2) + len(registry.tier3)
            == registry.python_event_type_total
        )

    def test_no_event_type_appears_in_more_than_one_tier(
        self, registry: EventSchemaRegistry
    ) -> None:
        tier1 = {row.event_type for row in registry.tier1}
        tier2 = {row.event_type for row in registry.tier2}
        tier3 = {row.event_type for row in registry.tier3}
        assert not (tier1 & tier2)
        assert not (tier1 & tier3)
        assert not (tier2 & tier3)
