# cricdata

Unofficial Python client for retrieving cricket data from ESPNCricinfo. Designed for data analytics and machine learning pipelines.

Covers live scores, full scorecards, ball-by-ball data, player/team/ground statistics, series fixtures, and ICC rankings — all returned as typed Python objects (`TypedDict` subclasses for autocomplete and type-checker support, `py.typed` included).

> **Disclaimer** — This package is not affiliated with, endorsed by, or connected to ESPN or ESPNCricinfo. All data is retrieved from publicly accessible web pages and APIs.

## Installation

```bash
pip install cricdata
```

Requires Python 3.10+.

## Quick start

```python
from cricdata import CricinfoClient

ci = CricinfoClient()
```

### Discover matches from a series

```python
fixtures = ci.series_fixtures("ipl-2025-1449924")
matches = fixtures["content"]["matches"]

# Every match/series object contains the slugs needed for other calls
m = matches[0]
series_slug = f"{m['series']['slug']}-{m['series']['objectId']}"
match_slug = f"{m['slug']}-{m['objectId']}"
```

### Get full ball-by-ball data

```python
balls = ci.match_ball_by_ball(series_slug, match_slug)

for innings in balls:
    for ball in innings:
        print(
            ball["shortText"],
            ball["over"]["overs"],
            ball["scoreValue"],
        )
```

### Search for a player and pull their stats

```python
results = ci.search_players("Virat Kohli")
player_id = results[0]["id"]

bio = ci.player_bio(player_id)
print(bio["displayName"], bio["displayDOB"])

# Career batting averages in Tests
stats = ci.player_career_stats(player_id, fmt="test", stat_type="batting")
print(stats["summary"])  # {"Mat": "123", "Runs": "9230", "Ave": "46.85", ...}

# Filter: only innings in Australia since 2020
filtered = ci.player_innings(
    player_id,
    fmt="test",
    stat_type="batting",
    filters={"opposition": 2, "start_date": "01+Jan+2020"},
)
print(f"{len(filtered['innings'])} innings")
```

### Match detail in one scorecard fetch

```python
info = ci.match_info(series_slug, match_slug)
print(info["time"])        # {"startTime": "...", "hoursInfo": "...", ...}
print(info["toss"])        # {"winner_team": "...", "decision": "field"}
print(info["venue"])       # {"name": "Eden Gardens, Kolkata", ...}
print(info["captains"])    # [{"player_id": 51096, "name": "Ajinkya Rahane", "team_name": "KKR", ...}, ...]
print(info["over_groups"]) # powerplay / middle / death phase aggregates

overs = ci.match_overs(series_slug, match_slug)  # over-by-over progression
fow = ci.match_fall_of_wickets(series_slug, match_slug)
partnerships = ci.match_partnerships(series_slug, match_slug)

# Weather (works for live and completed matches)
weather = ci.match_weather(series_slug, match_slug)
print(weather["source"])   # "espncricinfo" (live) or "open-meteo" (historical)
if weather["source"] == "open-meteo":
    print(weather["hourly"]["temperature_2m"])  # hourly temps for match day(s)
```

### Live matches

```python
for match in ci.live_matches():
    series = match["series"]
    print(match["title"], "-", series.get("longName", ""))
```

### Async client for concurrent fetching

`AsyncCricinfoClient` is a full async mirror of `CricinfoClient` — every method listed in the API reference below is available as an `async def`. Use it as an async context manager and overlap requests with `asyncio.gather` for large batch workloads.

```python
import asyncio
from cricdata import AsyncCricinfoClient

async def main():
    async with AsyncCricinfoClient() as ci:
        fixtures = await ci.series_fixtures("ipl-2025-1449924")
        matches = fixtures["content"]["matches"]

        # fetch multiple scorecards concurrently (bounded)
        sem = asyncio.Semaphore(15)

        async def fetch(m):
            s = f"{m['series']['slug']}-{m['series']['objectId']}"
            ms = f"{m['slug']}-{m['objectId']}"
            async with sem:
                return await ci.match_scorecard(s, ms)

        scorecards = await asyncio.gather(*[fetch(m) for m in matches])

        # all other methods work the same way
        bio = await ci.player_bio(253802)
        india = await ci.team_career_stats(6, fmt="test")

asyncio.run(main())
```

### Team and ground stats from Statsguru

```python
# India's Test record by opposition
india = ci.team_career_stats(6, fmt="test")
for row in india["breakdowns"][:3]:
    print(row["Grouping"], row["Won"], row["Lost"])

# Eden Gardens venue stats
ground = ci.ground_stats(57980, fmt="test")
print(ground["summary"])  # {"Mat": "43", "Ave": "32.13", "RPO": "2.78", ...}
```

