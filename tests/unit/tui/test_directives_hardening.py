"""WO-29 hardening contracts for ``babylon.tui.directives.BabylonFence``.

Contract-tests and hardens the three keel directives — ``_directive_statblock``,
``_directive_absence``, ``_directive_narrative`` — against **real
view-model-derived** inputs: rows produced by
:mod:`babylon.projection.vault.render`'s ``_statblock_rows``/``_absent_fields``
walking an actual :class:`~babylon.projection.view_models.CountyView`, not
hand-typed strings. Both the baked-page path (numbers in the fence body) and
the live path (:data:`~babylon.tui.directives.StatblockProvider`) are covered
for the statblock directive; the absence directive is exercised against the
*exact* production shape ``county.md.j2`` bakes (empty body, ``"{field} —
{remedy}"`` in the fence arg); the narrative directive is exercised against
the design canon's literal cache-key byline convention
(``ai/_inbox/tui/20260719archiveinterfacedesign.md`` line 100:
``{narrative} cached:{{ tick }}:{{ model_pin }}``).

**Scope note (honest, not a claim of more than was tested):** the WO brief
asks for hardening "across all Wave-1 kinds." At this integration point only
:class:`CountyView` (Program 24 P1 keel) is a landed Wave-1 view-model — the
Lane P per-kind view-models (state/national/organization/... — WO-16..24)
had not merged when this WO ran. Both hardened directives dispatch on plain
``str`` (a subject id, or already-flattened ``key: value`` lines) rather than
on any typed view-model, so kind-genericity is structural, not per-kind
code — :class:`TestStatblockAcrossKinds` demonstrates this by running the
*same* directive machinery over CountyView-derived rows and a second,
differently-shaped row set standing in for a not-yet-landed kind. No Lane P
view-model is invented or referenced by name to produce this second fixture.

New directive methods are explicitly out of scope here (Lane T owns
``_directive_paoh``'s siblings) — every test below exercises
``_directive_statblock``, ``_directive_absence``, or ``_directive_narrative``
only.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import pytest
from textual.app import App, ComposeResult
from textual.content import Content
from textual.widgets import Label

from babylon.projection.vault.render import _absent_fields, _statblock_rows
from babylon.projection.view_models import CountyView, hydrate_county
from babylon.tui.directives import BabylonFence, StatblockProvider, StatblockRow

WAYNE_FIPS = "26163"
WAYNE_TICK = 847


def _wayne_view(**overrides: object) -> CountyView:
    """A fully-populated ``CountyView`` shaped like Wayne County @ tick 847.

    The canonical fixture identity used across the Archive program (WO-25's
    peek-plate fixture, ``test_county.py``'s tick-847 dossier) — reused here
    rather than re-invented, per project convention.

    :param overrides: field overrides layered onto the base payload (e.g. to
        inject a deliberately bracket-laden string value or drop a field to
        ``None`` for the absence path).
    :returns: the validated, frozen view.
    """
    payload: dict[str, object] = {
        "kind": "county",
        "county_fips": WAYNE_FIPS,
        "verified_tick": WAYNE_TICK,
        "population": 1_749_343,
        "class_composition": {
            "bourgeoisie": 0.02,
            "petit_bourgeoisie": 0.08,
            "labor_aristocracy": 0.30,
            "proletariat": 0.55,
            "lumpenproletariat": 0.05,
        },
        "median_wage": 18.5,
        "imperial_rent_phi": 4.2,
        "consciousness": {"revolutionary": 0.3, "liberal": 0.6, "fascist": 0.1},
        "legitimacy": 0.42,
        "p_acquiescence": 0.7,
        "p_revolution": 0.25,
        "bifurcation_score": -0.35,
        "sovereign_id": "SOV_USA",
    }
    payload.update(overrides)
    return hydrate_county(payload)


def _wayne_view_with_absences() -> CountyView:
    """The same identity with only the always-attributed trio present.

    Matches ``tests/unit/projection/vault/conftest.py``'s
    ``wayne_county_view_with_absences`` shape: every optional field beyond
    population/median_wage/imperial_rent_phi hydrates honestly to ``None``.
    """
    return hydrate_county(
        {
            "kind": "county",
            "county_fips": WAYNE_FIPS,
            "verified_tick": WAYNE_TICK,
            "population": 1_749_343,
            "median_wage": 18.5,
            "imperial_rent_phi": 4.2,
        }
    )


def _baked_statblock_body(rows: Sequence[StatblockRow]) -> str:
    """Render rows the way ``county.md.j2`` actually bakes them: one
    ``label: value`` line per row (the template's ``{% for label, value in
    statblock_rows %}{{ label }}: {{ value }}`` loop)."""
    return "\n".join(f"{label}: {value}" for label, value in rows)


def _provider_over(rows_by_subject: Mapping[str, Sequence[StatblockRow]]) -> StatblockProvider:
    """A live ``StatblockProvider`` closed over a fixed subject->rows map.

    :param rows_by_subject: subject id -> its statblock rows.
    :returns: a provider returning ``None`` for any subject not in the map
        (the honest "no projection for this subject" contract).
    """

    def provider(subject: str) -> Sequence[StatblockRow] | None:
        return rows_by_subject.get(subject)

    return provider


class _FenceHost(App[None]):
    """Bare app hosting an arbitrary markdown fragment with a live provider.

    Mirrors ``tests/unit/tui/test_directives.py``'s ``_FenceHost`` but takes
    an explicit statblock provider so baked and live paths can be exercised
    against the *same* real row data in one test. Never touches
    ``babylon.tui.app`` — Lane W discipline (app.py is Wave-2 WO-45 only).
    """

    def __init__(self, markdown: str, *, statblocks: StatblockProvider) -> None:
        super().__init__()
        self._markdown_text = markdown
        self._statblocks = statblocks

    def compose(self) -> ComposeResult:
        # Constructing BabylonMarkdown directly (not via ArchiveApp/app.py)
        # keeps this fixture inside Lane W's file-touch boundary.
        from babylon.tui.app import BabylonMarkdown

        yield BabylonMarkdown(self._markdown_text, open_links=False, statblocks=self._statblocks)


def _plain_text(label: Label) -> str:
    """The label's fully-rendered plain text, exactly as it appears on screen.

    ``label.content`` is "the original content set in the constructor" (a
    Textual ``Static`` API fact, not the parsed result) — checking a
    substring against it would pass even for an *unescaped*,
    content-mangling bug, since escaping only inserts a backslash before the
    literal characters. Running it back through the real ``Content`` parser
    (the same one ``Label(markup=True)`` uses internally, per
    ``textual.visual.visualize``) is the only oracle that actually proves a
    bracket span survives rendering rather than being silently swallowed as
    an unrecognized style tag.

    :param label: a mounted ``Label`` from a ``BabylonFence`` directive.
    :returns: the rendered plain text.
    """
    if label._render_markup:
        return Content.from_markup(label.content).plain
    return str(label.content)


class TestStatblockBakedVsLive:
    """Baked (``key: value`` body) and live (``StatblockProvider``) parity."""

    @pytest.mark.asyncio
    async def test_baked_and_live_paths_render_the_same_real_rows(self) -> None:
        """The same CountyView-derived rows render identically either way."""
        view = _wayne_view()
        rows = _statblock_rows(view)
        subject = f"county/{WAYNE_FIPS}"

        baked_page = f"```{{statblock}} {subject}\n{_baked_statblock_body(rows)}\n```\n"
        baked_app = _FenceHost(baked_page, statblocks=_provider_over({}))
        async with baked_app.run_test():
            baked_label = baked_app.query_one(BabylonFence).query_one(Label)
            baked_text = _plain_text(baked_label)

        live_page = f"```{{statblock}} {subject}\n```\n"
        live_app = _FenceHost(live_page, statblocks=_provider_over({subject: rows}))
        async with live_app.run_test():
            live_label = live_app.query_one(BabylonFence).query_one(Label)
            live_text = _plain_text(live_label)

        assert baked_text == live_text
        for label, value in rows:
            assert f"{label}" in baked_text
            assert f"{value}" in baked_text

    @pytest.mark.asyncio
    async def test_live_provider_returning_none_renders_absence(self) -> None:
        """An unknown subject id — honest absence, never a fabricated row."""
        app = _FenceHost("```{statblock} org/unknown-9999\n```\n", statblocks=_provider_over({}))
        async with app.run_test():
            label = app.query_one(BabylonFence).query_one(Label)
            assert "no statblock projection for org/unknown-9999" in _plain_text(label)

    @pytest.mark.asyncio
    async def test_a_baked_body_with_an_interior_blank_line_is_refused(self) -> None:
        """A blank line mid-body has no colon — malformed, refuse loudly."""
        body = "population: 1749343\n\nmedian_wage: 18.500000"
        app = _FenceHost(
            f"```{{statblock}} county/{WAYNE_FIPS}\n{body}\n```\n",
            statblocks=_provider_over({}),
        )
        async with app.run_test():
            label = app.query_one(BabylonFence).query_one(Label)
            text = _plain_text(label)
            assert "MALFORMED STATBLOCK BODY" in text

    @pytest.mark.asyncio
    async def test_a_baked_line_missing_a_colon_is_refused(self) -> None:
        """A line with no ``:`` at all is a shape violation, not a value."""
        app = _FenceHost(
            f"```{{statblock}} county/{WAYNE_FIPS}\npopulation 1749343\n```\n",
            statblocks=_provider_over({}),
        )
        async with app.run_test():
            label = app.query_one(BabylonFence).query_one(Label)
            assert "MALFORMED STATBLOCK BODY" in _plain_text(label)

    @pytest.mark.asyncio
    async def test_a_colon_inside_a_value_survives_first_colon_partition(self) -> None:
        """``partition(":")`` splits at the FIRST colon only — a value that
        itself contains a colon (e.g. a time-like string) must survive whole."""
        app = _FenceHost(
            f"```{{statblock}} county/{WAYNE_FIPS}\nnote: shift change at 14:30\n```\n",
            statblocks=_provider_over({}),
        )
        async with app.run_test():
            label = app.query_one(BabylonFence).query_one(Label)
            assert "shift change at 14:30" in _plain_text(label)

    @pytest.mark.asyncio
    async def test_an_empty_value_after_the_colon_is_not_malformed(self) -> None:
        """A key with a colon but no value is a syntactically valid (odd, but
        honest) row — not a shape violation."""
        app = _FenceHost(
            f"```{{statblock}} county/{WAYNE_FIPS}\nnickname:\n```\n",
            statblocks=_provider_over({}),
        )
        async with app.run_test():
            label = app.query_one(BabylonFence).query_one(Label)
            text = _plain_text(label)
            assert "MALFORMED" not in text
            assert "nickname" in text

    @pytest.mark.asyncio
    async def test_a_lowercase_bracket_span_in_a_real_baked_value_survives(self) -> None:
        """``sovereign_id`` is an unconstrained ``str`` — a plausible
        annotation-style value (lowercase-initiated bracket span) must not be
        silently eaten by Textual's Content markup parser."""
        view = _wayne_view(sovereign_id="SOV_USA [contested]")
        rows = _statblock_rows(view)
        body = _baked_statblock_body(rows)
        app = _FenceHost(
            f"```{{statblock}} county/{WAYNE_FIPS}\n{body}\n```\n",
            statblocks=_provider_over({}),
        )
        async with app.run_test():
            label = app.query_one(BabylonFence).query_one(Label)
            assert "SOV_USA [contested]" in _plain_text(label)

    @pytest.mark.asyncio
    async def test_a_lowercase_bracket_span_in_a_live_row_survives(self) -> None:
        """Same hazard via the live-provider path (not just the baked path)."""
        subject = "county/48999"
        rows: tuple[StatblockRow, ...] = (("status", "under review [pending]"),)
        app = _FenceHost(
            f"```{{statblock}} {subject}\n```\n",
            statblocks=_provider_over({subject: rows}),
        )
        async with app.run_test():
            label = app.query_one(BabylonFence).query_one(Label)
            assert "under review [pending]" in _plain_text(label)


