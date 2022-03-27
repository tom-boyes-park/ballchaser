from contextlib import nullcontext as does_not_raise
from tempfile import NamedTemporaryFile
from typing import ContextManager, Dict

import pytest
from requests import Response
from requests_mock import Mocker as RequestsMocker

from ballchaser.client import BallChaser


@pytest.mark.parametrize(
    argnames=["mock_status_code", "mock_json", "exception"],
    argvalues=(
        (200, {"chaser": True, "type": "regular"}, does_not_raise()),
        (
            401,
            {"error": "Invalid API key."},
            pytest.raises(Exception, match="Invalid API key."),
        ),
        (
            500,
            {"error": "Internal server error."},
            pytest.raises(Exception, match="Internal server error."),
        ),
    ),
)
def test_ball_chaser___init__(
    mock_status_code: int, mock_json: dict, exception: ContextManager
):
    with RequestsMocker() as rm, exception:
        rm.get(
            "https://ballchasing.com/api", status_code=mock_status_code, json=mock_json
        )
        ball_chaser = BallChaser("abc-123")
        assert ball_chaser.patronage == mock_json["type"]


@pytest.mark.parametrize(
    argnames=["url", "mock_status_code", "mock_json", "exception"],
    argvalues=(
        ("http://abc.com", 200, {"map_1": "Map 1", "map_2": "Map 2"}, does_not_raise()),
        ("http://abc.com", 201, {"id": "abc"}, does_not_raise()),
        (
            "http://abc.com",
            300,
            {"error": "error"},
            pytest.raises(Exception, match='{"error": "error"}'),
        ),
        (
            "http://abc.com",
            400,
            {"error": "bad request"},
            pytest.raises(Exception, match='{"error": "bad request"}'),
        ),
        (
            "http://def.com",
            500,
            {"error": "Internal server error."},
            pytest.raises(Exception, match='{"error": "Internal server error."}'),
        ),
    ),
)
def test_ball_chaser__request(
    url: str,
    mock_status_code: int,
    mock_json: Dict,
    exception: ContextManager,
    ball_chaser: BallChaser,
):
    with RequestsMocker() as rm, exception:
        rm.get(
            url=url,
            status_code=mock_status_code,
            json=mock_json,
        )
        actual = ball_chaser._request("GET", url, {"a": 1})
        assert isinstance(actual, Response)
        assert actual.json() == mock_json


@pytest.mark.parametrize(
    argnames=["mock_status_code", "mock_json", "exception"],
    argvalues=(
        (200, {"chaser": True, "type": "regular"}, does_not_raise()),
        (
            401,
            {"error": "Invalid API key."},
            pytest.raises(Exception, match="Invalid API key."),
        ),
        (
            500,
            {"error": "Internal server error."},
            pytest.raises(Exception, match="Internal server error."),
        ),
    ),
)
def test_ball_chaser_ping(
    mock_status_code: int,
    mock_json: dict,
    exception: ContextManager,
    ball_chaser: BallChaser,
):
    with RequestsMocker() as rm, exception:
        rm.get(
            "https://ballchasing.com/api", status_code=mock_status_code, json=mock_json
        )
        actual = ball_chaser.ping()
        assert actual == mock_json


@pytest.mark.parametrize(
    argnames=["mock_status_code", "mock_json", "exception"],
    argvalues=(
        (200, {"map_1": "Map 1", "map_2": "Map 2"}, does_not_raise()),
        (
            500,
            {"error": "Internal server error."},
            pytest.raises(Exception, match='{"error": "Internal server error."}'),
        ),
    ),
)
def test_ball_chaser_get_maps(
    mock_status_code: int,
    mock_json: Dict,
    exception: ContextManager,
    ball_chaser: BallChaser,
):
    with RequestsMocker() as rm, exception:
        rm.get(
            "https://ballchasing.com/api/maps",
            status_code=mock_status_code,
            json=mock_json,
        )
        actual = ball_chaser.get_maps()
        assert actual == mock_json


@pytest.mark.parametrize(
    argnames=["replay_id", "mock_status_code", "mock_json", "exception"],
    argvalues=(
        (
            "abc-123",
            200,
            {"id": "abc-123", "status": "ok"},
            does_not_raise(),
        ),
        (
            "def-456",
            200,
            {"id": "def-456", "status": "ok"},
            does_not_raise(),
        ),
        (
            "What a save!",
            500,
            {"error": "Internal server error."},
            pytest.raises(Exception, match='{"error": "Internal server error."}'),
        ),
    ),
)
def test_ball_chaser_get_replay(
    replay_id: str,
    mock_status_code: int,
    mock_json: dict,
    exception: ContextManager,
    ball_chaser: BallChaser,
):
    with RequestsMocker() as rm, exception:
        rm.get(
            f"https://ballchasing.com/api/replays/{replay_id}",
            status_code=mock_status_code,
            json=mock_json,
        )
        actual = ball_chaser.get_replay(replay_id)
        assert actual == mock_json


