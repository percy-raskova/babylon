"""Kind-dispatch statblock registry — the WO-45 integrator seam.

Every Lane P work order shipped a per-kind ``{statblock}`` provider (or
row builder) without touching ``app.py`` (shared-file discipline); this
module is the single place they compose. :func:`kind_dispatch_statblocks`
routes a subject id (``"<kind>/<id>"``) to its kind's provider;
:func:`fixture_statblock_providers` is the committed-fixture demo
composition the app boots with until a live session wires per-tick views
(P3), and :func:`fixture_known_entities` is the matching wikilink
known-set. A live session replaces both: providers built from per-tick
projections, and the known-set from
:func:`babylon.projection.epistemic_search.known_entity_ids`
(``reach ∪ intel`` — no global oracle).

Provider heterogeneity is deliberate, not accidental: direct providers
(state, industry) pass through unchanged; factory providers hydrate their
committed fixture once at composition time (national, organization,
institution, social_class); ``key_figure_statblocks`` is a row builder
over a kind with no live producer (honest empty rows); county, sovereign
and community have no fixture-shaped provider of their own, so
:func:`view_statblock_rows` derives rows generically from the frozen view
(same 6-decimal float form the vault renderer uses).

:func:`fixture_subject_views` (Program 24 P6) is a sibling of
:func:`fixture_statblock_providers`: same ten committed fixtures, same
loader calls, but handing back the loaded :data:`~babylon.projection.
view_models.ProjectionRecord` itself rather than its row projection —
the shape :func:`~babylon.tui.peek.peek` needs (the watchlist rail's
stat-plate renderer), which operates on a view-model, not on
already-tabulated ``StatblockRow`` pairs.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Final

from pydantic import BaseModel

from babylon.projection.fixtures.recorder import (
    load_community_fixture,
    load_county_fixture,
    load_industry_fixture,
    load_institution_fixture,
    load_key_figure_fixture,
    load_national_fixture,
    load_organization_fixture,
    load_social_class_fixture,
    load_sovereign_fixture,
    load_state_fixture,
)
from babylon.projection.industry import industry_statblocks
from babylon.projection.institution import institution_statblocks
from babylon.projection.key_figure import key_figure_statblocks
from babylon.projection.national import national_statblocks
from babylon.projection.organization import org_statblocks
from babylon.projection.social_class import social_class_statblocks
from babylon.projection.state import state_statblocks

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from babylon.projection.view_models import ProjectionRecord
    from babylon.tui.directives import StatblockProvider, StatblockRow

#: The committed projection fixtures (one per Lane P kind), keyed by the
#: full subject id each provider matches on.
_FIXTURE_DIR: Final = Path("tests/fixtures/projection")

#: Identity/provenance fields never tabulated as statblock rows — the
#: fence header already names the subject, and staleness is frontmatter.
_NON_ROW_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "kind",
        "verified_tick",
        "county_fips",
        "state_fips",
        "national_id",
        "org_id",
        "institution_id",
        "sovereign_id",
        "key_figure_id",
        "class_id",
        "community_id",
        "industry_id",
    }
)


def view_statblock_rows(view: BaseModel) -> list[StatblockRow]:
    """Derive statblock rows generically from any frozen projection view.

    Walks declared fields in declaration order (deterministic); ``None``
    is honest absence and contributes no row; floats format to six decimal
    places (the vault renderer's stable textual form); nested models
    flatten to dotted rows; sequences join comma-separated.

    :param view: any projection view model.
    :returns: the derived rows (possibly empty).
    """
    rows: list[StatblockRow] = []
    for name in type(view).model_fields:
        if name in _NON_ROW_FIELDS:
            continue
        value = getattr(view, name)
        if value is None:
            continue
        if isinstance(value, BaseModel):
            for sub_name in type(value).model_fields:
                sub_value = getattr(value, sub_name)
                if sub_value is None:
                    continue
                rows.append((f"{name}.{sub_name}", _format_scalar(sub_value)))
        elif isinstance(value, (tuple, list)):
            rows.append((name, ", ".join(str(item) for item in value)))
        else:
            rows.append((name, _format_scalar(value)))
    return rows


def _format_scalar(value: object) -> str:
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value)


def _single_subject_provider(subject: str, rows: Sequence[StatblockRow]) -> StatblockProvider:
    """A provider answering exactly one subject with fixed rows."""

    def provider(candidate: str) -> Sequence[StatblockRow] | None:
        return list(rows) if candidate == subject else None

    return provider


def kind_dispatch_statblocks(providers: Mapping[str, StatblockProvider]) -> StatblockProvider:
    """Compose per-kind providers into one subject-routed provider.

    :param providers: kind (the segment before the first ``/``) → that
        kind's provider; each provider receives the FULL subject id (every
        Lane P provider matches on ``"<kind>/<id>"``, not the bare id).
    :returns: a provider returning ``None`` (honest absence) for an
        unknown kind, a subject with no ``/``, or a known kind whose
        provider does not recognize the id.
    """

    def provider(subject: str) -> Sequence[StatblockRow] | None:
        kind, separator, _ = subject.partition("/")
        if not separator:
            return None
        kind_provider = providers.get(kind)
        if kind_provider is None:
            return None
        return kind_provider(subject)

    return provider


def fixture_statblock_providers(
    fixture_dir: Path = _FIXTURE_DIR,
) -> dict[str, StatblockProvider]:
    """The committed-fixture demo composition, one provider per Lane P kind.

    :param fixture_dir: where the committed projection fixtures live.
    :returns: kind → provider over that kind's committed fixture.
    """
    county = load_county_fixture(fixture_dir / "county_26163.json")
    sovereign = load_sovereign_fixture(fixture_dir / "sovereign_SOV_USA_FED.json")
    community = load_community_fixture(fixture_dir / "community_settler.json")
    key_figure = load_key_figure_fixture(fixture_dir / "key_figure_kf-001.json")
    return {
        "county": _single_subject_provider("county/26163", view_statblock_rows(county)),
        "state": state_statblocks,
        "national": national_statblocks(
            {"national/USA": load_national_fixture(fixture_dir / "national_USA.json")}
        ),
        "organization": org_statblocks(
            load_organization_fixture(fixture_dir / "organization_org_rwp.json")
        ),
        "institution": institution_statblocks(
            {"institution/doj": load_institution_fixture(fixture_dir / "institution_doj.json")}
        ),
        "sovereign": _single_subject_provider(
            "sovereign/SOV_USA_FED", view_statblock_rows(sovereign)
        ),
        "key_figure": _single_subject_provider(
            "key_figure/kf-001", key_figure_statblocks(key_figure)
        ),
        "social_class": social_class_statblocks(
            load_social_class_fixture(fixture_dir / "social_class_C004.json")
        ),
        "community": _single_subject_provider("community/settler", view_statblock_rows(community)),
        "industry": industry_statblocks,
    }


def fixture_subject_views(fixture_dir: Path = _FIXTURE_DIR) -> dict[str, ProjectionRecord]:
    """The committed-fixture view-models, keyed by subject id (Program 24 P6).

    Sibling of :func:`fixture_statblock_providers`: loads the SAME ten
    committed fixture files with the SAME loader calls, but hands back each
    loaded :data:`~babylon.projection.view_models.ProjectionRecord` itself
    rather than converting it to statblock rows — the shape
    :func:`~babylon.tui.peek.peek` needs (the watchlist rail's pinned
    stat-plate rows, Program 24 P6). No new fixture data, no duplicated
    JSON; only what each caller does with the loaded object differs.

    :param fixture_dir: where the committed projection fixtures live.
    :returns: subject id -> its loaded view-model, one entry per fixture
        kind (matching :func:`fixture_known_entities`'s ten ids exactly).
    """
    return {
        "county/26163": load_county_fixture(fixture_dir / "county_26163.json"),
        "state/26": load_state_fixture(fixture_dir / "state_26.json"),
        "national/USA": load_national_fixture(fixture_dir / "national_USA.json"),
        "organization/org_rwp": load_organization_fixture(
            fixture_dir / "organization_org_rwp.json"
        ),
        "institution/doj": load_institution_fixture(fixture_dir / "institution_doj.json"),
        "sovereign/SOV_USA_FED": load_sovereign_fixture(fixture_dir / "sovereign_SOV_USA_FED.json"),
        "key_figure/kf-001": load_key_figure_fixture(fixture_dir / "key_figure_kf-001.json"),
        "social_class/C004": load_social_class_fixture(fixture_dir / "social_class_C004.json"),
        "community/settler": load_community_fixture(fixture_dir / "community_settler.json"),
        "industry/ind_31-33": load_industry_fixture(fixture_dir / "industry_ind_31-33.json"),
    }


def fixture_known_entities() -> frozenset[str]:
    """The demo wikilink known-set: every committed fixture's subject id.

    A live session replaces this with
    :func:`~babylon.projection.epistemic_search.known_entity_ids` —
    ``reach ∪ intel``, no global oracle.

    :returns: the ten fixture subject ids.
    """
    return frozenset(
        {
            "county/26163",
            "state/26",
            "national/USA",
            "organization/org_rwp",
            "institution/doj",
            "sovereign/SOV_USA_FED",
            "key_figure/kf-001",
            "social_class/C004",
            "community/settler",
            "industry/ind_31-33",
        }
    )


__all__ = [
    "fixture_known_entities",
    "fixture_statblock_providers",
    "fixture_subject_views",
    "kind_dispatch_statblocks",
    "view_statblock_rows",
]
