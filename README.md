# CineMatch AI — Personalized Movie Recommendation System

**DecodeLabs Artificial Intelligence Industrial Training · Project 3: AI Recommendation Logic**

CineMatch AI is a content-based movie recommendation system. It collects a user's preferences, finds matching patterns in movie metadata, calculates similarity scores, and returns ranked recommendations. Each recommendation comes with an explanation of why it was chosen.

All processing runs locally. The project uses no paid APIs, API keys, external AI services, or randomness. Every score can be traced back to the dataset and the algorithm.

| Requirement | How it is met |
|---|---|
| User preference collection | React form for genres, moods, favourite movies, themes or keywords, year range, minimum rating, languages, and result count |
| Pattern matching | Genre and mood overlap (Jaccard), keyword and theme matching, and genres and moods inferred from liked movies |
| Content-based logic | Weighted "content soup" per movie, vectorised with TF-IDF |
| Similarity scores | Cosine similarity (user profile → movie) and a precomputed movie → movie similarity matrix |
| Personalised recommendations | A hybrid score ranks every movie that passes the user's filters |
| Explainable results | Reasons, matched tags, the most similar liked movie, the strongest shared features, and a full score breakdown |

---

## 1. Tech stack

| Layer | Technology |
|---|---|
| Frontend | React 19, Vite 8, JavaScript, modern CSS (custom properties, grid), Lucide React icons |
| Backend | Python 3.10+, FastAPI, Uvicorn, Pydantic v2 |
| ML / data | Pandas, NumPy, scikit-learn (`TfidfVectorizer`, `cosine_similarity`) |
| Dataset | Local CSV with 130 curated movies (`backend/data/movies.csv`) |
| Testing | Pytest with FastAPI `TestClient` |

## 2. System architecture

```
┌──────────────────────────── Browser (React + Vite) ────────────────────────────┐
│  PreferencePanel ──► App state ──► api/client.js ──► fetch('/api/...')         │
│  TasteProfile · MovieCard · ScoreBreakdown · MovieModal (similar movies)       │
└───────────────────────────────────────┬────────────────────────────────────────┘
                                        │  Vite dev proxy  /api → 127.0.0.1:8000
┌───────────────────────────────────────▼────────────────────────────────────────┐
│ FastAPI (app/main.py)                                                          │
│   routes.py  ── validates with schemas.py (Pydantic) ──► RecommendationEngine  │
│                                                                                │
│ RecommendationEngine (app/recommender.py) — built once at startup              │
│   1. content soup per movie      4. cosine similarity (profile ↔ movies)       │
│   2. TF-IDF matrix (scikit-learn) 5. hybrid score + filters + ranking          │
│   3. user profile vector         6. explanation generation                     │
│                                                                                │
│ data_loader.py ── reads + validates + cleans ──► data/movies.csv               │
└────────────────────────────────────────────────────────────────────────────────┘
```

* When the server starts, it loads the dataset once, then builds the TF-IDF matrix and the movie-to-movie similarity matrix. Each request is a small amount of vector maths.
* The frontend calls relative `/api/...` URLs. In development, Vite proxies them to FastAPI, so no CORS setup is needed. CORS is still enabled for direct access.

## 3. Folder structure

```
CineMatch-AI/
├── backend/
│   ├── app/
│   │   ├── __init__.py        # package + version
│   │   ├── config.py          # paths, CORS origins, field weights, score weights
│   │   ├── data_loader.py     # CSV loading, validation, cleaning, token normalisation
│   │   ├── recommender.py     # RecommendationEngine: TF-IDF, similarity, scoring, explanations
│   │   ├── schemas.py         # Pydantic request/response models
│   │   ├── routes.py          # REST endpoints
│   │   └── main.py            # FastAPI app, startup (lifespan), CORS
│   ├── data/movies.csv        # dataset (130 movies)
│   ├── tests/test_recommender.py
│   ├── requirements.txt       # runtime dependencies
│   ├── requirements-dev.txt   # + pytest, httpx
│   └── pytest.ini
├── frontend/
│   ├── index.html
│   ├── vite.config.js         # dev server + /api proxy
│   ├── package.json
│   ├── public/favicon.svg
│   └── src/
│       ├── main.jsx           # React entry
│       ├── App.jsx            # state management + page layout
│       ├── styles.css         # design system + responsive layout
│       ├── api/client.js      # backend API wrapper
│       ├── hooks/useDebounce.js
│       ├── utils/genres.js    # genre → icon/colour mapping
│       └── components/
│           ├── Header.jsx          # brand + engine status
│           ├── PreferencePanel.jsx # 5-step preference form
│           ├── ChipSelector.jsx    # multi-select chips
│           ├── MovieSearch.jsx     # autocomplete for liked movies
│           ├── KeywordInput.jsx    # free-text themes + suggestions
│           ├── TasteProfile.jsx    # profile vector terms + weights
│           ├── MovieCard.jsx       # recommendation + explanation
│           ├── ScoreBreakdown.jsx  # per-component score maths
│           ├── ScoreRing.jsx       # circular match indicator
│           ├── Poster.jsx          # generated poster (no image API)
│           ├── MovieModal.jsx      # details + "more like this"
│           ├── EmptyState.jsx      # quick-start presets
│           └── HowItWorks.jsx      # algorithm explanation section
├── docs/ALGORITHM.md          # detailed algorithm walkthrough
├── scripts/                   # Windows PowerShell helpers
│   ├── setup.ps1
│   ├── start-backend.ps1
│   ├── start-frontend.ps1
│   └── start-all.ps1
└── README.md
```

