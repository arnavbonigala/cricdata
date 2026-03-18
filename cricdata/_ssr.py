"""Cricinfo SSR page fetcher — extracts __NEXT_DATA__ JSON from server-rendered pages."""

from __future__ import annotations

import json
import re
from typing import Dict, List, Tuple

from ._session import AsyncSession, Session

_NEXT_DATA_RE = re.compile(
    r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>'
)

_BASE = "https://www.espncricinfo.com"
_GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

_ARCHIVE_HOURLY_VARS = (
    "temperature_2m,relative_humidity_2m,precipitation,"
    "weather_code,wind_speed_10m,cloud_cover"
)

_TEAM_RANKING_PAGES = {
    "test": 211271,
    "odi": 211270,
    "t20i": 211274,
}


def _extract_page_data(text: str, url: str) -> dict:
    m = _NEXT_DATA_RE.search(text)
    if not m:
        raise ValueError(f"No __NEXT_DATA__ in {url}")
    return json.loads(m.group(1))["props"]["appPageProps"]["data"]


class SSR:
    """Fetch espncricinfo.com pages and extract embedded JSON data."""

    def __init__(self, session: Session):
        self._s = session
        self._scorecard_cache: Dict[Tuple[str, str], dict] = {}

    def _page_data(self, path: str) -> dict:
        url = f"{_BASE}{path}" if path.startswith("/") else path
        r = self._s.get(url)
        r.raise_for_status()
        return _extract_page_data(r.text, url)

    def _scorecard_data(self, series_slug: str, match_slug: str) -> dict:
        key = (series_slug, match_slug)
        if key not in self._scorecard_cache:
            self._scorecard_cache[key] = self._page_data(
                f"/series/{series_slug}/{match_slug}/full-scorecard"
            )
        return self._scorecard_cache[key]

    # ------------------------------------------------------------------
    # Matches — basic
    # ------------------------------------------------------------------

    def live_matches(self) -> List[dict]:
        data = self._page_data("/live-cricket-score")
        return data.get("content", {}).get("matches", [])

    def match_scorecard(self, series_slug: str, match_slug: str) -> dict:
        return self._scorecard_data(series_slug, match_slug)

    def match_commentary(self, series_slug: str, match_slug: str) -> dict:
        return self._page_data(
            f"/series/{series_slug}/{match_slug}/ball-by-ball-commentary"
        )

    # ------------------------------------------------------------------
    # Matches — detailed analytics
    # ------------------------------------------------------------------

    def match_ball_by_ball(self, series_slug: str, match_slug: str) -> List[List[dict]]:
        """Balls from the scorecard SSR, grouped by innings.

        NOTE: The SSR only populates ball-level detail for the most recent
        over of each innings.  For over-level aggregates (runs, wickets,
        run rate per over) across the full match use match_overs() instead.

        Each ball dict has: oversActual, ballNumber, batsmanRuns, totalRuns,
        isFour, isSix, isWicket, wagonX/Y/Zone, pitchLine, pitchLength,
        shotType, shotControl, batsmanPlayerId, bowlerPlayerId, predictions,
        timestamp.
        """
        data = self._scorecard_data(series_slug, match_slug)
        result = []
        for inn in data.get("content", {}).get("innings", []):
            balls = []
            for ov in inn.get("inningOvers", []):
                balls.extend(ov.get("balls", []))
            result.append(balls)
        return result

    def match_partnerships(self, series_slug: str, match_slug: str) -> List[List[dict]]:
        """Partnerships grouped by innings."""
        data = self._scorecard_data(series_slug, match_slug)
        return [
            inn.get("inningPartnerships", [])
            for inn in data.get("content", {}).get("innings", [])
        ]

    def match_fall_of_wickets(self, series_slug: str, match_slug: str) -> List[List[dict]]:
        """Fall of wickets grouped by innings."""
        data = self._scorecard_data(series_slug, match_slug)
        return [
            inn.get("inningFallOfWickets", [])
            for inn in data.get("content", {}).get("innings", [])
        ]

    def match_overs(self, series_slug: str, match_slug: str) -> List[List[dict]]:
        """Over-by-over progression grouped by innings (without nested balls).

        Each over dict has overNumber, overRuns, overWickets, overRunRate,
        requiredRunRate, requiredRuns, remainingBalls, predictions, bowlers.
        """
        data = self._scorecard_data(series_slug, match_slug)
        result = []
        for inn in data.get("content", {}).get("innings", []):
            overs = []
            for ov in inn.get("inningOvers", []):
                ov_copy = {k: v for k, v in ov.items() if k != "balls"}
                overs.append(ov_copy)
            result.append(overs)
        return result

    def match_info(self, series_slug: str, match_slug: str) -> dict:
        """Match-level metadata: toss, venue, weather, awards, phase stats.

        Returns dict with keys: match, toss, venue, weather, player_awards,
        over_groups (powerplay/middle/death phase aggregates per innings).
        """
        data = self._scorecard_data(series_slug, match_slug)
        match = data.get("match", {})
        content = data.get("content", {})
        support = content.get("supportInfo") or {}

        teams_by_id = {}
        for inn in content.get("innings", []):
            team = inn.get("team", {})
            if team.get("id"):
                teams_by_id[team["id"]] = team

        toss_winner_id = match.get("tossWinnerTeamId")
        toss_choice_map = {1: "bat", 2: "field"}

        return {
            "match": match,
            "time": {
                "startDate": match.get("startDate"),
                "startTime": match.get("startTime"),
                "endDate": match.get("endDate"),
                "endTime": match.get("endTime"),
                "daysInfo": match.get("daysInfo"),
                "hoursInfo": match.get("hoursInfo"),
                "scheduledDays": match.get("scheduledDays"),
                "scheduledOvers": match.get("scheduledOvers"),
                "floodlit": match.get("floodlit"),
                "dayType": match.get("dayType"),
            },
            "toss": {
                "winner_team_id": toss_winner_id,
                "winner_team": teams_by_id.get(toss_winner_id, {}).get("longName"),
                "decision": toss_choice_map.get(match.get("tossWinnerChoice")),
            },
            "venue": match.get("ground", {}),
            "weather": support.get("weather"),
            "player_awards": content.get("matchPlayerAwards", []),
            "over_groups": [
                inn.get("inningOverGroups", [])
                for inn in content.get("innings", [])
            ],
        }

    def match_weather(self, series_slug: str, match_slug: str) -> dict | None:
        """Weather for a match. Uses ESPNCricinfo when available, otherwise
        falls back to Open-Meteo historical data (free, no key required).

        Returns dict with a ``source`` key (``"espncricinfo"`` or
        ``"open-meteo"``) so callers know which schema to expect, or
        ``None`` when weather cannot be resolved.
        """
        data = self._scorecard_data(series_slug, match_slug)
        match = data.get("match", {})
        support = (data.get("content", {}).get("supportInfo") or {})

        espn = support.get("weather")
        if espn:
            return {"source": "espncricinfo", **espn}

        return self._open_meteo_weather(match)

    def _open_meteo_weather(self, match: dict) -> dict | None:
        town = match.get("ground", {}).get("town", {})
        town_name = town.get("name")
        if not town_name:
            return None

        r = self._s.get(_GEOCODE_URL, params={"name": town_name, "count": 1})
        r.raise_for_status()
        results = r.json().get("results")
        if not results:
            return None

        lat, lon = results[0]["latitude"], results[0]["longitude"]
        start = (match.get("startDate") or "")[:10]
        end = (match.get("endDate") or start)[:10]
        if not start:
            return None

        r = self._s.get(
            _ARCHIVE_URL,
            params={
                "latitude": lat,
                "longitude": lon,
                "start_date": start,
                "end_date": end,
                "hourly": _ARCHIVE_HOURLY_VARS,
                "timezone": town.get("timezone", "UTC"),
            },
        )
        if not r.ok:
            return None
        body = r.json()
        return {
            "source": "open-meteo",
            "latitude": body.get("latitude"),
            "longitude": body.get("longitude"),
            "timezone": body.get("timezone"),
            "hourly_units": body.get("hourly_units"),
            "hourly": body.get("hourly"),
        }

    # ------------------------------------------------------------------
    # Series
    # ------------------------------------------------------------------

    def series(self, slug: str) -> dict:
        return self._page_data(f"/series/{slug}")

    def series_matches(self, slug: str) -> dict:
        return self._page_data(f"/series/{slug}/match-results")

    def series_standings(self, slug: str) -> dict:
        return self._page_data(f"/series/{slug}/points-table-standings")

    def series_stats(self, slug: str) -> dict:
        return self._page_data(f"/series/{slug}/stats")

    def series_squads(self, slug: str) -> dict:
        return self._page_data(f"/series/{slug}/squads")

    def series_fixtures(self, slug: str) -> dict:
        return self._page_data(f"/series/{slug}/match-schedule-fixtures")

    # ------------------------------------------------------------------
    # Teams & Rankings
    # ------------------------------------------------------------------

    def team(self, slug: str) -> dict:
        return self._page_data(f"/team/{slug}")

    def team_rankings(self, fmt: str) -> List[dict]:
        page_id = _TEAM_RANKING_PAGES.get(fmt)
        if page_id is None:
            raise ValueError(f"Unknown format {fmt!r}, use: {list(_TEAM_RANKING_PAGES)}")
        data = self._page_data(f"/rankings/content/page/{page_id}.html")
        return data.get("content", {}).get("rankings", [])


