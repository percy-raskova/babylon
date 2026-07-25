"""Behavioral contract for the computed backlink index + facets (Task 7)."""

from babylon.tui.shell.backlinks import build_backlink_index, facets_by_type


def test_backlinks_invert_outbound_wikilinks():
    pages = {
        "county/26163": "Links to [[state/26|Michigan]].",
        "org/uaw": "Based in [[county/26163|Wayne]] and [[state/26|Michigan]].",
    }
    idx = build_backlink_index(pages)
    assert idx["state/26"] == ("county/26163", "org/uaw")
    assert idx["county/26163"] == ("org/uaw",)


def test_pages_with_no_inbound_links_are_absent_not_empty():
    idx = build_backlink_index({"a": "no links here"})
    assert "a" not in idx


def test_facets_group_slugs_by_type_prefix():
    pages = {"county/26163": "", "county/26099": "", "org/uaw": ""}
    facets = facets_by_type(pages)
    assert facets["county"] == ("county/26099", "county/26163")
    assert facets["org"] == ("org/uaw",)
