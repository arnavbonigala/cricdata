"""Public API — CricinfoClient composes SSR, ESPN, and Statsguru sources."""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Union

from ._espn import AsyncESPN, ESPN
from ._session import AsyncSession, Session
from ._ssr import AsyncSSR, SSR
from ._statsguru import AsyncStatsguru, Statsguru

_TRAILING_ID_RE = re.compile(r"-(\d+)$")


class CricinfoClient:
    """Unified client for cricket data from ESPNCricinfo.

    Combines three backends:
      - Cricinfo SSR: matches, series, scorecards, teams, rankings
      - ESPN open API: player search and bio
      - Statsguru: player career statistics (opt-in, slower)
    """

    def __init__(self, impersonate: str = "chrome", timeout: int = 30):
        self._session = Session(impersonate=impersonate, timeout=timeout)
        self._ssr = SSR(self._session)
        self._espn = ESPN(self._session)
        self._statsguru = Statsguru(self._session)

    @staticmethod
    def _extract_match_id(match_id: Union[int, str]) -> Union[int, str]:
        """Return a numeric match ID from an int, numeric string, or slug."""
        if isinstance(match_id, int):
            return match_id
        m = _TRAILING_ID_RE.search(str(match_id))
        return int(m.group(1)) if m else match_id

    # ------------------------------------------------------------------
    # Matches — basic
    # ------------------------------------------------------------------

    def live_matches(self) -> List[dict]:
        """All currently live / recent matches."""
        return self._ssr.live_matches()

    def match_scorecard(self, series_slug: str, match_slug: str) -> dict:
        """Full scorecard for a match (innings, batsmen, bowlers, FOW)."""
        return self._ssr.match_scorecard(series_slug, match_slug)

    def match_commentary(self, series_slug: str, match_slug: str) -> dict:
        """Ball-by-ball commentary for a match."""
        return self._ssr.match_commentary(series_slug, match_slug)

    # ------------------------------------------------------------------
    # Matches — detailed analytics
    # ------------------------------------------------------------------

    def match_ball_by_ball(self, series_slug: str, match_slug: str) -> List[List[dict]]:
        """Full ball-by-ball for a match, grouped by innings.

        Each ball dict includes: playType, text, shortText, scoreValue,
        batsman, bowler, over, innings, dismissal, team, athletesInvolved,
        and cumulative innings/over state.
        """
        mid = self._extract_match_id(match_slug)
        return self._espn.match_ball_by_ball(mid)

    def match_partnerships(self, series_slug: str, match_slug: str) -> List[List[dict]]:
        """Partnerships grouped by innings."""
        return self._ssr.match_partnerships(series_slug, match_slug)

    def match_fall_of_wickets(self, series_slug: str, match_slug: str) -> List[List[dict]]:
        """Fall of wickets grouped by innings."""
        return self._ssr.match_fall_of_wickets(series_slug, match_slug)

    def match_overs(self, series_slug: str, match_slug: str) -> List[List[dict]]:
        """Over-by-over progression grouped by innings.

        Each over dict has overNumber, overRuns, overWickets, overRunRate,
        requiredRunRate, requiredRuns, remainingBalls, predictions, bowlers.
        """
        return self._ssr.match_overs(series_slug, match_slug)

    def match_info(self, series_slug: str, match_slug: str) -> dict:
        """Match-level metadata: toss, venue, weather, awards, phase stats."""
        return self._ssr.match_info(series_slug, match_slug)

    def match_weather(self, series_slug: str, match_slug: str) -> dict | None:
        """Weather conditions for a match.

        Returns ESPNCricinfo weather for live matches or Open-Meteo
        historical data for completed matches.  The returned dict
        contains a ``source`` key (``"espncricinfo"`` or ``"open-meteo"``).
        Returns ``None`` when weather cannot be resolved.
        """
        return self._ssr.match_weather(series_slug, match_slug)

    # ------------------------------------------------------------------
    # Series
    # ------------------------------------------------------------------

    def series(self, slug: str) -> dict:
        """Series metadata and content feed."""
        return self._ssr.series(slug)

    def series_matches(self, slug: str) -> dict:
        """Completed match results for a series."""
        return self._ssr.series_matches(slug)

    def series_standings(self, slug: str) -> dict:
        """Points table / standings."""
        return self._ssr.series_standings(slug)

    def series_stats(self, slug: str) -> dict:
        """Top batsmen, bowlers, and smart stats for a series."""
        return self._ssr.series_stats(slug)

    def series_squads(self, slug: str) -> dict:
        """All team squads with player bios for a series."""
        return self._ssr.series_squads(slug)

    def series_fixtures(self, slug: str) -> dict:
        """Match schedule / upcoming fixtures for a series."""
        return self._ssr.series_fixtures(slug)

    # ------------------------------------------------------------------
    # Teams
    # ------------------------------------------------------------------

    def team(self, slug: str) -> dict:
        """Team info, recent results, squads, top performers."""
        return self._ssr.team(slug)

    def team_career_stats(
        self,
        team_id: Union[int, str],
        fmt: str = "test",
    ) -> dict:
        """Team W/L/D record with per-opposition breakdown from Statsguru."""
        return self._statsguru.team_career_stats(team_id, fmt)

    def team_match_list(
        self,
        team_id: Union[int, str],
        fmt: str = "test",
    ) -> dict:
        """Team match-by-match results from Statsguru."""
        return self._statsguru.team_match_list(team_id, fmt)

    # ------------------------------------------------------------------
    # Players
    # ------------------------------------------------------------------

    def search_players(self, query: str, limit: int = 10) -> List[dict]:
        """Search for players by name. Returns list with id, displayName, etc."""
        return self._espn.search_players(query, limit=limit)

    def player_bio(self, player_id: Union[int, str]) -> dict:
        """Player bio: name, DOB, age, bat/bowl style, position, team, headshot."""
        return self._espn.player_bio(player_id)

    def player_career_stats(
        self,
        player_id: Union[int, str],
        fmt: str = "test",
        stat_type: str = "batting",
        filters: Optional[Dict[str, Union[str, int]]] = None,
    ) -> dict:
        """Career averages + per-opposition breakdowns from Statsguru.

        fmt: test, odi, t20i, fc, lista, t20
        stat_type: batting, bowling, fielding, allround
        filters: optional dict with keys opposition, home_or_away,
                 start_date, end_date, ground
        """
        return self._statsguru.player_career_stats(player_id, fmt, stat_type, filters)

    def player_innings(
        self,
        player_id: Union[int, str],
        fmt: str = "test",
        stat_type: str = "batting",
        filters: Optional[Dict[str, Union[str, int]]] = None,
    ) -> dict:
        """Innings-by-innings match history from Statsguru."""
        return self._statsguru.player_innings(player_id, fmt, stat_type, filters)

    def player_match_list(
        self,
        player_id: Union[int, str],
        fmt: str = "test",
        stat_type: str = "batting",
        filters: Optional[Dict[str, Union[str, int]]] = None,
    ) -> dict:
        """Match-by-match scores from Statsguru."""
        return self._statsguru.player_match_list(player_id, fmt, stat_type, filters)

    def player_series_list(
        self,
        player_id: Union[int, str],
        fmt: str = "test",
        stat_type: str = "batting",
        filters: Optional[Dict[str, Union[str, int]]] = None,
    ) -> dict:
        """Per-series averages from Statsguru."""
        return self._statsguru.player_series_list(player_id, fmt, stat_type, filters)

    def player_ground_stats(
        self,
        player_id: Union[int, str],
        fmt: str = "test",
        stat_type: str = "batting",
        filters: Optional[Dict[str, Union[str, int]]] = None,
    ) -> dict:
        """Per-venue averages from Statsguru."""
        return self._statsguru.player_ground_stats(player_id, fmt, stat_type, filters)

    # ------------------------------------------------------------------
    # Grounds
    # ------------------------------------------------------------------

    def ground_stats(
        self,
        ground_id: Union[int, str],
        fmt: str = "test",
    ) -> dict:
        """Venue stats: average score, W/L, RPO by team from Statsguru."""
        return self._statsguru.ground_stats(ground_id, fmt)

    # ------------------------------------------------------------------
    # Rankings
    # ------------------------------------------------------------------

    def team_rankings(self, fmt: str = "test") -> List[dict]:
        """ICC team rankings (test, odi, or t20i)."""
        return self._ssr.team_rankings(fmt)


