"""Pydantic request / response models (they also drive the OpenAPI docs at /docs)."""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from .config import DEFAULT_TOP_N, MAX_TOP_N

Label = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=60)]
MovieId = Annotated[int, Field(ge=1)]


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


class MovieList(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[Movie]


# ------------------------------------------------------------------ request
class ScoreWeights(BaseModel):
    """Relative importance of each component. Any non-negative numbers work:
    they are re-normalised to sum to 1 over the components you used."""

    model_config = ConfigDict(extra="forbid")

    genre: float = Field(0.30, ge=0, le=100)
    keyword: float = Field(0.25, ge=0, le=100)
    mood: float = Field(0.20, ge=0, le=100)
    language: float = Field(0.15, ge=0, le=100)
    year: float = Field(0.10, ge=0, le=100)

    @model_validator(mode="after")
    def not_all_zero(self):
        if sum(self.model_dump().values()) <= 0:
            raise ValueError("at least one weight must be greater than 0")
        return self


class RecommendationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    genres: list[Label] = Field(default_factory=list, max_length=20, examples=[["Science Fiction", "Thriller"]])
    languages: list[Label] = Field(default_factory=list, max_length=20, examples=[["English"]])
    moods: list[Label] = Field(default_factory=list, max_length=20, examples=[["Mind-Bending"]])
    keywords: list[Label] = Field(default_factory=list, max_length=20, examples=[["time travel", "dreams"]])
    liked_movie_ids: list[MovieId] = Field(default_factory=list, max_length=20)
    exclude_movie_ids: list[MovieId] = Field(default_factory=list, max_length=200)
    year_min: int | None = Field(default=None, ge=1880, le=2100, examples=[1995])
    year_max: int | None = Field(default=None, ge=1880, le=2100, examples=[2020])
    min_rating: float = Field(default=0.0, ge=0, le=10, examples=[7.5])
    strict_years: bool = Field(default=False, description="Treat the year range as a hard filter")
    strict_languages: bool = Field(default=False, description="Treat languages as a hard filter")
    top_n: int = Field(default=DEFAULT_TOP_N, ge=1, le=MAX_TOP_N)
    weights: ScoreWeights | None = None

    @model_validator(mode="after")
    def check_year_range(self):
        if self.year_min is not None and self.year_max is not None and self.year_min > self.year_max:
            raise ValueError("year_min must be less than or equal to year_max")
        return self


# ------------------------------------------------------------------ response
class ScoreComponent(BaseModel):
    value: float = Field(description="Normalised component score in [0, 1] used in the weighted sum")
    raw: float = Field(description="Score before normalisation (differs only for keyword: raw TF-IDF cosine)")
    weight: float = Field(description="Effective weight after re-normalisation")
    contribution: float = Field(description="weight × value")
    active: bool = Field(description="False when the user gave no preference for this component")


class MatchedPreferences(BaseModel):
    genres: list[str]
    moods: list[str]
    language: str | None
    keywords: list[str]
    year_in_range: bool | None


class SimilarLiked(BaseModel):
    movie_id: int
    title: str
    similarity: float


class Recommendation(BaseModel):
    rank: int
    movie_id: int
    title: str
    movie: Movie
    score: float = Field(description="Weighted relevance score in [0, 1]; not a probability")
    components: dict[str, ScoreComponent]
    matched: MatchedPreferences
    reasons: list[str]
    top_terms: list[str]
    similar_to: SimilarLiked | None = None


class MovieExplanation(Recommendation):
    """How one movie scores against the preferences, even if it is not in the top N."""

    rank: int | None = Field(description="Position in the full ranking, or null if a hard filter removes it")
    passes_filters: bool
    filtered_by: list[str] = Field(description="Hard filters that remove this movie")
    candidates: int = Field(description="Number of movies that pass every filter")
    weights: dict[str, float]


class ProfileTerm(BaseModel):
    term: str
    weight: float


class LikedMovieRef(BaseModel):
    movie_id: int
    title: str


class UserProfile(BaseModel):
    genres: list[str]
    moods: list[str]
    languages: list[str]
    keywords: list[str]
    year_min: int | None
    year_max: int | None
    min_rating: float
    genres_inferred: bool
    moods_inferred: bool
    liked_movies: list[LikedMovieRef]
    top_terms: list[ProfileTerm]
    active_components: list[str]
    weights: dict[str, float]


class RecommendationResponse(BaseModel):
    recommendations: list[Recommendation]
    profile: UserProfile
    filter_report: dict[str, int] = Field(description="Number of movies left after each hard filter")
    total_movies: int
    message: str | None = Field(description="Explanation when no movies are recommended")
    warnings: list[str]


class SimilarMovie(BaseModel):
    movie: Movie
    similarity: float
    shared_genres: list[str]
    shared_moods: list[str]
    shared_keywords: list[str]
    same_language: bool
    same_director: bool
    shared_cast: list[str]


class SimilarMoviesResponse(BaseModel):
    source: Movie
    similar: list[SimilarMovie]


class PreferenceOptions(BaseModel):
    genres: dict[str, int]
    moods: dict[str, int]
    languages: dict[str, int]
    popular_keywords: dict[str, int]
    year_min: int
    year_max: int
    rating_min: float
    rating_max: float
    default_weights: dict[str, float]
    year_decay_years: int
    default_top_n: int
    max_top_n: int


class DatasetInfo(BaseModel):
    name: str
    synthetic: bool
    verified: bool
    provenance: str
    total_movies: int
    genres: int
    moods: int
    languages: int
    vocabulary_size: int
    year_range: list[int]


class HealthResponse(BaseModel):
    status: str
    movies_loaded: int
    version: str
