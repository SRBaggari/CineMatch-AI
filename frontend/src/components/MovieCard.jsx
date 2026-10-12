import { useState } from 'react';
import { ChevronDown, ChevronUp, Clock, Globe, Heart, Lightbulb, Star } from 'lucide-react';
import Poster from './Poster.jsx';
import ScoreRing from './ScoreRing.jsx';
import ScoreBreakdown from './ScoreBreakdown.jsx';

export default function MovieCard({ rec, isLiked, onToggleLike, onOpen }) {
  const [showMath, setShowMath] = useState(false);
  const { movie, matched } = rec;

  return (
    <article className="movie-card">
      <button type="button" className="movie-card-poster" onClick={() => onOpen(movie)} aria-label={`Open ${movie.title}`}>
        <Poster movie={movie} />
        <span className="rank">#{rec.rank}</span>
      </button>

      <div className="movie-card-body">
        <div className="movie-card-top">
          <div>
            <h3 className="movie-title">
              <button type="button" className="link" onClick={() => onOpen(movie)}>
                {movie.title}
              </button>
            </h3>
            <div className="meta-row">
              <span className={matched.year_in_range ? 'meta-match' : ''}>{movie.year}</span>
              <span title="Approximate rating (unverified)">
                <Star size={12} fill="currentColor" className="star" /> {movie.rating.toFixed(1)}
              </span>
              <span>
                <Clock size={12} /> {movie.runtime}m
              </span>
              <span className={matched.language ? 'meta-match' : ''}>
                <Globe size={12} /> {movie.language}
              </span>
            </div>
          </div>
          <ScoreRing score={rec.score} />
        </div>

        <div className="tag-row">
          {movie.genres.map((g) => (
            <span key={g} className={`tag ${matched.genres.includes(g) ? 'tag-match' : ''}`}>
              {g}
            </span>
          ))}
          {movie.moods.map((m) => (
            <span key={m} className={`tag tag-mood ${matched.moods.includes(m) ? 'tag-match' : ''}`}>
              {m}
            </span>
          ))}
        </div>

        <div className="why">
          <div className="why-title">
            <Lightbulb size={14} /> Why this movie?
          </div>
          <ul>
            {rec.reasons.slice(0, 4).map((r) => (
              <li key={r}>{r}</li>
            ))}
            {rec.similar_to && (
              <li>
                Closest to <strong>{rec.similar_to.title}</strong>, which you liked (similarity{' '}
                {rec.similar_to.similarity.toFixed(2)})
              </li>
            )}
          </ul>
          {rec.top_terms.length > 0 && (
            <p className="signals">
              Strongest shared TF-IDF terms: <strong>{rec.top_terms.join(' · ')}</strong>
            </p>
          )}
        </div>

        <div className="card-actions">
          <button type="button" className="btn btn-small btn-ghost" onClick={() => setShowMath((s) => !s)}>
            {showMath ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
            Score components
          </button>
          <button
            type="button"
            className={`btn btn-small ${isLiked ? 'btn-liked' : 'btn-ghost'}`}
            onClick={() => onToggleLike(movie)}
          >
            <Heart size={14} fill={isLiked ? 'currentColor' : 'none'} />
            {isLiked ? 'Liked' : 'Like'}
          </button>
        </div>

        {showMath && <ScoreBreakdown components={rec.components} total={rec.score} />}
      </div>
    </article>
  );
}
