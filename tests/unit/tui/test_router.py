"""Unit tests for babylon.tui.router: babylon:// URI parsing."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from babylon.tui.router import (
    BabylonTarget,
    InvalidBabylonUri,
    format_babylon_uri,
    parse_babylon_uri,
)


class TestParseBabylonUri:
    def test_it_parses_an_explicit_kind_href(self) -> None:
        target = parse_babylon_uri("babylon://county/26163")
        assert target == BabylonTarget(kind="county", entity_id="26163")
        assert target.redlink is False

    def test_it_parses_a_fully_bare_href_with_no_slash(self) -> None:
        target = parse_babylon_uri("babylon://uaw-600")
        assert target == BabylonTarget(kind="wikilink", entity_id="uaw-600")
        assert target.redlink is False

    def test_it_parses_a_redlink_href(self) -> None:
        target = parse_babylon_uri("babylon://redlink/org/uaw-9999")
        assert target.kind == "redlink"
        assert target.entity_id == "org/uaw-9999"
        assert target.redlink is True

    def test_it_parses_a_redlink_href_with_a_single_token_target(self) -> None:
        target = parse_babylon_uri("babylon://redlink/uaw-9999")
        assert target == BabylonTarget(kind="redlink", entity_id="uaw-9999", redlink=True)

    def test_it_rejects_a_non_babylon_scheme(self) -> None:
        with pytest.raises(InvalidBabylonUri, match="not a babylon"):
            parse_babylon_uri("http://county/26163")

    def test_it_rejects_a_uri_with_no_host_segment(self) -> None:
        with pytest.raises(InvalidBabylonUri, match="missing host"):
            parse_babylon_uri("babylon:///26163")

    def test_it_rejects_a_malformed_id_segment(self) -> None:
        with pytest.raises(InvalidBabylonUri, match="malformed"):
            parse_babylon_uri("babylon://county/26 163")

    def test_it_rejects_a_malformed_kind_segment(self) -> None:
        with pytest.raises(InvalidBabylonUri, match="malformed"):
            parse_babylon_uri("babylon://coun ty/26163")

    def test_it_rejects_an_empty_string(self) -> None:
        with pytest.raises(InvalidBabylonUri):
            parse_babylon_uri("")


class TestFormatBabylonUri:
    def test_it_round_trips_an_explicit_kind_target(self) -> None:
        target = parse_babylon_uri("babylon://county/26163")
        assert parse_babylon_uri(format_babylon_uri(target)) == target

    def test_it_round_trips_a_redlink_target(self) -> None:
        target = parse_babylon_uri("babylon://redlink/org/uaw-9999")
        assert parse_babylon_uri(format_babylon_uri(target)) == target

    def test_it_round_trips_a_bare_wikilink_target(self) -> None:
        target = parse_babylon_uri("babylon://uaw-600")
        assert parse_babylon_uri(format_babylon_uri(target)) == target


class TestBabylonTarget:
    def test_it_is_frozen(self) -> None:
        target = BabylonTarget(kind="county", entity_id="26163")
        with pytest.raises(ValidationError):
            target.kind = "org"  # type: ignore[misc]

    def test_it_rejects_an_empty_kind(self) -> None:
        with pytest.raises(ValidationError):
            BabylonTarget(kind="", entity_id="26163")

    def test_it_rejects_an_empty_entity_id(self) -> None:
        with pytest.raises(ValidationError):
            BabylonTarget(kind="county", entity_id="")