class AsyncSSR:
    """Async variant of SSR — mirrors every SSR method."""

    def __init__(self, session: AsyncSession):
        self._s = session

    async def _page_data(self, path: str) -> dict:
        url = f"{_BASE}{path}" if path.startswith("/") else path
        r = await self._s.get(url)
        r.raise_for_status()
        return _extract_page_data(r.text, url)

    async def _scorecard_data(self, series_slug: str, match_slug: str) -> dict:
        return await self._page_data(
            f"/series/{series_slug}/{match_slug}/full-scorecard"
        )

    # Matches — basic

    async def live_matches(self) -> List[dict]:
        data = await self._page_data("/live-cricket-score")
        return data.get("content", {}).get("matches", [])

    async def match_scorecard(self, series_slug: str, match_slug: str) -> dict:
        return await self._scorecard_data(series_slug, match_slug)

    async def match_commentary(self, series_slug: str, match_slug: str) -> dict:
        return await self._page_data(
            f"/series/{series_slug}/{match_slug}/ball-by-ball-commentary"
        )

    # Matches — detailed analytics

    async def match_ball_by_ball(self, series_slug: str, match_slug: str) -> List[List[dict]]:
        data = await self._scorecard_data(series_slug, match_slug)
        result = []
        for inn in data.get("content", {}).get("innings", []):
            balls = []
            for ov in inn.get("inningOvers", []):
                balls.extend(ov.get("balls", []))
            result.append(balls)
        return result

    async def match_partnerships(self, series_slug: str, match_slug: str) -> List[List[dict]]:
        data = await self._scorecard_data(series_slug, match_slug)
        return [
            inn.get("inningPartnerships", [])
            for inn in data.get("content", {}).get("innings", [])
        ]

    async def match_fall_of_wickets(self, series_slug: str, match_slug: str) -> List[List[dict]]:
        data = await self._scorecard_data(series_slug, match_slug)
        return [
            inn.get("inningFallOfWickets", [])
            for inn in data.get("content", {}).get("innings", [])
        ]

    async def match_overs(self, series_slug: str, match_slug: str) -> List[List[dict]]:
        data = await self._scorecard_data(series_slug, match_slug)
        result = []
        for inn in data.get("content", {}).get("innings", []):
            overs = []
            for ov in inn.get("inningOvers", []):
                ov_copy = {k: v for k, v in ov.items() if k != "balls"}
                overs.append(ov_copy)
            result.append(overs)
        return result

    async def match_info(self, series_slug: str, match_slug: str) -> dict:
        data = await self._scorecard_data(series_slug, match_slug)
        match = data.get("match", {})
        content = data.get("content", {})
        support = content.get("supportInfo") or {}

        teams_by_id = {}
        for inn in content.get("innings", []):
            team = inn.get("team", {})
            if team.get("id"):
                teams_by_id[team["id"]] = team

        toss_winner_id = match.get("tossWinnerTeamId")
        toss_choice_map = {1: "bat", 2: "field"}

        return {
            "match": match,
            "time": {
                "startDate": match.get("startDate"),
                "startTime": match.get("startTime"),
                "endDate": match.get("endDate"),
                "endTime": match.get("endTime"),
                "daysInfo": match.get("daysInfo"),
                "hoursInfo": match.get("hoursInfo"),
                "scheduledDays": match.get("scheduledDays"),
                "scheduledOvers": match.get("scheduledOvers"),
                "floodlit": match.get("floodlit"),
                "dayType": match.get("dayType"),
            },
            "toss": {
                "winner_team_id": toss_winner_id,
                "winner_team": teams_by_id.get(toss_winner_id, {}).get("longName"),
                "decision": toss_choice_map.get(match.get("tossWinnerChoice")),
            },
            "venue": match.get("ground", {}),
            "weather": support.get("weather"),
            "player_awards": content.get("matchPlayerAwards", []),
            "over_groups": [
                inn.get("inningOverGroups", [])
                for inn in content.get("innings", [])
            ],
        }

    async def match_weather(self, series_slug: str, match_slug: str) -> dict | None:
        data = await self._scorecard_data(series_slug, match_slug)
        match = data.get("match", {})
        support = (data.get("content", {}).get("supportInfo") or {})

        espn = support.get("weather")
        if espn:
            return {"source": "espncricinfo", **espn}

        return await self._open_meteo_weather(match)

    async def _open_meteo_weather(self, match: dict) -> dict | None:
        town = match.get("ground", {}).get("town", {})
        town_name = town.get("name")
        if not town_name:
            return None

        r = await self._s.get(_GEOCODE_URL, params={"name": town_name, "count": 1})
        r.raise_for_status()
        results = r.json().get("results")
        if not results:
            return None

        lat, lon = results[0]["latitude"], results[0]["longitude"]
        start = (match.get("startDate") or "")[:10]
        end = (match.get("endDate") or start)[:10]
        if not start:
            return None

        r = await self._s.get(
            _ARCHIVE_URL,
            params={
                "latitude": lat,
                "longitude": lon,
                "start_date": start,
                "end_date": end,
                "hourly": _ARCHIVE_HOURLY_VARS,
                "timezone": town.get("timezone", "UTC"),
            },
        )
        if not r.ok:
            return None
        body = r.json()
        return {
            "source": "open-meteo",
            "latitude": body.get("latitude"),
            "longitude": body.get("longitude"),
            "timezone": body.get("timezone"),
            "hourly_units": body.get("hourly_units"),
            "hourly": body.get("hourly"),
        }

    # Series

    async def series(self, slug: str) -> dict:
        return await self._page_data(f"/series/{slug}")

    async def series_matches(self, slug: str) -> dict:
        return await self._page_data(f"/series/{slug}/match-results")

    async def series_standings(self, slug: str) -> dict:
        return await self._page_data(f"/series/{slug}/points-table-standings")

    async def series_stats(self, slug: str) -> dict:
        return await self._page_data(f"/series/{slug}/stats")

    async def series_squads(self, slug: str) -> dict:
        return await self._page_data(f"/series/{slug}/squads")

    async def series_fixtures(self, slug: str) -> dict:
        return await self._page_data(f"/series/{slug}/match-schedule-fixtures")

    # Teams & Rankings

    async def team(self, slug: str) -> dict:
        return await self._page_data(f"/team/{slug}")

    async def team_rankings(self, fmt: str) -> List[dict]:
        page_id = _TEAM_RANKING_PAGES.get(fmt)
        if page_id is None:
            raise ValueError(f"Unknown format {fmt!r}, use: {list(_TEAM_RANKING_PAGES)}")
        data = await self._page_data(f"/rankings/content/page/{page_id}.html")
        return data.get("content", {}).get("rankings", [])
