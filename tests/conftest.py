""" Contains fixtures used in unit tests. """
from ballchaser.client import BallChaser

from requests_mock import Mocker as RequestsMocker
import pytest


@pytest.fixture()
def ball_chaser():
    with RequestsMocker() as rm:
        rm.get(
            "https://ballchasing.com/api",
            status_code=200,
            json={"chaser": True, "type": "regular"},
        )
        return BallChaser("abc-123")
