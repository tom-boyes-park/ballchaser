""" Contains fixtures used in unit tests. """
import pytest

from ballchaser.client import BallChaser


@pytest.fixture()
def ball_chaser():
    return BallChaser("abc-123")
