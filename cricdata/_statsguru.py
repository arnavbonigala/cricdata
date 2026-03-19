"""Statsguru HTML table parser — player, team, and ground statistics."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Union

from ._session import AsyncSession, Session
from ._types import (
    CareerStats,
    Format,
    GroundAverages,
    InningsList,
    MatchList,
    SeriesList,
    StatType,
    StatsFilter,
)

_PLAYER_BASE = "https://stats.espncricinfo.com/ci/engine/player"
_TEAM_BASE = "https://stats.espncricinfo.com/ci/engine/team"
_GROUND_BASE = "https://stats.espncricinfo.com/ci/engine/ground"

FORMAT_CLASS: Dict[str, int] = {
    "test": 1,
    "odi": 2,
    "t20i": 3,
    "fc": 4,
    "lista": 5,
    "t20": 6,
}

FILTER_MAP: Dict[str, str] = {
    "opposition": "opposition",
    "home_or_away": "home_or_away",
    "start_date": "spanmin1",
    "end_date": "spanmax1",
    "ground": "ground",
}

_ENGINE_TABLE_RE = re.compile(
    r'<table class="engineTable">(.*?)</table>', re.DOTALL
)
_ROW_RE = re.compile(r"<tr[^>]*>(.*?)</tr>", re.DOTALL)
_CELL_RE = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.DOTALL)
_TAG_RE = re.compile(r"<[^>]+>")


def _strip(html: str) -> str:
    return _TAG_RE.sub("", html).strip()


def _parse_tables(html: str) -> List[List[List[str]]]:
    """Extract all engineTable tables as lists of rows of cell strings."""
    tables = []
    for table_match in _ENGINE_TABLE_RE.finditer(html):
        rows = []
        for row_match in _ROW_RE.finditer(table_match.group(1)):
            cells = [_strip(c) for c in _CELL_RE.findall(row_match.group(1))]
            rows.append(cells)
        tables.append(rows)
    return tables


def _rows_to_dicts(rows: List[List[str]]) -> List[dict]:
    """Convert header row + data rows into a list of dicts."""
    if len(rows) < 2:
        return []
    headers = rows[0]
    out = []
    for row in rows[1:]:
        if len(row) != len(headers):
            continue
        out.append(dict(zip(headers, row)))
    return out


def _summary_and_detail(tables: List[List[List[str]]], detail_key: str) -> Any:
    result: dict = {"summary": {}, detail_key: []}
    if tables:
        summary_rows = _rows_to_dicts(tables[0])
        if summary_rows:
            result["summary"] = summary_rows[0]
    if len(tables) > 1:
        result[detail_key] = _rows_to_dicts(tables[1])
    return result


def _build_filter_params(filters: Optional[Dict[str, Union[str, int]]]) -> str:
    if not filters:
        return ""
    parts = ["filter=advanced"]
    for key, value in filters.items():
        sg_key = FILTER_MAP.get(key)
        if sg_key is None:
            raise ValueError(
                f"Unknown filter {key!r}, use: {list(FILTER_MAP)}"
            )
        parts.append(f"{sg_key}={value}")
    if "start_date" in filters or "end_date" in filters:
        parts.append("spanval1=span")
    return ";" + ";".join(parts)


def _class_param(fmt: str) -> int:
    cls = FORMAT_CLASS.get(fmt)
    if cls is None:
        raise ValueError(f"Unknown format {fmt!r}, use: {list(FORMAT_CLASS)}")
    return cls


class Statsguru:
    """Fetch and parse Statsguru HTML pages for player, team, and ground statistics."""

    def __init__(self, session: Session):
        self._s = session

    def _fetch_url(self, url: str) -> str:
        r = self._s.get(url)
        r.raise_for_status()
        return r.text

    def _player_url(
        self,
        player_id: Union[int, str],
        fmt: Format,
        stat_type: StatType,
        view: Optional[str] = None,
        filters: Optional[StatsFilter] = None,
    ) -> str:
        cls = _class_param(fmt)
        parts = f"class={cls};orderby=default;template=results;type={stat_type}"
        if view:
            parts += f";view={view}"
        parts += _build_filter_params(filters)
        return f"{_PLAYER_BASE}/{player_id}.html?{parts}"

    # ------------------------------------------------------------------
    # Player stats
    # ------------------------------------------------------------------

    def player_career_stats(
        self,
        player_id: Union[int, str],
        fmt: Format = "test",
        stat_type: StatType = "batting",
        filters: Optional[StatsFilter] = None,
    ) -> CareerStats:
        """Career summary + per-opposition breakdown.

        Returns {"summary": {...}, "breakdowns": [...]}.
        """
        html = self._fetch_url(
            self._player_url(player_id, fmt, stat_type, filters=filters)
        )
        return _summary_and_detail(_parse_tables(html), "breakdowns")

    def player_innings(
        self,
        player_id: Union[int, str],
        fmt: Format = "test",
        stat_type: StatType = "batting",
        filters: Optional[StatsFilter] = None,
    ) -> InningsList:
        """Innings-by-innings list.

        Returns {"summary": {...}, "innings": [...]}.
        """
        html = self._fetch_url(
            self._player_url(player_id, fmt, stat_type, view="innings", filters=filters)
        )
        return _summary_and_detail(_parse_tables(html), "innings")

    def player_match_list(
        self,
        player_id: Union[int, str],
        fmt: Format = "test",
        stat_type: StatType = "batting",
        filters: Optional[StatsFilter] = None,
    ) -> MatchList:
        """Match-by-match scores.

        Returns {"summary": {...}, "matches": [...]}.
        """
        html = self._fetch_url(
            self._player_url(player_id, fmt, stat_type, view="match", filters=filters)
        )
        return _summary_and_detail(_parse_tables(html), "matches")

    def player_series_list(
        self,
        player_id: Union[int, str],
        fmt: Format = "test",
        stat_type: StatType = "batting",
        filters: Optional[StatsFilter] = None,
    ) -> SeriesList:
        """Per-series averages.

        Returns {"summary": {...}, "series": [...]}.
        """
        html = self._fetch_url(
            self._player_url(player_id, fmt, stat_type, view="series", filters=filters)
        )
        return _summary_and_detail(_parse_tables(html), "series")

    def player_ground_stats(
        self,
        player_id: Union[int, str],
        fmt: Format = "test",
        stat_type: StatType = "batting",
        filters: Optional[StatsFilter] = None,
    ) -> GroundAverages:
        """Per-venue averages.

        Returns {"summary": {...}, "grounds": [...]}.
        """
        html = self._fetch_url(
            self._player_url(player_id, fmt, stat_type, view="ground", filters=filters)
        )
        return _summary_and_detail(_parse_tables(html), "grounds")

    # ------------------------------------------------------------------
    # Team stats
    # ------------------------------------------------------------------

    def team_career_stats(
        self,
        team_id: Union[int, str],
        fmt: Format = "test",
    ) -> CareerStats:
        """Team W/L/D record with per-opposition breakdown.

        Returns {"summary": {...}, "breakdowns": [...]}.
        """
        cls = _class_param(fmt)
        url = f"{_TEAM_BASE}/{team_id}.html?class={cls};orderby=default;template=results;type=team"
        html = self._fetch_url(url)
        return _summary_and_detail(_parse_tables(html), "breakdowns")

    def team_match_list(
        self,
        team_id: Union[int, str],
        fmt: Format = "test",
    ) -> MatchList:
        """Team match-by-match results.

        Returns {"summary": {...}, "matches": [...]}.
        """
        cls = _class_param(fmt)
        url = f"{_TEAM_BASE}/{team_id}.html?class={cls};orderby=default;template=results;type=team;view=results"
        html = self._fetch_url(url)
        return _summary_and_detail(_parse_tables(html), "matches")

    # ------------------------------------------------------------------
    # Ground stats
    # ------------------------------------------------------------------

    def ground_stats(
        self,
        ground_id: Union[int, str],
        fmt: Format = "test",
    ) -> CareerStats:
        """Venue stats: average score, W/L, RPO by team.

        Returns {"summary": {...}, "breakdowns": [...]}.
        """
        cls = _class_param(fmt)
        url = f"{_GROUND_BASE}/{ground_id}.html?class={cls};orderby=default;template=results;type=team"
        html = self._fetch_url(url)
        return _summary_and_detail(_parse_tables(html), "breakdowns")


class AsyncStatsguru:
    """Async variant of Statsguru — mirrors every Statsguru method."""

    def __init__(self, session: AsyncSession):
        self._s = session

    async def _fetch_url(self, url: str) -> str:
        r = await self._s.get(url)
        r.raise_for_status()
        return r.text

    def _player_url(
        self,
        player_id: Union[int, str],
        fmt: Format,
        stat_type: StatType,
        view: Optional[str] = None,
        filters: Optional[StatsFilter] = None,
    ) -> str:
        cls = _class_param(fmt)
        parts = f"class={cls};orderby=default;template=results;type={stat_type}"
        if view:
            parts += f";view={view}"
        parts += _build_filter_params(filters)
        return f"{_PLAYER_BASE}/{player_id}.html?{parts}"

    async def player_career_stats(
        self,
        player_id: Union[int, str],
        fmt: Format = "test",
        stat_type: StatType = "batting",
        filters: Optional[StatsFilter] = None,
    ) -> CareerStats:
        html = await self._fetch_url(
            self._player_url(player_id, fmt, stat_type, filters=filters)
        )
        return _summary_and_detail(_parse_tables(html), "breakdowns")

    async def player_innings(
        self,
        player_id: Union[int, str],
        fmt: Format = "test",
        stat_type: StatType = "batting",
        filters: Optional[StatsFilter] = None,
    ) -> InningsList:
        html = await self._fetch_url(
            self._player_url(player_id, fmt, stat_type, view="innings", filters=filters)
        )
        return _summary_and_detail(_parse_tables(html), "innings")

    async def player_match_list(
        self,
        player_id: Union[int, str],
        fmt: Format = "test",
        stat_type: StatType = "batting",
        filters: Optional[StatsFilter] = None,
    ) -> MatchList:
        html = await self._fetch_url(
            self._player_url(player_id, fmt, stat_type, view="match", filters=filters)
        )
        return _summary_and_detail(_parse_tables(html), "matches")

    async def player_series_list(
        self,
        player_id: Union[int, str],
        fmt: Format = "test",
        stat_type: StatType = "batting",
        filters: Optional[StatsFilter] = None,
    ) -> SeriesList:
        html = await self._fetch_url(
            self._player_url(player_id, fmt, stat_type, view="series", filters=filters)
        )
        return _summary_and_detail(_parse_tables(html), "series")

    async def player_ground_stats(
        self,
        player_id: Union[int, str],
        fmt: Format = "test",
        stat_type: StatType = "batting",
        filters: Optional[StatsFilter] = None,
    ) -> GroundAverages:
        html = await self._fetch_url(
            self._player_url(player_id, fmt, stat_type, view="ground", filters=filters)
        )
        return _summary_and_detail(_parse_tables(html), "grounds")

    async def team_career_stats(
        self,
        team_id: Union[int, str],
        fmt: Format = "test",
    ) -> CareerStats:
        cls = _class_param(fmt)
        url = f"{_TEAM_BASE}/{team_id}.html?class={cls};orderby=default;template=results;type=team"
        html = await self._fetch_url(url)
        return _summary_and_detail(_parse_tables(html), "breakdowns")

    async def team_match_list(
        self,
        team_id: Union[int, str],
        fmt: Format = "test",
    ) -> MatchList:
        cls = _class_param(fmt)
        url = f"{_TEAM_BASE}/{team_id}.html?class={cls};orderby=default;template=results;type=team;view=results"
        html = await self._fetch_url(url)
        return _summary_and_detail(_parse_tables(html), "matches")

    async def ground_stats(
        self,
        ground_id: Union[int, str],
        fmt: Format = "test",
    ) -> CareerStats:
        cls = _class_param(fmt)
        url = f"{_GROUND_BASE}/{ground_id}.html?class={cls};orderby=default;template=results;type=team"
        html = await self._fetch_url(url)
        return _summary_and_detail(_parse_tables(html), "breakdowns")
