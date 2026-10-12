import { useEffect, useState } from 'react';
import { Clock, Film, Globe, Heart, LoaderCircle, Star, Users, X } from 'lucide-react';
import { api } from '../api/client.js';
import Poster from './Poster.jsx';

function sharedSummary(item) {
  const parts = [];
  if (item.shared_genres.length) parts.push(item.shared_genres.join(', '));
  if (item.shared_moods.length) parts.push(item.shared_moods.join(', '));
  if (item.shared_keywords.length) parts.push(`themes: ${item.shared_keywords.join(', ')}`);
  if (item.same_director) parts.push('same director');
  if (item.shared_cast.length) parts.push(`cast: ${item.shared_cast.join(', ')}`);
  return parts.join(' · ');
}

export default function MovieModal({ movie, onClose, onSelect, isLiked, onToggleLike }) {
  const [similar, setSimilar] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError('');
    api
      .similar(movie.movie_id, 6)
      .then((data) => !cancelled && setSimilar(data.similar))
      .catch((e) => !cancelled && setError(e.message))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [movie.movie_id]);

  useEffect(() => {
    const onKey = (e) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  return (
    <div className="modal-backdrop" onClick={onClose} role="presentation">
      <div className="modal" role="dialog" aria-modal="true" aria-label={movie.title} onClick={(e) => e.stopPropagation()}>
        <button type="button" className="modal-close icon-button" onClick={onClose} aria-label="Close">
          <X size={18} />
        </button>

        <div className="modal-hero">
          <Poster movie={movie} size="lg" />
          <div className="modal-info">
            <h2>{movie.title}</h2>
            <div className="meta-row">
              <span>{movie.year}</span>
              <span>
                <Star size={13} fill="currentColor" className="star" /> {movie.rating.toFixed(1)}/10 (approx.)
              </span>
              <span>
                <Clock size={13} /> {movie.runtime} min
              </span>
              <span>
                <Globe size={13} /> {movie.language}
              </span>
            </div>
            <p className="overview">{movie.overview}</p>
            <dl className="details">
              <dt>
                <Film size={13} /> Director
              </dt>
              <dd>{movie.director}</dd>
              <dt>
                <Users size={13} /> Cast
              </dt>
              <dd>{movie.cast.join(', ')}</dd>
            </dl>
            <div className="tag-row">
              {movie.genres.map((g) => (
                <span key={g} className="tag">
                  {g}
                </span>
              ))}
              {movie.moods.map((m) => (
                <span key={m} className="tag tag-mood">
                  {m}
                </span>
              ))}
              {movie.keywords.map((k) => (
                <span key={k} className="tag tag-keyword">
                  #{k}
                </span>
              ))}
            </div>
            <button
              type="button"
              className={`btn btn-small ${isLiked ? 'btn-liked' : 'btn-ghost'}`}
              onClick={() => onToggleLike(movie)}
            >
              <Heart size={14} fill={isLiked ? 'currentColor' : 'none'} />
              {isLiked ? 'In your favourites' : 'Add to favourites'}
            </button>
          </div>
        </div>

        <h3 className="modal-subtitle">More like this (cosine similarity of movie feature vectors)</h3>
        {loading && (
          <p className="muted">
            <LoaderCircle size={14} className="spin" /> Computing similar movies…
          </p>
        )}
        {error && <p className="error-text">{error}</p>}
        <div className="similar-grid">
          {similar.map((item) => (
            <button key={item.movie.movie_id} type="button" className="similar-item" onClick={() => onSelect(item.movie)}>
              <Poster movie={item.movie} size="sm" />
              <div>
                <strong>{item.movie.title}</strong>
                <span className="similar-score">similarity {item.similarity.toFixed(2)}</span>
                <span className="muted small">{sharedSummary(item)}</span>
              </div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
