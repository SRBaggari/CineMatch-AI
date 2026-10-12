# CineMatch AI — Personalized Movie Recommendation System

**DecodeLabs Artificial Intelligence Industrial Training · Project 3: AI Recommendation Logic**

CineMatch AI is a content-based movie recommendation system. It collects a user's preferences, represents movies as feature vectors, and scores each movie with TF-IDF and cosine similarity. A configurable weighted sum combines the scores into a ranked top 10. Every recommendation lists its matched preferences, the reasons for the pick, and each score component.

All processing runs locally. The project uses no paid APIs, API keys, external AI services, or random selection. Every score can be traced back to the dataset and the algorithm.

| Requirement | How it is met |
|---|---|
| Movie dataset | 130 movies with id, title, genres, description, year, language, runtime, rating, keywords, and moods ([dataset note](#4-dataset)) |
| Preference collection | Genres, languages, moods, keywords or themes, year range, and minimum rating (plus optional liked movies) |
| Content-based filtering | Multi-hot genre and mood vectors, one-hot language vector, TF-IDF text vector, and release year per movie |
| TF-IDF vectorisation | `TfidfVectorizer` over each movie's keywords and description |
| Cosine similarity | Between the user's preferences and each movie, in every feature space |
| Weighted preference matching | Configurable weights for genre, language, mood, keyword, and year, normalised over the components in use |
| Ranking | Top 10 by default, hard filters, duplicate removal, an explained empty result, deterministic tie-breaking |
| Explainable AI | Title, relevance score, matched genres and preferences, reasons ordered by contribution, and per-component scores |
| API | FastAPI with Pydantic validation: preference options, movie list and details, recommendations, similar movies |
| Testing | 65 pytest tests covering scoring maths, engine behaviour on a synthetic fixture, and the API on the real dataset |

---

## 1. Tech stack

| Layer | Technology |
|---|---|
| Frontend | React 19, Vite 8, JavaScript, modern CSS, Lucide React icons |
| Backend | Python 3.10+, FastAPI, Uvicorn, Pydantic v2 |
| ML / data | Pandas, NumPy, SciPy, scikit-learn (`TfidfVectorizer`, `MultiLabelBinarizer`, `cosine_similarity`) |
| Dataset | Local CSV (`backend/data/movies.csv`) |
| Testing | Pytest with FastAPI `TestClient` |

## 2. System architecture

```
┌──────────────────────────── Browser (React + Vite) ────────────────────────────┐
│  PreferencePanel ─► App state ─► api/client.js ─► fetch('/api/...')            │
│  TasteProfile · MovieCard · ScoreBreakdown · MovieModal (similar movies)       │
└───────────────────────────────────────┬────────────────────────────────────────┘
                                        │  Vite dev proxy  /api → 127.0.0.1:8000
┌───────────────────────────────────────▼────────────────────────────────────────┐
│ FastAPI (app/main.py)                                                          │
│   routes.py ─ validates with schemas.py (Pydantic) ─► RecommendationEngine     │
│                                                                                │
│ RecommendationEngine (app/recommender.py), built once at startup               │
│   1. feature vectors (multi-hot, one-hot, TF-IDF, year)                        │
│   2. user profile in the same spaces                                           │
│   3. five component scores in [0, 1] (cosine similarities, match, year fit)    │
│   4. normalised weighted sum                                                   │
│   5. hard filters, de-duplication, deterministic ranking                       │
│   6. explanation (matched preferences, reasons, components)                    │
│                                                                                │
│ data_loader.py ─ reads, validates, cleans, de-duplicates ─► data/movies.csv    │
└────────────────────────────────────────────────────────────────────────────────┘
```

## 3. Folder structure

```
CineMatch-AI/
├── backend/
│   ├── app/
│   │   ├── config.py          # paths, weights, year decay, dataset provenance
│   │   ├── data_loader.py     # CSV loading, validation, cleaning, de-duplication
│   │   ├── recommender.py     # RecommendationEngine + pure scoring helpers
│   │   ├── schemas.py         # Pydantic request/response models
│   │   ├── routes.py          # REST endpoints
│   │   ├── main.py            # FastAPI app, startup, CORS
│   │   └── demo.py            # command-line demo with a sample input
│   ├── data/movies.csv
│   ├── tests/
│   │   ├── conftest.py        # synthetic 7-movie fixture catalogue + API client
│   │   ├── test_scoring.py    # unit tests of the maths
│   │   ├── test_engine.py     # behaviour: exact/partial/no match, ranking, ties…
│   │   └── test_api.py        # endpoints + invalid input on the real dataset
│   ├── requirements.txt / requirements-dev.txt / pytest.ini
├── frontend/
│   ├── vite.config.js         # dev server + /api proxy (API_TARGET env var)
│   └── src/
│       ├── App.jsx            # state, payload building, page layout
│       ├── api/client.js      # backend API wrapper
│       ├── utils/             # genre styling, component labels
│       ├── hooks/useDebounce.js
│       ├── styles.css
│       └── components/        # PreferencePanel, MovieCard, ScoreBreakdown, TasteProfile,
│                              # MovieModal, ScoreRing, Poster, HowItWorks, …
├── docs/ALGORITHM.md          # detailed algorithm + worked example
├── scripts/                   # Windows PowerShell setup/start helpers
└── README.md
```

## 4. Dataset

`backend/data/movies.csv` contains 130 movies across 19 genres, 15 moods, and 10 languages.

> **Provenance: please read.** The catalogue is **hand-curated for educational use and is not verified.** Titles, release years, directors, and cast refer to real films. The ratings, runtimes, keywords, moods, and one-sentence descriptions were written from general knowledge for this project. They are **approximate** and have **not** been checked against an authoritative source such as IMDb or TMDB. Do not cite them as factual. The same note is returned by `GET /api/dataset` and shown in the app footer. The automated tests use a separate, clearly **synthetic** 7-movie fixture (`tests/conftest.py`).

| Required field | Column | Type | Example |
|---|---|---|---|
| Unique movie ID | `movie_id` | int | `6` |
| Movie title | `title` | string | `Inception` |
| Genre | `genres` | pipe list | `Science Fiction\|Action\|Thriller` |
| Description | `overview` | string | `A thief who steals secrets…` |
| Release year | `year` | int | `2010` |
| Language | `language` | string | `English` |
| Duration | `runtime` | int (minutes) | `148` |
| Rating | `rating` | float 0–10 (approx.) | `8.8` |
| Keywords | `keywords` | pipe list | `dreams\|heist\|reality` |
| Mood or theme | `moods` | pipe list | `Mind-Bending\|Action-Packed` |
| *(extra)* | `director`, `cast` | string, pipe list | used only in "More like this" explanations |

The loader checks that the required columns exist, coerces types, removes duplicate labels inside list fields, and drops duplicate movies (same `movie_id`, or same title and year).

## 5. Recommendation algorithm (summary)

`docs/ALGORITHM.md` has the full derivation and a worked example.

| Component | Feature vectors | Score in [0, 1] | Default weight |
|---|---|---|---|
| Genre | multi-hot user vs. movie | cosine = \|U∩M\| / √(\|U\|·\|M\|) | 0.30 |
| Keyword | TF-IDF of keywords + description | cosine ÷ best cosine in catalogue | 0.25 |
| Mood | multi-hot user vs. movie | cosine | 0.20 |
| Language | one-hot | 1 if preferred, else 0 | 0.15 |
| Year | release year | 1 inside range, −1/20 per year outside | 0.10 |

```
score = Σ w'_c · s_c        where  w'_c = w_c / Σ_{active} w_k   (only components the user set)
```

* **Comparable components:** every component is in [0, 1], with 1 meaning a perfect match. Raw TF-IDF cosines are small (rarely above 0.5), so the keyword score is max-normalised: the best text match in the catalogue scores 1. The raw cosine is still returned.
* **Hard filters:** minimum rating always applies. The year range and languages become hard filters only when `strict_years` or `strict_languages` is set. A preference used as a hard filter stops counting as a score component (it would be 1.0 for every remaining movie), unless it is the only preference given.
* **Ranking:** liked and excluded movies are removed, along with movies scoring 0 (they match nothing). The rest are sorted by **score ↓, rating ↓, movie_id ↑**, so ties always resolve the same way. The top `top_n` (default 10) are returned.
* **No match:** the response is still `200`. It has an empty list, a `message` naming the filter that removed everything, and a `filter_report` showing how many movies survived each step.
* **Score meaning:** the score is a weighted similarity for **ranking**. It is **not** a calibrated probability that the user will like the movie, and the UI shows it as a 0–1 relevance score, not a percentage.

## 6. API reference

Interactive docs are at **http://127.0.0.1:8000/docs** when the backend is running.

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/health` | Engine status |
| GET | `/api/dataset` | Catalogue size, vocabulary, and provenance note |
| GET | `/api/preferences/options` | Available genres, moods, languages, popular keywords, year and rating ranges, default weights |
| GET | `/api/movies?search=&genre=&language=&limit=&offset=` | Paginated movie list: `{total, limit, offset, items}` |
| GET | `/api/movies/{id}` | Movie details (404 if unknown) |
| GET | `/api/movies/{id}/similar?top_n=` | Item-to-item similarity |
| POST | `/api/recommendations` | Ranked, explained recommendations |

Request (all fields optional, but at least one preference is required; unknown fields are rejected):

```json
{
  "genres": ["Science Fiction", "Thriller"],
  "languages": ["English"],
  "moods": ["Mind-Bending"],
  "keywords": ["time travel", "dreams", "artificial intelligence"],
  "year_min": 1995,
  "year_max": 2020,
  "min_rating": 7.5,
  "strict_years": false,
  "strict_languages": false,
  "liked_movie_ids": [],
  "exclude_movie_ids": [],
  "top_n": 10,
  "weights": {"genre": 0.30, "keyword": 0.25, "mood": 0.20, "language": 0.15, "year": 0.10}
}
```

Each recommendation contains `rank`, `movie_id`, `title`, `movie`, `score`, `components` (each with `value`, `raw`, `weight`, `contribution`, and `active`), `matched` (genres, moods, language, keywords, year_in_range), `reasons`, `top_terms`, and `similar_to`. The response also carries `profile` (effective weights, active components, and inferred genres or moods), `filter_report`, `message`, and `warnings`.

The API returns **422** for empty preferences, out-of-range values, `year_min > year_max`, unknown genres, moods, languages, or movie ids, blank labels, unknown fields, negative weights, and all-zero weights.

## 7. Sample output

`.\.venv\Scripts\python.exe -m app.demo` (run from `backend/`) prints the following for the request above:

```
EFFECTIVE WEIGHTS  genre=0.30  language=0.15  mood=0.20  keyword=0.25  year=0.10
FILTER REPORT {'total': 130, 'after_min_rating': 125, 'with_positive_score': 124}

 #  Title                         Score    genre  langu   mood  keywo   year  kw cos
 1  Ex Machina                    0.725    0.817  1.000  0.577  0.460  1.000   0.192
 2  Inception                     0.717    0.817  1.000  0.577  0.425  1.000   0.178
 3  The Matrix                    0.635    0.500  1.000  0.577  0.479  1.000   0.200
 4  Terminator 2: Judgment Day    0.630    0.500  1.000  0.000  1.000  0.800   0.418
 5  The Prestige                  0.578    0.707  1.000  0.577  0.000  1.000   0.000
 …
```

## 8. Running on Windows (PowerShell)

**Prerequisites:** Python 3.10+ and Node.js 20+. This project was tested with Python 3.14 and Node 24.

### Option A: helper scripts

```powershell
cd C:\Users\rinki\CineMatch-AI
powershell -ExecutionPolicy Bypass -File .\scripts\setup.ps1      # one-time: venv + pip + npm
powershell -ExecutionPolicy Bypass -File .\scripts\start-all.ps1  # backend + frontend windows
```

Open **http://localhost:5173**.

### Option B: manual commands

```powershell
# Terminal 1: backend
cd C:\Users\rinki\CineMatch-AI\backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000

# Terminal 2: frontend
cd C:\Users\rinki\CineMatch-AI\frontend
npm install
npm run dev
```

### Tests and demo

```powershell
cd C:\Users\rinki\CineMatch-AI\backend
.\.venv\Scripts\python.exe -m pytest -v
.\.venv\Scripts\python.exe -m app.demo
```

### If port 8000 is busy

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start-all.ps1 -Port 8001
# or manually:
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8001   # backend
$env:API_TARGET = "http://127.0.0.1:8001"; npm run dev                      # frontend
```

### Production build of the frontend

```powershell
cd frontend
npm run build      # outputs frontend/dist
npm run preview    # serves the build on http://localhost:4173 (still proxies /api)
```
