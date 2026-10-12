// Preference state helpers shared by the preference, results and details pages.

export const FALLBACK_WEIGHTS = { genre: 0.3, keyword: 0.25, mood: 0.2, language: 0.15, year: 0.1 };

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

// Drop saved values that no longer exist in the catalogue and clamp ranges.
export function sanitizePrefs(saved, options) {
  const base = defaultPrefs(options);
  if (!saved || typeof saved !== 'object') return base;
  const keep = (list, allowed) => (Array.isArray(list) ? list.filter((v) => v in allowed) : []);
  const clampYear = (y, fallback) =>
    Number.isFinite(y) ? Math.min(options.year_max, Math.max(options.year_min, y)) : fallback;
  const yearMin = clampYear(saved.yearMin, base.yearMin);
  const yearMax = clampYear(saved.yearMax, base.yearMax);
  return {
    ...base,
    genres: keep(saved.genres, options.genres),
    languages: keep(saved.languages, options.languages),
    moods: keep(saved.moods, options.moods),
    keywords: Array.isArray(saved.keywords) ? saved.keywords.filter((k) => typeof k === 'string' && k.trim()) : [],
    likedMovies: Array.isArray(saved.likedMovies)
      ? saved.likedMovies.filter((m) => m && Number.isInteger(m.movie_id) && typeof m.title === 'string')
      : [],
    yearMin: Math.min(yearMin, yearMax),
    yearMax: Math.max(yearMin, yearMax),
    minRating: Number.isFinite(saved.minRating) ? Math.min(10, Math.max(0, saved.minRating)) : 0,
    strictLanguages: Boolean(saved.strictLanguages),
    strictYears: Boolean(saved.strictYears),
    topN: Number.isInteger(saved.topN) ? Math.min(options.max_top_n, Math.max(1, saved.topN)) : base.topN,
    weights: { ...base.weights, ...(saved.weights && typeof saved.weights === 'object' ? saved.weights : {}) },
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