class TestStatblockAcrossKinds:
    """Genericity: the directive dispatches on a subject id and rows, never
    on a specific view-model type — proven with two differently-shaped row
    sets (see module docstring's scope note)."""

    @pytest.mark.asyncio
    async def test_county_derived_rows_and_a_second_row_shape_both_dispatch(self) -> None:
        county_rows = _statblock_rows(_wayne_view())
        other_kind_rows: tuple[StatblockRow, ...] = (
            ("consciousness_tendency", "0.42"),
            ("cohesion", "0.77"),
        )
        provider = _provider_over(
            {
                f"county/{WAYNE_FIPS}": county_rows,
                "org/example": other_kind_rows,
            }
        )
        for subject, expected_row in (
            (f"county/{WAYNE_FIPS}", county_rows[0]),
            ("org/example", other_kind_rows[0]),
        ):
            app = _FenceHost(f"```{{statblock}} {subject}\n```\n", statblocks=provider)
            async with app.run_test():
                label = app.query_one(BabylonFence).query_one(Label)
                text = _plain_text(label)
                assert expected_row[0] in text
                assert expected_row[1] in text


class TestAbsenceHardening:
    """The ``{absence}`` directive against the real ``county.md.j2`` shape:
    empty fence body, ``"{field} — {remedy}"`` carried in the fence arg."""

    @pytest.mark.asyncio
    async def test_the_real_baked_production_shape_renders_the_registered_remedy(
        self,
    ) -> None:
        absences = _absent_fields(_wayne_view_with_absences())
        field, remedy = next(pair for pair in absences if pair[0] == "class_composition")
        app = _FenceHost(f"```{{absence}} {field} — {remedy}\n```\n", statblocks=_provider_over({}))
        async with app.run_test():
            label = app.query_one(BabylonFence).query_one(Label)
            text = _plain_text(label)
            assert field in text
            assert remedy in text
            assert "Census(Territory)" in text

    @pytest.mark.asyncio
    async def test_every_registered_absent_field_remedy_renders_verbatim(self) -> None:
        absences = _absent_fields(_wayne_view_with_absences())
        assert absences, "fixture must actually exercise the absence path"
        for field, remedy in absences:
            app = _FenceHost(
                f"```{{absence}} {field} — {remedy}\n```\n", statblocks=_provider_over({})
            )
            async with app.run_test():
                label = app.query_one(BabylonFence).query_one(Label)
                text = _plain_text(label)
                assert f"ABSENT — {field} — {remedy}" in text

    @pytest.mark.asyncio
    async def test_an_empty_body_and_empty_arg_yields_a_diagnostic_not_a_bare_dash(
        self,
    ) -> None:
        """A template bug (absence block with no remedy at all) must still
        say something diagnostic, never a bare, mysterious ``"ABSENT — "``."""
        app = _FenceHost("```{absence}\n```\n", statblocks=_provider_over({}))
        async with app.run_test():
            label = app.query_one(BabylonFence).query_one(Label)
            text = _plain_text(label)
            assert text.strip() != "▌ ABSENT —"
            assert "no remedy recorded" in text


