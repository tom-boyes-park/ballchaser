# ballchaser ⚽️🚗

![PyPI](https://img.shields.io/pypi/v/ballchaser)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat)](https://pycqa.github.io/isort/)

Unofficial Python API client for the ballchasing.com API.

# Usage
```commandline
pip install ballchaser
```

All API requests are exposed via the `BallChaser` class which is initialised with a [ballchasing.com API token](https://ballchasing.com/doc/api#header-authentication).

```python
import os

from ballchaser.client import BallChaser

ball_chaser = BallChaser(os.getenv("BALLCHASING_API_TOKEN"))

# search and retrieve replay metadata
replays = [
    replay
    for replay in ball_chaser.list_replays(player_name="GarrettG", replay_count=10)
]

# retrieve replay statistics
replay_stats = [
    ball_chaser.get_replay(replay["id"])
    for replay in replays
]
```

API requests can automatically be retried if they return a rate limit response by specifying `backoff=True`. Requests
will be tried up to `max_tries` times with exponential backoff between subsequent retries, e.g.

```python
import os

from ballchaser.client import BallChaser

ball_chaser = BallChaser(os.getenv("BALLCHASING_API_TOKEN"), backoff=True, max_tries=5)
```

# Contributing & Feedback

If there are any new features you'd like, or you encounter a bug, you can contribute by opening an issue or submitting a pull request.
