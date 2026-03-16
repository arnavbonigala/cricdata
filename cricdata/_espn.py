"""ESPN open API — player search, bio, and ball-by-ball (no auth required)."""

from __future__ import annotations

from typing import Dict, List, Union

from ._session import AsyncSession, Session

_SEARCH_URL = "https://site.web.api.espn.com/apis/common/v3/search"
_ATHLETE_URL = "https://site.web.api.espn.com/apis/common/v3/sports/cricket/athletes"
_PLAYBYPLAY_URL = "https://site.web.api.espn.com/apis/site/v2/sports/cricket/8676/playbyplay"


class ESPN:
    """Thin wrapper around ESPN's open cricket endpoints."""

    def __init__(self, session: Session):
        self._s = session

    def search_players(self, query: str, limit: int = 10) -> List[dict]:
        r = self._s.get(
            _SEARCH_URL,
            params={"query": query, "type": "player", "sport": "cricket", "limit": limit},
        )
        r.raise_for_status()
        return r.json().get("items", [])

    def player_bio(self, player_id: int | str) -> dict:
        r = self._s.get(f"{_ATHLETE_URL}/{player_id}")
        r.raise_for_status()
        return r.json().get("athlete", {})

    def match_ball_by_ball(self, match_id: Union[int, str]) -> List[List[dict]]:
        """Full ball-by-ball for a match via ESPN playbyplay API.

        Paginates through all pages (25 items each) and groups balls by
        innings number.  Returns a list of innings, each a list of ball dicts.
        """
        all_items: List[dict] = []
        page = 1
        while True:
            r = self._s.get(
                _PLAYBYPLAY_URL, params={"event": match_id, "page": page}
            )
            r.raise_for_status()
            commentary = r.json().get("commentary", {})
            items = commentary.get("items", [])
            if not items:
                break
            all_items.extend(items)
            page_count = commentary.get("pageCount", 1)
            if page >= page_count:
                break
            page += 1

        innings_map: Dict[int, List[dict]] = {}
        for item in all_items:
            inn_obj = item.get("innings", {})
            inn_num = inn_obj.get("number", item.get("period", 0))
            innings_map.setdefault(inn_num, []).append(item)

        return [innings_map[k] for k in sorted(innings_map)]


class AsyncESPN:
    """Async variant of ESPN — mirrors every ESPN method."""

    def __init__(self, session: AsyncSession):
        self._s = session

    async def search_players(self, query: str, limit: int = 10) -> List[dict]:
        r = await self._s.get(
            _SEARCH_URL,
            params={"query": query, "type": "player", "sport": "cricket", "limit": limit},
        )
        r.raise_for_status()
        return r.json().get("items", [])

    async def player_bio(self, player_id: int | str) -> dict:
        r = await self._s.get(f"{_ATHLETE_URL}/{player_id}")
        r.raise_for_status()
        return r.json().get("athlete", {})

    async def match_ball_by_ball(self, match_id: Union[int, str]) -> List[List[dict]]:
        all_items: List[dict] = []
        page = 1
        while True:
            r = await self._s.get(
                _PLAYBYPLAY_URL, params={"event": match_id, "page": page}
            )
            r.raise_for_status()
            commentary = r.json().get("commentary", {})
            items = commentary.get("items", [])
            if not items:
                break
            all_items.extend(items)
            page_count = commentary.get("pageCount", 1)
            if page >= page_count:
                break
            page += 1

        innings_map: Dict[int, List[dict]] = {}
        for item in all_items:
            inn_obj = item.get("innings", {})
            inn_num = inn_obj.get("number", item.get("period", 0))
            innings_map.setdefault(inn_num, []).append(item)

        return [innings_map[k] for k in sorted(innings_map)]
