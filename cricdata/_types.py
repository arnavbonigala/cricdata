"""Public type definitions for cricdata."""

from __future__ import annotations

from typing import Any, Literal, TypedDict, Union

Format = Literal["test", "odi", "t20i", "fc", "lista", "t20"]
RankingFormat = Literal["test", "odi", "t20i"]
StatType = Literal["batting", "bowling", "fielding", "allround"]

StatsRow = dict[str, str]


class StatsFilter(TypedDict, total=False):
    opposition: Union[int, str]
    home_or_away: Union[int, str]
    start_date: str
    end_date: str
    ground: Union[int, str]


# ------------------------------------------------------------------
# Statsguru result shapes
# ------------------------------------------------------------------


class CareerStats(TypedDict):
    summary: StatsRow
    breakdowns: list[StatsRow]


class InningsList(TypedDict):
    summary: StatsRow
    innings: list[StatsRow]


class MatchList(TypedDict):
    summary: StatsRow
    matches: list[StatsRow]


class SeriesList(TypedDict):
    summary: StatsRow
    series: list[StatsRow]


class GroundAverages(TypedDict):
    summary: StatsRow
    grounds: list[StatsRow]


# ------------------------------------------------------------------
# ESPN — player search & bio
# ------------------------------------------------------------------


class PlayerSearchResult(TypedDict, total=False):
    id: str
    uuid: str
    guid: str
    displayName: str
    shortName: str
    type: str
    sport: str
    teamRelationships: list[dict[str, Any]]
    relevance: str
    isActive: bool
    isRetired: bool
    defaultLeagueSlug: str
    label: str
    uid: str
    headshot: dict[str, Any]
    links: list[dict[str, Any]]
    flag: dict[str, Any]


class PlayerBio(TypedDict, total=False):
    id: str
    uid: str
    guid: str
    type: str
    firstName: str
    lastName: str
    displayName: str
    fullName: str
    shortName: str
    links: list[dict[str, Any]]
    headshot: dict[str, Any]
    position: dict[str, Any]
    team: dict[str, Any]
    active: bool
    displayDOB: str
    age: int
    gender: str
    flag: dict[str, Any]
    batStyle: list[dict[str, str]]
    bowlStyle: list[dict[str, str]]


# ------------------------------------------------------------------
# ESPN — ball-by-ball
# ------------------------------------------------------------------


class PlayType(TypedDict):
    id: str
    description: str


class BallTeam(TypedDict):
    id: str
    name: str
    abbreviation: str
    displayName: str


class Athlete(TypedDict, total=False):
    id: str
    name: str
    shortName: str
    fullName: str
    displayName: str


class BatsmanState(TypedDict, total=False):
    athlete: Athlete
    team: BallTeam
    totalRuns: int
    faced: int
    fours: int
    runs: int
    sixes: int


class BowlerState(TypedDict, total=False):
    athlete: Athlete
    team: BallTeam
    maidens: int
    balls: int
    wickets: int
    overs: float
    conceded: int


class BallOver(TypedDict, total=False):
    ball: int
    balls: int
    complete: bool
    limit: float
    maiden: int
    noBall: int
    wide: int
    legByes: int
    byes: int
    number: int
    runs: int
    wickets: int
    overs: float
    actual: float
    unique: float


class BallInnings(TypedDict, total=False):
    id: str
    runRate: float
    remainingBalls: int
    byes: int
    number: int
    balls: int
    noBalls: int
    wickets: int
    legByes: int
    ballLimit: int
    target: int
    session: int


class Dismissal(TypedDict, total=False):
    dismissal: bool
    bowled: bool
    type: str
    bowler: dict[str, Any]
    batsman: dict[str, Any]
    fielders: list[dict[str, Any]]


class BallItem(TypedDict, total=False):
    id: str
    clock: str
    date: str
    playType: PlayType
    team: BallTeam
    mediaId: int
    period: int
    periodText: str
    preText: str
    text: str
    postText: str
    shortText: str
    homeScore: str
    awayScore: str
    scoreValue: int
    sequence: int
    athletesInvolved: list[Athlete]
    bowler: BowlerState
    otherBowler: BowlerState
    batsman: BatsmanState
    otherBatsman: BatsmanState
    innings: BallInnings
    over: BallOver
    dismissal: Dismissal
    bbbTimestamp: int


