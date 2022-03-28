import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterator, Optional, Union

from requests import Response, Session


# TODO: implement rate limiting based on patronage
class BallChaser:
    _bc_url = "https://ballchasing.com/api"

    def __init__(self, token: str):
        self.session = Session()
        self.session.headers["Authorization"] = token
        self._set_patronage()

    def _set_patronage(self) -> None:
        """
        Determine and set patron level so that we know what rate limits to apply
        when hitting endpoints.
        """
        response = self.ping()
        self.patronage = response["type"]

    def _request(
        self, method: str, url: str, params: Optional[Dict[str, Any]] = None, **kwargs
    ) -> Response:
        """
        Helper method for API requests.

        Args:
            method: HTTP method for request
            url: request url
            params: request parameters

        Returns:
            Response
        """
        response = self.session.request(url=url, method=method, params=params, **kwargs)
        if not (200 <= response.status_code < 300):
            raise Exception(response.text)

        return response

    def ping(self) -> Dict:
        """
        Can be used to check if your API key is correct and if ballchasing API is
        reachable.
        """
        return self._request("GET", self._bc_url).json()

    def get_maps(self) -> Dict:
        """
        Get dict of map codes to map names (map as in stadium).
        """
        return self._request("GET", f"{self._bc_url}/maps").json()

    def get_replay(self, replay_id: str) -> Dict:
        """
        Retrieve the details and stats of the supplied replay id.

        This endpoint is rate limited to:

        - GC patrons: 16 calls/second
        - Champion patrons: 8 calls/second
        - Diamond patrons: 4 calls/second, 5000/hour
        - Gold patrons: 2 calls/second, 2000/hour
        - All others: 2 calls/second, 1000/hour

        Args:
            replay_id: unique identifier of replay to retrieve

        Returns:
            dict containing replay details and stats
        """
        return self._request("GET", f"{self._bc_url}/replays/{replay_id}").json()

    # TODO: use Enums for args where appropriate
    def get_replays(
        self,
        player_name: Optional[Union[str, list]] = None,
        player_id: Optional[Union[str, list]] = None,
        replay_count: Optional[int] = 50,
        title: Optional[str] = None,
        playlist: Optional[Union[str, list]] = None,
        season: Optional[str] = None,
        match_result: Optional[str] = None,
        min_rank: Optional[str] = None,
        max_rank: Optional[str] = None,
        pro: Optional[bool] = None,
        uploader: Optional[str] = None,
        group: Optional[str] = None,
        map_code: Optional[str] = None,
        created_before: Optional[datetime] = None,
        created_after: Optional[datetime] = None,
        replay_date_before: Optional[datetime] = None,
        replay_date_after: Optional[datetime] = None,
        count: Optional[int] = None,
        sort_by: Optional[int] = None,
        sort_dir: Optional[int] = None,
    ) -> Iterator:
        """
        Filter and retrieve replays. At least one of player_name or player_id must be
        supplied.

        This endpoint is rate limited to:

        - GC patrons: 16 calls/second
        - Champion patrons: 8 calls/second
        - Diamond patrons: 4 calls/second, 2000/hour
        - Gold patrons: 2 calls/second, 1000/hour
        - All others: 2 calls/second, 500/hour

        Args:
            player_name: filter replays by a player’s name
                (can supply a single player name as a str, or multiple player names via
                list of strings)
            player_id: filter replays by a player’s platform id in the $platform:$id
                (can supply a single player id as a str, or multiple player ids via list
                of strings)
            replay_count: number of replays to retrieve
            title: replay title
            playlist: filter replays by one or more playlists (string or list of strings
                respectively)
            season: filter replays by season. Must be a number between 1 and 14 (for
                old seasons) or f1, f2, etc. for the new free to play seasons
            match_result: filter replays by result ('win' or 'loss')
            min_rank: filter replays based on players minimum rank
            max_rank: filter replays based on players maximum rank
            pro: only include replays containing at least one pro player
            uploader: only include replays uploaded by the specified user, accepts
                either the numerical 76*************44 steam id, or the special value me
            group: only include replays belonging to the specified group, this only
                includes replays immediately under the specified group, but not replays
                in child groups
            map_code: only include replays in the specified map, use `get_maps` to
                retrieve valid map codes
            created_before: only include replays created before this date
            created_after: only include replays created after this date
            replay_date_before: only include replays for games before this date
            replay_date_after: only include replays for games after this date
            count: number of replays to retrieve (max 200) in each batch
            sort_by: how to sort replays ('replay-date' or 'upload-date')
            sort_dir: sort direction ('asc' or 'desc')

        Returns:
            iterator of replay dicts
        """
        if not player_name and not player_id:
            raise Exception(
                "At least one of 'player_name' or 'player_id' must be supplied"
            )

        created_before = (
            created_before if created_before is None else created_before.isoformat()
        )
        created_after = (
            created_after if created_after is None else created_after.isoformat()
        )
        replay_date_before = (
            replay_date_before
            if replay_date_before is None
            else replay_date_before.isoformat()
        )
        replay_date_after = (
            replay_date_after
            if replay_date_after is None
            else replay_date_after.isoformat()
        )

        params = {
            "title": title,
            "player-name": player_name,
            "player-id": player_id,
            "playlist": playlist,
            "season": season,
            "match-result": match_result,
            "min-rank": min_rank,
            "max-rank": max_rank,
            "pro": pro,
            "uploader": uploader,
            "group": group,
            "map": map_code,
            "created-before": created_before,
            "created-after": created_after,
            "replay-date-before": replay_date_before,
            "replay-date-after": replay_date_after,
            "count": count,
            "sort-by": sort_by,
            "sort-dir": sort_dir,
        }
        r = self._request("GET", f"{self._bc_url}/replays", params=params)

        replays = r.json()["list"]
        yield from replays[:replay_count]

        remaining = replay_count - len(replays)
        while remaining > 0 and "next" in r.json():
            r = self._request(
                "GET", r.json()["next"], params={"count": min(remaining, 200)}
            )

            replays = r.json()["list"]
            yield from replays[:remaining]
            remaining = replay_count - len(replays)

    def upload(self, path: str, visibility: str = "public", group: str = None) -> Dict:
        """
        Upload replay file at `path` to ballchasing.com.

        Args:
            path: path to replay file
            visibility: public, unlisted or private
            group: id of the group to assign to the uploaded replay
        """
        with open(path, "rb") as file:
            response = self._request(
                "POST",
                f"{self._bc_url}/v2/upload",
                params={"visibility": visibility, "group": group},
                files={"file": file},
            )

        return response.json()

    def delete_replay(self, replay_id: str) -> Response:
        """
        Delete a replay uploaded to ballchasing.com.

        Careful with this one, this operation is permanent and irreversible.

        Args:
            replay_id: id of the replay to delete
        """
        return self._request("DELETE", f"{self._bc_url}/replays/{replay_id}")

    def patch_replay(self, replay_id: str, **kwargs) -> Response:
        """
        Patch one or more fields of a given replay. Fields to patch are accepted as
        kwargs.

        Args:
            replay_id: id of replay to patch
            **kwargs: fields to patch with new values
        """
        return self._request(
            "PATCH", f"{self._bc_url}/replays/{replay_id}", data=kwargs
        )

    def download_replay(
        self, replay_id: str, directory: Optional[str] = os.getcwd()
    ) -> None:
        """
        Download a replay from ballchasing.com, writing it to a .replay file.

        Optionally provide the path to the directory into which to save the replay.
        Defaults to current working directory if not specified.

        Args:
            replay_id: id of the replay to download
            directory: directory into which the replay will be saved
        """
        response = self._request("GET", f"{self._bc_url}/replays/{replay_id}/file")
        d = Path(directory)
        d.mkdir(parents=True, exist_ok=True)
        with open(Path(d, f"{replay_id}.replay"), "wb") as file:
            file.write(response.content)

    def __repr__(self):
        return f"BallChaser(patronage={self.patronage})"
