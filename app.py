"""Streamlit interface for the movie recommendation system."""

from __future__ import annotations

from html import escape

import streamlit as st

from recommender import MovieRecommender
from tmdb_client import MovieArt, fetch_art_batch


# UI STEP 1: Configure the Streamlit page.
st.set_page_config(
    page_title="CineMatch",
    page_icon="🎬",
    layout="wide",
)

# UI STEP 2: Add the page styling.
st.markdown(
    """
    <style>
    .stApp { background: linear-gradient(145deg, #090d18 0%, #11182a 100%); }
    .hero { padding: 2.5rem 0 1.5rem; }
    .hero h1 { color: #f7c948; font-size: 3.2rem; margin-bottom: .2rem; }
    .hero p { color: #b6bfd4; font-size: 1.05rem; }
    .movie-card {
        background: #171f33;
        border: 1px solid #2a3550;
        border-radius: 14px;
        min-height: 590px;
        overflow: hidden;
        margin-bottom: 1rem;
        box-shadow: 0 14px 34px rgba(0, 0, 0, .24);
        transition: transform .2s ease, border-color .2s ease;
    }
    .movie-card:hover { transform: translateY(-4px); border-color: #f7c948; }
    .poster { width: 100%; height: 355px; object-fit: cover; display: block; }
    .poster-placeholder {
        height: 355px; display: grid; place-items: center; color: #74809a;
        background: radial-gradient(circle at 25% 15%, #34415e, #11182a 62%);
        font-size: 3rem;
    }
    .movie-copy { padding: 1rem 1.05rem 1.2rem; }
    .movie-card h3 { color: #ffffff; margin: 0 0 .35rem; line-height: 1.2; }
    .movie-card .meta { color: #f7c948; font-size: .88rem; margin-bottom: .8rem; }
    .movie-card p { color: #b6bfd4; font-size: .92rem; }
    .match { color: #78e08f; font-weight: 700; }
    .tmdb-link { color: #90cea1 !important; text-decoration: none; font-size: .85rem; }
    .credits {
        border: 1px solid #26324b; border-radius: 12px; padding: 1rem 1.2rem;
        color: #9ca8bf; background: #11182a; margin-top: 1rem;
        display: flex; gap: 1rem; align-items: center;
    }
    .credits strong { color: #90cea1; letter-spacing: .06em; }
    .tmdb-logo { width: 52px; height: auto; flex: 0 0 auto; }
    </style>
    """,
    unsafe_allow_html=True,
)


# UI STEP 3: Cache the model and poster responses.
@st.cache_resource(show_spinner="Building the recommendation engine...")
def load_recommender() -> MovieRecommender:
    return MovieRecommender.from_csv()


@st.cache_data(ttl=21600, show_spinner=False)
def load_movie_art(movie_ids: tuple[int, ...], read_token: str) -> dict[int, MovieArt]:
    return fetch_art_batch(movie_ids, read_token)


def compact(text: str, length: int = 240) -> str:
    text = str(text).strip()
    text = text if len(text) <= length else f"{text[:length].rsplit(' ', 1)[0]}…"
    return escape(text)


def poster_markup(art: MovieArt | None, title: str) -> str:
    if art and art.get("poster_url"):
        poster_url = escape(str(art["poster_url"]), quote=True)
        return f'<img class="poster" src="{poster_url}" alt="Poster for {escape(title)}">'
    return '<div class="poster-placeholder" aria-label="Poster unavailable">🎬</div>'


# UI STEP 4: Read the private TMDB token.
try:
    tmdb_token = str(st.secrets.get("TMDB_READ_TOKEN", "")).strip()
except Exception:
    tmdb_token = ""