# ------------------------------------------------------------------
# SSR — match overs, partnerships, fall of wickets
# ------------------------------------------------------------------


class OverPredictions(TypedDict, total=False):
    score: int
    winProbability: float


class OverSummary(TypedDict, total=False):
    overNumber: int
    overRuns: int
    overWickets: int
    isComplete: bool
    totalBalls: int
    totalRuns: int
    totalWickets: int
    overRunRate: float
    bowlers: list[dict[str, Any]]
    requiredRunRate: float
    requiredRuns: int
    remainingBalls: int
    predictions: OverPredictions
    events: list[dict[str, Any]]


class PartnershipEnd(TypedDict, total=False):
    oversActual: float
    ballsActual: int | None
    totalInningRuns: int
    totalInningWickets: int


class Partnership(TypedDict, total=False):
    player1: dict[str, Any]
    player2: dict[str, Any]
    outPlayerId: int
    player1Runs: int
    player1Balls: int
    player2Runs: int
    player2Balls: int
    runs: int
    balls: int
    overs: float
    start: PartnershipEnd | None
    end: PartnershipEnd | None
    isLive: bool


class FallOfWicket(TypedDict, total=False):
    dismissalBatsman: dict[str, Any]
    fowType: int
    fowOrder: int
    fowWicketNum: int
    fowRuns: int
    fowOvers: float
    fowBalls: int | None


# ------------------------------------------------------------------
# SSR — match info sub-types
# ------------------------------------------------------------------


class MatchTime(TypedDict):
    startDate: Any
    startTime: Any
    endDate: Any
    endTime: Any
    daysInfo: Any
    hoursInfo: Any
    scheduledDays: Any
    scheduledOvers: Any
    floodlit: Any
    dayType: Any


class Toss(TypedDict):
    winner_team_id: int | None
    winner_team: str | None
    decision: str | None


class Captain(TypedDict):
    player_id: int | None
    player_object_id: int | None
    name: str | None
    slug: str | None
    team_id: int | None
    team_name: str | None


class MatchInfo(TypedDict):
    match: dict[str, Any]
    time: MatchTime
    toss: Toss
    venue: dict[str, Any]
    captains: list[Captain]
    weather: Any
    player_awards: list[dict[str, Any]]
    over_groups: list[list[dict[str, Any]]]


# ------------------------------------------------------------------
# SSR — weather
# ------------------------------------------------------------------


class OpenMeteoWeather(TypedDict):
    source: Literal["open-meteo"]
    latitude: float | None
    longitude: float | None
    timezone: str | None
    hourly_units: dict[str, str] | None
    hourly: dict[str, list[Any]] | None


class EspnWeather(TypedDict, total=False):
    source: str


WeatherResult = Union[OpenMeteoWeather, EspnWeather]


# ------------------------------------------------------------------
# SSR — page data (top-level shapes returned by SSR pages)
# ------------------------------------------------------------------


class ScorecardData(TypedDict):
    match: dict[str, Any]
    content: dict[str, Any]


class CommentaryData(TypedDict):
    match: dict[str, Any]
    content: dict[str, Any]


class SeriesPageData(TypedDict):
    series: dict[str, Any]
    content: dict[str, Any]


class TeamPageData(TypedDict):
    data: dict[str, Any]
    recordClassMetas: list[dict[str, Any]]


class StandingsData(TypedDict, total=False):
    data: dict[str, Any]
    isExternalSource: bool


# ------------------------------------------------------------------
# SSR — rankings
# ------------------------------------------------------------------


class RankingTeam(TypedDict, total=False):
    rank: int
    rating: float
    points: int
    matches: int
    team: dict[str, Any]


class RankingGroup(TypedDict, total=False):
    teams: list[RankingTeam]
    matchClassMeta: dict[str, Any]
    modified: str
