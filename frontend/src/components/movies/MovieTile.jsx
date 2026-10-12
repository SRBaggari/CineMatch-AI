import { Link } from 'react-router-dom';
import { Star } from 'lucide-react';
import Poster from '../ui/Poster.jsx';

// Compact poster tile used for featured rows and similar movies.
export default function MovieTile({ movie, caption }) {
  return (
    <Link to={`/movies/${movie.movie_id}`} className="movie-tile">
      <Poster movie={movie} size="tile" showCaption={false} />
      <div className="movie-tile-info">
        <strong>{movie.title}</strong>
        <span className="muted small">
          {movie.year} · <Star size={11} fill="currentColor" className="star" /> {movie.rating.toFixed(1)}
        </span>
        {caption && <span className="tile-caption">{caption}</span>}
      </div>
    </Link>
  );
}
