import os.path
import re
from contextlib import nullcontext as does_not_raise
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory
from typing import ContextManager, Dict

import pytest
from requests import Response
from requests_mock import Mocker as RequestsMocker

from ballchaser.client import BallChaser, RateLimitException


@pytest.mark.parametrize(
    argnames=["param", "allowed_values", "param_name", "exception"],
    argvalues=[
        (
            [1, 2, 3],
            [1, 2, 3],
            "numbers",
            does_not_raise(),
        ),
        (
            1,
            [1, 2, 3],
            "numbers",
            does_not_raise(),
        ),
        (
            1,
            {1, 2, 3},
            "numbers",
            does_not_raise(),
        ),
        (["a", "b", "c"], {"a", "b", "c"}, "letters", does_not_raise()),
        (
            123,
            {1, 2, 3},
            "numbers",
            pytest.raises(
                ValueError,
                match=re.escape("'numbers' value(s) must be one of {1, 2, 3}, got 123"),
            ),
        ),
        (
            "a",
            {"b"},
            "letters",
            pytest.raises(
                ValueError,
                match=re.escape("'letters' value(s) must be one of {'b'}, got a"),
            ),
        ),
    ],
)
def test_ball_chaser__check_param(
    param, allowed_values, param_name, exception, ball_chaser
):
    with exception:
        ball_chaser._check_param(param, allowed_values, param_name)


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
            "http://abc.com",
            429,
            {"error": "too many requests"},
            pytest.raises(RateLimitException, match='{"error": "too many requests"}'),
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
    argnames=["mock_responses", "expected_json", "exception"],
    argvalues=[
        (
            [
                {
                    "status_code": 200,
                    "json": {"key": "value"},
                }
            ],
            {"key": "value"},
            does_not_raise(),
        ),
        (
            [
                {
                    "status_code": 429,
                    "json": {"error": "too many requests"},
                },
                {
                    "status_code": 200,
                    "json": {"key1": "value1"},
                },
            ],
            {"key1": "value1"},
            does_not_raise(),
        ),
        (
            [
                {
                    "status_code": 429,
                    "json": {"error": "too many requests"},
                },
                {
                    "status_code": 429,
                    "json": {"error": "too many requests"},
                },
            ],
            None,
            pytest.raises(RateLimitException, match='{"error": "too many requests"}'),
        ),
    ],
)
def test_ball_chaser__request_backoff(
    mock_responses, expected_json, exception, ball_chaser
):
    url = "https://ballchasing.com/api"
    ball_chaser = BallChaser("abc", max_tries=2)
    with RequestsMocker() as rm, exception:
        rm.get(url=url, response_list=mock_responses)
        actual = ball_chaser._request_backoff("GET", url)
        assert isinstance(actual, Response)
        assert actual.json() == expected_json


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


