# Architecture

## Overview

cricdata is a Python client library that retrieves cricket data from ESPNCricinfo. It exposes a single facade (`CricinfoClient` / `AsyncCricinfoClient`) that internally delegates to three backend modules, each targeting a distinct ESPNCricinfo data source.

There is no database, no server, no transformation pipeline. The library fetches, extracts, and returns plain Python dicts/lists.

## File layout

```
cricdata/
├── __init__.py        # Public exports: CricinfoClient, AsyncCricinfoClient
├── client.py          # Facade — composes SSR, ESPN, and Statsguru backends
├── _session.py        # HTTP session wrapper (curl_cffi + TLS impersonation)
├── _ssr.py            # Next.js __NEXT_DATA__ extractor for espncricinfo.com pages
├── _espn.py           # ESPN open JSON API (player search, bio, play-by-play)
└── _statsguru.py      # Statsguru HTML table scraper (player/team/ground stats)
```

## Component diagram

```
┌──────────────────────────────────────────────────┐
│                  CricinfoClient                  │
│           (or AsyncCricinfoClient)               │
│                                                  │
│   Facade — routes each public method to the      │
│   correct backend                                │
└───────┬──────────────┬──────────────┬────────────┘
        │              │              │
        ▼              ▼              ▼
   ┌─────────┐   ┌──────────┐   ┌────────────┐
   │   SSR   │   │   ESPN   │   │ Statsguru  │
   └────┬────┘   └────┬─────┘   └─────┬──────┘
        │              │               │
        ▼              ▼               ▼
   espncricinfo   ESPN open API   stats.espncricinfo
   .com HTML      (JSON)          .com HTML
        │              │               │
        └──────────┬───┘───────────────┘
                   │
            ┌──────┴──────┐
            │   Session   │
            │ (curl_cffi) │
            └─────────────┘
```

## Backends

### SSR (`_ssr.py`)

Fetches server-rendered espncricinfo.com pages (Next.js) and extracts the `__NEXT_DATA__` JSON blob embedded in `<script id="__NEXT_DATA__">`. This is the richest source — it powers:

- Live matches, scorecards, commentary
- Match overs, partnerships, fall of wickets, match info
- Series metadata, fixtures, results, standings, stats, squads
- Team pages, ICC rankings

The sync `SSR` class caches scorecard responses in a per-instance dict keyed by `(series_slug, match_slug)` since multiple public methods (scorecard, partnerships, FOW, overs, match_info) read from the same page. The async `AsyncSSR` does not cache.

### ESPN (`_espn.py`)

Calls ESPN's public JSON API (`site.web.api.espn.com`). Three endpoints:

| Endpoint | Used for |
|---|---|
| `/apis/common/v3/search` | `search_players()` |
| `/apis/common/v3/sports/cricket/athletes/{id}` | `player_bio()` |
| `/apis/site/v2/sports/cricket/8676/playbyplay` | `match_ball_by_ball()` |

The play-by-play endpoint paginates (25 items/page). `match_ball_by_ball` fetches all pages, then groups balls into innings by `innings.number`.

### Statsguru (`_statsguru.py`)

Scrapes `stats.espncricinfo.com/ci/engine/` HTML pages (player, team, ground). Parses `<table class="engineTable">` elements with regex, converts header+data rows into dicts. All Statsguru methods return `{"summary": {...}, "<detail_key>": [...]}`.

Supports filtering by opposition, home/away, date range, and ground via Statsguru's semicolon-delimited query parameters.

## Session layer (`_session.py`)

Thin wrapper around `curl_cffi.requests.Session` / `AsyncSession`. Configures:

- **TLS fingerprint impersonation** (default: `"chrome"`) — curl_cffi reproduces a real browser's TLS ClientHello, which is necessary because ESPNCricinfo blocks requests with standard Python TLS fingerprints.
- **Timeout** (default: 30s)

This is the only external dependency.

## Sync / async duality

Every internal class has a sync and async variant:

| Sync | Async |
|---|---|
| `Session` | `AsyncSession` |
| `SSR` | `AsyncSSR` |
| `ESPN` | `AsyncESPN` |
| `Statsguru` | `AsyncStatsguru` |
| `CricinfoClient` | `AsyncCricinfoClient` |

The async client supports `async with` for lifecycle management. Sync client has no explicit close.

## Data flow

```
User calls ci.match_scorecard(series_slug, match_slug)
    │
    ▼
CricinfoClient delegates to SSR.match_scorecard()
    │
    ▼
SSR._scorecard_data() checks cache, calls SSR._page_data() on miss
    │
    ▼
Session.get() fetches https://www.espncricinfo.com/series/{s}/{m}/full-scorecard
    │
    ▼
_extract_page_data() regex-extracts __NEXT_DATA__ JSON, parses it,
returns data["props"]["appPageProps"]["data"]
    │
    ▼
Dict returned to caller
```

For Statsguru methods the flow differs at the extraction step — HTML tables are parsed with regex instead of JSON extraction.

For ESPN methods the response is already JSON — `.json()` is called directly on the response.

## Slug and ID conventions

- **Slugs** are URL path segments from espncricinfo.com, formatted as `"{name}-{objectId}"` (e.g., `"ipl-2025-1449924"`). Used by SSR methods.
- **Numeric IDs** identify players, teams, and grounds. Used by ESPN and Statsguru methods.
- `CricinfoClient._extract_match_id()` handles the conversion from slug to numeric ID when a method needs to cross from SSR-style slugs to ESPN-style numeric IDs (specifically for `match_ball_by_ball`).

## Dependencies

| Dependency | Purpose |
|---|---|
| `curl_cffi >= 0.7` | HTTP client with browser TLS fingerprint impersonation |

No other runtime dependencies. Python 3.10+ required.

## Build

Uses `hatchling` as the build backend, configured in `pyproject.toml`.
