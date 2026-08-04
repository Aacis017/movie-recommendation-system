# CineMatch movie recommendation system

CineMatch is a content-based movie recommender built from the TMDB 5000
dataset. It compares plot descriptions, genres, keywords, cast, director, and
production companies, then returns the closest movies using cosine similarity.

## Run locally

1. Install Python 3.12 (the current Streamlit Community Cloud default).
2. Create and activate a virtual environment.
3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Create `.streamlit/secrets.toml` and add your TMDB API Read Access Token:

   ```toml
   TMDB_READ_TOKEN = "your-api-read-access-token"
   ```

   Get the token from **Settings > API** in your
   [TMDB account](https://www.themoviedb.org/settings/api). Use the long API
   Read Access Token, not your account password. Never commit `secrets.toml`.

5. Start the app:

   ```bash
   streamlit run app.py
   ```

The two dataset files must remain in `data/`:

- `tmdb_5000_movies.csv`
- `tmdb_5000_credits.csv`

## Deploy on Streamlit Community Cloud

### 1. Create the GitHub repository

On GitHub, create an empty repository. Do not add a README, `.gitignore`, or
license when creating it because this project already contains those files.

From PowerShell in the project directory, run:

```powershell
git init
git add .
git status
git commit -m "Initial movie recommendation app"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPOSITORY.git
git push -u origin main
```

Before committing, check the `git status` output and confirm that
`.streamlit/secrets.toml` is not listed. Only `secrets.toml.example` should be
included.

### 2. Create the Streamlit app

1. Sign in at [share.streamlit.io](https://share.streamlit.io/) with GitHub.
2. Select **Create app**, choose the repository and `main` branch, and set the
   entry point to `app.py`.
3. Open **Advanced settings**, select Python 3.12, and add this to **Secrets**:

   ```toml
   TMDB_READ_TOKEN = "your-api-read-access-token"
   ```

4. Select **Deploy**.

For future updates, commit and push your changes. Streamlit Community Cloud
will redeploy automatically:

```powershell
git add .
git commit -m "Describe your update"
git push
```

The first visit after the app sleeps may take a short time while the dataset is
loaded and vectorized. Later interactions use Streamlit's resource cache.

## Project structure

```text
.
|-- app.py                 # Streamlit user interface
|-- recommender.py         # Data preparation and recommendation engine
|-- requirements.txt       # Deployment dependencies
`-- data/
    |-- tmdb_5000_movies.csv
    `-- tmdb_5000_credits.csv
```

The dataset is relatively large (about 46 MB total), but each file is below
GitHub's 100 MB per-file limit. Confirm that your use of the dataset follows its
source terms before publishing the repository.

TMDB permits free non-commercial API use with attribution. The app includes an
approved logo and the required notice; review the current
[TMDB attribution requirements](https://developer.themoviedb.org/docs/faq)
before public launch.
