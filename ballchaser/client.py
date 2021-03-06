import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Set, Union

from backoff import expo, on_exception
from requests import Response, Session


class RateLimitException(Exception):
    pass


class BallChaser:
    _bc_url = "https://ballchasing.com/api"
    _playlists = {
        "unranked-duels",
        "unranked-doubles",
        "unranked-standard",
        "unranked-chaos",
        "private",
        "season",
        "offline",
        "ranked-duels",
        "ranked-doubles",
        "ranked-solo-standard",
        "ranked-standard",
        "snowday",
        "rocketlabs",
        "hoops",
        "rumble",
        "tournament",
        "dropshot",
        "ranked-hoops",
        "ranked-rumble",
        "ranked-dropshot",
        "ranked-snowday",
        "dropshot-rumble",
        "heatseeker",
    }
    _ranks = {
        "unranked",
        "bronze-1",
        "bronze-2",
        "bronze-3",
        "silver-1",
        "silver-2",
        "silver-3",
        "gold-1",
        "gold-2",
        "gold-3",
        "platinum-1",
        "platinum-2",
        "platinum-3",
        "diamond-1",
        "diamond-2",
        "diamond-3",
        "champion-1",
        "champion-2",
        "champion-3",
        "grand-champion",
    }
    _match_results = {"win", "loss"}
    _visibilities = {"public", "unlisted", "private"}
    _player_identifications = {"by-id", "by-name"}
    _team_identifications = {"by-distinct-players", "by-player-clusters"}
    _sort_by_replays = {"created", "replay-date"}
    _sort_by_groups = {"created", "name"}
    _sort_dir = {"asc", "desc"}

    def __init__(self, token: str, backoff: bool = False, max_tries: int = 10):
        """
        Args:
            token: ballchasing.com API token
            backoff: whether to retry API requests that run into rate limit errors
            max_tries: maximum number of attempts a request will be made if retrying
                request due to rate limit errors
        """
        self.session = Session()
        self.session.headers["Authorization"] = token
        self.backoff = backoff

        # Wrapper around helper method for API requests that will retry request if rate
        # limit is exceeded. Requests will be tried up to max_tries times with
        # exponential backoff between subsequent retries.
        self._request_backoff = on_exception(
            expo, RateLimitException, max_tries=max_tries, jitter=None
        )(self._request)

    @staticmethod
    def _check_param(
        param: Any,
        allowed_values: Union[List, Set],
        param_name: str,
    ) -> None:
        """
        Validates that the items in `param` exist in `allowed_values` raising a
        ValueError if not.
        """
        param = [param] if not isinstance(param, (list, set)) else param
        for item in param:
            if item not in allowed_values:
                raise ValueError(
                    f"'{param_name}' value(s) must be one of {allowed_values}, "
                    f"got {item}"
                )

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
            if response.status_code == 429:
                raise RateLimitException(response.text)
            raise Exception(response.text)

        return response

    def __request(
        self, method: str, url: str, params: Optional[Dict[str, Any]] = None, **kwargs
    ):
        if self.backoff:
            return self._request_backoff(method, url, params, **kwargs)

        return self._request(method, url, params, **kwargs)

    def ping(self) -> Dict:
        """
        Can be used to check if your API key is correct and if ballchasing API is
        reachable.
        """
        return self.__request("GET", self._bc_url).json()

    def get_maps(self) -> Dict:
        """
        Get dict of map codes to map names (map as in stadium).
        """
        return self.__request("GET", f"{self._bc_url}/maps").json()

    def get_replay(self, replay_id: str) -> Dict:
        """
        Retrieve the details and stats of the supplied replay id.

        Args:
            replay_id: unique identifier of replay to retrieve

        Returns:
            dict containing replay details and stats
        """
        return self.__request("GET", f"{self._bc_url}/replays/{replay_id}").json()

    def list_replays(
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
        group_id: Optional[str] = None,
        map_code: Optional[str] = None,
        created_before: Optional[datetime] = None,
        created_after: Optional[datetime] = None,
        replay_date_before: Optional[datetime] = None,
        replay_date_after: Optional[datetime] = None,
        count: Optional[int] = None,
        sort_by: Optional[str] = "created",
        sort_dir: Optional[str] = "desc",
    ) -> Iterator[Dict]:
        """
        Filter and list replays. At least one of player_name or player_id must be
        supplied.

        Args:
            player_name: filter replays by a player???s name
                (can supply a single player name as a str, or multiple player names via
                list of strings)
            player_id: filter replays by a player???s platform id in the $platform:$id
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
            group_id: only include replays belonging to the specified group, this only
                includes replays immediately under the specified group, but not replays
                in child groups
            map_code: only include replays in the specified map, use `get_maps` to
                retrieve valid map codes
            created_before: only include replays created before this date
            created_after: only include replays created after this date
            replay_date_before: only include replays for games before this date
            replay_date_after: only include replays for games after this date
            count: number of replays to retrieve (max 200) in each batch
            sort_by: how to sort replays ('created' or 'replay-date')
            sort_dir: sort direction ('asc' or 'desc')

        Returns:
            iterator of replay dicts
        """
        if not player_name and not player_id:
            raise Exception(
                "At least one of 'player_name' or 'player_id' must be supplied"
            )

        if playlist is not None:
            self._check_param(playlist, self._playlists, "playlist")
        if match_result is not None:
            self._check_param(match_result, self._match_results, "match_result")
        if min_rank is not None:
            self._check_param(min_rank, self._ranks, "min_rank")
        if max_rank is not None:
            self._check_param(max_rank, self._ranks, "max_rank")

        self._check_param(sort_by, self._sort_by_replays, "sort_by")
        self._check_param(sort_dir, self._sort_dir, "sort_dir")

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
            "group": group_id,
            "map": map_code,
            "created-before": created_before,
            "created-after": created_after,
            "replay-date-before": replay_date_before,
            "replay-date-after": replay_date_after,
            "count": count,
            "sort-by": sort_by,
            "sort-dir": sort_dir,
        }
        r = self.__request("GET", f"{self._bc_url}/replays", params=params)

        replays = r.json()["list"]
        yield from replays[:replay_count]

        remaining = replay_count - len(replays)
        while remaining > 0 and "next" in r.json():
            r = self.__request(
                "GET", r.json()["next"], params={"count": min(remaining, 200)}
            )

            replays = r.json()["list"]
            yield from replays[:remaining]
            remaining = replay_count - len(replays)

    def upload_replay(
        self, path: str, visibility: str = "public", group_id: str = None
    ) -> Dict:
        """
        Upload replay file at `path` to ballchasing.com.

        Args:
            path: path to replay file
            visibility: public, unlisted or private
            group_id: id of the group to assign to the uploaded replay
        """
        self._check_param(visibility, self._visibilities, "visibility")
        with open(path, "rb") as file:
            response = self.__request(
                "POST",
                f"{self._bc_url}/v2/upload",
                params={"visibility": visibility, "group": group_id},
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
        return self.__request("DELETE", f"{self._bc_url}/replays/{replay_id}")

    def patch_replay(self, replay_id: str, **kwargs) -> Response:
        """
        Patch one or more fields of a given replay. Fields to patch are accepted as
        kwargs.

        Args:
            replay_id: id of replay to patch
            **kwargs: fields to patch with new values
        """
        return self.__request(
            "PATCH", f"{self._bc_url}/replays/{replay_id}", json=kwargs
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
        response = self.__request("GET", f"{self._bc_url}/replays/{replay_id}/file")
        d = Path(directory)
        d.mkdir(parents=True, exist_ok=True)
        with open(Path(d, f"{replay_id}.replay"), "wb") as file:
            file.write(response.content)

    def create_group(
        self,
        name: str,
        player_identification: str,
        team_identification: str,
        parent_group_id: Optional[str] = None,
    ) -> Dict:
        """
        Create a new replay group.

        Args:
            name: name of the group
            player_identification: How to identify the same player across multiple
                replays. Some tournaments (e.g. RLCS) make players use a pool of
                generic Steam accounts, meaning the same player could end up using 2
                different accounts in 2 series. That's when the `by-name` comes in
                handy. Otherwise, use `by-id`.
            team_identification: How to identify the same team across multiple replays.
                Set to `by-distinct-players` if teams have a fixed roster of players
                for every single game. In some tournaments/leagues, teams allow player
                rotations, or a sub can replace another player, in which case use
                `by-player-clusters`.
            parent_group_id: id of the group to use as parent group for new group
        """
        self._check_param(
            player_identification, self._player_identifications, "player_identification"
        )
        self._check_param(
            team_identification,
            self._team_identifications,
            "team_identification",
        )
        return self.__request(
            "POST",
            f"{self._bc_url}/groups",
            json={
                "name": name,
                "player_identification": player_identification,
                "team_identification": team_identification,
                "parent": parent_group_id,
            },
        ).json()

    def list_groups(
        self,
        name: Optional[str] = None,
        creator: Optional[str] = None,
        group_id: Optional[str] = None,
        created_before: Optional[datetime] = None,
        created_after: Optional[datetime] = None,
        group_count: Optional[int] = 50,
        sort_by: Optional[str] = "created",
        sort_dir: Optional[str] = "desc",
    ) -> Iterator[Dict]:
        """
        Filter and list replay groups.

        Args:
            name: filter groups by name
            creator: only include groups created by the specified user, accepts either
                the numerical 76*************44 steam id, or the special value `me`
            group_id: only include children of the specified group id
            created_before: only include groups created (uploaded) before some date
            created_after: only include groups created (uploaded) after some date
            group_count: number of groups (max) to return
            sort_by: `created` or `name`
            sort_dir: `desc` or `asc`

        Returns:
            iterator of dicts
        """
        self._check_param(sort_by, self._sort_by_groups, "sort_by")
        self._check_param(sort_dir, self._sort_dir, "sort_dir")
        created_before = (
            created_before if created_before is None else created_before.isoformat()
        )
        created_after = (
            created_after if created_after is None else created_after.isoformat()
        )
        params = {
            "name": name,
            "creator": creator,
            "group": group_id,
            "created-before": created_before,
            "created-after": created_after,
            "sort-by": sort_by,
            "sort-dir": sort_dir,
        }
        r = self.__request("GET", f"{self._bc_url}/groups", params=params)

        groups = r.json()["list"]
        yield from groups[:group_count]

        remaining = group_count - len(groups)
        while remaining > 0 and "next" in r.json():
            r = self.__request(
                "GET", r.json()["next"], params={"count": min(remaining, 200)}
            )

            groups = r.json()["list"]
            yield from groups[:remaining]
            remaining = group_count - len(groups)

    def get_group(self, group_id: str) -> Dict:
        """
        Retrieve group metadata.

        Args:
            group_id: id of group
        """
        return self.__request("GET", f"{self._bc_url}/groups/{group_id}").json()

    def delete_group(self, group_id: str) -> Response:
        """
        Delete a group on ballchasing.com.

        Careful with this one, this operation is permanent and irreversible.

        Args:
            group_id: id of the group to delete
        """
        return self.__request("DELETE", f"{self._bc_url}/groups/{group_id}")

    def patch_group(self, group_id: str, **kwargs) -> Response:
        """
        Patch one or more fields of a given group. Fields to patch are accepted as
        kwargs.

        Args:
            group_id: id of group to patch
            **kwargs: fields to patch with new values
        """
        return self.__request("PATCH", f"{self._bc_url}/groups/{group_id}", json=kwargs)
