"""Pydantic request / response models (they also drive the OpenAPI docs at /docs)."""

from typing import Annotated, Literal

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
    use_feedback: bool = Field(default=True, description="Adjust scores with saved likes, dislikes and favourites")

    @model_validator(mode="after")
    def check_year_range(self):
        if self.year_min is not None and self.year_max is not None and self.year_min > self.year_max:
            raise ValueError("year_min must be less than or equal to year_max")
        return self

    def engine_fields(self) -> dict:
        """Fields understood by the engine's UserPreferences (excludes API-only flags)."""
        return self.model_dump(exclude={"use_feedback"})


class SearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: Annotated[str, StringConstraints(strip_whitespace=True, max_length=100)] = ""
    genres: list[Label] = Field(default_factory=list, max_length=20)
    languages: list[Label] = Field(default_factory=list, max_length=20)
    year_min: int | None = Field(default=None, ge=1880, le=2100)
    year_max: int | None = Field(default=None, ge=1880, le=2100)
    sort: Literal["relevance", "rating", "year", "title"] = "relevance"
    preferences: RecommendationRequest | None = Field(
        default=None, description="When given, relevance = match score for these preferences"
    )
    limit: int = Field(default=24, ge=1, le=200)
    offset: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def check_year_range(self):
        if self.year_min is not None and self.year_max is not None and self.year_min > self.year_max:
            raise ValueError("year_min must be less than or equal to year_max")
        return self


class FeedbackUpdate(BaseModel):
    """Omitted fields are left unchanged; reaction=null clears a like/dislike."""

    model_config = ConfigDict(extra="forbid")

    reaction: Literal["like", "dislike"] | None = None
    favorite: bool | None = None

    @model_validator(mode="after")
    def something_to_update(self):
        if not self.model_fields_set:
            raise ValueError("provide 'reaction' and/or 'favorite'")
        if "favorite" in self.model_fields_set and self.favorite is None:
            raise ValueError("favorite must be true or false")
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


class MovieRef(BaseModel):
    movie_id: int
    title: str


class FeedbackEffect(BaseModel):
    applied: bool = Field(description="False when there is no saved feedback or use_feedback is off")
    adjustment: float = Field(description="FEEDBACK_WEIGHT × (liked_similarity − disliked_similarity)")
    liked_similarity: float
    closest_liked: MovieRef | None
    disliked_similarity: float
    closest_disliked: MovieRef | None


class Recommendation(BaseModel):
    rank: int
    movie_id: int
    title: str
    movie: Movie
    base_score: float = Field(description="Preference-based score in [0, 1] (weighted sum of components)")
    feedback_adjustment: float = Field(description="Change from saved feedback; 0 when none is applied")
    score: float = Field(description="Final relevance score = clip(base + adjustment, 0, 1); not a probability")
    components: dict[str, ScoreComponent]
    matched: MatchedPreferences
    summary: str = Field(description="One-sentence explanation built from the matched attributes")
    reasons: list[str]
    top_terms: list[str]
    similar_to: SimilarLiked | None = None
    feedback: FeedbackEffect


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
    feedback_applied: bool


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


class SearchItem(BaseModel):
    movie: Movie
    title_relevance: float | None
    match_score: float | None
    base_score: float | None
    feedback_adjustment: float | None


class SearchResponse(BaseModel):
    total: int
    limit: int
    offset: int
    sort: str
    personalized: bool
    items: list[SearchItem]


class FeedbackItem(BaseModel):
    movie_id: int
    reaction: Literal["like", "dislike"] | None
    favorite: bool
    updated_at: str
    movie: Movie


class FeedbackList(BaseModel):
    items: list[FeedbackItem]
    counts: dict[str, int]


class FeedbackState(BaseModel):
    movie_id: int
    reaction: Literal["like", "dislike"] | None
    favorite: bool


class HistogramBin(BaseModel):
    label: str
    start: float
    end: float
    count: int


class DatasetAnalytics(BaseModel):
    total_movies: int
    genre_distribution: dict[str, int]
    mood_distribution: dict[str, int]
    language_distribution: dict[str, int]
    decade_distribution: dict[str, int]
    rating_distribution: list[HistogramBin]
    average_rating: float
    average_runtime: float
    vocabulary_size: int
    feature_source: str
    score_cache: dict[str, int]


class UsageAnalytics(BaseModel):
    total_requests: int
    recommendations_served: int
    genre_selections: dict[str, int]
    mood_selections: dict[str, int]
    language_selections: dict[str, int]
    keyword_selections: dict[str, int]
    score_distribution: list[HistogramBin]
    average_score: float | None
    most_recommended: list[dict]


class Analytics(BaseModel):
    dataset: DatasetAnalytics
    usage: UsageAnalytics
    feedback: dict[str, int]
    notes: list[str]


class HealthResponse(BaseModel):
    status: str
    movies_loaded: int
    version: str
