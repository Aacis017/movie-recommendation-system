"""Data preparation and recommendation logic for the Streamlit app."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity


DATA_DIR = Path(__file__).resolve().parent / "data"
MOVIES_CSV = DATA_DIR / "tmdb_5000_movies.csv"
CREDITS_CSV = DATA_DIR / "tmdb_5000_credits.csv"


# These three conversion functions follow the functions in the notebook.
def convert(value: str) -> list[str]:
    names = []
    for item in ast.literal_eval(value):
        names.append(item["name"])
    return names


def convert3(value: str) -> list[str]:
    names = []
    for item in ast.literal_eval(value)[:3]:
        names.append(item["name"])
    return names


def fetch_director(value: str) -> list[str]:
    directors = []
    for item in ast.literal_eval(value):
        if item["job"] == "Director":
            directors.append(item["name"])
            break
    return directors


@dataclass
class MovieRecommender:
    movies: pd.DataFrame
    vectorizer: CountVectorizer
    features: Any

    @classmethod
    def from_csv(cls) -> "MovieRecommender":
        # STEP 1: Check that both CSV files are present.
        if not MOVIES_CSV.exists() or not CREDITS_CSV.exists():
            raise FileNotFoundError(
                "Dataset files are missing. Put tmdb_5000_movies.csv and "
                "tmdb_5000_credits.csv in the data directory."
            )

        # STEP 2: Load the movies and credits datasets.
        movies = pd.read_csv(MOVIES_CSV)
        credits = pd.read_csv(CREDITS_CSV)

        # STEP 3: Merge both datasets using the movie title.
        movies = movies.merge(credits, on="title")

        # STEP 4: Keep the same eight columns selected in the notebook.
        movies = movies[
            [
                "movie_id",
                "title",
                "keywords",
                "overview",
                "production_companies",
                "cast",
                "crew",
                "genres",
            ]
        ].copy()
        # STEP 5: Remove missing and repeated movie records.
        movies.dropna(inplace=True)
        movies.rename(columns={"movie_id": "id"}, inplace=True)
        movies.drop_duplicates("id", inplace=True)

        # STEP 6: Convert the JSON-like text columns into lists of names.
        movies["genres"] = movies["genres"].apply(convert)
        movies["keywords"] = movies["keywords"].apply(convert)
        movies["cast"] = movies["cast"].apply(convert3)
        movies["crew"] = movies["crew"].apply(fetch_director)
        movies["production_companies"] = movies["production_companies"].apply(convert)

        # Save the readable sentence for the UI before splitting it into words.
        # This copy is display-only and is not an additional model feature.
        movies["overview_text"] = movies["overview"]
        movies["overview"] = movies["overview"].apply(lambda text: text.split())

        # Keep readable values for the Streamlit cards. They are not extra
        # recommendation features.
        movies["genre_names"] = movies["genres"]
        movies["director_names"] = movies["crew"]

        # STEP 7: Remove spaces inside names, exactly as in the notebook.
        columns_to_transform = [
            "genres",
            "keywords",
            "cast",
            "crew",
            "production_companies",
            "overview",
        ]
        for column in columns_to_transform:
            movies[column] = movies[column].apply(
                lambda values: [value.replace(" ", "") for value in values]
            )

        # STEP 8: Combine the same six columns into one tags column.
        movies["tags"] = (
            movies["overview"]
            + movies["genres"]
            + movies["keywords"]
            + movies["cast"]
            + movies["crew"]
            + movies["production_companies"]
        )

        # STEP 9: Convert the tag list to lowercase text.
        movies["tags"] = movies["tags"].apply(lambda values: " ".join(values).lower())
        movies.reset_index(drop=True, inplace=True)

        # STEP 10: Vectorize the tags using the notebook's CountVectorizer.
        vectorizer = CountVectorizer(max_features=5000, stop_words="english")
        features = vectorizer.fit_transform(movies["tags"])
        return cls(movies=movies, vectorizer=vectorizer, features=features)

    @property
    def movie_ids(self) -> list[int]:
        ordered = self.movies.sort_values("title", key=lambda col: col.str.casefold())
        return ordered["id"].astype(int).tolist()

    def movie_details(self, movie_id: int) -> pd.Series:
        matches = self.movies.index[self.movies["id"] == movie_id]
        if matches.empty:
            raise ValueError(f"Unknown movie ID: {movie_id}")
        return self.movies.iloc[matches[0]]

    def recommend(self, movie_id: int, count: int = 5) -> pd.DataFrame:
        # STEP 11: Find the selected movie's row.
        matches = self.movies.index[self.movies["id"] == movie_id]
        if matches.empty:
            raise ValueError(f"Unknown movie ID: {movie_id}")

        selected_index = int(matches[0])

        # STEP 12: Calculate cosine similarity with every movie.
        # Only one row is calculated to keep deployment memory usage low.
        scores = cosine_similarity(self.features[selected_index], self.features).ravel()

        # STEP 13: Sort the scores and keep the closest movies.
        best_indices = scores.argsort()[::-1]
        best_indices = [index for index in best_indices if index != selected_index][:count]

        # STEP 14: Return the recommendation information to the UI.
        result = self.movies.iloc[best_indices][
            ["id", "title", "genre_names", "director_names", "overview_text"]
        ].copy()
        result["match"] = (scores[best_indices] * 100).round().astype(int)
        return result.reset_index(drop=True)