# UI STEP 5: Display the heading.
st.markdown(
    """
    <div class="hero">
      <h1>🎬 CineMatch</h1>
      <p>Choose a film you enjoy and discover similar movies based on story,
      genres, cast, director, keywords, and production company.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# UI STEP 6: Load the recommendation engine.
try:
    engine = load_recommender()
except Exception as exc:
    st.error(f"The recommendation engine could not start: {exc}")
    st.stop()

# UI STEP 7: Display the movie selector and recommendation count.
left, right = st.columns([4, 1])
with left:
    movie_ids = engine.movie_ids
    movie_labels = {}
    for _, movie in engine.movies.iterrows():
        movie_labels[int(movie["id"])] = movie["title"]
    avatar_matches = engine.movies.index[engine.movies["title"] == "Avatar"]
    default_id = (
        int(engine.movies.iloc[avatar_matches[0]]["id"])
        if not avatar_matches.empty
        else movie_ids[0]
    )
    selected_id = st.selectbox(
        "Pick a movie",
        movie_ids,
        index=movie_ids.index(default_id),
        format_func=movie_labels.get,
        placeholder="Type to search for a movie...",
    )
with right:
    recommendation_count = st.slider("Recommendations", 5, 10, 5)

# UI STEP 8: Show information about the selected movie.
selected = engine.movie_details(selected_id)
selected_title = selected["title"]
genres = " · ".join(selected["genre_names"]) or "Genres unavailable"
st.caption(f"Selected: **{selected_title}** — {genres}")

if not tmdb_token:
    st.info(
        "Add `TMDB_READ_TOKEN` to `.streamlit/secrets.toml` to display official "
        "TMDB posters. Recommendations still work without it."
    )

# UI STEP 9: Generate recommendations after the button is clicked.
if st.button("Find movies", type="primary", use_container_width=True):
    recommendations = engine.recommend(selected_id, recommendation_count)
    recommendation_ids = tuple(recommendations["id"].astype(int).tolist())
    with st.spinner("Finding your next movie night..."):
        artwork = load_movie_art(recommendation_ids, tmdb_token)
    st.subheader("You might also like")

    columns_per_row = 3
    for start in range(0, len(recommendations), columns_per_row):
        columns = st.columns(columns_per_row)
        for column, (_, movie) in zip(columns, recommendations.iloc[start:].head(3).iterrows()):
            movie_id = int(movie["id"])
            movie_genres = escape(" · ".join(movie["genre_names"][:3]) or "Uncategorized")
            director = escape(
                movie["director_names"][0]
                if movie["director_names"]
                else "Unknown director"
            )
            movie_title = escape(movie["title"])
            movie_art = artwork.get(movie_id)
            poster = poster_markup(movie_art, movie["title"])
            tmdb_url = (
                escape(movie_art["tmdb_url"], quote=True)
                if movie_art
                else f"https://www.themoviedb.org/movie/{movie_id}"
            )
            with column:
                st.markdown(
                    f"""
                    <div class="movie-card">
                        {poster}
                      <div class="movie-copy">
                        <h3>{movie_title}</h3>
                        <div class="meta">{movie_genres}</div>
                        <p><strong>Director:</strong> {director}</p>
                        <p>{compact(movie['overview_text'], 170)}</p>
                        <span class="match">{movie['match']}% content match</span><br>
                        <a class="tmdb-link" href="{tmdb_url}" target="_blank">View on TMDB ↗</a>
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

# UI STEP 10: Display TMDB attribution.
st.divider()
st.markdown(
    """
    <div class="credits">
      <a href="https://www.themoviedb.org" target="_blank">
        <img class="tmdb-logo"
          src="https://www.themoviedb.org/assets/2/v4/logos/v2/blue_square_2-d537fb228cf3ded904ef09b136fe3fec72548ebc1fea3fbbd1ad9e36364db38b.svg"
          alt="TMDB logo">
      </a>
      <div><strong>POWERED BY TMDB</strong><br>
        Recommendations use the TMDB 5000 dataset. Poster artwork is provided
        through the <a href="https://www.themoviedb.org" target="_blank">TMDB API</a>.
        This product uses the TMDB API but is not endorsed or certified by TMDB.
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)
