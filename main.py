"""SofaScore football (soccer) API wrapper.

A FastAPI service that mirrors SofaScore's private v1 endpoints and transparently
adds the browser TLS fingerprint (via curl_cffi) and rotating token they require.
Supports optional DNS-over-HTTPS (DoH) via the ``DOH_URL`` env var to bypass the
system/ISP resolver.

Interactive Swagger docs are served automatically by FastAPI:

    Swagger UI : http://localhost:8080/docs
    ReDoc      : http://localhost:8080/redoc
    OpenAPI    : http://localhost:8080/openapi.json

Run:
    pip install -r requirements.txt
    uvicorn main:app --port 8080 --reload
    # or: python main.py
"""

from __future__ import annotations

import logging
import os
import re

from fastapi import FastAPI, HTTPException, Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from sofascore_client import SofaScoreClient, SofaScoreError

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("sofascore")

DESCRIPTION = """
A thin wrapper around the public **SofaScore football (soccer)** v1 API
(`https://api.sofascore.com/api/v1`).

It uses **curl_cffi** to impersonate a real browser's TLS handshake and attaches
the rotating `X-Requested-With` token + `Sec-Fetch-*` headers SofaScore requires,
then streams the upstream JSON straight back. Paths mirror the upstream API 1:1.

Optionally set `DOH_URL` (e.g. `https://cloudflare-dns.com/dns-query`) to route
DNS through DNS-over-HTTPS, bypassing the system/ISP resolver.
"""

client = SofaScoreClient(
    impersonate=os.getenv("IMPERSONATE", "chrome"),
    timeout=float(os.getenv("TIMEOUT", "20")),
    doh_url=os.getenv("DOH_URL") or None,
)

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


