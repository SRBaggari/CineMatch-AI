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
| API | FastAPI with Pydantic validation: preference options, movie list and details, recommendations, per-movie explanation, similar movies, search, feedback, analytics |
| Feedback & personalisation | Like / dislike / favourite stored in local SQLite; a separate, bounded feedback adjustment re-ranks matching movies ([section 10](#10-feedback-search-analytics-and-performance)) |
| Frontend | Multi-page React app: Home, Preferences (6-step wizard), Recommendations, Movie Details, Browse (search & filters), My List, Analytics, How It Works ([section 9](#9-frontend)) |
| Testing | 138 backend tests (pytest) and 22 frontend unit tests (Vitest), covering scoring maths, explanations, feedback, search, caching, data cleaning, the SQLite store, analytics, the API, preference sanitising, and API error handling |

---

## 1. Tech stack

| Layer | Technology |
|---|---|
| Frontend | React 19, React Router 7, Vite 8, JavaScript, plain CSS (no Tailwind), Lucide React icons |
| Backend | Python 3.10+, FastAPI, Uvicorn, Pydantic v2 |
| ML / data | Pandas, NumPy, SciPy, scikit-learn (`TfidfVectorizer`, `MultiLabelBinarizer`, `cosine_similarity`) |
| Dataset | Local CSV (`backend/data/movies.csv`) |
| Testing | Pytest with FastAPI `TestClient`; Vitest for frontend logic |

## 2. System architecture

```
┌──────────────────────────── Browser (React + Vite) ────────────────────────────┐
│  Routes: / · /preferences · /recommendations · /movies/:id · /how-it-works     │
│  AppContext (options, saved preferences, cached results) ─► api/client.js      │
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
│   │   ├── recommender.py     # RecommendationEngine: features, caching, scoring, feedback, search
│   │   ├── store.py           # SQLite: feedback + anonymous usage log
│   │   ├── analytics.py       # analytics payload (dataset + logged usage)
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
│       ├── main.jsx           # BrowserRouter + AppProvider + styles
│       ├── App.jsx            # route table
│       ├── api/client.js      # backend API wrapper (typed errors)
│       ├── context/AppContext.jsx  # options, persisted preferences, cached results
│       ├── pages/             # Home, Preferences, Results, MovieDetails, HowItWorks, NotFound
│       ├── components/
│       │   ├── layout/        # Navbar (mobile menu), Footer, Layout (offline banner)
│       │   ├── ui/            # Poster, ScoreRing, ChipSelector, MultiSelectDropdown,
│       │   │                  # RangeSlider, Toggle, Feedback (spinner/empty/error/skeleton)
│       │   ├── movies/        # RecommendationCard, MovieTile, ScoreBreakdown, FilterReport
│       │   └── preferences/   # Stepper, KeywordInput, MovieSearch
│       ├── utils/             # prefs (payload/validation), storage, genres, moods, tfidf demo
│       ├── hooks/useDebounce.js
│       └── styles/            # tokens, base, layout, components, pages (.css)
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

**Missing values are never invented.**

* **Dropped rows:** a row is dropped (and logged by reason) when it is missing a valid `movie_id`, `title`, `year` (1880–2100), or `rating` (0–10). These fields identify, filter, or rank a movie.
* **Filled fields:** missing optional fields get explicit empty values. Genres, moods, keywords, and cast become empty lists. Director and language become `Unknown`, and the overview becomes empty.
* **Unknown runtime:** a missing or non-positive runtime becomes `0`, which the UI shows as "Runtime —".
* **No usable rows:** a dataset with no valid rows fails at startup with a clear error.

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
base  = Σ w'_c · s_c        where  w'_c = w_c / Σ_{active} w_k   (only components the user set)
score = clip(base + feedback_adjustment, 0, 1)      (adjustment = 0 without saved feedback)
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
| POST | `/api/movies/{id}/explain` | Score, components, reasons, and rank of **one** movie for the given preferences (same body as `/recommendations`); `rank` is `null` and `filtered_by` lists the reason when a hard filter removes it |
| POST | `/api/recommendations` | Ranked, explained recommendations (logged to the local usage table) |
| POST | `/api/movies/search` | Title search + genre / language / year filters; `sort`: `relevance`, `rating`, `year`, `title`; optional `preferences` makes relevance = match score |
| GET | `/api/feedback` | Saved likes, dislikes, and favourites with movie details |
| PUT | `/api/feedback/{id}` | `{"reaction": "like" \| "dislike" \| null, "favorite": true \| false}`; omitted fields are unchanged |
| DELETE | `/api/feedback/{id}`, `/api/feedback` | Clear one movie's feedback, or all of it |
| GET | `/api/analytics` | Catalogue distributions, logged usage (selected genres, score distribution), feedback counts, cache stats |

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
  "weights": {"genre": 0.30, "keyword": 0.25, "mood": 0.20, "language": 0.15, "year": 0.10},
  "use_feedback": true
}
```

Each recommendation contains `rank`, `movie_id`, `title`, `movie`, `base_score` (preferences only), `feedback_adjustment`, `score` (final), `feedback` (closest liked / disliked movie and similarities), `summary` (one-sentence explanation), `components` (each with `value`, `raw`, `weight`, `contribution`, and `active`), `matched` (genres, moods, language, keywords, year_in_range), `reasons`, `top_terms`, and `similar_to`. The response also carries `profile` (effective weights, active components, and inferred genres or moods), `filter_report`, `message`, and `warnings`.

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
.\.venv\Scripts\python.exe -m pytest -v      # 138 backend tests
.\.venv\Scripts\python.exe -m app.demo       # sample input + scored, ranked output

cd C:\Users\rinki\CineMatch-AI\frontend
npm test                                     # 22 Vitest unit tests
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

## 9. Frontend

| Route | Page | What it does |
|---|---|---|
| `/` | Home | Hero ("Discover Movies Made for You"), Get Started, catalogue stats, featured highest-rated movie and a scrollable row (clearly labelled *not* personalised), How It Works preview |
| `/preferences` | Preferences | 6-step wizard with a progress stepper: genre chips → language dropdown (+ strict toggle) → mood selection cards → themes and liked movies → era cards, dual year slider, rating slider, result-count dropdown → review with editable weights and **Generate My Recommendations** |
| `/recommendations` | Results | Calls `POST /api/recommendations`. Shows the weights used, a filter funnel, a sort dropdown (default: match score), and cards with title, genres, rating, year, description, match score, reasons, and **View Details** |
| `/movies/:id` | Movie details | Movie info, genres, moods, keywords, credits, a match explanation from `POST /api/movies/{id}/explain` (rank, reasons, component breakdown), and similar movies |
| `/how-it-works` | How It Works | Beginner-friendly explanations of content-based filtering, TF-IDF, cosine similarity, weighted matching, and ranking, with live mini-demos |

* **Data:** every personalised result comes from the backend. Nothing is hard-coded. The How It Works demos use small labelled teaching examples.
* **Persistence:** preferences are saved to `localStorage` (`cinematch.preferences.v2`) and checked against the current catalogue on load. If storage is unavailable, the app still works.
* **States:** skeleton loaders while scoring, an offline banner with retry when the backend is unreachable, error panels with retry, and empty states for no preferences, no matches (with the filter funnel), and unknown movie or page.
* **Responsive:** tested at 1440 px desktop, 820 px tablet, and 390 px phone widths with no horizontal scrolling. On narrow screens the navbar collapses to a menu.
* **Design:** black and charcoal surfaces, a purple-to-blue gradient accent, glass panels, rounded cards, and hover lift animations. Animations are reduced when the OS asks for reduced motion. Posters are generated from genre colours, with no external image service.

| `/browse` | Browse | Title search, genre and language dropdowns, release-year slider, sort by relevance / rating / newest / title, optional "rank by my preferences" with match-score badges, pagination |
| `/my-list` | My List | Favourites, liked, and disliked movies, with buttons to change or clear them |
| `/analytics` | Analytics | Stat tiles, genre distribution, most-selected genres, score distribution, rating and language distributions, most-recommended movies, engine cache stats; each chart has hover tooltips and a table view |

## 10. Feedback, search, analytics, and performance

**Explanations.** Every recommendation has a `summary` sentence built only from attributes that actually matched, ordered by how much each contributed. For example: *"Recommended because you selected serial killer as favourite theme, enjoy Crime and Thriller movies, prefer English-language content, and are in the mood for something Dark."* A genre or language you chose that the movie doesn't have never appears. If nothing matched, the summary says so.

**Feedback.** Like, dislike, and favourite are stored in SQLite (`backend/data/cinematch.db`, git-ignored, one local profile). With `use_feedback` on (the default):

```
adjustment = 0.15 × (max item-similarity to a liked or favourite movie − max item-similarity to a disliked movie)
score      = clip(base_score + adjustment, 0, 1)
```

* `base_score` (preferences) and `feedback_adjustment` are separate fields, and the UI shows them separately ("Preference 0.83 − feedback 0.02 = 0.82").
* A movie never boosts itself; disliked movies are hidden (`filter_report.after_dislikes`).
* Feedback only re-ranks movies that already match a preference (`base_score > 0`), so it cannot pull in unrelated titles.
* Switching feedback off (`use_feedback: false`, or the toggle on the results page) restores the preference-only ranking exactly.

**Analytics.** `/api/analytics` reports catalogue figures from the CSV, plus usage from the local log. The usage section covers explicit genre, mood, and language selections per `/recommendations` call, and the final scores of every movie served. With no requests logged, the usage section is empty (zeros) and says so. Nothing is estimated. Searches and explanations are not logged.

**Performance.**

| Optimisation | Effect (measured on this machine, 130 movies) |
|---|---|
| Fitted encoders, TF-IDF matrix, and item-similarity matrix cached on disk (`backend/data/.cache`), keyed by a SHA-256 of the dataset + pipeline settings; rebuilt only when the data changes | No TF-IDF re-fit on restart; startup 61 ms → 40 ms |
| In-memory LRU cache (256 entries) of component scores per preference set; `min_rating` and `top_n` are applied fresh, so filters stay correct | Repeat recommendation 5.4 ms → 1.4 ms; per-movie explanation 5.4 ms → 0.5 ms |
| LRU cache of keyword TF-IDF vectors | Repeated themes skip `vectorizer.transform` |
| Precomputed row norms, serialised movies, and keyword tokens; vectorised year scoring; explanation terms read straight from the CSR arrays | Response building about 4× faster |

Tests cover cache hits and misses, a cache hit that still applies a new `min_rating`, no re-fit when a valid disk cache exists, invalidation when data changes, and recovery from a corrupt cache file.
