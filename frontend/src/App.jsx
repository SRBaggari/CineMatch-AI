import { useCallback, useEffect, useState } from 'react';
import { LoaderCircle, RefreshCw, SearchX, TriangleAlert } from 'lucide-react';
import { api } from './api/client.js';
import EmptyState from './components/EmptyState.jsx';
import Header from './components/Header.jsx';
import HowItWorks from './components/HowItWorks.jsx';
import MovieCard from './components/MovieCard.jsx';
import MovieModal from './components/MovieModal.jsx';
import PreferencePanel from './components/PreferencePanel.jsx';
import TasteProfile, { FilterReport } from './components/TasteProfile.jsx';

function defaultPrefs(options) {
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
    weights: { ...(options?.default_weights ?? { genre: 0.3, keyword: 0.25, mood: 0.2, language: 0.15, year: 0.1 }) },
  };
}

function toPayload(prefs, options) {
  // A slider left at the catalogue bounds means "no year preference".
  const yearMin = prefs.yearMin > options.year_min ? prefs.yearMin : null;
  const yearMax = prefs.yearMax < options.year_max ? prefs.yearMax : null;
  return {
    genres: prefs.genres,
    languages: prefs.languages,
    moods: prefs.moods,
    keywords: prefs.keywords,
    liked_movie_ids: prefs.likedMovies.map((m) => m.movie_id),
    year_min: yearMin,
    year_max: yearMax,
    min_rating: prefs.minRating,
    strict_years: prefs.strictYears,
    strict_languages: prefs.strictLanguages,
    top_n: prefs.topN,
    weights: prefs.weights,
  };
}

function hasPreference(prefs, options) {
  if (!options) return false;
  const yearPref = prefs.yearMin > options.year_min || prefs.yearMax < options.year_max;
  return (
    prefs.genres.length + prefs.languages.length + prefs.moods.length + prefs.keywords.length + prefs.likedMovies.length >
      0 || yearPref
  );
}

export default function App() {
  const [options, setOptions] = useState(null);
  const [dataset, setDataset] = useState(null);
  const [status, setStatus] = useState({ online: false, checking: true, movies: 0 });
  const [prefs, setPrefs] = useState(defaultPrefs(null));
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [stale, setStale] = useState(false);
  const [selected, setSelected] = useState(null);

  const loadOptions = useCallback(() => {
    setStatus((s) => ({ ...s, checking: true }));
    setError('');
    Promise.all([api.health(), api.options(), api.dataset()])
      .then(([health, opts, info]) => {
        setOptions(opts);
        setDataset(info);
        setPrefs(defaultPrefs(opts));
        setStatus({ online: true, checking: false, movies: health.movies_loaded });
      })
      .catch((e) => {
        setStatus({ online: false, checking: false, movies: 0 });
        setError(e.message);
      });
  }, []);

  useEffect(loadOptions, [loadOptions]);

  const runRecommend = useCallback(
    async (currentPrefs) => {
      setLoading(true);
      setError('');
      try {
        setResult(await api.recommend(toPayload(currentPrefs, options)));
        setStale(false);
      } catch (e) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    },
    [options],
  );

  const updatePrefs = (updater) => {
    setPrefs(updater);
    if (result) setStale(true);
  };

  const applyPreset = (preset) => {
    const next = { ...defaultPrefs(options), ...preset.prefs };
    setPrefs(next);
    runRecommend(next);
  };

  const likedIds = new Set(prefs.likedMovies.map((m) => m.movie_id));
  const toggleLike = (movie) =>
    updatePrefs((p) => ({
      ...p,
      likedMovies: likedIds.has(movie.movie_id)
        ? p.likedMovies.filter((m) => m.movie_id !== movie.movie_id)
        : [...p.likedMovies, { movie_id: movie.movie_id, title: movie.title, year: movie.year }],
    }));

  const hasSignal = hasPreference(prefs, options);
  const recs = result?.recommendations ?? [];

  return (
    <div className="app">
      <Header status={status} />

      <section className="hero">
        <h2>
          Movies matched to <span className="gradient-text">your taste</span>, explained.
        </h2>
        <p>
          A content-based recommender built on feature vectors, TF-IDF and cosine similarity with weighted preference
          matching. Every recommendation shows its score components and the reasons behind it.
        </p>
      </section>

      {!options && (
        <div className="panel center-panel">
          {status.checking ? (
            <p>
              <LoaderCircle className="spin" size={18} /> Connecting to the recommendation engine…
            </p>
          ) : (
            <>
              <TriangleAlert size={32} />
              <h2>Backend not reachable</h2>
              <p className="muted">{error}</p>
              <p className="muted small">
                Start it with <code>uvicorn app.main:app --reload --port 8000</code> inside the backend folder.
              </p>
              <button type="button" className="btn btn-primary" onClick={loadOptions}>
                <RefreshCw size={16} /> Retry
              </button>
            </>
          )}
        </div>
      )}

      {options && (
        <main className="layout">
          <aside>
            <PreferencePanel
              options={options}
              prefs={prefs}
              setPrefs={updatePrefs}
              onSubmit={() => runRecommend(prefs)}
              onReset={() => {
                setPrefs(defaultPrefs(options));
                setResult(null);
                setStale(false);
                setError('');
              }}
              loading={loading}
              hasSignal={hasSignal}
            />
          </aside>

          <div className="results">
            {error && (
              <div className="alert">
                <TriangleAlert size={16} /> {error}
              </div>
            )}

            {!result && !loading && <EmptyState onPreset={applyPreset} />}

            {loading && !result && (
              <div className="panel center-panel">
                <LoaderCircle className="spin" size={28} />
                <p>Scoring every movie against your preferences…</p>
              </div>
            )}

            {result && (
              <>
                {stale && (
                  <div className="stale-banner">
                    Your preferences changed.
                    <button
                      type="button"
                      className="btn btn-small btn-primary"
                      onClick={() => runRecommend(prefs)}
                      disabled={loading || !hasSignal}
                    >
                      {loading ? <LoaderCircle size={14} className="spin" /> : <RefreshCw size={14} />} Update results
                    </button>
                  </div>
                )}

                <TasteProfile result={result} />

                {recs.length === 0 ? (
                  <div className="panel center-panel no-results">
                    <SearchX size={36} />
                    <h2>No matching movies</h2>
                    <p className="muted">{result.message}</p>
                    <FilterReport report={result.filter_report} />
                  </div>
                ) : (
                  <>
                    <div className="results-heading">
                      <h2>Top {recs.length} recommendations</h2>
                      <span className="muted small">Ranked by relevance score (0–1), not a probability</span>
                    </div>
                    <div className={`card-list ${loading ? 'is-loading' : ''}`}>
                      {recs.map((rec) => (
                        <MovieCard
                          key={rec.movie_id}
                          rec={rec}
                          isLiked={likedIds.has(rec.movie_id)}
                          onToggleLike={toggleLike}
                          onOpen={setSelected}
                        />
                      ))}
                    </div>
                  </>
                )}
              </>
            )}
          </div>
        </main>
      )}

      <HowItWorks dataset={dataset} />

      <footer className="footer">
        <p>CineMatch AI · DecodeLabs AI Industrial Training · Project 3: AI Recommendation Logic</p>
        {dataset && <p className="provenance">Dataset note: {dataset.provenance}</p>}
      </footer>

      {selected && (
        <MovieModal
          movie={selected}
          onClose={() => setSelected(null)}
          onSelect={setSelected}
          isLiked={likedIds.has(selected.movie_id)}
          onToggleLike={toggleLike}
        />
      )}
    </div>
  );
}