class AsyncCricinfoClient:
    """Async mirror of CricinfoClient for concurrent data fetching.

    Use as an async context manager to ensure proper cleanup.
    """

    def __init__(self, impersonate: str = "chrome", timeout: int = 30):
        self._session = AsyncSession(impersonate=impersonate, timeout=timeout)
        self._ssr = AsyncSSR(self._session)
        self._espn = AsyncESPN(self._session)
        self._statsguru = AsyncStatsguru(self._session)

    @staticmethod
    def _extract_match_id(match_id: Union[int, str]) -> Union[int, str]:
        if isinstance(match_id, int):
            return match_id
        m = _TRAILING_ID_RE.search(str(match_id))
        return int(m.group(1)) if m else match_id

    # ------------------------------------------------------------------
    # Matches — basic
    # ------------------------------------------------------------------

    async def live_matches(self) -> List[dict]:
        return await self._ssr.live_matches()

    async def match_scorecard(self, series_slug: str, match_slug: str) -> dict:
        return await self._ssr.match_scorecard(series_slug, match_slug)

    async def match_commentary(self, series_slug: str, match_slug: str) -> dict:
        return await self._ssr.match_commentary(series_slug, match_slug)

    # ------------------------------------------------------------------
    # Matches — detailed analytics
    # ------------------------------------------------------------------

    async def match_ball_by_ball(self, series_slug: str, match_slug: str) -> List[List[dict]]:
        mid = self._extract_match_id(match_slug)
        return await self._espn.match_ball_by_ball(mid)

    async def match_partnerships(self, series_slug: str, match_slug: str) -> List[List[dict]]:
        return await self._ssr.match_partnerships(series_slug, match_slug)

    async def match_fall_of_wickets(self, series_slug: str, match_slug: str) -> List[List[dict]]:
        return await self._ssr.match_fall_of_wickets(series_slug, match_slug)

    async def match_overs(self, series_slug: str, match_slug: str) -> List[List[dict]]:
        return await self._ssr.match_overs(series_slug, match_slug)

    async def match_info(self, series_slug: str, match_slug: str) -> dict:
        return await self._ssr.match_info(series_slug, match_slug)

    async def match_weather(self, series_slug: str, match_slug: str) -> dict | None:
        return await self._ssr.match_weather(series_slug, match_slug)

    # ------------------------------------------------------------------
    # Series
    # ------------------------------------------------------------------

    async def series(self, slug: str) -> dict:
        return await self._ssr.series(slug)

    async def series_matches(self, slug: str) -> dict:
        return await self._ssr.series_matches(slug)

    async def series_standings(self, slug: str) -> dict:
        return await self._ssr.series_standings(slug)

    async def series_stats(self, slug: str) -> dict:
        return await self._ssr.series_stats(slug)

    async def series_squads(self, slug: str) -> dict:
        return await self._ssr.series_squads(slug)

    async def series_fixtures(self, slug: str) -> dict:
        return await self._ssr.series_fixtures(slug)

    # ------------------------------------------------------------------
    # Teams
    # ------------------------------------------------------------------

    async def team(self, slug: str) -> dict:
        return await self._ssr.team(slug)

    async def team_career_stats(
        self,
        team_id: Union[int, str],
        fmt: str = "test",
    ) -> dict:
        return await self._statsguru.team_career_stats(team_id, fmt)

    async def team_match_list(
        self,
        team_id: Union[int, str],
        fmt: str = "test",
    ) -> dict:
        return await self._statsguru.team_match_list(team_id, fmt)

    # ------------------------------------------------------------------
    # Players
    # ------------------------------------------------------------------

    async def search_players(self, query: str, limit: int = 10) -> List[dict]:
        return await self._espn.search_players(query, limit=limit)

    async def player_bio(self, player_id: Union[int, str]) -> dict:
        return await self._espn.player_bio(player_id)

    async def player_career_stats(
        self,
        player_id: Union[int, str],
        fmt: str = "test",
        stat_type: str = "batting",
        filters: Optional[Dict[str, Union[str, int]]] = None,
    ) -> dict:
        return await self._statsguru.player_career_stats(player_id, fmt, stat_type, filters)

    async def player_innings(
        self,
        player_id: Union[int, str],
        fmt: str = "test",
        stat_type: str = "batting",
        filters: Optional[Dict[str, Union[str, int]]] = None,
    ) -> dict:
        return await self._statsguru.player_innings(player_id, fmt, stat_type, filters)

    async def player_match_list(
        self,
        player_id: Union[int, str],
        fmt: str = "test",
        stat_type: str = "batting",
        filters: Optional[Dict[str, Union[str, int]]] = None,
    ) -> dict:
        return await self._statsguru.player_match_list(player_id, fmt, stat_type, filters)

    async def player_series_list(
        self,
        player_id: Union[int, str],
        fmt: str = "test",
        stat_type: str = "batting",
        filters: Optional[Dict[str, Union[str, int]]] = None,
    ) -> dict:
        return await self._statsguru.player_series_list(player_id, fmt, stat_type, filters)

    async def player_ground_stats(
        self,
        player_id: Union[int, str],
        fmt: str = "test",
        stat_type: str = "batting",
        filters: Optional[Dict[str, Union[str, int]]] = None,
    ) -> dict:
        return await self._statsguru.player_ground_stats(player_id, fmt, stat_type, filters)

    # ------------------------------------------------------------------
    # Grounds
    # ------------------------------------------------------------------

    async def ground_stats(
        self,
        ground_id: Union[int, str],
        fmt: str = "test",
    ) -> dict:
        return await self._statsguru.ground_stats(ground_id, fmt)

    # ------------------------------------------------------------------
    # Rankings
    # ------------------------------------------------------------------

    async def team_rankings(self, fmt: str = "test") -> List[dict]:
        return await self._ssr.team_rankings(fmt)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def aclose(self) -> None:
        await self._session.aclose()

    async def __aenter__(self) -> "AsyncCricinfoClient":
        return self

    async def __aexit__(self, *exc) -> None:
        await self.aclose()
