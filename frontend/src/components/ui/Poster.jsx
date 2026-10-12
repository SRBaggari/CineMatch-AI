import { genreStyle, titleHash } from '../../utils/genres.js';

// Generated artwork: no external image API. Colours come from the movie's main
// genre plus a per-title offset, so every poster is stable and distinct.
export default function Poster({ movie, size = 'md', showCaption = true, className = '' }) {
  const { icon: Icon, hue } = genreStyle(movie.genres[0]);
  const h = titleHash(movie.title);
  const shift = (h % 50) - 25;
  const angle = 130 + (h % 70);
  const style = {
    '--poster-a': `hsl(${hue + shift} 85% 58%)`,
    '--poster-b': `hsl(${hue + shift + 35} 70% 30%)`,
    '--poster-angle': `${angle}deg`,
  };

  return (
    <div className={`poster poster-${size} ${className}`} style={style} aria-hidden="true">
      <div className="poster-glow" />
      <Icon className="poster-icon" strokeWidth={1.4} />
      {showCaption && size !== 'xs' && (
        <div className="poster-caption">
          <span className="poster-title">{movie.title}</span>
          <span className="poster-year">{movie.year}</span>
        </div>
      )}
    </div>
  );
}