def test_ball_chaser_get_replays_no_player_name_or_id(ball_chaser: BallChaser):
    with pytest.raises(
        Exception, match="At least one of 'player_name' or 'player_id' must be supplied"
    ):
        next(ball_chaser.get_replays())


@pytest.mark.parametrize(
    argnames=["replay_count", "mock_responses", "expected", "exception"],
    argvalues=(
        (
            1,
            [
                {
                    "status_code": 200,
                    "json": {
                        "count": 4,
                        "list": [{"id": "abc-123"}, {"id": "def-456"}],
                        "next": "https://ballchasing.com/api/replays",
                    },
                },
                {
                    "status_code": 200,
                    "json": {
                        "count": 4,
                        "list": [{"id": "ghi-789"}, {"id": "jkl-101"}],
                    },
                },
            ],
            [
                {"id": "abc-123"},
            ],
            does_not_raise(),
        ),
        (
            4,
            [
                {
                    "status_code": 200,
                    "json": {
                        "count": 4,
                        "list": [{"id": "abc-123"}, {"id": "def-456"}],
                        "next": "https://ballchasing.com/api/replays",
                    },
                },
                {
                    "status_code": 200,
                    "json": {
                        "count": 4,
                        "list": [{"id": "ghi-789"}, {"id": "jkl-101"}],
                    },
                },
            ],
            [
                {"id": "abc-123"},
                {"id": "def-456"},
                {"id": "ghi-789"},
                {"id": "jkl-101"},
            ],
            does_not_raise(),
        ),
        (
            100,
            [
                {
                    "status_code": 200,
                    "json": {
                        "count": 4,
                        "list": [{"id": "abc-123"}, {"id": "def-456"}],
                        "next": "https://ballchasing.com/api/replays",
                    },
                },
                {
                    "status_code": 200,
                    "json": {
                        "count": 4,
                        "list": [{"id": "ghi-789"}, {"id": "jkl-101"}],
                    },
                },
            ],
            [
                {"id": "abc-123"},
                {"id": "def-456"},
                {"id": "ghi-789"},
                {"id": "jkl-101"},
            ],
            does_not_raise(),
        ),
        (
            10,
            [
                {
                    "status_code": 200,
                    "json": {"list": []},
                }
            ],
            [],
            does_not_raise(),
        ),
        (
            10,
            [
                {
                    "status_code": 500,
                    "json": {"error": "Internal server error."},
                }
            ],
            None,
            pytest.raises(Exception, match='{"error": "Internal server error."}'),
        ),
        (
            4,
            [
                {
                    "status_code": 200,
                    "json": {
                        "count": 4,
                        "list": [{"id": "abc-123"}, {"id": "def-456"}],
                        "next": "https://ballchasing.com/api/replays",
                    },
                },
                {
                    "status_code": 500,
                    "json": {"error": "What a save!"},
                },
            ],
            None,
            pytest.raises(Exception, match='{"error": "What a save!"}'),
        ),
    ),
)
def test_ball_chaser_get_replays(
    replay_count: int,
    mock_responses: list,
    expected: dict,
    exception: ContextManager,
    ball_chaser: BallChaser,
):
    with RequestsMocker() as rm, exception:
        rm.get("https://ballchasing.com/api/replays", response_list=mock_responses)
        actual = [
            replay
            for replay in ball_chaser.get_replays(
                player_name="GarrettG", replay_count=replay_count
            )
        ]
        assert actual == expected


@pytest.mark.parametrize(
    argnames=["mock_status_code", "mock_json", "exception"],
    argvalues=(
        (
            201,
            {
                "id": "abc-123",
                "location": "https://ballchasing.com/replay/abc-123",
            },
            does_not_raise(),
        ),
        (
            409,
            {
                "chat": {"Roundhouse": "My Fault.", "YOU": "Savage!"},
                "error": "duplicate replay",
                "id": "abc-123",
                "location": "https://ballchasing.com/replay/abc-123",
            },
            pytest.raises(Exception, match="duplicate replay"),
        ),
        (
            500,
            {"error": "Internal server error."},
            pytest.raises(Exception, match='{"error": "Internal server error."}'),
        ),
    ),
)
def test_ball_chaser_upload(
    mock_status_code: int,
    mock_json: dict,
    exception: ContextManager,
    ball_chaser: BallChaser,
):
    with RequestsMocker() as rm, exception:
        rm.post(
            "https://ballchasing.com/api/v2/upload",
            status_code=mock_status_code,
            json=mock_json,
        )
        with NamedTemporaryFile() as file:
            actual = ball_chaser.upload(file.name, "public", "group-123")
            assert actual == mock_json
