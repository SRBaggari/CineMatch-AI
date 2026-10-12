"""HTTP endpoints. All routes are mounted under the /api prefix in main.py."""

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from . import __version__
from .recommender import EmptyPreferencesError, RecommendationEngine, UserPreferences
from .schemas import (
    HealthResponse,
    Metadata,
    Movie,
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


@router.get("/meta", response_model=Metadata, tags=["system"])
def metadata(engine: RecommendationEngine = Depends(get_engine)):
    """Genres, moods, keywords, languages and ranges used to build the preference form."""
    return engine.metadata()


@router.get("/movies", response_model=list[Movie], tags=["movies"])
def list_movies(
    search: str = Query("", max_length=100, description="Case-insensitive title search"),
    genre: str | None = Query(None, description="Filter by genre"),
    limit: int = Query(20, ge=1, le=200),
    engine: RecommendationEngine = Depends(get_engine),
):
    return engine.search_movies(search, genre, limit)


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
    """Item-to-item recommendations: movies whose TF-IDF vectors are closest to this one."""
    similar = engine.similar_movies(movie_id, top_n)
    if similar is None:
        raise HTTPException(status_code=404, detail=f"Movie {movie_id} not found")
    return {"source": engine.get_movie(movie_id), "similar": similar}


@router.post("/recommend", response_model=RecommendationResponse, tags=["recommendations"])
def recommend(payload: RecommendationRequest, engine: RecommendationEngine = Depends(get_engine)):
    """Personalised, explainable recommendations from the user's preferences."""
    try:
        return engine.recommend(UserPreferences(**payload.model_dump()))
    except EmptyPreferencesError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
