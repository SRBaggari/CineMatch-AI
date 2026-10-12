import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { ChevronDown, Info, Pencil, RefreshCw, SearchX, SlidersHorizontal, Sparkles, ThumbsUp } from 'lucide-react';
import FilterReport from '../components/movies/FilterReport.jsx';
import RecommendationCard from '../components/movies/RecommendationCard.jsx';
import { ErrorState, SkeletonCard, Spinner, StateMessage } from '../components/ui/Feedback.jsx';
import Toggle from '../components/ui/Toggle.jsx';
import { useApp } from '../context/AppContext.jsx';
import { COMPONENTS, COMPONENT_INFO } from '../utils/components.js';
import { hasYearPreference } from '../utils/prefs.js';

const SORTS = {
  score: { label: 'Match score', compare: (a, b) => a.rank - b.rank },
  rating: { label: 'Rating', compare: (a, b) => b.movie.rating - a.movie.rating || a.rank - b.rank },
  year: { label: 'Newest first', compare: (a, b) => b.movie.year - a.movie.year || a.rank - b.rank },
};

function PreferenceSummary({ prefs, options }) {
  const chips = [
    ...prefs.genres,
    ...prefs.languages.map((l) => `${l}${prefs.strictLanguages ? ' only' : ''}`),
    ...prefs.moods,
    ...prefs.keywords.map((k) => `#${k}`),
    ...prefs.likedMovies.map((m) => `♥ ${m.title}`),
  ];
  if (hasYearPreference(prefs, options)) chips.push(`${prefs.yearMin}–${prefs.yearMax}`);
  if (prefs.minRating > 0) chips.push(`★ ${prefs.minRating.toFixed(1)}+`);
  return (
    <div className="summary-chips">
      {chips.map((chip, i) => (
        <span key={`${i}-${chip}`} className="tag">
          {chip}
        </span>
      ))}
    </div>
  );
}

// Send the user to the step whose filter removed every movie.
function adjustStep(report) {
  if (report.after_min_rating === 0 || report.after_year_range === 0) return 4;
  if ('after_languages' in report) return 1; // a strict language filter emptied or narrowed the list
  if ('after_year_range' in report) return 4;
  return 0;
}

