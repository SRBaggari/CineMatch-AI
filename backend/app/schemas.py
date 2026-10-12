"""Pydantic request / response models (also drive the OpenAPI docs at /docs)."""

from pydantic import BaseModel, Field, model_validator

from .config import DEFAULT_TOP_N, MAX_TOP_N


class Movie(BaseModel):
    movie_id: int
    title: str
    year: int
    genres: list[str]
    director: str
    cast: list[str]
    keywords: list[str]
    moods: list[str]
    overview: str
    rating: float
    runtime: int
    language: str


class RecommendationRequest(BaseModel):
    genres: list[str] = Field(default_factory=list, examples=[["Science Fiction", "Thriller"]])
    moods: list[str] = Field(default_factory=list, examples=[["Mind-Bending"]])
    keywords: list[str] = Field(default_factory=list, examples=[["time travel"]])
    liked_movie_ids: list[int] = Field(default_factory=list, examples=[[6]])
    year_min: int | None = Field(default=None, ge=1900, le=2100)
    year_max: int | None = Field(default=None, ge=1900, le=2100)
    min_rating: float = Field(default=0.0, ge=0, le=10)
    languages: list[str] = Field(default_factory=list)
    top_n: int = Field(default=DEFAULT_TOP_N, ge=1, le=MAX_TOP_N)

    @model_validator(mode="after")
    def check_year_range(self):
        if self.year_min is not None and self.year_max is not None and self.year_min > self.year_max:
            raise ValueError("year_min must be less than or equal to year_max")
        return self


class ScoreComponent(BaseModel):
    score: float
    weight: float
    contribution: float


class SimilarTo(BaseModel):
    movie_id: int
    title: str
    similarity: float
    shared_director: bool
    shared_cast: list[str]
    shared_keywords: list[str]


class Explanation(BaseModel):
    reasons: list[str]
    matched_genres: list[str]
    matched_moods: list[str]
    matched_keywords: list[str]
    shared_features: list[str]
    similar_to: SimilarTo | None = None


class Recommendation(BaseModel):
    rank: int
    movie: Movie
    score: float
    match_percent: int
    score_breakdown: dict[str, ScoreComponent]
    explanation: Explanation


class ProfileTerm(BaseModel):
    term: str
    weight: float


class LikedMovieRef(BaseModel):
    movie_id: int
    title: str


class TasteProfile(BaseModel):
    top_terms: list[ProfileTerm]
    genres: list[str]
    moods: list[str]
    genres_inferred: bool
    moods_inferred: bool
    liked_movies: list[LikedMovieRef]
    weights: dict[str, float]


class RecommendationResponse(BaseModel):
    recommendations: list[Recommendation]
    profile: TasteProfile
    candidates_considered: int
    total_movies: int
    warnings: list[str]


class SimilarMovie(BaseModel):
    movie: Movie
    similarity: float
    match_percent: int
    shared_genres: list[str]
    shared_moods: list[str]
    shared_keywords: list[str]
    shared_cast: list[str]
    shared_director: bool
    shared_features: list[str]


class SimilarMoviesResponse(BaseModel):
    source: Movie
    similar: list[SimilarMovie]


class Metadata(BaseModel):
    total_movies: int
    vocabulary_size: int
    genres: dict[str, int]
    moods: dict[str, int]
    popular_keywords: dict[str, int]
    languages: dict[str, int]
    year_min: int
    year_max: int
    rating_min: float
    rating_max: float
    score_weights: dict[str, float]
    field_weights: dict[str, int]


class HealthResponse(BaseModel):
    status: str
    movies_loaded: int
    version: str
