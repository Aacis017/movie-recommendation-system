"""Small, dependency-light client for TMDB movie artwork."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import TypedDict

import requests


API_BASE_URL = "https://api.themoviedb.org/3"
IMAGE_BASE_URL = "https://image.tmdb.org/t/p"


class MovieArt(TypedDict):
    poster_url: str | None
    backdrop_url: str | None
    tmdb_url: str


def fetch_movie_art(movie_id: int, read_token: str) -> MovieArt:
    """Fetch poster and backdrop paths for one TMDB movie ID."""
    response = requests.get(
        f"{API_BASE_URL}/movie/{movie_id}",
        params={"language": "en-US"},
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {read_token}",
        },
        timeout=8,
    )
    response.raise_for_status()
    payload = response.json()
    poster_path = payload.get("poster_path")
    backdrop_path = payload.get("backdrop_path")
    return {
        "poster_url": f"{IMAGE_BASE_URL}/w500{poster_path}" if poster_path else None,
        "backdrop_url": f"{IMAGE_BASE_URL}/w1280{backdrop_path}" if backdrop_path else None,
        "tmdb_url": f"https://www.themoviedb.org/movie/{movie_id}",
    }


def fetch_art_batch(movie_ids: tuple[int, ...], read_token: str) -> dict[int, MovieArt]:
    """Fetch a small group of artwork records concurrently."""
    if not read_token or not movie_ids:
        return {}

    art: dict[int, MovieArt] = {}
    with ThreadPoolExecutor(max_workers=min(6, len(movie_ids))) as executor:
        futures = {
            executor.submit(fetch_movie_art, movie_id, read_token): movie_id
            for movie_id in movie_ids
        }
        for future in as_completed(futures):
            movie_id = futures[future]
            try:
                art[movie_id] = future.result()
            except (requests.RequestException, ValueError):
                # A missing image or temporary API error should not break recommendations.
                continue
    return art
