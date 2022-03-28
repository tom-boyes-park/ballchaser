# ballchaser ⚽️🚗

![PyPI](https://img.shields.io/pypi/v/ballchaser)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat)](https://pycqa.github.io/isort/)

Unofficial Python API client for the ballchasing.com API.

# Getting Started
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
relay_stats = [
    ball_chaser.get_replay(replay["id"])
    for replay in replays
]
```
