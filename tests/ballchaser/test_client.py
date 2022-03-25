from contextlib import nullcontext as does_not_raise
from typing import ContextManager, Dict

import pytest
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
def test_ball_chaser_init(
    mock_status_code: int, mock_json: dict, exception: ContextManager
):
    with RequestsMocker() as rm, exception:
        rm.get(
            "https://ballchasing.com/api", status_code=mock_status_code, json=mock_json
        )
        ball_chaser = BallChaser("abc-123")
        assert ball_chaser.patronage == mock_json["type"]


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
    mock_status_code: int, mock_json: Dict, exception: ContextManager
):
    with RequestsMocker() as rm, exception:
        rm.get(
            "https://ballchasing.com/api",
            status_code=200,
            json={"chaser": True, "type": "regular"},
        )
        rm.get(
            "https://ballchasing.com/api/maps",
            status_code=mock_status_code,
            json=mock_json,
        )
        ball_chaser = BallChaser("abc-123")
        actual = ball_chaser.get_maps()
        assert actual == mock_json