class TestNarrativeHardening:
    """The ``{narrative}`` directive against the design canon's cache-key
    byline convention (``cached:{tick}:{model_pin}``) and honest absence."""

    @pytest.mark.asyncio
    async def test_a_cache_key_byline_surfaces_tick_and_model_pin(self) -> None:
        app = _FenceHost(
            "```{narrative} cached:847:local-chat\nThe picket line held.\n```\n",
            statblocks=_provider_over({}),
        )
        async with app.run_test():
            label = app.query_one(BabylonFence).query_one(Label)
            text = _plain_text(label)
            assert "The picket line held." in text
            assert "847" in text
            assert "local-chat" in text

    @pytest.mark.asyncio
    async def test_empty_body_with_a_cache_key_arg_is_an_honest_absence(self) -> None:
        """The design canon's literal template fragment
        (``{narrative} cached:{{ tick }}:{{ model_pin }}`` with an empty
        body — the shape every baked page has until WO-42 wires the async
        narrator writer) must render an honest, tick-naming absence, never a
        blank plate."""
        app = _FenceHost(
            "```{narrative} cached:847:local-chat\n```\n",
            statblocks=_provider_over({}),
        )
        async with app.run_test():
            label = app.query_one(BabylonFence).query_one(Label)
            text = _plain_text(label)
            assert "no narration cached" in text
            assert "847" in text

    @pytest.mark.asyncio
    async def test_empty_body_with_no_arg_is_still_an_honest_absence(self) -> None:
        app = _FenceHost("```{narrative}\n```\n", statblocks=_provider_over({}))
        async with app.run_test():
            label = app.query_one(BabylonFence).query_one(Label)
            assert "no narration cached" in _plain_text(label)

    @pytest.mark.parametrize(
        "bad_arg",
        ["cached:", "cached:847", "cached:notanumber:model", "cached:847:", "cached:-1:model"],
    )
    @pytest.mark.asyncio
    async def test_a_malformed_cache_key_arg_refuses_loudly(self, bad_arg: str) -> None:
        app = _FenceHost(
            f"```{{narrative}} {bad_arg}\nSome prose.\n```\n",
            statblocks=_provider_over({}),
        )
        async with app.run_test():
            label = app.query_one(BabylonFence).query_one(Label)
            text = _plain_text(label)
            assert "MALFORMED NARRATIVE CACHE KEY" in text
            assert bad_arg in text

    @pytest.mark.asyncio
    async def test_legacy_free_label_byline_matches_pre_hardening_text(self) -> None:
        """A non-cache-key arg (the existing sample page's convention) must
        keep rendering byte-identical to the pre-hardening byline, so the
        keel's committed snapshot golden doesn't drift."""
        app = _FenceHost(
            "```{narrative} the Narrator\nThe picket line held through the second shift change.\n```\n",
            statblocks=_provider_over({}),
        )
        async with app.run_test():
            label = app.query_one(BabylonFence).query_one(Label)
            assert label.content == (
                "[i $foreground]The picket line held through the second shift change.[/]\n"
                "[$text-muted]— the Narrator (the Narrator)[/]"
            )

    @pytest.mark.asyncio
    async def test_empty_arg_renders_without_dangling_empty_parens(self) -> None:
        app = _FenceHost(
            "```{narrative}\nSome prose with no byline label.\n```\n",
            statblocks=_provider_over({}),
        )
        async with app.run_test():
            label = app.query_one(BabylonFence).query_one(Label)
            text = _plain_text(label)
            assert "()" not in text
            assert "— the Narrator" in text

    @pytest.mark.asyncio
    async def test_bracket_laden_llm_prose_survives_escaping(self) -> None:
        """Real narrator prose is unconstrained free text — a plausible
        transcription-style annotation must not be silently swallowed."""
        app = _FenceHost(
            "```{narrative} cached:847:local-chat\n"
            "The picket line held, though the tape was [unclear] near the end.\n"
            "```\n",
            statblocks=_provider_over({}),
        )
        async with app.run_test():
            label = app.query_one(BabylonFence).query_one(Label)
            assert "[unclear]" in _plain_text(label)
