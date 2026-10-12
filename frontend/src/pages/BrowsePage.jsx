import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { ChevronDown, LoaderCircle, RotateCcw, Search, SearchX, Star, X } from 'lucide-react';
import { api } from '../api/client.js';
import FeedbackButtons from '../components/movies/FeedbackButtons.jsx';
import { ErrorState, Spinner, StateMessage } from '../components/ui/Feedback.jsx';
import MultiSelectDropdown from '../components/ui/MultiSelectDropdown.jsx';
import Poster from '../components/ui/Poster.jsx';
import RangeSlider from '../components/ui/RangeSlider.jsx';
import Toggle from '../components/ui/Toggle.jsx';
import { useApp } from '../context/AppContext.jsx';
import { useDebounce } from '../hooks/useDebounce.js';

const PAGE_SIZE = 24;
const SORTS = [
  ['relevance', 'Relevance'],
  ['rating', 'Rating'],
  ['year', 'Newest'],
  ['title', 'Title A–Z'],
];

function BrowseCard({ item }) {
  const { movie } = item;
  return (
    <article className="browse-card glass">
      <Link to={`/movies/${movie.movie_id}`} className="browse-poster" aria-label={`View details for ${movie.title}`}>
        <Poster movie={movie} size="tile" showCaption={false} />
        {item.match_score !== null && (
          <span className="match-badge" title="Match score for your preferences (0–1)">
            {item.match_score.toFixed(2)}
          </span>
        )}
      </Link>
      <div className="browse-info">
        <Link to={`/movies/${movie.movie_id}`} className="browse-title">
          {movie.title}
        </Link>
        <span className="muted small">
          {movie.year} · <Star size={11} fill="currentColor" className="star" /> {movie.rating.toFixed(1)} · {movie.language}
        </span>
        <span className="muted small browse-genres">{movie.genres.join(' · ')}</span>
        <FeedbackButtons movie={movie} size="sm" />
      </div>
    </article>
  );
}