def test_ball_chaser_list_replays_no_player_name_or_id(ball_chaser: BallChaser):
    with pytest.raises(
        Exception, match="At least one of 'player_name' or 'player_id' must be supplied"
    ):
        next(ball_chaser.list_replays())


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
def test_ball_chaser_list_replays(
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
            for replay in ball_chaser.list_replays(
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
def test_ball_chaser_upload_replay(
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
            actual = ball_chaser.upload_replay(file.name, "public", "group-123")
            assert actual == mock_json


@pytest.mark.parametrize(
    argnames=["replay_id", "mock_status_code", "exception"],
    argvalues=(
        (
            "abc-123",
            204,
            does_not_raise(),
        ),
        (
            "What a save!",
            500,
            pytest.raises(Exception),
        ),
    ),
)
def test_ball_chaser_delete_replay(
    replay_id: str,
    mock_status_code: int,
    exception: ContextManager,
    ball_chaser: BallChaser,
):
    with RequestsMocker() as rm, exception:
        rm.delete(
            f"https://ballchasing.com/api/replays/{replay_id}",
            status_code=mock_status_code,
        )
        actual = ball_chaser.delete_replay(replay_id)
        assert isinstance(actual, Response)


@pytest.mark.parametrize(
    argnames=["replay_id", "mock_status_code", "exception"],
    argvalues=(
        (
            "abc-123",
            204,
            does_not_raise(),
        ),
        (
            "What a save!",
            500,
            pytest.raises(Exception),
        ),
    ),
)
def test_ball_chaser_patch_replay(
    replay_id: str,
    mock_status_code: int,
    exception: ContextManager,
    ball_chaser: BallChaser,
):
    with RequestsMocker() as rm, exception:
        rm.patch(
            f"https://ballchasing.com/api/replays/{replay_id}",
            status_code=mock_status_code,
        )
        actual = ball_chaser.patch_replay(
            replay_id, title="New Title", visibility="private", group="group-1"
        )
        assert isinstance(actual, Response)


@pytest.mark.parametrize(
    argnames=["replay_id", "mock_status_code", "mock_content", "exception"],
    argvalues=(
        (
            "abc-123",
            200,
            b"some_bytes",
            does_not_raise(),
        ),
        (
            "abc-does-not-exist",
            404,
            None,
            pytest.raises(Exception),
        ),
        (
            "def",
            500,
            None,
            pytest.raises(Exception),
        ),
    ),
)
def test_ball_chaser_download(
    replay_id: str,
    mock_status_code: int,
    mock_content: bytes,
    exception: ContextManager,
    ball_chaser: BallChaser,
):
    with RequestsMocker() as rm, exception:
        rm.get(
            url=f"https://ballchasing.com/api/replays/{replay_id}/file",
            status_code=mock_status_code,
            content=mock_content,
        )

        # directory not supplied, saves to current working directory
        assert not os.path.isfile(Path(os.getcwd(), f"{replay_id}.replay"))
        ball_chaser.download_replay(replay_id)
        assert os.path.isfile(Path(os.getcwd(), f"{replay_id}.replay"))
        os.remove(Path(os.getcwd(), f"{replay_id}.replay"))

        # save to existing directory
        with TemporaryDirectory() as td:
            assert not os.path.isfile(Path(td, f"{replay_id}.replay"))
            ball_chaser.download_replay(replay_id, directory=td)
            assert os.path.isfile(Path(td, f"{replay_id}.replay"))

        # save to directory that doesn't exist (i.e. test directory creation)
        assert not os.path.isfile(Path(os.getcwd(), "./12345", f"{replay_id}.replay"))
        ball_chaser.download_replay(replay_id, directory="./12345")
        assert os.path.isfile(Path(os.getcwd(), "./12345", f"{replay_id}.replay"))
        os.remove(Path(os.getcwd(), "./12345", f"{replay_id}.replay"))
        os.rmdir(Path(os.getcwd(), "./12345"))


@pytest.mark.parametrize(
    argnames=["mock_status_code", "mock_json", "exception"],
    argvalues=(
        (
            201,
            {
                "id": "my-new-group-abc-123",
                "link": "https://ballchasing.com/api/groups/my-new-group-abc-123",
            },
            does_not_raise(),
        ),
        (
            409,
            {"error": "duplicate group"},
            pytest.raises(Exception, match="duplicate group"),
        ),
        (
            500,
            {"error": "Internal server error."},
            pytest.raises(Exception, match='{"error": "Internal server error."}'),
        ),
    ),
)
def test_ball_chaser_create_group(
    mock_status_code: int,
    mock_json: dict,
    exception: ContextManager,
    ball_chaser: BallChaser,
):
    with RequestsMocker() as rm, exception:
        rm.post(
            "https://ballchasing.com/api/groups",
            status_code=mock_status_code,
            json=mock_json,
        )
        actual = ball_chaser.create_group(
            name="my-new-group",
            player_identification="by-id",
            team_identification="by-player-clusters",
            parent_group_id="group-parent",
        )
        assert actual == mock_json


@pytest.mark.parametrize(
    argnames=["group_count", "mock_responses", "expected", "exception"],
    argvalues=(
        (
            1,
            [
                {
                    "status_code": 200,
                    "json": {
                        "count": 4,
                        "list": [{"id": "abc-123"}, {"id": "def-456"}],
                        "next": "https://ballchasing.com/api/groups",
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
                        "next": "https://ballchasing.com/api/groups",
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
                        "next": "https://ballchasing.com/api/groups",
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
                        "next": "https://ballchasing.com/api/groups",
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
def test_ball_chaser_list_groups(
    group_count: int,
    mock_responses: list,
    expected: dict,
    exception: ContextManager,
    ball_chaser: BallChaser,
):
    with RequestsMocker() as rm, exception:
        rm.get("https://ballchasing.com/api/groups", response_list=mock_responses)
        actual = [
            replay
            for replay in ball_chaser.list_groups(name="RLCS", group_count=group_count)
        ]
        assert actual == expected


@pytest.mark.parametrize(
    argnames=["mock_status_code", "mock_json", "exception"],
    argvalues=(
        (
            200,
            {"id": "my-group-abc-123"},
            does_not_raise(),
        ),
        (
            404,
            {"error": "not found"},
            pytest.raises(Exception, match="not found"),
        ),
        (
            500,
            {"error": "Internal server error."},
            pytest.raises(Exception, match='{"error": "Internal server error."}'),
        ),
    ),
)
def test_ball_chaser_get_group(
    mock_status_code: int,
    mock_json: dict,
    exception: ContextManager,
    ball_chaser: BallChaser,
):
    with RequestsMocker() as rm, exception:
        rm.get(
            "https://ballchasing.com/api/groups/my-group",
            status_code=mock_status_code,
            json=mock_json,
        )
        actual = ball_chaser.get_group("my-group")
        assert actual == mock_json


@pytest.mark.parametrize(
    argnames=["group_id", "mock_status_code", "exception"],
    argvalues=(
        (
            "abc-123",
            204,
            does_not_raise(),
        ),
        (
            "What a save!",
            500,
            pytest.raises(Exception),
        ),
    ),
)
def test_ball_chaser_delete_group(
    group_id: str,
    mock_status_code: int,
    exception: ContextManager,
    ball_chaser: BallChaser,
):
    with RequestsMocker() as rm, exception:
        rm.delete(
            f"https://ballchasing.com/api/groups/{group_id}",
            status_code=mock_status_code,
        )
        actual = ball_chaser.delete_group(group_id)
        assert isinstance(actual, Response)


@pytest.mark.parametrize(
    argnames=["group_id", "mock_status_code", "exception"],
    argvalues=(
        (
            "abc-123",
            204,
            does_not_raise(),
        ),
        (
            "What a save!",
            500,
            pytest.raises(Exception),
        ),
    ),
)
def test_ball_chaser_patch_group(
    group_id: str,
    mock_status_code: int,
    exception: ContextManager,
    ball_chaser: BallChaser,
):
    with RequestsMocker() as rm, exception:
        rm.patch(
            f"https://ballchasing.com/api/groups/{group_id}",
            status_code=mock_status_code,
        )
        actual = ball_chaser.patch_group(
            group_id,
            team_identification="by-player-clusters",
            shared=True,
            parent="new-parent-group",
        )
        assert isinstance(actual, Response)
