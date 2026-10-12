"""FastAPI application entry point.

Run from the backend folder:
    uvicorn app.main:app --reload --port 8000
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .config import APP_DESCRIPTION, APP_NAME, CORS_ORIGINS, DATA_PATH, DB_PATH, FEATURE_CACHE_DIR
from .data_loader import load_movies
from .recommender import RecommendationEngine
from .routes import router
from .store import Store

logger = logging.getLogger("cinematch")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Fit (or load from the disk cache) the TF-IDF model and similarity matrix once.
    movies = load_movies(DATA_PATH)
    app.state.engine = RecommendationEngine(movies, cache_dir=FEATURE_CACHE_DIR)
    app.state.store = Store(DB_PATH)
    logger.info(
        "Recommendation engine ready: %d movies, %d features (%s); feedback DB at %s",
        len(movies),
        len(app.state.engine.feature_names),
        app.state.engine.feature_source,
        DB_PATH,
    )
    yield


app = FastAPI(title=APP_NAME, description=APP_DESCRIPTION, version=__version__, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")


@app.get("/", include_in_schema=False)
def root():
    return {"name": APP_NAME, "version": __version__, "docs": "/docs", "api": "/api"}