export default function BrowsePage() {
  const { options, status, statusError, connect, payload, ready, feedbackVersion } = useApp();
  const [query, setQuery] = useState('');
  const [genres, setGenres] = useState([]);
  const [languages, setLanguages] = useState([]);
  const [years, setYears] = useState(null);
  const [sort, setSort] = useState('relevance');
  const [personal, setPersonal] = useState(true);
  const [state, setState] = useState({ items: [], total: 0, loading: true, error: '', personalized: false });
  const [page, setPage] = useState(1);
  const [retry, setRetry] = useState(0);
  const debouncedQuery = useDebounce(query.trim(), 250);

  const yearRange = years ?? (options ? [options.year_min, options.year_max] : null);
  const usePrefs = personal && ready;

  const request = useMemo(() => {
    if (!options) return null;
    return {
      query: debouncedQuery,
      genres,
      languages,
      year_min: yearRange[0] > options.year_min ? yearRange[0] : null,
      year_max: yearRange[1] < options.year_max ? yearRange[1] : null,
      sort,
      preferences: usePrefs ? payload : null,
      limit: PAGE_SIZE * page,
      offset: 0,
    };
  }, [options, debouncedQuery, genres, languages, yearRange, sort, usePrefs, payload, page]);
  const requestKey = request ? JSON.stringify(request) : '';

  useEffect(() => {
    if (!requestKey) return undefined;
    let cancelled = false;
    setState((s) => ({ ...s, loading: true, error: '' }));
    api
      .search(JSON.parse(requestKey))
      .then((data) => !cancelled && setState({ items: data.items, total: data.total, loading: false, error: '', personalized: data.personalized }))
      .catch((e) => !cancelled && setState((s) => ({ ...s, loading: false, error: e.message })));
    return () => {
      cancelled = true;
    };
    // feedbackVersion: personalised relevance includes feedback, so re-query after changes.
  }, [requestKey, feedbackVersion, retry]);

  // Any filter change starts again from the first page.
  useEffect(() => {
    setPage(1);
  }, [debouncedQuery, genres, languages, years, sort, usePrefs]);

  if (!options) {
    return (
      <div className="page container narrow">
        {status === 'offline' ? <ErrorState title="Can’t load the catalogue" message={statusError} onRetry={connect} /> : <Spinner label="Loading catalogue…" />}
      </div>
    );
  }

  const filtersActive = query || genres.length || languages.length || years || sort !== 'relevance';
  const relevanceNote = state.personalized
    ? 'Relevance = match score for your saved preferences and feedback.'
    : debouncedQuery
      ? 'Relevance = how closely the title matches your search.'
      : 'Relevance falls back to rating until you search or set preferences.';

  return (
    <div className="page browse-page container">
      <div className="page-head">
        <span className="eyebrow">
          <Search size={14} /> Browse the catalogue
        </span>
        <h1>Search & filter movies</h1>
      </div>

      <section className="filter-panel glass" aria-label="Search and filters">
        <div className="input-shell search-shell">
          <Search size={18} />
          <input
            type="search"
            value={query}
            placeholder="Search by title…"
            aria-label="Search movies by title"
            onChange={(e) => setQuery(e.target.value)}
          />
          {query && (
            <button type="button" className="icon-btn" onClick={() => setQuery('')} aria-label="Clear search">
              <X size={16} />
            </button>
          )}
        </div>
        <div className="filter-grid">
          <MultiSelectDropdown label="Genre" options={Object.keys(options.genres).sort()} selected={genres} counts={options.genres} placeholder="Any genre" onChange={setGenres} />
          <MultiSelectDropdown label="Language" options={Object.keys(options.languages)} selected={languages} counts={options.languages} placeholder="Any language" onChange={setLanguages} />
          <div>
            <span className="field-label">Release year</span>
            <RangeSlider label="Release year" min={options.year_min} max={options.year_max} low={yearRange[0]} high={yearRange[1]} onChange={setYears} />
          </div>
          <label>
            <span className="field-label">Sort by</span>
            <span className="select-shell">
              <select value={sort} onChange={(e) => setSort(e.target.value)}>
                {SORTS.map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
              <ChevronDown size={18} />
            </span>
          </label>
        </div>
        <div className="filter-footer">
          <Toggle
            checked={personal && ready}
            onChange={setPersonal}
            label="Rank by my preferences"
            description={ready ? 'Shows each movie’s match score.' : 'Set preferences first to enable this.'}
          />
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            disabled={!filtersActive}
            onClick={() => {
              setQuery('');
              setGenres([]);
              setLanguages([]);
              setYears(null);
              setSort('relevance');
            }}
          >
            <RotateCcw size={14} /> Reset filters
          </button>
        </div>
      </section>

      <div className="results-toolbar">
        <p className="muted" aria-live="polite">
          <strong className="text">{state.total}</strong> movie{state.total === 1 ? '' : 's'} found.{' '}
          {sort === 'relevance' && relevanceNote}
        </p>
        {state.loading && <LoaderCircle size={18} className="spin muted" />}
      </div>

      {state.error && <ErrorState title="Search failed" message={state.error} onRetry={() => setRetry((r) => r + 1)} />}

      {!state.error && !state.loading && state.items.length === 0 ? (
        <StateMessage icon={SearchX} title="No movies match these filters">
          <p>Try a shorter title, fewer genres or a wider year range.</p>
        </StateMessage>
      ) : (
        <div className={`browse-grid ${state.loading ? 'is-loading' : ''}`}>
          {state.items.map((item) => (
            <BrowseCard key={item.movie.movie_id} item={item} />
          ))}
        </div>
      )}

      {state.items.length < state.total && (
        <div className="load-more">
          <button type="button" className="btn btn-ghost" onClick={() => setPage((p) => p + 1)} disabled={state.loading}>
            Show more ({state.total - state.items.length} remaining)
          </button>
        </div>
      )}
    </div>
  );
}