export default function ResultsPage() {
  const { options, status, statusError, connect, prefs, setPrefs, ready, hasPrefs, results, resultsCurrent, fetchRecommendations, feedback, feedbackStale } = useApp();
  const feedbackCount = Object.keys(feedback).length;
  const [sort, setSort] = useState('score');

  useEffect(() => {
    if (ready && !resultsCurrent) fetchRecommendations();
  }, [ready, resultsCurrent, fetchRecommendations]);

  const data = resultsCurrent ? results.data : null;
  const loading = resultsCurrent && results.loading;
  const error = resultsCurrent ? results.error : '';
  const sorted = useMemo(
    () => (data ? [...data.recommendations].sort(SORTS[sort].compare) : []),
    [data, sort],
  );

  if (!options) {
    return (
      <div className="page container narrow">
        {status === 'offline' ? (
          <ErrorState title="Can’t reach the recommendation engine" message={statusError} onRetry={connect} />
        ) : (
          <Spinner label="Connecting to the recommendation engine…" />
        )}
      </div>
    );
  }

  if (hasPrefs && !ready) {
    return (
      <div className="page container narrow">
        <StateMessage
          icon={SlidersHorizontal}
          title="All of your scoring weights are zero"
          action={
            <Link to="/preferences?step=5" className="btn btn-primary btn-lg">
              <SlidersHorizontal size={18} /> Adjust weights
            </Link>
          }
        >
          <p>Every weight for the preferences you set is 0, so no score can be calculated. Raise at least one weight.</p>
        </StateMessage>
      </div>
    );
  }

  if (!ready) {
    return (
      <div className="page container narrow">
        <StateMessage
          icon={SlidersHorizontal}
          title="No preferences yet"
          action={
            <Link to="/preferences" className="btn btn-primary btn-lg">
              <Sparkles size={18} /> Set my preferences
            </Link>
          }
        >
          <p>Recommendations are calculated from your taste. Pick at least one genre, language, mood or theme to begin.</p>
        </StateMessage>
      </div>
    );
  }

  return (
    <div className="page results-page container">
      <div className="page-head results-head">
        <div>
          <span className="eyebrow">
            <Sparkles size={14} /> Personalised for you
          </span>
          <h1>Your recommendations</h1>
          <PreferenceSummary prefs={prefs} options={options} />
        </div>
        <div className="head-actions">
          <Link to="/preferences?step=5" className="btn btn-ghost">
            <Pencil size={16} /> Edit preferences
          </Link>
          <button type="button" className="btn btn-ghost" onClick={() => fetchRecommendations({ force: true })} disabled={loading}>
            <RefreshCw size={16} className={loading ? 'spin' : ''} /> Refresh
          </button>
        </div>
      </div>

      {error && <ErrorState title="Couldn’t generate recommendations" message={error} onRetry={() => fetchRecommendations({ force: true })} />}

      {loading && (
        <>
          <div className="insight-panel glass skeleton-panel" aria-hidden="true" />
          <div className="rec-grid" aria-busy="true">
            {Array.from({ length: Math.min(prefs.topN, 6) }, (_, i) => (
              <SkeletonCard key={i} />
            ))}
          </div>
        </>
      )}

      {data && (
        <>
          <section className="insight-panel glass" aria-label="How these results were scored">
            <div className="insight-weights">
              <span className="field-label">Weights used (sum to 1)</span>
              <div className="weight-bars">
                {COMPONENTS.map((c) => (
                  <div key={c} className={`weight-bar ${data.profile.weights[c] ? '' : 'is-inactive'}`} title={COMPONENT_INFO[c].help}>
                    <span>{COMPONENT_INFO[c].label}</span>
                    <span className="bar">
                      <span className={`bar-fill fill-${c}`} style={{ width: `${data.profile.weights[c] * 100}%` }} />
                    </span>
                    <strong>{data.profile.weights[c].toFixed(2)}</strong>
                  </div>
                ))}
              </div>
            </div>
            <div className="insight-side">
              <FilterReport report={data.filter_report} />
              {(data.profile.genres_inferred || data.profile.moods_inferred) && (
                <p className="muted small">
                  <Info size={13} /> Genres or moods were inferred from the movies you love.
                </p>
              )}
              {data.warnings.map((w, i) => (
                <p key={`${i}-${w}`} className="warning small">
                  <Info size={13} /> {w}
                </p>
              ))}
            </div>
          </section>

          <section className="feedback-bar glass" aria-label="Feedback personalisation">
            <Toggle
              checked={prefs.useFeedback}
              onChange={(useFeedback) => setPrefs((p) => ({ ...p, useFeedback }))}
              label="Personalise with my feedback"
              description={
                feedbackCount
                  ? `${feedbackCount} movie${feedbackCount === 1 ? '' : 's'} rated. Likes and favourites boost similar movies; dislikes are hidden and demote similar ones.`
                  : 'Like, dislike or save movies to fine-tune future rankings.'
              }
            />
            {feedbackStale && (
              <div className="rerank">
                <ThumbsUp size={15} />
                <span>Your feedback changed since these results were ranked.</span>
                <button type="button" className="btn btn-primary btn-sm" onClick={() => fetchRecommendations({ force: true })}>
                  <RefreshCw size={14} /> Re-rank
                </button>
              </div>
            )}
          </section>

          {sorted.length === 0 ? (
            <StateMessage
              icon={SearchX}
              title="No movies match these preferences"
              action={
                <Link to={`/preferences?step=${adjustStep(data.filter_report)}`} className="btn btn-primary">
                  <SlidersHorizontal size={16} /> Adjust preferences
                </Link>
              }
            >
              <p>{data.message}</p>
              <FilterReport report={data.filter_report} />
            </StateMessage>
          ) : (
            <>
              <div className="results-toolbar">
                <p className="muted">
                  <strong className="text">{sorted.length}</strong> movies, from {data.filter_report.with_positive_score} that
                  matched. Match score is a 0–1 weighted similarity, not a probability.
                </p>
                <label className="sort-control">
                  <span className="muted small">Sort by</span>
                  <span className="select-shell">
                    <select value={sort} onChange={(e) => setSort(e.target.value)}>
                      {Object.entries(SORTS).map(([key, s]) => (
                        <option key={key} value={key}>
                          {s.label}
                        </option>
                      ))}
                    </select>
                    <ChevronDown size={16} />
                  </span>
                </label>
              </div>
              <div className="rec-grid">
                {sorted.map((rec, i) => (
                  <RecommendationCard key={rec.movie_id} rec={rec} style={{ animationDelay: `${Math.min(i, 10) * 45}ms` }} />
                ))}
              </div>
            </>
          )}
        </>
      )}
    </div>
  );
}