## 4. Dataset schema (`backend/data/movies.csv`)

| Column | Type | Example | Notes |
|---|---|---|---|
| `movie_id` | int | `6` | Unique primary key |
| `title` | string | `Inception` | |
| `year` | int | `2010` | Used by the year filter |
| `genres` | pipe list | `Science Fiction\|Action\|Thriller` | 19 distinct genres |
| `director` | string | `Christopher Nolan` | |
| `cast` | pipe list | `Leonardo DiCaprio\|Elliot Page` | Top three billed actors |
| `keywords` | pipe list | `dreams\|heist\|reality` | Themes and plot elements |
| `moods` | pipe list | `Mind-Bending\|Action-Packed` | 15 curated moods |
| `overview` | string | `A thief who steals secrets…` | One-sentence synopsis |
| `rating` | float | `8.8` | Score out of 10, used for quality and filtering |
| `runtime` | int | `148` | Minutes |
| `language` | string | `English` | 10 languages, including Hindi, Telugu, Korean, and Japanese |

To extend the dataset, add rows that follow the same schema. The engine rebuilds automatically on the next backend start, and `data_loader.py` checks that the required columns exist.

## 5. Recommendation algorithm (summary)

`docs/ALGORITHM.md` has the full walkthrough with a worked example.

1. **Feature engineering.** Each movie becomes a text "soup": genres ×3, moods ×2, keywords ×2, director ×1, cast ×1, and the overview. Multi-word labels are squashed into single tokens, so `Science Fiction` becomes `sciencefiction` and `Christopher Nolan` becomes `christophernolan`. This keeps a person or tag as one feature.
2. **TF-IDF vectorisation.** `TfidfVectorizer(stop_words="english", sublinear_tf=True)` turns each soup into a vector. Specific terms such as *time loop* outweigh common ones such as *drama*.
3. **User profile vector.** The user's genres, moods, and keywords are vectorised the same way. The TF-IDF vectors of their liked movies are averaged. The two are blended equally and L2-normalised.
4. **Similarity.** `cosine_similarity(profile, every_movie)` gives the content score in [0, 1].
5. **Hybrid score.**

   ```
   score = 0.55·content + 0.20·Jaccard(genres) + 0.15·Jaccard(moods) + 0.10·rating_norm
   ```

   If a component has no signal (for example, the user picked no moods and liked no movies), its weight is removed and the remaining weights are re-normalised. Filters for year, minimum rating, and language are then applied, and liked movies are excluded.
6. **Explanation.** Each result includes the matched genres, moods, and keywords. It also includes the liked movie it is most similar to, with any shared director, cast, or keywords. It lists the five terms that contribute most to the cosine similarity (largest `profile_i × movie_i`) and gives a per-component score breakdown that adds up to the final score.

The same TF-IDF space also powers **"More like this"**, which shows item-to-item similarity in the movie details modal.

## 6. API reference

Interactive docs are at **http://127.0.0.1:8000/docs** when the backend is running.

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/health` | Engine status and number of movies |
| GET | `/api/meta` | Genres, moods, keywords, and languages (with counts), year and rating ranges, weights |
| GET | `/api/movies?search=&genre=&limit=` | Title search |
| GET | `/api/movies/{id}` | One movie |
| GET | `/api/movies/{id}/similar?top_n=` | Item-to-item recommendations |
| POST | `/api/recommend` | Personalised recommendations |

Example request:

```json
POST /api/recommend
{
  "genres": ["Science Fiction"],
  "moods": ["Mind-Bending"],
  "keywords": ["time travel"],
  "liked_movie_ids": [6],
  "year_min": 1990,
  "year_max": 2023,
  "min_rating": 7.5,
  "languages": [],
  "top_n": 10
}
```

The response contains `recommendations[]`, where each item has `movie`, `score`, `match_percent`, `score_breakdown`, and `explanation`. It also contains the `profile` (top profile terms, active weights, and inferred genres and moods), `candidates_considered`, and `warnings`.

## 7. Running on Windows (PowerShell)

**Prerequisites:** Python 3.10+ and Node.js 20+. This project was tested with Python 3.14 and Node 24.

### Option A: helper scripts

```powershell
cd C:\Users\rinki\CineMatch-AI

# one-time setup (venv + pip + npm)
powershell -ExecutionPolicy Bypass -File .\scripts\setup.ps1

# start backend + frontend in two new windows
powershell -ExecutionPolicy Bypass -File .\scripts\start-all.ps1
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

### Run the tests

```powershell
cd C:\Users\rinki\CineMatch-AI\backend
.\.venv\Scripts\python.exe -m pytest -v
```

### If port 8000 is busy

If another program already uses port 8000, run the backend on a different port and point the frontend proxy at it:

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

## 8. Reading the match percentage

`match_percent` is the hybrid score × 100. It is **not** rescaled to make the top result read 100%. Cosine similarity between a short preference profile and a full movie description rarely goes above 0.5, so a strong match usually scores 30–60%. Because the number is honest, it can be compared across queries, and the score breakdown shows exactly where each point came from.
