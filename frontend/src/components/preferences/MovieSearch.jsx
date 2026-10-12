import { useEffect, useState } from 'react';
import { Heart, LoaderCircle, Search, Star, X } from 'lucide-react';
import { api } from '../../api/client.js';
import { useDebounce } from '../../hooks/useDebounce.js';

// Optional: movies the user already loves. Their keywords/descriptions join the
// TF-IDF theme profile on the backend, and they are excluded from results.
export default function MovieSearch({ liked, onAdd, onRemove }) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const debounced = useDebounce(query.trim());

  useEffect(() => {
    if (!debounced) {
      setResults([]);
      return undefined;
    }
    let cancelled = false;
    setLoading(true);
    api
      .searchMovies(debounced)
      .then((movies) => !cancelled && setResults(movies))
      .catch(() => !cancelled && setResults([]))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [debounced]);

  const likedIds = new Set(liked.map((m) => m.movie_id));

  return (
    <div className="movie-search">
      <div className="input-shell">
        <Search size={17} />
        <input
          type="text"
          value={query}
          placeholder="Search the catalogue, e.g. Interstellar"
          onChange={(e) => {
            setQuery(e.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          onBlur={() => setTimeout(() => setOpen(false), 150)}
          aria-label="Search movies you love"
        />
        {loading && <LoaderCircle size={17} className="spin" />}
      </div>

      {open && debounced && (
        <ul className="search-results glass" role="listbox">
          {results.length === 0 && !loading && <li className="search-empty">No movies found</li>}
          {results.map((movie) => (
            <li key={movie.movie_id}>
              <button
                type="button"
                disabled={likedIds.has(movie.movie_id)}
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => {
                  onAdd(movie);
                  setQuery('');
                  setOpen(false);
                }}
              >
                <span>
                  {movie.title} <span className="muted">({movie.year})</span>
                </span>
                <span className="search-meta">
                  <Star size={12} fill="currentColor" /> {movie.rating.toFixed(1)}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}

      {liked.length > 0 && (
        <div className="pill-row">
          {liked.map((movie) => (
            <span key={movie.movie_id} className="pill pill-love">
              <Heart size={12} fill="currentColor" />
              {movie.title}
              <button type="button" onClick={() => onRemove(movie.movie_id)} aria-label={`Remove ${movie.title}`}>
                <X size={12} />
              </button>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
