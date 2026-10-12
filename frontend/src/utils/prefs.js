// Preference state helpers shared by the preference, results and details pages.

export const FALLBACK_WEIGHTS = { genre: 0.3, keyword: 0.25, mood: 0.2, language: 0.15, year: 0.1 };
export const WEIGHT_KEYS = Object.keys(FALLBACK_WEIGHTS);
export const TOP_N_OPTIONS = [5, 10, 15, 20, 30];
// Mirror the backend's request limits (schemas.RecommendationRequest).
export const MAX_LIST_ITEMS = 20;
export const MAX_LABEL_LENGTH = 60;

export function defaultPrefs(options) {
  return {
    genres: [],
    languages: [],
    moods: [],
    keywords: [],
    likedMovies: [],
    yearMin: options?.year_min ?? 1900,
    yearMax: options?.year_max ?? 2100,
    minRating: 0,
    strictLanguages: false,
    strictYears: false,
    topN: options?.default_top_n ?? 10,
    weights: { ...(options?.default_weights ?? FALLBACK_WEIGHTS) },
    useFeedback: true,
  };
}

function uniqueBy(list, keyOf) {
  const seen = new Set();
  return list.filter((item) => {
    const key = keyOf(item);
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

export function normalizeKeyword(value) {
  return value.trim().replace(/\s+/g, ' ').slice(0, MAX_LABEL_LENGTH);
}

// Only the five known components, as finite numbers in [0, 1]; defaults if unusable.
export function sanitizeWeights(saved, defaults = FALLBACK_WEIGHTS) {
  if (!saved || typeof saved !== 'object') return { ...defaults };
  const weights = {};
  for (const key of WEIGHT_KEYS) {
    const value = Number(saved[key]);
    weights[key] = Number.isFinite(value) ? Math.min(1, Math.max(0, value)) : defaults[key];
  }
  return WEIGHT_KEYS.some((k) => weights[k] > 0) ? weights : { ...defaults };
}

export function nearestTopN(value, fallback = 10) {
  if (!Number.isFinite(value)) return fallback;
  return TOP_N_OPTIONS.reduce((best, n) => (Math.abs(n - value) < Math.abs(best - value) ? n : best), TOP_N_OPTIONS[0]);
}

// Drop saved values that no longer exist in the catalogue, enforce request limits and clamp ranges.
export function sanitizePrefs(saved, options) {
  const base = defaultPrefs(options);
  if (!saved || typeof saved !== 'object') return base;
  const keep = (list, allowed) =>
    Array.isArray(list) ? [...new Set(list.filter((v) => typeof v === 'string' && v in allowed))].slice(0, MAX_LIST_ITEMS) : [];
  const clampYear = (y, fallback) =>
    Number.isFinite(y) ? Math.min(options.year_max, Math.max(options.year_min, Math.round(y))) : fallback;
  const yearMin = clampYear(saved.yearMin, base.yearMin);
  const yearMax = clampYear(saved.yearMax, base.yearMax);
  const keywords = Array.isArray(saved.keywords)
    ? uniqueBy(
        saved.keywords.filter((k) => typeof k === 'string' && k.trim()).map(normalizeKeyword),
        (k) => k.toLowerCase(),
      ).slice(0, MAX_LIST_ITEMS)
    : [];
  const likedMovies = Array.isArray(saved.likedMovies)
    ? uniqueBy(
        saved.likedMovies.filter((m) => m && Number.isInteger(m.movie_id) && m.movie_id > 0 && typeof m.title === 'string'),
        (m) => m.movie_id,
      ).slice(0, MAX_LIST_ITEMS)
    : [];
  return {
    ...base,
    genres: keep(saved.genres, options.genres),
    languages: keep(saved.languages, options.languages),
    moods: keep(saved.moods, options.moods),
    keywords,
    likedMovies,
    yearMin: Math.min(yearMin, yearMax),
    yearMax: Math.max(yearMin, yearMax),
    minRating: Number.isFinite(saved.minRating) ? Math.min(9.5, Math.max(0, saved.minRating)) : 0,
    strictLanguages: Boolean(saved.strictLanguages),
    strictYears: Boolean(saved.strictYears),
    topN: Number.isFinite(saved.topN) ? nearestTopN(saved.topN, base.topN) : base.topN,
    weights: sanitizeWeights(saved.weights, base.weights),
    useFeedback: saved.useFeedback !== false,
  };
}

export function hasYearPreference(prefs, options) {
  return Boolean(options) && (prefs.yearMin > options.year_min || prefs.yearMax < options.year_max);
}

export function hasPreference(prefs, options) {
  return (
    prefs.genres.length + prefs.languages.length + prefs.moods.length + prefs.keywords.length + prefs.likedMovies.length >
      0 || hasYearPreference(prefs, options)
  );
}

// Which score components the backend will use for these preferences
// (same rules as RecommendationEngine._compute_scores; liked movies imply genre,
// mood and theme signals, and a strict filter is not scored unless it is the only one).
export function activeComponents(prefs, options) {
  const liked = prefs.likedMovies.length > 0;
  const active = {
    genre: prefs.genres.length > 0 || liked,
    keyword: prefs.keywords.length > 0 || liked,
    mood: prefs.moods.length > 0 || liked,
    language: prefs.languages.length > 0,
    year: hasYearPreference(prefs, options),
  };
  for (const [key, strict] of [['language', prefs.strictLanguages], ['year', prefs.strictYears]]) {
    const others = WEIGHT_KEYS.some((k) => k !== key && active[k]);
    if (strict && active[key] && others) active[key] = false;
  }
  return active;
}

// Sum of the weights the backend will actually use; 0 means every used weight is zero.
export function activeWeightTotal(prefs, options) {
  const active = activeComponents(prefs, options);
  return WEIGHT_KEYS.reduce((sum, k) => sum + (active[k] ? prefs.weights[k] : 0), 0);
}

// Request body for POST /api/recommendations and /api/movies/{id}/explain.
export function toPayload(prefs, options) {
  return {
    genres: prefs.genres,
    languages: prefs.languages,
    moods: prefs.moods,
    keywords: prefs.keywords,
    liked_movie_ids: prefs.likedMovies.map((m) => m.movie_id),
    // A slider left at the catalogue bounds means "no year preference".
    year_min: prefs.yearMin > options.year_min ? prefs.yearMin : null,
    year_max: prefs.yearMax < options.year_max ? prefs.yearMax : null,
    min_rating: prefs.minRating,
    strict_years: prefs.strictYears,
    strict_languages: prefs.strictLanguages,
    top_n: prefs.topN,
    weights: prefs.weights,
    use_feedback: prefs.useFeedback !== false,
  };
}

export function countSelections(prefs, options) {
  return (
    prefs.genres.length +
    prefs.languages.length +
    prefs.moods.length +
    prefs.keywords.length +
    prefs.likedMovies.length +
    (hasYearPreference(prefs, options) ? 1 : 0) +
    (prefs.minRating > 0 ? 1 : 0)
  );
}
