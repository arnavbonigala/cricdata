"""Statsguru HTML table parser — player, team, and ground statistics."""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Union

from ._session import Session

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


def _summary_and_detail(tables: List[List[List[str]]], detail_key: str) -> dict:
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
        fmt: str,
        stat_type: str,
        view: Optional[str] = None,
        filters: Optional[Dict[str, Union[str, int]]] = None,
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
        fmt: str = "test",
        stat_type: str = "batting",
        filters: Optional[Dict[str, Union[str, int]]] = None,
    ) -> dict:
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
        fmt: str = "test",
        stat_type: str = "batting",
        filters: Optional[Dict[str, Union[str, int]]] = None,
    ) -> dict:
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
        fmt: str = "test",
        stat_type: str = "batting",
        filters: Optional[Dict[str, Union[str, int]]] = None,
    ) -> dict:
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
        fmt: str = "test",
        stat_type: str = "batting",
        filters: Optional[Dict[str, Union[str, int]]] = None,
    ) -> dict:
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
        fmt: str = "test",
        stat_type: str = "batting",
        filters: Optional[Dict[str, Union[str, int]]] = None,
    ) -> dict:
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
        fmt: str = "test",
    ) -> dict:
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
        fmt: str = "test",
    ) -> dict:
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
        fmt: str = "test",
    ) -> dict:
        """Venue stats: average score, W/L, RPO by team.

        Returns {"summary": {...}, "breakdowns": [...]}.
        """
        cls = _class_param(fmt)
        url = f"{_GROUND_BASE}/{ground_id}.html?class={cls};orderby=default;template=results;type=team"
        html = self._fetch_url(url)
        return _summary_and_detail(_parse_tables(html), "breakdowns")