app = FastAPI(
    title="SofaScore Football API Wrapper",
    version="1.0.0",
    description=DESCRIPTION,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


def proxy(path: str) -> Response:
    """Fetch an upstream path and return its JSON body + status verbatim."""
    try:
        body, status = client.get(path)
    except SofaScoreError as exc:
        log.error("upstream request to %s failed: %s", path, exc)
        raise HTTPException(status_code=502, detail=str(exc))
    return Response(
        content=body,
        status_code=status,
        media_type="application/json",
        headers={"X-Upstream-Status": str(status)},
    )


# --------------------------------------------------------------------------- #
# Meta
# --------------------------------------------------------------------------- #
@app.get("/healthz", tags=["Meta"], summary="Health check")
def healthz() -> dict:
    """Service status, current token, impersonation target and DoH provider."""
    return {
        "status": "ok",
        "token": client.token(),
        "impersonate": client.impersonate,
        "doh_url": client.doh_url,
        "timeout": client.timeout,
    }


# --------------------------------------------------------------------------- #
# Daily schedules & tournaments
# --------------------------------------------------------------------------- #
@app.get("/sport/football/scheduled-events/{date}", tags=["Schedules & Tournaments"],
         summary="Scheduled football events for a date")
def scheduled_events(date: str = Path(..., examples=["2026-03-26"], description="YYYY-MM-DD")) -> Response:
    if not DATE_RE.match(date):
        raise HTTPException(status_code=400, detail="date must be in YYYY-MM-DD format")
    return proxy(f"/sport/football/scheduled-events/{date}")


@app.get("/sport/football/unique-tournaments", tags=["Schedules & Tournaments"],
         summary="List unique tournaments")
def unique_tournaments() -> Response:
    return proxy("/sport/football/unique-tournaments")


@app.get("/unique-tournament/{tournament_id}/seasons", tags=["Schedules & Tournaments"],
         summary="Seasons for a unique tournament")
def tournament_seasons(tournament_id: int = Path(..., ge=0, examples=[7])) -> Response:
    return proxy(f"/unique-tournament/{tournament_id}/seasons")


@app.get("/tournament/{tournament_id}/season/{season_id}/standings/total",
         tags=["Schedules & Tournaments"], summary="Total standings for a tournament season")
def standings(tournament_id: int = Path(..., ge=0, examples=[7]),
              season_id: int = Path(..., ge=0, examples=[61643])) -> Response:
    return proxy(f"/tournament/{tournament_id}/season/{season_id}/standings/total")


# --------------------------------------------------------------------------- #
# Event (match) endpoints
# --------------------------------------------------------------------------- #
@app.get("/event/{event_id}", tags=["Event"], summary="Core event (match) details")
def event(event_id: int = Path(..., ge=0, examples=[11352523])) -> Response:
    return proxy(f"/event/{event_id}")


@app.get("/event/{event_id}/statistics", tags=["Event"], summary="Match statistics")
def event_statistics(event_id: int = Path(..., ge=0, examples=[11352523])) -> Response:
    return proxy(f"/event/{event_id}/statistics")


@app.get("/event/{event_id}/incidents", tags=["Event"],
         summary="Match timeline / incidents (goals, cards, subs, VAR)")
def event_incidents(event_id: int = Path(..., ge=0, examples=[11352523])) -> Response:
    return proxy(f"/event/{event_id}/incidents")


@app.get("/event/{event_id}/lineups", tags=["Event"], summary="Lineups")
def event_lineups(event_id: int = Path(..., ge=0, examples=[11352523])) -> Response:
    return proxy(f"/event/{event_id}/lineups")


@app.get("/event/{event_id}/graph", tags=["Event"], summary="Momentum graph")
def event_graph(event_id: int = Path(..., ge=0, examples=[11352523])) -> Response:
    return proxy(f"/event/{event_id}/graph")


@app.get("/event/{event_id}/managers", tags=["Event"], summary="Managers")
def event_managers(event_id: int = Path(..., ge=0, examples=[11352523])) -> Response:
    return proxy(f"/event/{event_id}/managers")


@app.get("/event/{event_id}/player/{player_id}/statistics", tags=["Event"],
         summary="Player statistics within an event")
def event_player_statistics(event_id: int = Path(..., ge=0, examples=[11352523]),
                            player_id: int = Path(..., ge=0, examples=[991011])) -> Response:
    return proxy(f"/event/{event_id}/player/{player_id}/statistics")


# --------------------------------------------------------------------------- #
# Team endpoints
# --------------------------------------------------------------------------- #
@app.get("/team/{team_id}", tags=["Team"], summary="Core team profile")
def team(team_id: int = Path(..., ge=0, examples=[2829])) -> Response:
    return proxy(f"/team/{team_id}")


@app.get("/team/{team_id}/players", tags=["Team"], summary="Squad roster")
def team_players(team_id: int = Path(..., ge=0, examples=[2829])) -> Response:
    return proxy(f"/team/{team_id}/players")


@app.get("/team/{team_id}/performance", tags=["Team"], summary="Form guide")
def team_performance(team_id: int = Path(..., ge=0, examples=[2829])) -> Response:
    return proxy(f"/team/{team_id}/performance")


@app.get("/team/{team_id}/events/next", tags=["Team"], summary="Upcoming matches")
def team_events_next(team_id: int = Path(..., ge=0, examples=[2829])) -> Response:
    return proxy(f"/team/{team_id}/events/next/0")


@app.get("/team/{team_id}/events/last", tags=["Team"], summary="Recent matches")
def team_events_last(team_id: int = Path(..., ge=0, examples=[2829])) -> Response:
    return proxy(f"/team/{team_id}/events/last/0")


# --------------------------------------------------------------------------- #
# Player endpoints
# --------------------------------------------------------------------------- #
@app.get("/player/{player_id}", tags=["Player"], summary="Core player profile")
def player(player_id: int = Path(..., ge=0, examples=[991011])) -> Response:
    return proxy(f"/player/{player_id}")


@app.get("/player/{player_id}/statistics/seasons", tags=["Player"],
         summary="Career stats by season")
def player_statistics_seasons(player_id: int = Path(..., ge=0, examples=[991011])) -> Response:
    return proxy(f"/player/{player_id}/statistics/seasons")


@app.get("/player/{player_id}/characteristics", tags=["Player"], summary="Player traits")
def player_characteristics(player_id: int = Path(..., ge=0, examples=[991011])) -> Response:
    return proxy(f"/player/{player_id}/characteristics")


@app.get("/player/{player_id}/national-team-statistics", tags=["Player"],
         summary="International statistics")
def player_national_team_statistics(player_id: int = Path(..., ge=0, examples=[991011])) -> Response:
    return proxy(f"/player/{player_id}/national-team-statistics")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8080")),
        reload=bool(os.getenv("RELOAD")),
    )