## API reference

All methods live on `CricinfoClient` (and `AsyncCricinfoClient`). Every return value is a `TypedDict` — your editor will autocomplete keys and your type checker will catch typos.

All types are importable: `from cricdata import BallItem, MatchInfo, CareerStats, ...`

### Matches

| Method | Parameters | Returns |
|---|---|---|
| `live_matches()` | — | `list[dict]` — current/recent matches |
| `match_scorecard(series_slug, match_slug)` | series & match slugs | `ScorecardData` — full scorecard (innings, batsmen, bowlers, FOW) |
| `match_commentary(series_slug, match_slug)` | series & match slugs | `CommentaryData` — recent ball-by-ball commentary |
| `match_ball_by_ball(series_slug, match_slug)` | series & match slugs | `list[list[BallItem]]` — every delivery grouped by innings |
| `match_overs(series_slug, match_slug)` | series & match slugs | `list[list[OverSummary]]` — over-by-over progression per innings |
| `match_partnerships(series_slug, match_slug)` | series & match slugs | `list[list[Partnership]]` — partnership details per innings |
| `match_fall_of_wickets(series_slug, match_slug)` | series & match slugs | `list[list[FallOfWicket]]` — FOW per innings |
| `match_info(series_slug, match_slug)` | series & match slugs | `MatchInfo` — toss, venue, captains, time, weather, awards, phase stats |
| `match_weather(series_slug, match_slug)` | series & match slugs | `WeatherResult \| None` — weather (live via ESPNCricinfo, historical via Open-Meteo) |

### Series

| Method | Parameters | Returns |
|---|---|---|
| `series(slug)` | series slug | `SeriesPageData` — series metadata |
| `series_matches(slug)` | series slug | `SeriesPageData` — completed match results |
| `series_fixtures(slug)` | series slug | `SeriesPageData` — upcoming schedule |
| `series_standings(slug)` | series slug | `StandingsData` — points table |
| `series_stats(slug)` | series slug | `SeriesPageData` — top performers |
| `series_squads(slug)` | series slug | `SeriesPageData` — squad lists with player bios |

### Players

| Method | Parameters | Returns |
|---|---|---|
| `search_players(query, limit=10)` | name string | `list[PlayerSearchResult]` — matching players with IDs |
| `player_bio(player_id)` | numeric ID | `PlayerBio` — name, DOB, bat/bowl style, team, headshot |
| `player_career_stats(player_id, fmt, stat_type, filters)` | numeric ID, `Format`, `StatType` | `CareerStats` — career averages + per-opposition breakdowns |
| `player_innings(player_id, fmt, stat_type, filters)` | numeric ID, `Format`, `StatType` | `InningsList` — innings-by-innings list |
| `player_match_list(player_id, fmt, stat_type, filters)` | numeric ID, `Format`, `StatType` | `MatchList` — match-by-match scores |
| `player_series_list(player_id, fmt, stat_type, filters)` | numeric ID, `Format`, `StatType` | `SeriesList` — per-series averages |
| `player_ground_stats(player_id, fmt, stat_type, filters)` | numeric ID, `Format`, `StatType` | `GroundAverages` — per-venue averages |

`Format`: `"test"`, `"odi"`, `"t20i"`, `"fc"`, `"lista"`, `"t20"`
`StatType`: `"batting"`, `"bowling"`, `"fielding"`, `"allround"`
`filters`: optional `StatsFilter` — `opposition` (team ID), `home_or_away` (1/2/3), `start_date`, `end_date`, `ground` (ground ID)

### Teams

| Method | Parameters | Returns |
|---|---|---|
| `team(slug)` | team slug | `TeamPageData` — team info, recent results, squads |
| `team_career_stats(team_id, fmt)` | numeric ID, `Format` | `CareerStats` — W/L/D record by opposition |
| `team_match_list(team_id, fmt)` | numeric ID, `Format` | `MatchList` — match-by-match results |
| `team_rankings(fmt)` | `RankingFormat` (`"test"`/`"odi"`/`"t20i"`) | `list[RankingGroup]` — ICC team rankings |

### Grounds

| Method | Parameters | Returns |
|---|---|---|
| `ground_stats(ground_id, fmt)` | numeric ID, `Format` | `CareerStats` — venue averages, W/L, RPO by team |

## Slugs and IDs

**Slugs** come from ESPNCricinfo URLs and are returned by discovery methods like `live_matches()`, `series_fixtures()`, and `series_matches()`. Construct them as `"{slug}-{objectId}"` from any match or series object in a response.

**Numeric IDs** (for players, teams, grounds) can be found via `search_players()` or from Statsguru/ESPNCricinfo URLs.

## License

MIT
