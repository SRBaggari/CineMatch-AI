import { useCallback, useEffect, useState } from 'react';
import { LoaderCircle, RefreshCw, TriangleAlert } from 'lucide-react';
import { api } from './api/client.js';
import EmptyState from './components/EmptyState.jsx';
import Header from './components/Header.jsx';
import HowItWorks from './components/HowItWorks.jsx';
import MovieCard from './components/MovieCard.jsx';
import MovieModal from './components/MovieModal.jsx';
import PreferencePanel from './components/PreferencePanel.jsx';
import TasteProfile from './components/TasteProfile.jsx';

function defaultPrefs(meta) {
  return {
    genres: [],
    moods: [],
    keywords: [],
    likedMovies: [],
    yearMin: meta?.year_min ?? 1900,
    yearMax: meta?.year_max ?? 2100,
    minRating: 0,
    languages: [],
    topN: 12,
  };
}

function toPayload(prefs) {
  return {
    genres: prefs.genres,
    moods: prefs.moods,
    keywords: prefs.keywords,
    liked_movie_ids: prefs.likedMovies.map((m) => m.movie_id),
    year_min: prefs.yearMin,
    year_max: prefs.yearMax,
    min_rating: prefs.minRating,
    languages: prefs.languages,
    top_n: prefs.topN,
  };
}

export default function App() {
  const [meta, setMeta] = useState(null);
  const [status, setStatus] = useState({ online: false, checking: true, movies: 0 });
  const [prefs, setPrefs] = useState(defaultPrefs(null));
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [stale, setStale] = useState(false);
  const [selected, setSelected] = useState(null);

  const loadMeta = useCallback(() => {
    setStatus((s) => ({ ...s, checking: true }));
    setError('');
    Promise.all([api.health(), api.meta()])
      .then(([health, metadata]) => {
        setMeta(metadata);
        setPrefs(defaultPrefs(metadata));
        setStatus({ online: true, checking: false, movies: health.movies_loaded });
      })
      .catch((e) => {
        setStatus({ online: false, checking: false, movies: 0 });
        setError(e.message);
      });
  }, []);

  useEffect(loadMeta, [loadMeta]);

  const runRecommend = useCallback(async (currentPrefs) => {
    setLoading(true);
    setError('');
    try {
      setResult(await api.recommend(toPayload(currentPrefs)));
      setStale(false);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  const updatePrefs = (updater) => {
    setPrefs(updater);
    if (result) setStale(true);
  };

  const applyPreset = (preset) => {
    const next = { ...defaultPrefs(meta), ...preset.prefs };
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

  const hasSignal =
    prefs.genres.length + prefs.moods.length + prefs.keywords.length + prefs.likedMovies.length > 0;

  return (
    <div className="app">
      <Header status={status} />

      <section className="hero">
        <h2>
          Movies matched to <span className="gradient-text">your taste</span>, explained.
        </h2>
        <p>
          A content-based recommender built with TF-IDF, cosine similarity and hybrid scoring. Every recommendation shows
          exactly why it was chosen.
        </p>
      </section>

      {!meta && (
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
              <button type="button" className="btn btn-primary" onClick={loadMeta}>
                <RefreshCw size={16} /> Retry
              </button>
            </>
          )}
        </div>
      )}

      {meta && (
        <main className="layout">
          <aside>
            <PreferencePanel
              meta={meta}
              prefs={prefs}
              setPrefs={updatePrefs}
              onSubmit={() => runRecommend(prefs)}
              onReset={() => {
                setPrefs(defaultPrefs(meta));
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
                <p>Building your taste profile and scoring every movie…</p>
              </div>
            )}

            {result && (
              <>
                {stale && (
                  <div className="stale-banner">
                    Your preferences changed.
                    <button type="button" className="btn btn-small btn-primary" onClick={() => runRecommend(prefs)} disabled={loading || !hasSignal}>
                      {loading ? <LoaderCircle size={14} className="spin" /> : <RefreshCw size={14} />} Update results
                    </button>
                  </div>
                )}
                <TasteProfile result={result} />
                <div className="results-heading">
                  <h2>Top {result.recommendations.length} recommendations</h2>
                  <span className="muted small">Ranked by hybrid score</span>
                </div>
                <div className={`card-list ${loading ? 'is-loading' : ''}`}>
                  {result.recommendations.map((rec) => (
                    <MovieCard
                      key={rec.movie.movie_id}
                      rec={rec}
                      isLiked={likedIds.has(rec.movie.movie_id)}
                      onToggleLike={toggleLike}
                      onOpen={setSelected}
                    />
                  ))}
                </div>
              </>
            )}
          </div>
        </main>
      )}

      <HowItWorks meta={meta} />

      <footer className="footer">
        CineMatch AI · DecodeLabs AI Industrial Training · Project 3: AI Recommendation Logic
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
