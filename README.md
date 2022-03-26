# ballchaser ⚽️🚗
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
    for replay in ball_chaser.get_replays(player_name="GarrettG", replay_count=10)
]

# retrieve replay statistics
relay_stats = [
    ball_chaser.get_replay(replay["id"])
    for replay in replays
]
```
