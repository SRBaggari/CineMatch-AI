import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Bookmark, ThumbsDown, ThumbsUp, Trash2 } from 'lucide-react';
import { api } from '../api/client.js';
import FeedbackButtons from '../components/movies/FeedbackButtons.jsx';
import { ErrorState, Spinner, StateMessage } from '../components/ui/Feedback.jsx';
import Poster from '../components/ui/Poster.jsx';
import { useApp } from '../context/AppContext.jsx';

const TABS = [
  { id: 'favorites', label: 'Favourites', icon: Bookmark, match: (f) => f.favorite, empty: 'Save movies with the bookmark button to build your list.' },
  { id: 'liked', label: 'Liked', icon: ThumbsUp, match: (f) => f.reaction === 'like', empty: 'Movies you like boost similar movies in your recommendations.' },
  { id: 'disliked', label: 'Disliked', icon: ThumbsDown, match: (f) => f.reaction === 'dislike', empty: 'Movies you dislike are hidden from recommendations.' },
];

export default function MyListPage() {
  const { feedback, feedbackVersion, clearAllFeedback, status, statusError, connect } = useApp();
  const [retry, setRetry] = useState(0);
  const [tab, setTab] = useState('favorites');
  const [movies, setMovies] = useState({ byId: {}, loading: true, error: '' });

  // Movie details for everything the user has rated, from the feedback endpoint.
  useEffect(() => {
    if (status !== 'online') return undefined;
    let cancelled = false;
    setMovies((m) => ({ ...m, loading: !Object.keys(m.byId).length, error: '' }));
    api
      .feedback()
      .then((data) => !cancelled && setMovies({ byId: Object.fromEntries(data.items.map((i) => [i.movie_id, i.movie])), loading: false, error: '' }))
      .catch((e) => !cancelled && setMovies((m) => ({ ...m, loading: false, error: e.message })));
    return () => {
      cancelled = true;
    };
  }, [status, feedbackVersion, retry]);

  const current = TABS.find((t) => t.id === tab);
  // Live feedback state drives membership, so un-favouriting removes a card immediately.
  const listed = Object.entries(feedback)
    .filter(([, f]) => current.match(f))
    .map(([id]) => movies.byId[id])
    .filter(Boolean);

  return (
    <div className="page my-list-page container">
      <div className="page-head">
        <span className="eyebrow">
          <Bookmark size={14} /> Saved on this device
        </span>
        <h1>My list</h1>
        <p className="muted">Your feedback is stored in the local CineMatch database and used to fine-tune recommendations.</p>
      </div>

      <div className="tabs" role="tablist" aria-label="Feedback lists">
        {TABS.map(({ id, label, icon: Icon, match }) => (
          <button key={id} type="button" role="tab" aria-selected={tab === id} className={`tab ${tab === id ? 'is-active' : ''}`} onClick={() => setTab(id)}>
            <Icon size={16} /> {label}
            <span className="chip-count">{Object.values(feedback).filter(match).length}</span>
          </button>
        ))}
        {Object.keys(feedback).length > 0 && (
          <button
            type="button"
            className="btn btn-ghost btn-sm clear-all"
            onClick={() => window.confirm('Remove all likes, dislikes and favourites?') && clearAllFeedback()}
          >
            <Trash2 size={14} /> Clear all feedback
          </button>
        )}
      </div>

      {status === 'offline' ? (
        <ErrorState title="Can’t load your list" message={statusError} onRetry={connect} />
      ) : movies.error ? (
        <ErrorState title="Couldn’t load your list" message={movies.error} onRetry={() => setRetry((r) => r + 1)} />
      ) : movies.loading ? (
        <Spinner label="Loading your list…" />
      ) : listed.length === 0 ? (
        <StateMessage
          icon={current.icon}
          title={`No ${current.label.toLowerCase()} movies yet`}
          action={
            <Link to="/browse" className="btn btn-primary">
              Browse movies
            </Link>
          }
        >
          <p>{current.empty}</p>
        </StateMessage>
      ) : (
        <div className="browse-grid">
          {listed.map((movie) => (
            <article key={movie.movie_id} className="browse-card glass">
              <Link to={`/movies/${movie.movie_id}`} className="browse-poster">
                <Poster movie={movie} size="tile" showCaption={false} />
              </Link>
              <div className="browse-info">
                <Link to={`/movies/${movie.movie_id}`} className="browse-title">
                  {movie.title}
                </Link>
                <span className="muted small">
                  {movie.year} · {movie.language}
                </span>
                <span className="muted small browse-genres">{movie.genres.join(' · ')}</span>
                <FeedbackButtons movie={movie} size="sm" />
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
