import { Link } from 'react-router-dom';
import { ArrowRight, Clock, EyeOff, Globe, Lightbulb, Star } from 'lucide-react';
import { useApp } from '../../context/AppContext.jsx';
import Poster from '../ui/Poster.jsx';
import ScoreRing from '../ui/ScoreRing.jsx';
import FeedbackButtons from './FeedbackButtons.jsx';
import ScoreSummary from './ScoreSummary.jsx';

// Compact breakdown shown on every card (full maths lives on the details page).
const CARD_COMPONENTS = [
  ['genre', 'Genre match'],
  ['language', 'Language match'],
  ['mood', 'Mood match'],
  ['keyword', 'Keyword similarity'],
];

export default function RecommendationCard({ rec, style }) {
  const { feedback } = useApp();
  const { movie, matched } = rec;
  const disliked = feedback[movie.movie_id]?.reaction === 'dislike';

  return (
    <article className={`rec-card glass ${disliked ? 'is-disliked' : ''}`} style={style}>
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
          <p className="why-summary">{rec.summary}</p>
        </div>

        <dl className="card-breakdown" aria-label="Score breakdown">
          {CARD_COMPONENTS.map(([key, label]) => {
            const c = rec.components[key];
            return (
              <div key={key} className={c.active ? '' : 'is-inactive'} title={c.active ? `${c.value.toFixed(2)} × weight ${c.weight.toFixed(2)}` : 'No preference set'}>
                <dt>{label}</dt>
                <dd>
                  <span className="bar">
                    <span className={`bar-fill fill-${key}`} style={{ width: `${c.value * 100}%` }} />
                  </span>
                  <span className="mono">{c.active ? c.value.toFixed(2) : '—'}</span>
                </dd>
              </div>
            );
          })}
          <div className="overall">
            <dt>Overall relevance</dt>
            <dd>
              <ScoreSummary item={rec} compact />
            </dd>
          </div>
        </dl>

        {disliked && (
          <p className="disliked-note">
            <EyeOff size={14} /> You disliked this. It will be hidden next time recommendations refresh.
          </p>
        )}

        <footer className="rec-footer">
          <FeedbackButtons movie={movie} size="sm" />
          <Link to={`/movies/${movie.movie_id}`} className="btn btn-secondary btn-sm">
            View Details <ArrowRight size={15} />
          </Link>
        </footer>
      </div>
    </article>
  );
}
