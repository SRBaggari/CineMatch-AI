import { genreStyle, titleHash } from '../utils/genres.js';

// Generated poster: no external image APIs, just a genre-coloured gradient.
export default function Poster({ movie, size = 'md' }) {
  const primary = movie.genres[0];
  const { icon: Icon, hue } = genreStyle(primary);
  const shift = titleHash(movie.title) % 40;
  const style = {
    background: `linear-gradient(150deg, hsl(${hue + shift} 70% 42%) 0%, hsl(${hue + shift + 40} 60% 18%) 70%, hsl(${hue} 40% 10%) 100%)`,
  };

  return (
    <div className={`poster poster-${size}`} style={style} aria-hidden="true">
      <Icon className="poster-icon" strokeWidth={1.5} />
      {size !== 'sm' && (
        <div className="poster-caption">
          <span className="poster-title">{movie.title}</span>
          <span className="poster-year">{movie.year}</span>
        </div>
      )}
    </div>
  );
}
