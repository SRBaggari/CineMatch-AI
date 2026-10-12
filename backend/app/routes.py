"""HTTP endpoints. All routes are mounted under the /api prefix in main.py."""

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from . import __version__
from .recommender import (
    EmptyPreferencesError,
    InvalidPreferenceError,
    RecommendationEngine,
    UserPreferences,
)
from .schemas import (
    DatasetInfo,
    HealthResponse,
    Movie,
    MovieList,
    PreferenceOptions,
    RecommendationRequest,
    RecommendationResponse,
    SimilarMoviesResponse,
)

router = APIRouter()


def get_engine(request: Request) -> RecommendationEngine:
    return request.app.state.engine


@router.get("/health", response_model=HealthResponse, tags=["system"])
def health(engine: RecommendationEngine = Depends(get_engine)):
    return {"status": "ok", "movies_loaded": len(engine.movies), "version": __version__}


@router.get("/dataset", response_model=DatasetInfo, tags=["system"])
def dataset_info(engine: RecommendationEngine = Depends(get_engine)):
    """Dataset size, vocabulary and provenance (the data is curated, not verified)."""
    return engine.dataset_info()


@router.get("/preferences/options", response_model=PreferenceOptions, tags=["preferences"])
def preference_options(engine: RecommendationEngine = Depends(get_engine)):
    """Every genre, mood, language and popular keyword a user can choose, plus default weights."""
    return engine.preference_options()


@router.get("/movies", response_model=MovieList, tags=["movies"])
def list_movies(
    search: str = Query("", max_length=100, description="Case-insensitive title search"),
    genre: str | None = Query(None, max_length=60),
    language: str | None = Query(None, max_length=60),
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    engine: RecommendationEngine = Depends(get_engine),
):
    return engine.list_movies(search, genre, language, limit, offset)


@router.get("/movies/{movie_id}", response_model=Movie, tags=["movies"])
def get_movie(movie_id: int, engine: RecommendationEngine = Depends(get_engine)):
    movie = engine.get_movie(movie_id)
    if movie is None:
        raise HTTPException(status_code=404, detail=f"Movie {movie_id} not found")
    return movie


@router.get("/movies/{movie_id}/similar", response_model=SimilarMoviesResponse, tags=["recommendations"])
def similar_movies(
    movie_id: int,
    top_n: int = Query(8, ge=1, le=30),
    engine: RecommendationEngine = Depends(get_engine),
):
    """Item-to-item recommendations from the combined movie feature vectors."""
    similar = engine.similar_movies(movie_id, top_n)
    if similar is None:
        raise HTTPException(status_code=404, detail=f"Movie {movie_id} not found")
    return {"source": engine.get_movie(movie_id), "similar": similar}


@router.post("/recommendations", response_model=RecommendationResponse, tags=["recommendations"])
def recommend(payload: RecommendationRequest, engine: RecommendationEngine = Depends(get_engine)):
    """Ranked, explained recommendations for the submitted preferences."""
    data = payload.model_dump()
    try:
        return engine.recommend(UserPreferences(**data))
    except (EmptyPreferencesError, InvalidPreferenceError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
