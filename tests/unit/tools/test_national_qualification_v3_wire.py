"""Strict cross-language wire contracts for Wayne's opt-in qualification socket."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from pydantic import ValidationError
from tools.devtools import national_windowed_qualification as wire

# Unedited production-reader and status frames emitted by the Rust client at
# e9cdc0037c4ea71b6a34410447c9ca8f5d61f8d8, task-3/qualification-v3-wire-*.jsonl.
FRAMES = Path(__file__).resolve().parents[2] / "fixtures" / "national_qualification_v3"
DIGESTS = {
    "requests": "15f002f469e1a2a18732a7302f399707647e19938a65af418905670746ece0b0",
    "responses": "d1cc08f8c4fab93b2d5e7b78e5cade0bf295a5e43cd72ee19deb7816eac0a797",
    "reviewed-accepted": "4edb5a91f6255a2bb6707a883cedd62a765dff7db1dbf725d8e624770209824c",
}


def frames(kind: str) -> list[bytes]:
    data = (FRAMES / f"qualification-v3-wire-{kind}.jsonl").read_bytes()
    assert hashlib.sha256(data).hexdigest() == DIGESTS[kind]
    return data.splitlines()


def test_rust_input_and_numbered_replies_preserve_every_json_value() -> None:
    requests = frames("requests")
    responses = frames("responses")
    assert len(requests) == len(responses) == 6
    for request_raw, response_raw in zip(requests, responses, strict=True):
        request = wire.ControlInput.model_validate_json(request_raw)
        response = wire.ControlResponse.model_validate_json(response_raw)
        assert json.loads(request.model_dump_json()) == json.loads(request_raw)
        assert json.loads(response.model_dump_json()) == json.loads(response_raw)
        assert request.sequence == response.sequence
        assert response.event == (
            "refused" if request.sequence == 1 else wire.expected_event(request.action)
        )

    invalid = wire.ControlResponse.model_validate_json(responses[-1])
    assert invalid.event == "applied"
    assert invalid.state.amount_text == "28-"
    assert invalid.state.allocation_error is not None
    assert isinstance(invalid.state.collection_allocation, wire.CollectionAllocation)
    assert invalid.state.collection_allocation.collection.target_cash_micros == "28000000"


def test_rust_observed_statuses_preserve_the_reviewed_and_accepted_original() -> None:
    raw_review, raw_accept = frames("reviewed-accepted")
    review = wire.ControlResponse.model_validate_json(raw_review)
    accepted = wire.ControlResponse.model_validate_json(raw_accept)
    assert json.loads(review.model_dump_json()) == json.loads(raw_review)
    assert json.loads(accepted.model_dump_json()) == json.loads(raw_accept)
    assert review.event == accepted.event == "observed"
    assert review.state.foundation_sha256 is accepted.state.foundation_sha256 is None
    command = review.state.reviewed_command
    assert command is not None and review.state.preview is not None
    assert command.allocation == review.state.preview.allocation == review.state.aid_allocation
    assert accepted.state.commitment is not None and accepted.state.commitment.command == command
    assert accepted.state.reviewed_command is accepted.state.preview is None


@pytest.mark.parametrize(
    "key",
    [
        "focused_amount",
        "amount_text",
        "allocation_error",
        "collection_allocation",
        "aid_allocation",
    ],
)
def test_absent_editor_field_is_not_null(key: str) -> None:
    data = json.loads(frames("responses")[0])
    data["state"][key] = None
    wire.ControlResponse.model_validate(data)
    del data["state"][key]
    with pytest.raises(ValidationError):
        wire.ControlResponse.model_validate(data)


@pytest.mark.parametrize("bad", [2, True, "3", 3.0])
def test_every_control_envelope_requires_exact_version(bad: object) -> None:
    request = json.loads(frames("requests")[0])
    response = json.loads(frames("responses")[0])
    startup = {"phase": "capture_ready", "campaign_id": request["campaign_id"]}
    for model, fields in (
        (wire.StartupAdmission, startup),
        (wire.ControlInput, request),
        (wire.ControlResponse, response),
    ):
        with pytest.raises(ValidationError):
            model.model_validate({**fields, "version": bad})


@pytest.mark.parametrize(
    "action",
    [
        {"focus_amount": "cash", "unknown": 1},
        {"amount_key": {"character": "12"}},
        {"amount_key": {"character": 3}},
        {"amount_key": {"character": ""}},
        {"amount_key": "select_all"},
        {"select_aid_partner": "workplace"},
        {"focus_amount": "stock"},
        {"amount_key": {"character": "1", "extra": False}},
    ],
)
def test_tagged_actions_reject_malformed_payloads(action: object) -> None:
    data = json.loads(frames("requests")[0])
    with pytest.raises(ValidationError):
        wire.ControlInput.model_validate({**data, "action": action})


@pytest.mark.parametrize(
    "amount", ["-1", "+1", "01", "1.0", "1\n", str(2**127), "0" * 40, 3, True, None]
)
def test_cash_must_be_a_canonical_nonnegative_i128_decimal_string(amount: object) -> None:
    cmd = json.loads(frames("reviewed-accepted")[0])["state"]["reviewed_command"]
    cmd["allocation"]["aid"]["cash_micros"] = amount
    with pytest.raises(ValidationError):
        wire.Command.model_validate(cmd)
    cmd["allocation"]["aid"]["cash_micros"] = str(2**127 - 1)
    assert wire.Command.model_validate(cmd).model_dump(mode="json") == cmd


@pytest.mark.parametrize(
    "changes",
    [
        {"allocation": None},
        {"allocation": "none"},
        {"choice": "collect"},
        {"allocation": {"aid": {"food_quantity": 0, "cash_micros": "0"}}},
        {"allocation": {"aid": {"food_quantity": True, "cash_micros": "0"}}},
        {"allocation": {"aid": {"food_quantity": 2**64, "cash_micros": "0"}}},
        {"allocation": {"aid": {"food_quantity": 1, "cash_micros": "0", "extra": 0}}},
        {"nonce": [True] * 16},
        {"nonce": [1] * 15},
        {"authority_id": [256] * 16},
        {"expected_period": False},
        {"content_digest": [0] * 31},
        {"other": 1},
    ],
)
def test_full_original_rejects_wrong_types_tags_lengths_or_extra_fields(
    changes: dict[str, object],
) -> None:
    cmd = json.loads(frames("reviewed-accepted")[0])["state"]["reviewed_command"]
    with pytest.raises(ValidationError):
        wire.Command.model_validate({**cmd, **changes})
    del cmd["allocation"]
    with pytest.raises(ValidationError):
        wire.Command.model_validate(cmd)


def test_collection_only_authorizes_a_positive_selected_target() -> None:
    cmd = json.loads(frames("reviewed-accepted")[0])["state"]["reviewed_command"]
    cmd.update(choice="collect", allocation={"collection": {"target_cash_micros": "1450000000"}})
    assert wire.Command.model_validate(cmd).model_dump(mode="json") == cmd
    cmd["allocation"]["collection"]["target_cash_micros"] = "0"
    with pytest.raises(ValidationError):
        wire.Command.model_validate(cmd)


@pytest.mark.parametrize(
    "field,value",
    [
        ("scope_epoch", True),
        ("expected_generation", -1),
        ("expected_tick", 2**64),
        ("sequence", 0),
        ("sequence", True),
        ("campaign_id", "a" * 32),
    ],
)
def test_input_identity_scalar_types_and_bounds(field: str, value: object) -> None:
    raw = json.loads(frames("requests")[0])
    with pytest.raises(ValidationError):
        wire.ControlInput.model_validate({**raw, field: value})
    del raw["scope_epoch"]
    with pytest.raises(ValidationError):
        wire.ControlInput.model_validate(raw)


def test_oversize_refusal_sentinel_is_never_a_numbered_control_result() -> None:
    with pytest.raises(ValidationError):
        wire.ControlResponse.model_validate(
            {
                "version": 3,
                "sequence": None,
                "event": "refused",
                "reason": "control_response_not_bounded",
            }
        )
