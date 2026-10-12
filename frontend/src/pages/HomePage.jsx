import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  ArrowRight,
  BookOpen,
  Clock,
  Cpu,
  Globe,
  Layers,
  ListOrdered,
  Network,
  Play,
  SlidersHorizontal,
  Sparkles,
  Star,
} from 'lucide-react';
import { api } from '../api/client.js';
import MovieTile from '../components/movies/MovieTile.jsx';
import { ErrorState, Spinner } from '../components/ui/Feedback.jsx';
import Poster from '../components/ui/Poster.jsx';
import { useApp } from '../context/AppContext.jsx';
import { formatRuntime } from '../utils/format.js';

const STEPS = [
  { icon: SlidersHorizontal, title: 'Tell us your taste', text: 'Pick genres, languages, a mood, themes, an era and a minimum rating.' },
  { icon: Layers, title: 'Movies become vectors', text: 'Every movie is described by numbers: its genres, moods, language, year and words.' },
  { icon: Network, title: 'Similarity is measured', text: 'TF-IDF and cosine similarity compare your preferences with each movie.' },
  { icon: ListOrdered, title: 'Ranked & explained', text: 'A weighted score ranks the catalogue and every pick shows why it was chosen.' },
];

export default function HomePage() {
  const { dataset, ready, status } = useApp();
  const [top, setTop] = useState({ items: [], loading: true, error: '' });

  const loadTop = () => {
    setTop((t) => ({ ...t, loading: true, error: '' }));
    api
      .listMovies({ limit: '10' })
      .then((page) => setTop({ items: page.items, loading: false, error: '' }))
      .catch((e) => setTop({ items: [], loading: false, error: e.message }));
  };

  useEffect(() => {
    if (status === 'online') loadTop();
  }, [status]);

  const featured = top.items[0];
  const collage = top.items.slice(1, 4);

  return (
    <div className="page home-page">
      {/* ---------------------------------------------------------------- hero */}
      <section className="hero container">
        <div className="hero-copy">
          <span className="eyebrow">
            <Sparkles size={14} /> Explainable AI movie recommendations
          </span>
          <h1>
            Discover Movies <span className="gradient-text">Made for You</span>
          </h1>
          <p className="lead">
            Tell CineMatch AI what you enjoy and it scores every movie in its catalogue against your taste using
            content-based filtering, TF-IDF and cosine similarity. No random picks: every recommendation comes with the
            reasons and the numbers behind it.
          </p>
          <div className="hero-actions">
            <Link to="/preferences" className="btn btn-primary btn-lg">
              Get Started <ArrowRight size={18} />
            </Link>
            <Link to="/how-it-works" className="btn btn-ghost btn-lg">
              <BookOpen size={18} /> How it works
            </Link>
          </div>
          {dataset && (
            <dl className="hero-stats">
              <div>
                <dt>Movies</dt>
                <dd>{dataset.total_movies}</dd>
              </div>
              <div>
                <dt>Genres</dt>
                <dd>{dataset.genres}</dd>
              </div>
              <div>
                <dt>Languages</dt>
                <dd>{dataset.languages}</dd>
              </div>
              <div>
                <dt>Moods</dt>
                <dd>{dataset.moods}</dd>
              </div>
            </dl>
          )}
        </div>

        <div className="hero-visual" aria-hidden="true">
          {collage.length === 3 ? (
            <div className="poster-stack">
              {collage.map((movie, i) => (
                <Poster key={movie.movie_id} movie={movie} size="lg" className={`stack-${i}`} />
              ))}
            </div>
          ) : (
            <div className="poster-stack placeholder">
              <div className="skeleton stack-0" />
              <div className="skeleton stack-1" />
              <div className="skeleton stack-2" />
            </div>
          )}
          <div className="hero-orb" />
        </div>
      </section>

      {ready && (
        <section className="container">
          <div className="welcome-back glass">
            <Sparkles size={20} />
            <span>Welcome back. Your preferences are saved on this device.</span>
            <Link to="/recommendations" className="btn btn-primary btn-sm">
              See my recommendations <ArrowRight size={15} />
            </Link>
          </div>
        </section>
      )}

      {/* ---------------------------------------------------------------- featured */}
      <section className="section container" aria-labelledby="featured-heading">
        <div className="section-head">
          <div>
            <span className="eyebrow">Featured</span>
            <h2 id="featured-heading">Highest rated in the catalogue</h2>
          </div>
          <p className="muted small section-note">
            Sorted by catalogue rating, not personalised. Your personal picks are on the recommendations page.
          </p>
        </div>

        {top.loading && status !== 'offline' && <Spinner label="Loading featured movies…" />}
        {top.error && <ErrorState title="Couldn’t load featured movies" message={top.error} onRetry={loadTop} />}
        {status === 'offline' && !top.items.length && (
          <p className="muted">Featured movies will appear once the backend is running.</p>
        )}

        {featured && (
          <>
            <article className="featured glass">
              <Poster movie={featured} size="xl" />
              <div className="featured-body">
                <span className="badge">
                  <Star size={13} fill="currentColor" /> {featured.rating.toFixed(1)} catalogue rating
                </span>
                <h3>{featured.title}</h3>
                <div className="meta-row">
                  <span>{featured.year}</span>
                  <span>
                    <Clock size={14} /> {formatRuntime(featured.runtime)}
                  </span>
                  <span>
                    <Globe size={14} /> {featured.language}
                  </span>
                  <span>Directed by {featured.director}</span>
                </div>
                <div className="tag-row">
                  {featured.genres.map((g) => (
                    <span key={g} className="tag">
                      {g}
                    </span>
                  ))}
                  {featured.moods.map((m) => (
                    <span key={m} className="tag tag-mood">
                      {m}
                    </span>
                  ))}
                </div>
                <p className="featured-overview">{featured.overview}</p>
                <div className="hero-actions">
                  <Link to={`/movies/${featured.movie_id}`} className="btn btn-primary">
                    <Play size={16} fill="currentColor" /> View details
                  </Link>
                  <Link to="/preferences" className="btn btn-ghost">
                    Find movies like this for me
                  </Link>
                </div>
              </div>
            </article>

            <div className="tile-row" role="list">
              {top.items.slice(1).map((movie) => (
                <div role="listitem" key={movie.movie_id}>
                  <MovieTile movie={movie} />
                </div>
              ))}
            </div>
          </>
        )}
      </section>

      {/* ---------------------------------------------------------------- how it works */}
      <section className="section container" aria-labelledby="how-heading">
        <div className="section-head">
          <div>
            <span className="eyebrow">
              <Cpu size={14} /> Under the hood
            </span>
            <h2 id="how-heading">How It Works</h2>
          </div>
          <Link to="/how-it-works" className="btn btn-ghost btn-sm">
            Full explanation <ArrowRight size={15} />
          </Link>
        </div>
        <div className="step-grid">
          {STEPS.map(({ icon: Icon, title, text }, i) => (
            <div key={title} className="step-card glass">
              <span className="step-number">0{i + 1}</span>
              <span className="step-icon">
                <Icon size={22} />
              </span>
              <h3>{title}</h3>
              <p>{text}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="section container">
        <div className="cta-band">
          <div>
            <h2>Ready for your next favourite movie?</h2>
            <p>It takes about a minute to set your preferences.</p>
          </div>
          <Link to="/preferences" className="btn btn-light btn-lg">
            Get Started <ArrowRight size={18} />
          </Link>
        </div>
      </section>
    </div>
  );
}
