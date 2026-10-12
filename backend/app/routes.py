"""HTTP endpoints. All routes are mounted under the /api prefix in main.py."""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response

from . import __version__
from .analytics import build_analytics
from .recommender import (
    EmptyPreferencesError,
    FeedbackProfile,
    InvalidPreferenceError,
    RecommendationEngine,
    UserPreferences,
)
from .schemas import (
    Analytics,
    DatasetInfo,
    FeedbackList,
    FeedbackState,
    FeedbackUpdate,
    HealthResponse,
    Movie,
    MovieExplanation,
    MovieList,
    PreferenceOptions,
    RecommendationRequest,
    RecommendationResponse,
    SearchRequest,
    SearchResponse,
    SimilarMoviesResponse,
)
from .store import UNSET, Store

router = APIRouter()


def get_engine(request: Request) -> RecommendationEngine:
    return request.app.state.engine


def get_store(request: Request) -> Store:
    return request.app.state.store


def feedback_profile(store: Store, enabled: bool) -> FeedbackProfile | None:
    return FeedbackProfile(**store.feedback_sets()) if enabled else None


def bad_request(exc: Exception) -> HTTPException:
    return HTTPException(status_code=422, detail=str(exc))


# ---------------------------------------------------------------- system
@router.get("/health", response_model=HealthResponse, tags=["system"])
def health(engine: RecommendationEngine = Depends(get_engine)):
    return {"status": "ok", "movies_loaded": len(engine.movies), "version": __version__}


@router.get("/dataset", response_model=DatasetInfo, tags=["system"])
def dataset_info(engine: RecommendationEngine = Depends(get_engine)):
    """Dataset size, vocabulary and provenance (the data is curated, not verified)."""
    return engine.dataset_info()


@router.get("/analytics", response_model=Analytics, tags=["system"])
def analytics(engine: RecommendationEngine = Depends(get_engine), store: Store = Depends(get_store)):
    """Catalogue distributions plus usage statistics recorded locally in SQLite."""
    return build_analytics(engine, store)


@router.get("/preferences/options", response_model=PreferenceOptions, tags=["preferences"])
def preference_options(engine: RecommendationEngine = Depends(get_engine)):
    """Every genre, mood, language and popular keyword a user can choose, plus default weights."""
    return engine.preference_options()


# ---------------------------------------------------------------- movies
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


@router.post("/movies/search", response_model=SearchResponse, tags=["movies"])
def search_movies(
    payload: SearchRequest,
    engine: RecommendationEngine = Depends(get_engine),
    store: Store = Depends(get_store),
):
    """Search by title and filter by genre, language and release year; sort by relevance or rating."""
    prefs = payload.preferences
    try:
        return engine.search(
            query=payload.query,
            genres=payload.genres,
            languages=payload.languages,
            year_min=payload.year_min,
            year_max=payload.year_max,
            sort=payload.sort,
            prefs=UserPreferences(**prefs.engine_fields()) if prefs else None,
            feedback=feedback_profile(store, prefs.use_feedback) if prefs else None,
            limit=payload.limit,
            offset=payload.offset,
        )
    except (EmptyPreferencesError, InvalidPreferenceError) as exc:
        raise bad_request(exc) from exc


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
    """Item-to-item recommendations from the cached movie feature vectors."""
    similar = engine.similar_movies(movie_id, top_n)
    if similar is None:
        raise HTTPException(status_code=404, detail=f"Movie {movie_id} not found")
    return {"source": engine.get_movie(movie_id), "similar": similar}


# ---------------------------------------------------------------- recommendations
@router.post("/recommendations", response_model=RecommendationResponse, tags=["recommendations"])
def recommend(
    payload: RecommendationRequest,
    engine: RecommendationEngine = Depends(get_engine),
    store: Store = Depends(get_store),
):
    """Ranked, explained recommendations for the submitted preferences."""
    try:
        result = engine.recommend(
            UserPreferences(**payload.engine_fields()), feedback_profile(store, payload.use_feedback)
        )
    except (EmptyPreferencesError, InvalidPreferenceError) as exc:
        raise bad_request(exc) from exc
    store.log_recommendation(result["profile"], result["recommendations"], result["profile"]["feedback_applied"])
    return result


@router.post("/movies/{movie_id}/explain", response_model=MovieExplanation, tags=["recommendations"])
def explain_movie(
    movie_id: int,
    payload: RecommendationRequest,
    engine: RecommendationEngine = Depends(get_engine),
    store: Store = Depends(get_store),
):
    """Score breakdown and reasons for one movie under the submitted preferences."""
    try:
        result = engine.explain(
            UserPreferences(**payload.engine_fields()), movie_id, feedback_profile(store, payload.use_feedback)
        )
    except (EmptyPreferencesError, InvalidPreferenceError) as exc:
        raise bad_request(exc) from exc
    if result is None:
        raise HTTPException(status_code=404, detail=f"Movie {movie_id} not found")
    return result


# ---------------------------------------------------------------- feedback
@router.get("/feedback", response_model=FeedbackList, tags=["feedback"])
def list_feedback(engine: RecommendationEngine = Depends(get_engine), store: Store = Depends(get_store)):
    """Likes, dislikes and favourites saved on this installation (newest first)."""
    items = [
        {**entry, "movie": engine.get_movie(entry["movie_id"])}
        for entry in sorted(store.get_feedback().values(), key=lambda e: e["updated_at"], reverse=True)
        if engine.get_movie(entry["movie_id"]) is not None
    ]
    return {
        "items": items,
        "counts": {
            "likes": sum(i["reaction"] == "like" for i in items),
            "dislikes": sum(i["reaction"] == "dislike" for i in items),
            "favorites": sum(i["favorite"] for i in items),
        },
    }


@router.put("/feedback/{movie_id}", response_model=FeedbackState, tags=["feedback"])
def update_feedback(
    movie_id: int,
    payload: FeedbackUpdate,
    engine: RecommendationEngine = Depends(get_engine),
    store: Store = Depends(get_store),
):
    """Like / dislike / clear a reaction and add / remove a favourite. Omitted fields stay unchanged."""
    if engine.get_movie(movie_id) is None:
        raise HTTPException(status_code=404, detail=f"Movie {movie_id} not found")
    fields = payload.model_fields_set
    state = store.set_feedback(
        movie_id,
        reaction=payload.reaction if "reaction" in fields else UNSET,
        favorite=payload.favorite if "favorite" in fields else UNSET,
    )
    return state or {"movie_id": movie_id, "reaction": None, "favorite": False}


@router.delete("/feedback/{movie_id}", status_code=204, tags=["feedback"])
def delete_feedback(movie_id: int, store: Store = Depends(get_store)):
    store.clear_feedback(movie_id)
    return Response(status_code=204)


@router.delete("/feedback", status_code=204, tags=["feedback"])
def clear_feedback(store: Store = Depends(get_store)):
    """Remove all saved feedback."""
    store.clear_feedback()
    return Response(status_code=204)
