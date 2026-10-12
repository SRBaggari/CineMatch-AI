import { Link } from 'react-router-dom';
import { ArrowRight, Clock, Globe, Lightbulb, Star } from 'lucide-react';
import Poster from '../ui/Poster.jsx';
import ScoreRing from '../ui/ScoreRing.jsx';

export default function RecommendationCard({ rec, style }) {
  const { movie, matched } = rec;
  return (
    <article className="rec-card glass" style={style}>
      <Link to={`/movies/${movie.movie_id}`} className="rec-poster" aria-label={`View details for ${movie.title}`}>
        <Poster movie={movie} />
        <span className="rank-badge">#{rec.rank}</span>
      </Link>

      <div className="rec-body">
        <header className="rec-header">
          <div>
            <h3 className="rec-title">{movie.title}</h3>
            <div className="meta-row">
              <span className={matched.year_in_range ? 'is-match' : ''}>{movie.year}</span>
              <span title="Approximate rating (unverified)">
                <Star size={13} fill="currentColor" className="star" /> {movie.rating.toFixed(1)}
              </span>
              <span>
                <Clock size={13} /> {movie.runtime} min
              </span>
              <span className={matched.language ? 'is-match' : ''}>
                <Globe size={13} /> {movie.language}
              </span>
            </div>
          </div>
          <ScoreRing score={rec.score} size={60} />
        </header>

        <div className="tag-row">
          {movie.genres.map((g) => (
            <span key={g} className={`tag ${matched.genres.includes(g) ? 'is-match' : ''}`}>
              {g}
            </span>
          ))}
        </div>

        <p className="rec-description">{movie.overview}</p>

        <div className="why-box">
          <span className="why-title">
            <Lightbulb size={14} /> Why it’s recommended
          </span>
          <ul>
            {rec.reasons.slice(0, 3).map((reason) => (
              <li key={reason}>{reason}</li>
            ))}
          </ul>
        </div>

        <footer className="rec-footer">
          <div className="mini-bars" aria-label="Score components">
            {Object.entries(rec.components)
              .filter(([, c]) => c.active)
              .map(([name, c]) => (
                <span key={name} title={`${name}: ${c.value.toFixed(2)} × ${c.weight.toFixed(2)}`}>
                  <span className="mini-bar">
                    <span className={`mini-fill fill-${name}`} style={{ height: `${Math.max(6, c.value * 100)}%` }} />
                  </span>
                </span>
              ))}
          </div>
          <Link to={`/movies/${movie.movie_id}`} className="btn btn-secondary btn-sm">
            View Details <ArrowRight size={15} />
          </Link>
        </footer>
      </div>
    </article>
  );
}
